# On-Set Studio -- ComfyUI node pack + routes.  (nodes-v10)
#
# On-Set Studio is a virtual-stage tool: it produces control images, structured
# JSON, and persistent GROUND PLANS for AI image/video pipelines. The output
# handler is model-agnostic (Ideogram/Krea/LTX/etc.).
#
# NAMING CONTRACT -- three things must agree or the app 404s its own assets:
#     1. the vite build flag   vite build --base=/on-set-studio/app/
#     2. the routes below      /on-set-studio/...
#     3. the button URL        web/onsetstudio.js -> window.open("/on-set-studio/app/")
# The editor is COMPILED against that base, so changing one without the others
# silently breaks asset loading at runtime, not at build time. If the namespace
# ever changes again, grep the whole tree (source AND the ComfyUI node) first --
# a missed copy is the failure mode, and it is not obvious from the console.
#
# ARCHITECTURE (dual-track, unchanged):
#   - Vite editor is the dev env (C:\dev\on-set-studio).
#   - `vite build --base=/on-set-studio/app/` -> copy dist/ -> ./editor_dist
#     == "pushing an update".
#   - This file serves ./editor_dist at /on-set-studio/app/ and takes the
#     editor payload at /on-set-studio/submit ("Send to ComfyUI").
#
# GROUND PLANS (new, node-pack-v2):
#   A Ground Plan is a named, versioned, self-contained FOLDER -- the film
#   term for a top-down stage layout. The browser cannot touch disk, so the
#   EDITOR ships the scene doc + asset bytes to these routes, and PYTHON does
#   the filesystem work.
#
#     <output>/on_set_studio/groundplans/<slug>/
#         meta.json           { id, name, created, modified, schemaVersion }
#         groundplan.json      the scene document (editor owns its schema)
#         assets/<assetId>.<ext>   ONE copy per asset id (in-plan dedup)
#         versions/<ts>.json       timestamped copies of groundplan.json ONLY
#                                   (tiny -- version control without asset bloat)
#         thumbnail.png        optional, for the SCENES list
#
#   The node is DUMB STORAGE: it never parses the scene doc. The editor owns
#   schemaVersion + migration. On save the editor sends an asset manifest
#   [{id,ext}]; the node reports which ids it does NOT already have, and the
#   editor uploads only those -- so a 40MB FBX is sent once per plan, not
#   every save, and each id is stored exactly once.

import base64
import io
import json
import math
import os
import re
import shutil
import time

import numpy as np
import torch
from PIL import Image

_DIR = os.path.dirname(os.path.abspath(__file__))
_PAYLOAD_DIR = os.path.join(_DIR, "payloads")
os.makedirs(_PAYLOAD_DIR, exist_ok=True)
_EDITOR_DIST = os.path.join(_DIR, "editor_dist")

# Ground Plans live in ComfyUI's OUTPUT dir when available (survives node
# updates -- custom_nodes/ can be wiped on reinstall), else beside this file.
try:
    import folder_paths

    _BASE = folder_paths.get_output_directory()
except Exception:
    _BASE = _DIR
_GROUNDPLAN_DIR = os.path.join(_BASE, "on_set_studio", "groundplans")
os.makedirs(_GROUNDPLAN_DIR, exist_ok=True)

# v8: baked PLATE frames. Filed under the same on_set_studio/ folder as the
# ground plans rather than its own top-level directory -- everything this pack
# writes lives in one place, which is the same grouping rule as the node
# names. One constant to change if you want it elsewhere.
#
# Emphatically NOT inside editor_dist/: the deploy loop whole-folder-deletes
# that, and an hour of baking would go with it.
_PLATE_DIR = os.path.join(_BASE, "on_set_studio", "plate_cache")
os.makedirs(_PLATE_DIR, exist_ok=True)


# ---- ground-plan filesystem helpers ----
def _slug(name):
    """Human-browsable, filesystem-safe folder name."""
    s = re.sub(r"[^A-Za-z0-9 _-]", "", str(name or "")).strip()
    s = re.sub(r"\s+", "_", s)
    return s[:80] or "untitled"


def _plan_dir(name):
    return os.path.join(_GROUNDPLAN_DIR, _slug(name))


def _safe_id(s):
    """Asset ids / extensions are used in filenames -- keep them clean."""
    return re.sub(r"[^A-Za-z0-9._-]", "", str(s or ""))


def _inside(base, full):
    base = os.path.normpath(base)
    full = os.path.normpath(full)
    return full == base or full.startswith(base + os.sep)


def _read_json(path, default=None):
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return default


def _write_json(path, data):
    tmp = path + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)
    os.replace(tmp, path)  # atomic


def _now():
    return time.strftime("%Y-%m-%dT%H:%M:%S")


def _asset_path(pdir, asset_id, ext):
    ext = _safe_id(ext).lstrip(".")
    return os.path.join(pdir, "assets", f"{_safe_id(asset_id)}.{ext}")


# v10 SECURITY. Every other client-supplied string on these routes already
# goes through _slug or _safe_id; the pass KEY in submit_frame did not, and
# it lands straight in a filename. Same treatment, plus a length cap.
def _safe_key(s):
    return re.sub(r"[^A-Za-z0-9_-]", "", str(s or ""))[:40]


# v10: base64 payloads arrived with no ceiling. A single POST could fill the
# disk or take the process out on memory. These are generous for real work
# (a 4K PNG pass is a few MB, a big FBX tens) and still bounded.
_MAX_IMAGE_B64 = 64 * 1024 * 1024
_MAX_ASSET_B64 = 512 * 1024 * 1024


def _same_origin(request):
    """
    v10 CSRF. These routes have no authentication because they are local, but
    "local" does not mean "only my app can reach them": any page open in the
    browser can POST to 127.0.0.1. A JSON content-type would normally force a
    CORS preflight and be blocked, but a simple request with text/plain still
    carries a JSON body straight through.

    So state-changing routes check the Origin. Same-origin requests from the
    editor either omit it or send this host, and anything from another site
    carries that site's origin and is refused. No allowlist to maintain and
    nothing to configure.
    """
    origin = request.headers.get("Origin")
    if not origin:
        return True  # same-origin fetches and non-browser callers
    host = request.headers.get("Host") or ""
    return origin.split("//", 1)[-1] == host


def _find_asset(pdir, asset_id):
    """Return the stored file for an id regardless of ext, or None."""
    adir = os.path.join(pdir, "assets")
    sid = _safe_id(asset_id)
    if not os.path.isdir(adir):
        return None
    for fn in os.listdir(adir):
        if os.path.splitext(fn)[0] == sid:
            return os.path.join(adir, fn)
    return None


