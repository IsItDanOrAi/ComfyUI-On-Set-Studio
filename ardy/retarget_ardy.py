# retarget_ardy.py -- ARDY Core-27 motion -> On-Set Studio Mixamo clip  (retarget-v4)
#
# Usage (inside the ARDY venv at C:\dev\ardy):
#   python retarget_ardy.py outputs\output.npz mixamo_rest.json -o walk_circle.json
#
# Inputs:
#   1. an ARDY generate.py .npz (local_rot_mats/smooth_root_pos/posed_joints/fps)
#   2. mixamo_rest.json -- dumped from the editor: reload the editor (fresh
#      T-pose!), open the browser console, run:  copy(ipDumpRestPose())
#      then paste into a file named mixamo_rest.json  (editor-v127+)
#
# Output: a JSON clip (onset-ardy-clip-v1): per-bone quaternion keyframes for
# mixamorig:* bones + Hips positions, ready for the editor's clip ingestion.
#
# Math (the whole trick in three lines):
#   ARDY joint frames are world-aligned at neutral, so G_ardy(j) -- the FK
#   product of its local rotations -- IS the world-space delta from neutral.
#   Apply that delta on top of the Mixamo rest global:
#       G_mix(b) = G_ardy(src(b)) @ G_restM(b)
#       L_mix(b) = G_mix(parent(b))^-1 @ G_mix(b)
#   Hips translation = smooth_root_pos, meters -> cm, height-scaled.
#
# Validation: recomputes ARDY world joint positions by FK from the local
# rotations + neutral skeleton and compares against posed_joints in the npz.
# If that residual is ~0, the rotations were interpreted correctly.

import os

os.environ.setdefault("CUDA_VISIBLE_DEVICES", "0")  # 4090 pin (5060 Ti = sm_120, unsupported by cu126 torch)

import argparse
import json
import sys
from pathlib import Path

import numpy as np

# ---------------------------------------------------------------- constants

CORE27 = [
    ("Hips", None), ("Spine", "Hips"), ("Spine1", "Spine"), ("Spine2", "Spine1"),
    ("Spine3", "Spine2"), ("Neck", "Spine3"), ("Head", "Neck"),
    ("RightShoulder", "Spine3"), ("RightArm", "RightShoulder"),
    ("RightForeArm", "RightArm"), ("RightHand", "RightForeArm"),
    ("RightHandEnd", "RightHand"), ("RightHandThumb1", "RightHand"),
    ("LeftShoulder", "Spine3"), ("LeftArm", "LeftShoulder"),
    ("LeftForeArm", "LeftArm"), ("LeftHand", "LeftForeArm"),
    ("LeftHandEnd", "LeftHand"), ("LeftHandThumb1", "LeftHand"),
    ("RightUpLeg", "Hips"), ("RightLeg", "RightUpLeg"), ("RightFoot", "RightLeg"),
    ("RightToeBase", "RightFoot"),
    ("LeftUpLeg", "Hips"), ("LeftLeg", "LeftUpLeg"), ("LeftFoot", "LeftLeg"),
    ("LeftToeBase", "LeftFoot"),
]
CORE_NAMES = [n for n, _ in CORE27]
CORE_INDEX = {n: i for i, n in enumerate(CORE_NAMES)}
CORE_PARENT = [(-1 if p is None else CORE_INDEX[p]) for _, p in CORE27]

# Mixamo bone -> ARDY source joint. The world delta of the SOURCE drives the
# bone. Spine chain: ARDY has 4 segments, Mixamo 3 -- Mixamo Spine2 takes
# ARDY Spine3's world delta (the deepest merged segment), which keeps every
# child (Neck, both Shoulders, whose ARDY parent IS Spine3) consistent.
# HandEnd/Thumb1 are dropped: hands belong to the editor's hand-pose system.
MIX_FROM_ARDY = {
    "Hips": "Hips", "Spine": "Spine", "Spine1": "Spine1", "Spine2": "Spine3",
    "Neck": "Neck", "Head": "Head",
    "RightShoulder": "RightShoulder", "RightArm": "RightArm",
    "RightForeArm": "RightForeArm", "RightHand": "RightHand",
    "LeftShoulder": "LeftShoulder", "LeftArm": "LeftArm",
    "LeftForeArm": "LeftForeArm", "LeftHand": "LeftHand",
    "RightUpLeg": "RightUpLeg", "RightLeg": "RightLeg",
    "RightFoot": "RightFoot", "RightToeBase": "RightToeBase",
    "LeftUpLeg": "LeftUpLeg", "LeftLeg": "LeftLeg",
    "LeftFoot": "LeftFoot", "LeftToeBase": "LeftToeBase",
}

