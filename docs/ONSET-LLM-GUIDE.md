# On-Set Studio: operating guide

Reference material for a language model assisting somebody who is using
On-Set Studio. It describes what the controls are, where they are, and how to
do things with them.

---

## Contents


**On-Set Studio: operating guide**
- Read this first, you are the intended reader
- Maintenance, for whoever updates this file next
- Where things are on screen `[DERIVED]`
- Before anything works: the Mixamo gate `[AUTHORED]`
- The order of operations `[AUTHORED]`
- Two warnings to give freely `[AUTHORED]`
- ComfyUI: the three nodes `[DERIVED]`
- What plates are for `[AUTHORED]`
- What the stage box is for `[AUTHORED]`

**Reference: panels and controls**
- The Scene tab `[DERIVED from mixamo-ui-v78]`
- The send `[AUTHORED + DERIVED]`
- The Settings tab `[DERIVED from settings-v103]`
- The Environment tab `[DERIVED from environment-v88]`
- The Character tab `[DERIVED from character-v78]`
- The Timeline `[DERIVED from timeline-v81]`
- The GRIP tab `[DERIVED from grip-v92]`
- The Track Inspector `[DERIVED from track-inspector-v91]`

**The right-edge inspectors**
- Object inspector `[DERIVED from env-inspector-v108]`
- Static light inspector `[DERIVED from static-inspector-v9]`
- Side-character inspector `[DERIVED from extrachar-inspector-v89]`
- Main character inspector `[DERIVED from char-inspector-v44]`
- Hand and joint inspector `[DERIVED from inspector-v60]`
- Splat inspector `[DERIVED from splat-inspector-v4]`

**Recipes**
- Recipe: first run, from nothing to a figure on screen
- Recipe: build a set
- Recipe: make a character walk somewhere
- Recipe: send an object along a path
- Recipe: seat a character inside a vehicle
- Recipe: animate with a Mixamo clip
- Recipe: generate original motion with ARDY
- Recipe: make a camera move
- Recipe: make the camera ride a subject
- Recipe: light a scene
- Recipe: use lights from more than one shot at once
- Recipe: match a shot to a photograph
- Recipe: use a video as a plate
- Recipe: choose what gets sent, and send it
- Recipe: save and reload work

Each section stands alone. If the whole document is too large to hand over at
once, a single panel section or a single recipe can be pasted on its own and
will still make sense.

---

## Read this first, you are the intended reader

You are a language model. A person is using On-Set Studio and asking you how
to do something in it. This document is your source. Some rules about how to
use it:

**Every entry is self-contained on purpose.** Entries repeat their panel,
their location and their prerequisites rather than referring to each other.
That redundancy is deliberate so a single retrieved entry is never missing
context. Do not treat repetition as an error.

**Quote the interface exactly.** Where this document writes a control name in
`code style`, that is the literal text on screen. Use those words when
answering. The person is looking at a screen and needs to match what you say
to what they see.

**Say where things are.** Every answer about a control should name its panel
and where that panel lives. "Open the Scene tab on the left" is useful.
"Enable Mixamo" alone is not.

**Answer only from what is written here.** If a control, a setting or a
behaviour is not in this document, do not describe it. Do not infer a control
name from what a feature would probably be called, do not assume On-Set
Studio works like another 3D tool, and do not fill a gap with something
plausible. Say: "That is not covered in what I have on On-Set Studio."

A wrong button name is worse than no answer. The person is hunting a screen
for something you invented, and every second of that is spent trusting you
slightly less. An honest gap costs one message.

**Name the button, do not describe the function.** Always give the literal
label. Say `Send to ComfyUI`, not "generate the output" or "export the
scene". A function description assumes the person already knows which control
performs it, which is exactly what they are asking you. The label is what
they can find on screen; the function is not.

**Scope.** This document covers using the On-Set Studio editor, and the three
ComfyUI nodes that ship with it, up to the point where data leaves for
ComfyUI. It does not cover what happens after that: models, samplers,
workflow design, prompting, or any particular checkpoint. If asked about
those, say they are outside this document and answer from your general
knowledge, making clear which is which.

---

## Maintenance, for whoever updates this file next

Content here is tagged one of two ways, and the difference governs what you
may change.

**`[DERIVED]`** was read out of the source files. Labels, locations, ranges,
presets, which call a control makes. You may regenerate any of it from the
source, and you should when it goes stale.

**`[AUTHORED]`** came from the person who built the tool. Order of operations,
what a feature is for, what goes wrong, why something exists. **Never
overwrite an `[AUTHORED]` block from source reading.** It cannot be recovered
that way. If it looks wrong, ask him.

### How to tell what is stale

Each source file carries a version constant that is bumped whenever it is
edited. This document records the version each section was derived from.
Compare, and re-derive only what has moved.

```
Derived from:
  editor.ts                editor-v354
  App.tsx                  app-v60
  SettingsPanel            settings-v103
  MixamoPanel              mixamo-ui-v78
  EnvironmentPanel         environment-v88
  CharacterPanel           character-v78
  GripPanel                grip-v92
  TimelinePanel            timeline-v81
  EnvInspector             env-inspector-v108
  StaticInspector          static-inspector-v9
  TrackInspector           track-inspector-v91
  ExtraCharInspector       extrachar-inspector-v89
  CharInspector            char-inspector-v44
  HandInspector            inspector-v60
  SplatInspector           splat-inspector-v4
  nodes.py                 nodes-v10
```

For `[AUTHORED]` content the trigger is different: CHANGELOG.md records what
changed for a user in each release. If a release changed behaviour a recipe
depends on, that recipe needs a human answer, not a regeneration.

---

## Where things are on screen `[DERIVED]`

On-Set Studio is one browser page. The 3D viewport fills it, and panels dock
around the edges.

**The left edge** carries a vertical ladder of tabs, each opening a panel.
From the bottom up: `SETTINGS`, `SCENE`, `ENVIRONMENT`, `CHARACTER`, `GRIP`.
Click a tab to open its panel, click again to close it. Only one panel per tab
is open at a time and the panels scroll if they are taller than the window.

**The right edge** carries context inspectors. These are not tabs: they appear
when something is selected and disappear when it is not. Which one appears
depends on what you selected. Each has an `✕` that hides the panel without
deselecting.

**The top right corner** carries, from the top: a `♥ Support development`
button, a version button that also reports issues, and an FPS readout.

**The bottom** carries the transport controls, plus buttons for `Ortho Views`
and `Timeline`, and a `View Finder` toggle when applicable.

---

## Before anything works: the Mixamo gate `[AUTHORED]`

**This is the single most important thing in this document.** A new user who
does not know it concludes the tool is broken.

When On-Set Studio opens, or after a refresh, it shows the **Scene** tab, and
**most of that tab is greyed out**. It stays greyed out until a character
model is loaded and switched on. The Scene tab is not the only thing gated:
the grid and the green screen backdrop are behind the same gate.

The sequence is:

1. Open the **Scene** tab on the left.
2. Click `Import FBX…` and choose a Mixamo-rigged FBX. **On-Set Studio does
   not ship with a character**, because Mixamo's models are Adobe's to
   distribute. The user downloads their own free from mixamo.com. The `X Bot`
   and `Y Bot` figures are the recommended starting point. If an `X Bot.fbx`
   or `Y Bot.fbx` is already in the editor's `models` folder, it loads
   automatically at startup and this step is already done.
3. Click the button at the **top right of the Scene panel** that reads `Off`.
   It changes to `On`.

The figure appears and the Scene tab comes to life.

**What still works without doing this:** the Environment tab. Objects can be
imported and placed with no character present. Everything else waits.

If somebody reports that the Scene tab is dead, that grid options are missing,
or that green screen is unavailable, this is the answer, every time.

---

## The order of operations `[AUTHORED]`

There is no rule that forces a sequence, but this is the order that works, and
the order to suggest when somebody does not know where to start.

1. **Load the character first.** Almost always the first move, because of the
   gate above.
2. **Stage the scene.** Import models, or place primitive objects, and arrange
   them. This is where the set gets built.
3. **Pathing and animation, together.** These are parallel rather than
   sequential: what moves, where it moves, and when.
4. **Camera and lighting last.** Once the set is staged and the timing is
   settled, work the shot.