# ---- routes ----
try:
    from server import PromptServer
    from aiohttp import web

    _routes = PromptServer.instance.routes

    # ===== existing: editor payload ("Send to ComfyUI") =====
    @_routes.post("/on-set-studio/submit")
    async def _oss_submit(request):
        if not _same_origin(request):
            return web.json_response({"ok": False, "error": "bad origin"}, status=403)
        data = await request.json()
        session = str(data.get("session", "default"))
        session = "".join(c for c in session if c.isalnum() or c in "-_") or "default"
        path = os.path.join(_PAYLOAD_DIR, f"{session}.json")
        tmp = path + ".tmp"
        with open(tmp, "w", encoding="utf-8") as f:
            json.dump(data, f)
        os.replace(tmp, path)  # atomic -- node never reads a half-write
        print(f"[On-Set Studio] payload received -> {path}")
        return web.json_response({"ok": True, "session": session})

    # ===== NEW (v5): SEQUENCE transport -- one frame per POST =====
    # The editor's ExportSequenceToComfy walks the timeline and POSTs each
    # frame separately, so the BROWSER never holds more than one frame in
    # memory (flat cost for any clip length). We mirror that here: each frame
    # lands on disk immediately as PNG rather than accumulating in RAM.
    #
    # Layout:  payloads/<session>/frames/NNNNN_<pass>.png
    #          payloads/<session>/manifest.json      (written on frame 0)
    #
    # Frame 0 WIPES any previous frames for the session. Without that, a
    # re-send of a shorter range would leave the old tail behind and the node
    # would emit a clip longer than what was actually sent.
    @_routes.post("/on-set-studio/submit_frame")
    async def _oss_submit_frame(request):
        if not _same_origin(request):
            return web.json_response({"ok": False, "error": "bad origin"}, status=403)
        data = await request.json()
        session = str(data.get("session", "default"))
        session = "".join(c for c in session if c.isalnum() or c in "-_") or "default"
        try:
            frame = int(data.get("frame", 0))
        except (TypeError, ValueError):
            frame = 0
        sdir = os.path.join(_PAYLOAD_DIR, session)
        fdir = os.path.join(sdir, "frames")

        if frame <= 0 and os.path.isdir(fdir):
            shutil.rmtree(fdir, ignore_errors=True)
        os.makedirs(fdir, exist_ok=True)

        images = data.get("images", {}) or {}
        written = 0
        for key, data_url in images.items():
            if not data_url or "," not in data_url:
                continue
            b64 = data_url.split(",", 1)[1]
            if len(b64) > _MAX_IMAGE_B64:
                print(f"[On-Set Studio] frame pass '{key}' rejected: too large")
                continue
            try:
                raw = base64.b64decode(b64)
            except Exception:
                continue
            # temp + replace so the node never reads a half-written PNG
            # v10 PATH TRAVERSAL, fixed. `key` is the pass name and it comes
            # from the request body. Unsanitised it goes into a filename, and
            # a name carrying enough parent segments walks out of the frames
            # folder and writes wherever the process can. Everything else on
            # these routes was already slugged; this was the one that was not.
            safe_key = _safe_key(key)
            if not safe_key:
                continue
            dst = os.path.join(fdir, f"{frame:05d}_{safe_key}.png")
            if not _inside(fdir, dst):
                continue
            tmp = dst + ".tmp"
            with open(tmp, "wb") as f:
                f.write(raw)
            os.replace(tmp, dst)
            written += 1

        # OpenPose keypoints are per-frame; keep them all on disk. The node's
        # openpose_json socket is a single STRING, so it emits the FIRST
        # frame's -- same shape as a still, so a graph doesn't break when you
        # switch a slot from still to sequence. Per-frame keypoint consumption
        # would need its own node reading this folder.
        if data.get("openpose"):
            with open(
                os.path.join(fdir, f"{frame:05d}_openpose.json"), "w", encoding="utf-8"
            ) as f:
                json.dump(data["openpose"], f)

        # Manifest is written once, on frame 0: it describes the whole clip
        # and the per-frame POSTs carry identical metadata anyway. The node
        # counts actual PNGs rather than trusting `total`, so an interrupted
        # send yields a short clip instead of an error.
        if frame <= 0:
            manifest = {
                "session": session,
                "total": data.get("total"),
                "fps": data.get("fps"),
                "slots": data.get("slots"),
                "characters": data.get("characters") or {},
                "environment": data.get("environment") or [],
                "scene": data.get("scene") or {},
                # v6 (step 4): shot mechanics, kept SEPARATE from the
                # character/environment docs on purpose -- those drive prompt
                # formatting and fps/size fields in among them steer the model
                # off course. The Scene Data node reads this one.
                "technical": data.get("technical") or {},
            }
            mpath = os.path.join(sdir, "manifest.json")
            tmp = mpath + ".tmp"
            with open(tmp, "w", encoding="utf-8") as f:
                json.dump(manifest, f)
            os.replace(tmp, mpath)
            print(f"[On-Set Studio] sequence started -> {fdir}")

        return web.json_response(
            {"ok": True, "session": session, "frame": frame, "written": written}
        )

    # ===== existing: serve the built editor =====
    @_routes.get("/on-set-studio/app/{tail:.*}")
    async def _oss_app(request):
        tail = request.match_info.get("tail") or "index.html"
        full = os.path.normpath(os.path.join(_EDITOR_DIST, tail))
        if not _inside(_EDITOR_DIST, full):
            return web.Response(status=403)
        if os.path.isdir(full):
            full = os.path.join(full, "index.html")
        if not os.path.isfile(full):
            return web.Response(
                status=404,
                text="editor_dist not found -- run `vite build "
                "--base=/on-set-studio/app/` and copy dist/ here "
                "as editor_dist/ (see README).",
            )
        return web.FileResponse(full)

    # ===== NEW: Ground Plan lifecycle =====
    # All under /on-set-studio/groundplan/* (same invisible namespace).

    @_routes.get("/on-set-studio/groundplan/list")
    async def _oss_gp_list(request):
        plans = []
        if os.path.isdir(_GROUNDPLAN_DIR):
            for slug in sorted(os.listdir(_GROUNDPLAN_DIR)):
                pdir = os.path.join(_GROUNDPLAN_DIR, slug)
                if not os.path.isdir(pdir):
                    continue
                meta = _read_json(os.path.join(pdir, "meta.json"), {}) or {}
                vdir = os.path.join(pdir, "versions")
                vcount = (
                    len([f for f in os.listdir(vdir) if f.endswith(".json")])
                    if os.path.isdir(vdir)
                    else 0
                )
                plans.append(
                    {
                        "slug": slug,
                        "name": meta.get("name", slug),
                        "id": meta.get("id"),
                        "created": meta.get("created"),
                        "modified": meta.get("modified"),
                        "schemaVersion": meta.get("schemaVersion"),
                        "versions": vcount,
                        "hasThumbnail": os.path.isfile(
                            os.path.join(pdir, "thumbnail.png")
                        ),
                    }
                )
        return web.json_response({"ok": True, "plans": plans})

    @_routes.post("/on-set-studio/groundplan/save")
    async def _oss_gp_save(request):
        """Write groundplan.json (+meta, +version snapshot). Report which
        asset ids still need uploading. Body:
          { name, id?, schemaVersion?, doc, assets:[{id,ext}], thumbnail? }
        """
        if not _same_origin(request):
            return web.json_response({"ok": False, "error": "bad origin"}, status=403)
        data = await request.json()
        name = data.get("name")
        if not name:
            return web.json_response({"ok": False, "error": "name required"}, status=400)
        pdir = _plan_dir(name)
        if not _inside(_GROUNDPLAN_DIR, pdir):
            return web.json_response({"ok": False, "error": "bad name"}, status=400)
        os.makedirs(os.path.join(pdir, "assets"), exist_ok=True)
        os.makedirs(os.path.join(pdir, "versions"), exist_ok=True)

        gp_path = os.path.join(pdir, "groundplan.json")
        # snapshot the OLD doc before overwrite (version control, json only)
        if os.path.isfile(gp_path):
            ts = time.strftime("%Y%m%d_%H%M%S")
            try:
                shutil.copy2(gp_path, os.path.join(pdir, "versions", f"{ts}.json"))
            except Exception as e:
                print("[On-Set Studio] version snapshot failed:", e)

        _write_json(gp_path, data.get("doc", {}))

        # meta (preserve created; refresh modified)
        meta_path = os.path.join(pdir, "meta.json")
        meta = _read_json(meta_path, {}) or {}
        meta["name"] = name
        meta["id"] = data.get("id", meta.get("id"))
        meta["schemaVersion"] = data.get("schemaVersion", meta.get("schemaVersion"))
        meta.setdefault("created", _now())
        meta["modified"] = _now()
        _write_json(meta_path, meta)

        # optional thumbnail (dataURL)
        thumb = data.get("thumbnail")
        if thumb and "," in thumb:
            try:
                raw = base64.b64decode(thumb.split(",", 1)[1])
                with open(os.path.join(pdir, "thumbnail.png"), "wb") as f:
                    f.write(raw)
            except Exception as e:
                print("[On-Set Studio] thumbnail write failed:", e)

        # which declared assets are NOT yet stored -> editor uploads only these
        need = []
        for a in data.get("assets", []) or []:
            aid = a.get("id")
            if aid and _find_asset(pdir, aid) is None:
                need.append(aid)

        print(f"[On-Set Studio] saved Ground Plan '{name}' ({_slug(name)})")
        return web.json_response(
            {"ok": True, "slug": _slug(name), "needAssets": need}
        )

    @_routes.post("/on-set-studio/groundplan/asset")
    async def _oss_gp_asset(request):
        """Store ONE asset by id (dedup: skip if already present). Body:
          { name, id, ext, data:"data:...;base64,..." | base64 }
        """
        if not _same_origin(request):
            return web.json_response({"ok": False, "error": "bad origin"}, status=403)
        data = await request.json()
        pdir = _plan_dir(data.get("name"))
        if not _inside(_GROUNDPLAN_DIR, pdir) or not os.path.isdir(pdir):
            return web.json_response({"ok": False, "error": "no such plan"}, status=404)
        aid = data.get("id")
        if not aid:
            return web.json_response({"ok": False, "error": "id required"}, status=400)
        if _find_asset(pdir, aid) is not None:
            return web.json_response({"ok": True, "skipped": True})  # dedup
        blob = data.get("data", "")
        if "," in blob:
            blob = blob.split(",", 1)[1]
        if len(blob) > _MAX_ASSET_B64:
            return web.json_response(
                {"ok": False, "error": "asset too large"}, status=413
            )
        try:
            raw = base64.b64decode(blob)
        except Exception:
            return web.json_response({"ok": False, "error": "bad data"}, status=400)
        os.makedirs(os.path.join(pdir, "assets"), exist_ok=True)
        path = _asset_path(pdir, aid, data.get("ext", "bin"))
        if not _inside(pdir, path):
            return web.json_response({"ok": False, "error": "bad ext"}, status=400)
        with open(path, "wb") as f:
            f.write(raw)
        print(f"[On-Set Studio] stored asset {aid} ({len(raw)} bytes)")
        return web.json_response({"ok": True, "bytes": len(raw)})

    @_routes.get("/on-set-studio/groundplan/load")
    async def _oss_gp_load(request):
        """Return the scene doc + an asset index (ids -> fetch urls). Query:
          ?name=X [&version=<ts>.json]
        """
        name = request.query.get("name")
        pdir = _plan_dir(name)
        if not _inside(_GROUNDPLAN_DIR, pdir) or not os.path.isdir(pdir):
            return web.json_response({"ok": False, "error": "no such plan"}, status=404)
        version = request.query.get("version")
        if version:
            vpath = os.path.join(pdir, "versions", _safe_id(version))
            if not _inside(pdir, vpath) or not os.path.isfile(vpath):
                return web.json_response({"ok": False, "error": "no such version"}, status=404)
            doc = _read_json(vpath, {})
        else:
            doc = _read_json(os.path.join(pdir, "groundplan.json"), {})
        meta = _read_json(os.path.join(pdir, "meta.json"), {}) or {}
        assets = []
        adir = os.path.join(pdir, "assets")
        if os.path.isdir(adir):
            for fn in sorted(os.listdir(adir)):
                aid, ext = os.path.splitext(fn)
                assets.append(
                    {
                        "id": aid,
                        "ext": ext.lstrip("."),
                        "url": f"/on-set-studio/groundplan/file?name={_slug(name)}&id={aid}",
                    }
                )
        return web.json_response(
            {"ok": True, "meta": meta, "doc": doc, "assets": assets}
        )

    @_routes.get("/on-set-studio/groundplan/file")
    async def _oss_gp_file(request):
        """Serve one asset's bytes so the editor can rebuild the mesh."""
        pdir = _plan_dir(request.query.get("name"))
        if not _inside(_GROUNDPLAN_DIR, pdir):
            return web.Response(status=403)
        path = _find_asset(pdir, request.query.get("id"))
        if not path or not os.path.isfile(path) or not _inside(pdir, path):
            return web.Response(status=404)
        # v10: these bytes were uploaded by whoever used the app, and they are
        # served back from ComfyUI's OWN origin. Left to sniff, an asset saved
        # with an .html or .svg extension would execute as a page here, with
        # full access to every ComfyUI API on this host. The editor only ever
        # fetches these as ArrayBuffers, so declaring them opaque bytes costs
        # nothing and closes that path.
        return web.FileResponse(
            path,
            headers={
                "Content-Type": "application/octet-stream",
                "X-Content-Type-Options": "nosniff",
                "Content-Disposition": "attachment",
            },
        )

    # ===== v8: PLATE CACHE =====
    # The editor browses baked plates through these. Listing reads only the
    # manifests, never the frames, so a cache with 20,000 PNGs in it still
    # lists instantly.
    @_routes.get("/on-set-studio/plates/list")
    async def _oss_plates_list(request):
        plates = []
        if os.path.isdir(_PLATE_DIR):
            for slug in sorted(os.listdir(_PLATE_DIR)):
                pdir = os.path.join(_PLATE_DIR, slug)
                if not os.path.isdir(pdir):
                    continue
                m = _read_json(os.path.join(pdir, "manifest.json"), None)
                if not m:
                    continue
                size = 0
                try:
                    for fn in os.listdir(pdir):
                        size += os.path.getsize(os.path.join(pdir, fn))
                except OSError:
                    pass
                m["slug"] = slug
                m["bytes"] = size
                plates.append(m)
        return web.json_response(
            {
                "ok": True,
                "plates": plates,
                "bytes": sum(p.get("bytes", 0) for p in plates),
                "dir": _PLATE_DIR,
            }
        )

    @_routes.get("/on-set-studio/plates/frame")
    async def _oss_plates_frame(request):
        """One baked frame. ?name=<slug>&i=<1-based index>."""
        pdir = os.path.join(_PLATE_DIR, _slug(request.query.get("name")))
        if not _inside(_PLATE_DIR, pdir) or not os.path.isdir(pdir):
            return web.Response(status=404)
        try:
            i = max(1, int(request.query.get("i", "1")))
        except ValueError:
            i = 1
        path = os.path.join(pdir, "frame_%05d.png" % i)
        if not os.path.isfile(path):
            return web.Response(status=404)
        return web.FileResponse(path)

    @_routes.post("/on-set-studio/plates/delete")
    async def _oss_plates_delete(request):
        """Cleanup lives in On-Set, so it needs a way to actually delete."""
        if not _same_origin(request):
            return web.json_response({"ok": False, "error": "bad origin"}, status=403)
        data = await request.json()
        pdir = os.path.join(_PLATE_DIR, _slug(data.get("name")))
        if not _inside(_PLATE_DIR, pdir) or pdir == _PLATE_DIR:
            return web.json_response({"ok": False, "error": "bad name"}, status=400)
        if not os.path.isdir(pdir):
            return web.json_response({"ok": False, "error": "no such plate"}, status=404)
        shutil.rmtree(pdir, ignore_errors=True)
        return web.json_response({"ok": True})

    @_routes.get("/on-set-studio/groundplan/versions")
    async def _oss_gp_versions(request):
        pdir = _plan_dir(request.query.get("name"))
        if not _inside(_GROUNDPLAN_DIR, pdir) or not os.path.isdir(pdir):
            return web.json_response({"ok": False, "error": "no such plan"}, status=404)
        vdir = os.path.join(pdir, "versions")
        out = []
        if os.path.isdir(vdir):
            for fn in sorted(os.listdir(vdir), reverse=True):
                if fn.endswith(".json"):
                    out.append(
                        {"version": fn, "modified": os.path.getmtime(os.path.join(vdir, fn))}
                    )
        return web.json_response({"ok": True, "versions": out})

    @_routes.post("/on-set-studio/groundplan/delete")
    async def _oss_gp_delete(request):
        if not _same_origin(request):
            return web.json_response({"ok": False, "error": "bad origin"}, status=403)
        data = await request.json()
        pdir = _plan_dir(data.get("name"))
        if not _inside(_GROUNDPLAN_DIR, pdir) or pdir == _GROUNDPLAN_DIR:
            return web.json_response({"ok": False, "error": "bad name"}, status=400)
        if os.path.isdir(pdir):
            shutil.rmtree(pdir, ignore_errors=True)
        return web.json_response({"ok": True})

    @_routes.post("/on-set-studio/groundplan/rename")
    async def _oss_gp_rename(request):
        if not _same_origin(request):
            return web.json_response({"ok": False, "error": "bad origin"}, status=403)
        data = await request.json()
        src = _plan_dir(data.get("name"))
        dst = _plan_dir(data.get("newName"))
        if not (_inside(_GROUNDPLAN_DIR, src) and _inside(_GROUNDPLAN_DIR, dst)):
            return web.json_response({"ok": False, "error": "bad name"}, status=400)
        if not os.path.isdir(src):
            return web.json_response({"ok": False, "error": "no such plan"}, status=404)
        if os.path.exists(dst):
            return web.json_response({"ok": False, "error": "target exists"}, status=409)
        os.rename(src, dst)
        meta_path = os.path.join(dst, "meta.json")
        meta = _read_json(meta_path, {}) or {}
        meta["name"] = data.get("newName")
        meta["modified"] = _now()
        _write_json(meta_path, meta)
        return web.json_response({"ok": True, "slug": _slug(data.get("newName"))})

    @_routes.post("/on-set-studio/groundplan/duplicate")
    async def _oss_gp_duplicate(request):
        if not _same_origin(request):
            return web.json_response({"ok": False, "error": "bad origin"}, status=403)
        data = await request.json()
        src = _plan_dir(data.get("name"))
        dst = _plan_dir(data.get("newName"))
        if not (_inside(_GROUNDPLAN_DIR, src) and _inside(_GROUNDPLAN_DIR, dst)):
            return web.json_response({"ok": False, "error": "bad name"}, status=400)
        if not os.path.isdir(src):
            return web.json_response({"ok": False, "error": "no such plan"}, status=404)
        if os.path.exists(dst):
            return web.json_response({"ok": False, "error": "target exists"}, status=409)
        shutil.copytree(src, dst)
        meta_path = os.path.join(dst, "meta.json")
        meta = _read_json(meta_path, {}) or {}
        meta["name"] = data.get("newName")
        meta["created"] = _now()
        meta["modified"] = _now()
        _write_json(meta_path, meta)
        return web.json_response({"ok": True, "slug": _slug(data.get("newName"))})

    print(
        "[On-Set Studio] routes up: /on-set-studio/app/ + /submit + "
        "/groundplan/* + /plates/*"
    )
