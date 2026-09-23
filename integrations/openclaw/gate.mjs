import { spawn } from "node:child_process";

const DEFAULT_TIMEOUT_MS = 2500;
const MAX_TIMEOUT_MS = 10000;
const MAX_DRAFT_BYTES = 200_000;
const MAX_OUTPUT_BYTES = 16_000;
const ADVISORY_PREFIX = "[Hermeneutic evidence check:";

function childEnvironment() {
  return Object.fromEntries(
    Object.entries(process.env).filter(([name]) => !name.startsWith("HERMENEUTIC_TELEMETRY")),
  );
}

function parseVerdict(stdout, exitCode) {
  const match = /^RISK — highest severity: (high|med|low)$/m.exec(stdout);
  if (!match || (exitCode !== 0 && exitCode !== 1)) {
    return undefined;
  }

  const severity = match[1];
  if (severity !== "high" && severity !== "med") {
    return undefined;
  }

  const ruleIds = [...stdout.matchAll(/^\s+\[(?:high|med)\]\s+([a-z0-9_-]+)/gm)]
    .map((item) => item[1]);
  const uniqueRuleIds = [...new Set(ruleIds)].slice(0, 3);
  if (uniqueRuleIds.length === 0) {
    return undefined;
  }

  return { severity, ruleIds: uniqueRuleIds };
}

export function runGate(command, draft, timeoutMs = DEFAULT_TIMEOUT_MS) {
  if (typeof command !== "string" || command.length === 0 || Buffer.byteLength(draft, "utf8") > MAX_DRAFT_BYTES) {
    return Promise.resolve(undefined);
  }

  const boundedTimeout = Number.isInteger(timeoutMs)
    ? Math.min(Math.max(timeoutMs, 100), MAX_TIMEOUT_MS)
    : DEFAULT_TIMEOUT_MS;

  return new Promise((resolve) => {
    let child;
    const stdoutChunks = [];
    let outputBytes = 0;
    let settled = false;
    let timer;
    const finish = (result) => {
      if (settled) return;
      settled = true;
      clearTimeout(timer);
      resolve(result);
    };

    try {
      child = spawn(command, ["gate"], {
        shell: false,
        stdio: ["pipe", "pipe", "ignore"],
        env: childEnvironment(),
      });
    } catch {
      finish(undefined);
      return;
    }

    timer = setTimeout(() => {
      child.kill("SIGKILL");
      finish(undefined);
    }, boundedTimeout);
    timer.unref?.();

    child.stdout.on("data", (chunk) => {
      outputBytes += chunk.length;
      if (outputBytes > MAX_OUTPUT_BYTES) {
        child.kill("SIGKILL");
        finish(undefined);
        return;
      }
      stdoutChunks.push(chunk);
    });
    child.on("error", () => finish(undefined));
    child.on("close", (code) => {
      finish(parseVerdict(Buffer.concat(stdoutChunks).toString("utf8"), code));
    });
    child.stdin.on("error", () => {});
    child.stdin.end(draft, "utf8");
  });
}

export async function transformOutgoingText(text, options = {}) {
  if (typeof text !== "string" || text.length === 0 || text.includes(ADVISORY_PREFIX)) {
    return undefined;
  }

  const result = await (options.runner ?? runGate)(
    options.command ?? "hermeneutic",
    text,
    options.timeoutMs ?? DEFAULT_TIMEOUT_MS,
  );
  if (!result || (result.severity !== "med" && result.severity !== "high")) {
    return undefined;
  }

  const ruleIds = Array.isArray(result.ruleIds)
    ? [...new Set(result.ruleIds.filter((rule) => typeof rule === "string" && /^[a-z0-9_-]+$/.test(rule)))].slice(0, 3)
    : [];
  if (ruleIds.length === 0) {
    return undefined;
  }

  return `${text}\n\n${ADVISORY_PREFIX} ${result.severity} — review evidence for ${ruleIds.join(", ")} before relying on these claims.]`;
}

export function createReplyPayloadHandler({ runner } = {}) {
  const options = {
    command: "hermeneutic",
    timeoutMs: DEFAULT_TIMEOUT_MS,
    ...(typeof runner === "function" ? { runner } : {}),
  };

  return async (event) => {
    const payload = event?.payload;
    if (!payload || typeof payload !== "object") return undefined;

    if (typeof payload.text === "string" && payload.text.length > 0) {
      const text = await transformOutgoingText(payload.text, options);
      return text === undefined ? undefined : { payload: { ...payload, text } };
    }

    const fallback = payload.fallbackText;
    if (fallback && typeof fallback.text === "string") {
      const text = await transformOutgoingText(fallback.text, options);
      return text === undefined
        ? undefined
        : { payload: { ...payload, fallbackText: { ...fallback, text } } };
    }

    return undefined;
  };
}