# ------------------------------------------------------------- small linalg


def quat_to_mat(q):
    x, y, z, w = q
    n = x * x + y * y + z * z + w * w
    if n < 1e-12:
        return np.eye(3)
    x, y, z, w = np.array([x, y, z, w]) / np.sqrt(n)
    return np.array([
        [1 - 2 * (y * y + z * z), 2 * (x * y - z * w), 2 * (x * z + y * w)],
        [2 * (x * y + z * w), 1 - 2 * (x * x + z * z), 2 * (y * z - x * w)],
        [2 * (x * z - y * w), 2 * (y * z + x * w), 1 - 2 * (x * x + y * y)],
    ])


def mat_to_quat(m):
    # returns [x, y, z, w]; robust Shepperd-style branch
    t = np.trace(m)
    if t > 0:
        s = np.sqrt(t + 1.0) * 2
        w = 0.25 * s
        x = (m[2, 1] - m[1, 2]) / s
        y = (m[0, 2] - m[2, 0]) / s
        z = (m[1, 0] - m[0, 1]) / s
    elif m[0, 0] > m[1, 1] and m[0, 0] > m[2, 2]:
        s = np.sqrt(1.0 + m[0, 0] - m[1, 1] - m[2, 2]) * 2
        w = (m[2, 1] - m[1, 2]) / s
        x = 0.25 * s
        y = (m[0, 1] + m[1, 0]) / s
        z = (m[0, 2] + m[2, 0]) / s
    elif m[1, 1] > m[2, 2]:
        s = np.sqrt(1.0 + m[1, 1] - m[0, 0] - m[2, 2]) * 2
        w = (m[0, 2] - m[2, 0]) / s
        x = (m[0, 1] + m[1, 0]) / s
        y = 0.25 * s
        z = (m[1, 2] + m[2, 1]) / s
    else:
        s = np.sqrt(1.0 + m[2, 2] - m[0, 0] - m[1, 1]) * 2
        w = (m[1, 0] - m[0, 1]) / s
        x = (m[0, 2] + m[2, 0]) / s
        y = (m[1, 2] + m[2, 1]) / s
        z = 0.25 * s
    q = np.array([x, y, z, w])
    return q / np.linalg.norm(q)


import re
# EXACTLY the editor's retargetClipTo short(): strips mixamorig / mixamorig0 /
# mixamorig: / mixamorig0: — anything the FBX names its bones. Using the same
# rule guarantees our track names round-trip through the editor's pipeline.
_MIXORIG = re.compile(r"^mixamorig\d*:?")


def short(name):
    return _MIXORIG.sub("", name)


def detect_prefix(full_names):
    """Return the common mixamorig prefix (e.g. 'mixamorig:') so the output
    clip can re-attach it to bone tracks."""
    for n in full_names:
        m = _MIXORIG.match(n)
        if m and m.group(0):
            return m.group(0)
    return ""


# ------------------------------------------------------------ ARDY FK + data


def ardy_neutral_joints():
    """Instantiate ARDY's CoreSkeleton27 for its neutral pose. Falls back to
    None (validation limited, retarget still valid) if assets can't load."""
    try:
        import ardy as ardy_pkg
        from ardy.skeleton.definitions import CoreSkeleton27

        base = Path(ardy_pkg.__file__).parent / "assets" / "skeletons" / "cskel27"
        sk = CoreSkeleton27(base) if base.exists() else CoreSkeleton27()
        nj = sk.neutral_joints
        nj = nj.detach().cpu().numpy() if hasattr(nj, "detach") else np.asarray(nj)
        return nj.reshape(27, 3)
    except Exception as e:  # noqa: BLE001
        print(f"[warn] could not load ARDY neutral skeleton ({e}); "
              "FK validation and T-pose check skipped")
        return None