except Exception as e:  # headless import (tests) or very old ComfyUI
    print("[On-Set Studio] route registration skipped:", e)


# ---- helpers ----
_BLANK = torch.zeros(1, 64, 64, 3)


def _data_url_to_image_tensor(data_url):
    """dataURL PNG -> ComfyUI IMAGE tensor [1,H,W,3] float 0..1."""
    if not data_url or "," not in data_url:
        return None
    b64 = data_url.split(",", 1)[1]
    img = Image.open(io.BytesIO(base64.b64decode(b64))).convert("RGB")
    arr = np.asarray(img).astype(np.float32) / 255.0
    return torch.from_numpy(arr)[None, ...]


# v3: the legacy fixed routing -- also the fallback when a payload predates
# the editor's configurable output slots (editor-v126+ sends data["slots"]).
_LEGACY_SLOTS = ["depth", "normal", "canny", "pose"]


# ---- v5: sequence helpers -------------------------------------------------
# A ComfyUI IMAGE is [B,H,W,3]; the still path already produces [1,H,W,3].
# A clip is therefore the SAME socket with a deeper batch -- which is why the
# frozen socket contract survives video: nothing about the node's shape
# changes, only the depth of the tensor. Video nodes (VHS VideoCombine,
# WanVideo, ...) consume exactly this.


