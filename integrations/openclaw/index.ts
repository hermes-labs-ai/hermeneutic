import { definePluginEntry } from "openclaw/plugin-sdk/plugin-entry";
import { createReplyPayloadHandler } from "./gate.mjs";

export default definePluginEntry({
  id: "hermeneutic",
  name: "Hermeneutic",
  description: "Append local evidence-check advisories to risky OpenClaw replies.",
  register(api) {
    api.on("reply_payload_sending", createReplyPayloadHandler(), { timeoutMs: 5000 });
  },
});