def ardy_neutral_hips_above_floor(neutral=None) -> float:
    """v4: ARDY neutral hips height above the FLOOR PLANE (meters) -- the
    SINGLE SOURCE OF TRUTH for the pipeline's cm<->m scale basis. The bridge
    (onset_ardy_server.py) imports this too, so the editor->ARDY->editor
    round trip cannot drift onto two bases again.
    FLOOR = the ToeBase joint plane, NOT the Foot joint: the v137 probe
    measured the Mixamo rig's Foot joint (the ANKLE) at y=8.73cm with
    ToeBase at exactly y=0 -- the toe joint IS the floor-contact level on
    both skeletons. Measuring hips-above-Foot mixes an above-FLOOR numerator
    (mixamo 104.3cm) with an above-ANKLE denominator and inflates the scale
    by the ankle height (~9%) -- the residual "walking on air" hover.
    Returns 0.0 when the skeleton assets are unavailable (caller falls back)."""
    if neutral is None:
        neutral = ardy_neutral_joints()
    if neutral is None:
        return 0.0
    floor = min(neutral[CORE_INDEX["LeftToeBase"]][1],
                neutral[CORE_INDEX["RightToeBase"]][1])
    return float(neutral[CORE_INDEX["Hips"]][1] - floor)


def ardy_fk(local_rot, root_pos, neutral):
    """FK in ARDY convention (SMPL-style: world-aligned joint frames at
    neutral, offsets are pure translations).
    local_rot (T,27,3,3), root_pos (T,3), neutral (27,3) ->
    globals (T,27,3,3), positions (T,27,3)."""
    T = local_rot.shape[0]
    G = np.zeros((T, 27, 3, 3))
    P = np.zeros((T, 27, 3))
    G[:, 0] = local_rot[:, 0]
    P[:, 0] = root_pos
    for j in range(1, 27):
        p = CORE_PARENT[j]
        G[:, j] = G[:, p] @ local_rot[:, j]
        off = neutral[j] - neutral[p]
        P[:, j] = P[:, p] + np.einsum("tij,j->ti", G[:, p], off)
    return G, P


# --------------------------------------------------------------------- main