def _seq_paths(session):
    """(session dir, frames dir, manifest path) for a sequence session."""
    sdir = os.path.join(_PAYLOAD_DIR, session)
    return sdir, os.path.join(sdir, "frames"), os.path.join(sdir, "manifest.json")


def _seq_frame_indices(fdir):
    """Sorted frame numbers actually present on disk (any pass)."""
    if not os.path.isdir(fdir):
        return []
    seen = set()
    for name in os.listdir(fdir):
        if not name.endswith(".png"):
            continue
        head = name.split("_", 1)[0]
        if head.isdigit():
            seen.add(int(head))
    return sorted(seen)


def _png_to_tensor(path):
    """PNG on disk -> [H,W,3] float 0..1 (no batch dim -- caller stacks)."""
    img = Image.open(path).convert("RGB")
    arr = np.asarray(img).astype(np.float32) / 255.0
    return torch.from_numpy(arr)


def _frames_to_batch(fdir, key, indices):
    """Stack one pass across frames -> [N,H,W,3], or None if that pass was
    never rendered (slot set to a still, or not selected at all)."""
    out = []
    for i in indices:
        p = os.path.join(fdir, f"{i:05d}_{key}.png")
        if os.path.isfile(p):
            out.append(_png_to_tensor(p))
    if not out:
        return None
    # Guard against a mid-run resolution change: mismatched frames can't be
    # stacked, and a torch error here would be cryptic. Truncate instead.
    h, w, _ = out[0].shape
    clean = [t for t in out if t.shape[0] == h and t.shape[1] == w]
    if len(clean) != len(out):
        print(
            f"[On-Set Studio] '{key}': dropped {len(out) - len(clean)} frame(s) "
            "with a different resolution -- re-send the sequence without "
            "changing output size mid-run."
        )
    return torch.stack(clean, dim=0) if clean else None