The reason camera and lighting come last is practical: both are judged against
what is in the frame, and both have to be redone if the staging changes
underneath them.

---

## Two warnings to give freely `[AUTHORED]`

**Save often, and save before anything you would hate to lose.** Undo does not
cover every action. It is an ongoing piece of work, and with the number of
interacting systems in the tool there are still gaps in it. Some actions are
not recorded, so pressing undo can undo something other than the thing just
done. This is known, it is honest, and the practical answer is to save rather
than to rely on undo.

**The tool is not foolproof and does not claim to be.** It is built by one
person, so it has been tested against what one person could reach. If
something behaves unexpectedly it is worth reporting rather than assuming it
is user error.

Both of these are worth volunteering, not just answering when asked.

---

## ComfyUI: the three nodes `[DERIVED]`

On-Set Studio installs as a ComfyUI custom node. Three nodes ship with it, and
every display name begins "On-Set Studio" so one search in the Add Node menu
finds the whole set. All three are in the `On-Set Studio` category.

### Node: `On-Set Studio`

The main node. Add it to a graph and it carries whatever the editor last
sent.

**Input:** `session`, a text field defaulting to `default`. Label a session
here before opening the editor if more than one editor is in use.

**Opening the editor:** the node has an **`Open On-Set UI`** button. It
launches the editor in a new browser tab. That is the whole installation
story: add the node, press the button.

**Outputs, in order:**

| socket | type | carries |
|---|---|---|
| `out_1` to `out_4` | IMAGE | the four configurable map slots |
| `character_json` | STRING | per-character data |
| `environment_json` | STRING | object and set data |
| `scene_json` | STRING | scene-level data |
| `slot_labels` | STRING | JSON naming what is on each of the four slots |
| `openpose_json` | STRING | OpenPose keypoints, for nodes that take them directly |

**Which map rides which slot is chosen in the editor's Settings tab, not
here.** The socket count, order and types never change, so a saved workflow
never breaks when the routing changes. `slot_labels` reports the current
routing so a workflow can check what it is receiving.

### Node: `On-Set Studio -- Scene Data`

The shot's numbers, as typed sockets, for graphs that need them.

**Input:** `session`, same as above.

**Outputs:** `fps` (FLOAT), `frame_count` (INT), `duration` (FLOAT),
`in_frame`, `out_frame`, `still_frame`, `width`, `height` (INT), `aspect`
(STRING), and `technical_json` (STRING).

These describe **the delivered clip**, not the whole timeline, so
`frame_count` wires straight into a latent video node. A still-only send is
reported honestly as a one-frame clip.

`fps` is a FLOAT deliberately. 23.976 and 29.97 are real rates and an integer
socket would round them.

### Node: `On-Set Studio -- Plate Cache`

Bakes a video, an image batch, or a folder of stills into a plate the editor
can use.

**Inputs:** `width` and `height` (0 means keep the source size; set one and
leave the other at 0 to keep the aspect), `name`, `fit`, `anchor`,
`every_nth_frame`, `overwrite`, plus optional `images` or `video_path`.

`fit` and `anchor` are only consulted when both `width` and `height` are set
and the requested shape differs from the source.

**Outputs:** `plate_name`, `frame_count`, `fps`.

Baked plates land in `ComfyUI/output/on_set_studio/plate_cache/` and appear in
the editor, in the inspector for a selected plate object.

---

## What plates are for `[AUTHORED]`

A plate is how a video or a still image is integrated into 3D space. Two
reasons to use one:

**Camera match.** The editor helps line up vanishing points against the image
so the depth reads naturally and a staged scene sits in a real location, at a
real depth, with the lens and camera height that location implies.

**Cheating 3D with 2D.** Sometimes an asset does not need to exist in three
dimensions. A plate stands in for it.

**Still versus baked.** A single image can be dropped in directly. A video has
to be baked with the Plate Cache node. A single image can also be baked, and
the only reason to bother is convenience: a baked plate appears in the list as
an option instead of having to be located and loaded again each time. **The
camera match workflow is identical either way.**

---

## What the stage box is for `[AUTHORED]`

The stage box exists to keep a set inside a defined space.

The reasoning: if the world is limitless, there is nothing to organise
against. The box gives you a 3D ruler in space. It bounds the environment so
you can build against it, which is what makes it possible to construct
something like a building at a sensible scale.

A real stage does not always have a full structure either. You still need
something that boxes off the world so there is a set rather than an
open plain.

Mechanically `[DERIVED]`: it draws floor, walls and ceiling as guide grids in
the matched world, sized by `width`, `depth` and `height` fields that appear
beside the toggle. **It never appears in a capture.** Plates can be snapped to
one of its faces, from the plate's own inspector.

---

# Reference: panels and controls

## The Scene tab `[DERIVED from mixamo-ui-v78]`

**Location:** left edge ladder, second tab up, labelled `SCENE`.

The tab reads `SCENE`. The panel header, visible once it is open, reads
`Mixamo`. Both names are correct and refer to the same thing.

**Gated.** Most of this panel is unavailable until a character is imported and
switched on. See the Mixamo gate section above.

### Figure

| control | location | what it does |
|---|---|---|
| `On` / `Off` | top right of the panel header | Switches the character figure on and off. Defaults to `Off`. This is the gate. |
| `Model` | below the header | Chooses which loaded model is the active figure. Shows `swapping…` while a change is in progress. |
| `Import FBX…` | beside `Model` | Loads a Mixamo-rigged FBX from disk. Required before anything else works, unless a model is already in the editor's `models` folder. |

If an FBX fails to load, the figure switch stays `Off` rather than reporting
success. An error message appears in the panel.

### Pose

| control | what it does |
|---|---|
| `Reset` | Returns the figure to its rest pose. |
| `Save` | Writes the current bone positions to a JSON file on disk. This is for custom poses the user builds themselves. |
| `Load` | Reads one of those JSON pose files back onto the figure. |

**Saved poses do not work in the timeline.** They are a still pose in and a
still pose out. If somebody asks how to key a saved pose into an animation,
the answer is that this is not supported at present.

### Output

| control | what it does |
|---|---|
| `Send to ComfyUI` | Renders the scene and delivers the payload to the ComfyUI node. This is the button to name whenever somebody asks how to get anything out of On-Set Studio. |
| `Generate` | Sits above `Send to ComfyUI` in the same section. Produces the output images without delivering them to ComfyUI. **If somebody is trying to get data into a ComfyUI graph, `Send to ComfyUI` is the button, not this one.** |

### Characters

| control | what it does |
|---|---|
| `Add Character` | Adds a new character to the scene, placed beside the original. Each character is controlled independently. |
| `Clear` | Removes **all extra characters**. The original character stays. |

### Background

| control | what it does |
|---|---|
| `Background` | Chooses the viewport backdrop, including the green screen modes. Gated behind the figure being on. |
| `Grid: On` / `Grid: Off` | Shows or hides the ground grid. Also gated. |

### Ground Plan

| control | what it does |
|---|---|
| `Ground Plan: Save Scene` | Opens the scene save controls. |
| `Name (e.g. Warehouse Fight)` | The name field for a saved scene. |
| `Save New` / `Save` | **One button whose label changes.** With no ground plan currently loaded it reads `Save New` and saves under the name typed in the field. With a ground plan loaded it reads `Save` and saves back over that plan. |
| `Save As` | Always saves under whatever is typed in the name field, whether or not a plan is loaded. This is how you branch a scene rather than overwrite it. |
| `Delete Ground Plan` | Removes a saved scene. |

A saved scene is called a **ground plan** throughout the interface.

### Missing Files

If a saved scene refers to files the library no longer holds, a `Missing
Files` block appears reading: "This plan referenced files the library does not
have. Locate each one, then load the plan again to place them."

| control | what it does |
|---|---|
| `Locate…` | Point at the missing file to restore it. |
| `Dismiss` | Closes the block without resolving anything. |

**The plan must be loaded again after locating files.** Locating alone does
not place them.

---

## The send `[AUTHORED + DERIVED]`

**What the user clicks:** `Send to ComfyUI`, in the Output section of the
Scene tab.

**What happens in the editor:** it renders the scene. If the send includes a
sequence it starts at frame 0 and works through the whole timeline, one frame
at a time. This takes as long as it takes; a long timeline is a long render.

