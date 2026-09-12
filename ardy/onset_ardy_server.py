# onset_ardy_server.py -- On-Set Studio <-> ARDY bridge  (ardy-bridge-v5.3)
#
# Run (in the ARDY venv, from C:\dev\ardy):
#   python onset_ardy_server.py
#
# v4 = ROOT WAYPOINTS (Tier-3 slice 1). /generate now accepts optional
# root_waypoints -- ground marks the editor samples from a character's drawn
# path -- and turns them into ARDY Root2DConstraintSet kinematic constraints,
# mirroring scripts/generate.py's --constraints branch exactly:
#   constraint_lst -> motion_rep.create_conditions_from_constraints_batched
#   -> model(motion_mask=..., observed_motion=...) -> post_process_motion(
#      constraint_lst=...).
# Waypoint wire format (editor -> bridge), all editor-side numbers:
#   root_waypoints: [{"f": 0..1, "x": cm, "z": cm}, ...]
#     f      = time fraction of the clip at which to hit the mark
#     x, z   = ground offset in RIG-LOCAL CM RELATIVE TO THE REST HIPS XZ
#              (the same frame the retargeted Hips pos track plays in, so
#              the round-trip editor->ARDY->editor lands on the mark)
#   hips_rest_y_cm: the ACTIVE rig's hips rest height (cm). REQUIRED with
#     waypoints -- it is the cm side of the cm->m conversion, and sending
#     the active rig's own value (not mixamo_rest.json's) makes the editor's
#     per-rig clip rescale (k = thisRig/clipRig) cancel out exactly.
# cm -> m scale for constraints = hips_rest_y_cm / ARDY neutral standing
# height (hips-above-foot at neutral, from the skeleton assets). KNOWN
# CALIBRATION: retarget_ardy.py maps m -> cm with the PER-CLIP posed height
# (mean hips-above-foot while moving, slightly less than neutral -- knees
# bend), so landings can run a few % short of the mark. If you measure a
# consistent undershoot, the lever is switching retarget's scale to the
# same neutral height (its own versioned change; do not bury it here).
#
# v3 = FULLY WARM, IN-PROCESS. v1/v2 kept NVIDIA's gradio text-encoder
# service warm as a child -- but that service is broken on Windows (it
# writes embeddings to C:\tmp\text_encoder, a POSIX-ism gradio's security
# check refuses to serve; observed 2026-07-16). v3 removes it entirely:
# the bridge imports ARDY and loads the model ONCE in-process -- the same
# "local LLM2Vec fallback" path every successful solo run used -- then
# generates per-request with everything warm. First /generate (or /load)
# pays the one-time Llama load; after that, prompts take seconds.
#
# Endpoints (same contract as v1/v2 -- the editor needs no change):
#   POST /generate {prompt, duration, seed?} -> clip JSON + saved paths
#   POST /unload   -> frees the model (~14GB VRAM) for ComfyUI runs
#   POST /load     -> pre-warm ahead of time (optional)
#   GET  /status   -> loaded state + VRAM numbers
#
# The generation body mirrors scripts/generate.py exactly (single sample,
# no constraints): load_model -> length_to_mask -> model(...) ->
# motion_rep.inverse -> post_process_motion -> to_numpy -> npz -> retarget.

import os

os.environ.setdefault("CUDA_VISIBLE_DEVICES", "0")  # 4090 pin (5060 Ti sm_120 unsupported)
# v3.1: HF OFFLINE MODE. Every model file is already in the local HF cache
# (the 16GB Llama download is done); without this, huggingface_hub HEAD-
# checks hf.co for updates on every load, and an HF outage (504s, observed
# 2026-07-16) stalls the bridge for nothing. Offline = load straight from
# cache, zero network. ESCAPE HATCH: if a future model/file is genuinely
# missing from the cache, offline mode errors instead of downloading -- set
# ONSET_HF_ONLINE=1 in the environment (or delete these lines) for that one
# run, let it download, then go offline again.
if not os.environ.get("ONSET_HF_ONLINE"):
    os.environ.setdefault("HF_HUB_OFFLINE", "1")
    os.environ.setdefault("TRANSFORMERS_OFFLINE", "1")

import gc
import json
import random
import re
import time
from pathlib import Path

import numpy as np
import torch
import uvicorn
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from retarget_ardy import retarget