class OnSetStudioNode:
    """Flagship node: emit the latest editor payload for a session into the
    graph. v3 -- CONFIGURABLE OUTPUT SLOTS: the editor's Settings tab picks
    which map rides each of out_1..out_4 (scene depth, character-only depth,
    normal, canny, pose/color, splat mask, ...). Socket COUNT, ORDER, and
    TYPES are frozen so saved graphs never break (Comfy links by index);
    only the cargo is routed. slot_labels (appended last) reports the
    routing as JSON for workflow-side sanity checks."""

    @classmethod
    def INPUT_TYPES(cls):
        return {"required": {"session": ("STRING", {"default": "default"})}}

    # v4: openpose_json APPENDED as a trailing output. Comfy links by
    # index, so appending never disturbs an existing link -- the four image
    # sockets and the first four strings keep their positions. The OpenPose
    # IMAGE itself still rides a normal out_1..out_4 slot like any other map;
    # this extra output carries only the keypoint JSON for nodes that consume
    # OpenPose keypoints directly.
    RETURN_TYPES = (
        "IMAGE", "IMAGE", "IMAGE", "IMAGE",
        "STRING", "STRING", "STRING", "STRING", "STRING",
    )
    RETURN_NAMES = (
        "out_1", "out_2", "out_3", "out_4",
        "character_json", "environment_json", "scene_json", "slot_labels",
        "openpose_json",
    )
    FUNCTION = "run"
    CATEGORY = "On-Set Studio"

    @classmethod
    def IS_CHANGED(cls, session):
        # v5: two transports now feed this node -- a still payload
        # (<session>.json) and a sequence (<session>/manifest.json). Report
        # BOTH mtimes so re-running after either kind of send re-executes.
        stamps = []
        still = os.path.join(_PAYLOAD_DIR, f"{session}.json")
        _, _, manifest = _seq_paths(session)
        for p in (still, manifest):
            try:
                stamps.append(str(os.path.getmtime(p)))
            except OSError:
                stamps.append("-")
        if stamps == ["-", "-"]:
            return str(time.time())
        return "|".join(stamps)

    def run(self, session):
        # v5: WHICHEVER TRANSPORT IS NEWER WINS. Send a still -> get a still;
        # send a sequence -> get a clip. "Most recent send" is the least
        # surprising rule: it matches what the user last pressed, and it needs
        # no mode widget on the node to stay in sync with the editor.
        still_path = os.path.join(_PAYLOAD_DIR, f"{session}.json")
        _, fdir, manifest_path = _seq_paths(session)
        still_t = (
            os.path.getmtime(still_path) if os.path.isfile(still_path) else -1.0
        )
        seq_t = (
            os.path.getmtime(manifest_path)
            if os.path.isfile(manifest_path)
            else -1.0
        )

        if still_t < 0 and seq_t < 0:
            raise RuntimeError(
                f"On-Set Studio: no payload for session '{session}'. Open "
                "/on-set-studio/app/ in a browser tab, build the scene, and "
                "press 'Send to ComfyUI'. Whether you get a still or a "
                "clip is decided by the Frame/Video toggles on the output "
                "slots in the editor's Settings tab."
            )
        if seq_t > still_t:
            return self._run_sequence(session, fdir, manifest_path)

        with open(still_path, "r", encoding="utf-8") as f:
            data = json.load(f)

        images = data.get("images", {}) or {}
        # v3: slot routing from the editor; legacy payloads fall back to the
        # classic depth/normal/canny/pose so old sends keep working.
        slots = data.get("slots")
        if not (isinstance(slots, list) and len(slots) == 4):
            slots = list(_LEGACY_SLOTS)
        out_imgs = []
        for key in slots:
            t = _data_url_to_image_tensor(images.get(key))
            out_imgs.append(t if t is not None else _BLANK)

        character_json = json.dumps(data.get("characters", {}), indent=2)
        environment_json = json.dumps(data.get("environment", []), indent=2)
        scene_json = json.dumps(data.get("scene", {}), indent=2)
        slot_labels = json.dumps(
            {f"out_{i + 1}": key for i, key in enumerate(slots)}, indent=2
        )
        # v4: the editor sends OpenPose keypoints as data["openpose"] when the
        # openpose slot was routed. Absent otherwise -> emit an empty object
        # so a downstream node always gets valid JSON rather than "null".
        openpose_json = json.dumps(data.get("openpose") or {}, indent=2)
        return (
            *out_imgs,
            character_json,
            environment_json,
            scene_json,
            slot_labels,
            openpose_json,
        )

    # ----- v5: sequence path ------------------------------------------------
    def _run_sequence(self, session, fdir, manifest_path):
        """Emit a clip. Same sockets, deeper tensors: out_1..out_4 become
        [N,H,W,3] batches that video nodes consume directly."""
        with open(manifest_path, "r", encoding="utf-8") as f:
            manifest = json.load(f)

        indices = _seq_frame_indices(fdir)
        if not indices:
            raise RuntimeError(
                f"On-Set Studio: sequence for session '{session}' has no "
                "frames on disk. Re-send the sequence from the editor."
            )
        declared = manifest.get("total")
        if isinstance(declared, int) and declared > 0 and len(indices) < declared:
            # Not an error: an interrupted send should still be usable. Say so
            # plainly, because a silently-short clip is worse than a warning.
            print(
                f"[On-Set Studio] sequence '{session}': {len(indices)} of "
                f"{declared} frames present -- emitting the short clip."
            )

        slots = manifest.get("slots")
        if not (isinstance(slots, list) and len(slots) == 4):
            slots = list(_LEGACY_SLOTS)

        out_imgs = []
        for key in slots:
            batch = _frames_to_batch(fdir, key, indices) if key else None
            out_imgs.append(batch if batch is not None else _BLANK)

        character_json = json.dumps(manifest.get("characters", {}), indent=2)
        environment_json = json.dumps(manifest.get("environment", []), indent=2)
        scene_json = json.dumps(manifest.get("scene", {}), indent=2)
        slot_labels = json.dumps(
            {f"out_{i + 1}": key for i, key in enumerate(slots)}, indent=2
        )
        # First frame's keypoints -- keeps the socket the same shape as a
        # still so switching a slot to sequence never breaks a wired graph.
        first_kp = os.path.join(fdir, f"{indices[0]:05d}_openpose.json")
        openpose_json = "{}"
        if os.path.isfile(first_kp):
            with open(first_kp, "r", encoding="utf-8") as f:
                openpose_json = json.dumps(json.load(f), indent=2)

        print(
            f"[On-Set Studio] emitting sequence '{session}': "
            f"{len(indices)} frames, slots={slots}"
        )
        return (
            *out_imgs,
            character_json,
            environment_json,
            scene_json,
            slot_labels,
            openpose_json,
        )