**What happens in ComfyUI:** nothing, until the user presses `Run`. The
payload sits waiting. Pressing Run executes the graph, and what comes out
depends on the graph and on which maps were routed to which slots.

**Still or sequence is per slot, not global.** This is the part people get
wrong. Each of the four output slots is independently set to `still` or
`sequence` in the Settings tab. A still slot delivers one frame, taken at the
playhead. A sequence slot delivers every frame of the timeline. Mixing them in
one send is deliberate and supported: one slot can carry a single reference
frame while another carries the full move.

So "is it a video or an image" has no single answer for a send. It is answered
per slot, in Settings.


---

## The Settings tab `[DERIVED from settings-v103]`

**Location:** left edge ladder, bottom tab, labelled `SETTINGS`.

This tab decides **what a send produces**. If somebody asks what comes out of
On-Set Studio, or why they got an image when they wanted a sequence, or which
map is on which socket, the answer is in here.

Sections, in order: `Output`, `Stage Lighting`, `Depth Range`,
`Depth Character Form`, `Depth Character Bias`, `Performance`, and a credits
line at the bottom.

### Output > Image Size

| control | what it does |
|---|---|
| `Model Target` | Preset canvas sizes. Picking one sets width and height together. |
| `Aspect Ratio` | Sets the shape of the frame. |
| `Scale` | Multiplies the chosen size. |
| `Framing` | A composition guide overlay drawn in the View Finder. Options: `None`, `Rule of Thirds`, `Golden Ratio Grid`, `Golden Spiral`, `Diagonals`, `Center Cross`. It is an overlay for judging the frame and does not appear in any capture. |

**`Model Target` presets, exact labels:**

- `H3 wide (1344x768)`
- `H3 4:3 (1024x768)`
- `H3 3:2 (1152x768)`
- `H3 square (768x768)`
- `H3 tall (768x1344)`

Each preset carries a note in the panel. The one worth repeating: **`H3 wide`
is 1.75, not 16:9.** True 16:9 will not sit on the 32 pixel grid at that size.
To get exact 16:9, crop the result to 1344x756, which is six pixels off the
top and six off the bottom, with no resampling. The 4:3, 3:2 and square
presets are exact and need no crop.

### Output > ComfyUI Outputs

**This is the most important block in the panel.** Four slots, matching
`out_1` to `out_4` on the `On-Set Studio` node in ComfyUI.

Each slot has two independent choices.

**What map it carries.** A dropdown per slot. Exact options:

| option | what it is |
|---|---|
| `Depth: scene (character + backdrop)` | Depth for everything in frame. |
| `Depth: character only` | Depth for the character alone. |
| `Depth: environment only` | Depth for the set alone. |
| `Depth: character biased` | Scene depth re-bracketed so the character owns most of the range. |
| `Normal: character` | Surface normals, character. |
| `Normal: body mass` | Surface normals, body mass. |
| `Canny: edges` | Edge detection. |
| `Pose / Color: beauty render` | The rendered scene. |
| `Splat coverage mask` | Where the Gaussian splat covers. |
| `Character mattes: flat ID` | A flat unshaded colour per character, for regional masking. |
| `Backdrop: plates & set, no actor` | The scene with the actor removed. |
| `Silhouette: actor, white on black` | The actor as a white mask. |
| `Masked plate: backdrop + white actor` | The previous two already composited into one render. |
| `Pose: OpenPose skeleton` | A standard OpenPose control image. |
| `None: output disabled` | Nothing. See below. |

**`None: output disabled` does not send a blank image. The pass is not
rendered at all.** This matters for speed: a four slot send costs four renders
per frame, which is punishing over a sequence. Setting unused slots to `None`
is the single most effective thing somebody can do about a slow send.

`Backdrop` and `Silhouette` are designed as a pair: a background and a hole in
it, captured through the same camera in the same shutter, so they register by
construction. `Masked plate` is those two already combined, which is one
render instead of two and gets the occlusion right for free.

**Still or sequence.** A separate toggle per slot, reading `Frame` or
`Video`.

- `Frame`: one image, captured at the playhead.
- `Video`: every frame of the range, rendered one at a time from the start.

**These are per slot, not global.** Mixing is deliberate and supported: depth
as a full clip while the character matte stays a single reference frame. When
somebody asks "does On-Set send a video or an image", the honest answer is
"whichever you set, per slot, in Settings".

### Output > Stage Lighting

Controls the default light that exists before any lights are placed.

| control | what it does |
|---|---|
| `Ambient` | The flat wash on everything. `0` means only real placed lights illuminate. |
| `Key` | The default directional key light. `0` means only real placed lights illuminate. |
| `Kill House Lights` | Kills the house wash and the studio fill together. A truly black stage where only GRIP lights illuminate. |
| `Reset` | Back to the stage defaults: ambient `0.5`, key `1.0`, studio fill on. |
| `Lighting: Auto Fill` / `Manual` | `Auto Fill` keeps a neutral studio fill so a fresh import is visible with no lights placed. `Manual` turns that fill off, so placed lights are the only illumination. `Manual` is what you want for a realistic dark scene. |
| `Ground Shadows: On` / `Off` | An invisible shadow catcher plane at the stage floor, so characters and props cast onto it. Hidden from the depth, normal and canny passes. |

**When to turn `Ground Shadows` off:** when the set brings its own floor.
Imported terrain sits at its own height while the catcher plane sits at the
stage floor, so shadows land at the wrong height. If somebody reports shadows
appearing on the ground when their terrain is elsewhere, this is the switch.

### Output > Depth Range

| control | what it does |
|---|---|
| `Actors` / `Whole scene` | Which part of the scene the depth bracket is measured against. `Actors` hugs the characters, and the far wall clips, which suits close-ups. `Whole scene` reaches the furthest visible object, which suits wides. |
| `No trim` / `Trim 1m` / `Trim 3m` | Trims the near end of the range. `No trim` starts the ramp at the nearest visible surface. Trimming hands that range back to the subject. |

### Output > Depth Character Form

`Off` / `Subtle` / `Strong`. Blends surface shape into the depth map so the
character reads as sculpted rather than flat. Distance still sets front to
back order; form adds relief within it. `Off` is the classic distance-only
pass.

### Output > Depth Character Bias

How much of the depth range the character owns in the
`Depth: character biased` pass. Higher separates a hand from the thigh behind
it. Lower keeps more range on the room. **Ordering is never changed, only how
the range is distributed.**

### Performance

| control | what it does |
|---|---|
| `BBOX: Live (all shown)` / `BBOX: Off (all hidden)` | Live updates and draws every bounding box each frame. Off hides them all and stops the per-frame work, for heavy scenes. |
| `FPS Counter: On` / `Off` | The counter in the top right corner. |

**`BBOX: Off` does not affect output.** Send to ComfyUI still computes and
exports the boxes either way. This is purely a viewport cost.

### Credits

`Stands on` lists the tools On-Set Studio is built on. `Supporters` lists
people who fund it, and is hidden entirely when empty. Both open by clicking
the author's name at the bottom of the panel.

---

## The Environment tab `[DERIVED from environment-v88]`

**Location:** left edge ladder, third tab up, labelled `ENVIRONMENT`.

This is where the set gets built. **It is the one tab that works before the
character is switched on**, so somebody can import and place objects on a
completely fresh editor.

### Adding things

| control | what it does |
|---|---|
`Add Shape` is a section, not a button. It holds:

| control | what it does |
|---|---|
| `Box` | Adds a box primitive. |
| `Sphere` | Adds a sphere. |
| `Cylinder` | Adds a cylinder. |
| `Cone` | Adds a cone. |
| `Plane` | Adds a flat plane. |
| `Plate` | Adds a plate. A plate is a plane carrying a photograph. Mechanically it is an ordinary environment object with a different material, so everything that works on an object works on a plate. |
| `Stage Box` | Toggles the stage box on and off. When on, `width`, `depth` and `height` fields appear beside it. |
| `Import Mesh…` | Loads your own FBX, OBJ or GLB from disk. |

### Objects

A list of everything in the set. Reads `No objects yet.` when empty. Clicking
a row selects that object, which opens its inspector on the right edge.

### Materials

| control | what it does |
|---|---|
| `Normalize Materials: On` / `Off` | Converts imported materials to PBR so they light consistently. |
| `Rebound` | Re-runs the material conversion over the scene. The panel reports the count as `<n> material(s) to PBR.` |