ROOT = Path(__file__).resolve().parent          # C:\dev\ardy
OUT_DIR = ROOT / "outputs" / "onset"
REST_JSON = ROOT / "mixamo_rest.json"
PORT = 8765
DEVICE = "cuda:0" if torch.cuda.is_available() else "cpu"

app = FastAPI(title="On-Set ARDY bridge v4")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # local tool: the editor runs on localhost
    allow_methods=["*"],
    allow_headers=["*"],
)

_model = None
_model_name = ""


def vram_mb() -> int:
    if not torch.cuda.is_available():
        return 0
    return int(torch.cuda.memory_allocated() / (1024 * 1024))


def ensure_model():
    """Load ARDY once; every later prompt reuses the warm model."""
    global _model, _model_name
    if _model is not None:
        return _model
    from ardy.model import DEFAULT_MODEL, load_model
    from ardy.model.loading import get_env_var
    from ardy.model.registry import resolve_model_name

    t0 = time.time()
    ckpt_dir = get_env_var("CHECKPOINTS_DIR")
    _model_name = resolve_model_name(DEFAULT_MODEL, checkpoints_dir=ckpt_dir)
    print(f"[bridge] loading {_model_name} (one-time; the local text encoder "
          "makes this a few minutes on a cold cache)…")
    _model = load_model(_model_name, device=DEVICE, checkpoints_dir=ckpt_dir)
    print(f"[bridge] model warm in {time.time() - t0:.0f}s -- VRAM {vram_mb()}MB. "
          "Prompts are fast from here.")
    return _model


def free_model() -> str:
    global _model
    if _model is None:
        gc.collect()
        if torch.cuda.is_available():
            torch.cuda.empty_cache()
        return "already cold"
    before = vram_mb()
    _model = None
    gc.collect()
    if torch.cuda.is_available():
        torch.cuda.empty_cache()
        torch.cuda.synchronize()
    return f"model unloaded -- VRAM {before}MB -> {vram_mb()}MB"


