#!/usr/bin/env node
"use strict";

const {
  chmodSync,
  closeSync,
  constants,
  copyFileSync,
  existsSync,
  fstatSync,
  lstatSync,
  mkdtempSync,
  mkdirSync,
  openSync,
  readFileSync,
  readlinkSync,
  readdirSync,
  renameSync,
  realpathSync,
  rmSync,
  statSync,
  symlinkSync,
  writeFileSync,
} = require("node:fs");
const https = require("node:https");
const { platform, release, tmpdir } = require("node:os");
const { spawnSync } = require("node:child_process");
const { inflateRawSync } = require("node:zlib");
const { basename, dirname, isAbsolute, join, relative, resolve, sep, win32 } = require("node:path");
const { createHash } = require("node:crypto");
const readline = require("node:readline");

const pathSafetyPolicyPath = join(__dirname, "..", "path_safety_policy.json");
const maxJsonPayloadBytes = 1_048_576;
const packageVersionFallbackMaxDepth = 20;
const payloadDescriptor = "payload.json";
const managedSkillMarker = "aw.marker";
const managedSkillMarkerVersion = "aw-managed-skill-marker.v2";
const deployedFileMode = 0o644;
const deployedDirMode = 0o755;
const agentsBackend = "agents";
const claudeBackend = "claude";
const bundleBackend = "bundle";
const packageSource = "package";
const githubSource = "github";
const legacyAwRuntimeDir = ".aw";
const servoRuntimeDir = ".servo";
const runtimeMigrationSentinel = ".servo-installer-aw-migration.json";
const runtimeMigrationSentinelVersion = "aw-to-servo-runtime-migration.v1";
const runtimeMigrationTextExtensions = new Set([".md", ".json", ".txt"]);
const runtimeMigrationAwPathReplacements = [
  [/\.aw\//g, ".servo/"],
  [/`\.aw`/g, "`.servo`"],
  [/\.aw(?=\s)/g, ".servo"],
  [/aw-set-harness-goal-skill/g, "servo-set-harness-goal-skill"],
];
const defaultGithubRepo = "OceanEyeFF/servo";
const githubRepoPattern = /^[A-Za-z0-9_.-]+\/[A-Za-z0-9_.-]+$/;
const githubRefPattern = /^[A-Za-z0-9][A-Za-z0-9._/-]{0,199}$/;
const githubShaRefPattern = /^[0-9a-fA-F]{40}$/;
const sha256HexPattern = /^[0-9a-fA-F]{64}$/;
const githubArchiveMaxBytes = 500 * 1024 * 1024;
const githubArchiveMaxUncompressedBytes = 500 * 1024 * 1024;
const githubArchiveMaxAttempts = 3;
// ZIP32 APPNOTE field signatures and offsets used by the minimal GitHub source archive reader.
const zipEndOfCentralDirectorySignature = 0x06054b50;
const zipCentralDirectoryHeaderSignature = 0x02014b50;
const zipLocalFileHeaderSignature = 0x04034b50;
const zip64FieldSentinel = 0xffffffff;
const zipEocdMinBytes = 22;
const zipEocdMaxCommentBytes = 0xffff;
const zipEocdSearchWindowBytes = zipEocdMinBytes + zipEocdMaxCommentBytes;
const zipEocdEntryCountOffset = 10;
const zipEocdCentralDirectoryOffset = 16;
const zipCentralDirectoryHeaderBytes = 46;
const zipCentralDirectoryMethodOffset = 10;
const zipCentralDirectoryCrc32Offset = 16;
const zipCentralDirectoryCompressedSizeOffset = 20;
const zipCentralDirectoryUncompressedSizeOffset = 24;
const zipCentralDirectoryFileNameLengthOffset = 28;
const zipCentralDirectoryExtraLengthOffset = 30;
const zipCentralDirectoryCommentLengthOffset = 32;
const zipCentralDirectoryLocalHeaderOffset = 42;
const zipLocalFileHeaderBytes = 30;
const zipLocalFileNameLengthOffset = 26;
const zipLocalExtraLengthOffset = 28;
const expectedPayloadVersions = Object.freeze({
  [agentsBackend]: "agents-skill-payload.v1",
  [claudeBackend]: "claude-skill-payload.v1",
});
const backendTargetRootConfig = Object.freeze({
  [agentsBackend]: Object.freeze({
    optionName: "agentsRoot",
    overrideFlag: "--agents-root",
    defaultSegments: [".agents", "skills"],
  }),
  [claudeBackend]: Object.freeze({
    optionName: "claudeRoot",
    overrideFlag: "--claude-root",
    defaultSegments: [".claude", "skills"],
  }),
});
const cliFlags = Object.freeze({
  all: "--all",
  agentsRoot: "--agents-root",
  backend: "--backend",
  claudeRoot: "--claude-root",
  from: "--from",
  githubArchiveSha256: "--github-archive-sha256",
  githubRef: "--github-ref",
  githubRepo: "--github-repo",
  json: "--json",
  logDir: "--log-dir",
  reinstall: "--reinstall",
  source: "--source",
  to: "--to",
  yes: "--yes",
});
const unrecognizedIssueCodes = new Set(["unrecognized-target-directory"]);
// Diagnose treats these as conflict signals for operator visibility. Update
// may still recover selected conflicts when prune --all can remove them safely.
const conflictIssueCodes = new Set([
  "unexpected-managed-directory",
  "unrecognized-target-directory",
  "wrong-target-entry-type",
]);
// These states are expected to be repaired by the destructive reinstall
// sequence. unexpected-managed-directory is also a diagnose conflict, but
// update can recover it because the recognized marker lets prune --all own it.
// Type/safety violations still block because update must not guess.
const updateRecoverableIssueCodes = new Set([
  "missing-target-root",
  "missing-target-entry",
  "missing-required-payload",
  "target-payload-drift",
  "unexpected-managed-directory",
]);
let cachedPathSafetyPolicy = null;

// ─── ANSI TUI rendering utilities ────────────────────────────────────────────
// Color is always secondary to text/symbol — never the sole state carrier.
// Contract: docs/servo-installer/tui/human-cli-contract.md

const ttyOut = process.stdout.isTTY;
const ttyIn = process.stdin.isTTY;
const noColor = "NO_COLOR" in process.env && process.env.NO_COLOR.length > 0;
const forceColor = "FORCE_COLOR" in process.env && process.env.FORCE_COLOR !== "0";
const haveColor = !noColor && (forceColor || ttyOut);

const ansi = (code) => haveColor ? `\x1b[${code}` : "";

const SGR_RESET = ansi("0m");
const SGR_BOLD = ansi("1m");
const SGR_DIM = ansi("2m");
const SGR_GREEN = ansi("32m");
const SGR_YELLOW = ansi("33m");
const SGR_RED = ansi("31m");
const SGR_CYAN = ansi("36m");
const SGR_WHITE = ansi("37m");

const CSI_HIDE_CURSOR = haveColor ? "\x1b[?25l" : "";
const CSI_SHOW_CURSOR = haveColor ? "\x1b[?25h" : "";
const CSI_CLEAR_SCREEN = haveColor ? "\x1b[2J\x1b[H" : "";
const CSI_SAVE_CURSOR = haveColor ? "\x1b[s" : "";
const CSI_RESTORE_CURSOR = haveColor ? "\x1b[u" : "";
function csiCursorTo(row, col) { return haveColor ? `\x1b[${row};${col}H` : ""; }
function csiEraseToEnd() { return haveColor ? "\x1b[0J" : ""; }

const SYM_OK = haveColor ? `${SGR_GREEN}[OK]${SGR_RESET}` : "[OK]";
const SYM_WARN = haveColor ? `${SGR_YELLOW}[WARN]${SGR_RESET}` : "[WARN]";
const SYM_FAIL = haveColor ? `${SGR_RED}[FAIL]${SGR_RESET}` : "[FAIL]";
const SYM_ARROW = haveColor ? `${SGR_CYAN}>${SGR_RESET}` : ">";

function colorGreen(text)  { return haveColor ? `${SGR_GREEN}${text}${SGR_RESET}` : text; }
function colorYellow(text) { return haveColor ? `${SGR_YELLOW}${text}${SGR_RESET}` : text; }
function colorRed(text)    { return haveColor ? `${SGR_RED}${text}${SGR_RESET}` : text; }
function colorCyan(text)   { return haveColor ? `${SGR_CYAN}${text}${SGR_RESET}` : text; }
function colorDim(text)    { return haveColor ? `${SGR_DIM}${text}${SGR_RESET}` : text; }
function colorBold(text)   { return haveColor ? `${SGR_BOLD}${text}${SGR_RESET}` : text; }

const STATUS_LINES = 7;

// Interactive arrow-key menu using readline.emitKeypressEvents for proper
// terminal mode integration. Returns selected index (0-based), or -1 on cancel.
let _keypressSetup = false;
let suppressMenuReturnUntil = 0;
function setTuiRawMode(enabled) {
  if (ttyIn && typeof process.stdin.setRawMode === "function") {
    process.stdin.setRawMode(enabled);
  }
}
function _ensureKeypress() {
  if (!_keypressSetup && ttyIn) {
    readline.emitKeypressEvents(process.stdin);
    _keypressSetup = true;
  }
}

function _waitKey() {
  return new Promise((resolve) => {
    process.stdin.once("keypress", (str, key) => {
      resolve({ str, key });
    });
  });
}

async function interactiveSelect(rl, options, prompt_) {
  // Non-TTY: use numbered line-input fallback
  if (!ttyIn) {
    refreshTui(tuiState);
    let menu = "\n";
    for (let i = 0; i < options.length; i++) {
      menu += `    ${i + 1}. ${options[i]}\n`;
    }
    menu += `\n${colorDim("1-" + options.length + " choose, q back")}`;
    process.stdout.write(menu);
    const line = await new Promise((resolve) => rl.question("> ", resolve));
    const trimmed = line.trim();
    if (trimmed === "q" || trimmed === "") { return -1; }
    const num = parseInt(trimmed, 10);
    if (num >= 1 && num <= options.length) { return num - 1; }
    return -1;
  }

  // TTY: keypress-based arrow-key selection
  _ensureKeypress();
  setTuiRawMode(true);
  let selected = 0;
  const promptStr = prompt_ || "";

  while (true) {
    refreshTui(tuiState);
    let menu = "\n";
    for (let i = 0; i < options.length; i++) {
      if (i === selected) {
        menu += `  \x1b[7m   ${options[i]}   \x1b[0m\n`;
      } else {
        menu += `    ${options[i]}\n`;
      }
    }
    menu += `\n${colorDim(promptStr + "↑↓ navigate  Enter confirm  q back  b cycle backend")}`;
    process.stdout.write(menu);

    const ev = await _waitKey();

    if (ev.key && ev.key.name === "up") {
      selected = selected > 0 ? selected - 1 : options.length - 1;
    } else if (ev.key && ev.key.name === "down") {
      selected = selected < options.length - 1 ? selected + 1 : 0;
    } else if (ev.key && ev.key.name === "return") {
      if (Date.now() < suppressMenuReturnUntil) {
        suppressMenuReturnUntil = 0;
        continue;
      }
      return selected;
    } else if (ev.str === "q" || (ev.key && ev.key.name === "escape")) {
      return -1;
    } else if (ev.str === "b") {
      tuiState.backend = cycleBackend(tuiState.backend);
    }
    // Unknown key: ignore, re-render
  }
}

const crc32Table = Uint32Array.from({ length: 256 }, (_, index) => {
  let value = index;
  for (let bit = 0; bit < 8; bit += 1) {
    value = value & 1 ? 0xedb88320 ^ (value >>> 1) : value >>> 1;
  }
  return value >>> 0;
});

function crc32(buffer) {
  let checksum = 0xffffffff;
  for (const byte of buffer) {
    checksum = crc32Table[(checksum ^ byte) & 0xff] ^ (checksum >>> 8);
  }
  return (checksum ^ 0xffffffff) >>> 0;
}

function tryReadPackageVersionAt(candidate) {
  try {
    const packageMetadata = JSON.parse(readFileSync(candidate, "utf8"));
    if (packageMetadata.name === "servo-installer" && packageMetadata.version) {
      return packageMetadata.version;
    }
    return "";
  } catch (error) {
    return "";
  }
}

function printHelp() {
  console.log(`usage: servo-installer [tui|<deploy-mode>] [options]

Run servo harness installer commands through the stable Node.js distribution
wrapper. Supported package/runtime deploy modes are handled directly by Node.

commands:
  tui                         open the interactive installer shell
  diagnose --backend agents|claude|bundle
                              print a read-only deploy status summary
  verify --backend agents|claude|bundle
                              run strict read-only deploy verification
  install --backend agents|claude|bundle
                              install the current source payload
  update --backend agents|claude|bundle
                              print an update dry-run plan
  update --backend agents --yes
                              apply the explicit update plan
  update --backend agents --source github --github-ref REF
                              update from a GitHub source archive containing current payloads
  migrate-runtime --from aw --to servo [--json|--yes]
                              preview or copy .aw runtime state into .servo
  prune --all --backend agents|claude|bundle
                              remove managed installs for the backend
  check_paths_exist --backend agents|claude|bundle
                              scan write paths before install

options:
  -h, --help                  show this help message
  -V, --version               show package version
  --from aw --to servo        select the supported runtime migration direction
  --backend agents|claude|bundle
                              include backend in migration reinstall plan output
  --reinstall                 include deploy reinstall/update in migration plan output
  --source package|github     select package-local or GitHub update source
  --agents-root PATH          override the managed agents skills target root
  --claude-root PATH          override the managed Claude skills target root
  --github-repo OWNER/REPO    GitHub source repository for --source github
                              defaults from SERVO_INSTALLER_GITHUB_REPO,
                              GITHUB_REPOSITORY, then upstream repo
  --github-ref REF            GitHub branch/ref for --source github
  --github-archive-sha256 SHA256
                              optional SHA256 digest for the GitHub source archive
  --log-dir PATH              write a sanitized run log JSON file
`);
}

function readPackageVersion() {
  const knownPackagePaths = [
    join(__dirname, "..", "..", "..", "..", "package.json"),
    join(__dirname, "..", "package.json"),
  ];
  for (const candidate of knownPackagePaths) {
    if (!existsSync(candidate)) {
      continue;
    }
    const packageVersion = tryReadPackageVersionAt(candidate);
    if (packageVersion) {
      return packageVersion;
    }
  }

  let current = __dirname;
  for (let depth = 0; depth < packageVersionFallbackMaxDepth; depth += 1) {
    const candidate = join(current, "package.json");
    if (existsSync(candidate)) {
      const packageVersion = tryReadPackageVersionAt(candidate);
      if (packageVersion) {
        return packageVersion;
      }
    }

    const parent = dirname(current);
    if (parent === current) {
      throw new Error("could not find servo-installer package metadata");
    }
    current = parent;
  }
  throw new Error(
    `could not find servo-installer package metadata within ${packageVersionFallbackMaxDepth} parent directories`,
  );
}

function printVersion() {
  console.log(`servo-installer ${readPackageVersion()}`);
}

function parseLogDirOption(args) {
  const strippedArgs = [];
  let logDir;
  for (let index = 0; index < args.length; index += 1) {
    const arg = args[index];
    if (arg === cliFlags.logDir) {
      const value = readOptionValue(args, index);
      if (value === null) {
        return { error: "missing value for --log-dir", args, logDir: undefined };
      }
      logDir = value;
      index += 1;
      continue;
    }
    const logDirValue = readEqualsOption(arg, cliFlags.logDir);
    if (logDirValue !== null) {
      logDir = logDirValue;
      continue;
    }
    strippedArgs.push(arg);
  }
  return { args: strippedArgs, logDir };
}

function defaultInstallerLogDir(targetRepoRoot) {
  return join(targetRepoRoot || process.cwd(), ".logs", "servo-installer");
}

function ensureTargetLogGitignore(targetRepoRoot, logDir) {
  if (!targetRepoRoot || !logDir) {
    return false;
  }
  const defaultLogDir = resolve(defaultInstallerLogDir(targetRepoRoot));
  if (resolve(logDir) !== defaultLogDir) {
    return false;
  }
  const gitignorePath = join(targetRepoRoot, ".gitignore");
  const entry = ".logs/";
  let existing = "";
  if (existsSync(gitignorePath)) {
    existing = readFileSync(gitignorePath, "utf8");
  }
  const alreadyPresent = existing
    .split(/\r?\n/)
    .some((line) => line.trim() === entry);
  if (alreadyPresent) {
    return false;
  }
  const prefix = existing.trimEnd();
  const updated = `${prefix}${prefix ? "\n" : ""}${entry}\n`;
  writeFileSync(gitignorePath, updated, "utf8");
  return true;
}

function timestampForFileName(date = new Date()) {
  return date.toISOString().replace(/[:.]/g, "-");
}

function boundedLines(lines, maxLines = 240) {
  if (lines.length <= maxLines) {
    return lines;
  }
  return [
    ...lines.slice(0, maxLines),
    `[truncated ${lines.length - maxLines} additional line(s)]`,
  ];
}

function safeCommandArgs(args) {
  const redacted = [];
  let redactNext = false;
  for (const arg of args) {
    if (redactNext) {
      redacted.push("<redacted>");
      redactNext = false;
      continue;
    }
    if (/token|secret|password|credential/i.test(arg)) {
      redacted.push("<redacted>");
      if (!arg.includes("=") && arg.startsWith("--")) {
        redactNext = true;
      }
      continue;
    }
    redacted.push(arg);
  }
  return redacted;
}

function shellHint() {
  if (process.env.PSModulePath && process.platform === "win32") {
    return "PowerShell";
  }
  if (process.env.SHELL) {
    return basename(process.env.SHELL);
  }
  if (process.env.ComSpec) {
    return basename(process.env.ComSpec);
  }
  return "unknown";
}

function npmVersion() {
  try {
    const result = spawnSync("npm", ["--version"], {
      encoding: "utf8",
      timeout: 5000,
      env: { ...process.env, npm_config_update_notifier: "false" },
    });
    if (result.status === 0) {
      return result.stdout.trim();
    }
  } catch (error) {
    return "unavailable";
  }
  return "unavailable";
}

function targetStateSummary(targetRepoRoot) {
  const root = targetRepoRoot || process.cwd();
  return {
    target_repo_root: root,
    aw_exists: pathExists(join(root, legacyAwRuntimeDir)),
    servo_exists: pathExists(join(root, servoRuntimeDir)),
    agents_exists: pathExists(join(root, ".agents")),
    claude_exists: pathExists(join(root, ".claude")),
  };
}

function backendFromArgs(args) {
  for (let index = 0; index < args.length; index += 1) {
    const arg = args[index];
    if (arg === cliFlags.backend) {
      return readOptionValue(args, index) || null;
    }
    const backendValue = readEqualsOption(arg, cliFlags.backend);
    if (backendValue !== null) {
      return backendValue;
    }
  }
  return null;
}

function sourceFromArgs(args) {
  for (let index = 0; index < args.length; index += 1) {
    const arg = args[index];
    if (arg === cliFlags.source) {
      return readOptionValue(args, index) || packageSource;
    }
    const sourceValue = readEqualsOption(arg, cliFlags.source);
    if (sourceValue !== null) {
      return sourceValue;
    }
  }
  return packageSource;
}

function createRunLogger({ logDir, args, targetRepoRoot, tui }) {
  if (!logDir) {
    return null;
  }
  mkdirSync(logDir, { recursive: true });
  const startedAt = new Date();
  const output = [];
  return {
    logDir,
    logPath: join(logDir, `${timestampForFileName(startedAt)}-${tui ? "tui" : (args[0] || "default")}.json`),
    startedAt: startedAt.toISOString(),
    args: safeCommandArgs(args),
    targetRepoRoot: targetRepoRoot || process.cwd(),
    tui: Boolean(tui),
    output,
    capture(stream, text) {
      for (const line of String(text).split(/\r?\n/)) {
        if (line.length > 0) {
          output.push({ stream, line: line.slice(0, 1000) });
        }
      }
    },
  };
}

async function withRunLogger(logger, callback) {
  if (logger === null) {
    return await callback();
  }
  const originalLog = console.log;
  const originalError = console.error;
  console.log = (...args) => {
    const line = args.join(" ");
    logger.capture("stdout", line);
    originalLog(...args);
  };
  console.error = (...args) => {
    const line = args.join(" ");
    logger.capture("stderr", line);
    originalError(...args);
  };
  let status = 1;
  let errorMessage = null;
  try {
    status = await callback();
    return status;
  } catch (error) {
    errorMessage = error.message;
    logger.capture("stderr", `servo-installer failed: ${error.message}`);
    throw error;
  } finally {
    console.log = originalLog;
    console.error = originalError;
    const completedAt = new Date().toISOString();
    const logPayload = {
      schema_version: "servo-installer-run-log/v1",
      started_at: logger.startedAt,
      completed_at: completedAt,
      command: logger.args,
      backend: backendFromArgs(logger.args),
      source: sourceFromArgs(logger.args),
      tui: logger.tui,
      environment: {
        platform: process.platform,
        os_platform: platform(),
        os_release: release(),
        shell: shellHint(),
        node: process.version,
        npm: npmVersion(),
      },
      target_state: targetStateSummary(logger.targetRepoRoot),
      verdict: status === 0 ? "pass" : "fail",
      exit_status: status,
      error: errorMessage,
      output: boundedLines(logger.output),
      sanitization: {
        full_environment_dumped: false,
        sensitive_values_redacted: true,
        max_output_lines: 240,
        max_line_chars: 1000,
      },
    };
    writeFileSync(logger.logPath, `${JSON.stringify(logPayload, null, 2)}\n`, "utf8");
    originalLog(`servo-installer log: ${logger.logPath}`);
  }
}

function pathExists(path) {
  return existsSync(path);
}

function lstatOrNull(path) {
  try {
    return lstatSync(path);
  } catch (error) {
    if (error.code === "ENOENT" || error.code === "EACCES" || error.code === "EPERM") {
      return null;
    }
    throw error;
  }
}

function resolveExistingOrLexical(path) {
  let candidate = path;
  if (candidate === "~" || candidate.startsWith(`~${sep}`) || candidate.startsWith("~/")) {
    const home = process.env.HOME || "";
    if (home) {
      candidate = join(home, candidate.slice(2));
    }
  }
  let resolved = resolve(candidate);
  try {
    return realpathSync(resolved);
  } catch (error) {
    if (error.code !== "ENOENT") {
      throw error;
    }
  }

  const suffix = [];
  while (!existsSync(resolved)) {
    const parent = dirname(resolved);
    if (parent === resolved) {
      return resolve(candidate);
    }
    suffix.unshift(basename(resolved));
    resolved = parent;
  }
  return resolve(realpathSync(resolved), ...suffix);
}

/** Return true when `child` is contained in (or equal to) `parent`.
 *  Both arguments are resolved with `path.resolve` before comparison.
 *  Symlinks are NOT dereferenced — callers who need that should pass
 *  already-resolved paths from {@link resolveTargetRepoRoot}. */
function isPathContainedIn(child, parent) {
  const rChild = resolve(child);
  const rParent = resolve(parent);
  const rel = relative(rParent, rChild);
  return rel === "" || (!rel.startsWith("..") && !isAbsolute(rel));
}

function pathSafetyPolicy() {
  if (cachedPathSafetyPolicy !== null) {
    return cachedPathSafetyPolicy;
  }
  cachedPathSafetyPolicy = readJsonObject(pathSafetyPolicyPath);
  return cachedPathSafetyPolicy;
}

function pathSafetyPolicyStringList(fieldName) {
  const value = pathSafetyPolicy()[fieldName];
  if (!Array.isArray(value) || !value.every((item) => typeof item === "string")) {
    throw new Error(`path safety policy field must be a string array: ${fieldName}`);
  }
  return value;
}

function exactSensitiveTargetRepoRoots() {
  return pathSafetyPolicyStringList("exact_sensitive_target_repo_roots").map((path) =>
    resolveExistingOrLexical(path),
  );
}

function recursiveSensitiveTargetRepoRoots() {
  const home = process.env.HOME || "";
  const roots = [...pathSafetyPolicyStringList("recursive_sensitive_target_repo_roots")];
  if (home) {
    roots.push(
      ...pathSafetyPolicyStringList("home_relative_recursive_sensitive_target_repo_roots").map(
        (path) => join(home, path),
      ),
    );
  }
  return roots.map((path) => resolveExistingOrLexical(path));
}

function validateNotSensitiveRepoRoot(resolved, subject, action) {
  for (const sensitiveRoot of exactSensitiveTargetRepoRoots()) {
    if (resolved === sensitiveRoot) {
      throw new Error(`${subject} is protected and cannot be ${action}: ${resolved}`);
    }
  }
  for (const sensitiveRoot of recursiveSensitiveTargetRepoRoots()) {
    if (resolved === sensitiveRoot || isPathContainedIn(resolved, sensitiveRoot)) {
      throw new Error(`${subject} is protected and cannot be ${action}: ${resolved}`);
    }
  }
}

function validateTargetRepoRoot(path, sourceRoot) {
  const resolved = resolveExistingOrLexical(path);
  validateNotSensitiveRepoRoot(resolved, "Target repo root", "managed");

  const tokens = {
    $cwd: process.cwd(),
    $source_root: sourceRoot,
    $home: process.env.HOME || "",
  };
  const allowedPrefixes = pathSafetyPolicyStringList("allowed_target_repo_root_prefixes")
    .map((entry) => tokens[entry] || entry)
    .filter(Boolean)
    .map((candidate) => resolveExistingOrLexical(candidate));
  const uniqueAllowedPrefixes = [...new Set(allowedPrefixes)];
  if (!uniqueAllowedPrefixes.some((prefix) => resolved === prefix || isPathContainedIn(resolved, prefix))) {
    throw new Error(
      `Target repo root ${resolved} is outside allowed paths: ${uniqueAllowedPrefixes.join(", ")}`,
    );
  }
  return resolved;
}

function validateSourceRepoRoot(path) {
  const resolved = resolveExistingOrLexical(path);
  validateNotSensitiveRepoRoot(resolved, "Source repo root", "used");

  const requiredPaths = [
    join(resolved, "product", "harness", "adapters", "agents", "skills"),
    join(resolved, "product", "harness", "adapters", "claude", "skills"),
    join(resolved, "product", "harness", "skills"),
  ];
  const missingPaths = requiredPaths
    .filter((requiredPath) => !isDirectory(requiredPath))
    .map((requiredPath) => relative(resolved, requiredPath).split(sep).join("/"));
  if (missingPaths.length > 0) {
    throw new Error(
      `Source repo root ${resolved} is not a Harness payload source; missing: ${missingPaths.join(", ")}`,
    );
  }
  return resolved;
}

function resolveSourceRoot() {
  const override = process.env.SERVO_HARNESS_REPO_ROOT;
  if (override) {
    return validateSourceRepoRoot(override);
  }
  return validateSourceRepoRoot(join(__dirname, "..", "..", "..", ".."));
}

function resolveTargetRepoRoot(sourceRoot, sourceRootFromEnv) {
  const targetOverride = process.env.SERVO_HARNESS_TARGET_REPO_ROOT;
  if (targetOverride) {
    return validateTargetRepoRoot(targetOverride, sourceRoot);
  }
  if (sourceRootFromEnv) {
    return validateTargetRepoRoot(sourceRoot, sourceRoot);
  }
  return validateTargetRepoRoot(process.cwd(), sourceRoot);
}

function resolveTuiTargetRepoRoot() {
  return resolveTargetRepoRoot(resolveSourceRoot(), Boolean(process.env.SERVO_HARNESS_REPO_ROOT));
}

function targetRootForBackend(backend, targetRepoRoot, options = {}) {
  const config = backendTargetRootConfig[backend];
  const rootOverride = options[config.optionName];
  if (rootOverride === undefined) {
    return join(targetRepoRoot, ...config.defaultSegments);
  }
  return validateTargetRepoRoot(rootOverride, options.sourceRoot);
}

function buildNodeBackendContext(options = {}) {
  const backend = options.backend || agentsBackend;
  if (!Object.prototype.hasOwnProperty.call(expectedPayloadVersions, backend)) {
    throw new Error(`Unsupported backend for Node-owned path: ${backend}`);
  }
  const sourceRootOverride = options.sourceRootOverride;
  const sourceRootFromEnv = sourceRootOverride === undefined && Boolean(process.env.SERVO_HARNESS_REPO_ROOT);
  const sourceRoot =
    sourceRootOverride === undefined
      ? resolveSourceRoot()
      : validateSourceRepoRoot(sourceRootOverride);
  const targetRepoRoot = resolveTargetRepoRoot(sourceRoot, sourceRootFromEnv);
  const targetRoot = targetRootForBackend(backend, targetRepoRoot, {
    ...options,
    sourceRoot,
  });
  const targetRootConfig = backendTargetRootConfig[backend];
  const targetRootOverrideFlag =
    options[targetRootConfig.optionName] === undefined
      ? {}
      : { targetRootOverrideFlag: targetRootConfig.overrideFlag };
  return {
    backend,
    sourceKind: options.sourceKind || packageSource,
    sourceRef: options.sourceRef || "package-local",
    sourceRoot,
    targetRepoRoot,
    targetRoot,
    ...targetRootOverrideFlag,
    adapterSkillsDir: join(sourceRoot, "product", "harness", "adapters", backend, "skills"),
  };
}

function buildNodeAgentsContext(options = {}) {
  return buildNodeBackendContext({ ...options, backend: agentsBackend });
}

function isDirectory(path) {
  const stat = lstatOrNull(path);
  return stat !== null && !stat.isSymbolicLink() && stat.isDirectory();
}

function isFile(path) {
  const stat = lstatOrNull(path);
  return stat !== null && !stat.isSymbolicLink() && stat.isFile();
}

function readRegularFileText(path) {
  const noFollowFlag = constants.O_NOFOLLOW || 0;
  let fd = null;
  try {
    fd = openSync(path, constants.O_RDONLY | noFollowFlag);
    const stat = fstatSync(fd);
    if (!stat.isFile()) {
      const error = new Error(`Path is not a regular file: ${path}`);
      error.code = "ENOTREG";
      throw error;
    }
    return readFileSync(fd, "utf8");
  } catch (error) {
    if (error.code === "ELOOP") {
      const regularFileError = new Error(`Path is not a regular file: ${path}`);
      regularFileError.code = "ENOTREG";
      throw regularFileError;
    }
    throw error;
  } finally {
    if (fd !== null) {
      closeSync(fd);
    }
  }
}

function readJsonText(path, missingMessage) {
  let stat;
  try {
    stat = lstatSync(path);
  } catch (error) {
    if (error.code === "ENOENT" && missingMessage) {
      throw new Error(missingMessage);
    }
    throw error;
  }
  if (!stat.isFile()) {
    throw new Error(`JSON payload must be a real file: ${path}`);
  }
  if (stat.size > maxJsonPayloadBytes) {
    throw new Error(
      `JSON payload exceeds ${maxJsonPayloadBytes} byte limit: ${path}`,
    );
  }
  return readFileSync(path, "utf8");
}

function readJsonObject(path) {
  let data;
  try {
    data = JSON.parse(readJsonText(path));
  } catch (error) {
    throw new Error(`Invalid JSON in ${path}: ${error.message}`);
  }
  if (data === null || Array.isArray(data) || typeof data !== "object") {
    throw new Error(`JSON payload must be an object: ${path}`);
  }
  return data;
}

function readJsonObjectWithText(path) {
  const text = readJsonText(path, `Missing JSON file: ${path}`);
  let data;
  try {
    data = JSON.parse(text);
  } catch (error) {
    throw new Error(`Invalid JSON in ${path}: ${error.message}`);
  }
  if (data === null || Array.isArray(data) || typeof data !== "object") {
    throw new Error(`JSON payload must be an object: ${path}`);
  }
  return { data, text };
}

function normalizeRelativePath(value, fieldName, skillId, rootDescription) {
  if (typeof value !== "string" || value.trim() === "") {
    throw new Error(`${fieldName} must be a non-empty relative path for skill ${skillId}`);
  }
  if (value.includes("\0")) {
    throw new Error(`${fieldName} must not contain null bytes for skill ${skillId}: ${value}`);
  }
  const normalized = value.replace(/\\/g, "/");
  if (normalized.startsWith("/") || /^[A-Za-z]:/.test(normalized)) {
    throw new Error(`${fieldName} must stay within the ${rootDescription} for skill ${skillId}: ${value}`);
  }
  const segments = normalized.split("/").filter(Boolean);
  const invalidSegment = segments.find((segment) => segment === "." || segment === "..");
  if (invalidSegment) {
    throw new Error(`${fieldName} must not contain '${invalidSegment}' path segments for skill ${skillId}: ${value}`);
  }
  if (segments.length === 0) {
    throw new Error(`${fieldName} must be a non-empty relative path for skill ${skillId}`);
  }
  return segments.join("/");
}

function stringList(value) {
  return Array.isArray(value) && value.every((item) => typeof item === "string") ? value : null;
}

function payloadTargetMetadata(payload, binding) {
  const targetDirValue = payload.target_dir;
  const targetEntryName = payload.target_entry_name;
  const requiredPayloadFiles = stringList(payload.required_payload_files);
  if (typeof targetDirValue !== "string" || typeof targetEntryName !== "string") {
    throw new Error(`payload target metadata is invalid for skill ${binding.skillId}`);
  }
  if (requiredPayloadFiles === null) {
    throw new Error(`payload required_payload_files must be a string array for skill ${binding.skillId}`);
  }

  const targetDir = normalizeRelativePath(
    targetDirValue,
    "payload target_dir",
    binding.skillId,
    "backend target root",
  );
  if (targetDir.includes("/")) {
    throw new Error(`payload target_dir must be a single directory name for skill ${binding.skillId}: ${targetDirValue}`);
  }
  const targetEntry = normalizeRelativePath(
    targetEntryName,
    "payload target_entry_name",
    binding.skillId,
    "backend target root",
  );
  const requiredFiles = requiredPayloadFiles.map((entry) =>
    normalizeRelativePath(entry, "payload required_payload_files entry", binding.skillId, "backend target root"),
  );
  if (!requiredFiles.includes(targetEntry)) {
    throw new Error(
      `payload target_entry_name ${targetEntryName} must be listed in required_payload_files for skill ${binding.skillId}`,
    );
  }
  if (!requiredFiles.includes(payloadDescriptor)) {
    throw new Error(`payload required_payload_files must include ${payloadDescriptor} for skill ${binding.skillId}`);
  }
  if (!requiredFiles.includes(managedSkillMarker)) {
    throw new Error(`payload required_payload_files must include ${managedSkillMarker} for skill ${binding.skillId}`);
  }

  const legacyTargetDirsRaw = payload.legacy_target_dirs === undefined ? [] : stringList(payload.legacy_target_dirs);
  if (legacyTargetDirsRaw === null) {
    throw new Error(`payload legacy_target_dirs must be a list of strings for skill ${binding.skillId}`);
  }
  const legacyTargetDirs = legacyTargetDirsRaw.map((entry) =>
    normalizeRelativePath(entry, "payload legacy_target_dirs entry", binding.skillId, "backend target root"),
  );
  for (const legacyDir of legacyTargetDirs) {
    if (legacyDir.includes("/")) {
      throw new Error(
        `payload legacy_target_dirs entries must be single directory names for skill ${binding.skillId}: ${legacyDir}`,
      );
    }
  }
  if (legacyTargetDirs.includes(targetDir)) {
    throw new Error(`payload target_dir ${targetDir} must not be listed in legacy_target_dirs for skill ${binding.skillId}`);
  }

  const legacySkillIdsRaw = payload.legacy_skill_ids === undefined ? [] : stringList(payload.legacy_skill_ids);
  if (legacySkillIdsRaw === null) {
    throw new Error(`payload legacy_skill_ids must be a list of strings for skill ${binding.skillId}`);
  }
  const legacySkillIds = legacySkillIdsRaw.map((entry) =>
    normalizeRelativePath(entry, "payload legacy_skill_ids entry", binding.skillId, "backend target root"),
  );
  for (const legacySkillId of legacySkillIds) {
    if (legacySkillId.includes("/")) {
      throw new Error(
        `payload legacy_skill_ids entries must be single directory names for skill ${binding.skillId}: ${legacySkillId}`,
      );
    }
  }
  if (legacySkillIds.includes(binding.skillId)) {
    throw new Error(`binding skill_id ${binding.skillId} must not be listed in legacy_skill_ids for skill ${binding.skillId}`);
  }

  return {
    targetDir,
    targetEntryName: targetEntry,
    requiredPayloadFiles: requiredFiles,
    legacyTargetDirs,
    legacySkillIds,
  };
}

function collectSkillBindings(context) {
  const backend = context.backend || agentsBackend;
  if (!isDirectory(context.adapterSkillsDir)) {
    return [];
  }
  return readdirSync(context.adapterSkillsDir, { withFileTypes: true })
    .filter((entry) => entry.isDirectory())
    .map((entry) => entry.name)
    .sort()
    .map((skillId) => ({
      backend,
      skillId,
      payloadDir: join(context.adapterSkillsDir, skillId),
      payloadPath: join(context.adapterSkillsDir, skillId, payloadDescriptor),
    }));
}

function cachedBindingPayload(binding, loadedPayloads) {
  if (loadedPayloads === null || loadedPayloads === undefined) {
    return null;
  }
  return loadedPayloads.get(binding.payloadPath) || null;
}

function bindingPayloadObject(binding, loadedPayloads) {
  const cachedPayload = cachedBindingPayload(binding, loadedPayloads);
  if (cachedPayload !== null) {
    return cachedPayload.payload;
  }
  return readJsonObject(binding.payloadPath);
}

function bindingPayloadWithText(binding, loadedPayloads) {
  const cachedPayload = cachedBindingPayload(binding, loadedPayloads);
  if (cachedPayload !== null) {
    return cachedPayload;
  }
  const loadedPayload = readJsonObjectWithText(binding.payloadPath);
  return {
    payload: loadedPayload.data,
    payloadText: loadedPayload.text,
  };
}

class PayloadLoadError extends Error {
  constructor(binding, cause) {
    super(cause.message, { cause });
    this.name = "PayloadLoadError";
    this.payloadPath = binding.payloadPath;
  }
}

/**
 * Preloads payload JSON and original text by payload path for one deploy pass.
 */
function loadBindingPayloads(bindings) {
  const loadedPayloads = new Map();
  for (const binding of bindings) {
    try {
      loadedPayloads.set(binding.payloadPath, bindingPayloadWithText(binding, null));
    } catch (error) {
      throw new PayloadLoadError(binding, error);
    }
  }
  return loadedPayloads;
}

function issue(code, path, detail) {
  return { code, path, detail };
}

function verifyTargetRoot(targetRoot, backend = agentsBackend) {
  const stat = lstatOrNull(targetRoot);
  if (stat === null) {
    return [issue("missing-target-root", targetRoot, `${backend} target root does not exist`)];
  }
  if (stat.isSymbolicLink()) {
    if (existsSync(targetRoot)) {
      return [issue("wrong-target-root-type", targetRoot, "target root must be a real directory, not a symlink")];
    }
    return [issue("broken-target-root-symlink", targetRoot, "target root is a broken symlink")];
  }
  if (stat.isDirectory()) {
    return [];
  }
  return [issue("wrong-target-root-type", targetRoot, "target root exists but is not a directory")];
}

function validateGithubRepo(value) {
  if (!githubRepoPattern.test(value)) {
    throw new Error(`GitHub repo must use OWNER/REPO with safe characters only: ${value}`);
  }
  return value;
}

function validateGithubRef(value) {
  if (
    !githubRefPattern.test(value) ||
    value.includes("..") ||
    value.endsWith("/") ||
    value.endsWith(".lock")
  ) {
    throw new Error(`GitHub ref contains unsupported characters: ${value}`);
  }
  return value;
}

function validateSha256Digest(value) {
  if (!sha256HexPattern.test(value)) {
    throw new Error(`SHA256 digest must be 64 hexadecimal characters: ${value}`);
  }
  return value.toLowerCase();
}

function defaultGithubSourceRepo() {
  return process.env.SERVO_INSTALLER_GITHUB_REPO || process.env.GITHUB_REPOSITORY || defaultGithubRepo;
}

function githubArchiveRefPath(ref) {
  if (ref.startsWith("refs/")) {
    return ref;
  }
  if (githubShaRefPattern.test(ref)) {
    return ref;
  }
  return `refs/heads/${ref}`;
}

function githubArchiveUrl(repo, ref) {
  const safeRepo = validateGithubRepo(repo);
  const safeRef = validateGithubRef(ref);
  return `https://codeload.github.com/${safeRepo}/zip/${encodeURI(githubArchiveRefPath(safeRef))}`;
}

function validateZipMemberPath(memberName) {
  const unsafeMessage = `GitHub archive contains unsafe path: ${memberName}`;
  if (memberName.includes("\0")) {
    throw new Error(unsafeMessage);
  }
  const normalized = memberName.replace(/\\/g, "/");
  const windowsPath = win32.parse(memberName);
  if (normalized.startsWith("/") || isAbsolute(normalized) || windowsPath.root || /^[A-Za-z]:/.test(memberName)) {
    throw new Error(unsafeMessage);
  }
  const segments = normalized.split("/").filter(Boolean);
  if (segments.length === 0 || segments.some((segment) => segment === "." || segment === "..")) {
    throw new Error(unsafeMessage);
  }
  return segments.join("/");
}

function findZipEndOfCentralDirectory(buffer) {
  const minOffset = Math.max(0, buffer.length - zipEocdSearchWindowBytes);
  for (let offset = buffer.length - zipEocdMinBytes; offset >= minOffset; offset -= 1) {
    if (buffer.readUInt32LE(offset) === zipEndOfCentralDirectorySignature) {
      return offset;
    }
  }
  throw new Error("GitHub source archive is not a supported ZIP file");
}

function zipEntries(buffer) {
  const eocdOffset = findZipEndOfCentralDirectory(buffer);
  const entryCount = buffer.readUInt16LE(eocdOffset + zipEocdEntryCountOffset);
  const centralDirOffset = buffer.readUInt32LE(eocdOffset + zipEocdCentralDirectoryOffset);
  const entries = [];
  let offset = centralDirOffset;
  for (let index = 0; index < entryCount; index += 1) {
    if (offset + zipCentralDirectoryHeaderBytes > buffer.length) {
      throw new Error("GitHub source archive central directory is invalid");
    }
    if (buffer.readUInt32LE(offset) !== zipCentralDirectoryHeaderSignature) {
      throw new Error("GitHub source archive central directory is invalid");
    }
    const method = buffer.readUInt16LE(offset + zipCentralDirectoryMethodOffset);
    const crc32Value = buffer.readUInt32LE(offset + zipCentralDirectoryCrc32Offset);
    const compressedSize = buffer.readUInt32LE(offset + zipCentralDirectoryCompressedSizeOffset);
    const uncompressedSize = buffer.readUInt32LE(offset + zipCentralDirectoryUncompressedSizeOffset);
    const fileNameLength = buffer.readUInt16LE(offset + zipCentralDirectoryFileNameLengthOffset);
    const extraLength = buffer.readUInt16LE(offset + zipCentralDirectoryExtraLengthOffset);
    const commentLength = buffer.readUInt16LE(offset + zipCentralDirectoryCommentLengthOffset);
    const localHeaderOffset = buffer.readUInt32LE(offset + zipCentralDirectoryLocalHeaderOffset);
    if (
      compressedSize === zip64FieldSentinel ||
      uncompressedSize === zip64FieldSentinel ||
      localHeaderOffset === zip64FieldSentinel
    ) {
      throw new Error("GitHub source archive ZIP64 entries are not supported by the Node path");
    }
    const nameStart = offset + zipCentralDirectoryHeaderBytes;
    const nameEnd = nameStart + fileNameLength;
    const nextOffset = nameEnd + extraLength + commentLength;
    if (nextOffset > buffer.length) {
      throw new Error("GitHub source archive central directory is invalid");
    }
    const name = buffer.subarray(nameStart, nameEnd).toString("utf8");
    entries.push({ name, method, crc32: crc32Value, compressedSize, uncompressedSize, localHeaderOffset });
    offset = nextOffset;
  }
  return entries;
}

function githubArchiveUncompressedLimitError(maxBytes, entryName = undefined) {
  const suffix = entryName === undefined ? "" : `: ${entryName}`;
  return new Error(`GitHub source archive uncompressed size exceeds ${maxBytes} byte limit${suffix}`);
}

function zipEntryData(buffer, entry, options = {}) {
  const maxUncompressedBytes = options.maxUncompressedBytes;
  const localOffset = entry.localHeaderOffset;
  if (localOffset + zipLocalFileHeaderBytes > buffer.length) {
    throw new Error(`GitHub source archive local header is invalid: ${entry.name}`);
  }
  if (buffer.readUInt32LE(localOffset) !== zipLocalFileHeaderSignature) {
    throw new Error(`GitHub source archive local header is invalid: ${entry.name}`);
  }
  const fileNameLength = buffer.readUInt16LE(localOffset + zipLocalFileNameLengthOffset);
  const extraLength = buffer.readUInt16LE(localOffset + zipLocalExtraLengthOffset);
  const dataStart = localOffset + zipLocalFileHeaderBytes + fileNameLength + extraLength;
  const dataEnd = dataStart + entry.compressedSize;
  if (dataEnd > buffer.length) {
    throw new Error(`GitHub source archive entry data is invalid: ${entry.name}`);
  }
  const compressed = buffer.subarray(dataStart, dataStart + entry.compressedSize);
  let data;
  if (entry.method === 0) {
    data = compressed;
  } else if (entry.method === 8) {
    try {
      data = inflateRawSync(
        compressed,
        maxUncompressedBytes === undefined ? undefined : { maxOutputLength: maxUncompressedBytes + 1 },
      );
    } catch (error) {
      if (maxUncompressedBytes !== undefined) {
        throw githubArchiveUncompressedLimitError(maxUncompressedBytes, entry.name);
      }
      throw error;
    }
  } else {
    throw new Error(`GitHub source archive uses unsupported ZIP compression method ${entry.method}: ${entry.name}`);
  }
  if (maxUncompressedBytes !== undefined && data.length > maxUncompressedBytes) {
    throw githubArchiveUncompressedLimitError(maxUncompressedBytes, entry.name);
  }
  if (data.length !== entry.uncompressedSize) {
    throw new Error(`GitHub source archive entry size mismatch: ${entry.name}`);
  }
  if (crc32(data) !== entry.crc32) {
    throw new Error(`GitHub source archive entry CRC32 mismatch: ${entry.name}`);
  }
  return data;
}

function safeExtractZipBuffer(buffer, destination, options = {}) {
  const maxUncompressedBytes =
    options.maxUncompressedBytes === undefined ? githubArchiveMaxUncompressedBytes : options.maxUncompressedBytes;
  mkdirSync(destination, { recursive: true });
  if (readdirSync(destination).length > 0) {
    throw new Error(`GitHub archive extraction destination must be empty: ${destination}`);
  }
  const stagingRoot = mkdtempSync(join(dirname(destination), "servo-installer-extract-"));
  try {
    let extractedBytes = 0;
    for (const entry of zipEntries(buffer)) {
      const relativeName = validateZipMemberPath(entry.name);
      const targetPath = resolve(stagingRoot, relativeName);
      if (!isPathContainedIn(targetPath, stagingRoot)) {
        throw new Error(`GitHub archive contains unsafe path: ${entry.name}`);
      }
      if (entry.name.endsWith("/")) {
        mkdirSync(targetPath, { recursive: true });
        continue;
      }
      const remainingBytes = maxUncompressedBytes - extractedBytes;
      if (entry.uncompressedSize > remainingBytes) {
        throw githubArchiveUncompressedLimitError(maxUncompressedBytes, entry.name);
      }
      mkdirSync(dirname(targetPath), { recursive: true });
      const data = zipEntryData(buffer, entry, { maxUncompressedBytes: remainingBytes });
      extractedBytes += data.length;
      if (extractedBytes > maxUncompressedBytes) {
        throw githubArchiveUncompressedLimitError(maxUncompressedBytes, entry.name);
      }
      writeFileSync(targetPath, data);
    }
    rmSync(destination, { recursive: true, force: true });
    renameSync(stagingRoot, destination);
  } catch (error) {
    rmSync(stagingRoot, { recursive: true, force: true });
    throw error;
  }
}

function extractedArchiveRoot(destination) {
  const candidates = readdirSync(destination, { withFileTypes: true })
    .filter((entry) => entry.isDirectory())
    .map((entry) => join(destination, entry.name));
  if (candidates.length !== 1) {
    throw new Error(
      `Expected GitHub archive to contain one repository root, found ${candidates.length}. ` +
        "Check --github-repo/--github-ref and ensure the downloaded archive is a GitHub source archive.",
    );
  }
  return candidates[0];
}

function githubSourceRootFromArchiveBuffer(repo, ref, archiveBuffer, archiveSha256 = undefined, options = {}) {
  const safeRepo = validateGithubRepo(repo);
  const safeRef = validateGithubRef(ref);
  if (archiveSha256 !== undefined) {
    const expectedSha256 = validateSha256Digest(archiveSha256);
    const actualSha256 = createHash("sha256").update(archiveBuffer).digest("hex");
    if (actualSha256 !== expectedSha256) {
      throw new Error(`GitHub source archive SHA256 mismatch: expected ${expectedSha256}, got ${actualSha256}`);
    }
  }
  const tempRoot = mkdtempSync(join(tmpdir(), "servo-installer-github-source-"));
  try {
    const extractRoot = join(tempRoot, "extract");
    mkdirSync(extractRoot);
    safeExtractZipBuffer(archiveBuffer, extractRoot, {
      maxUncompressedBytes: options.maxUncompressedBytes,
    });
    const sourceRoot = validateSourceRepoRoot(extractedArchiveRoot(extractRoot));
    return {
      sourceRoot,
      sourceKind: githubSource,
      sourceRef: `${safeRepo}@${safeRef}`,
      cleanup: () => rmSync(tempRoot, { recursive: true, force: true }),
    };
  } catch (error) {
    rmSync(tempRoot, { recursive: true, force: true });
    throw error;
  }
}

function githubArchiveDownloadError(repo, ref, message, retryable = false) {
  const error = new Error(`Failed to download GitHub source archive ${repo}@${ref}: ${message}`);
  error.retryable = retryable;
  return error;
}

function githubArchiveStatusIsRetryable(statusCode) {
  return statusCode === 408 || statusCode === 425 || statusCode === 429 || statusCode >= 500;
}

function sleep(ms) {
  if (ms <= 0) {
    return Promise.resolve();
  }
  return new Promise((resolvePromise) => setTimeout(resolvePromise, ms));
}

function downloadGithubArchiveAttempt(repo, ref, options) {
  const url = githubArchiveUrl(repo, ref);
  return new Promise((resolvePromise, rejectPromise) => {
    let settled = false;
    const fail = (error) => {
      if (settled) {
        return;
      }
      settled = true;
      rejectPromise(error);
    };
    const request = https.get(url, { timeout: options.timeoutMs }, (response) => {
      response.on("error", (error) => {
        if (error && error.retryable !== undefined && error.message.startsWith("Failed to download GitHub source archive ")) {
          fail(error);
          return;
        }
        fail(githubArchiveDownloadError(repo, ref, error.message, true));
      });
      if (response.statusCode < 200 || response.statusCode >= 300) {
        response.resume();
        fail(githubArchiveDownloadError(
          repo,
          ref,
          `HTTP ${response.statusCode}`,
          githubArchiveStatusIsRetryable(response.statusCode),
        ));
        return;
      }
      const contentLength = Number(response.headers && response.headers["content-length"]);
      if (Number.isFinite(contentLength) && contentLength > options.maxBytes) {
        const error = githubArchiveDownloadError(repo, ref, `archive exceeds ${options.maxBytes} byte limit`);
        fail(error);
        if (typeof response.destroy === "function") {
          response.destroy(error);
        } else {
          request.destroy(error);
        }
        return;
      }
      const chunks = [];
      let downloadedBytes = 0;
      response.on("data", (chunk) => {
        if (settled) {
          return;
        }
        downloadedBytes += chunk.length;
        if (downloadedBytes > options.maxBytes) {
          const error = githubArchiveDownloadError(repo, ref, `archive exceeds ${options.maxBytes} byte limit`);
          fail(error);
          if (typeof response.destroy === "function") {
            response.destroy(error);
          } else {
            request.destroy(error);
          }
          return;
        }
        chunks.push(chunk);
      });
      response.on("end", () => {
        if (settled) {
          return;
        }
        settled = true;
        resolvePromise(Buffer.concat(chunks, downloadedBytes));
      });
    });
    request.on("timeout", () => {
      request.destroy(githubArchiveDownloadError(repo, ref, "timeout", true));
    });
    request.on("error", (error) => {
      if (error && error.retryable !== undefined && error.message.startsWith("Failed to download GitHub source archive ")) {
        fail(error);
        return;
      }
      fail(githubArchiveDownloadError(repo, ref, error.message, Boolean(error.retryable)));
    });
  });
}

async function downloadGithubArchive(repo, ref, options = {}) {
  const safeRepo = validateGithubRepo(repo);
  const safeRef = validateGithubRef(ref);
  const maxBytes = options.maxBytes === undefined ? githubArchiveMaxBytes : options.maxBytes;
  const maxAttempts = options.maxAttempts === undefined ? githubArchiveMaxAttempts : options.maxAttempts;
  const retryDelayMs = options.retryDelayMs === undefined ? 250 : options.retryDelayMs;
  const timeoutMs = options.timeoutMs === undefined ? 60_000 : options.timeoutMs;
  if (!Number.isSafeInteger(maxBytes) || maxBytes <= 0) {
    throw new Error("GitHub archive maxBytes must be a positive safe integer");
  }
  if (!Number.isSafeInteger(maxAttempts) || maxAttempts <= 0) {
    throw new Error("GitHub archive maxAttempts must be a positive safe integer");
  }
  let lastError = null;
  for (let attempt = 1; attempt <= maxAttempts; attempt += 1) {
    try {
      return await downloadGithubArchiveAttempt(safeRepo, safeRef, { maxBytes, timeoutMs });
    } catch (error) {
      lastError = error;
      if (!error.retryable || attempt === maxAttempts) {
        throw error;
      }
      await sleep(retryDelayMs * 2 ** (attempt - 1));
    }
  }
  throw lastError;
}

function canonicalSourceMetadata(payload, binding, context) {
  const canonicalDirValue = payload.canonical_dir;
  const canonicalPaths = stringList(payload.canonical_paths);
  if (typeof canonicalDirValue !== "string" || canonicalPaths === null) {
    throw new Error(`payload canonical_dir and canonical_paths must be defined for skill ${binding.skillId}`);
  }
  const canonicalDir = normalizeRelativePath(
    canonicalDirValue,
    "payload canonical_dir",
    binding.skillId,
    "repository root",
  );
  const canonicalFiles = new Map();
  const includedPaths = [];
  for (const canonicalPath of canonicalPaths) {
    const normalizedCanonicalPath = normalizeRelativePath(
      canonicalPath,
      "payload canonical_paths entry",
      binding.skillId,
      "repository root",
    );
    const relativePath = relative(
      join(context.sourceRoot, canonicalDir),
      join(context.sourceRoot, normalizedCanonicalPath),
    ).split(sep).join("/");
    if (relativePath === "" || relativePath.startsWith("..") || isAbsolute(relativePath)) {
      throw new Error(
        `payload canonical_paths entry must stay within canonical_dir for skill ${binding.skillId}: ${canonicalPath}`,
      );
    }
    if (canonicalFiles.has(relativePath)) {
      throw new Error(
        `payload canonical_paths contain duplicate target-relative file ${relativePath} for skill ${binding.skillId}`,
      );
    }
    includedPaths.push(relativePath);
    canonicalFiles.set(relativePath, join(context.sourceRoot, normalizedCanonicalPath));
  }
  return { canonicalDir, includedPaths, canonicalFiles };
}

function verifySourceBinding(binding, context, loadedPayloads = null) {
  const issues = [];
  const backend = context.backend || agentsBackend;
  if (!isDirectory(binding.payloadDir)) {
    return [
      issue(
        "missing-backend-payload-source",
        binding.payloadDir,
        `missing backend payload source for skill ${binding.skillId}`,
      ),
    ];
  }

  let payload;
  try {
    payload = bindingPayloadObject(binding, loadedPayloads);
  } catch (error) {
    return [issue("payload-contract-invalid", binding.payloadPath, error.message)];
  }

  let canonicalSource = null;
  try {
    canonicalSource = canonicalSourceMetadata(payload, binding, context);
  } catch (error) {
    issues.push(issue("payload-contract-invalid", binding.payloadPath, error.message));
  }

  const canonicalDir = join(
    context.sourceRoot,
    canonicalSource === null ? String(payload.canonical_dir || "") : canonicalSource.canonicalDir,
  );
  if (!isDirectory(canonicalDir)) {
    issues.push(issue("missing-canonical-source", canonicalDir, `missing canonical directory for skill ${binding.skillId}`));
  }
  if (canonicalSource !== null && canonicalSource.canonicalDir.split("/").at(-1) !== binding.skillId) {
    issues.push(
      issue(
        "payload-contract-invalid",
        binding.payloadPath,
        `payload canonical_dir must end with ${binding.skillId} for skill ${binding.skillId}`,
      ),
    );
  }
  if (canonicalSource !== null) {
    for (const [includedPath, canonicalFile] of canonicalSource.canonicalFiles) {
      if (!isFile(canonicalFile)) {
        issues.push(
          issue("missing-canonical-source", canonicalFile, `missing canonical file ${includedPath} for skill ${binding.skillId}`),
        );
      }
    }
  }

  const expectedPayloadVersion = expectedPayloadVersions[backend];
  if (payload.payload_version !== expectedPayloadVersion) {
    issues.push(
      issue(
        "payload-contract-invalid",
        binding.payloadPath,
        `payload payload_version must be ${expectedPayloadVersion} for backend ${backend} skill ${binding.skillId}`,
      ),
    );
  }
  if (payload.backend !== backend) {
    issues.push(
      issue(
        "payload-contract-invalid",
        binding.payloadPath,
        `payload backend must be ${backend} for skill ${binding.skillId}`,
      ),
    );
  }
  if (payload.skill_id !== binding.skillId) {
    issues.push(issue("payload-contract-invalid", binding.payloadPath, `payload skill_id must be ${binding.skillId}`));
  }

  try {
    const targetMetadata = payloadTargetMetadata(payload, binding);
    const expectedRequiredFiles = [
      ...(canonicalSource === null ? [] : canonicalSource.includedPaths),
      payloadDescriptor,
      managedSkillMarker,
    ];
    if (JSON.stringify(targetMetadata.requiredPayloadFiles) !== JSON.stringify(expectedRequiredFiles)) {
      issues.push(
        issue(
          "payload-contract-invalid",
          binding.payloadPath,
          `payload required_payload_files must equal payload canonical_paths plus ${payloadDescriptor} and ${managedSkillMarker} for skill ${binding.skillId}`,
        ),
      );
    }
  } catch (error) {
    issues.push(issue("payload-contract-invalid", binding.payloadPath, error.message));
  }

  if (payload.payload_policy !== "canonical-copy") {
    issues.push(
      issue(
        "payload-policy-mismatch",
        binding.payloadPath,
        `payload_policy must be canonical-copy for backend ${backend} skill ${binding.skillId}`,
      ),
    );
  }
  if (payload.reference_distribution !== "copy-listed-canonical-paths") {
    issues.push(
      issue(
        "reference-policy-mismatch",
        binding.payloadPath,
        `reference_distribution must be copy-listed-canonical-paths for backend ${backend} skill ${binding.skillId}`,
      ),
    );
  }

  return issues;
}

function loadRuntimeMarker(markerPath) {
  if (!isFile(markerPath)) {
    return null;
  }
  let marker;
  try {
    marker = readJsonObject(markerPath);
  } catch (error) {
    return null;
  }
  const expectedKeys = [
    "backend",
    "marker_version",
    "payload_fingerprint",
    "payload_version",
    "skill_id",
  ];
  if (JSON.stringify(Object.keys(marker).sort()) !== JSON.stringify(expectedKeys)) {
    return null;
  }
  if (
    marker.marker_version !== managedSkillMarkerVersion ||
    typeof marker.backend !== "string" ||
    typeof marker.skill_id !== "string" ||
    typeof marker.payload_version !== "string" ||
    typeof marker.payload_fingerprint !== "string"
  ) {
    return null;
  }
  return marker;
}

function sourcePathForTargetRelativeFile(binding, relativeName, context, payload, canonicalSource = null) {
  if (relativeName === payloadDescriptor) {
    return binding.payloadPath;
  }
  if (relativeName === managedSkillMarker) {
    throw new Error(`${managedSkillMarker} is runtime-generated for skill ${binding.skillId}`);
  }
  const resolvedCanonicalSource = canonicalSource || canonicalSourceMetadata(payload, binding, context);
  const sourcePath = resolvedCanonicalSource.canonicalFiles.get(relativeName);
  if (sourcePath === undefined) {
    throw new Error(
      `payload required file ${relativeName} is not declared in payload canonical_paths for skill ${binding.skillId}`,
    );
  }
  return sourcePath;
}

function claudeFrontmatterOverrides(payload, binding) {
  if (payload.claude_frontmatter === undefined) {
    return {};
  }
  if (payload.claude_frontmatter === null || Array.isArray(payload.claude_frontmatter) || typeof payload.claude_frontmatter !== "object") {
    throw new Error(`payload claude_frontmatter must be an object for skill ${binding.skillId}`);
  }
  const overrides = {};
  for (const [key, value] of Object.entries(payload.claude_frontmatter)) {
    if (key === "") {
      throw new Error(`payload claude_frontmatter keys must be non-empty strings for skill ${binding.skillId}`);
    }
    if (typeof value !== "boolean") {
      throw new Error(`payload claude_frontmatter values must be booleans for skill ${binding.skillId}`);
    }
    overrides[key] = value;
  }
  return overrides;
}

function renderFrontmatterValue(value) {
  return value ? "true" : "false";
}

function frontmatterKey(line) {
  const match = /^([A-Za-z0-9_-]+)\s*:/.exec(line);
  return match === null ? "" : match[1];
}

function applyMarkdownFrontmatterOverrides(sourceText, overrides) {
  const entries = Object.entries(overrides);
  if (entries.length === 0) {
    return sourceText;
  }

  const lines = sourceText.match(/[^\n]*\n|[^\n]+$/g) || [];
  if (lines.length > 0 && lines[0].trim() === "---") {
    let closingIndex = -1;
    for (let index = 1; index < lines.length; index += 1) {
      if (lines[index].trim() === "---") {
        closingIndex = index;
        break;
      }
    }
    if (closingIndex !== -1) {
      const seenKeys = new Set();
      const updatedFrontmatter = [];
      for (const line of lines.slice(1, closingIndex)) {
        const key = frontmatterKey(line);
        if (Object.prototype.hasOwnProperty.call(overrides, key)) {
          updatedFrontmatter.push(`${key}: ${renderFrontmatterValue(overrides[key])}\n`);
          seenKeys.add(key);
        } else {
          updatedFrontmatter.push(line);
        }
      }
      for (const [key, value] of entries) {
        if (!seenKeys.has(key)) {
          updatedFrontmatter.push(`${key}: ${renderFrontmatterValue(value)}\n`);
        }
      }
      return [lines[0], ...updatedFrontmatter, ...lines.slice(closingIndex)].join("");
    }
  }

  return [
    "---\n",
    ...entries.map(([key, value]) => `${key}: ${renderFrontmatterValue(value)}\n`),
    "---\n",
    sourceText,
  ].join("");
}

function targetFrontmatterOverrides(binding, relativeName, metadata, payload) {
  if (relativeName !== metadata.targetEntryName || binding.backend !== claudeBackend) {
    return {};
  }
  return claudeFrontmatterOverrides(payload, binding);
}

function expectedTargetFileText(binding, relativeName, context, payload, sourcePath) {
  const sourceText = readFileSync(sourcePath, "utf8");
  const metadata = payloadTargetMetadata(payload, binding);
  const overrides = targetFrontmatterOverrides(binding, relativeName, metadata, payload);
  return applyMarkdownFrontmatterOverrides(sourceText, overrides);
}

function computePayloadFingerprint(binding, context, payload, payloadText, metadata) {
  if (typeof payload.payload_version !== "string") {
    throw new Error(`payload payload_version must be a string for skill ${binding.skillId}`);
  }
  const fingerprintParts = [
    `backend=${binding.backend}\nskill_id=${binding.skillId}\npayload_version=${payload.payload_version}\n`,
  ];
  let canonicalSource = null;
  for (const relativeName of metadata.requiredPayloadFiles) {
    if (relativeName === managedSkillMarker || relativeName === payloadDescriptor) {
      continue;
    }
    if (canonicalSource === null) {
      canonicalSource = canonicalSourceMetadata(payload, binding, context);
    }
    const sourcePath = sourcePathForTargetRelativeFile(
      binding,
      relativeName,
      context,
      payload,
      canonicalSource,
    );
    let sourceText;
    try {
      sourceText = readFileSync(sourcePath, "utf8");
    } catch (error) {
      if (error.code === "ENOENT") {
        throw new Error(`Missing payload source file while computing fingerprint: ${sourcePath}`);
      }
      throw error;
    }
    fingerprintParts.push(`file:${relativeName}\n${sourceText}\n`);
  }
  fingerprintParts.push(`file:${payloadDescriptor}\n${payloadText}\n`);
  return createHash("sha256").update(fingerprintParts.join(""), "utf8").digest("hex");
}

function runtimeMarkerText(marker) {
  return `${JSON.stringify(
    {
      marker_version: marker.marker_version,
      backend: marker.backend,
      skill_id: marker.skill_id,
      payload_version: marker.payload_version,
      payload_fingerprint: marker.payload_fingerprint,
    },
    null,
    2,
  )}\n`;
}

function buildRuntimeMarker(backend, skillId, payloadVersion, payloadFingerprint) {
  return {
    marker_version: managedSkillMarkerVersion,
    backend,
    skill_id: skillId,
    payload_version: payloadVersion,
    payload_fingerprint: payloadFingerprint,
  };
}

function targetRootChildren(targetRoot, action = "verify target root") {
  try {
    return readdirSync(targetRoot, { withFileTypes: true })
      .map((entry) => join(targetRoot, entry.name))
      .sort();
  } catch (error) {
    throw new Error(`Failed to scan ${action} at ${targetRoot}: ${error.message}`);
  }
}

function targetRootIdentity(path) {
  let stat;
  try {
    stat = lstatSync(path);
  } catch (error) {
    if (error.code === "ENOENT") {
      throw new Error(`Target root does not exist: ${path}`);
    }
    throw error;
  }
  if (stat.isSymbolicLink()) {
    if (existsSync(path)) {
      throw new Error(`Target root must be a real directory, not a symlink: ${path}`);
    }
    throw new Error(`Target root is a broken symlink: ${path}`);
  }
  if (!stat.isDirectory()) {
    throw new Error(`Target root exists but is not a directory: ${path}`);
  }
  return { path, dev: stat.dev, ino: stat.ino };
}

function assertDirectoryIdentityCurrent(identity, action) {
  let stat;
  try {
    stat = lstatSync(identity.path);
  } catch (error) {
    if (error.code === "ENOENT") {
      throw new Error(`Target root changed during ${action}, refusing to continue: ${identity.path}`);
    }
    throw error;
  }
  if (stat.dev !== identity.dev || stat.ino !== identity.ino || stat.isSymbolicLink() || !stat.isDirectory()) {
    throw new Error(`Target root changed during ${action}, refusing to continue: ${identity.path}`);
  }
}

function ensureInstallTargetRoot(path) {
  if (pathExists(path) || lstatOrNull(path)?.isSymbolicLink()) {
    const identity = targetRootIdentity(path);
    console.log(`ready target root ${path}`);
    return identity;
  }
  try {
    mkdirSync(dirname(path), { recursive: true, mode: deployedDirMode });
    mkdirSync(path, { mode: deployedDirMode });
  } catch (error) {
    if (error.code === "EEXIST") {
      const identity = targetRootIdentity(path);
      console.log(`ready target root ${path}`);
      return identity;
    }
    throw new Error(`Target root could not be created: ${path}: ${error.message}`);
  }
  const identity = targetRootIdentity(path);
  console.log(`created target root ${path}`);
  return identity;
}

/**
 * Resolves each binding target metadata and rejects duplicate live target dirs.
 */
function collectTargetDirMetadata(bindings, loadedPayloads = null) {
  const targetDirs = new Set();
  const metadataByPayloadPath = new Map();
  for (const binding of bindings) {
    const metadata = payloadTargetMetadata(bindingPayloadObject(binding, loadedPayloads), binding);
    if (targetDirs.has(metadata.targetDir)) {
      throw new Error(`Multiple skills map to the same target_dir for backend ${binding.backend}: ${metadata.targetDir}`);
    }
    targetDirs.add(metadata.targetDir);
    metadataByPayloadPath.set(binding.payloadPath, metadata);
  }
  return { targetDirs, metadataByPayloadPath };
}

function expectedTargetDirs(bindings, loadedPayloads = null) {
  return collectTargetDirMetadata(bindings, loadedPayloads).targetDirs;
}

function knownTargetDirsFromMetadata(bindings, metadataByPayloadPath) {
  const knownTargetDirs = new Set();
  for (const binding of bindings) {
    const metadata = metadataByPayloadPath.get(binding.payloadPath);
    knownTargetDirs.add(metadata.targetDir);
    for (const legacyTargetDir of metadata.legacyTargetDirs) {
      knownTargetDirs.add(legacyTargetDir);
    }
  }
  return knownTargetDirs;
}

/**
 * Collects live and legacy target dir names that update may recognize.
 */
function collectAllKnownTargetDirs(bindings, loadedPayloads = null) {
  const { metadataByPayloadPath } = collectTargetDirMetadata(bindings, loadedPayloads);
  return knownTargetDirsFromMetadata(bindings, metadataByPayloadPath);
}

function loadDeployedSkillState(binding, targetRoot, context, loadedPayloads) {
  try {
    const loadedPayload = bindingPayloadWithText(binding, loadedPayloads);
    const payload = loadedPayload.payload;
    const metadata = payloadTargetMetadata(payload, binding);
    return {
      payload,
      metadata,
      payloadFingerprint: computePayloadFingerprint(
        binding,
        context,
        payload,
        loadedPayload.payloadText,
        metadata,
      ),
      targetSkillDir: join(targetRoot, metadata.targetDir),
    };
  } catch (error) {
    return {
      issues: [issue("payload-contract-invalid", binding.payloadPath, error.message)],
    };
  }
}

function verifyDeployedSkillDirectory(binding, targetSkillDir) {
  if (!pathExists(targetSkillDir)) {
    return [
      issue(
        "missing-target-entry",
        targetSkillDir,
        `missing deployed skill directory for skill ${binding.skillId}`,
      ),
    ];
  }
  if (!isDirectory(targetSkillDir)) {
    return [
      issue(
        "wrong-target-entry-type",
        targetSkillDir,
        `deployed skill directory must be a real directory for skill ${binding.skillId}`,
      ),
    ];
  }
  return [];
}

function verifyDeployedMarker(binding, targetSkillDir, payload, payloadFingerprint) {
  const marker = loadRuntimeMarker(join(targetSkillDir, managedSkillMarker));
  if (marker === null) {
    return {
      fatalIssues: [
        issue(
          "unrecognized-target-directory",
          targetSkillDir,
          `existing deployed directory has no recognized ${managedSkillMarker}`,
        ),
      ],
    };
  }
  if (marker.backend !== binding.backend || marker.skill_id !== binding.skillId || marker.payload_version !== payload.payload_version) {
    return {
      fatalIssues: [
        issue(
          "unrecognized-target-directory",
          targetSkillDir,
          `recognized ${managedSkillMarker} does not match current backend/skill/payload_version`,
        ),
      ],
    };
  }

  const issues = [];
  const expectedMarker = {
    marker_version: managedSkillMarkerVersion,
    backend: binding.backend,
    skill_id: binding.skillId,
    payload_version: payload.payload_version,
    payload_fingerprint: payloadFingerprint,
  };
  const markerMatchesSource = marker.payload_fingerprint === payloadFingerprint;
  if (!markerMatchesSource) {
    issues.push(
      issue(
        "target-payload-drift",
        join(targetSkillDir, managedSkillMarker),
        `deployed payload fingerprint drifted from adapter source for skill ${binding.skillId}`,
      ),
    );
  }
  return {
    expectedMarker,
    issues,
    markerMatchesSource,
  };
}

function targetPayloadReadIssue(error, targetPath, relativeName, binding) {
  if (error.code === "ENOENT") {
    return issue(
      "missing-required-payload",
      targetPath,
      `missing deployed payload file ${relativeName} for skill ${binding.skillId}`,
    );
  }
  if (error.code === "ENOTREG" || error.code === "EISDIR") {
    return issue(
      "wrong-target-entry-type",
      targetPath,
      `deployed payload file ${relativeName} must be a real file for skill ${binding.skillId}`,
    );
  }
  return issue(
    "target-payload-drift",
    targetPath,
    `could not read deployed payload file ${relativeName} for skill ${binding.skillId}: ${error.message}`,
  );
}

function verifyDeployedPayloadFiles(binding, targetSkillDir, context, payload, metadata, markerState) {
  const issues = [];
  let canonicalSource = null;
  for (const relativeName of metadata.requiredPayloadFiles) {
    const targetPath = join(targetSkillDir, relativeName);
    if (!pathExists(targetPath)) {
      issues.push(
        issue(
          "missing-required-payload",
          targetPath,
          `missing deployed payload file ${relativeName} for skill ${binding.skillId}`,
        ),
      );
      continue;
    }
    if (!isFile(targetPath)) {
      issues.push(
        issue(
          "wrong-target-entry-type",
          targetPath,
          `deployed payload file ${relativeName} must be a real file for skill ${binding.skillId}`,
        ),
      );
      continue;
    }
    if (relativeName === managedSkillMarker) {
      let markerText;
      try {
        markerText = readRegularFileText(targetPath);
      } catch (error) {
        issues.push(targetPayloadReadIssue(error, targetPath, relativeName, binding));
        continue;
      }
      if (markerState.markerMatchesSource && markerText !== runtimeMarkerText(markerState.expectedMarker)) {
        issues.push(
          issue(
            "target-payload-drift",
            targetPath,
            `deployed payload file ${relativeName} drifted from adapter source for skill ${binding.skillId}`,
          ),
        );
      }
      continue;
    }
    let sourcePath;
    try {
      if (relativeName !== payloadDescriptor && canonicalSource === null) {
        canonicalSource = canonicalSourceMetadata(payload, binding, context);
      }
      sourcePath =
        relativeName === payloadDescriptor
          ? binding.payloadPath
          : sourcePathForTargetRelativeFile(binding, relativeName, context, payload, canonicalSource);
    } catch (error) {
      issues.push(issue("payload-contract-invalid", binding.payloadPath, error.message));
      continue;
    }
    let sourceText;
    let targetText;
    try {
      sourceText = expectedTargetFileText(binding, relativeName, context, payload, sourcePath);
    } catch (error) {
      issues.push(issue("payload-contract-invalid", binding.payloadPath, error.message));
      continue;
    }
    try {
      targetText = readRegularFileText(targetPath);
    } catch (error) {
      issues.push(targetPayloadReadIssue(error, targetPath, relativeName, binding));
      continue;
    }
    if (sourceText !== targetText) {
      issues.push(
        issue(
          "target-payload-drift",
          targetPath,
          `deployed payload file ${relativeName} drifted from adapter source for skill ${binding.skillId}`,
        ),
      );
    }
  }
  return issues;
}

function verifyDeployedTargetEntry(binding, targetSkillDir, metadata) {
  const targetEntry = join(targetSkillDir, metadata.targetEntryName);
  if (!pathExists(targetEntry)) {
    return [
      issue(
        "missing-target-entry",
        targetEntry,
        `missing target entry ${metadata.targetEntryName} for skill ${binding.skillId}`,
      ),
    ];
  }
  if (!isFile(targetEntry)) {
    return [
      issue(
        "wrong-target-entry-type",
        targetEntry,
        `target entry ${metadata.targetEntryName} must be a real file for skill ${binding.skillId}`,
      ),
    ];
  }
  return [];
}

function verifyDeployedSkill(binding, targetRoot, context, loadedPayloads = null) {
  const state = loadDeployedSkillState(binding, targetRoot, context, loadedPayloads);
  if (state.issues) {
    return state.issues;
  }

  const directoryIssues = verifyDeployedSkillDirectory(binding, state.targetSkillDir);
  if (directoryIssues.length > 0) {
    return directoryIssues;
  }

  const markerState = verifyDeployedMarker(
    binding,
    state.targetSkillDir,
    state.payload,
    state.payloadFingerprint,
  );
  if (markerState.fatalIssues) {
    return markerState.fatalIssues;
  }

  return [
    ...markerState.issues,
    ...verifyDeployedPayloadFiles(
      binding,
      state.targetSkillDir,
      context,
      state.payload,
      state.metadata,
      markerState,
    ),
    ...verifyDeployedTargetEntry(binding, state.targetSkillDir, state.metadata),
  ];
}

function unexpectedManagedTargetDirs(targetRoot, expectedTargetDirNames, targetChildren, backend = agentsBackend) {
  if (!isDirectory(targetRoot)) {
    return [];
  }
  const issues = [];
  for (const child of targetChildren) {
    const stat = lstatOrNull(child);
    if (stat === null || stat.isSymbolicLink() || !stat.isDirectory()) {
      continue;
    }
    if (expectedTargetDirNames.has(child.split(/[\\/]/).at(-1))) {
      continue;
    }
    const marker = loadRuntimeMarker(join(child, managedSkillMarker));
    if (marker === null || marker.backend !== backend) {
      continue;
    }
    issues.push(
      issue(
        "unexpected-managed-directory",
        child,
        `recognized managed install for skill ${marker.skill_id} is not part of the current source bindings`,
      ),
    );
  }
  return issues;
}

/**
 * Verifies the agents backend using optional pre-collected bindings/payloads.
 */
function verifyBackend(context, options = {}) {
  const backend = context.backend || agentsBackend;
  const targetRoot = context.targetRoot;
  const issues = verifyTargetRoot(targetRoot, backend);
  const bindings = options.bindings ?? collectSkillBindings(context);
  const loadedPayloads = options.loadedPayloads ?? null;
  const collectTargetChildrenOnIssue = options.collectTargetChildrenOnIssue === true;
  if (bindings.length === 0) {
    issues.push(
      issue(
        "missing-backend-payload-source",
        context.adapterSkillsDir,
        `No payload bindings found for backend ${backend}.`,
      ),
    );
  } else {
    for (const binding of bindings) {
      issues.push(...verifySourceBinding(binding, context, loadedPayloads));
    }
  }

  let expectedTargetDirNames = new Set();
  if (issues.length === 0) {
    try {
      expectedTargetDirNames = expectedTargetDirs(bindings, loadedPayloads);
    } catch (error) {
      issues.push(issue("payload-contract-invalid", context.adapterSkillsDir, error.message));
    }
  }

  let children = null;
  if ((issues.length === 0 || collectTargetChildrenOnIssue) && isDirectory(targetRoot)) {
    children = targetRootChildren(targetRoot);
  }
  if (issues.length === 0 && children !== null) {
    for (const binding of bindings) {
      issues.push(...verifyDeployedSkill(binding, targetRoot, context, loadedPayloads));
    }
    issues.push(...unexpectedManagedTargetDirs(targetRoot, expectedTargetDirNames, children, backend));
  }

  return {
    backend,
    sourceRoot: context.sourceRoot,
    targetRoot,
    issues,
    bindings,
    targetChildren: children,
  };
}

function verifyAgentsBackend(context, options = {}) {
  return verifyBackend(context, options);
}

function targetRootStatus(path) {
  const stat = lstatOrNull(path);
  if (stat === null) {
    return "missing";
  }
  if (stat.isSymbolicLink()) {
    return existsSync(path) ? "symlink" : "broken-symlink";
  }
  if (stat.isDirectory()) {
    return "directory";
  }
  return "wrong-type";
}

function managedInstallDirs(targetRoot, targetChildren, backend = agentsBackend) {
  if (!isDirectory(targetRoot)) {
    return [];
  }
  const children = targetChildren === null ? targetRootChildren(targetRoot) : targetChildren;
  return children.filter((child) => {
    const stat = lstatOrNull(child);
    if (stat === null || stat.isSymbolicLink() || !stat.isDirectory()) {
      return false;
    }
    const marker = loadRuntimeMarker(join(child, managedSkillMarker));
    return marker !== null && marker.backend === backend;
  });
}

function targetRootReadyIssuesForAction(targetRoot, backend = agentsBackend) {
  return verifyTargetRoot(targetRoot, backend).filter((currentIssue) => currentIssue.code !== "missing-target-root");
}

function childDirectoryIdentity(path) {
  const stat = lstatOrNull(path);
  if (stat === null || stat.isSymbolicLink() || !stat.isDirectory()) {
    return null;
  }
  return { path, dev: stat.dev, ino: stat.ino };
}

function assertManagedDirectoryIdentityCurrent(identity) {
  const stat = lstatOrNull(identity.path);
  if (stat === null) {
    return false;
  }
  if (stat.dev !== identity.dev || stat.ino !== identity.ino || stat.isSymbolicLink() || !stat.isDirectory()) {
    throw new Error(`Managed skill dir changed during pruning, refusing to remove: ${identity.path}`);
  }
  return true;
}

function pruneBackendManagedInstalls(context) {
  const targetRootIssues = targetRootReadyIssuesForAction(context.targetRoot, context.backend);
  if (targetRootIssues.length > 0) {
    throw new Error(targetRootReadyFailureMessage("prune managed installs", targetRootIssues));
  }

  if (!pathExists(context.targetRoot)) {
    console.log(`no managed skill dirs found at ${context.targetRoot}`);
    return 0;
  }

  let removedCount = 0;
  for (const child of targetRootChildren(context.targetRoot, "managed install pruning")) {
    const identity = childDirectoryIdentity(child);
    if (identity === null) {
      continue;
    }

    const marker = loadRuntimeMarker(join(child, managedSkillMarker));
    if (marker === null || marker.backend !== context.backend) {
      continue;
    }

    if (!assertManagedDirectoryIdentityCurrent(identity)) {
      continue;
    }

    try {
      rmSync(child, { recursive: true });
    } catch (error) {
      throw new Error(`Failed to remove managed skill dir ${child}: ${error.message}`);
    }
    removedCount += 1;
    console.log(`removed managed skill dir ${child}`);
  }

  if (removedCount === 0) {
    console.log(`no managed skill dirs found at ${context.targetRoot}`);
  }
  return removedCount;
}

/**
 * Finds existing target entries that update must refuse or classify before prune.
 */
function collectUpdateTargetEntryIssues(targetRoot, knownTargetDirNames, targetChildren, backend = agentsBackend) {
  if (!isDirectory(targetRoot)) {
    return [];
  }
  const children = targetChildren === null ? targetRootChildren(targetRoot) : targetChildren;
  const issues = [];
  for (const child of children) {
    const childName = child.split(/[\\/]/).at(-1);
    if (!knownTargetDirNames.has(childName)) {
      continue;
    }

    const stat = lstatOrNull(child);
    if (stat === null || stat.isSymbolicLink() || !stat.isDirectory()) {
      issues.push(
        issue(
          "wrong-target-entry-type",
          child,
          "update target path must be a real directory before reinstall",
        ),
      );
      continue;
    }

    const marker = loadRuntimeMarker(join(child, managedSkillMarker));
    if (marker === null) {
      issues.push(
        issue(
          "unrecognized-target-directory",
          child,
          "update will not remove target directories without a recognized marker",
        ),
      );
      continue;
    }

    if (marker.backend !== backend) {
      issues.push(
        issue(
          "foreign-managed-directory",
          child,
          `update will not remove managed directory for backend ${marker.backend}`,
        ),
      );
    }
  }
  return issues;
}

function pathExistsOrIsSymlink(path) {
  return lstatOrNull(path) !== null;
}

function describeExistingTargetPath(path) {
  const stat = lstatOrNull(path);
  if (stat === null) {
    return "existing target path already exists";
  }
  if (stat.isSymbolicLink()) {
    return existsSync(path)
      ? "existing target path is a symlink"
      : "existing target path is a broken symlink";
  }
  if (stat.isDirectory()) {
    return "existing target path is a directory";
  }
  if (stat.isFile()) {
    return "existing target path is a file";
  }
  return "existing target path already exists";
}

function pathConflict(skillId, path, detail) {
  return { skillId, path, detail };
}

function collectPathConflicts(plans) {
  const conflicts = [];
  for (const plan of plans) {
    if (!pathExistsOrIsSymlink(plan.targetSkillDir)) {
      continue;
    }
    conflicts.push(
      pathConflict(
        plan.binding.skillId,
        plan.targetSkillDir,
        describeExistingTargetPath(plan.targetSkillDir),
      ),
    );
  }
  return conflicts;
}

function collectLegacyPathConflicts(plans, targetRoot) {
  const conflicts = [];
  for (const plan of plans) {
    for (const legacyDirName of plan.targetMetadata.legacyTargetDirs) {
      const legacyPath = join(targetRoot, legacyDirName);
      if (!pathExistsOrIsSymlink(legacyPath)) {
        continue;
      }
      const identity = childDirectoryIdentity(legacyPath);
      const marker = identity === null ? null : loadRuntimeMarker(join(legacyPath, managedSkillMarker));
      if (
        marker !== null &&
        marker.backend === plan.binding.backend &&
        (marker.skill_id === plan.binding.skillId ||
          plan.targetMetadata.legacySkillIds.includes(marker.skill_id))
      ) {
        continue;
      }
      conflicts.push(
        pathConflict(
          plan.binding.skillId,
          legacyPath,
          `legacy directory ${legacyDirName} is occupied by unmanaged content`,
        ),
      );
    }
  }
  return conflicts;
}

function legacyTargetDirMigrationSummary(plans, targetRoot) {
  const legacyManagedInstalls = [];
  const legacyBlocked = [];
  if (!isDirectory(targetRoot)) {
    return {
      legacy_target_dir_count: 0,
      legacy_target_dirs: legacyManagedInstalls,
      legacy_blocked_count: 0,
      legacy_blocked: legacyBlocked,
    };
  }
  for (const plan of plans) {
    for (const legacyDirName of plan.targetMetadata.legacyTargetDirs) {
      const legacyPath = join(targetRoot, legacyDirName);
      if (!pathExistsOrIsSymlink(legacyPath)) {
        continue;
      }
      const identity = childDirectoryIdentity(legacyPath);
      const marker = identity === null ? null : loadRuntimeMarker(join(legacyPath, managedSkillMarker));
      const item = {
        skill_id: plan.binding.skillId,
        legacy_dir: legacyDirName,
        legacy_path: legacyPath,
        target_dir: plan.targetMetadata.targetDir,
        target_path: join(targetRoot, plan.targetMetadata.targetDir),
      };
      if (
        marker !== null &&
        marker.backend === plan.binding.backend &&
        (marker.skill_id === plan.binding.skillId ||
          plan.targetMetadata.legacySkillIds.includes(marker.skill_id))
      ) {
        legacyManagedInstalls.push(item);
        continue;
      }
      legacyBlocked.push({
        ...item,
        reason: marker === null
          ? "legacy target path is not an installer-managed directory for this backend"
          : `legacy target path is managed for backend ${marker.backend} skill ${marker.skill_id}`,
      });
    }
  }
  return {
    legacy_target_dir_count: legacyManagedInstalls.length,
    legacy_target_dirs: legacyManagedInstalls,
    legacy_blocked_count: legacyBlocked.length,
    legacy_blocked: legacyBlocked,
  };
}

function formatPathConflicts(conflicts) {
  return [
    "target path conflicts:",
    ...conflicts.map((conflict) => `- ${conflict.skillId}: ${conflict.path} (${conflict.detail})`),
  ].join("\n");
}

function sourceValidationFailureMessage(action, issues) {
  const details = issues
    .map((currentIssue) => `  - ${currentIssue.code}: ${currentIssue.path} (${currentIssue.detail})`)
    .join("\n");
  return `Cannot ${action} because source validation failed:\n${details}`;
}

function targetRootReadyFailureMessage(action, issues) {
  const details = issues
    .map((currentIssue) => `  - ${currentIssue.code}: ${currentIssue.path} (${currentIssue.detail})`)
    .join("\n");
  return `Cannot ${action} because target root is not ready:\n${details}`;
}

function collectValidatedBindingsForAction(context, action) {
  const backend = context.backend || agentsBackend;
  const bindings = collectSkillBindings(context);
  if (bindings.length === 0) {
    throw new Error(`No payload bindings found for backend ${backend}.`);
  }

  const validationIssues = [];
  for (const binding of bindings) {
    validationIssues.push(...verifySourceBinding(binding, context));
  }
  if (validationIssues.length > 0) {
    throw new Error(sourceValidationFailureMessage(action, validationIssues));
  }
  const loadedPayloads = loadBindingPayloads(bindings);
  return { bindings, loadedPayloads };
}

function collectValidatedBindingsForCheckPaths(context) {
  return collectValidatedBindingsForAction(context, "check target paths");
}

function checkPathsExistSummary(context) {
  const backend = context.backend || agentsBackend;
  const { bindings, loadedPayloads } = collectValidatedBindingsForCheckPaths(context);
  const targetRootIssues = verifyTargetRoot(context.targetRoot, backend).filter(
    (currentIssue) => currentIssue.code !== "missing-target-root",
  );
  if (targetRootIssues.length > 0) {
    throw new Error(targetRootReadyFailureMessage("check target paths", targetRootIssues));
  }

  const targetMetadata = collectTargetDirMetadata(bindings, loadedPayloads);
  const plans = bindings.map((binding) =>
    buildInstallPlan(binding, context.targetRoot, context, {
      loadedPayloads,
      targetMetadata: targetMetadata.metadataByPayloadPath.get(binding.payloadPath),
    }),
  );
  const conflicts = [
    ...collectPathConflicts(plans),
    ...collectLegacyPathConflicts(plans, context.targetRoot),
  ];
  return {
    backend,
    targetRoot: context.targetRoot,
    plannedTargetPaths: plans.map((plan) => plan.targetSkillDir),
    conflicts,
  };
}

function writeDeployedTextFile(path, text) {
  writeFileSync(path, text, "utf8");
  if ((statSync(path).mode & 0o777) !== deployedFileMode) {
    chmodSync(path, deployedFileMode);
  }
}

function sourceTextForTargetRelativeFile(binding, relativeName, context, payload, loadedPayload, canonicalSource) {
  if (relativeName === payloadDescriptor) {
    return loadedPayload.payloadText;
  }
  const sourcePath = sourcePathForTargetRelativeFile(binding, relativeName, context, payload, canonicalSource);
  return expectedTargetFileText(binding, relativeName, context, payload, sourcePath);
}

function installBackendPayloads(context) {
  const { bindings, loadedPayloads } = collectValidatedBindingsForAction(context, "install");
  const targetRootIssues = verifyTargetRoot(context.targetRoot, context.backend).filter(
    (currentIssue) => currentIssue.code !== "missing-target-root",
  );
  if (targetRootIssues.length > 0) {
    throw new Error(targetRootReadyFailureMessage("install", targetRootIssues));
  }

  const targetMetadata = collectTargetDirMetadata(bindings, loadedPayloads);
  const plans = bindings.map((binding) =>
    buildInstallPlan(binding, context.targetRoot, context, {
      loadedPayloads,
      targetMetadata: targetMetadata.metadataByPayloadPath.get(binding.payloadPath),
    }),
  );
  const conflicts = [
    ...collectPathConflicts(plans),
    ...collectLegacyPathConflicts(plans, context.targetRoot),
  ];
  if (conflicts.length > 0) {
    throw new Error(
      `[${context.backend}] install blocked by ${conflicts.length} existing target path(s)\n\n${formatPathConflicts(conflicts)}`,
    );
  }

  const targetRootIdentitySnapshot = ensureInstallTargetRoot(context.targetRoot);
  for (const plan of plans) {
    const binding = plan.binding;
    for (const legacyDirName of plan.targetMetadata.legacyTargetDirs) {
      assertDirectoryIdentityCurrent(targetRootIdentitySnapshot, "install legacy cleanup");
      const legacyPath = join(context.targetRoot, legacyDirName);
      if (!pathExists(legacyPath)) {
        continue;
      }
      const identity = childDirectoryIdentity(legacyPath);
      if (identity === null) {
        continue;
      }
      const marker = loadRuntimeMarker(join(legacyPath, managedSkillMarker));
      if (
        marker !== null &&
        marker.backend === binding.backend &&
        (marker.skill_id === binding.skillId ||
          plan.targetMetadata.legacySkillIds.includes(marker.skill_id))
      ) {
        assertDirectoryIdentityCurrent(targetRootIdentitySnapshot, "install legacy cleanup");
        if (!assertManagedDirectoryIdentityCurrent(identity)) {
          continue;
        }
        try {
          rmSync(legacyPath, { recursive: true });
        } catch (error) {
          throw new Error(`Failed to remove legacy skill dir ${legacyPath}: ${error.message}`);
        }
        console.log(`removed legacy skill dir ${binding.skillId} -> ${legacyPath}`);
      }
    }
  }
  for (const plan of plans) {
    const binding = plan.binding;
    const loadedPayload = bindingPayloadWithText(binding, loadedPayloads);
    const payload = loadedPayload.payload;
    const targetSkillDir = plan.targetSkillDir;
    const targetMetadataForPlan = plan.targetMetadata;
    let canonicalSource = null;

    assertDirectoryIdentityCurrent(targetRootIdentitySnapshot, "install");
    mkdirSync(targetSkillDir, { mode: deployedDirMode });
    assertDirectoryIdentityCurrent(targetRootIdentitySnapshot, "install");
    chmodSync(targetSkillDir, deployedDirMode);

    for (const relativeName of targetMetadataForPlan.requiredPayloadFiles) {
      const targetPath = join(targetSkillDir, relativeName);
      assertDirectoryIdentityCurrent(targetRootIdentitySnapshot, "install");
      mkdirSync(dirname(targetPath), { recursive: true, mode: deployedDirMode });
      chmodSync(dirname(targetPath), deployedDirMode);
      assertDirectoryIdentityCurrent(targetRootIdentitySnapshot, "install");
      if (relativeName === managedSkillMarker) {
        writeDeployedTextFile(
          targetPath,
          runtimeMarkerText(
            buildRuntimeMarker(
              binding.backend,
              binding.skillId,
              payload.payload_version,
              plan.payloadFingerprint,
            ),
          ),
        );
        continue;
      }
      if (relativeName !== payloadDescriptor && canonicalSource === null) {
        canonicalSource = canonicalSourceMetadata(payload, binding, context);
      }
      writeDeployedTextFile(
        targetPath,
        sourceTextForTargetRelativeFile(binding, relativeName, context, payload, loadedPayload, canonicalSource),
      );
    }
    console.log(`installed skill ${binding.skillId} -> ${targetSkillDir}`);
  }
}

/**
 * Keeps the first issue for each code/path pair while preserving issue order.
 */
function dedupeIssues(issues) {
  const seen = new Set();
  const uniqueIssues = [];
  for (const currentIssue of issues) {
    const key = `${currentIssue.code}\0${currentIssue.path}`;
    if (seen.has(key)) {
      continue;
    }
    seen.add(key);
    uniqueIssues.push(currentIssue);
  }
  return uniqueIssues;
}

/**
 * Builds the dry-run install plan entry for one binding.
 */
function buildInstallPlan(binding, targetRoot, context, options = {}) {
  const loadedPayloads = options.loadedPayloads ?? null;
  const targetMetadata = options.targetMetadata ?? null;
  const includePayloadFingerprint = options.includePayloadFingerprint !== false;
  const resolvedTargetMetadata =
    targetMetadata || payloadTargetMetadata(bindingPayloadObject(binding, loadedPayloads), binding);
  const plan = {
    binding,
    targetMetadata: resolvedTargetMetadata,
    targetSkillDir: join(targetRoot, resolvedTargetMetadata.targetDir),
  };
  if (includePayloadFingerprint) {
    const loadedPayload = bindingPayloadWithText(binding, loadedPayloads);
    plan.payloadFingerprint = computePayloadFingerprint(
      binding,
      context,
      loadedPayload.payload,
      loadedPayload.payloadText,
      resolvedTargetMetadata,
    );
  }
  return plan;
}

/**
 * Classifies whether an issue should block the destructive reinstall wrapper.
 */
function isUpdateBlockingIssue(currentIssue, managedDeletePaths) {
  if (updateRecoverableIssueCodes.has(currentIssue.code)) {
    return false;
  }
  if (currentIssue.code === "unrecognized-target-directory" && managedDeletePaths.has(currentIssue.path)) {
    return false;
  }
  return true;
}

/**
 * Produces an update dry-run JSON summary without mutating target files.
 */
function updatePlanSummary(context) {
  const backend = context.backend || agentsBackend;
  const bindings = collectSkillBindings(context);
  let loadedPayloads = null;
  const preloadIssues = [];
  try {
    loadedPayloads = loadBindingPayloads(bindings);
  } catch (error) {
    preloadIssues.push(
      issue(
        "payload-contract-invalid",
        error.payloadPath || context.adapterSkillsDir,
        `failed to preload payloads: ${error.message}`,
      ),
    );
    loadedPayloads = null;
  }
  const result = verifyBackend(context, {
    bindings,
    loadedPayloads,
    collectTargetChildrenOnIssue: true,
  });
  const targetRoot = result.targetRoot;
  const targetChildren = result.targetChildren;

  const planIssues = [];
  let plans = [];
  let knownTargetDirNames = new Set();
  if (bindings.length === 0) {
    planIssues.push(
      issue(
        "missing-backend-payload-source",
        context.adapterSkillsDir,
        `No payload bindings found for backend ${backend}.`,
      ),
    );
  } else {
    try {
      const targetMetadata = collectTargetDirMetadata(bindings, loadedPayloads);
      knownTargetDirNames = knownTargetDirsFromMetadata(bindings, targetMetadata.metadataByPayloadPath);
      plans = bindings.map((binding) =>
        buildInstallPlan(binding, targetRoot, context, {
          loadedPayloads,
          targetMetadata: targetMetadata.metadataByPayloadPath.get(binding.payloadPath),
          includePayloadFingerprint: false,
        }),
      );
    } catch (error) {
      planIssues.push(issue("payload-contract-invalid", context.adapterSkillsDir, error.message));
    }
  }

  const targetEntryIssues = collectUpdateTargetEntryIssues(
    targetRoot,
    knownTargetDirNames,
    targetChildren,
    backend,
  );
  const legacyMigration = legacyTargetDirMigrationSummary(plans, targetRoot);
  const managedInstallsToDelete = managedInstallDirs(targetRoot, targetChildren, backend);
  const managedDeletePaths = new Set(managedInstallsToDelete);
  const allIssues = dedupeIssues([...result.issues, ...planIssues, ...targetEntryIssues, ...preloadIssues]);
  const blockingIssues = allIssues.filter((currentIssue) => isUpdateBlockingIssue(currentIssue, managedDeletePaths));

  return {
    backend,
    source_kind: context.sourceKind,
    source_ref: context.sourceRef,
    source_root: context.sourceRoot,
    target_root: targetRoot,
    operation_sequence: ["prune --all", "check_paths_exist", "install", "verify"],
    managed_installs_to_delete: managedInstallsToDelete,
    planned_target_paths: plans.map((plan) => plan.targetSkillDir),
    ...legacyMigration,
    upgrade_guidance: legacyMigration.legacy_target_dir_count > 0
      ? `Run servo-installer update --backend ${backend} --yes to replace legacy target dirs with current servo target dirs.`
      : null,
    issue_count: allIssues.length,
    issues: allIssues,
    blocking_issue_count: blockingIssues.length,
    blocking_issues: blockingIssues,
  };
}

function diagnosticSummary(result) {
  const backend = result.backend || agentsBackend;
  const managedDirs = managedInstallDirs(result.targetRoot, result.targetChildren, backend);
  let legacyMigration = {
    legacy_target_dir_count: 0,
    legacy_target_dirs: [],
    legacy_blocked_count: 0,
    legacy_blocked: [],
  };
  if (result.bindings.length > 0 && isDirectory(result.targetRoot)) {
    try {
      const loadedPayloads = loadBindingPayloads(result.bindings);
      const targetMetadata = collectTargetDirMetadata(result.bindings, loadedPayloads);
      const plans = result.bindings.map((binding) =>
        buildInstallPlan(binding, result.targetRoot, { sourceRoot: result.sourceRoot }, {
          loadedPayloads,
          targetMetadata: targetMetadata.metadataByPayloadPath.get(binding.payloadPath),
          includePayloadFingerprint: false,
        }),
      );
      legacyMigration = legacyTargetDirMigrationSummary(plans, result.targetRoot);
    } catch (_) {
      legacyMigration = {
        legacy_target_dir_count: 0,
        legacy_target_dirs: [],
        legacy_blocked_count: 0,
        legacy_blocked: [],
      };
    }
  }
  const issueCodes = [...new Set(result.issues.map((currentIssue) => currentIssue.code))].sort();
  const unrecognized = result.issues.filter((currentIssue) => unrecognizedIssueCodes.has(currentIssue.code));
  const conflicts = result.issues.filter((currentIssue) => conflictIssueCodes.has(currentIssue.code));
  return {
    backend,
    source_root: result.sourceRoot,
    target_root: result.targetRoot,
    target_root_status: targetRootStatus(result.targetRoot),
    target_root_exists: pathExists(result.targetRoot),
    binding_count: result.bindings.length,
    managed_install_count: managedDirs.length,
    managed_installs: managedDirs,
    ...legacyMigration,
    upgrade_guidance: legacyMigration.legacy_target_dir_count > 0
      ? `Run servo-installer update --backend ${backend} --yes to replace legacy target dirs with current servo target dirs.`
      : null,
    issue_count: result.issues.length,
    issue_codes: issueCodes,
    issues: result.issues,
    unrecognized_count: unrecognized.length,
    unrecognized,
    conflict_count: conflicts.length,
    conflicts,
  };
}

function sortJsonObjectKeys(value) {
  if (Array.isArray(value)) {
    return value.map((item) => sortJsonObjectKeys(item));
  }
  if (value === null || typeof value !== "object") {
    return value;
  }
  return Object.fromEntries(
    Object.keys(value)
      .sort()
      .map((key) => [key, sortJsonObjectKeys(value[key])]),
  );
}

function readOptionValue(args, index) {
  if (index + 1 >= args.length) {
    return null;
  }
  return args[index + 1];
}

function readEqualsOption(arg, flag) {
  const prefix = `${flag}=`;
  return arg.startsWith(prefix) ? arg.slice(prefix.length) : null;
}

function backendAllowed(backend, allowedBackends) {
  return allowedBackends.includes(backend);
}

function parsedBackendRoots(backend, agentsRoot, claudeRoot) {
  if (backend === bundleBackend) {
    return {
      backend,
      agentsRoot,
      ...(claudeRoot !== undefined ? { claudeRoot } : {}),
    };
  }
  return {
    backend,
    agentsRoot,
    ...(backend === claudeBackend && claudeRoot !== undefined ? { claudeRoot } : {}),
  };
}

function parsedGithubOptions(githubRepo, githubRef, githubArchiveSha256) {
  return {
    githubRepo: githubRepo === undefined ? defaultGithubSourceRepo() : githubRepo,
    githubRef: githubRef === undefined ? "master" : githubRef,
    ...(githubArchiveSha256 === undefined ? {} : { githubArchiveSha256 }),
  };
}

function parseNodeMigrateRuntimeArgs(args) {
  if (args[0] !== "migrate-runtime") {
    return null;
  }
  const parsed = {
    from: undefined,
    to: undefined,
    backend: agentsBackend,
    json: false,
    yes: false,
    reinstall: false,
    agentsRoot: undefined,
    claudeRoot: undefined,
  };
  for (let index = 1; index < args.length; index += 1) {
    const arg = args[index];
    if (arg === cliFlags.json) {
      parsed.json = true;
      continue;
    }
    if (arg === cliFlags.yes) {
      parsed.yes = true;
      continue;
    }
    if (arg === cliFlags.reinstall) {
      parsed.reinstall = true;
      continue;
    }
    if (arg === cliFlags.from) {
      const value = readOptionValue(args, index);
      if (value === null) {
        return null;
      }
      parsed.from = value;
      index += 1;
      continue;
    }
    const fromValue = readEqualsOption(arg, cliFlags.from);
    if (fromValue !== null) {
      parsed.from = fromValue;
      continue;
    }
    if (arg === cliFlags.to) {
      const value = readOptionValue(args, index);
      if (value === null) {
        return null;
      }
      parsed.to = value;
      index += 1;
      continue;
    }
    const toValue = readEqualsOption(arg, cliFlags.to);
    if (toValue !== null) {
      parsed.to = toValue;
      continue;
    }
    if (arg === cliFlags.backend) {
      const value = readOptionValue(args, index);
      if (value === null) {
        return null;
      }
      parsed.backend = value;
      index += 1;
      continue;
    }
    const backendValue = readEqualsOption(arg, cliFlags.backend);
    if (backendValue !== null) {
      parsed.backend = backendValue;
      continue;
    }
    if (arg === cliFlags.agentsRoot) {
      const value = readOptionValue(args, index);
      if (value === null) {
        return null;
      }
      parsed.agentsRoot = value;
      index += 1;
      continue;
    }
    const agentsRootValue = readEqualsOption(arg, cliFlags.agentsRoot);
    if (agentsRootValue !== null) {
      parsed.agentsRoot = agentsRootValue;
      continue;
    }
    if (arg === cliFlags.claudeRoot) {
      const value = readOptionValue(args, index);
      if (value === null) {
        return null;
      }
      parsed.claudeRoot = value;
      index += 1;
      continue;
    }
    const claudeRootValue = readEqualsOption(arg, cliFlags.claudeRoot);
    if (claudeRootValue !== null) {
      parsed.claudeRoot = claudeRootValue;
      continue;
    }
    return null;
  }
  if (parsed.from !== "aw" || parsed.to !== "servo" || (parsed.json && parsed.yes)) {
    return null;
  }
  if (!backendAllowed(parsed.backend, [agentsBackend, claudeBackend, bundleBackend])) {
    return null;
  }
  return {
    ...parsedBackendRoots(parsed.backend, parsed.agentsRoot, parsed.claudeRoot),
    from: parsed.from,
    to: parsed.to,
    json: parsed.json,
    yes: parsed.yes,
    reinstall: parsed.reinstall,
  };
}

function parseNodeUpdateArgs(args) {
  if (args[0] !== "update") {
    return null;
  }
  const parsed = {
    backend: agentsBackend,
    source: packageSource,
    json: false,
    yes: false,
    agentsRoot: undefined,
    claudeRoot: undefined,
    githubRepo: undefined,
    githubRef: undefined,
    githubArchiveSha256: undefined,
  };
  for (let index = 1; index < args.length; index += 1) {
    const arg = args[index];
    if (arg === cliFlags.json) {
      parsed.json = true;
      continue;
    }
    if (arg === cliFlags.yes) {
      parsed.yes = true;
      continue;
    }
    if (arg === cliFlags.backend) {
      const value = readOptionValue(args, index);
      if (value === null) {
        return null;
      }
      parsed.backend = value;
      index += 1;
      continue;
    }
    const backendValue = readEqualsOption(arg, cliFlags.backend);
    if (backendValue !== null) {
      parsed.backend = backendValue;
      continue;
    }
    if (arg === cliFlags.source) {
      const value = readOptionValue(args, index);
      if (value === null) {
        return null;
      }
      parsed.source = value;
      index += 1;
      continue;
    }
    const sourceValue = readEqualsOption(arg, cliFlags.source);
    if (sourceValue !== null) {
      parsed.source = sourceValue;
      continue;
    }
    if (arg === cliFlags.githubRepo) {
      const value = readOptionValue(args, index);
      if (value === null) {
        return null;
      }
      parsed.githubRepo = value;
      index += 1;
      continue;
    }
    const githubRepoValue = readEqualsOption(arg, cliFlags.githubRepo);
    if (githubRepoValue !== null) {
      parsed.githubRepo = githubRepoValue;
      continue;
    }
    if (arg === cliFlags.githubRef) {
      const value = readOptionValue(args, index);
      if (value === null) {
        return null;
      }
      parsed.githubRef = value;
      index += 1;
      continue;
    }
    const githubRefValue = readEqualsOption(arg, cliFlags.githubRef);
    if (githubRefValue !== null) {
      parsed.githubRef = githubRefValue;
      continue;
    }
    if (arg === cliFlags.githubArchiveSha256) {
      const value = readOptionValue(args, index);
      if (value === null) {
        return null;
      }
      parsed.githubArchiveSha256 = value;
      index += 1;
      continue;
    }
    const githubArchiveSha256Value = readEqualsOption(arg, cliFlags.githubArchiveSha256);
    if (githubArchiveSha256Value !== null) {
      parsed.githubArchiveSha256 = githubArchiveSha256Value;
      continue;
    }
    if (arg === cliFlags.agentsRoot) {
      const value = readOptionValue(args, index);
      if (value === null) {
        return null;
      }
      parsed.agentsRoot = value;
      index += 1;
      continue;
    }
    const agentsRootValue = readEqualsOption(arg, cliFlags.agentsRoot);
    if (agentsRootValue !== null) {
      parsed.agentsRoot = agentsRootValue;
      continue;
    }
    if (arg === cliFlags.claudeRoot) {
      const value = readOptionValue(args, index);
      if (value === null) {
        return null;
      }
      parsed.claudeRoot = value;
      index += 1;
      continue;
    }
    const claudeRootValue = readEqualsOption(arg, cliFlags.claudeRoot);
    if (claudeRootValue !== null) {
      parsed.claudeRoot = claudeRootValue;
      continue;
    }
    return null;
  }
  return parsed;
}

function parsedNodeUpdateResult(parsed, includeYes = false) {
  if (!backendAllowed(parsed.backend, [agentsBackend, claudeBackend, bundleBackend])) {
    return null;
  }
  if (parsed.source === githubSource) {
    if (!backendAllowed(parsed.backend, [agentsBackend])) {
      return null;
    }
    return {
      backend: parsed.backend,
      source: parsed.source,
      ...(includeYes ? { yes: true } : {}),
      agentsRoot: parsed.agentsRoot,
      ...parsedGithubOptions(parsed.githubRepo, parsed.githubRef, parsed.githubArchiveSha256),
    };
  }
  if (parsed.source !== packageSource) {
    return null;
  }
  return {
    backend: parsed.backend,
    source: parsed.source,
    ...(includeYes ? { yes: true } : {}),
    agentsRoot: parsed.agentsRoot,
    ...(parsed.claudeRoot === undefined ? {} : { claudeRoot: parsed.claudeRoot }),
  };
}

function parseNodeBackendRootArgs(args, command, allowedBackends = [agentsBackend, bundleBackend]) {
  if (args[0] !== command) {
    return null;
  }
  let backend = agentsBackend;
  let agentsRoot;
  let claudeRoot;
  for (let index = 1; index < args.length; index += 1) {
    const arg = args[index];
    if (arg === cliFlags.backend) {
      const value = readOptionValue(args, index);
      if (value === null) {
        return null;
      }
      backend = value;
      index += 1;
      continue;
    }
    const backendValue = readEqualsOption(arg, cliFlags.backend);
    if (backendValue !== null) {
      backend = backendValue;
      continue;
    }
    if (arg === cliFlags.agentsRoot) {
      const value = readOptionValue(args, index);
      if (value === null) {
        return null;
      }
      agentsRoot = value;
      index += 1;
      continue;
    }
    const agentsRootValue = readEqualsOption(arg, cliFlags.agentsRoot);
    if (agentsRootValue !== null) {
      agentsRoot = agentsRootValue;
      continue;
    }
    if (arg === cliFlags.claudeRoot) {
      const value = readOptionValue(args, index);
      if (value === null) {
        return null;
      }
      claudeRoot = value;
      index += 1;
      continue;
    }
    const claudeRootValue = readEqualsOption(arg, cliFlags.claudeRoot);
    if (claudeRootValue !== null) {
      claudeRoot = claudeRootValue;
      continue;
    }
    return null;
  }
  if (!backendAllowed(backend, allowedBackends)) {
    return null;
  }
  return parsedBackendRoots(backend, agentsRoot, claudeRoot);
}

function parseNodeDiagnoseJsonArgs(args) {
  if (args[0] !== "diagnose") {
    return null;
  }
  if (!args.includes(cliFlags.json)) {
    return null;
  }
  const withoutJson = args.filter((arg) => arg !== cliFlags.json);
  return parseNodeBackendRootArgs(withoutJson, "diagnose", [agentsBackend, claudeBackend, bundleBackend]);
}

function parseNodeDiagnoseArgs(args) {
  return parseNodeBackendRootArgs(args, "diagnose", [agentsBackend, claudeBackend, bundleBackend]);
}

function parseNodeUpdateJsonArgs(args) {
  const parsed = parseNodeUpdateArgs(args);
  if (parsed === null || !parsed.json || parsed.yes) {
    return null;
  }
  return parsedNodeUpdateResult(parsed);
}

function parseNodeUpdateDryRunArgs(args) {
  const parsed = parseNodeUpdateArgs(args);
  if (parsed === null || parsed.json || parsed.yes) {
    return null;
  }
  return parsedNodeUpdateResult(parsed);
}

function parseNodeUpdateYesArgs(args) {
  const parsed = parseNodeUpdateArgs(args);
  if (parsed === null || !parsed.yes || parsed.json) {
    return null;
  }
  return parsedNodeUpdateResult(parsed, true);
}

function parseNodeUnsupportedUpdateJsonYesArgs(args) {
  if (args[0] !== "update") {
    return null;
  }
  let backend = agentsBackend;
  let source = packageSource;
  let hasJson = false;
  let hasYes = false;
  let agentsRoot;
  for (let index = 1; index < args.length; index += 1) {
    const arg = args[index];
    if (arg === cliFlags.json) {
      hasJson = true;
      continue;
    }
    if (arg === cliFlags.yes) {
      hasYes = true;
      continue;
    }
    if (arg === cliFlags.backend) {
      const value = readOptionValue(args, index);
      if (value === null) {
        return null;
      }
      backend = value;
      index += 1;
      continue;
    }
    const backendValue = readEqualsOption(arg, cliFlags.backend);
    if (backendValue !== null) {
      backend = backendValue;
      continue;
    }
    if (arg === cliFlags.source) {
      const value = readOptionValue(args, index);
      if (value === null) {
        return null;
      }
      source = value;
      index += 1;
      continue;
    }
    const sourceValue = readEqualsOption(arg, cliFlags.source);
    if (sourceValue !== null) {
      source = sourceValue;
      continue;
    }
    if (arg === cliFlags.githubRepo || arg === cliFlags.githubRef || arg === cliFlags.githubArchiveSha256) {
      if (readOptionValue(args, index) === null) {
        return null;
      }
      index += 1;
      continue;
    }
    if (
      readEqualsOption(arg, cliFlags.githubRepo) !== null ||
      readEqualsOption(arg, cliFlags.githubRef) !== null ||
      readEqualsOption(arg, cliFlags.githubArchiveSha256) !== null
    ) {
      continue;
    }
    if (arg === cliFlags.agentsRoot) {
      const value = readOptionValue(args, index);
      if (value === null) {
        return null;
      }
      agentsRoot = value;
      index += 1;
      continue;
    }
    const agentsRootValue = readEqualsOption(arg, cliFlags.agentsRoot);
    if (agentsRootValue !== null) {
      agentsRoot = agentsRootValue;
      continue;
    }
    if (arg === cliFlags.claudeRoot) {
      if (readOptionValue(args, index) === null) {
        return null;
      }
      index += 1;
      continue;
    }
    if (readEqualsOption(arg, cliFlags.claudeRoot) !== null) {
      continue;
    }
    return null;
  }
  if (!hasJson || !hasYes || backend !== agentsBackend || !backendAllowed(source, [packageSource, githubSource])) {
    return null;
  }
  return { backend, source, agentsRoot };
}

function parseNodeCheckPathsExistArgs(args) {
  return parseNodeBackendRootArgs(args, "check_paths_exist", [agentsBackend, claudeBackend, bundleBackend]);
}

function runNodeJson(args, parser, buildSummary, exitStatus) {
  const parsed = parser(args);
  if (parsed === null) {
    return null;
  }
  try {
    const summary = buildSummary(buildNodeBackendContext(parsed));
    console.log(JSON.stringify(sortJsonObjectKeys(summary), null, 2));
    return exitStatus(summary);
  } catch (error) {
    console.error(error.message);
    return 1;
  }
}

function runNodeDiagnoseJson(args) {
  return runNodeJson(
    args,
    parseNodeDiagnoseJsonArgs,
    (context) => diagnosticSummary(verifyBackend(context)),
    () => 0,
  );
}

function printDiagnosticSummary(summary) {
  console.log(
    `[${summary.backend}] diagnose: ${summary.issue_count} issue(s), ` +
      `${summary.managed_install_count} managed install(s) at ${summary.target_root}`,
  );
  if (summary.legacy_target_dir_count > 0) {
    console.log(
      `[${summary.backend}] upgrade guidance: ${summary.legacy_target_dir_count} legacy target dir(s) can be replaced by current servo target dirs`,
    );
    console.log(`[${summary.backend}] next: ${summary.upgrade_guidance}`);
  }
  if (summary.issue_codes.length > 0) {
    console.log(`issue codes: ${summary.issue_codes.join(", ")}`);
  }
  if (summary.unrecognized_count > 0) {
    console.log(`unrecognized target entries: ${summary.unrecognized_count}`);
  }
  if (summary.conflict_count > 0) {
    console.log(`conflict entries: ${summary.conflict_count}`);
  }
}

function runNodeDiagnose(args) {
  const parsed = parseNodeDiagnoseArgs(args);
  if (parsed === null) {
    return null;
  }
  try {
    printDiagnosticSummary(diagnosticSummary(verifyBackend(buildNodeBackendContext(parsed))));
    return 0;
  } catch (error) {
    console.error(`error: ${error.message}`);
    return 1;
  }
}

function runtimeMigrationContext(parsed) {
  const sourceRoot = process.env.SERVO_HARNESS_REPO_ROOT || process.cwd();
  const targetRepoRoot = validateTargetRepoRoot(
    process.env.SERVO_HARNESS_TARGET_REPO_ROOT || process.cwd(),
    sourceRoot,
  );
  return {
    ...parsed,
    targetRepoRoot,
    sourceRuntimePath: join(targetRepoRoot, legacyAwRuntimeDir),
    destinationRuntimePath: join(targetRepoRoot, servoRuntimeDir),
    sentinelPath: join(targetRepoRoot, servoRuntimeDir, runtimeMigrationSentinel),
  };
}

function readRuntimeMigrationSentinel(path) {
  const stat = lstatOrNull(path);
  if (stat === null || !stat.isFile()) {
    return null;
  }
  try {
    return readJsonObject(path);
  } catch (error) {
    return null;
  }
}

function runtimeMigrationReinstallPlan(context) {
  if (!context.reinstall) {
    return {
      requested: false,
      backend: context.backend,
      command: null,
      status: "not-requested",
      blocking_issue_count: 0,
      note: "not requested",
    };
  }
  const args = ["servo-installer", "update", "--backend", context.backend, "--yes"];
  if (context.backend === agentsBackend && context.agentsRoot !== undefined) {
    args.push("--agents-root", context.agentsRoot);
  }
  if (context.backend === claudeBackend && context.claudeRoot !== undefined) {
    args.push("--claude-root", context.claudeRoot);
  }
  if (context.backend === bundleBackend) {
    if (context.agentsRoot !== undefined) {
      args.push("--agents-root", context.agentsRoot);
    }
    if (context.claudeRoot !== undefined) {
      args.push("--claude-root", context.claudeRoot);
    }
  }
  let summaries;
  if (context.backend === bundleBackend) {
    const { agentsContext, claudeContext } = validateBundleDisjointRoots(context);
    const agentsSummary = updatePlanSummary(agentsContext);
    const claudeSummary = updatePlanSummary(claudeContext);
    summaries = {
      [agentsBackend]: agentsSummary,
      [claudeBackend]: claudeSummary,
    };
  } else {
    summaries = {
      [context.backend]: updatePlanSummary(buildNodeBackendContext(context)),
    };
  }
  const blockingIssueCount = Object.values(summaries)
    .reduce((total, summary) => total + summary.blocking_issue_count, 0);
  return {
    requested: true,
    backend: context.backend,
    command: args.join(" "),
    status: blockingIssueCount === 0 ? "ready" : "blocked",
    blocking_issue_count: blockingIssueCount,
    summaries,
    note: "uses existing update --yes chain after runtime migration succeeds",
  };
}

function runtimeMigrationBlockingIssueCount(summary) {
  const reinstallBlocking =
    summary.reinstall_plan && summary.reinstall_plan.requested
      ? summary.reinstall_plan.blocking_issue_count
      : 0;
  return summary.issue_count + reinstallBlocking;
}

async function applyRuntimeMigrationReinstall(context) {
  if (context.backend === bundleBackend) {
    return await runBundleUpdateYes(context);
  }
  return applyUpdateContext(buildNodeBackendContext(context));
}

function runtimeMigrationIssue(code, path, detail) {
  return { code, path, detail };
}

function assertRuntimeSymlinksStayInsideSource(sourcePath) {
  const sourceRealpath = realpathSync(sourcePath);
  const stack = [sourcePath];
  while (stack.length > 0) {
    const currentPath = stack.pop();
    for (const entry of readdirSync(currentPath, { withFileTypes: true })) {
      const entryPath = join(currentPath, entry.name);
      if (entry.isDirectory()) {
        stack.push(entryPath);
        continue;
      }
      if (!entry.isSymbolicLink()) {
        continue;
      }
      let targetRealpath;
      try {
        targetRealpath = realpathSync(entryPath);
      } catch (error) {
        throw new Error(`runtime migration blocked: symlink target is unreadable: ${entryPath}`);
      }
      if (!isPathContainedIn(targetRealpath, sourceRealpath)) {
        throw new Error(
          `runtime migration blocked: symlink target escapes ${legacyAwRuntimeDir}: ${entryPath} -> ${targetRealpath}`,
        );
      }
    }
  }
}

function rewriteAwPathsInDirectory(dirPath) {
  const pending = [dirPath];
  let rewrittenFileCount = 0;
  while (pending.length > 0) {
    const current = pending.pop();
    for (const entry of readdirSync(current, { withFileTypes: true })) {
      const entryPath = join(current, entry.name);
      if (entry.isSymbolicLink()) {
        continue;
      }
      if (entry.isDirectory()) {
        pending.push(entryPath);
        continue;
      }
      if (!entry.isFile()) {
        continue;
      }
      const ext = entry.name.slice(entry.name.lastIndexOf("."));
      if (!runtimeMigrationTextExtensions.has(ext)) {
        continue;
      }
      const original = readFileSync(entryPath, "utf8");
      let rewritten = original;
      for (const [pattern, replacement] of runtimeMigrationAwPathReplacements) {
        rewritten = rewritten.replace(pattern, replacement);
      }
      if (rewritten !== original) {
        writeFileSync(entryPath, rewritten, "utf8");
        rewrittenFileCount++;
      }
    }
  }
  return rewrittenFileCount;
}

function copyRuntimeDirectory(sourcePath, destinationPath) {
  const sourceStat = lstatSync(sourcePath);
  if (sourceStat.isSymbolicLink()) {
    symlinkSync(readlinkSync(sourcePath), destinationPath);
    return;
  }
  if (sourceStat.isDirectory()) {
    mkdirSync(destinationPath, { mode: sourceStat.mode & 0o777 });
    for (const entry of readdirSync(sourcePath, { withFileTypes: true })) {
      copyRuntimeDirectory(join(sourcePath, entry.name), join(destinationPath, entry.name));
    }
    chmodSync(destinationPath, sourceStat.mode & 0o777);
    return;
  }
  if (sourceStat.isFile()) {
    copyFileSync(sourcePath, destinationPath, constants.COPYFILE_EXCL);
    chmodSync(destinationPath, sourceStat.mode & 0o777);
    return;
  }
  throw new Error(`runtime migration blocked: unsupported runtime entry type: ${sourcePath}`);
}

function runtimeMigrationSummary(context) {
  validateNotSensitiveRepoRoot(context.targetRepoRoot, "Runtime migration target repo root", "migrated");
  const sourceStat = lstatOrNull(context.sourceRuntimePath);
  const destinationStat = lstatOrNull(context.destinationRuntimePath);
  const sentinel = readRuntimeMigrationSentinel(context.sentinelPath);
  const issues = [];
  let state = "no-runtime";
  let action = "noop";
  let mutationAllowed = false;

  if (sourceStat !== null && (!sourceStat.isDirectory() || sourceStat.isSymbolicLink())) {
    issues.push(runtimeMigrationIssue(
      "malformed-source-runtime",
      context.sourceRuntimePath,
      `${legacyAwRuntimeDir} must be a real directory`,
    ));
    state = "blocked";
    action = "blocked";
  } else if (destinationStat !== null && (!destinationStat.isDirectory() || destinationStat.isSymbolicLink())) {
    issues.push(runtimeMigrationIssue(
      "malformed-destination-runtime",
      context.destinationRuntimePath,
      `${servoRuntimeDir} must be absent or a real directory`,
    ));
    state = "blocked";
    action = "blocked";
  } else if (sourceStat === null && destinationStat === null) {
    state = "no-runtime";
    action = "noop";
  } else if (sourceStat === null && destinationStat !== null) {
    state = "destination-only";
    action = "noop";
  } else if (sourceStat !== null && destinationStat === null) {
    state = "ready";
    action = "copy";
    mutationAllowed = true;
  } else if (
    sentinel !== null &&
    sentinel.marker_version === runtimeMigrationSentinelVersion &&
    sentinel.from === legacyAwRuntimeDir &&
    sentinel.to === servoRuntimeDir
  ) {
    state = "already-migrated";
    action = "noop";
  } else {
    issues.push(runtimeMigrationIssue(
      "destination-runtime-exists",
      context.destinationRuntimePath,
      `${servoRuntimeDir} already exists; refusing to overwrite or merge runtime state`,
    ));
    state = "blocked";
    action = "blocked";
  }

  return {
    command: "migrate-runtime",
    from: "aw",
    to: "servo",
    target_repo_root: context.targetRepoRoot,
    target_root: context.targetRepoRoot,
    source_runtime_path: context.sourceRuntimePath,
    destination_runtime_path: context.destinationRuntimePath,
    state,
    verdict: issues.length > 0 ? "blocked" : state,
    action,
    planned_actions: mutationAllowed ? ["copy .aw to .servo", "rewrite .aw path references to .servo in migrated text files"] : [],
    backup_policy: "retain .aw in place; no default cleanup",
    mutation_allowed: mutationAllowed,
    mutation_performed: false,
    source_exists: sourceStat !== null,
    destination_exists: destinationStat !== null,
    sentinel_path: context.sentinelPath,
    sentinel_present: sentinel !== null,
    issue_count: issues.length,
    issues,
    blocking_issues: issues,
    recovery_hints: issues.length > 0
      ? ["preserve .aw; fix or relocate the reported path; rerun migrate-runtime"]
      : [],
    reinstall_plan: runtimeMigrationReinstallPlan(context),
  };
}

function applyRuntimeMigration(context) {
  const summary = runtimeMigrationSummary(context);
  if (summary.issue_count > 0) {
    throw new Error(`runtime migration blocked by ${summary.issue_count} issue(s)`);
  }
  if (!summary.mutation_allowed) {
    return summary;
  }
  assertRuntimeSymlinksStayInsideSource(context.sourceRuntimePath);
  copyRuntimeDirectory(context.sourceRuntimePath, context.destinationRuntimePath);
  const rewrittenCount = rewriteAwPathsInDirectory(context.destinationRuntimePath);
  writeFileSync(
    context.sentinelPath,
    `${JSON.stringify({
      marker_version: runtimeMigrationSentinelVersion,
      from: legacyAwRuntimeDir,
      to: servoRuntimeDir,
      source_runtime_path: context.sourceRuntimePath,
      destination_runtime_path: context.destinationRuntimePath,
      migrated_at: new Date().toISOString(),
      rewritten_file_count: rewrittenCount,
    }, null, 2)}\n`,
    "utf8",
  );
  return {
    ...runtimeMigrationSummary(context),
    state: "migrated",
    action: "copy",
    mutation_performed: true,
    rewritten_file_count: rewrittenCount,
  };
}

function printRuntimeMigrationSummary(summary) {
  console.log(`runtime migration ${summary.from} -> ${summary.to} for ${summary.target_repo_root}`);
  console.log(`state: ${summary.state}`);
  console.log(`action: ${summary.action}`);
  console.log(`source: ${summary.source_runtime_path}`);
  console.log(`destination: ${summary.destination_runtime_path}`);
  if (summary.issue_count > 0) {
    console.log(`blocking issues: ${summary.issue_count}`);
    for (const issue of summary.issues) {
      console.log(`  - ${issue.code}: ${issue.path} (${issue.detail})`);
    }
  }
  if (summary.reinstall_plan.requested) {
    console.log(`reinstall plan: ${summary.reinstall_plan.command}`);
    console.log(`reinstall status: ${summary.reinstall_plan.status}`);
    console.log(`reinstall blocking issues: ${summary.reinstall_plan.blocking_issue_count}`);
  }
  if (summary.rewritten_file_count !== undefined && summary.rewritten_file_count > 0) {
    console.log(`rewritten files: ${summary.rewritten_file_count}`);
  }
  if (!summary.mutation_performed && summary.mutation_allowed) {
    console.log("dry-run only; pass --yes to copy .aw into .servo");
  }
}

async function runNodeMigrateRuntime(args) {
  const parsed = parseNodeMigrateRuntimeArgs(args);
  if (parsed === null) {
    return null;
  }
  try {
    const context = runtimeMigrationContext(parsed);
    const summary = runtimeMigrationSummary(context);
    if (parsed.yes && runtimeMigrationBlockingIssueCount(summary) === 0) {
      const appliedSummary = applyRuntimeMigration(context);
      if (parsed.reinstall) {
        printRuntimeMigrationSummary(appliedSummary);
        const reinstallStatus = await applyRuntimeMigrationReinstall(context);
        return reinstallStatus === 0 ? 0 : 1;
      }
      printRuntimeMigrationSummary(appliedSummary);
      return appliedSummary.issue_count > 0 ? 1 : 0;
    }
    if (parsed.json) {
      console.log(JSON.stringify(sortJsonObjectKeys(summary), null, 2));
    } else {
      printRuntimeMigrationSummary(summary);
    }
    return runtimeMigrationBlockingIssueCount(summary) > 0 ? 1 : 0;
  } catch (error) {
    console.error(`error: ${error.message}`);
    return 1;
  }
}

function buildNodeGithubSourceContext(parsed, archiveBuffer) {
  const source = githubSourceRootFromArchiveBuffer(
    parsed.githubRepo,
    parsed.githubRef,
    archiveBuffer,
    parsed.githubArchiveSha256,
  );
  try {
    const context = buildNodeBackendContext({
      ...parsed,
      sourceKind: source.sourceKind,
      sourceRef: source.sourceRef,
      sourceRootOverride: source.sourceRoot,
    });
    return {
      context: {
        ...context,
        updateSourceRecoveryArgs: githubSourceRecoveryArgs(parsed),
      },
      cleanup: source.cleanup,
    };
  } catch (error) {
    source.cleanup();
    throw error;
  }
}

function githubSourceRecoveryArgs(parsed) {
  const args = [
    `${cliFlags.source} ${githubSource}`,
    `${cliFlags.githubRepo} ${JSON.stringify(parsed.githubRepo)}`,
    `${cliFlags.githubRef} ${JSON.stringify(parsed.githubRef)}`,
  ];
  if (parsed.githubArchiveSha256 !== undefined) {
    args.push(`${cliFlags.githubArchiveSha256} ${JSON.stringify(parsed.githubArchiveSha256)}`);
  }
  return args.join(" ");
}

function validateParsedGithubSource(parsed) {
  validateGithubRepo(parsed.githubRepo);
  validateGithubRef(parsed.githubRef);
  if (parsed.githubArchiveSha256 !== undefined) {
    validateSha256Digest(parsed.githubArchiveSha256);
  }
}

async function withNodeUpdateContext(parsed, callback) {
  let githubCleanup = null;
  try {
    let context;
    if (parsed.source === githubSource) {
      validateParsedGithubSource(parsed);
      const archiveBuffer = await downloadGithubArchive(parsed.githubRepo, parsed.githubRef);
      const githubContext = buildNodeGithubSourceContext(parsed, archiveBuffer);
      context = githubContext.context;
      githubCleanup = githubContext.cleanup;
    } else {
      context = buildNodeBackendContext(parsed);
    }
    return await callback(context);
  } finally {
    if (githubCleanup !== null) {
      githubCleanup();
    }
  }
}

async function runNodeUpdateJson(args) {
  const parsed = parseNodeUpdateJsonArgs(args);
  if (parsed === null) {
    return null;
  }
  try {
    return await withNodeUpdateContext(parsed, (context) => {
      const summary = updatePlanSummary(context);
      console.log(JSON.stringify(sortJsonObjectKeys(summary), null, 2));
      return summary.blocking_issue_count ? 1 : 0;
    });
  } catch (error) {
    console.error(`error: ${error.message}`);
    return 1;
  }
}

async function runNodeUpdateDryRun(args) {
  const parsed = parseNodeUpdateDryRunArgs(args);
  if (parsed === null) {
    return null;
  }
  try {
    return await withNodeUpdateContext(parsed, (context) => {
      const summary = updatePlanSummary(context);
      printUpdatePlan(summary);
      if (summary.blocking_issue_count > 0) {
        throw new Error(`[${summary.backend}] update blocked by ${summary.blocking_issue_count} preflight issue(s)`);
      }
      console.log(`[${summary.backend}] dry-run only; pass --yes to apply update`);
      return 0;
    });
  } catch (error) {
    console.error(`error: ${error.message}`);
    return 1;
  }
}

function applyUpdateContext(context) {
  const summary = updatePlanSummary(context);
  printUpdatePlan(summary);
  if (summary.blocking_issue_count > 0) {
    throw new Error(`[${context.backend}] update blocked by ${summary.blocking_issue_count} preflight issue(s)`);
  }
  console.log(`[${context.backend}] applying update`);
  let result = null;
  try {
    pruneBackendManagedInstalls(context);
    checkBackendTargetPaths(context);
    installBackendPayloads(context);
    result = verifyBackend(context);
    if (result.issues.length > 0) {
      printVerifyResult(result);
      throw new Error(`[${context.backend}] update failed strict verify with ${result.issues.length} issue(s)`);
    }
  } catch (error) {
    throw new Error(`${error.message}\n${updateFailureRecoveryHint(context)}`);
  }
  printVerifyResult(result);
  console.log(`[${context.backend}] update complete`);
  return 0;
}

function printUpdatePlan(summary) {
  console.log(`[${summary.backend}] update plan for ${summary.target_root}`);
  console.log(`sequence: ${summary.operation_sequence.join(" -> ")}`);
  console.log(`managed installs to delete: ${summary.managed_installs_to_delete.length}`);
  for (const currentPath of summary.managed_installs_to_delete) {
    console.log(`  - ${currentPath}`);
  }
  console.log(`target paths to write: ${summary.planned_target_paths.length}`);
  for (const currentPath of summary.planned_target_paths) {
    console.log(`  - ${currentPath}`);
  }
  if (summary.legacy_target_dir_count > 0) {
    console.log(`legacy target dirs to replace: ${summary.legacy_target_dir_count}`);
    for (const current of summary.legacy_target_dirs) {
      console.log(`  - ${current.legacy_path} -> ${current.target_path}`);
    }
    console.log(`upgrade guidance: ${summary.upgrade_guidance}`);
  }
  console.log(`blocking preflight issues: ${summary.blocking_issue_count}`);
  for (const currentIssue of summary.blocking_issues) {
    console.log(`  - ${currentIssue.code}: ${currentIssue.path} (${currentIssue.detail})`);
  }
}

function updateFailureRecoveryHint(context) {
  const sourceOverride =
    context.updateSourceRecoveryArgs === undefined
      ? ""
      : ` ${context.updateSourceRecoveryArgs}`;
  const rootOverride =
    context.targetRootOverrideFlag === undefined
      ? ""
      : ` ${context.targetRootOverrideFlag} ${JSON.stringify(context.targetRoot)}`;
  return (
    `[${context.backend}] recovery: the update may be partially applied at ${context.targetRoot}. ` +
    "After fixing the reported error, run diagnose and then rerun " +
    `\`servo-installer update --backend ${context.backend}${sourceOverride} --yes${rootOverride}\`.`
  );
}

function checkBackendTargetPaths(context) {
  const summary = checkPathsExistSummary(context);
  if (summary.conflicts.length > 0) {
    throw new Error(
      `[${context.backend}] found ${summary.conflicts.length} pre-existing path(s) — prune first\n\n${formatPathConflicts(summary.conflicts)}`,
    );
  }
  console.log(`[${context.backend}] ok: no pre-existing paths at ${summary.targetRoot}`);
}

async function runNodeUpdateYes(args) {
  const parsed = parseNodeUpdateYesArgs(args);
  if (parsed === null) {
    return null;
  }
  try {
    return await withNodeUpdateContext(parsed, applyUpdateContext);
  } catch (error) {
    console.error(`error: ${error.message}`);
    return 1;
  }
}

function runNodeCheckPathsExist(args) {
  const parsed = parseNodeCheckPathsExistArgs(args);
  if (parsed === null) {
    return null;
  }
  try {
    const summary = checkPathsExistSummary(buildNodeBackendContext(parsed));
    if (summary.conflicts.length > 0) {
      console.log(
        `[${summary.backend}] found ${summary.conflicts.length} existing path(s) — prune first to overwrite\n\n${formatPathConflicts(summary.conflicts)}`,
      );
      return 1;
    }
    console.log(`[${summary.backend}] ok: no pre-existing paths at ${summary.targetRoot}`);
    return 0;
  } catch (error) {
    console.error(`error: ${error.message}`);
    return 1;
  }
}

function parseNodeVerifyArgs(args) {
  return parseNodeBackendRootArgs(args, "verify", [agentsBackend, claudeBackend, bundleBackend]);
}

function parseNodeInstallArgs(args) {
  return parseNodeBackendRootArgs(args, "install", [agentsBackend, claudeBackend, bundleBackend]);
}

function parseNodePruneArgs(args) {
  if (args[0] !== "prune") {
    return null;
  }
  let hasAll = false;
  let backend = agentsBackend;
  let agentsRoot;
  let claudeRoot;
  for (let index = 1; index < args.length; index += 1) {
    const arg = args[index];
    if (arg === cliFlags.all) {
      hasAll = true;
      continue;
    }
    if (arg === cliFlags.backend) {
      const value = readOptionValue(args, index);
      if (value === null) {
        return null;
      }
      backend = value;
      index += 1;
      continue;
    }
    const backendValue = readEqualsOption(arg, cliFlags.backend);
    if (backendValue !== null) {
      backend = backendValue;
      continue;
    }
    if (arg === cliFlags.agentsRoot) {
      const value = readOptionValue(args, index);
      if (value === null) {
        return null;
      }
      agentsRoot = value;
      index += 1;
      continue;
    }
    const agentsRootValue = readEqualsOption(arg, cliFlags.agentsRoot);
    if (agentsRootValue !== null) {
      agentsRoot = agentsRootValue;
      continue;
    }
    if (arg === cliFlags.claudeRoot) {
      const value = readOptionValue(args, index);
      if (value === null) {
        return null;
      }
      claudeRoot = value;
      index += 1;
      continue;
    }
    const claudeRootValue = readEqualsOption(arg, cliFlags.claudeRoot);
    if (claudeRootValue !== null) {
      claudeRoot = claudeRootValue;
      continue;
    }
    return null;
  }
  if (!hasAll || !backendAllowed(backend, [agentsBackend, claudeBackend, bundleBackend])) {
    return null;
  }
  return { backend, agentsRoot, ...(claudeRoot === undefined ? {} : { claudeRoot }) };
}

function parseNodeUnsupportedPruneMissingAllArgs(args) {
  if (args[0] !== "prune") {
    return null;
  }
  let hasAll = false;
  let backend = agentsBackend;
  let source = packageSource;
  let agentsRoot;
  for (let index = 1; index < args.length; index += 1) {
    const arg = args[index];
    if (arg === cliFlags.all) {
      hasAll = true;
      continue;
    }
    if (arg === cliFlags.backend) {
      const value = readOptionValue(args, index);
      if (value === null) {
        return null;
      }
      backend = value;
      index += 1;
      continue;
    }
    const backendValue = readEqualsOption(arg, cliFlags.backend);
    if (backendValue !== null) {
      backend = backendValue;
      continue;
    }
    if (arg === cliFlags.source) {
      const value = readOptionValue(args, index);
      if (value === null) {
        return null;
      }
      source = value;
      index += 1;
      continue;
    }
    const sourceValue = readEqualsOption(arg, cliFlags.source);
    if (sourceValue !== null) {
      source = sourceValue;
      continue;
    }
    if (arg === cliFlags.agentsRoot) {
      const value = readOptionValue(args, index);
      if (value === null) {
        return null;
      }
      agentsRoot = value;
      index += 1;
      continue;
    }
    const agentsRootValue = readEqualsOption(arg, cliFlags.agentsRoot);
    if (agentsRootValue !== null) {
      agentsRoot = agentsRootValue;
      continue;
    }
    if (arg === cliFlags.claudeRoot) {
      if (readOptionValue(args, index) === null) {
        return null;
      }
      index += 1;
      continue;
    }
    if (readEqualsOption(arg, cliFlags.claudeRoot) !== null) {
      continue;
    }
    return null;
  }
  if (hasAll || backend !== agentsBackend || source !== packageSource) {
    return null;
  }
  return { backend, source, agentsRoot };
}

function runNodeUnsupportedAgentsVariant(args) {
  if (parseNodeUnsupportedUpdateJsonYesArgs(args) !== null) {
    console.error("error: update --json is only supported for dry-run plans; omit --json with --yes");
    return 1;
  }
  if (parseNodeUnsupportedPruneMissingAllArgs(args) !== null) {
    console.error("error: prune currently requires --all");
    return 1;
  }
  return null;
}

function printVerifyResult(result) {
  if (result.issues.length === 0) {
    console.log(`[${result.backend}] ok: target root is ready at ${result.targetRoot}`);
    return;
  }
  console.log(
    `[${result.backend}] drift: ${result.issues.length} issue(s) in target root at ${result.targetRoot}`,
  );
  for (const currentIssue of result.issues) {
    console.log(`  - ${currentIssue.code}: ${currentIssue.path} (${currentIssue.detail})`);
  }
}

function runNodeVerify(args) {
  const parsed = parseNodeVerifyArgs(args);
  if (parsed === null) {
    return null;
  }
  try {
    const result = verifyBackend(buildNodeBackendContext(parsed));
    printVerifyResult(result);
    return result.issues.length > 0 ? 1 : 0;
  } catch (error) {
    console.error(`error: ${error.message}`);
    return 1;
  }
}

function runNodeInstall(args) {
  const parsed = parseNodeInstallArgs(args);
  if (parsed === null) {
    return null;
  }
  try {
    const context = buildNodeBackendContext(parsed);
    installBackendPayloads(context);
    return 0;
  } catch (error) {
    console.error(`error: ${error.message}`);
    return 1;
  }
}

function runNodePrune(args) {
  const parsed = parseNodePruneArgs(args);
  if (parsed === null) {
    return null;
  }
  try {
    pruneBackendManagedInstalls(buildNodeBackendContext(parsed));
    return 0;
  } catch (error) {
    console.error(`error: ${error.message}`);
    return 1;
  }
}

function buildBundleBackendOptions(parsed, backend) {
  const options = { backend };
  if (parsed.agentsRoot !== undefined) {
    options.agentsRoot = parsed.agentsRoot;
  }
  if (parsed.claudeRoot !== undefined) {
    options.claudeRoot = parsed.claudeRoot;
  }
  return options;
}

function buildBundleArgs(command, backend, parsed) {
  const args = [command, "--backend", backend];
  if (parsed.agentsRoot !== undefined) {
    args.push("--agents-root", parsed.agentsRoot);
  }
  if (parsed.claudeRoot !== undefined) {
    args.push("--claude-root", parsed.claudeRoot);
  }
  return args;
}

// SA-C trust boundary: reject bundle mode when agents and claude target roots
// resolve to the same physical directory. Both roots must be path-disjoint to
// prevent cross-backend interference.
function validateBundleDisjointRoots(parsed) {
  const agentsContext = buildNodeBackendContext(buildBundleBackendOptions(parsed, agentsBackend));
  const claudeContext = buildNodeBackendContext(buildBundleBackendOptions(parsed, claudeBackend));
  const rootsOverlap =
    isPathContainedIn(agentsContext.targetRoot, claudeContext.targetRoot) ||
    isPathContainedIn(claudeContext.targetRoot, agentsContext.targetRoot);
  if (rootsOverlap) {
    throw new Error(
      `[${bundleBackend}] agents and claude target roots must be path-disjoint: ` +
        `agents=${agentsContext.targetRoot}, claude=${claudeContext.targetRoot}. ` +
        "Use non-overlapping --agents-root and --claude-root paths, or omit both to use per-backend defaults.",
    );
  }
  return { agentsContext, claudeContext };
}

function printBundlePartialCompletion(command, agentsStatus, claudeStatus) {
  const agentsResult = agentsStatus === 0 ? "ok" : "failed";
  const claudeResult = claudeStatus === 0 ? "ok" : "failed";
  console.error(`[${bundleBackend}] partial ${command}: agents=${agentsResult}, claude=${claudeResult}`);
}

async function runBundleDiagnoseJson(parsed) {
  const { agentsContext, claudeContext } = validateBundleDisjointRoots(parsed);
  const agentsSummary = diagnosticSummary(verifyBackend(agentsContext));
  const claudeSummary = diagnosticSummary(verifyBackend(claudeContext));
  const bundleSummary = {
    bundle: true,
    backends: {
      [agentsBackend]: agentsSummary,
      [claudeBackend]: claudeSummary,
    },
    total_issues: agentsSummary.issue_count + claudeSummary.issue_count,
    total_managed: agentsSummary.managed_install_count + claudeSummary.managed_install_count,
  };
  console.log(JSON.stringify(sortJsonObjectKeys(bundleSummary), null, 2));
  return 0;
}

async function runBundleDiagnose(parsed) {
  const { agentsContext, claudeContext } = validateBundleDisjointRoots(parsed);
  printDiagnosticSummary({ ...diagnosticSummary(verifyBackend(agentsContext)), backend: agentsBackend });
  printDiagnosticSummary({ ...diagnosticSummary(verifyBackend(claudeContext)), backend: claudeBackend });
  return 0;
}

async function runBundleVerify(parsed) {
  const { agentsContext, claudeContext } = validateBundleDisjointRoots(parsed);
  const agentsResult = verifyBackend(agentsContext);
  const claudeResult = verifyBackend(claudeContext);
  printVerifyResult({ ...agentsResult, backend: agentsBackend });
  printVerifyResult({ ...claudeResult, backend: claudeBackend });
  return (agentsResult.issues.length > 0 || claudeResult.issues.length > 0) ? 1 : 0;
}

async function runBundleCheckPathsExist(parsed) {
  // SA-C: fail-closed if roots are not path-disjoint
  validateBundleDisjointRoots(parsed);
  const agentsArgs = buildBundleArgs("check_paths_exist", agentsBackend, parsed);
  const claudeArgs = buildBundleArgs("check_paths_exist", claudeBackend, parsed);
  const agentsStatus = await runNodeOwned(agentsArgs);
  const claudeStatus = await runNodeOwned(claudeArgs);
  if (agentsStatus === 0 && claudeStatus === 0) {
    return 0;
  }
  return 1;
}

async function runBundleInstall(parsed) {
  // SA-C: fail-closed if roots are not path-disjoint (pre-write guard)
  validateBundleDisjointRoots(parsed);
  const agentsArgs = buildBundleArgs("install", agentsBackend, parsed);
  const claudeArgs = buildBundleArgs("install", claudeBackend, parsed);
  const agentsCheckArgs = buildBundleArgs("check_paths_exist", agentsBackend, parsed);
  const claudeCheckArgs = buildBundleArgs("check_paths_exist", claudeBackend, parsed);
  const agentsCheckStatus = await runNodeOwned(agentsCheckArgs);
  const claudeCheckStatus = await runNodeOwned(claudeCheckArgs);
  if (agentsCheckStatus !== 0 || claudeCheckStatus !== 0) {
    console.error(`[${bundleBackend}] pre-write check failed; aborting install`);
    return 1;
  }
  const agentsStatus = await runNodeOwned(agentsArgs);
  const claudeStatus = await runNodeOwned(claudeArgs);
  if (agentsStatus === 0 && claudeStatus === 0) {
    console.log(`[${bundleBackend}] install complete for both backends`);
    return 0;
  }
  printBundlePartialCompletion("install", agentsStatus, claudeStatus);
  if (agentsStatus !== 0) {
    console.error(`[${bundleBackend}] recovery: run \`servo-installer prune --backend agents --all\` then \`servo-installer install --backend agents\` then \`servo-installer verify --backend agents\``);
  }
  if (claudeStatus !== 0) {
    console.error(`[${bundleBackend}] recovery: run \`servo-installer prune --backend claude --all\` then \`servo-installer install --backend claude\` then \`servo-installer verify --backend claude\``);
  }
  return 1;
}

async function runBundleUpdateJson(parsed) {
  // SA-C: reject if roots are not path-disjoint
  validateBundleDisjointRoots(parsed);
  const agentsArgs = buildBundleArgs("update", agentsBackend, parsed);
  agentsArgs.push("--json");
  const claudeArgs = buildBundleArgs("update", claudeBackend, parsed);
  claudeArgs.push("--json");
  const agentsStatus = await runNodeOwned(agentsArgs);
  const claudeStatus = await runNodeOwned(claudeArgs);
  return (agentsStatus === 0 && claudeStatus === 0) ? 0 : 1;
}

async function runBundleUpdateDryRun(parsed) {
  // SA-C: reject if roots are not path-disjoint
  validateBundleDisjointRoots(parsed);
  const agentsArgs = buildBundleArgs("update", agentsBackend, parsed);
  const claudeArgs = buildBundleArgs("update", claudeBackend, parsed);
  const agentsStatus = await runNodeOwned(agentsArgs);
  const claudeStatus = await runNodeOwned(claudeArgs);
  if (agentsStatus === 0 && claudeStatus === 0) {
    return 0;
  }
  printBundlePartialCompletion("update", agentsStatus, claudeStatus);
  return 1;
}

async function runBundleUpdateYes(parsed) {
  // SA-C: reject if roots are not path-disjoint
  const { agentsContext, claudeContext } = validateBundleDisjointRoots(parsed);
  const agentsSummary = updatePlanSummary(agentsContext);
  const claudeSummary = updatePlanSummary(claudeContext);
  printUpdatePlan(agentsSummary);
  printUpdatePlan(claudeSummary);
  if (agentsSummary.blocking_issue_count > 0 || claudeSummary.blocking_issue_count > 0) {
    console.error(`[${bundleBackend}] pre-write update preflight failed; aborting update`);
    return 1;
  }
  const agentsArgs = buildBundleArgs("update", agentsBackend, parsed);
  agentsArgs.push("--yes");
  const claudeArgs = buildBundleArgs("update", claudeBackend, parsed);
  claudeArgs.push("--yes");
  const agentsStatus = await runNodeOwned(agentsArgs);
  const claudeStatus = await runNodeOwned(claudeArgs);
  if (agentsStatus === 0 && claudeStatus === 0) {
    console.log(`[${bundleBackend}] update complete for both backends`);
    return 0;
  }
  printBundlePartialCompletion("update", agentsStatus, claudeStatus);
  return 1;
}

async function runBundlePrune(parsed) {
  // SA-C: reject if roots are not path-disjoint; prune is ordered agents then claude
  validateBundleDisjointRoots(parsed);
  const agentsArgs = buildBundleArgs("prune", agentsBackend, parsed);
  agentsArgs.push("--all");
  const claudeArgs = buildBundleArgs("prune", claudeBackend, parsed);
  claudeArgs.push("--all");
  const agentsStatus = await runNodeOwned(agentsArgs);
  if (agentsStatus !== 0) {
    // SA-B: first-root failure stops second root; claude was not started
    console.error(`[${bundleBackend}] partial prune: agents failed, claude not started`);
    return 1;
  }
  const claudeStatus = await runNodeOwned(claudeArgs);
  if (claudeStatus === 0) {
    console.log(`[${bundleBackend}] prune complete for both backends`);
    return 0;
  }
  // claude ran but failed; agents already completed successfully
  console.error(`[${bundleBackend}] partial prune: agents ok, claude failed`);
  return 1;
}

async function runNodeBundle(args) {
  try {
    const diagnoseJson = parseNodeDiagnoseJsonArgs(args);
    if (diagnoseJson !== null && diagnoseJson.backend === bundleBackend) {
      return await runBundleDiagnoseJson(diagnoseJson);
    }
    const diagnose = parseNodeDiagnoseArgs(args);
    if (diagnose !== null && diagnose.backend === bundleBackend) {
      return await runBundleDiagnose(diagnose);
    }
    const updateJson = parseNodeUpdateJsonArgs(args);
    if (updateJson !== null && updateJson.backend === bundleBackend) {
      return await runBundleUpdateJson(updateJson);
    }
    const updateDryRun = parseNodeUpdateDryRunArgs(args);
    if (updateDryRun !== null && updateDryRun.backend === bundleBackend) {
      return await runBundleUpdateDryRun(updateDryRun);
    }
    const updateYes = parseNodeUpdateYesArgs(args);
    if (updateYes !== null && updateYes.backend === bundleBackend) {
      return await runBundleUpdateYes(updateYes);
    }
    const checkPaths = parseNodeCheckPathsExistArgs(args);
    if (checkPaths !== null && checkPaths.backend === bundleBackend) {
      return await runBundleCheckPathsExist(checkPaths);
    }
    const verify = parseNodeVerifyArgs(args);
    if (verify !== null && verify.backend === bundleBackend) {
      return await runBundleVerify(verify);
    }
    const install = parseNodeInstallArgs(args);
    if (install !== null && install.backend === bundleBackend) {
      return await runBundleInstall(install);
    }
    const prune = parseNodePruneArgs(args);
    if (prune !== null && prune.backend === bundleBackend) {
      return await runBundlePrune(prune);
    }
  } catch (error) {
    console.error(`error: ${error.message}`);
    return 1;
  }
  return null;
}

async function runNodeOwned(args) {
  const bundleStatus = await runNodeBundle(args);
  if (bundleStatus !== null) {
    return bundleStatus;
  }

  const nodeMigrateRuntimeStatus = await runNodeMigrateRuntime(args);
  if (nodeMigrateRuntimeStatus !== null) {
    return nodeMigrateRuntimeStatus;
  }

  const nodeDiagnoseStatus = runNodeDiagnoseJson(args);
  if (nodeDiagnoseStatus !== null) {
    return nodeDiagnoseStatus;
  }

  const nodeDiagnoseHumanStatus = runNodeDiagnose(args);
  if (nodeDiagnoseHumanStatus !== null) {
    return nodeDiagnoseHumanStatus;
  }

  const nodeUpdateStatus = await runNodeUpdateJson(args);
  if (nodeUpdateStatus !== null) {
    return nodeUpdateStatus;
  }

  const nodeUpdateDryRunStatus = await runNodeUpdateDryRun(args);
  if (nodeUpdateDryRunStatus !== null) {
    return nodeUpdateDryRunStatus;
  }

  const nodeUpdateYesStatus = await runNodeUpdateYes(args);
  if (nodeUpdateYesStatus !== null) {
    return nodeUpdateYesStatus;
  }

  const nodeCheckPathsExistStatus = runNodeCheckPathsExist(args);
  if (nodeCheckPathsExistStatus !== null) {
    return nodeCheckPathsExistStatus;
  }

  const nodeVerifyStatus = runNodeVerify(args);
  if (nodeVerifyStatus !== null) {
    return nodeVerifyStatus;
  }

  const nodeInstallStatus = runNodeInstall(args);
  if (nodeInstallStatus !== null) {
    return nodeInstallStatus;
  }

  const nodePruneStatus = runNodePrune(args);
  if (nodePruneStatus !== null) {
    return nodePruneStatus;
  }

  const unsupportedAgentsStatus = runNodeUnsupportedAgentsVariant(args);
  if (unsupportedAgentsStatus !== null) {
    return unsupportedAgentsStatus;
  }

  console.error(
    `unsupported servo-installer command or options for Node-only distribution: ${args.join(" ")}`,
  );
  console.error("Run servo-installer --help for supported package/runtime commands.");
  return 1;
}

function question(rl, prompt) {
  if (ttyIn) {
    _ensureKeypress();
    if (rl && typeof rl.pause === "function") {
      rl.pause();
    }
    process.stdout.write(prompt);
    setTuiRawMode(true);
    process.stdin.resume();
    return new Promise((resolve) => {
      let answer = "";
      const onKeypress = (str, key) => {
        const next = applyPromptInputKey(answer, str, key);
        answer = next.answer;
        if (next.output) {
          process.stdout.write(next.output);
        }
        if (next.exitCode !== undefined) {
          process.exit(130);
        }
        if (next.done) {
          process.stdin.removeListener("keypress", onKeypress);
          resolve(answer);
        }
      };
      process.stdin.on("keypress", onKeypress);
    });
  }

  return new Promise((resolve) => {
    if (rl && typeof rl.resume === "function") {
      rl.resume();
    }
    rl.question(prompt, (answer) => {
      resolve(answer);
    });
  });
}

function applyPromptInputKey(answer, str, key) {
  if (key && key.ctrl && key.name === "c") {
    return { answer, output: "^C\n", done: true, exitCode: 130 };
  }
  if (key && (key.name === "return" || key.name === "enter")) {
    return { answer, output: "\n", done: true };
  }
  if (key && (key.name === "backspace" || key.name === "delete")) {
    if (answer.length === 0) {
      return { answer, output: "", done: false };
    }
    return { answer: answer.slice(0, -1), output: "\b \b", done: false };
  }
  if (str && str >= " " && str !== "\x7f") {
    return { answer: answer + str, output: str, done: false };
  }
  return { answer, output: "", done: false };
}

async function pause(rl) {
  await question(rl, "\nPress Enter to return to the installer menu...");
  suppressMenuReturnUntil = Date.now() + 300;
}

// ─── Console capture for TUI-friendly output ──────────────────────────────

function captureConsole(fn) {
  const origLog = console.log;
  const origError = console.error;
  const captured = [];
  console.log = (...args) => captured.push(args.join(" "));
  console.error = (...args) => captured.push(args.join(" "));
  try {
    const result = fn();
    // Async: restore in Promise continuation (after async work completes)
    if (result && typeof result.then === "function") {
      return result.then(
        (v) => { console.log = origLog; console.error = origError; return { value: v, captured }; },
        (e) => { console.log = origLog; console.error = origError; throw e; },
      );
    }
    // Sync: restore now
    console.log = origLog;
    console.error = origError;
    return { value: result, captured };
  } catch (e) {
    console.log = origLog;
    console.error = origError;
    throw e;
  }
}

// ─── Six-stage guided flow (per TUI contract) ────────────────────────────
// Contract: docs/servo-installer/tui/bundle-default-contract.md
// Stages: diagnose → preview paths → confirm → install/update → verify → summary

function buildDiagnoseSummary(capturedOutput, backend) {
  // Try to parse JSON from captured output
  let diagnosis = null;
  for (const line of capturedOutput) {
    try { diagnosis = JSON.parse(line); break; } catch (_) { /* not JSON */ }
  }

  if (!diagnosis || !diagnosis.backends) {
    return { ok: false, summary: `${SYM_FAIL} Could not parse diagnose output.`, backends: [] };
  }

  const results = [];
  const targetBackends = backend === bundleBackend
    ? [agentsBackend, claudeBackend]
    : [backend];

  for (const bk of targetBackends) {
    const bd = diagnosis.backends[bk];
    if (!bd) {
      results.push({ backend: bk, ok: false, skillCount: 0, issueCount: 0, issues: [] });
      continue;
    }
    results.push({
      backend: bk,
      ok: bd.issue_count === 0,
      skillCount: bd.managed_install_count || 0,
      issueCount: bd.issue_count || 0,
      conflictCount: bd.conflict_count || 0,
      legacyTargetDirCount: bd.legacy_target_dir_count || 0,
      upgradeGuidance: bd.upgrade_guidance || null,
      issues: (bd.issues || []).slice(0, 5),
    });
  }
  return { ok: results.every((r) => r.ok), summary: null, backends: results };
}

function checkAwHealth() {
  const fs = require("node:fs");
  const path = require("node:path");
  const awDir = path.join(process.cwd(), ".servo");
  const checks = [];

  // .servo directory existence
  if (!fs.existsSync(awDir)) {
    return [{ item: ".servo directory", ok: false, detail: "missing - Harness not initialized" }];
  }

  // milestone dir
  const msDir = path.join(awDir, "milestone");
  if (fs.existsSync(msDir)) {
    try {
      const files = fs.readdirSync(msDir).filter((f) => f.endsWith(".md") && f !== "milestone-template.md");
      checks.push({ item: "milestones", ok: true, detail: `${files.length} artifacts` });
    } catch (_) {
      checks.push({ item: "milestones", ok: false, detail: "unreadable" });
    }
  } else {
    checks.push({ item: "milestones", ok: false, detail: "missing" });
  }

  // control-state
  const cs = path.join(awDir, "control-state.md");
  checks.push({
    item: "control-state",
    ok: fs.existsSync(cs),
    detail: fs.existsSync(cs) ? "present" : "missing",
  });

  // worktrack dir
  const wtDir = path.join(awDir, "worktrack");
  if (fs.existsSync(wtDir)) {
    try {
      const wts = fs.readdirSync(wtDir).filter((f) => f.endsWith(".md"));
      checks.push({ item: "worktrack artifacts", ok: true, detail: `${wts.length} files` });
    } catch (_) {
      checks.push({ item: "worktrack artifacts", ok: false, detail: "unreadable" });
    }
  } else {
    checks.push({ item: "worktrack artifacts", ok: false, detail: "missing" });
  }

  // repo backlogs
  const repoDir = path.join(awDir, "repo");
  if (fs.existsSync(repoDir)) {
    const backlogs = ["milestone-backlog.md", "worktrack-backlog.md", "snapshot-status.md"];
    for (const bl of backlogs) {
      const exists = fs.existsSync(path.join(repoDir, bl));
      checks.push({ item: bl.replace(".md", ""), ok: exists, detail: exists ? "present" : "missing" });
    }
  }

  return checks;
}

function buildTuiMigrationArgs(state, includeYes) {
  const args = [
    "migrate-runtime",
    "--from",
    "aw",
    "--to",
    "servo",
    "--backend",
    state.backend,
    "--reinstall",
  ];
  if (includeYes) {
    args.push("--yes");
  }
  return args;
}

function legacyRuntimeMigrationSummaryForTui(state) {
  return runtimeMigrationSummary(runtimeMigrationContext({
    backend: state.backend,
    from: "aw",
    to: "servo",
    json: false,
    yes: false,
    reinstall: true,
  }));
}

async function guidedRuntimeMigration(rl, state) {
  const summary = legacyRuntimeMigrationSummaryForTui(state);
  state.runtimeMigration = summary.state;

  if (summary.state === "no-runtime" || summary.state === "destination-only" || summary.state === "already-migrated") {
    return true;
  }

  refreshTui(state);
  console.log(`\n${SYM_ARROW} Legacy runtime migration check.`);
  printRuntimeMigrationSummary(summary);

  if (summary.issue_count > 0 || summary.action === "blocked") {
    console.log(`${SYM_FAIL} Runtime migration is blocked; guided install/update will not continue.`);
    console.log(`  ${colorDim("Preserve .aw, resolve the reported issue, then rerun guided install/update or migrate-runtime.")}`);
    return false;
  }

  const confirmation = (await question(
    rl,
    `\n${SYM_ARROW} Type ${colorYellow("migrate")} to copy .aw into .servo and reinstall ${state.backend}: `,
  )).trim().toLowerCase();
  if (confirmation !== "migrate") {
    console.log("Guided flow cancelled. No runtime migration performed.");
    return false;
  }

  state.currentStep = "runtime migration";
  refreshTui(state);
  console.log(`\n${SYM_ARROW} Migrating .aw runtime state into .servo.`);
  ensureTargetLogGitignore(state.targetRepo, state.logDir);
  const status = await runNodeOwned(buildTuiMigrationArgs(state, true));
  if (status !== 0) {
    console.log(`${SYM_FAIL} Runtime migration failed.`);
    return false;
  }
  state.runtimeMigrationPerformed = true;
  state.runtimeMigration = "migrated";
  console.log(`${SYM_OK} Runtime migration complete.`);
  return true;
}

async function guidedDiagnose(rl, state) {
  state.currentStep = "1/6 diagnose";
  refreshTui(state);
  console.log(`${SYM_ARROW} Diagnosing ${colorCyan(state.backend)} install...`);

  const { captured } = await captureConsole(
    () => runNodeOwned(["diagnose", "--backend", state.backend, "--json"]),
  );

  const diag = buildDiagnoseSummary(captured, state.backend);
  const awChecks = checkAwHealth();

  // ── Backend health ──
  console.log(`\n  ${colorBold("Backend Health")}`);
  for (const bk of diag.backends) {
    const icon = bk.ok ? SYM_OK : (bk.conflictCount > 0 ? SYM_WARN : SYM_FAIL);
    console.log(`  ${icon} ${colorCyan(bk.backend)}: ${bk.skillCount} skills installed, ${bk.issueCount} issues, ${bk.conflictCount} conflicts`);
    if (bk.legacyTargetDirCount > 0) {
      console.log(
        `     ${colorYellow("upgrade:")} ${bk.legacyTargetDirCount} legacy target dir(s) can be replaced by current servo target dirs`,
      );
      console.log(`     ${colorDim(bk.upgradeGuidance)}`);
    }
    if (!bk.ok && bk.issues.length > 0) {
      for (const iss of bk.issues.slice(0, 3)) {
        console.log(`     ${colorDim("- " + (iss.skill || iss.code || JSON.stringify(iss)))}`);
      }
      if (bk.issues.length > 3) console.log(`     ${colorDim("... and " + (bk.issues.length - 3) + " more")}`);
    }
  }

  // ── .servo health ──
  console.log(`\n  ${colorBold(".servo Control-plane Health")}`);
  for (const ck of awChecks) {
    const icon = ck.ok ? SYM_OK : SYM_FAIL;
    console.log(`  ${icon} ${ck.item}: ${ck.detail}`);
  }

  const overallOk = diag.ok && awChecks.every((c) => c.ok);
  if (overallOk) {
    console.log(`\n${SYM_OK} All checks passed.`);
  } else {
    console.log(`\n${SYM_WARN} Some checks found issues. Diagnose is not a blocking gate — you may continue.`);
  }
  return true;
}

async function guidedPreviewPaths(rl, state) {
  state.currentStep = "2/6 preview";
  refreshTui(state);
  console.log(`${SYM_ARROW} Checking paths for ${colorCyan(state.backend)}...`);

  const { captured } = await captureConsole(
    () => runNodeOwned(["check_paths_exist", "--backend", state.backend]),
  );

  // Parse conflict summary from captured output
  let totalConflicts = 0;
  const perBackend = {};
  for (const line of captured) {
    const m = line.match(/\[(\w+)\].*found (\d+) existing/);
    if (m) {
      perBackend[m[1]] = parseInt(m[2], 10);
      totalConflicts += parseInt(m[2], 10);
    }
  }

  if (totalConflicts > 0) {
    console.log(`\n${SYM_ARROW} ${totalConflicts} pre-existing path(s) — already installed:`);
    for (const [bk, count] of Object.entries(perBackend)) {
      console.log(`    ${colorCyan(bk)}: ${count} paths`);
    }

    // Split captured multi-line strings, extract only pre-existing path detail lines
    const allLines = captured.flatMap((s) => s.split("\n"));
    const existingLines = allLines.filter((l) => l.includes("existing target path"));
    if (existingLines.length > 0) {
      console.log(`\n  ${colorDim("Sample:")}`);
      for (const cl of existingLines.slice(0, 4)) {
        const short = cl.replace(/^\s*-\s*/, "").replace(/ \(existing.*\)/, "").trim();
        const parts = short.split("/");
        const compact = parts.length > 3 ? ".../" + parts.slice(-3).join("/") : short;
        console.log(`  ${colorDim("  " + compact)}`);
      }
      if (existingLines.length > 4) {
        console.log(`  ${colorDim("  ... and " + (existingLines.length - 4) + " more")}`);
      }
    }

    const choice = (await question(
      rl,
      `${SYM_ARROW} Run ${colorYellow("prune --all")} to clear before install? [${colorYellow("c")}=cancel / ${colorYellow("prune")}=prune] `,
    )).trim().toLowerCase();
    if (choice === "prune") {
      console.log(`\n${SYM_ARROW} Running prune --all --backend ${state.backend}...`);
      await runNodeOwned(["prune", "--all", "--backend", state.backend]);
      console.log(`${SYM_OK} Prune complete. Re-checking paths...`);
      return guidedPreviewPaths(rl, state);
    }
    console.log("Guided flow cancelled.");
    return false;
  }

  console.log(`${SYM_OK} No pre-existing paths — ready to install.`);
  return true;
}

async function guidedConfirm(rl, state) {
  state.currentStep = "3/6 confirm";
  refreshTui(state);
  console.log(`\n${SYM_ARROW} Ready to install/update ${colorCyan(state.backend)}.`);
  console.log(`  Target repo: ${colorDim(state.targetRepo)}`);
  console.log(`  Source:      ${state.source}`);

  const confirmation = (await question(
    rl,
    `\n${SYM_ARROW} Type ${colorYellow("yes")} to proceed, anything else to cancel: `,
  )).trim();
  if (confirmation !== "yes") {
    console.log("Guided flow cancelled. No changes made.");
    return false;
  }
  return true;
}

async function guidedInstall(rl, state) {
  state.currentStep = "4/6 install";
  refreshTui(state);
  console.log(`\n${SYM_ARROW} Installing ${colorCyan(state.backend)}...`);
  ensureTargetLogGitignore(state.targetRepo, state.logDir);
  const status = await runNodeOwned(["install", "--backend", state.backend]);
  if (status !== 0) {
    console.log(`${SYM_FAIL} Install failed for ${state.backend}.`);
    if (state.backend === bundleBackend) {
      console.log(`${SYM_WARN} Bundle partial: try single-backend recovery with ${colorYellow("servo-installer install --backend agents")} or ${colorYellow("--backend claude")}.`);
    }
    return false;
  }
  console.log(`${SYM_OK} Install complete for ${state.backend}.`);
  return true;
}

async function guidedVerify(rl, state) {
  state.currentStep = "5/6 verify";
  refreshTui(state);
  state.verifyResult = "running...";
  refreshTui(state);
  console.log(`\n${SYM_ARROW} Verifying ${colorCyan(state.backend)}...`);
  const status = await runNodeOwned(["verify", "--backend", state.backend]);
  state.verifyResult = status === 0 ? "passed" : "failed";
  if (status !== 0) {
    console.log(`${SYM_FAIL} Verification failed. Summary will be marked incomplete.`);
    return false;
  }
  console.log(`${SYM_OK} Verification passed.`);
  return true;
}

async function showRecoveryMenu(rl, state, failedStage, detail) {
  state.currentStep = "recovery";
  state.recoveryAttempts = (state.recoveryAttempts || 0) + 1;
  refreshTui(state);
  console.log("\n" + SYM_FAIL + " " + colorRed("Stage failed: " + failedStage));
  if (detail) { console.log("  " + colorDim(detail)); }
  console.log("\n" + colorBold("Recovery options:"));
  console.log("  1. Retry this stage");
  console.log("  2. Restart full guided flow");
  if (state.backend === bundleBackend && failedStage === "install") {
    console.log("  3. Retry single backend — " + colorYellow("servo-installer install --backend agents"));
    console.log("  4. Retry single backend — " + colorYellow("servo-installer install --backend claude"));
  }
  console.log("  c. Cancel and return to menu");
  const maxOpt = (state.backend === bundleBackend && failedStage === "install") ? "4" : "2";
  const choice = (await question(
    rl,
    "\n" + SYM_ARROW + " Choose recovery action [1-" + maxOpt + "/c]: ",
  )).trim().toLowerCase();
  if (choice === "1") { return "retry"; }
  if (choice === "2") { return "restart"; }
  if (choice === "3" && state.backend === bundleBackend && failedStage === "install") { return "retry-agents"; }
  if (choice === "4" && state.backend === bundleBackend && failedStage === "install") { return "retry-claude"; }
  return "cancel";
}

async function guidedSummary(rl, state, results) {
  state.currentStep = "6/6 summary";
  refreshTui(state);
  const ok = results.every(Boolean);
  const sep = "=".repeat(50);
  console.log("\n" + sep);
  if (ok) {
    console.log(SYM_OK + " " + colorBold("All stages completed successfully."));
    console.log("  Backend:    " + colorCyan(state.backend));
    console.log("  Version:    " + state.version);
    console.log("  Target:     " + colorDim(state.targetRepo));
    console.log("  Verify:     " + statusSymbol(results[4]) + " " + state.verifyResult);
    console.log("\n  " + SYM_OK + " " + colorGreen("Installation ready."));
    if (state.backend === bundleBackend) {
      console.log("  " + colorDim("Both agents and claude backends are deployed."));
    }
    console.log("  " + colorDim("Legacy target dir cleanup uses the same update flow: servo-installer update --backend " + state.backend + " --yes"));
  } else {
    console.log(SYM_FAIL + " " + colorBold("Guided flow incomplete — partial state."));
    var stageNames = ["diagnose", "preview", "confirm", "install", "verify"];
    results.forEach(function(pass, i) {
      console.log("  " + statusSymbol(pass) + " Stage " + (i + 1) + ": " + stageNames[i]);
    });
    console.log("\n" + SYM_WARN + " Recovery options:");
    if (!results[3] && state.backend === bundleBackend) {
      console.log("  → " + colorYellow("servo-installer install --backend agents") + "  (retry single backend)");
      console.log("  → " + colorYellow("servo-installer install --backend claude") + "  (retry single backend)");
    }
    if (!results[4]) {
      console.log("  → " + colorYellow("servo-installer verify --backend " + state.backend) + "  (re-verify)");
    }
    console.log("  → Re-run guided flow from TUI menu (option 1)");
    state.recoveryHint = results[3] ? "verify" : "install";
    state.failedStages = stageNames.filter(function(_, i) { return !results[i]; });
  }
  console.log(sep);
  return ok;
}

async function runGuidedFullFlow(rl, state) {
  state.recoveryAttempts = 0;
  state.recoveryHint = null;
  const results = [false, false, false, false, false];

  // Stage 1: Diagnose (non-blocking)
  results[0] = await guidedDiagnose(rl, state);
  await pause(rl);

  const migrationOk = await guidedRuntimeMigration(rl, state);
  if (!migrationOk) { return; }
  if (state.runtimeMigrationPerformed) {
    await pause(rl);
    results[1] = true;
    results[2] = true;
    results[3] = true;
    state.currentStep = "5/6 verify";
    refreshTui(state);
    state.verifyResult = "running...";
    const vStatus = await runNodeOwned(["verify", "--backend", state.backend]);
    state.verifyResult = vStatus === 0 ? "passed" : "failed";
    results[4] = vStatus === 0;
    if (results[4]) {
      console.log(`${SYM_OK} Verification passed.`);
    } else {
      console.log(`${SYM_FAIL} Verification failed. Summary will be marked incomplete.`);
    }
    await pause(rl);
    await guidedSummary(rl, state, results);
    await pause(rl);
    return;
  }

  // Stage 2: Preview paths (blocking)
  results[1] = await guidedPreviewPaths(rl, state);
  if (!results[1]) {
    const action = await showRecoveryMenu(rl, state, "preview", "Path conflicts must be resolved.");
    if (action === "restart") { return runGuidedFullFlow(rl, state); }
    return;
  }
  await pause(rl);

  // Stage 3: Confirm (explicit gate)
  results[2] = await guidedConfirm(rl, state);
  if (!results[2]) { return; }

  // Stage 4: Install with recovery loop
  let installOk = false;
  while (!installOk) {
    results[3] = await guidedInstall(rl, state);
    if (!results[3]) {
      const action = await showRecoveryMenu(rl, state, "install",
        "Install failed for " + state.backend + ".");
      if (action === "retry") { continue; }
      if (action === "retry-agents") {
        console.log("\n" + SYM_ARROW + " Retrying agents only...");
        await runNodeOwned(["install", "--backend", "agents"]);
        continue;
      }
      if (action === "retry-claude") {
        console.log("\n" + SYM_ARROW + " Retrying claude only...");
        await runNodeOwned(["install", "--backend", "claude"]);
        continue;
      }
      if (action === "restart") { return runGuidedFullFlow(rl, state); }
      break;
    }
    installOk = true;
  }

  if (installOk) {
    await pause(rl);

    // Stage 5: Verify with recovery
    results[4] = await guidedVerify(rl, state);
    if (!results[4]) {
      const action = await showRecoveryMenu(rl, state, "verify",
        "Verification found issues for " + state.backend + ".");
      if (action === "retry") {
        results[4] = await guidedVerify(rl, state);
      } else if (action === "restart") {
        return runGuidedFullFlow(rl, state);
      }
    }
  }

  await pause(rl);

  // Stage 6: Summary
  await guidedSummary(rl, state, results);
  await pause(rl);
}

// Legacy compact guided update (single command: update --yes)
async function runGuidedUpdateFlow(rl, state) {
  const backend = state.backend;

  state.currentStep = "update:diagnose";
  refreshTui(state);
  console.log(`\n${SYM_ARROW} Step 1: Diagnose current ${backend} install.`);
  const diagnoseStatus = await runNodeOwned(["diagnose", "--backend", backend, "--json"]);
  if (diagnoseStatus !== 0) {
    console.log(`${SYM_WARN} Diagnose found issues — update may not succeed as expected.`);
    const proceed = (await question(
      rl,
      `${SYM_ARROW} Continue anyway? Type ${colorYellow("yes")} to continue: `,
    )).trim();
    if (proceed !== "yes") {
      console.log("Update cancelled.");
      await pause(rl);
      return;
    }
  }

  state.currentStep = "update:preview";
  refreshTui(state);
  console.log(`\n${SYM_ARROW} Step 2: Review update dry-run plan.`);
  const dryRunStatus = await runNodeOwned(["update", "--backend", backend]);
  if (dryRunStatus !== 0) {
    console.log(`${SYM_FAIL} Update plan failed; not applying.`);
    await pause(rl);
    return;
  }

  state.currentStep = "update:confirm";
  refreshTui(state);
  const confirmation = (await question(
    rl,
    `${SYM_ARROW} Step 3: Type ${colorYellow("yes")} to apply: `,
  )).trim();
  if (confirmation === "yes") {
    state.currentStep = "update:install";
    refreshTui(state);
    console.log(`\n${SYM_ARROW} Step 4: Applying update.`);
    ensureTargetLogGitignore(state.targetRepo, state.logDir);
    await runNodeOwned(["update", "--backend", backend, "--yes"]);
    state.currentStep = "update:verify";
    refreshTui(state);
    state.verifyResult = "running...";
    const vStatus = await runNodeOwned(["verify", "--backend", backend]);
    state.verifyResult = vStatus === 0 ? "passed" : "failed";
  } else {
    console.log("Update cancelled.");
  }
  await pause(rl);
}

const backendCycle = [agentsBackend, claudeBackend, bundleBackend];

function cycleBackend(current) {
  const index = backendCycle.indexOf(current);
  return backendCycle[(index + 1) % backendCycle.length];
}

// Fixed-layout TUI state
let tuiState = null;

function initTuiState(backend, version, source, targetRepo) {
  return {
    version: version || "unknown",
    source: source || packageSource,
    targetRepo: targetRepo || process.cwd(),
    backend: backend,
    currentStep: "menu",
    verifyResult: "not yet run",
  };
}

const LINE_SEPARATOR = haveColor
  ? `${SGR_DIM}${"─".repeat(Math.min(process.stdout.columns || 80, 120))}${SGR_RESET}`
  : `${"-".repeat(Math.min(process.stdout.columns || 80, 120))}`;

function renderStatusBar(state) {
  const cols = process.stdout.columns || 80;
  const width = Math.min(cols, 120);
  const version = state.version.length > 20 ? state.version.slice(0, 19) + "…" : state.version;
  const repo = state.targetRepo.length > width - 18
    ? "..." + state.targetRepo.slice(-(width - 21))
    : state.targetRepo;

  const lines = [
    `${colorBold("AW Installer")}  ${colorDim("v" + version)}`,
    `${SYM_ARROW} ${state.currentStep}  |  backend: ${colorCyan(state.backend)}  |  source: ${state.source}`,
    `repo: ${colorDim(repo)}`,
    LINE_SEPARATOR,
    "",
    "",
    "",
  ];

  // Pad status area to exactly STATUS_LINES
  while (lines.length < STATUS_LINES) {
    lines.push("");
  }

  process.stdout.write(
    `${CSI_SAVE_CURSOR}${csiCursorTo(0, 0)}${CSI_HIDE_CURSOR}${
      lines.slice(0, STATUS_LINES).join("\n")
    }${CSI_SHOW_CURSOR}${CSI_RESTORE_CURSOR}`,
  );
}

function writeContent(text) {
  process.stdout.write(`${CSI_SAVE_CURSOR}${csiCursorTo(STATUS_LINES + 1, 0)}${csiEraseToEnd()}${text}${CSI_RESTORE_CURSOR}`);
}

function refreshTui(state) {
  if (!ttyOut) return;
  renderStatusBar(state);
  process.stdout.write(csiCursorTo(STATUS_LINES + 1, 0));
  process.stdout.write(csiEraseToEnd());
}

function statusSymbol(pass) {
  return pass ? SYM_OK : SYM_FAIL;
}

async function runTui(logDir) {
  if (!ttyIn || !ttyOut) {
    console.error("servo-installer tui requires an interactive terminal.");
    return 1;
  }

  const version = tryReadPackageVersionAt(join(__dirname, "..", "..", "..", "..", "package.json")) || "unknown";
  const targetRepo = resolveTuiTargetRepoRoot();
  const effectiveLogDir = logDir || defaultInstallerLogDir(targetRepo);
  const logger = createRunLogger({
    logDir: effectiveLogDir,
    args: ["tui"],
    targetRepoRoot: targetRepo,
    tui: true,
  });

  return await withRunLogger(logger, async () => {
    console.log(`servo-installer log location: ${effectiveLogDir}`);

    // Bundle default per TUI contract
    tuiState = initTuiState(bundleBackend, version, packageSource, targetRepo);
    tuiState.logDir = effectiveLogDir;

    try {
      process.stdout.write(CSI_CLEAR_SCREEN);
      process.stdout.write(CSI_HIDE_CURSOR);

      const menuOptions = [
        "Guided install/update (6-stage: diagnose → preview → confirm → install → verify → summary)",
        "Quick update (compact 4-step)",
        "Diagnose current install",
        "Verify current install",
        "Show update dry-run plan",
        "Exit",
      ];

      while (true) {
        tuiState.currentStep = "menu";
        refreshTui(tuiState);
        process.stdout.write(`\n${colorBold("TUI Menu")}  ${colorDim("backend: " + tuiState.backend + "  |  b to cycle: " + backendCycle.join("/"))}\n`);

        const idx = await interactiveSelect(null, menuOptions, " ");

        if (idx === -1) { break; }

        if (idx === 0) {
          await runGuidedFullFlow(null, tuiState);
        } else if (idx === 1) {
          tuiState.currentStep = "guided-update";
          await runGuidedUpdateFlow(null, tuiState);
        } else if (idx === 2) {
          tuiState.currentStep = "diagnose";
          refreshTui(tuiState);
          process.stdout.write(`\n${SYM_ARROW} Running diagnose --backend ${tuiState.backend}...\n`);
          await runNodeOwned(["diagnose", "--backend", tuiState.backend, "--json"]);
          await pause(null);
        } else if (idx === 3) {
          tuiState.currentStep = "verify";
          tuiState.verifyResult = "running...";
          refreshTui(tuiState);
          process.stdout.write(`\n${SYM_ARROW} Running verify --backend ${tuiState.backend}...\n`);
          const vStatus = await runNodeOwned(["verify", "--backend", tuiState.backend]);
          tuiState.verifyResult = vStatus === 0 ? "passed" : "failed";
          await pause(null);
        } else if (idx === 4) {
          tuiState.currentStep = "dry-run";
          refreshTui(tuiState);
          process.stdout.write(`\n${SYM_ARROW} Running update --backend ${tuiState.backend} (dry-run)...\n`);
          await runNodeOwned(["update", "--backend", tuiState.backend]);
          await pause(null);
        } else if (idx === 5) {
          break;
        }

        tuiState.currentStep = "menu";
      }
      return 0;
    } finally {
      process.stdout.write(CSI_SHOW_CURSOR);
      process.stdout.write(csiCursorTo(STATUS_LINES + 1, 0));
      process.stdout.write(csiEraseToEnd());
      try { process.stdin.setRawMode(false); } catch (_) { /* ignore */ }
    }
  });
}


async function main() {
  const parsedLogging = parseLogDirOption(process.argv.slice(2));
  if (parsedLogging.error) {
    console.error(`error: ${parsedLogging.error}`);
    return 1;
  }
  const args = parsedLogging.args;

  // Package/runtime agents and Claude deploy commands are Node-owned. Python
  // deploy sources may remain in the repository as reference/test assets, but
  // this distribution entrypoint must not fall back to Python.
  if (args.length === 0) {
    if (process.stdin.isTTY && process.stdout.isTTY) {
      return runTui(parsedLogging.logDir);
    }
    printHelp();
    return 0;
  }

  if (args[0] === "--help" || args[0] === "-h") {
    printHelp();
    return 0;
  }

  if (args[0] === "--version" || args[0] === "-V") {
    printVersion();
    return 0;
  }

  if (args[0] === "tui") {
    return runTui(parsedLogging.logDir);
  }

  const targetRepoRoot = process.env.SERVO_HARNESS_TARGET_REPO_ROOT || process.cwd();
  const logger = createRunLogger({
    logDir: parsedLogging.logDir,
    args,
    targetRepoRoot,
    tui: false,
  });
  return await withRunLogger(logger, () => runNodeOwned(args));
}

if (require.main === module) {
  main()
    .then((status) => {
      process.exit(status);
    })
    .catch((error) => {
      console.error(`servo-installer failed: ${error.message}`);
      process.exit(1);
    });
}

module.exports = {
  buildNodeAgentsContext,
  buildNodeBackendContext,
  buildNodeGithubSourceContext,
  buildInstallPlan,
  buildRuntimeMarker,
  canonicalSourceMetadata,
  assertManagedDirectoryIdentityCurrent,
  childDirectoryIdentity,
  collectAllKnownTargetDirs,
  collectLegacyPathConflicts,
  legacyTargetDirMigrationSummary,
  collectPathConflicts,
  collectTargetDirMetadata,
  collectUpdateTargetEntryIssues,
  computePayloadFingerprint,
  crc32,
  applyPromptInputKey,
  dedupeIssues,
  describeExistingTargetPath,
  diagnosticSummary,
  downloadGithubArchive,
  defaultInstallerLogDir,
  ensureTargetLogGitignore,
  exactSensitiveTargetRepoRoots,
  expectedTargetDirs,
  applyUpdateContext,
  checkPathsExistSummary,
  installBackendPayloads,
  isUpdateBlockingIssue,
  githubArchiveRefPath,
  githubArchiveUrl,
  githubSourceRootFromArchiveBuffer,
  loadBindingPayloads,
  loadRuntimeMarker,
  normalizeRelativePath,
  parseNodeCheckPathsExistArgs,
  parseNodeDiagnoseJsonArgs,
  parseNodeDiagnoseArgs,
  parseNodeInstallArgs,
  parseNodeMigrateRuntimeArgs,
  parseNodePruneArgs,
  parseNodeUnsupportedPruneMissingAllArgs,
  parseNodeUnsupportedUpdateJsonYesArgs,
  parseNodeUpdateDryRunArgs,
  parseNodeUpdateJsonArgs,
  parseNodeUpdateYesArgs,
  parseNodeVerifyArgs,
  pathSafetyPolicy,
  payloadTargetMetadata,
  printVerifyResult,
  printDiagnosticSummary,
  printUpdatePlan,
  pruneBackendManagedInstalls,
  recursiveSensitiveTargetRepoRoots,
  resolveExistingOrLexical,
  runtimeMigrationSummary,
  runNodeOwned,
  updatePlanSummary,
  validateSourceRepoRoot,
  validateTargetRepoRoot,
  validateGithubRef,
  validateGithubRepo,
  validateSha256Digest,
  verifyAgentsBackend,
  verifyDeployedSkill,
};
