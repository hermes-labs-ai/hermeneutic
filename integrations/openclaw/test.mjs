import assert from "node:assert/strict";
import { mkdtemp, chmod, rm, writeFile } from "node:fs/promises";
import { tmpdir } from "node:os";
import path from "node:path";
import { test } from "node:test";
import { createReplyPayloadHandler, runGate, transformOutgoingText } from "./gate.mjs";

test("clean, low severity, and unsupported reply payloads pass through", async () => {
  const clean = await transformOutgoingText("A grounded answer.", {
    runner: async () => undefined,
  });
  const low = await transformOutgoingText("A grounded answer.", {
    runner: async () => ({ severity: "low", ruleIds: ["unhedged_certainty"] }),
  });
  const unsupported = await createReplyPayloadHandler({ runner: async () => ({
    severity: "high",
    ruleIds: ["completion_with_number"],
  }) })({ payload: { mediaUrl: "https://example.invalid/audio" } });

  assert.equal(clean, undefined);
  assert.equal(low, undefined);
  assert.equal(unsupported, undefined);
});

test("medium/high findings append only bounded rule identifiers", async () => {
  const result = await transformOutgoingText("Done — shipped 12 changes.", {
    runner: async () => ({
      severity: "high",
      ruleIds: ["completion_with_number", "completion_with_all_quantifier", "private text\nleak"],
    }),
  });

  assert.equal(
    result,
    "Done — shipped 12 changes.\n\n[Hermeneutic evidence check: high — review evidence for completion_with_number, completion_with_all_quantifier before relying on these claims.]",
  );
});

test("reply payload rewrite preserves other fields and avoids duplicate advisories", async () => {
  const handler = createReplyPayloadHandler({
    runner: async () => ({ severity: "med", ruleIds: ["unsupported_quality_adjective"] }),
  });
  const payload = {
    text: "This is excellent.",
    mediaUrls: ["file:///tmp/audio.ogg"],
    presentation: { kind: "text" },
  };
  const result = await handler({ payload });
  assert.deepEqual(result.payload.mediaUrls, payload.mediaUrls);
  assert.deepEqual(result.payload.presentation, payload.presentation);
  assert.match(result.payload.text, /unsupported_quality_adjective/);
  assert.equal(await handler({ payload: result.payload }), undefined);
});

test("local subprocess receives the draft on stdin and telemetry is forcibly disabled", async () => {
  const previousSink = process.env.HERMENEUTIC_TELEMETRY;
  const previousMode = process.env.HERMENEUTIC_TELEMETRY_CONTEXT;
  const directory = await mkdtemp(path.join(tmpdir(), "hermeneutic-openclaw-"));
  const executable = path.join(directory, "hermeneutic");
  try {
    await writeFile(executable, `#!/usr/bin/env node
let input = "";
process.stdin.setEncoding("utf8");
process.stdin.on("data", (chunk) => { input += chunk; });
process.stdin.on("end", () => {
  if (process.env.HERMENEUTIC_TELEMETRY || process.env.HERMENEUTIC_TELEMETRY_CONTEXT) {
    process.exit(2);
  }
  if (input !== "private response text") process.exit(2);
  process.stdout.write("RISK — highest severity: high\\n  [high] completion_with_number: 'private response text'\\n");
});
`);
    await chmod(executable, 0o700);
    process.env.HERMENEUTIC_TELEMETRY = "/tmp/should-not-be-inherited.jsonl";
    process.env.HERMENEUTIC_TELEMETRY_CONTEXT = "raw";
    assert.deepEqual(await runGate(executable, "private response text", 2000), {
      severity: "high",
      ruleIds: ["completion_with_number"],
    });
  } finally {
    if (previousSink === undefined) delete process.env.HERMENEUTIC_TELEMETRY;
    else process.env.HERMENEUTIC_TELEMETRY = previousSink;
    if (previousMode === undefined) delete process.env.HERMENEUTIC_TELEMETRY_CONTEXT;
    else process.env.HERMENEUTIC_TELEMETRY_CONTEXT = previousMode;
    await rm(directory, { recursive: true, force: true });
  }
});