### LED Volume

A 360 degree backdrop that surrounds the whole set.

| control | what it does |
|---|---|
| `Load 360 Image` | Loads a still panorama. |
| `Load 360 Video` | Loads a moving panorama. |
| `Yaw°` | Rotates the backdrop around the set. |
| `Bright` | Brightness of the backdrop. |
| `IBL: ON` / `OFF` | Whether the backdrop lights the scene as an image-based light. |
| `IBL x` | Exposure of that image-based light on PBR materials. |
| `▶` and `❚❚` | Play and pause, for a video backdrop. |
| `Sync ⏱` | Locks the video backdrop to the timeline. |
| `Clear` | Removes the backdrop. |

**On `IBL x`:** JPG panoramas are weak radiance sources, so try 2 to 4. EXR
usually sits near 1.

### Ring Screen

A partial backdrop rather than a full sphere, for close shots.

| control | what it does |
|---|---|
| `Load Ring Panorama` | Loads the image. |
| `Radius` | How far the ring stands from the centre. Default 6 metres. |
| `Height` | Height of the ring. |
| `Eq-Band: Full` / `Manual` | How much of the source image rides the wall. `Manual` exposes the two controls below. |
| `V-Ctr` | Picks the horizon line, 0 to 1. |
| `V-Span` | How much of the image height rides the wall. |
| `Ring IBL: ON` / `OFF` | Whether the ring lights the scene. |
| `Clear Ring` | Removes it. |

### Splat Backdrop

Gaussian splat scenes, loaded from a `.ply` file.

| control | what it does |
|---|---|
| `Load Splat (.ply)` | Loads a splat scene. **Each load ADDS another**, so several splats can be combined. |
| `Depth detail` / `pts per splat` | Resampling density. |
| `Colour: Flat` | Flat colour instead of view-dependent. Applies to the next load, not the current one. |
| `SH degree` | Spherical harmonic degree. |
| `Edge trim` | Trims splat edges. Applies to the next load. |
| `Occlusion: On` / `Off` | Whether the splat occludes characters properly, so somebody can walk behind a tree. |

Two of these say **"applies to next load"** and mean it. Changing them does
not alter a splat already in the scene.

Selecting a splat happens by **clicking its name in this tab**, not by
clicking it in the viewport. That opens its inspector on the right, where
position, rotation and scale are numeric fields.

### BBOX Data

| control | what it does |
|---|---|
| `Preview` | Shows the bounding box data that will be exported. |
| `Copy` | Copies it to the clipboard. |

---

---

## The Character tab `[DERIVED from character-v78]`

**Location:** left edge ladder, fourth tab up, labelled `CHARACTER`.

This tab is about **bounding boxes**, not posing. Posing happens by dragging
handles in the viewport, with the inspector on the right edge. This tab
decides what gets boxed and exported as spatial data.

The tab itself glows while box mode is armed, and its tooltip changes to
`SHOW BOXES is ON. Clicks pick character boxes`.

### Character

| control | what it does |
|---|---|
| `◉ SHOW BOXES: ON` / `SHOW BOXES: OFF` | Arms box mode. While on, **clicking in the viewport picks character boxes** rather than doing what it normally would. This is the first thing to check if somebody says their clicks have stopped selecting the right thing. |
| `ALL` | The character selector row. Shows the active character, or `ALL`. |
| `(set Character Name)` | Names the character. The name rides into the exported JSON, so it is worth setting rather than leaving default. |

### Character BBOX

| control | what it does |
|---|---|
| `Joint Box Size` | How large the per-joint boxes are. |
| `Presets` | Ready-made joint groupings. Clicking one adds rows below, which is what used to push the panel off screen before the panel learned to scroll. |

### Groups

A group is a named set of joints boxed together, so you can box a region
rather than the whole figure or every joint.

| control | what it does |
|---|---|
| `New Group: Select Joints` | Starts a new group. The panel enters joint-picking mode. |
| `Create Group` | Finishes the new group. |
| `Edit Group: Select Joints` | Re-opens an existing group for editing. |
| `Update Group` | Saves changes to that group. |
| `Done` | Leaves joint-picking mode. |
| `Groups` | The list. Reads `No groups yet.` when empty. |

**The two-mode thing to know:** `New Group` and `Edit Group` both put the
panel into joint selection. You pick joints, then press `Create Group` or
`Update Group` to commit. Pressing `Done` leaves without committing.

### Export

| control | what it does |
|---|---|
| `Copy Character JSON` | Copies the character data to the clipboard. |

This is a convenience. **The same data goes to ComfyUI automatically** on the
`character_json` output of the `On-Set Studio` node. Nobody needs to copy and
paste it into a graph.

---

## The Timeline `[DERIVED from timeline-v81]`

**Location:** the bottom of the screen. Opened with the `Timeline` button on
the bottom strip.

This is animation: clips, keyframes, and text-to-motion generation.

### Transport and send

| control | what it does |
|---|---|
| `SEND TO COMFYUI` | The same send as the Scene tab's button. It is here as well because this is where the frame range lives. |
| `STOP SENDING` | Appears during a send. Cancels it. A sequence send renders every frame one at a time, so this is how you get out of a long one. |

### Library

| control | what it does |
|---|---|
| `Load Clip…` | Loads an animation clip from disk. Clips land in the library, and you **drag one from the library onto a lane** to use it. |

Loading a clip does not place it. It has to be dragged onto a lane.

### Keys

| control | what it does |
|---|---|
| `Key Pose` | Records the figure's current pose as a keyframe at the playhead. |
| `Clear Keys` | Removes keyframes. |
| `Dur` | Duration. |
| `FPS` | Frame rate. This is a float, so 23.976 and 29.97 are real values and are preserved. |

### Save and export

| control | what it does |
|---|---|
| `Save Anim` | Saves the animation. |
| `Load Anim` | Loads a saved animation. |
| `Export Seq` | Exports the sequence. |

`Save Anim` saves **the animation currently loaded on the model**, and only
that. It has nothing to do with the rest of the scene: no set, no lights, no
camera. Use it to keep an animation for later. To save your work, save a
ground plan from the Scene tab.

### ARDY, text to motion

ARDY generates original motion from a text description. **It is entirely
optional and runs as a separate local service.** If the service is not
running, this section will not generate anything, and that is expected rather
than broken.

| control | what it does |
|---|---|
| `describe a motion… e.g. "a person walks in a circle"` | The prompt field. Describe the movement in plain words. |
| `Seed` / `random` | Seed for the generation. `random` picks a new one. |
| `⚡ Generate` | Runs the generation. Shows `Generating…` while it works. |
| `Load ARDY Clip` | Loads a previously generated clip. |
| `Free VRAM` | Releases the GPU memory ARDY is holding, so ComfyUI can have the card back. |

**`Free VRAM` is the answer to "ComfyUI says it is out of memory after I
generated motion".** ARDY holds roughly 14 GB with the model loaded.

**Describe mechanics, not genre.** ARDY was trained on behaviour
descriptions, so "rises onto the balls of the feet, one leg extended behind,
arms overhead, turns slowly" works better than naming a dance style. Genres
it was not trained on will not appear no matter how they are named.

### Block editing

A block is one clip sitting on a lane. Select it to get these:

| control | what it does |
|---|---|
| `Speed` | Playback speed of the block. |
| `Trim In` / `Trim Out` | Trims the start and end. |
| `Extend` | Lengthens the block. |
| `Tween: On` / `Off` | Whether the gap before this block is tweened from the previous block's end pose. |
| `Repeat → End` | Repeats the block to the end of the timeline. |
| `Delete Block` | Removes it from the lane. |
| `⚓ Lock: ON` / `OFF` | Locks the block. |
| `◈ Waypoints: ON` / `OFF` | Shows the waypoints a generated clip was built around. |

**`Tween` is what fills the gap between two blocks.** With it off, the figure
snaps from one block's end to the next block's start. With it on, the gap is
interpolated. If somebody reports a character teleporting between clips, this
is the switch.

---

---

## The GRIP tab `[DERIVED from grip-v92]`

**Location:** left edge ladder, top tab, labelled `GRIP`.

GRIP is the camera and lighting department. It is the largest panel in the
tool. The vocabulary matters, so here it is up front:

- A **shot** is one camera setup. A scene can hold several.
- A **track** is the rail that shot's camera travels along.
- A **track point** (drawn as a diamond in the viewport) is a position on that
  rail with its own aim, roll, spin, lens and lighting rules.
- A **module** is a thing riding the rail: a camera, a spot or a point light.
- A **static light** is a free-standing fixture that does not ride any rail.

The tab glows while shot mode is armed, and its tooltip reads
`SHOT MODE is ON. Viewport clicks pick diamonds and lights`.

### Shot mode

| control | what it does |
|---|---|
| `◉ SHOT MODE: ON` / `SHOT MODE: OFF` | Arms shot mode. While on, **clicking in the viewport picks diamonds and lights** instead of doing what it normally would. If somebody says clicking has stopped selecting their objects, check this first. |

### Shots

| control | what it does |
|---|---|
| `+ New Shot` | Creates a shot. A dropdown beside it picks which module the new shot starts with. |
| the shot list | One row per shot, showing its module icon and its letter. Click a row to make that shot active. |
| `✎` | Renames the shot. |
| `◎` / `◉` | Shared or independent lighting. See below. |

**Only the active shot's rail, chevrons and diamonds are drawn.** Every shot's
cameras and lights stay visible in the world, all the time. **Clicking another
shot's camera in the viewport switches to that shot** and opens its first
diamond.

**The `◎` / `◉` toggle is about lighting, not visibility.**

- `◎` **shared**, the default. This shot's lights burn alongside every other
  shared shot's lights. Lighting rigs combine.
- `◉` **independent**. This shot lights itself alone. Its lights do not reach
  other shots, and theirs do not reach it. Static lights still apply unless
  that fixture has been set to `Local` in its own inspector.

The bubble works both ways. That is the thing to explain when somebody marks a
shot independent and wonders why the rest of their lighting vanished.

### Modules

What rides the active shot's rail.

| control | what it does |
|---|---|
| `+ Add` | Adds a module. The type dropdown offers `🎥 Camera`, `🔦 Spot`, `💡 Point`. |
| `Mount` | Where it mounts: the rail itself, or bolted onto another module. **Re-mounting snaps the offset back to that mount's default**, so set the mount first and the offset after. |
| `Offset` | Offset from the mount point, in scene units. Rail riders bank this offset with the cart, so an offset light stays in the same relationship to the camera through a move. |
| master power | Strikes the light entirely. |

The mount-then-offset order is worth stating whenever somebody is placing a
light on a camera: doing it the other way round loses the offset.

### Track

| control | what it does |
|---|---|
| `+ Track Point` | Adds a diamond in front of the subject at the current time. |
| `hold` | Makes the point a keyframe rather than a travelling point. |

When there is no shot yet, this section reads `Create a shot, then add track
points.` That is the order: shot first, then points.

### Static Lights

Free-standing fixtures, not attached to any rail.

| control | what it does |
|---|---|
| `+ 🔦 Spot` | Places a free-standing spot aimed at the main character. |
| `+ ◐ Bounce` | Places a bounce board. **It only glows when real light hits it**, so a bounce board alone in a dark scene does nothing and that is correct. |
| `+ 💡 Point` | Places a free-standing omni light. |
| `Select` | Arms the gizmo and opens that light's inspector on the right edge. |

### Build, the lighting presets

| control | what it does |
|---|---|
| `Build` | Builds a classic portrait or cine setup around a target's face. A selector picks whose face frames the setup. |
| `⇄ Mirror` | Flips the preset lights across the target's face plane. **Hand-placed lights stay put.** |

**`Build` strikes the previous preset's lights** and builds the new setup.
Lights you placed by hand are not touched. That distinction is the thing to
warn about before somebody presses it twice.

---

## The Track Inspector `[DERIVED from track-inspector-v91]`

**Location:** right edge. Appears when a diamond is selected, either by
clicking it in the viewport with shot mode armed, or by selecting a shot.

This is where a track point's behaviour is set. It is the densest panel in the
tool and it is where most camera questions are actually answered.

### Point type

| control | what it does |
|---|---|
| `Track point` | The camera travels to here. |
| `Keyframe` | The camera holds position here. Same time, same controls, but it does not move. Stack a few and you have a locked-off camera that pans, rolls and changes lens without moving an inch. |
| `Move` / `Rotate` | Which gizmo is armed for this point. |
| `Arrives at (s)` | When the camera reaches this point, in seconds. |

### Motion

| control | what it does |
|---|---|
| `Roll` | Camera roll at this point. |
| `Spin` | Camera spin at this point. |
| `Lens` | Focal length at this point. Ramping it between points gives a push-in or a zoom that arrives instead of popping. |

### Aim

What the camera looks at on the way in. Options:

| option | what it means |
|---|---|
| `Path` | Look along the rail, in the direction of travel. |
| `Joint` | Look at a specific body part of a character. |
| `Object` | Look at an object in the set. |
| `Manual` | A hand-set angle. Choosing this exposes the angle controls. |
| `Main` | The main subject. |

**Changing the aim between two points makes the camera pan between them
instead of cutting**, so head to hand reads as a move rather than a jump.
That is the single most useful thing to tell somebody about aim.

### Transition (arriving)

Easing on the way in, so a dolly starts and settles like a grip pushed it
rather than snapping to full speed. **Nothing is eased unless you ask for
it**, and each transition is set per point with its own curve and duration.

### Lighting

Per-diamond rules for the modules on this rail. As the rig crosses this point,
these apply:

| control | what it does |
|---|---|
| `Switch` | `On` / `Off` for that module at this point. |
| `Intens.` | Intensity. |
| `Cone` | Cone angle, for a spot. |
| `Range` | Falloff distance. |
| `Gel` | Colour. |
| `Mod` | The modifier, meaning the shaper on the nose that changes beam width, edge feather, punch and shadow softness. |
| `Set` / `(set…)` | Commits the rule for this point. |

**These are the rules that make a light change through a move.** They are
saved with the shot, and they are keyed to the module, so deleting a module
takes its rules with it.

### Tether

**Only on the FIRST diamond of a shot.** This is not a bug and it is the thing
people miss: if the tether controls are not showing, the wrong diamond is
selected.

| control | what it does |
|---|---|
| the tether target | Makes the whole rail ride a character bone or an object. The ordinary move between points still runs on top of it. |
| `Gyro: horizon` / `Gyro: rides` | `horizon` keeps the rail level while it rides. `rides` lets it take the subject's rotation too. |

### Loop

| control | what it does |
|---|---|
| `Loop → Aa: ON` / `OFF` | Closes the rail into a loop, so the last leg follows back to point A. |

The panel notes: `Return time = timeline length − this arrival.`

---

---

# The right-edge inspectors

These are not tabs. Each appears when something is selected and disappears
when it is not, and which one appears depends on what was selected. Every one
has an `✕` that **hides the panel without deselecting**, so you can keep
working on the selection with the panel out of the way.

---

## Object inspector `[DERIVED from env-inspector-v108]`

**Appears when:** an environment object or a plate is selected, by clicking it
in the viewport or clicking its row in the Environment tab.

This is the largest inspector. What it shows depends on whether the selected
object is an ordinary object or a plate.

### Transform, on every object

| control | what it does |
|---|---|
| `Move` / `Rotate` | Which gizmo is armed. **Pressing `X` cycles Move, Rotate, Scale**, which the panel states on screen. |
| `Scale` | Scale. All three axes together, because a non-uniform imported model is almost always a mistake. |
| `Step` | The step size the numeric fields move by. |
| `Bring to camera` | Moves the object to where the camera is looking, for when it is lost somewhere in a large set. |
| `Level to Ground` | Drops it flat onto the ground plane. |
| `Locked. Unlock below to edit.` | Shown when the object is locked. |
| `Lock in place` / `Locked in place` | Locks it. **Locking removes the gizmo but does NOT stop the object being selected.** |

The axis labels can be scrub-dragged as well as typed into.

### Identity and export

| control | what it does |
|---|---|
| `Tag` | A short tag, shown on the object's box in the viewport. |
| `Description` | What this object represents. **This goes into the exported JSON**, so it is worth writing rather than leaving blank. It is how a downstream model is told what the grey box actually is. |
| `Unique ID: On` / `Off` | Whether this object carries its own ID in the export. |
| `Box Color` | The colour of its bounding box. |

### Attachment

