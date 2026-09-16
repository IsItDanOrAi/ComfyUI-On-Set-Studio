# Changelog

All notable changes to On-Set Studio are recorded here, newest first.
Nothing is ever removed from this file. A fixed bug moves out of Known Issues
and into the release that fixed it, so the history stays readable.

Each release lists its internal **build string**. That is the same string the
in-app issue report prints, so a report always says exactly which release it
came from.

---

## 1.0.1

**Build: editor-v354 / app-v60**, unchanged from 1.0.0.

No change to the software. This release exists only to correct the listing on
the ComfyUI Registry.

### Fixed

- The icon on the Registry listing was oversized.
- The build string recorded for 1.0.0 in this file said `editor-v353`. The
  build that actually shipped was `editor-v354`. Corrected, because that
  string is how a bug report maps to a release.

---

## 1.0.0

**Build: editor-v354 / app-v60**

First public release.

### What it is

A virtual soundstage that runs as a ComfyUI custom node. You build the shot
the way you would build it on a set, then hand ComfyUI the ground truth of the
scene you actually built.

- **Staging.** Mixamo-rigged characters with full FK/IK, limb pinning, saved
  poses and hand posing. Multiple characters, each independently controlled.
- **Sets.** Import FBX, OBJ and GLB, or build primitives in the tool. Every
  object carries its own path system and BBOX data, and can be attached to a
  character's bones. Gaussian splat scenes and an LED volume / 360 backdrop
  system for environments.
- **Camera.** A track-based rig. Lay a track, drop trackpoints, and the camera
  travels between them with real lens, roll and spin control. Per-trackpoint
  aim, easing and lens ramps. Multiple cameras per shot, mountable on each
  other, with a View Finder that switches between them.
- **Lighting.** Rig-mounted modules, portrait presets, physical bounce
  reflectors with real incident-light behaviour, and beam-shaping modifiers.
- **Animation.** A full timeline with pose keyframes, multi-clip sequencing
  with gap tweening, and path tracking along spline curves.
- **Motion generation.** Optional ARDY integration: describe a movement in
  text, get original animation retargeted onto your rig.
- **Plate matching.** Solve the camera to a photograph so a staged scene sits
  in a real location at a real depth.
- **Output.** Rendered scene, depth, normal and canny control maps with
  multiple depth-pass types, character ID mattes, OpenPose skeletons, splat
  occlusion masks, BBOX data and structured JSON. Every pass renders from the
  same camera and framing, so they align exactly.

### Known issues

Listed so they read as understood rather than undiscovered. None of them
blocks normal use.

**Scene scale**

- The far clip plane is fixed at 10,000 units. A set larger than that will
  have parts of it clipped from view. Raising the number alone is not the fix,
  because depth precision follows the near/far ratio; it needs a far plane
  derived from the scene's own size.

**Staging**

- Actor marks sit on the ground plane and cannot be given their own height, so
  a character cannot be directed from one raised surface to another.
- A character standing inside an object can make that object hard to click.
  The character's control handles are drawn in front of everything by design,
  and they win the click.

**Lighting**

- Shadows land on an invisible catcher plane at ground level, which is how
  characters cast onto a floor made of grid lines. With imported terrain that
  plane is at the wrong height. Turn **Ground Shadows** off in Settings when
  your set brings its own floor.

**Interface**

- The inspectors on the right-hand side do not scroll or fit to the window the
  way the left-hand dock does, and can overlap the View Finder.
- **Undo does not cover every action.** It is still being filled in, and with
  the number of interacting systems there are gaps, so pressing undo can undo
  something other than the thing you just did. Camera moves are one known
  case. Save before anything you would not want to redo.

**Getting started**

- Most of the Scene tab is unavailable until a character is imported and
  switched on, and the ground grid and the green screen backdrop are behind
  the same gate. Import an FBX in the Scene tab, then press the `Off` button
  at the top right of that panel so it reads `On`. Objects can still be
  imported from the Environment tab with no character present.

**Rigs**

- Only Mixamo-style bone naming is understood. Rigs using Biped, Unreal
  Mannequin or Rokoko naming need converting first.
- On a clean install with no character file present, the browser console logs
  a 404 for the model it looked for. That is expected: On-Set Studio does not
  redistribute Adobe's rigs, and the probe is how it finds out none is there.

**Rare and not reproduced**

- Saving a scene containing a very large environment file has run out of
  memory once. It has not recurred and no reproduction is known.
- A camera rail tethered to a subject has once failed to take after a long
  sequence of build steps. A clean run of the same steps works.
- On the first play of a path-driven ARDY clip, a single frame of the end
  pose can appear before playback starts. It is intermittent and does not
  appear in any output pass.

### Notes

- The source is not published at this stage. The build ships prebuilt, so
  there is nothing to compile and no Node.js required.
- Anything you make with On-Set Studio is yours. The licence restricts the
  software, not its output.
- Bundled third-party components and their licences are listed in
  [NOTICE.md](NOTICE.md).

---

## How to add to this file

Newest release at the top, under a `## x.y.z` heading with its build string.
Group changes under **Added**, **Changed**, **Fixed** and **Known issues**,
dropping any heading that would be empty.

Write entries for somebody using the tool, not somebody reading the code. What
changed for them, and what they can now do that they could not before. Include
the workaround where one exists.

When a known issue is fixed, move it out of Known Issues and into that
release's **Fixed** list, so the file shows both that it was understood and
that it was dealt with.

If a release changes something a user does rather than just what they see,
check whether ONSET-LLM-GUIDE.md needs the same change. Its derived sections
regenerate from source by version stamp, but its authored sections, the ones
describing how to do a thing and why, only change when somebody writes them.
