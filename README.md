<img width="2560" height="800" alt="On-Set Studio Banner" src="https://github.com/user-attachments/assets/3fb0e5d7-ecb5-456a-af3f-fbf14c97de82" />

# On-Set Studio

### Don't let AI imagine your shot. Build it.

**A virtual soundstage for AI image, video, and asset creation, built for ComfyUI.**

On-Set Studio is a browser-based 3D staging tool that runs as a ComfyUI custom
node. You build the shot the way you'd build it on a set: block your cast, rig
your lights, choose a lens, move the camera. Then it hands ComfyUI the ground
truth of the scene you actually built.

<div align="center">
<img width="850" height="275" alt="Banner1-850x275" src="https://github.com/user-attachments/assets/10581776-75b3-42a1-b89c-e7b23b31c701" />
</div>

---

## Why it exists

Generative AI gets called slop, and often that's fair, because "a dog" typed
into a box gives you *someone's* dog, not yours. No direction. No control. No
authorship.

Garbage in, garbage out. Most workflows start from the weakest possible input,
a sentence, and then fight the results downstream. On-Set Studio attacks the
other end: **improve the output by improving the input.**

This is the **A** in an A-to-B pipeline. Previsualization, image-to-image,
image-to-video, video-to-video: whatever comes next in your workflow, this is
where the shot gets decided instead of discovered. Your blocking. Your
lighting. Your lens. Your camera move.

I built it because I needed it. You can adapt to someone else's limits, or you
can build a stage that doesn't have them. I built the stage.

>>> IMAGE: side-by-side, the staged scene in the editor to the generated result <<<

## Why not just use Blender or Unreal?

You can. They're extraordinarily powerful, they'll do everything here and far
more, and if you already live in one of them, use it.

But power isn't the same as fit. Using a full 3D suite to stage a single
ComfyUI shot is like running a language model to spell-check a sentence. It
works, it works beautifully, and it's a great deal more machine than the job
asked for. There's also a gap neither one closes: getting a staged scene *out*
of a production suite and *into* a ComfyUI workflow is a pipeline you build
yourself, every time.

On-Set Studio aims at a narrower target. Enough staging control to author a
real shot, purpose-built to feed ComfyUI directly, without a semester of
learning curve in front of it.

## A toolbox, not a checklist

This is a director's playground, not one fixed workflow. Not every tool fits
every shot, and that's the point. Take the pose pass for one job, depth and a
character matte for another, the BBOX data when your model uses it, the raw
render when that's all you need.

You're not meant to use all of it every time. You're meant to reach for
whatever gets *your* image where it needs to go.

---

## What you can do

>>> IMAGE per section, or one feature reel up top <<<

**Stage and block**
Pose Mixamo-rigged characters with full FK/IK, limb pinning, saved poses, and
hand posing. Stage multiple characters in one scene, each independently
controlled.

**Animate**
A full timeline with pose keyframes and interpolation, multi-clip sequencing
with gap tweening, and path tracking along spline curves. Conventional,
dependable animation tools. Keyframe it yourself, or generate it (see below).

**Light it for real**
Rig-mounted light modules, classic portrait lighting presets, physical bounce
reflectors with real incident-light behavior, and beam-shaping modifiers. Light
that behaves like light, not a prompt asking for "cinematic lighting."

**Work the camera**
A track-based camera rig. Lay a track, drop trackpoints along it, and the
camera travels between them with real lens, roll, and spin control.

Each trackpoint decides what the camera does on the way in:

- **Aim** at a subject, a specific body part, the path ahead, an object in the
  set, or a hand-set angle of your own. Change the aim between trackpoints and
  the camera *pans* between them instead of cutting, so head to hand reads as a
  move rather than a jump.
- **Ease the move**, so a dolly starts and settles like a grip pushed it rather
  than snapping to full speed.
- **Ramp the lens**, for a push-in or a zoom that arrives instead of popping.

Each of those is optional and set per trackpoint, with a curve and a duration
in seconds. Nothing is eased unless you ask for it.

A trackpoint can also be a **keyframe**: same time, same controls, but it holds
position instead of travelling. Stack a few and you have a locked-off camera
that pans, rolls, and changes lens on a timeline without moving an inch.

Multiple cameras per shot, mounted anywhere, including on each other, with a
view finder that switches between them. A head-tracking and eyeline system
keeps your subject's gaze where you want it.

