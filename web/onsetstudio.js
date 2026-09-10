// On-Set Studio frontend: adds an "Open On-Set UI" button to the node.
// The editor runs in its own browser tab, served by this node pack at
// /on-set-studio/app/. Its "Send to ComfyUI" button feeds the On-Set Studio
// node. That URL is part of the naming contract documented in nodes.py -- it
// must match the routes there and the vite --base the editor was built with.
import { app } from "../../scripts/app.js";

app.registerExtension({
    name: "OnSetStudio.OpenEditor",
    async beforeRegisterNodeDef(nodeType, nodeData) {
        // The button attaches by class name, so this string MUST track the
        // node's key in NODE_CLASS_MAPPINGS (nodes.py). A mismatch fails
        // silently -- no error, the button simply never appears.
        if (nodeData.name !== "OnSetStudioNode") return;
        const onCreated = nodeType.prototype.onNodeCreated;
        nodeType.prototype.onNodeCreated = function () {
            const r = onCreated ? onCreated.apply(this, arguments) : undefined;
            this.addWidget("button", "Open On-Set UI", null, () => {
                window.open("/on-set-studio/app/", "_blank");
            });
            return r;
        };
    },
});