def default_history_frames(fps: float, gen_horizon_len: int, patch: int) -> int:
    """scripts/generate.py's _default_history_frames, verbatim: the longest
    history that keeps each autoregressive step inside the trained 10s
    window (longer degrades into jitter)."""
    max_window_len = (int(10 * fps) // patch) * patch
    return ((max_window_len - gen_horizon_len) // patch) * patch


_neutral_h: float | None = None


def neutral_standing_height_m() -> float:
    """v4.1: the waypoint cm->m basis, now IMPORTED from retarget_ardy's
    ardy_neutral_hips_above_floor() -- hips above the FLOOR (ToeBase) plane.
    Single source of truth with the m->cm direction: v4.0 measured to the
    FOOT joint (the ankle) while the retarget's numerator measured to the
    floor, and that ~9% span mismatch was the residual "walking on air"
    hover plus a matching waypoint overshoot (retarget-v4's verdict comment
    has the probe numbers). Fallback 0.98m = floor-span human."""
    global _neutral_h
    if _neutral_h is not None:
        return _neutral_h
    try:
        from retarget_ardy import ardy_neutral_hips_above_floor
        h = ardy_neutral_hips_above_floor()
        if h > 1e-3:
            _neutral_h = h
            print(f"[bridge] ARDY neutral hips-above-floor {h:.3f}m (waypoint scale base)")
            return _neutral_h
    except Exception as e:  # noqa: BLE001
        print(f"[bridge][warn] neutral height unavailable ({e}); using 0.98m fallback")
    _neutral_h = 0.98
    return _neutral_h


def slugify(prompt: str, n: int = 36) -> str:
    s = re.sub(r"[^a-z0-9]+", "_", prompt.lower()).strip("_")
    return (s[:n].rstrip("_")) or "clip"


class GenReq(BaseModel):
    # v5.0.1 (fixing 422s in the field): OPTIONAL -- a segmented request carries its
    # prompts inside `segments` and has no top-level prompt; requiring one
    # made pydantic 422 the whole segmented feature at the door. Per-
    # segment prompt validation in the handler still rejects empties.
    prompt: str = ""
    duration: float = 5.0
    seed: int | None = None
    # v4: optional root waypoints (see header for the wire format). None or
    # empty = plain unconstrained generation, identical to v3.1 behavior.
    root_waypoints: list[dict] | None = None
    hips_rest_y_cm: float | None = None
    # v4.4: grapple points -- {f, hand:'L'|'R', x,y,z, hipX,hipY,hipZ, h},
    # all rig-local cm (+h radians), same frame as waypoints.
    grapples: list[dict] | None = None
    # v5.3 (Layer 3): FOOT constraints -- {f, foot:'L'|'R', x,y,z,
    # hipX,hipY,hipZ, h}, rig-local cm. Same authoring as grapples but the
    # target is a foot on a raised surface: stepping onto a crate, landing
    # a leap. This is the only way to express HEIGHT -- root waypoints are
    # XZ-only by construction.
    feet: list[dict] | None = None
    # v5, the "series of events" design: segments -- each generated
    # separately, seg N seeded from seg N-1's FINAL pose (FullBody@frame0
    # + matching first_heading) IN THE SAME COORDINATE FRAME, then all
    # concatenated into ONE clip. Kills the anticipatory crouch-walk: a
    # 2.5s action segment can only anticipate for 2.5s. Each segment:
    # {prompt, duration, root_waypoints?, grapples?} (fractions are
    # SEGMENT-local). Top-level prompt/duration are ignored when present.
    segments: list[dict] | None = None


@app.get("/status")
def status():
    return {"ok": True, "model": "warm" if _model is not None else "cold",
            "name": _model_name, "vramMB": vram_mb(), "device": DEVICE,
            "outputs": str(OUT_DIR)}


@app.post("/load")
def load():
    ensure_model()
    return {"ok": True, "message": f"model warm ({vram_mb()}MB)"}


@app.post("/unload")
def unload():
    return {"ok": True, "message": free_model()}


def _heading_from_pose(pj_last, skeleton) -> float:
    """Heading angle of a posed skeleton (tools.py's hip-line formula)."""
    import math as _m
    r, l = skeleton.hip_joint_idx
    d = pj_last[r] - pj_last[l]
    return float(_m.atan2(float(d[2]), float(-d[0])))


@app.post("/generate")
def generate(req: GenReq):
    # v5, the "series of events" verdict (2026-07-17): one text over a
    # whole clip + ARDY's long-horizon anticipation = the take crouch-walks
    # its entire run-up to a grab. Segmentation is the fix: each segment is
    # its own generation with its own text and SEGMENT-LOCAL constraints;
    # segment N is seeded with segment N-1's FINAL pose (FullBody@frame0,
    # first_heading matched) IN THE SAME COORDINATE FRAME, so the model
    # CONTINUES rather than restarts, and anticipation is bounded to the
    # segment's own length. All segments concatenate into ONE npz -> ONE
    # retarget -> ONE clip: the editor sees a single block, the seam is the
    # seed pose itself.
    t0 = time.time()
    segs = req.segments if req.segments else [{
        "prompt": req.prompt, "duration": req.duration,
        "root_waypoints": req.root_waypoints, "grapples": req.grapples,
    }]
    for sg in segs:
        if not str(sg.get("prompt", "") or "").strip():
            return {"ok": False, "error": "empty prompt in a segment"}
    if not REST_JSON.is_file():
        return {"ok": False, "error": f"missing {REST_JSON} -- dump it from "
                "the editor console with copy(ipDumpRestPose())"}
    seed = req.seed if req.seed is not None else random.randint(0, 2**31 - 1)
    any_con = any((sg.get("root_waypoints") or sg.get("grapples")) for sg in segs)
    if any_con and (not req.hips_rest_y_cm or req.hips_rest_y_cm <= 1.0):
        return {"ok": False, "error": "constraints need hips_rest_y_cm "
                "(the active rig's rest hips height in cm)"}
    cm_per_m = (float(req.hips_rest_y_cm) / neutral_standing_height_m()) if any_con else 0.0

    try:
        import math as _math

        from ardy.motion_rep.tools import length_to_mask
        from ardy.postprocess import post_process_motion
        from ardy.tools import seed_everything, to_numpy

        model = ensure_model()
        sk = model.skeleton
        fps = model.motion_rep.fps
        steps = int(model.diffusion.num_base_steps)
        patch = model.num_frames_per_token
        hist = default_history_frames(fps, model.gen_horizon_len, patch)
        seed_everything(seed)

        def build_constraints(wps, grs, fts, num_frames):
            """The v4.x constraint construction, per segment. Fractions are
            SEGMENT-local; coordinates stay in the shared rig-local frame
            (valid across segments because later segments generate in the
            first segment's coordinate frame)."""
            lst = []
            wp_used = []
            gr_used = []
            ft_used = []
            if wps:
                from ardy.constraints import Root2DConstraintSet
                by_frame = {}
                for w in wps:
                    try:
                        f = float(w["f"]); x = float(w["x"]); z = float(w["z"])
                        h = float(w["h"]) if w.get("h") is not None else None
                    except (KeyError, TypeError, ValueError):
                        raise ValueError(f"bad waypoint {w!r} (need f, x, z)")
                    fr = max(1, min(num_frames - 1, int(round(f * (num_frames - 1)))))
                    by_frame[fr] = (x / cm_per_m, z / cm_per_m, h)
                pos_frames = sorted(fr for fr, v in by_frame.items() if v[2] is None)
                head_frames = sorted(fr for fr, v in by_frame.items() if v[2] is not None)
                if pos_frames:
                    lst.append(Root2DConstraintSet(
                        sk, frame_indices=torch.tensor(pos_frames),
                        root_2d=torch.tensor(
                            [[by_frame[fr][0], by_frame[fr][1]] for fr in pos_frames],
                            dtype=torch.float32, device=DEVICE)))
                if head_frames:
                    lst.append(Root2DConstraintSet(
                        sk, frame_indices=torch.tensor(head_frames),
                        root_2d=torch.tensor(
                            [[by_frame[fr][0], by_frame[fr][1]] for fr in head_frames],
                            dtype=torch.float32, device=DEVICE),
                        global_root_heading=torch.tensor(
                            [by_frame[fr][2] for fr in head_frames],
                            dtype=torch.float32, device=DEVICE)))
                wp_used = [{"frame": fr, "x_m": round(by_frame[fr][0], 3),
                            "z_m": round(by_frame[fr][1], 3),
                            **({"heading_rad": round(by_frame[fr][2], 3)}
                               if by_frame[fr][2] is not None else {})}
                           for fr in sorted(by_frame)]
            if grs:
                from ardy.constraints import (LeftHandConstraintSet,
                                              RightHandConstraintSet)
                J = len(sk.bone_index)
                root_idx = sk.root_idx
                for g in grs:
                    try:
                        gf = float(g["f"]); hand = str(g["hand"]).upper()
                        hx = float(g["x"]) / cm_per_m
                        hy = float(g["y"]) / cm_per_m
                        hz = float(g["z"]) / cm_per_m
                        px = float(g["hipX"]) / cm_per_m
                        py = float(g["hipY"]) / cm_per_m
                        pz = float(g["hipZ"]) / cm_per_m
                        gh = float(g["h"])
                    except (KeyError, TypeError, ValueError):
                        raise ValueError(f"bad grapple {g!r}")
                    fr = max(1, min(num_frames - 1, int(round(gf * (num_frames - 1)))))
                    cy, sy = _math.cos(gh), _math.sin(gh)
                    local = torch.eye(3, device=DEVICE).repeat(1, J, 1, 1).clone()
                    local[0, root_idx] = torch.tensor(
                        [[cy, 0.0, sy], [0.0, 1.0, 0.0], [-sy, 0.0, cy]],
                        device=DEVICE)
                    root_pos = torch.tensor([[px, py, pz]], device=DEVICE,
                                            dtype=torch.float32)
                    g_rots, g_pos, _ = sk.fk(local, root_pos)
                    hand_name = "LeftHand" if hand == "L" else "RightHand"
                    hidx = sk.bone_index[hand_name]
                    g_pos = g_pos.clone()
                    g_pos[0, hidx] = torch.tensor([hx, hy, hz], device=g_pos.device)
                    cls = (LeftHandConstraintSet if hand == "L"
                           else RightHandConstraintSet)
                    lst.append(cls(sk, frame_indices=torch.tensor([fr]),
                                   global_joints_positions=g_pos,
                                   global_joints_rots=g_rots, root_2d=None))
                    gr_used.append({"frame": fr, "hand": hand,
                                    "hand_m": [round(hx, 3), round(hy, 3), round(hz, 3)],
                                    "hip_m": [round(px, 3), round(py, 3), round(pz, 3)],
                                    "heading_rad": round(gh, 3)})
            if fts:
                from ardy.constraints import (LeftFootConstraintSet,
                                              RightFootConstraintSet)
                J = len(sk.bone_index)
                root_idx = sk.root_idx
                for ft in fts:
                    try:
                        ff = float(ft["f"]); side = str(ft["foot"]).upper()
                        fx = float(ft["x"]) / cm_per_m
                        fy = float(ft["y"]) / cm_per_m
                        fz = float(ft["z"]) / cm_per_m
                        px = float(ft["hipX"]) / cm_per_m
                        py = float(ft["hipY"]) / cm_per_m
                        pz = float(ft["hipZ"]) / cm_per_m
                        fh = float(ft.get("h", 0.0))
                    except (KeyError, TypeError, ValueError):
                        raise ValueError(f"bad foot constraint {ft!r}")
                    fr = max(1, min(num_frames - 1, int(round(ff * (num_frames - 1)))))
                    cy, sy = _math.cos(fh), _math.sin(fh)
                    local = torch.eye(3, device=DEVICE).repeat(1, J, 1, 1).clone()
                    local[0, root_idx] = torch.tensor(
                        [[cy, 0.0, sy], [0.0, 1.0, 0.0], [-sy, 0.0, cy]],
                        device=DEVICE)
                    root_pos = torch.tensor([[px, py, pz]], device=DEVICE,
                                            dtype=torch.float32)
                    g_rots, g_pos, _ = sk.fk(local, root_pos)
                    fname = "LeftFoot" if side == "L" else "RightFoot"
                    fidx = sk.bone_index[fname]
                    g_pos = g_pos.clone()
                    g_pos[0, fidx] = torch.tensor([fx, fy, fz], device=g_pos.device)
                    cls = (LeftFootConstraintSet if side == "L"
                           else RightFootConstraintSet)
                    lst.append(cls(sk, frame_indices=torch.tensor([fr]),
                                   global_joints_positions=g_pos,
                                   global_joints_rots=g_rots, root_2d=None))
                    ft_used.append({"frame": fr, "foot": side,
                                    "foot_m": [round(fx, 3), round(fy, 3), round(fz, 3)],
                                    "hip_m": [round(px, 3), round(py, 3), round(pz, 3)]})
                print(f"[bridge] {len(ft_used)} foot constraint(s) built")
            return (lst or None), wp_used, gr_used, ft_used

        samples = []
        seg_meta = []
        wp_all = []
        gr_all = []
        prev_final = None  # dict: world-frame fk pose of the prior seg's end

        for si, sg in enumerate(segs):
            # v5.2, the "one good take on one part, but not another" case:
            # PER-SEGMENT SEEDS. Generation is deterministic given seed +
            # constraints + seed pose, so keeping act 1-2's seeds and
            # rerolling only act 3's reproduces 1-2 EXACTLY and changes
            # only 3 -- per-act retakes with no extra machinery.
            if sg.get("seed") is not None:
                seed_everything(int(sg["seed"]))
            text = str(sg["prompt"]).strip()
            duration = max(0.5, min(30.0, float(sg.get("duration") or 5.0)))
            num_frames = int(duration * fps)
            # v5.1 REBASE, the "resets then zooms" case: ARDY's frame 0
            # is CANONICAL -- generation starts at the origin by
            # construction (that's why first_heading_angle exists at all),
            # so a frame-0 position seed 3m out simply loses. Fix: every
            # segment after the first generates in its OWN canonical frame
            # -- the seed pose and this segment's constraints are
            # transformed INTO that frame (subtract the prior end position,
            # unrotate the prior end heading), and the generated arrays are
            # rigidly transformed BACK to world before concatenation.
            seg_h = 0.0
            seg_off = np.zeros(3)
            seg_R = np.eye(3)
            if prev_final is not None:
                seg_h = _heading_from_pose(prev_final["pos_np"], sk)
                rp_w = prev_final["pos_np"][sk.root_idx]
                seg_off = np.array([float(rp_w[0]), 0.0, float(rp_w[2])])
                c, sn = _math.cos(seg_h), _math.sin(seg_h)
                seg_R = np.array([[c, 0.0, sn], [0.0, 1.0, 0.0],
                                  [-sn, 0.0, c]])

            # constraints arrive in EDITOR rig-local cm == segment 1's
            # world frame; convert to THIS segment's frame (cm in, cm out)
            def seg_frame_constraints(lst, is_grapple):
                if not lst or prev_final is None:
                    return lst
                out = []
                off_cm = seg_off * cm_per_m
                c, sn = _math.cos(seg_h), _math.sin(seg_h)
                def rot(x, z):
                    dx, dz = x - off_cm[0], z - off_cm[2]
                    return (c * dx - sn * dz, sn * dx + c * dz)
                for w in lst:
                    w2 = dict(w)
                    x, z = rot(float(w["x"]), float(w["z"]))
                    w2["x"], w2["z"] = x, z
                    if w2.get("h") is not None:
                        w2["h"] = float(w2["h"]) - seg_h
                    if is_grapple:
                        hx, hz = rot(float(w["hipX"]), float(w["hipZ"]))
                        w2["hipX"], w2["hipZ"] = hx, hz
                    out.append(w2)
                return out

            constraint_lst, wp_used, gr_used, ft_used = build_constraints(
                seg_frame_constraints(sg.get("root_waypoints"), False),
                seg_frame_constraints(sg.get("grapples"), True),
                seg_frame_constraints(sg.get("feet"), True),
                num_frames)
            first_h = 0.0
            if prev_final is not None:
                # seed = the prior end pose expressed in THIS segment's
                # canonical frame: body configuration carries over, the
                # canonical start stays at the origin, heading 0.
                from ardy.constraints import FullBodyConstraintSet
                pos_b = (prev_final["pos_np"] - seg_off) @ seg_R
                rots_b = np.einsum("ij,njk->nik", seg_R.T,
                                   prev_final["rots_np"])
                fb = FullBodyConstraintSet(
                    sk, frame_indices=torch.tensor([0]),
                    global_joints_positions=torch.tensor(
                        pos_b[None], dtype=torch.float32, device=DEVICE),
                    global_joints_rots=torch.tensor(
                        rots_b[None], dtype=torch.float32, device=DEVICE))
                constraint_lst = (constraint_lst or []) + [fb]
                first_h = 0.0
            print(f"[bridge] seg {si + 1}/{len(segs)}: {text!r} ({num_frames}f, "
                  f"{len(wp_used)} wp, {len(gr_used)} grapple, "
                  f"{len(ft_used)} foot, "
                  f"constraints {'ON' if constraint_lst else 'off'}, "
                  f"heading {first_h:+.2f})")
            lengths = torch.tensor([num_frames], device=DEVICE)
            pad_mask = length_to_mask(lengths)
            first_heading = torch.full((1,), first_h, device=DEVICE)
            observed_motion = None
            motion_mask = None
            if constraint_lst:
                observed_motion, motion_mask = \
                    model.motion_rep.create_conditions_from_constraints_batched(
                        constraint_lst, lengths, to_normalize=True, device=DEVICE)
            with torch.no_grad():
                motion = model(
                    [text], num_frames, num_denoising_steps=steps,
                    pad_mask=pad_mask, first_heading_angle=first_heading,
                    motion_mask=motion_mask, observed_motion=observed_motion,
                    cfg_weight=(2.0, 2.0), crop_history_length=hist)
                output = model.motion_rep.inverse(motion, is_normalized=True)
            corrected = post_process_motion(
                output["local_rot_mats"], output["root_positions"],
                output["foot_contacts"], sk, constraint_lst=constraint_lst)
            output.update(corrected)
            output = to_numpy(output)
            n = int(output["posed_joints"].shape[0])
            sample = {k: (v[0] if hasattr(v, "shape") and len(v.shape) > 0
                          and v.shape[0] == n else v)
                      for k, v in output.items()}
            # v5.1: rigid transform back to WORLD (world = R . p + off).
            # Joint/root position arrays get rotate+translate; velocity-like
            # arrays rotate only; local_rot_mats' ROOT entry (the only
            # world-facing rotation) gets left-multiplied by R.
            if prev_final is not None:
                for k in list(sample.keys()):
                    a = np.asarray(sample[k])
                    if k == "local_rot_mats" and a.ndim == 4:
                        a = a.copy()
                        a[:, sk.root_idx] = np.einsum(
                            "ij,tjk->tik", seg_R, a[:, sk.root_idx])
                        sample[k] = a
                    elif a.ndim == 3 and a.shape[-1] == 3:
                        sample[k] = a @ seg_R.T + seg_off
                    elif a.ndim == 2 and a.shape[-1] == 3:
                        if "vel" in k:
                            sample[k] = a @ seg_R.T
                        else:
                            sample[k] = a @ seg_R.T + seg_off
            samples.append((sample, num_frames))
            seg_meta.append({"prompt": text, "frames": num_frames,
                             "waypoints": len(wp_used), "grapples": len(gr_used),
                             "feet": len(ft_used)})
            wp_all += wp_used
            gr_all += gr_used
            # v5.0.2: seed pose via the skeleton's own FK on the final
            # frame (local rot mats + the corrected root the retarget also
            # trusts) -- positions AND rotations from one consistent pass.
            _lr = torch.tensor(
                np.asarray(sample["local_rot_mats"])[-1:],
                dtype=torch.float32, device=DEVICE)
            _rk = ("smooth_root_pos" if "smooth_root_pos" in sample
                   else "root_positions")
            _rp = torch.tensor(
                np.asarray(sample[_rk])[-1:],
                dtype=torch.float32, device=DEVICE)
            _g_rots, _g_pos, _ = sk.fk(_lr, _rp)
            prev_final = {
                "pos_np": _g_pos[0].detach().cpu().numpy(),
                "rots_np": _g_rots[0].detach().cpu().numpy(),
            }
    except ValueError as e:
        return {"ok": False, "error": str(e)}
    except Exception as e:  # noqa: BLE001
        import traceback
        traceback.print_exc()
        return {"ok": False, "error": f"generation failed: {e}"}

    # concatenate: per-frame arrays along T, everything else from seg 1
    merged = {}
    first_sample, _ = samples[0]
    for k in first_sample:
        temporal = all(
            k in sm and hasattr(sm[k], "shape")
            and len(np.asarray(sm[k]).shape) > 0
            and np.asarray(sm[k]).shape[0] == nf
            for sm, nf in samples)
        if temporal:
            merged[k] = np.concatenate(
                [np.asarray(sm[k]) for sm, _ in samples], axis=0)
        else:
            merged[k] = np.asarray(first_sample[k])
    total_frames = sum(nf for _, nf in samples)
    total_dur = total_frames / fps
    joined = " then ".join(m["prompt"] for m in seg_meta)

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    stem = f"{slugify(joined)}_s{seed}_d{int(round(total_dur))}s"
    npz_path = OUT_DIR / f"{stem}.npz"
    arrays = {k: np.asarray(v) for k, v in merged.items()}
    arrays["fps"] = np.asarray(fps)
    arrays["text"] = np.asarray(joined)
    np.savez(npz_path, **arrays)

    json_path = OUT_DIR / f"{stem}.json"
    try:
        clip = retarget(npz_path, REST_JSON, str(json_path))
    except SystemExit as e:
        return {"ok": False, "error": f"retarget validation failed ({e})"}
    except Exception as e:  # noqa: BLE001
        return {"ok": False, "error": f"retarget error: {e}"}

    if wp_all or gr_all or len(segs) > 1:
        clip.setdefault("meta", {})["hasRootConstraints"] = bool(wp_all or gr_all)
        if wp_all:
            clip["meta"]["rootWaypoints"] = wp_all
        if gr_all:
            clip["meta"]["grapples"] = gr_all
        if len(segs) > 1:
            clip["meta"]["segments"] = seg_meta
        json_path.write_text(json.dumps(clip), encoding="utf-8")

    dt = time.time() - t0
    print(f"[bridge] done in {dt:.1f}s -> {json_path.name} "
          f"({len(segs)} segment(s), {total_frames}f, VRAM {vram_mb()}MB)")
    return {"ok": True, "clip": clip, "seed": seed, "duration": total_dur,
            "elapsed": round(dt, 1), "savedJson": str(json_path),
            "savedNpz": str(npz_path), "waypoints": len(wp_all),
            "grapples": len(gr_all), "segments": len(segs),
            "encoder": "warm" if _model is not None else "cold"}


if __name__ == "__main__":
    print(f"[bridge] On-Set ARDY bridge v4 (root waypoints) on http://127.0.0.1:{PORT}  (device {DEVICE})")
    print(f"[bridge] outputs -> {OUT_DIR}")
    print("[bridge] model loads on first /generate; POST /load to pre-warm; "
          "POST /unload to free VRAM for ComfyUI")
    uvicorn.run(app, host="127.0.0.1", port=PORT)