class OnSetStudioSceneData:
    """Shot mechanics as typed sockets -- fps, frame count, duration, the
    in/out range, output size, aspect.

    Deliberately a SEPARATE node rather than more outputs on the flagship
    (Dan's call, 2026-07-28). The flagship carries pictures and prose; this
    carries numbers, and most graphs want one or the other.

    There is NO key widget. The editor's technical document has a strict,
    known shape, so every field gets its own socket: self-documenting in the
    node browser, and nothing to mistype into a silent empty string.

    fps is FLOAT and must stay FLOAT. 23.976 and 29.97 are real broadcast
    rates; an INT socket rounds them to 24 and 30, which is a quarter-frame
    of drift per second and a visibly wrong clip length over a minute.

    The values describe THE DELIVERED CLIP, not the whole timeline, so
    frame_count wires straight into an EmptyLatentVideo. A still-only send
    is honestly a one-frame clip (count 1, in == out == the playhead).
    """

    @classmethod
    def INPUT_TYPES(cls):
        return {"required": {"session": ("STRING", {"default": "default"})}}

    RETURN_TYPES = (
        "FLOAT", "INT", "FLOAT",
        "INT", "INT", "INT",
        "INT", "INT", "STRING",
        "STRING",
    )
    RETURN_NAMES = (
        "fps", "frame_count", "duration",
        "in_frame", "out_frame", "still_frame",
        "width", "height", "aspect",
        "technical_json",
    )
    FUNCTION = "run"
    CATEGORY = "On-Set Studio"

    @classmethod
    def IS_CHANGED(cls, session):
        # Same dual-transport rule as the flagship node: report BOTH mtimes
        # so re-running after either kind of send re-executes.
        stamps = []
        still = os.path.join(_PAYLOAD_DIR, f"{session}.json")
        _, _, manifest = _seq_paths(session)
        for p in (still, manifest):
            try:
                stamps.append(str(os.path.getmtime(p)))
            except OSError:
                stamps.append("-")
        if stamps == ["-", "-"]:
            return str(time.time())
        return "|".join(stamps)

    def run(self, session):
        # Newest transport wins, exactly as the flagship resolves it -- the
        # two nodes must never disagree about which send they are describing.
        still_path = os.path.join(_PAYLOAD_DIR, f"{session}.json")
        _, _, manifest_path = _seq_paths(session)
        still_t = (
            os.path.getmtime(still_path) if os.path.isfile(still_path) else -1.0
        )
        seq_t = (
            os.path.getmtime(manifest_path)
            if os.path.isfile(manifest_path)
            else -1.0
        )
        if still_t < 0 and seq_t < 0:
            raise RuntimeError(
                f"On-Set Studio: no payload for session '{session}'. Open "
                "/on-set-studio/app/ in a browser tab, build the scene, and "
                "press 'Send to ComfyUI'."
            )

        is_sequence = seq_t > still_t
        src = manifest_path if is_sequence else still_path
        with open(src, "r", encoding="utf-8") as f:
            doc = json.load(f)

        tech = doc.get("technical") or {}

        # GRACEFUL on a payload sent by an editor older than v222: fall back
        # to fields that already existed rather than raising. A graph that
        # half-works and says why beats one that dies on an old payload.
        if not tech:
            print(
                "[On-Set Studio] Scene Data: this payload has no technical "
                "document -- it was sent by an editor older than v222. "
                "Falling back to the manifest; re-send to get exact values."
            )
        scene = doc.get("scene") or {}
        out = scene.get("output") or {}

        def _num(key, fallback, cast):
            v = tech.get(key, None)
            if v is None:
                v = fallback
            try:
                return cast(v)
            except (TypeError, ValueError):
                return cast(0)

        fps = _num("fps", doc.get("fps") or 0.0, float)
        frame_count = _num("frame_count", doc.get("total") or 1, int)
        width = _num("width", out.get("width") or 0, int)
        height = _num("height", out.get("height") or 0, int)
        duration = _num(
            "duration", (frame_count / fps) if fps > 0 else 0.0, float
        )
        in_frame = _num("in_frame", 0, int)
        out_frame = _num("out_frame", max(0, frame_count - 1), int)
        still_frame = _num("still_frame", in_frame, int)

        # v7: THE DISK IS THE TRUTH. technical.frame_count is written on frame
        # 0 and describes what the editor INTENDED to send; a send that was
        # stopped (editor v223 added a stop button), or that died with the
        # browser tab, leaves fewer PNGs than that. The flagship node already
        # counts actual files and emits the short clip -- if this node kept
        # reporting the declared count, the two would disagree and a
        # frame_count wired into an EmptyLatentVideo would size the latent for
        # frames that do not exist. Correct the count and everything derived
        # from it, and say so.
        if is_sequence:
            _, fdir, _ = _seq_paths(session)
            actual = len(_seq_frame_indices(fdir))
            if actual and actual != frame_count:
                print(
                    f"[On-Set Studio] scene data '{session}': {actual} frames "
                    f"on disk vs {frame_count} declared -- reporting the "
                    "actual count (interrupted or stopped send)."
                )
                frame_count = actual
                out_frame = in_frame + actual - 1
                duration = round(actual / fps, 6) if fps > 0 else 0.0

        aspect = tech.get("aspect")
        if not aspect:
            if width > 0 and height > 0:
                g = math.gcd(width, height) or 1
                aspect = f"{width // g}:{height // g}"
            else:
                aspect = ""

        print(
            f"[On-Set Studio] scene data '{session}': {frame_count} frames @ "
            f"{fps}fps ({duration}s), {width}x{height} {aspect}, "
            f"in {in_frame} out {out_frame}"
        )
        return (
            fps,
            frame_count,
            duration,
            in_frame,
            out_frame,
            still_frame,
            width,
            height,
            aspect,
            json.dumps(tech, indent=2),
        )