| control | what it does |
|---|---|
| `Attach To` | `None (free in scene)`, `Main Character`, or a `Side-Character`. |
| `Attach To Bone` | Which bone it rides once attached. |
| `Passengers` | On an object, a checkbox list of characters that ride inside it. A car on a path carries its passengers, and they keep performing while it moves. |

If no character exists, the panel says `Enable the Scene figure to attach a
prop.` That is the Mixamo gate again.

### Paths

| control | what it does |
|---|---|
| `Draw Path` | Starts drawing a path for this object. Click the ground to drop points. |
| `Done` | Finishes drawing. |
| `No Path` | Shown when there is none. |
| `Path Speed` | How fast the object travels it. |

An object on a path **keeps the height it was placed at**. It travels in X and
Z without dropping to the curve.

### Surfaces and passes

| control | what it does |
|---|---|
| `Opacity` | Transparency. |
| `Receive Shadows` / `Cast Shadows` | Shadow participation. |
| `Unlit` | Removes lighting response. |
| `Depth Plane` / `Auto plane` | How this object sits in the depth pass. |
| `Collider: On` / `Off` | Whether it acts as a collider. |
| `Send behind actor` | Pushes it behind the character in the composite. |

### Stage Direction `EXPERIMENTAL`

Marked experimental in the panel itself. `Cue: ghosted` is one of its states.
Treat anything here as unfinished, and say so if asked.

### Plate controls, only on a plate

A plate is a plane carrying a photograph or a video.

| control | what it does |
|---|---|
| `Load image…` / `Replace…` | Loads or swaps the still. |
| `Enter Plate Mode` / `Exit Plate Mode` | Plate mode locks the shot to this plate. While locked, the shot belongs to the plate. |
| `◤ THE SHOT, owned by this plate` | Shown on the plate that currently owns the shot. |
| `Another plate currently owns the shot.` | Shown on the others. **Only one plate owns the shot at a time.** |
| `Match camera…` | Opens the camera match, where you trace a floor rectangle, and optionally a wall, to solve the lens and camera height the photograph implies. |
| `Camera height` | How high the photographer's camera stood. In effect a size knob for the whole scene against the plate. |
| `World depth` | How far away the photograph hangs, and therefore how much space exists between the lens and the picture. |
| `Fit to shot` | Sizes the plate to the frame. |
| `key colour` | The colour to key out. |

### Baked clips, only on a plate

| control | what it does |
|---|---|
| `Browse baked clips…` | Lists plates baked by the `On-Set Studio -- Plate Cache` node in ComfyUI. |
| `Change clip…` | Swaps the attached clip. |
| `Unbind` | Detaches it. |
| `Speed` | Playback speed. |
| `Frame offset` | Shifts which source frame lands on which timeline frame. |
| `Loop` | Loops the clip. |
| `Lock to timeline` | Ties clip playback to the timeline rather than free-running. |