**Build the set**
Import your own FBX / OBJ / GLB objects, or create primitive 3D shapes in the
tool. Every object carries its own path system and its own BBOX data, and can
be attached to a character's bones, so a prop travels with the hand that holds
it. The same system handles a coffee cup in an actor's grip and a car tearing
along a track through the frame. Add Gaussian-splat scenes or the LED-volume /
360° backdrop system for environments.

**Match a plate**
Drop in a photograph or a plate and solve the camera to it, so your staged
scene sits in a real location at a real depth, with the lens and camera height
that location implies.

**Shoot against green (or blue, or black, or white)**
Built-in backdrop modes for clean keying and compositing downstream, in the
color that suits your pipeline.

**Send it to ComfyUI**
One button pushes the whole payload, every pass and every JSON structure,
straight into your ComfyUI workflow.

---

## Generate original motion, ARDY integration

<div align="center">
<img width="850" height="275" alt="ARDY v5" src="https://github.com/user-attachments/assets/7d86bfb2-2281-47e7-9be9-deb5bfe68239" />
</div>


On-Set Studio integrates **[ARDY](https://github.com/nv-tlabs/ardy)**, NVIDIA's
autoregressive motion diffusion model, published at
[SIGGRAPH 2026](https://research.nvidia.com/labs/sil/projects/ardy/), directly
into the editor. Describe a movement in text and get original animation
generated and retargeted onto your character's rig. No motion library, no
mocap, no hunting for a clip that almost works.

It's the piece most people haven't seen yet, in or out of the ComfyUI world:

- **Text to motion**, describe it, generate it, apply it to your character
- **Retargeted automatically** onto the Mixamo skeleton, with FK validation
- **Sequence and tween** generated clips together, and blend them with your own
  keyframed animation
- **Driven by your scene**, since ARDY supports kinematic constraints (paths,
  waypoints, keyframes) and On-Set Studio wires *your* set into them, so a
  generated performance can follow a path you drew and engage with objects you
  placed, instead of playing out in isolation

**Entirely optional.** ARDY runs as a separate local service and wants real
hardware, roughly 14 GB of VRAM with the model loaded (it frees on request so
ComfyUI can have the card back). If you'd rather keyframe by hand, every
conventional animation tool above works without it. It's an addition to the
toolbox, not a dependency.

---

## What it outputs

Every pass renders from the same camera and framing, so they align exactly for
masking and compositing. No re-registration, no drift.

**Images**
- The rendered scene
- A dynamic control-map system (depth, normal, and canny) with multiple
  depth-pass types (full scene, character-only, environment-only) so you can
  choose the map that serves the shot instead of forcing one map to do every
  job
- **Character ID mattes**, a flat, unshaded color per character for clean
  regional masking
- **OpenPose skeletons**, see below
- Gaussian-splat masks for true character-vs-backdrop occlusion

**Data**
- **BBOX data**, bounding boxes projected into frame space for the models and
  workflows that use spatial conditioning. They're generated automatically and
  follow the subject as it moves, and you control what gets boxed: the whole
  character, or specific regions you care about. Nothing to draw by hand.
- **Structured JSON**, per-character, environment, scene, and pose data, with
  cinematographic scaffolding (depth planes, motivated light sources, framing)

### About the pose output

This isn't an OpenPose editor. You pose a **Mixamo rig**, a real skeleton with
proper joints, IK, and hand control, and On-Set Studio converts that into a
standard OpenPose control image on export.

You get the control of a production rig and the compatibility of the format
ComfyUI already speaks. No trade.

>>> IMAGE: contact sheet, render / depth / normal / ID matte / pose / green screen <<<

---

## Installation

> On-Set Studio installs as a ComfyUI custom node.

1. Clone this repository into your ComfyUI `custom_nodes` folder. You'll end
   up with `...\ComfyUI\custom_nodes\ComfyUI-On-Set-Studio\`.
2. Restart ComfyUI. The **On-Set Studio** node appears in your node list, with
   an **Open On-Set UI** button that launches the editor in a new browser tab.
3. Add a character (below). The editor opens to an empty stage until you do.

The editor ships prebuilt, so there's nothing to compile and no Node.js
required.

### You'll need a character model

**On-Set Studio does not ship with a character.** Mixamo's models are Adobe's
to distribute, not mine, so you'll download your own. It takes a minute:

1. Go to [mixamo.com](https://www.mixamo.com) and sign in with a free Adobe
   account.
2. Download a rigged character as **FBX**. The default **X Bot** and **Y Bot**
   figures are the recommended starting point.
3. Drop the `.fbx` into the deployed editor's `models` folder:

   ```
   ...\ComfyUI\custom_nodes\ComfyUI-On-Set-Studio\editor_dist\models\Y Bot.fbx
   ```

   ...or skip the folder entirely and import the file directly in the app.

Any Mixamo-rigged FBX will work, including your own custom characters run
through Mixamo's auto-rigger.

### Optional: ARDY motion generation

Text-to-motion runs as a separate local service, so it's entirely opt-in. Skip
this if you're keyframing by hand.

**1. Install ARDY.** Follow NVIDIA's instructions at
[github.com/nv-tlabs/ardy](https://github.com/nv-tlabs/ardy), including the
model checkpoints. *Note: NVIDIA tests ARDY on Ubuntu 22.04. It runs on
Windows, but you're off their tested path, so expect to solve a dependency or
two.* This guide assumes you installed it to `C:\dev\ardy`.

**2. Copy the bridge files** from this repo into your ARDY folder:

```
...\ardy\onset_ardy_server.py     <- On-Set Studio <-> ARDY bridge (FastAPI, port 8765)
...\ardy\retarget_ardy.py         <- retargets ARDY motion onto the Mixamo skeleton
```

**3. Generate your rest-pose reference.** Retargeting needs to know your
character's rest pose, so you dump it from the editor once:

- Load your character and make sure it's at a **fresh T-pose** (reload the
  editor if you've been posing).
- Open the browser console and run: `copy(ipDumpRestPose())`
- Paste the result into a file named `mixamo_rest.json`, saved next to the two
  scripts above (`C:\dev\ardy\mixamo_rest.json`).

**4. Start the bridge** from ARDY's own Python environment:

```bash
cd C:\...\ardy
python onset_ardy_server.py
```

Leave it running. The editor will find it on port 8765, and motion generation
becomes available in the timeline. The bridge frees its VRAM on request, so
ComfyUI can have the GPU back between generations.

## Requirements

- A working [ComfyUI](https://github.com/comfyanonymous/ComfyUI) install
- A reasonably modern GPU, since this is a real-time 3D editor running in a
  browser
- A Mixamo-rigged FBX character (see above)
- *Optional:* additional VRAM if you want to run ARDY motion generation

---

## Status

**Version 1.0.0.** On-Set Studio is in active development and moving fast. It's
a working toolset built by one person (hi), not a finished commercial product.
Expect sharp edges, and expect it to keep growing.

On-Set Studio ships as a prebuilt editor. The source isn't published at this
stage. If you want a feature, hit a wall, or want to work on something
together, get in touch, that's genuinely the fastest route to both.

## Support this project

On-Set Studio is free to use, and developed by one person. Support is what buys
the time to keep building it.

Be the first to back this:

<a href="https://github.com/sponsors/IsItDanOrAi">
  <img alt="Sponsor on GitHub" src="https://img.shields.io/badge/Sponsor-GitHub%20Sponsors-2ea44f?style=for-the-badge" />
</a>


I'm also available for work. If you're hiring in AI filmmaking, virtual
production, or tooling, I'd like to hear from you.

>>> CONTACT LINK <<<

## Credits

Created and maintained by **Dan Oravasaari**.

Built on the foundation of
[**3D Openpose Editor**](https://github.com/ZhUyU1997/open-pose-editor) by
**yzhu (Yu Zhu)**. Sincere thanks to the original project.

Motion generation is powered by [**ARDY**](https://github.com/nv-tlabs/ardy)
from NVIDIA (Zhao, Petrovich, Zhang, Wang, Tang, and Rempe, SIGGRAPH 2026).
ARDY's inference code is Apache-2.0 and its model weights are released under
the NVIDIA Open Model License. Check the model download pages for the terms
that apply to the checkpoints you use. ARDY is not distributed with this
project, you install it yourself.

Mixamo is a service of Adobe Inc. On-Set Studio works with Mixamo-rigged
characters but is not affiliated with, endorsed by, or sponsored by Adobe. No
Adobe assets are distributed with this project.

The full list of bundled third-party components and their licences is in
[NOTICE](NOTICE.md).

## License

On-Set Studio is © 2026 Dan Oravasaari, all rights reserved, and is
distributed as a compiled build. See [LICENSE](LICENSE).

Anything you make with it is yours. The licence restricts the software, not its
output.

Portions derive from 3D Openpose Editor and remain under the MIT licence. See
[LICENSE-open-pose-editor](LICENSE-open-pose-editor).
