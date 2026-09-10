"""On-Set Studio — wraps the browser pose/scene editor as a node.

The editor (built with Vite) is served at /on-set-studio/app/ ;
its "Send to ComfyUI" button POSTs the full payload (images + multi-subject
character JSON + environment JSON + scene metadata) to /on-set-studio/submit.
The On-Set Studio node then emits the latest payload into the workflow.

See README.md for the build/copy loop.
"""

from .nodes import NODE_CLASS_MAPPINGS, NODE_DISPLAY_NAME_MAPPINGS

# serve ./web as a ComfyUI frontend extension (adds the Open Editor button)
WEB_DIRECTORY = "./web"

__all__ = ["NODE_CLASS_MAPPINGS", "NODE_DISPLAY_NAME_MAPPINGS", "WEB_DIRECTORY"]