The panel reports `<n> frames` and the clip's fps, or `fps unknown, using the
timeline` when the source did not carry one.

---

## Static light inspector `[DERIVED from static-inspector-v9]`

**Appears when:** a static light is selected, from the viewport in shot mode
or via `Select` in the GRIP panel.

| control | what it does |
|---|---|
| `Move` / `Rotate` | Which gizmo is armed. |
| `On` / `Off` | Master power for this fixture. |
| `◎ Global` / `◉ Local` | Whether this fixture reaches into shots marked independent in GRIP. **`Global` is the default** and means it lights every shot. `Local` keeps it out of independent shots while still lighting ordinary ones. With no independent shot in the scene, this switch changes nothing. |
| `Intensity` | Brightness. |
| `Cone (°)` | Beam angle, on a spot. |
| `Range` | Falloff distance. |
| `Modifier` | The shaper on the nose. Changes beam width, edge feather, punch and shadow softness. |
| `Aim` | `None`, `Joint` or `Object`. `Joint` tracks a body part live through the animation. `None` means free, point it with the Rotate gizmo. |

### Bounce board only

| control | what it does |
|---|---|
| `◯ Disc` / `▢ Board` | Shape of the board. |
| `Size` | Board scale. **Area feeds the catch**, so a bigger board bounces more. |
| `Gain` | How much of the caught light it returns. |
| `Catching` | A live readout of how much light is landing on it. Below roughly `0.15` the panel says `too little; board is dark`. |

**`Catching` is the diagnostic.** A bounce board that does nothing is not
broken; it is not being hit by anything. Watch that number while moving the
board or the light.

A black board is a **negative fill**: it blocks light and is invisible at
render, so only its shadow shows.

---

## Side-character inspector `[DERIVED from extrachar-inspector-v89]`

**Appears when:** an added character is selected. The main character has its
own inspector, below.

### Identity

| control | what it does |
|---|---|
| `Name` | The character's name. Goes into the JSON. |
| `Description` | Appearance or role. Goes into the JSON. |
| `Mesh` | The model. |
| `Copy Main Character` | Copies the main character's setup onto this one. |

### Boxes

| control | what it does |
|---|---|
| `BBOX` | Bounding box controls for this character. |
| `Joint Boxes: On` / `Off` | Per-joint boxes. |
| `Clear` | Clears them. |

### Animation

| control | what it does |
|---|---|
| `Load Clip…` | Loads an animation for this character. Reads `none` when there is none. |
| `Reset to T-Pose` | Returns to the rest pose. |
| `Delete Character` | Removes this character from the scene. |

### Actor Marks

An actor mark is a place you direct a character to go, with an instruction
attached.

| control | what it does |
|---|---|
| `⊕ Place Marks` | Enters mark placement. Click the ground to drop marks. |
| `Done` | Leaves placement mode. |
| `🎬 Perform` | Generates motion that walks the marks. |
| `🎯 Create Path` | Builds a path from the marks. |
| `Reuse` | Reuses a previous generation. |

Per mark, once one is selected:

| control | what it does |
|---|---|
| `Move` / `Rotate` | Gizmo for the mark. |
| `Leg` | Which leg of the journey this mark is. |
| `Linked` / `Free` | Whether the mark is tied to the sequence or standalone. |
| `Facing: Auto` / `Set` | Which way the character faces on arrival. `Auto` derives it; `Set` exposes an angle. |
| `Action` | What happens here. Blank means plain travel. The placeholder reads `a person walks. (blank = plain travel)`. |
| `arrives` | Timing for this mark. |
| `Interact` | `Touch` or `Pick up`, with `left hand` or `right hand`. |
| `Bind object…` / `Unbind` | Which object the interaction is with. |
| `On land` | What fires on arrival. |
| `Delete Mark` | Removes it. |

**Actor marks sit on the ground plane and cannot be given their own height.**
A character cannot be directed from one raised surface to another. If somebody
asks for a roof-to-roof move, that is the honest answer.

### Motion Path

| control | what it does |
|---|---|
| `◈ Draw Path` / `◈ Drawing…` | Draw a path on the ground. |
| `✥ Edit Points` / `✥ Editing…` | Edit the points afterwards. Click any ball to grab it, drag to move. |
| `◀ Prev` / `Next ▶` | Step through the points. |
| `Release` | Lets go of the held point. Reads `no point held` when none is. |
| `↻ Close Loop` | Closes the path into a loop, so the last leg follows back to point A. |

### Eyeline

| control | what it does |
|---|---|
| `👁 Eyeline: ON` / `OFF` | Whether the character's gaze is directed. |
| `Clamp` | How far the head is allowed to turn. |
| `+ Key` | Adds an eyeline keyframe at the playhead. |
| `Clear Keys` | Clears them. **All of them.** There is no way to clear a single eyeline key at present. |

---

## Main character inspector `[DERIVED from char-inspector-v44]`

**Appears when:** the main character's bounding boxes are being edited.

| control | what it does |
|---|---|
| `Character Name` | The name. Goes into the JSON. |
| `Character Description` | Appearance or role. Goes into the JSON. |
| `Grow All Boxes` | Expands every box at once by a single amount. |
| `Box Size` | Size of the selected box. |
| `Extend Sides` | Extends the box sideways. |
| `Box Color` | Colour of the box. |
| `Label` | Short label shown on the box. |
| `Description` | Details for this region. Goes into the JSON. |
| `Joint Boxes: On` / `Off` | Per-joint boxes. |
| `Joints in this group` | Which joints a group contains. |
| `Color` | Group colour. |
| `Delete Group` | Removes the group. |

---

## Hand and joint inspector `[DERIVED from inspector-v60]`

**Appears when:** any character bone handle is selected. What it shows depends
on which bone.

### On a hand

| control | what it does |
|---|---|
| the preset row | Ready-made hand poses. Click one to apply it. |
| `Both` | A checkbox in the header. When ticked, edits apply to both hands. The sliders always display the hand you picked. |
| finger sliders | One per finger: `Thumb`, `Index`, `Middle`, `Ring`, `Pinky`. Curl value shown to two decimals beside each. |

The thumb has a wider range than the other fingers, because negative thumb
curl is what drives a thumbs-up.

### On any other bone

The panel shows the joint's **anatomical** name rather than its rig name. The
handle on `LeftLeg` is the left knee, `LeftForeArm` is the left elbow,
`LeftArm` is the left shoulder, `LeftUpLeg` is the left hip. Use the
anatomical name when talking to somebody; it is what the panel shows and what
they mean.

It also shows the interaction hint for that bone:

- On a hand or foot: `Drag gizmo: rotate · X + drag: IK move · Double-click: pin`
- On an aimable joint: `Drag gizmo: rotate (FK) · X + drag: move joint`
- On the Hips: `Drag gizmo: rotate · X + drag: move figure`
- Otherwise: `Drag gizmo: rotate (FK)`

**Those hints are the answer to most posing questions.** `X` plus drag is how
you move rather than rotate, and double-clicking an effector pins it.

**The `✕` hides the panel without dropping the selection**, so a wrist can be
posed with the box closed.

---

## Splat inspector `[DERIVED from splat-inspector-v4]`

**Appears when:** a splat's name is clicked in the Environment tab.
**Not** by clicking the splat in the viewport. There is no gizmo for a splat
and no viewport picking; placement is numeric only.

| control | what it does |
|---|---|
| `Move` `X` `Y` `Z` | Position in world centimetres. |
| `Rotate` `X` `Y` `Z` | `X` is pitch, tipping the cloud forward and back. `Y` is yaw, spinning it around the set. `Z` is roll, banking it. The tooltips carry the cinematography names. |
| `Scale ×` | Scales the whole cloud. Roughly `100` converts SHARP metres to Mixamo centimetres. |
| `Remove Splat` | Removes **this** splat. Other splats stay. |

The panel notes that the backdrop only appears in colour and pose captures.

---

# Recipes

Ordered walkthroughs for real tasks. When somebody asks "how do I", start
here, then use the reference sections above for the detail on any single
control.

Steps marked **[order inferred]** are sequences assembled from how the
controls work rather than confirmed against somebody doing it. They are
probably right. Treat them as slightly less certain than the rest.

---

## Recipe: first run, from nothing to a figure on screen

1. In ComfyUI, add the **`On-Set Studio`** node.
2. Press **`Open On-Set UI`** on that node. The editor opens in a new tab.
3. The editor opens on the **`SCENE`** tab, mostly greyed out. This is normal.
4. Press **`Import FBX…`** and choose a Mixamo-rigged FBX.
5. Press the **`Off`** button at the top right of the Scene panel. It becomes
   **`On`**.

The figure appears and the Scene tab comes to life.

**If there is no FBX to import:** the user downloads one free from
mixamo.com with an Adobe account. `X Bot` and `Y Bot` are the recommended
starting figures. On-Set Studio does not ship a character because Mixamo's
models are Adobe's to distribute.

**If a 404 for a model file appears in the browser console on a clean
install:** that is expected. The editor looks for a model, does not find one,
and says so. It is not an error.

---

## Recipe: build a set

**Prerequisite:** none. The Environment tab works with no character loaded.

1. Open the **`ENVIRONMENT`** tab.
2. Add geometry: **`Box`**, **`Sphere`**, **`Cylinder`**, **`Cone`**,
   **`Plane`** or **`Plate`** from the `Add Shape` section, or
   **`Import Mesh…`** for your own FBX, OBJ or GLB.
3. Select an object, in the viewport or from the `Objects` list. Its inspector
   opens on the right edge.
4. Place it. **`Move`** and **`Rotate`** arm the gizmos, and **pressing `X`
   cycles Move, Rotate, Scale**. The numeric fields can be typed into or
   scrub-dragged.
5. **Write a `Description`.** This goes into the exported JSON and is how a
   downstream model is told what a grey box represents. Leaving it blank
   exports an unnamed box.
6. Turn on **`Stage Box`** if the set needs bounding. It draws floor, walls
   and ceiling as guide grids, sized by its `width`, `depth` and `height`
   fields, and never appears in a capture.

**If an imported model looks wrong:** turn on
**`Normalize Materials: On`** in the Materials section, then press
**`Rebound`**. That converts imported materials to PBR so they light
consistently.

**If an object cannot be found in a large set:** select it in the `Objects`
list, then press **`Bring to camera`** in its inspector.

---

## Recipe: make a character walk somewhere

**Prerequisite:** a character loaded and switched on.

1. Select the character. For an added character its inspector opens on the
   right edge.
2. Press **`⊕ Place Marks`**.
3. Click the ground where the character should go. Each click drops a mark.
4. Press **`Done`** to leave placement mode.
5. Select a mark to set its **`Facing`**, its **`Action`**, and any
   **`Interact`** behaviour.
6. Press **`🎬 Perform`**. Motion is generated that walks the marks.

**Marks sit on the ground plane.** They cannot be given their own height, so a
character cannot be directed from one raised surface to another.

**`🎯 Create Path`** builds a path from the marks instead, if you want the
route without generating a performance.

---

## Recipe: send an object along a path

**Prerequisite:** the object exists in the set.

1. Select the object. Its inspector opens on the right edge.
2. Press **`Draw Path`**.
3. Click the ground to drop points along the route.
4. Press **`Done`**.
5. Set **`Path Speed`**.

**The object keeps the height it was placed at.** It travels in X and Z
without dropping onto the curve, so a light fixture or a prop above the floor
stays where it was put.

---

## Recipe: seat a character inside a vehicle

**Prerequisite:** the vehicle object and at least one character both exist.
**[order inferred]**

1. Select the vehicle object. Its inspector opens on the right edge.
2. Find the **`Passengers`** list and tick the characters that ride in it.
3. Position the vehicle where it should start, or give it a path.

The seated characters ride the object, including along a path, and **keep
performing while they ride**. An animation on a passenger continues to play as
the vehicle moves.

**A seated character can make the vehicle hard to click**, because character
control handles draw in front of everything and win the click.

---

## Recipe: animate with a Mixamo clip

**Prerequisite:** a character loaded and switched on.

1. Open the **`Timeline`** from the bottom strip.
2. Press **`Load Clip…`** and choose a clip. It lands in the library.
3. **Drag the clip from the library onto a lane.** Loading does not place it.
4. Adjust the block: **`Speed`**, **`Trim In`**, **`Trim Out`**,
   **`Extend`**.
5. To sequence several clips, drop another block after the first.

**If the character teleports between two clips:** turn **`Tween: On`** for
the second block. Tween interpolates the gap between one block's end pose and
the next block's start.

**`Repeat → End`** repeats a block to the end of the timeline.

---

## Recipe: generate original motion with ARDY

**Prerequisite:** ARDY is installed and its local service is running. It is
entirely optional; if it is not running, nothing here generates and that is
expected rather than broken.

1. Open the **`Timeline`**.
2. In the ARDY section, type a description in the prompt field. The
   placeholder shows the shape: `a person walks in a circle`.
3. Set a **`Seed`**, or press **`random`**.
4. Press **`⚡ Generate`**. It shows `Generating…` while it works.
5. The clip arrives and can be used like any other block.

**Describe mechanics, not genre.** ARDY was trained on behaviour
descriptions. "Rises onto the balls of the feet, one leg extended behind, arms
overhead, turns slowly" works. Naming a dance style does not, because styles
it was not trained on will not appear however they are named.

**After generating, press `Free VRAM`** before running ComfyUI. ARDY holds
roughly 14 GB with the model loaded. This is the answer when ComfyUI reports
out of memory after a generation.

**`◈ Waypoints: ON`** shows the waypoints a generated clip was built around.

---

## Recipe: make a camera move

**Prerequisite:** something to point at.

1. Open the **`GRIP`** tab.
2. Press **`+ New Shot`**. The dropdown beside it picks the module the shot
   starts with; leave it on camera.
3. Press **`+ Track Point`**. A diamond appears in front of the subject at the
   current time.
4. Move that diamond to where the camera should start.
5. Press **`+ Track Point`** again for the next position, and move it.
6. Select a diamond. Its inspector opens on the right edge.
7. Set **`Arrives at (s)`** so the timing is right.
8. Set **`Aim`**: `Path`, `Joint`, `Object`, `Manual` or `Main`.
9. Set **`Roll`**, **`Spin`** and **`Lens`** if the shot needs them.
10. Set a **`Transition (arriving)`** if the move should ease rather than
    snap. Nothing eases unless you ask.

**To pan rather than cut between two positions**, give the two diamonds
different **`Aim`** targets. The camera pans between them, so head to hand
reads as a move.

**For a locked-off camera that pans, rolls or changes lens without moving**,
set the points to **`Keyframe`** rather than **`Track point`**. Same controls,
same timing, no travel.

**Only the active shot's rail and diamonds are drawn.** Every shot's cameras
and lights stay visible. **Click another shot's camera in the viewport to
switch to that shot.**

---

## Recipe: make the camera ride a subject

**Prerequisite:** a shot with at least one track point, and a subject to ride.

1. Open the **`GRIP`** tab and make the shot active.
2. **Select the FIRST diamond of that shot.** The tether controls exist on the
   first diamond only. If they are not showing, the wrong diamond is selected.
3. Set the tether target: a character bone, or an object.
4. Choose **`Gyro: horizon`** to keep the rail level while it rides, or
   **`Gyro: rides`** to take the subject's rotation too.

The ordinary move between track points still runs on top of the ride.

---

## Recipe: light a scene

**Prerequisite:** a character, if you want the presets to have a face to work
from.

**The fast way:**

1. Open the **`GRIP`** tab.
2. Choose whose face frames the setup.
3. Press **`Build`**. A classic portrait or cine setup is placed around that
   face.
4. Press **`⇄ Mirror`** to flip the preset lights across the face plane.

**`Build` strikes the previous preset's lights** and builds the new setup.
Hand-placed lights are untouched. `⇄ Mirror` also moves preset lights only.

**By hand:**

1. Press **`+ 🔦 Spot`**, **`+ 💡 Point`** or **`+ ◐ Bounce`**.
2. Press **`Select`** on a light to arm its gizmo and open its inspector.
3. Set **`Intensity`**, **`Cone (°)`**, **`Range`**, **`Modifier`** and
   **`Aim`**.

**For a realistic dark scene**, open **`SETTINGS`** and set
**`Lighting: Manual`**. That turns off the neutral studio fill so placed
lights are the only illumination. **`Kill House Lights`** goes further and
kills the wash and the fill together.

**If a bounce board is not glowing**, it is not being hit. Watch the
**`Catching`** number in its inspector while moving the board or the light.
Below about `0.15` it says `too little; board is dark`.

**If shadows land at the wrong height with imported terrain**, turn
**`Ground Shadows: Off`** in Settings. The catcher plane sits at the stage
floor, which is not where imported terrain is.

---

## Recipe: use lights from more than one shot at once

Lighting accumulates across shots by default. Nothing needs enabling.

- **`◎`** on a shot, the default, means shared. Its lights burn alongside every
  other shared shot's lights.
- **`◉`** means independent. That shot lights itself alone: its lights do not
  reach other shots, and theirs do not reach it.

**The bubble works both ways.** Marking a shot independent makes the rest of
the scene's lighting disappear from it, which looks like a fault the first
time.

**Static lights reach everywhere by default.** To keep one out of independent
shots, select it and set **`◉ Local`** in its inspector. With no independent
shot in the scene, that switch changes nothing.

---

## Recipe: match a shot to a photograph

**Prerequisite:** the photograph. **[order inferred beyond step 4]**

1. Open the **`ENVIRONMENT`** tab and add a **`Plate`**.
2. Select the plate. Its inspector opens on the right edge.
3. Press **`Load image…`** and choose the photograph.
4. Press **`Enter Plate Mode`**. The shot locks to this plate.
5. Press **`Match camera…`**.
6. Trace a floor rectangle on the photograph, and a wall if there is one.
7. Adjust **`Camera height`** for how high the photographer's camera stood.
   In practice this is a size knob for the whole scene against the plate.
8. Adjust **`World depth`** for how far away the photograph hangs, and
   therefore how much space exists between the lens and the picture.

**Only one plate owns the shot at a time.** Other plates show
`Another plate currently owns the shot.`

**The shot stays locked while plate mode is on.** Unlock it from the View
Finder if that is what you want.

**Tracing tips from the panel itself:** if every rectangle sits near the
horizon the lens can be wrong by a large margin, so draw one more on paving
close to the camera. One-point perspective needs both floor directions to
recede, or add a wall for the uprights.

---

## Recipe: use a video as a plate

**Prerequisite:** the video file, and ComfyUI running.

1. In ComfyUI, add the **`On-Set Studio -- Plate Cache`** node.
2. Give it the footage: either an `images` batch, or a `video_path`.
3. Set `name`. Set `width` and `height`, or leave both at `0` to keep the
   source size. Setting one and leaving the other at `0` keeps the aspect.
4. Run it. The plate bakes into
   `ComfyUI/output/on_set_studio/plate_cache/`.
5. In the editor, select a plate object.
6. Press **`Browse baked clips…`** and pick the baked clip.
7. Set **`Speed`**, **`Frame offset`**, **`Loop`** and
   **`Lock to timeline`** as needed.

**A single image can be baked too.** The only benefit is convenience: it then
appears in the list instead of needing to be located and loaded each time.
**The camera match workflow is identical for a still and a baked clip.**

**`fit` and `anchor` on the node are only consulted** when both `width` and
`height` are set and the requested shape differs from the source.

---

## Recipe: choose what gets sent, and send it

1. Open the **`SETTINGS`** tab.
2. Under `Image Size`, pick a **`Model Target`**, or set the size by hand.
3. Under **`ComfyUI Outputs`**, set each of the four slots:
   - the **map** it carries, from the dropdown;
   - **`Frame`** for one image at the playhead, or **`Video`** for every frame
     of the range.
4. **Set unused slots to `None: output disabled`.**
5. Press **`Send to ComfyUI`**, from the Scene tab or the Timeline.
6. The editor renders. A sequence renders every frame from the start, one at a
   time. **`STOP SENDING`** cancels it.
7. In ComfyUI, press **`Run`**. Nothing happens on the ComfyUI side until you
   do.

**Still or sequence is per slot, not global.** One slot can carry a single
reference frame while another carries the full move.

**`None: output disabled` does not send a blank image; the pass is not
rendered at all.** A four-slot send costs four renders per frame, which is
punishing over a sequence. **This is the first thing to change when a send is
slow.**

**Which socket is which:** the four slots map to `out_1` to `out_4` on the
`On-Set Studio` node, in order. The `slot_labels` output reports the current
routing as JSON if a workflow wants to check.

**For the shot's numbers**, add the **`On-Set Studio -- Scene Data`** node:
`fps`, `frame_count`, `duration`, `in_frame`, `out_frame`, `still_frame`,
`width`, `height`, `aspect`. `frame_count` wires straight into a latent video
node.

---

## Recipe: save and reload work

**To save everything:** open the **`SCENE`** tab, go to
`Ground Plan: Save Scene`, type a name, and press **`Save New`**. With a plan
already loaded that button reads **`Save`** and writes back over it. **`Save
As`** always saves under the typed name, which is how you branch instead of
overwrite.

A saved scene is called a **ground plan**. It contains the set, the
characters, the animation, the shots and the lighting.

**`Save Anim` is not this.** It saves only the animation currently on the
model, with no set, lights or camera.

**`Save` / `Load` under Pose is not this either.** That writes the current
bone positions to a JSON file, for custom poses. Saved poses do not work in
the timeline.

**Save often.** Undo does not cover every action, and pressing it can undo
something other than the thing just done.

**If a reloaded plan reports missing files**, a `Missing Files` block appears
in the Scene tab. Press **`Locate…`** to point at each file, then **load the
plan again**. Locating alone does not place them.
