ON-SET STUDIO: ARDY BRIDGE
==========================

ARDY is optional. Skip this entire folder if you are keyframing by hand or
using Mixamo clips. Every conventional animation tool in On-Set Studio works
without it.

ARDY is NVIDIA's text-to-motion model. It runs as a separate local service on
your machine and needs roughly 14 GB of VRAM with the model loaded. Install it
first, from https://github.com/nv-tlabs/ardy, including the model checkpoints.


WHAT IS IN HERE
---------------

  onset_ardy_server.py   the bridge between On-Set Studio and ARDY.
                         FastAPI, listens on port 8765.

  retarget_ardy.py       retargets ARDY's motion onto the Mixamo skeleton.
                         Imported by the server; you do not run it directly.

  mixamo_rest.json       the Mixamo skeleton's rest pose. See below.


HOW TO INSTALL
--------------

Copy all three files into your ARDY folder, beside ARDY's own scripts. They
must sit together in the same directory, because the server looks for the
other two next to itself. If you followed NVIDIA's guide that folder is
probably C:\dev\ardy.

Then start the bridge, from ARDY's own Python environment:

    cd C:\...\ardy
    python onset_ardy_server.py

Leave it running. The editor finds it on port 8765 and motion generation
becomes available in the Timeline. The bridge frees its VRAM on request, so
ComfyUI can have the card back between generations.


ABOUT mixamo_rest.json
----------------------

Retargeting has to know the shape of the skeleton it is aiming at. This file
is that description: 65 bones, their hierarchy, and their rest rotations.

The copy shipped here is the STANDARD MIXAMO SKELETON, with the hips at
104.27 cm. That is what X Bot and Y Bot are, and what any character run
through Mixamo's auto-rigger at default proportions is. For those, this file
is correct and you do not need to do anything.

ONE NUMBER IN IT MATTERS MORE THAN THE REST. The retarget reads the hips
height and uses it to convert ARDY's metres into your rig's centimetres:

    scale = mixamo hips height / ARDY standing height

So if your character's hips do NOT sit near 104 cm, the motion will be scaled
for a body that is not yours. A tall rig under-strides and sinks; a short one
over-strides and hovers.


WHEN TO REGENERATE IT
---------------------

Regenerate if your character has non-standard proportions: a converted Unreal
or Blender rig, a stylised figure, anything much taller or shorter than a
default Mixamo body.

HOW YOU WILL KNOW. The bridge prints a line like this when it retargets:

    [scale] mixamo hips 104.3cm / ardy standing 0.9xxm = ...

If that hips number is not close to your character's actual hips height, this
file is describing somebody else's skeleton. Regenerate it.

TO REGENERATE:

  1. Load your character in On-Set Studio and make sure it is at a FRESH
     T-POSE. Reload the editor if you have been posing, because the dump
     records whatever pose the rig is currently in.
  2. Open the browser console and run:

         copy(ipDumpRestPose())

  3. Paste the result over this file, keeping the name mixamo_rest.json.

The file must stay in the same folder as onset_ardy_server.py.


IF SOMETHING GOES WRONG
-----------------------

ModuleNotFoundError: fastapi / uvicorn / pydantic
    The bridge needs these three and ARDY's environment may not have them.
    Inside ARDY's own venv:

        pip install fastapi uvicorn


"missing mixamo_rest.json"
    The three files are not in the same folder, or the file was renamed.

"not an ipDumpRestPose dump"
    The file is not a rest dump. Its first field should read
    "format":"onset-mixamo-rest-v1".

"rest dump is missing bones: [...]"
    The dump came from a rig that is not Mixamo-named. On-Set Studio accepts
    both mixamorig:Hips and mixamorig_Hips, but a rig using Biped, Unreal or
    Rokoko naming has to be converted before any of this works.

The character floats, sinks, or strides the wrong distance
    The hips height in this file does not match your rig. Regenerate it, as
    above.