# ============================================================================
# PLATE CACHE  (v8)
# ============================================================================
# Bakes a video into numbered PNG frames that On-Set Studio scrubs as a PLATE
# (a photographic backing on a card in the scene).
#
# WHY BAKE. A <video> element seeks ASYNCHRONOUSLY; the editor's capture path
# is synchronous. Left as video, a captured frame would show whatever the
# decoder happened to have ready, and two captures of the same timeline
# position would not match -- which destroys the reproducibility that is the
# entire point of a staging tool. It is also faster, and it removes the judder
# you get when a clip's fps and the timeline's fps are not a clean ratio.
#
# TRANSPARENCY IS NOT BAKED IN, on purpose. Frames are written as they come
# and On-Set keys them at DRAW time (chroma or luma), so the key can be
# retuned after seeing a generation without re-baking a minute of footage.
# Feed it green screen and pick the colour in the editor.

_PLATE_IMAGE_EXTS = (".png", ".jpg", ".jpeg", ".webp", ".bmp")


# v9 (Dan: "if the actual size doesn't follow the original sizing we are just
# squishing the image"). Right. Setting both width and height to an aspect the
# source doesn't have has to mean SOMETHING, and stretching is the one answer
# that is always wrong -- a distorted plate is a distorted backing, and the
# card in the scene already takes its shape from the manifest, so nothing
# downstream corrects it.
#
# For a plate, CROP is nearly always what you want: it is reframing, which is
# a thing a director does on purpose. Pad exists for when the whole frame must
# survive, and stretch stays available because occasionally you really do want
# to squeeze an anamorphic plate back.
_PLATE_FITS = ["fill (crop)", "fit (pad)", "stretch"]
_PLATE_ANCHORS = ["center", "top", "bottom", "left", "right"]
_ANCHOR_XY = {
    "center": (0.5, 0.5),
    "top": (0.5, 0.0),
    "bottom": (0.5, 1.0),
    "left": (0.0, 0.5),
    "right": (1.0, 0.5),
}


def _plate_resize(img, w, h, fit="fill (crop)", anchor="center"):
    """0 on both axes keeps the source; 0 on ONE follows the aspect (and can
    never distort, which is why it is the recommended way to resize)."""
    sw, sh = img.size
    if w <= 0 and h <= 0:
        return img
    if w <= 0:
        w = max(1, int(round(sw * (h / float(sh)))))
        fit = "stretch"  # aspect already preserved; nothing to crop or pad
    elif h <= 0:
        h = max(1, int(round(sh * (w / float(sw)))))
        fit = "stretch"
    if (w, h) == (sw, sh):
        return img

    if fit == "stretch":
        return img.resize((w, h), Image.LANCZOS)

    ax, ay = _ANCHOR_XY.get(anchor, (0.5, 0.5))
    if fit == "fit (pad)":
        k = min(w / float(sw), h / float(sh))
        nw, nh = max(1, int(round(sw * k))), max(1, int(round(sh * k)))
        scaled = img.resize((nw, nh), Image.LANCZOS)
        canvas = Image.new(
            "RGBA" if scaled.mode == "RGBA" else "RGB", (w, h), (0, 0, 0, 0)
        )
        canvas.paste(scaled, (int(round((w - nw) * ax)), int(round((h - nh) * ay))))
        return canvas

    # fill (crop): cover the target, then take the anchored window
    k = max(w / float(sw), h / float(sh))
    nw, nh = max(w, int(round(sw * k))), max(h, int(round(sh * k)))
    scaled = img.resize((nw, nh), Image.LANCZOS)
    x = int(round((nw - w) * ax))
    y = int(round((nh - h) * ay))
    return scaled.crop((x, y, x + w, y + h))


def _plate_decode(path, every):
    """Decode a video with whatever this ComfyUI happens to have.

    Neither OpenCV nor imageio is guaranteed present in a given install, so a
    failure has to name every route tried rather than blaming whichever was
    last -- otherwise the user goes hunting for the wrong dependency.
    """
    errors = []

    def _cv2():
        import cv2

        cap = cv2.VideoCapture(path)
        if not cap.isOpened():
            raise RuntimeError("OpenCV could not open the file")
        fps = cap.get(cv2.CAP_PROP_FPS) or 0.0
        i = 0
        try:
            while True:
                ok, frame = cap.read()
                if not ok:
                    break
                if i % every == 0:
                    yield fps, Image.fromarray(frame[:, :, ::-1])  # BGR -> RGB
                i += 1
        finally:
            cap.release()

    def _iio():
        import imageio.v3 as iio

        fps = 0.0
        try:
            fps = float(iio.immeta(path, plugin="pyav").get("fps", 0.0) or 0.0)
        except Exception:
            pass
        for i, frame in enumerate(iio.imiter(path, plugin="pyav")):
            if i % every == 0:
                yield fps, Image.fromarray(frame)

    for fn in (_cv2, _iio):
        try:
            got = False
            for fps, img in fn():
                got = True
                yield fps, img
            if got:
                return
            errors.append("%s: produced no frames" % fn.__name__)
        except Exception as e:
            errors.append("%s: %s" % (fn.__name__, e))
    raise RuntimeError(
        "Could not decode the video. Tried: "
        + "; ".join(errors)
        + ". Install `opencv-python` or `imageio[pyav]` into ComfyUI's python, "
        "or feed frames in through the images input instead."
    )