def retarget(npz_path, rest_path, output_path=None, raw_root=False,
             no_recenter=False):
    """The whole pipeline as a callable (the bridge server imports this).
    Returns the clip dict; writes it to output_path when given."""

    class _A:  # mirror the CLI namespace
        npz, rest, output = str(npz_path), str(rest_path), output_path
        raw_root_f, no_recenter_f = raw_root, no_recenter

    args = _A()
    args.raw_root = _A.raw_root_f
    args.no_recenter = _A.no_recenter_f

    d = np.load(args.npz)
    local_rot = np.asarray(d["local_rot_mats"], dtype=np.float64)   # (T,27,3,3)
    root_key = "root_positions" if args.raw_root else "smooth_root_pos"
    root_pos = np.asarray(d[root_key], dtype=np.float64)            # (T,3) meters
    fps = int(d["fps"])
    text = str(d["text"]) if "text" in d.files else "ardy clip"
    T = local_rot.shape[0]
    print(f"[npz] {T} frames @ {fps}fps  |  prompt: {text!r}  |  root: {root_key}")

    rest = json.loads(Path(args.rest).read_text(encoding="utf-8"))
    assert rest.get("format") == "onset-mixamo-rest-v1", "not an ipDumpRestPose dump"
    rbones = rest["bones"]
    by_short = {short(n): n for n in rbones}
    prefix = detect_prefix(list(rbones.keys()))
    print(f"[rest] {len(rbones)} bones, prefix {prefix!r}")
    missing = [m for m in MIX_FROM_ARDY if m not in by_short]
    if missing:
        sys.exit(f"[fatal] rest dump is missing bones: {missing}")

    # armature sanity: hips world quat vs bone-chain product tells us whether
    # a rotated/scaled armature node sits between world and the bone chain
    hw = rest.get("hipsWorld") or {}
    ws = hw.get("scale", [1, 1, 1])
    if max(abs(s - 1.0) for s in ws) > 0.01:
        print(f"[warn] armature scale {ws} != 1 -- root translation may need a scale fix")

    # Mixamo global rest rotations by walking the dumped parent chain
    G_rest, chain_rot = {}, {}

    def rest_global(full):
        if full in G_rest:
            return G_rest[full]
        b = rbones[full]
        R = quat_to_mat(b["quat"])
        p = b["parent"]
        G = R if p is None else rest_global(p) @ R
        G_rest[full] = G
        return G

    for full in rbones:
        rest_global(full)

    # armature rotation A: world(hips) = A @ chainGlobal(hips)
    hips_full = by_short["Hips"]
    A = np.eye(3)
    if hw.get("quat"):
        A = quat_to_mat(hw["quat"]) @ rest_global(hips_full).T
        dev = np.linalg.norm(A - np.eye(3))
        if dev > 0.01:
            print(f"[note] armature rotation detected (|A-I|={dev:.3f}); compensating")
        else:
            A = np.eye(3)

    # ARDY neutral: T-pose check + FK validation reference
    neutral = ardy_neutral_joints()
    if neutral is not None:
        arm = neutral[CORE_INDEX["RightHand"]] - neutral[CORE_INDEX["RightArm"]]
        horiz = abs(arm[0]) / (np.linalg.norm(arm) + 1e-9)
        verdict = "T-pose (good: matches Mixamo rest, no extra offset needed)" if horiz > 0.9 \
            else f"NOT a clean T-pose (arm dir {arm.round(3)}) -- expect arm offset; report what you see"
        print(f"[neutral] ARDY rest arm check: {verdict}")

        G_ardy, P = ardy_fk(local_rot, np.asarray(d["root_positions"], np.float64), neutral)
        if "posed_joints" in d.files:
            err = np.abs(P - np.asarray(d["posed_joints"], np.float64)).max()
            print(f"[validate] FK vs posed_joints max error: {err:.5f} m "
                  f"({'PASS' if err < 0.02 else 'FAIL -- rotation convention mismatch, stop and report'})")
            if err >= 0.02:
                sys.exit(1)
    else:
        # FK still needed for G_ardy; neutral offsets only affect positions,
        # not global rotations, so zeros suffice for the rotation product
        G_ardy, _ = ardy_fk(local_rot, root_pos * 0, np.zeros((27, 3)))

    # height scale (v4 VERDICT -- the hover's TRUE root cause, nailed by the
    # v137 probe, 2026-07-16): the spans were anatomically MISMATCHED.
    # Numerator: mixamo hips-above-FLOOR (hipsWorld 104.3cm; probe shows the
    # rig's ToeBase at exactly y=0 and its Foot joint -- the ANKLE -- at
    # y=8.73cm). Denominator (v1-v3): ARDY hips-above-FOOT-JOINT -- also an
    # ankle. Floor-span over ankle-span inflates cm/m by the ankle height:
    # 104.3/0.896 = 116.4 vs the true 104.3/0.976 = ~106.9 (+8.9%) -- the
    # measured ~9cm float exactly (clip frame-0 root 0.963m near-standing x
    # the inflation = 112.1cm played vs 104.3cm rest). v3's neutral basis
    # fixed per-clip variance (+3.7%) but kept the ankle-span error; v4
    # fixes the span: FLOOR = ToeBase plane on BOTH skeletons, via
    # ardy_neutral_hips_above_floor() -- which the bridge imports too, so
    # waypoint cm->m and clip m->cm can never sit on different bases again.
    # Fallback chain: neutral-floor -> per-clip posed mean (same toe basis,
    # printed as a diagnostic either way) -> 0.98m (floor-span human).
    hips_rest_pos = np.array(rbones[hips_full]["pos"], dtype=np.float64)
    mix_hips_y = (hw.get("pos") or [0, hips_rest_pos[1], 0])[1]  # cm
    ardy_neutral_h = ardy_neutral_hips_above_floor(neutral)
    ardy_posed_h = 0.0
    if "posed_joints" in d.files:
        pj = np.asarray(d["posed_joints"], np.float64)  # (T,27,3) meters
        hips_h = pj[:, 0, 1]
        floor_h = np.minimum(pj[:, CORE_INDEX["RightToeBase"], 1],
                             pj[:, CORE_INDEX["LeftToeBase"], 1])
        ardy_posed_h = float(np.mean(hips_h - floor_h))  # hips above floor, m
    if ardy_neutral_h > 1e-3:
        ardy_hips_y = ardy_neutral_h
        basis = "neutral-floor"
    elif ardy_posed_h > 1e-6:
        ardy_hips_y = ardy_posed_h
        basis = "posed-floor-fallback"
    else:
        ardy_hips_y = 0.98  # sane human fallback, FLOOR span (m)
        basis = "0.98-fallback"
    scale = mix_hips_y / ardy_hips_y  # cm per meter
    if ardy_neutral_h > 1e-3 and ardy_posed_h > 1e-6:
        drift = (ardy_neutral_h / ardy_posed_h - 1.0) * 100.0
        print(f"[scale] diagnostic: posed mean {ardy_posed_h:.3f}m vs neutral "
              f"{ardy_neutral_h:.3f}m ({drift:+.1f}%, floor basis)")
    print(f"[scale] mixamo hips {mix_hips_y:.1f}cm / ardy standing {ardy_hips_y:.3f}m "
          f"({basis}) -> {scale:.2f} cm/m")

    # ------------------------------------------------ retarget every frame
    tracks = {}
    order = [m for m in MIX_FROM_ARDY]  # dict order: parents before children
    G_mix = {m: np.zeros((T, 3, 3)) for m in order}
    mix_parent_of = {m: (short(rbones[by_short[m]]["parent"]) if rbones[by_short[m]]["parent"] else None)
                     for m in order}
    for m in order:
        a = CORE_INDEX[MIX_FROM_ARDY[m]]
        Gr = rest_global(by_short[m])
        # world delta (through armature frame) on top of the rest global
        G_mix[m] = (A.T @ G_ardy[:, a] @ A) @ Gr
    for m in order:
        p = mix_parent_of[m]
        Lm = G_mix[m] if (p is None or p not in G_mix) else \
            np.transpose(G_mix[p], (0, 2, 1)) @ G_mix[m]
        quats = np.stack([mat_to_quat(Lm[t]) for t in range(T)])
        # enforce quaternion continuity (no sign flips between frames)
        for t in range(1, T):
            if np.dot(quats[t], quats[t - 1]) < 0:
                quats[t] = -quats[t]
        # key by SHORT name (m); the editor prepends boneNamePrefix once.
        tracks[m] = {"quat": quats.round(6).tolist()}

    # Hips positions: meters -> height-scaled cm, through armature, recentered
    hips_pos = root_pos * scale
    if A is not None:
        hips_pos = hips_pos @ A  # A.T applied row-wise == pos @ A
    if not args.no_recenter:
        hips_pos[:, 0] -= hips_pos[0, 0] - hips_rest_pos[0]
        hips_pos[:, 2] -= hips_pos[0, 2] - hips_rest_pos[2]
    tracks["Hips"]["pos"] = hips_pos.round(4).tolist()

    out = {
        "format": "onset-ardy-clip-v1",
        "name": text,
        "fps": fps,
        "frameCount": T,
        "duration": T / fps,
        "boneNamePrefix": prefix,  # e.g. "mixamorig:" — re-attached to track names editor-side
        "tracks": tracks,
        "meta": {"source": Path(args.npz).name, "rootKey": root_key,
                 "cmPerMeter": round(scale, 4), "scaleBasis": basis,
                 # v2: the hips rest height (cm) these positions are scaled
                 # for -- the editor rescales the track per-rig from this, so
                 # smaller/larger model swaps keep feet on the floor.
                 "hipsRestYcm": round(float(hips_rest_pos[1]), 3),
                 "dropped": ["RightHandEnd", "RightHandThumb1",
                             "LeftHandEnd", "LeftHandThumb1", "Spine3(merged)"]},
    }
    out_path = Path(args.output or (Path(args.npz).stem + "_mixamo_clip.json"))
    out_path.write_text(json.dumps(out), encoding="utf-8")
    print(f"[done] wrote {out_path}  ({len(tracks)} bone tracks, {T} frames)")
    return out


def main():
    ap = argparse.ArgumentParser(description="ARDY .npz -> On-Set Mixamo JSON clip")
    ap.add_argument("npz", help="ARDY output .npz")
    ap.add_argument("rest", help="mixamo_rest.json (from ipDumpRestPose in the editor)")
    ap.add_argument("-o", "--output", default=None, help="output clip path (.json)")
    ap.add_argument("--raw-root", action="store_true",
                    help="use root_positions instead of smooth_root_pos")
    ap.add_argument("--no-recenter", action="store_true",
                    help="keep ARDY's absolute XZ start instead of starting at the rest hips XZ")
    a = ap.parse_args()
    retarget(a.npz, a.rest, a.output, a.raw_root, a.no_recenter)


if __name__ == "__main__":
    main()