class OnSetStudioPlateCache:
    """Bake a video, an IMAGE batch, or a folder of stills into a plate cache."""

    CATEGORY = "On-Set Studio"
    FUNCTION = "bake"
    RETURN_TYPES = ("STRING", "INT", "FLOAT")
    RETURN_NAMES = ("plate_name", "frame_count", "fps")
    OUTPUT_NODE = True

    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                # INTs so another node can drive them
                "width": ("INT", {"default": 0, "min": 0, "max": 8192, "step": 8}),
                "height": ("INT", {"default": 0, "min": 0, "max": 8192, "step": 8}),
                "name": ("STRING", {"default": ""}),
                # v9: what to do when the requested size is a different SHAPE
                # from the source. Only consulted when both width and height
                # are set -- leave one at 0 and the aspect is kept for you.
                "fit": (_PLATE_FITS, {"default": "fill (crop)"}),
                "anchor": (_PLATE_ANCHORS, {"default": "center"}),
                "every_nth_frame": ("INT", {"default": 1, "min": 1, "max": 60}),
                "overwrite": ("BOOLEAN", {"default": False}),
            },
            "optional": {
                "images": ("IMAGE",),
                "video_path": ("STRING", {"default": ""}),
            },
        }

    def bake(
        self,
        width,
        height,
        name,
        fit,
        anchor,
        every_nth_frame,
        overwrite,
        images=None,
        video_path="",
    ):
        video_path = (video_path or "").strip().strip('"')
        if not name:
            name = (
                os.path.splitext(os.path.basename(video_path))[0]
                if video_path
                else time.strftime("plate_%Y%m%d_%H%M%S")
            )
        slug = _slug(name)
        out_dir = os.path.join(_PLATE_DIR, slug)
        manifest_path = os.path.join(out_dir, "manifest.json")

        # Re-running a graph must not re-bake. Returning the existing manifest
        # keeps the node usable as a permanent part of a workflow.
        if os.path.isdir(out_dir) and not overwrite:
            m = _read_json(manifest_path, None)
            if m:
                print(
                    "[On-Set Studio] plate '%s' already baked (%d frames) -- "
                    "tick overwrite to redo" % (slug, m.get("frame_count", 0))
                )
                return (slug, int(m.get("frame_count", 0)), float(m.get("fps", 0)))
        if os.path.isdir(out_dir):
            shutil.rmtree(out_dir, ignore_errors=True)
        os.makedirs(out_dir, exist_ok=True)

        fps = 0.0
        count = 0

        def write(img, idx):
            if img.mode == "P":
                img = img.convert("RGBA")
            img = _plate_resize(img, width, height, fit, anchor)
            if img.mode not in ("RGB", "RGBA"):
                img = img.convert("RGB")
            img.save(
                os.path.join(out_dir, "frame_%05d.png" % idx), compress_level=3
            )

        if images is not None and len(images) > 0:
            source = "images input"
            for i in range(0, len(images), every_nth_frame):
                arr = (images[i].cpu().numpy() * 255.0).clip(0, 255).astype(np.uint8)
                count += 1
                write(Image.fromarray(arr), count)
        elif video_path:
            source = video_path
            if os.path.isdir(video_path):
                files = sorted(
                    f
                    for f in os.listdir(video_path)
                    if f.lower().endswith(_PLATE_IMAGE_EXTS)
                )
                for i in range(0, len(files), every_nth_frame):
                    count += 1
                    write(Image.open(os.path.join(video_path, files[i])), count)
            elif os.path.isfile(video_path):
                for f, img in _plate_decode(video_path, every_nth_frame):
                    fps = fps or float(f or 0.0)
                    count += 1
                    write(img, count)
            else:
                raise RuntimeError("No such file or folder: %s" % video_path)
        else:
            raise RuntimeError(
                "Nothing to bake: connect an IMAGE input or set video_path."
            )

        if count == 0:
            raise RuntimeError("Baked 0 frames -- check the source.")

        # The stored fps is the rate the BAKED SEQUENCE runs at, which is what
        # the editor needs -- skipping frames divides it.
        if fps and every_nth_frame > 1:
            fps = fps / every_nth_frame

        first = Image.open(os.path.join(out_dir, "frame_00001.png"))
        if width > 0 and height > 0 and fit == "stretch":
            print(
                "[On-Set Studio] plate '%s': fit=stretch -- if the source was "
                "not %dx%d shaped, the frames are distorted. Leave width OR "
                "height at 0 to keep the aspect." % (slug, width, height)
            )
        _write_json(
            manifest_path,
            {
                "version": "onset-plate-cache-v1",
                "name": name,
                "slug": slug,
                "source": source,
                "frame_count": count,
                "fps": round(fps, 6),
                "width": first.width,
                "height": first.height,
                "aspect": round(first.width / float(max(1, first.height)), 6),
                "every_nth_frame": every_nth_frame,
                "fit": fit if (width > 0 and height > 0) else "aspect kept",
                "anchor": anchor,
                "created": _now(),
            },
        )
        print(
            "[On-Set Studio] plate '%s': %d frames at %dx%d%s"
            % (
                slug,
                count,
                first.width,
                first.height,
                (", %.3f fps" % fps) if fps else ", fps unknown (set it in On-Set)",
            )
        )
        return (slug, count, float(fps))


# Forward-facing nodes. The class keys are internal; the display names are
# what users see in the Add-Node menu. Keep "OnSetStudioNode" in sync with the
# match in web/onsetstudio.js -- the "Open On-Set UI" button attaches by class
# name, and a mismatch means it silently never appears.
NODE_CLASS_MAPPINGS = {
    "OnSetStudioNode": OnSetStudioNode,
    "OnSetStudioSceneData": OnSetStudioSceneData,
    "OnSetStudioPlateCache": OnSetStudioPlateCache,
}
NODE_DISPLAY_NAME_MAPPINGS = {
    "OnSetStudioNode": "On-Set Studio",
    "OnSetStudioSceneData": "On-Set Studio -- Scene Data",
    # v8: every display name starts "On-Set Studio" so one search in the
    # Add-Node menu turns up the whole pack.
    "OnSetStudioPlateCache": "On-Set Studio -- Plate Cache",
}

print("[On-Set Studio] nodes-v10 loaded (3 nodes)")
