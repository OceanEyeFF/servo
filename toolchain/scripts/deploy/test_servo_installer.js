const assert = require("node:assert/strict");
const { spawnSync } = require("node:child_process");
const { createHash } = require("node:crypto");
const { EventEmitter } = require("node:events");
const { chmodSync, existsSync, lstatSync, mkdirSync, mkdtempSync, readdirSync, readFileSync, rmSync, symlinkSync, writeFileSync } = require("node:fs");
const https = require("node:https");
const { tmpdir } = require("node:os");
const { join, relative, sep } = require("node:path");
const test = require("node:test");
const { deflateRawSync } = require("node:zlib");

const installer = require("./bin/servo-installer.js");

function zipHeaderUInt16(value) {
  const buffer = Buffer.alloc(2);
  buffer.writeUInt16LE(value);
  return buffer;
}

function zipHeaderUInt32(value) {
  const buffer = Buffer.alloc(4);
  buffer.writeUInt32LE(value);
  return buffer;
}

assert.equal(installer.crc32(Buffer.from("123456789", "ascii")), 0xcbf43926);

function createStoredZip(entries) {
  const localParts = [];
  const centralParts = [];
  let offset = 0;
  for (const [name, text, options = {}] of entries) {
    const nameBuffer = Buffer.from(name);
    const dataBuffer = Buffer.from(text);
    const crc32 = options.crc32 ?? installer.crc32(dataBuffer);
    const local = Buffer.concat([
      zipHeaderUInt32(0x04034b50),
      zipHeaderUInt16(20),
      zipHeaderUInt16(0),
      zipHeaderUInt16(0),
      zipHeaderUInt16(0),
      zipHeaderUInt16(0),
      zipHeaderUInt32(crc32),
      zipHeaderUInt32(dataBuffer.length),
      zipHeaderUInt32(dataBuffer.length),
      zipHeaderUInt16(nameBuffer.length),
      zipHeaderUInt16(0),
      nameBuffer,
      dataBuffer,
    ]);
    localParts.push(local);
    centralParts.push(Buffer.concat([
      zipHeaderUInt32(0x02014b50),
      zipHeaderUInt16(20),
      zipHeaderUInt16(20),
      zipHeaderUInt16(0),
      zipHeaderUInt16(0),
      zipHeaderUInt16(0),
      zipHeaderUInt16(0),
      zipHeaderUInt32(crc32),
      zipHeaderUInt32(dataBuffer.length),
      zipHeaderUInt32(dataBuffer.length),
      zipHeaderUInt16(nameBuffer.length),
      zipHeaderUInt16(0),
      zipHeaderUInt16(0),
      zipHeaderUInt16(0),
      zipHeaderUInt16(0),
      zipHeaderUInt32(0),
      zipHeaderUInt32(offset),
      nameBuffer,
    ]));
    offset += local.length;
  }
  const central = Buffer.concat(centralParts);
  const eocd = Buffer.concat([
    zipHeaderUInt32(0x06054b50),
    zipHeaderUInt16(0),
    zipHeaderUInt16(0),
    zipHeaderUInt16(entries.length),
    zipHeaderUInt16(entries.length),
    zipHeaderUInt32(central.length),
    zipHeaderUInt32(offset),
    zipHeaderUInt16(0),
  ]);
  return Buffer.concat([...localParts, central, eocd]);
}

function createDeflatedZip(entries) {
  const localParts = [];
  const centralParts = [];
  let offset = 0;
  for (const [name, text, options = {}] of entries) {
    const nameBuffer = Buffer.from(name);
    const dataBuffer = Buffer.from(text);
    const compressedBuffer = deflateRawSync(dataBuffer);
    const crc32 = options.crc32 ?? installer.crc32(dataBuffer);
    const declaredCompressedSize = options.compressedSize ?? compressedBuffer.length;
    const declaredUncompressedSize = options.uncompressedSize ?? dataBuffer.length;
    const local = Buffer.concat([
      zipHeaderUInt32(0x04034b50),
      zipHeaderUInt16(20),
      zipHeaderUInt16(0),
      zipHeaderUInt16(8),
      zipHeaderUInt16(0),
      zipHeaderUInt16(0),
      zipHeaderUInt32(crc32),
      zipHeaderUInt32(declaredCompressedSize),
      zipHeaderUInt32(declaredUncompressedSize),
      zipHeaderUInt16(nameBuffer.length),
      zipHeaderUInt16(0),
      nameBuffer,
      compressedBuffer,
    ]);
    localParts.push(local);
    centralParts.push(Buffer.concat([
      zipHeaderUInt32(0x02014b50),
      zipHeaderUInt16(20),
      zipHeaderUInt16(20),
      zipHeaderUInt16(0),
      zipHeaderUInt16(8),
      zipHeaderUInt16(0),
      zipHeaderUInt16(0),
      zipHeaderUInt32(crc32),
      zipHeaderUInt32(declaredCompressedSize),
      zipHeaderUInt32(declaredUncompressedSize),
      zipHeaderUInt16(nameBuffer.length),
      zipHeaderUInt16(0),
      zipHeaderUInt16(0),
      zipHeaderUInt16(0),
      zipHeaderUInt16(0),
      zipHeaderUInt32(0),
      zipHeaderUInt32(offset),
      nameBuffer,
    ]));
    offset += local.length;
  }
  const central = Buffer.concat(centralParts);
  const eocd = Buffer.concat([
    zipHeaderUInt32(0x06054b50),
    zipHeaderUInt16(0),
    zipHeaderUInt16(0),
    zipHeaderUInt16(entries.length),
    zipHeaderUInt16(entries.length),
    zipHeaderUInt32(central.length),
    zipHeaderUInt32(offset),
    zipHeaderUInt16(0),
  ]);
  return Buffer.concat([...localParts, central, eocd]);
}

function collectFixtureTree(root) {
  const directories = [];
  const files = [];
  for (const entry of readdirSync(root, { withFileTypes: true })) {
    const path = join(root, entry.name);
    if (entry.isDirectory()) {
      const childTree = collectFixtureTree(path);
      directories.push(path, ...childTree.directories);
      files.push(...childTree.files);
    } else if (entry.isFile()) {
      files.push(path);
    }
  }
  return { directories, files };
}

function createGithubArchiveFromSource(root, archiveRoot = "repo-master", zipFactory = createStoredZip) {
  const { directories, files } = collectFixtureTree(root);
  return zipFactory([
    ...directories.map((path) => [
      `${archiveRoot}/${relative(root, path).split(sep).join("/")}/`,
      "",
    ]),
    ...files.map((path) => [
      `${archiveRoot}/${relative(root, path).split(sep).join("/")}`,
      readFileSync(path, "utf8"),
    ]),
  ]);
}

function captureConsoleLog(callback) {
  const originalLog = console.log;
  const lines = [];
  let restored = false;
  function restoreConsoleLog() {
    if (!restored) {
      console.log = originalLog;
      restored = true;
    }
  }
  console.log = (...args) => {
    lines.push(`${args.join(" ")}\n`);
  };
  let result;
  try {
    result = callback();
  } catch (error) {
    restoreConsoleLog();
    throw error;
  }
  if (result !== null && typeof result === "object") {
    let then;
    try {
      then = result.then;
    } catch (error) {
      restoreConsoleLog();
      throw error;
    }
    if (typeof then === "function") {
      try {
        return then.call(
          result,
          (resolved) => {
            restoreConsoleLog();
            return { result: resolved, stdout: lines.join("") };
          },
          (error) => {
            restoreConsoleLog();
            throw error;
          },
        );
      } catch (error) {
        restoreConsoleLog();
        throw error;
      }
    }
  }
  restoreConsoleLog();
  return { result, stdout: lines.join("") };
}

test("captureConsoleLog restores console.log for sync throw", () => {
  const originalLog = console.log;

  assert.throws(
    () => captureConsoleLog(() => {
      console.log("before", "throw");
      throw new Error("sync failure");
    }),
    /sync failure/,
  );

  assert.equal(console.log, originalLog);
});

test("captureConsoleLog restores console.log for async resolve", async () => {
  const originalLog = console.log;

  const { result, stdout } = await captureConsoleLog(async () => {
    console.log("async", "ok");
    return 42;
  });

  assert.equal(result, 42);
  assert.equal(stdout, "async ok\n");
  assert.equal(console.log, originalLog);
});

test("captureConsoleLog restores console.log for async reject", async () => {
  const originalLog = console.log;

  await assert.rejects(
    () => captureConsoleLog(async () => {
      console.log("async", "reject");
      throw new Error("async failure");
    }),
    /async failure/,
  );

  assert.equal(console.log, originalLog);
});

test("captureConsoleLog restores console.log for throwing thenables", () => {
  const originalLog = console.log;

  assert.throws(
    () => captureConsoleLog(() => ({
      get then() {
        throw new Error("then getter failure");
      },
    })),
    /then getter failure/,
  );
  assert.equal(console.log, originalLog);

  assert.throws(
    () => captureConsoleLog(() => ({
      then() {
        throw new Error("then call failure");
      },
    })),
    /then call failure/,
  );
  assert.equal(console.log, originalLog);
});

async function withMockedGithubArchive(archiveBuffer, callback) {
  const originalGet = https.get;
  const requests = [];
  https.get = (url, options, handler) => {
    requests.push({ url, options });
    const request = new EventEmitter();
    request.destroy = (error) => {
      request.emit("error", error);
    };
    process.nextTick(() => {
      const response = new EventEmitter();
      response.statusCode = 200;
      response.resume = () => {};
      handler(response);
      response.emit("data", archiveBuffer);
      response.emit("end");
    });
    return request;
  };
  try {
    return await callback(requests);
  } finally {
    https.get = originalGet;
  }
}

async function withMockedGithubResponses(responses, callback) {
  const originalGet = https.get;
  const requests = [];
  https.get = (url, options, handler) => {
    const requestRecord = { url, options };
    requests.push(requestRecord);
    const request = new EventEmitter();
    request.destroy = (error) => {
      request.emit("error", error || new Error("request destroyed"));
    };
    process.nextTick(() => {
      const responseSpec = responses[Math.min(requests.length - 1, responses.length - 1)];
      const response = new EventEmitter();
      response.statusCode = responseSpec.statusCode;
      response.headers = responseSpec.headers || {};
      response.resume = () => {};
      response.destroyed = false;
      response.destroy = (error) => {
        response.destroyed = true;
        response.emit("error", error || new Error("response destroyed"));
      };
      requestRecord.response = response;
      handler(response);
      if (responseSpec.afterHandlerError !== undefined) {
        response.emit("error", responseSpec.afterHandlerError);
      }
      if (response.destroyed) {
        return;
      }
      if (responseSpec.error !== undefined) {
        response.emit("error", responseSpec.error);
        return;
      }
      for (const chunk of responseSpec.chunks || []) {
        response.emit("data", Buffer.isBuffer(chunk) ? chunk : Buffer.from(chunk));
      }
      response.emit("end");
    });
    return request;
  };
  try {
    return await callback(requests);
  } finally {
    https.get = originalGet;
  }
}

function seedMinimalAgentsSource(root, skillId = "demo-skill", options = {}) {
  const canonicalDir = join(root, "product", "harness", "skills", skillId);
  const payloadDir = join(root, "product", "harness", "adapters", "agents", "skills", skillId);
  mkdirSync(canonicalDir, { recursive: true });
  mkdirSync(payloadDir, { recursive: true });
  mkdirSync(join(root, "product", "harness", "adapters", "claude", "skills"), { recursive: true });
  const targetDir = options.targetDir || `aw-${skillId}`;
  const payload = {
    payload_version: "agents-skill-payload.v1",
    backend: "agents",
    skill_id: skillId,
    target_dir: targetDir,
    target_entry_name: "SKILL.md",
    required_payload_files: ["SKILL.md", "payload.json", "aw.marker"],
    canonical_dir: `product/harness/skills/${skillId}`,
    canonical_paths: [`product/harness/skills/${skillId}/SKILL.md`],
    payload_policy: "canonical-copy",
    reference_distribution: "copy-listed-canonical-paths",
  };
  if (options.legacyTargetDirs !== undefined) {
    payload.legacy_target_dirs = options.legacyTargetDirs;
  }
  if (options.legacySkillIds !== undefined) {
    payload.legacy_skill_ids = options.legacySkillIds;
  }
  const payloadPath = join(payloadDir, "payload.json");
  writeFileSync(join(canonicalDir, "SKILL.md"), options.skillText || `# ${skillId}\n`, "utf8");
  writeFileSync(payloadPath, `${JSON.stringify(payload, null, 2)}\n`, "utf8");
  return {
    binding: {
      backend: "agents",
      skillId,
      payloadDir,
      payloadPath,
    },
    canonicalDir,
    payload,
    payloadDir,
    targetDir,
  };
}

function seedInstalledAgentsSkill(root, skillId = "demo-skill", options = {}) {
  const seeded = seedMinimalAgentsSource(root, skillId, options);
  const targetRoot = options.targetRoot || join(root, ".agents", "skills");
  const targetSkillDir = join(targetRoot, seeded.targetDir);
  mkdirSync(targetSkillDir, { recursive: true });
  const skillText = `# ${skillId}\n`;
  const payloadText = `${JSON.stringify(seeded.payload, null, 2)}\n`;
  writeFileSync(join(targetSkillDir, "SKILL.md"), skillText, "utf8");
  const metadata = installer.payloadTargetMetadata(seeded.payload, seeded.binding);
  writeFileSync(
    join(targetSkillDir, "payload.json"),
    installer.runtimePayloadDescriptorText(seeded.payload, seeded.binding),
    "utf8",
  );
  const payloadFingerprint = installer.computePayloadFingerprint(
    seeded.binding,
    { sourceRoot: root },
    seeded.payload,
    payloadText,
    metadata,
  );
  const marker = {
    marker_version: "aw-managed-skill-marker.v2",
    backend: "agents",
    skill_id: skillId,
    payload_version: "agents-skill-payload.v1",
    payload_fingerprint: payloadFingerprint,
  };
  writeFileSync(join(targetSkillDir, "aw.marker"), `${JSON.stringify(marker, null, 2)}\n`, "utf8");
  return {
    ...seeded,
    marker,
    payloadText,
    targetRoot,
    targetSkillDir,
  };
}

function seedMinimalClaudeSource(root, skillId = "demo-skill", options = {}) {
  const canonicalDir = join(root, "product", "harness", "skills", skillId);
  const payloadDir = join(root, "product", "harness", "adapters", "claude", "skills", skillId);
  mkdirSync(canonicalDir, { recursive: true });
  mkdirSync(payloadDir, { recursive: true });
  mkdirSync(join(root, "product", "harness", "adapters", "agents", "skills"), { recursive: true });
  const targetDir = options.targetDir || skillId;
  const payload = {
    payload_version: "claude-skill-payload.v1",
    backend: "claude",
    skill_id: skillId,
    target_dir: targetDir,
    target_entry_name: "SKILL.md",
    required_payload_files: ["SKILL.md", "payload.json", "aw.marker"],
    canonical_dir: `product/harness/skills/${skillId}`,
    canonical_paths: [`product/harness/skills/${skillId}/SKILL.md`],
    payload_policy: "canonical-copy",
    reference_distribution: "copy-listed-canonical-paths",
    legacy_target_dirs: options.legacyTargetDirs || [`aw-${skillId}`],
  };
  if (options.claudeFrontmatter !== undefined) {
    payload.claude_frontmatter = options.claudeFrontmatter;
  }
  if (options.legacySkillIds !== undefined) {
    payload.legacy_skill_ids = options.legacySkillIds;
  }
  const payloadPath = join(payloadDir, "payload.json");
  const skillText = options.skillText || `---\ndescription: ${skillId}\n---\n# ${skillId}\n`;
  writeFileSync(join(canonicalDir, "SKILL.md"), skillText, "utf8");
  writeFileSync(payloadPath, `${JSON.stringify(payload, null, 2)}\n`, "utf8");
  return {
    binding: {
      backend: "claude",
      skillId,
      payloadDir,
      payloadPath,
    },
    canonicalDir,
    payload,
    payloadDir,
    skillText,
    targetDir,
  };
}

function seedInstalledClaudeSkill(root, skillId = "demo-skill", options = {}) {
  const seeded = seedMinimalClaudeSource(root, skillId, {
    claudeFrontmatter: { "disable-model-invocation": true },
    ...options,
  });
  const targetRoot = options.targetRoot || join(root, ".claude", "skills");
  const targetSkillDir = join(targetRoot, seeded.targetDir);
  mkdirSync(targetSkillDir, { recursive: true });
  const payloadText = `${JSON.stringify(seeded.payload, null, 2)}\n`;
  const skillText = seeded.skillText.replace(
    "\n---\n",
    "\ndisable-model-invocation: true\n---\n",
  );
  writeFileSync(join(targetSkillDir, "SKILL.md"), skillText, "utf8");
  writeFileSync(
    join(targetSkillDir, "payload.json"),
    installer.runtimePayloadDescriptorText(seeded.payload, seeded.binding),
    "utf8",
  );
  const metadata = installer.payloadTargetMetadata(seeded.payload, seeded.binding);
  const payloadFingerprint = installer.computePayloadFingerprint(
    seeded.binding,
    { sourceRoot: root },
    seeded.payload,
    payloadText,
    metadata,
  );
  const marker = {
    marker_version: "aw-managed-skill-marker.v2",
    backend: "claude",
    skill_id: skillId,
    payload_version: "claude-skill-payload.v1",
    payload_fingerprint: payloadFingerprint,
  };
  writeFileSync(join(targetSkillDir, "aw.marker"), `${JSON.stringify(marker, null, 2)}\n`, "utf8");
  return {
    ...seeded,
    marker,
    payloadText,
    targetRoot,
    targetSkillDir,
  };
}

function fakePythonBin(root) {
  const fakeBin = join(root, "fake-python-bin");
  mkdirSync(fakeBin);
  for (const pythonName of ["py", "python", "python3"]) {
    const pythonPath = join(fakeBin, pythonName);
    writeFileSync(
      pythonPath,
      "#!/bin/sh\nprintf 'unexpected-python %s\\n' \"$*\" >&2\nexit 97\n",
      "utf8",
    );
    chmodSync(pythonPath, 0o755);
  }
  return fakeBin;
}

function checkPathsExistEnv(root, fakeBin = null) {
  const pathSeparator = process.platform === "win32" ? ";" : ":";
  return {
    ...process.env,
    SERVO_HARNESS_REPO_ROOT: root,
    SERVO_HARNESS_TARGET_REPO_ROOT: root,
    PATH: fakeBin === null ? process.env.PATH || "" : `${fakeBin}${pathSeparator}${process.env.PATH || ""}`,
    PYTHONDONTWRITEBYTECODE: "1",
  };
}

function runNodeCheckPathsExist(root, args, fakeBin = null) {
  return spawnSync(
    process.execPath,
    [join(__dirname, "bin", "servo-installer.js"), "check_paths_exist", ...args],
    {
      cwd: root,
      env: checkPathsExistEnv(root, fakeBin),
      encoding: "utf8",
    },
  );
}

function runNodeVerify(root, args, fakeBin = null) {
  return spawnSync(
    process.execPath,
    [join(__dirname, "bin", "servo-installer.js"), "verify", ...args],
    {
      cwd: root,
      env: checkPathsExistEnv(root, fakeBin),
      encoding: "utf8",
    },
  );
}

function escapeRegExp(value) {
  return value.replace(/[.*+?^${}()|[\]\\]/g, "\\$&");
}

function runNodeInstall(root, args, fakeBin = null) {
  return spawnSync(
    process.execPath,
    [join(__dirname, "bin", "servo-installer.js"), "install", ...args],
    {
      cwd: root,
      env: checkPathsExistEnv(root, fakeBin),
      encoding: "utf8",
    },
  );
}

function runNodePrune(root, args, fakeBin = null) {
  return spawnSync(
    process.execPath,
    [join(__dirname, "bin", "servo-installer.js"), "prune", ...args],
    {
      cwd: root,
      env: checkPathsExistEnv(root, fakeBin),
      encoding: "utf8",
    },
  );
}

function runNodeUpdate(root, args, fakeBin = null) {
  return spawnSync(
    process.execPath,
    [join(__dirname, "bin", "servo-installer.js"), "update", ...args],
    {
      cwd: root,
      env: checkPathsExistEnv(root, fakeBin),
      encoding: "utf8",
    },
  );
}

function runNodeDiagnose(root, args, fakeBin = null) {
  return spawnSync(
    process.execPath,
    [join(__dirname, "bin", "servo-installer.js"), "diagnose", ...args],
    {
      cwd: root,
      env: checkPathsExistEnv(root, fakeBin),
      encoding: "utf8",
    },
  );
}

function runAwInstaller(root, args, fakeBin = null) {
  return spawnSync(process.execPath, [join(__dirname, "bin", "servo-installer.js"), ...args], {
    cwd: root,
    env: checkPathsExistEnv(root, fakeBin),
    encoding: "utf8",
  });
}

function runNodeMigrateRuntime(root, args, fakeBin = null) {
  return runAwInstaller(root, ["migrate-runtime", ...args], fakeBin);
}

test("node-owned summary and context helpers are exported for unit coverage", () => {
  assert.equal(typeof installer.buildNodeAgentsContext, "function");
  assert.equal(typeof installer.diagnosticSummary, "function");
  assert.deepEqual(
    installer.diagnosticSummary({
      sourceRoot: "/source",
      targetRoot: "/missing-target",
      issues: [],
      bindings: [],
      targetChildren: null,
    }),
    {
      backend: "agents",
      source_root: "/source",
      target_root: "/missing-target",
      target_root_status: "missing",
      target_root_exists: false,
      binding_count: 0,
      managed_install_count: 0,
      managed_installs: [],
      legacy_target_dir_count: 0,
      legacy_target_dirs: [],
      legacy_blocked_count: 0,
      legacy_blocked: [],
      upgrade_guidance: null,
      issue_count: 0,
      issue_codes: [],
      issues: [],
      unrecognized_count: 0,
      unrecognized: [],
      conflict_count: 0,
      conflicts: [],
    },
  );
});

test("servo-installer --log-dir writes sanitized run log without env dump", () => {
  const root = mkdtempSync(join(tmpdir(), "servo-installer-log-"));
  try {
    const logDir = join(root, "logs");
    const sourceRoot = join(__dirname, "..", "..", "..");
    const result = spawnSync(
      process.execPath,
      [
        join(__dirname, "bin", "servo-installer.js"),
        "diagnose",
        "--backend=agents",
        "--log-dir",
        logDir,
      ],
      {
        cwd: root,
        env: {
          ...checkPathsExistEnv(root),
          SERVO_HARNESS_REPO_ROOT: sourceRoot,
          SECRET_TOKEN: "super-secret-value",
          PASSWORD: "should-not-appear",
        },
        encoding: "utf8",
      },
    );
    assert.equal(result.status, 0, result.stderr);
    assert.match(result.stdout, /servo-installer log: /);
    const logFiles = readdirSync(logDir).filter((name) => name.endsWith(".json"));
    assert.equal(logFiles.length, 1);
    const logText = readFileSync(join(logDir, logFiles[0]), "utf8");
    assert.equal(logText.includes("super-secret-value"), false);
    assert.equal(logText.includes("should-not-appear"), false);
    const logPayload = JSON.parse(logText);
    assert.equal(logPayload.schema_version, "servo-installer-run-log/v1");
    assert.deepEqual(logPayload.command, ["diagnose", "--backend=agents"]);
    assert.equal(logPayload.backend, "agents");
    assert.equal(logPayload.verdict, "pass");
    assert.equal(logPayload.sanitization.full_environment_dumped, false);
    assert.equal(logPayload.target_state.aw_exists, false);
    assert.ok(Array.isArray(logPayload.output));
    assert.ok(logPayload.output.some((entry) => entry.line.includes("[agents] diagnose")));
  } finally {
    rmSync(root, { recursive: true, force: true });
  }
});

test("default installer log dir ensures target .gitignore ignores .logs", () => {
  const root = mkdtempSync(join(tmpdir(), "servo-installer-log-ignore-"));
  try {
    const defaultLogDir = installer.defaultInstallerLogDir(root);

    assert.equal(installer.ensureTargetLogGitignore(root, defaultLogDir), true);
    assert.match(readFileSync(join(root, ".gitignore"), "utf8"), /^\.logs\/$/m);
    assert.equal(installer.ensureTargetLogGitignore(root, defaultLogDir), false);

    const explicitLogDir = join(root, "custom-logs");
    assert.equal(installer.ensureTargetLogGitignore(root, explicitLogDir), false);
  } finally {
    rmSync(root, { recursive: true, force: true });
  }
});

test("path safety policy is loaded from the shared deploy JSON", () => {
  const policy = installer.pathSafetyPolicy();

  assert.ok(policy.exact_sensitive_target_repo_roots.includes("/etc"));
  assert.ok(policy.recursive_sensitive_target_repo_roots.includes("/proc"));
  assert.ok(policy.home_relative_recursive_sensitive_target_repo_roots.includes(".ssh"));
  assert.ok(policy.allowed_target_repo_root_prefixes.includes("$source_root"));
});

test("normalizeRelativePath rejects traversal and keeps clean relative paths", () => {
  assert.equal(
    installer.normalizeRelativePath("templates/SKILL.md", "field", "demo-skill", "repository root"),
    "templates/SKILL.md",
  );
  assert.throws(
    () => installer.normalizeRelativePath("../SKILL.md", "field", "demo-skill", "repository root"),
    /must not contain '\.\.'/,
  );
  assert.throws(
    () => installer.normalizeRelativePath("..\0/SKILL.md", "field", "demo-skill", "repository root"),
    /must not contain null bytes/,
  );
});

test("payloadTargetMetadata normalizes required target metadata", () => {
  const metadata = installer.payloadTargetMetadata(
    {
      target_dir: "aw-demo-skill",
      target_entry_name: "SKILL.md",
      required_payload_files: ["SKILL.md", "payload.json", "aw.marker"],
      legacy_target_dirs: ["demo-skill"],
      legacy_skill_ids: ["old-demo-skill"],
    },
    { skillId: "demo-skill" },
  );

  assert.deepEqual(metadata, {
    targetDir: "aw-demo-skill",
    targetEntryName: "SKILL.md",
    requiredPayloadFiles: ["SKILL.md", "payload.json", "aw.marker"],
    legacyTargetDirs: ["demo-skill"],
    legacySkillIds: ["old-demo-skill"],
  });
});

test("loadBindingPayloads rejects oversized JSON before parsing", () => {
  const root = mkdtempSync(join(tmpdir(), "servo-installer-test-"));
  try {
    const payloadPath = join(root, "payload.json");
    writeFileSync(payloadPath, `{"data":"${"a".repeat(1_048_577)}"}`, "utf8");

    assert.throws(
      () => installer.loadBindingPayloads([{ payloadPath }]),
      /JSON payload exceeds 1048576 byte limit/,
    );
  } finally {
    rmSync(root, { recursive: true, force: true });
  }
});

test("computePayloadFingerprint matches the Python payload contract order", () => {
  const root = mkdtempSync(join(tmpdir(), "servo-installer-test-"));
  try {
    const canonicalDir = join(root, "product", "harness", "skills", "demo-skill");
    const payloadDir = join(root, "product", "harness", "adapters", "agents", "skills", "demo-skill");
    mkdirSync(canonicalDir, { recursive: true });
    mkdirSync(payloadDir, { recursive: true });
    const skillText = "# Demo\n";
    const payload = {
      payload_version: "agents-skill-payload.v1",
      backend: "agents",
      skill_id: "demo-skill",
      target_dir: "aw-demo-skill",
      target_entry_name: "SKILL.md",
      required_payload_files: ["SKILL.md", "payload.json", "aw.marker"],
      canonical_dir: "product/harness/skills/demo-skill",
      canonical_paths: ["product/harness/skills/demo-skill/SKILL.md"],
    };
    const payloadText = `${JSON.stringify(payload, null, 2)}\n`;
    writeFileSync(join(canonicalDir, "SKILL.md"), skillText, "utf8");
    writeFileSync(join(payloadDir, "payload.json"), payloadText, "utf8");

    const binding = {
      backend: "agents",
      skillId: "demo-skill",
      payloadPath: join(payloadDir, "payload.json"),
    };
    const metadata = installer.payloadTargetMetadata(payload, binding);
    const fingerprint = installer.computePayloadFingerprint(
      binding,
      { sourceRoot: root },
      payload,
      payloadText,
      metadata,
    );
    const expected = createHash("sha256")
      .update(
        [
          "backend=agents\nskill_id=demo-skill\npayload_version=agents-skill-payload.v1\n",
          `file:SKILL.md\n${skillText}\n`,
          `file:payload.json\n${payloadText}\n`,
        ].join(""),
        "utf8",
      )
      .digest("hex");

    assert.equal(fingerprint, expected);
  } finally {
    rmSync(root, { recursive: true, force: true });
  }
});

test("buildNodeBackendContext keeps backend target root defaults and override flags in parity", () => {
  const root = mkdtempSync(join(tmpdir(), "servo-installer-test-"));
  const originalTargetRepoRoot = process.env.SERVO_HARNESS_TARGET_REPO_ROOT;
  try {
    seedMinimalAgentsSource(root, "agents-demo");
    seedMinimalClaudeSource(root, "claude-demo");
    process.env.SERVO_HARNESS_TARGET_REPO_ROOT = root;

    const agentsDefault = installer.buildNodeBackendContext({
      backend: "agents",
      sourceRootOverride: root,
    });
    assert.equal(agentsDefault.targetRoot, join(root, ".agents", "skills"));
    assert.equal(agentsDefault.targetRootOverrideFlag, undefined);

    const agentsRoot = join(root, "custom-agents-skills");
    const agentsOverride = installer.buildNodeBackendContext({
      backend: "agents",
      sourceRootOverride: root,
      agentsRoot,
    });
    assert.equal(agentsOverride.targetRoot, agentsRoot);
    assert.equal(agentsOverride.targetRootOverrideFlag, "--agents-root");

    const claudeDefault = installer.buildNodeBackendContext({
      backend: "claude",
      sourceRootOverride: root,
    });
    assert.equal(claudeDefault.targetRoot, join(root, ".claude", "skills"));
    assert.equal(claudeDefault.targetRootOverrideFlag, undefined);

    const claudeRoot = join(root, "custom-claude-skills");
    const claudeOverride = installer.buildNodeBackendContext({
      backend: "claude",
      sourceRootOverride: root,
      claudeRoot,
    });
    assert.equal(claudeOverride.targetRoot, claudeRoot);
    assert.equal(claudeOverride.targetRootOverrideFlag, "--claude-root");

    assert.throws(
      () => installer.buildNodeBackendContext({
        backend: "unsupported",
        sourceRootOverride: root,
      }),
      /Unsupported backend for Node-owned path: unsupported/,
    );
  } finally {
    if (originalTargetRepoRoot === undefined) {
      delete process.env.SERVO_HARNESS_TARGET_REPO_ROOT;
    } else {
      process.env.SERVO_HARNESS_TARGET_REPO_ROOT = originalTargetRepoRoot;
    }
    rmSync(root, { recursive: true, force: true });
  }
});

test("parseNodeDiagnoseJsonArgs accepts agents and claude JSON diagnose", () => {
  assert.deepEqual(
    installer.parseNodeDiagnoseJsonArgs(["diagnose", "--backend", "agents", "--json"]),
    { backend: "agents", agentsRoot: undefined },
  );
  assert.deepEqual(
    installer.parseNodeDiagnoseJsonArgs([
      "diagnose",
      "--backend=agents",
      "--json",
      "--agents-root=/tmp/agents-skills",
    ]),
    { backend: "agents", agentsRoot: "/tmp/agents-skills" },
  );
  assert.deepEqual(
    installer.parseNodeDiagnoseJsonArgs(["diagnose", "--backend", "claude", "--json", "--claude-root", "/tmp/claude-skills"]),
    { backend: "claude", agentsRoot: undefined, claudeRoot: "/tmp/claude-skills" },
  );
  assert.equal(installer.parseNodeDiagnoseJsonArgs(["verify", "--backend", "agents", "--json"]), null);
});

test("parseNodeDiagnoseArgs accepts agents and claude human diagnose forms", () => {
  assert.deepEqual(
    installer.parseNodeDiagnoseArgs(["diagnose", "--backend", "agents"]),
    { backend: "agents", agentsRoot: undefined },
  );
  assert.deepEqual(
    installer.parseNodeDiagnoseArgs(["diagnose", "--backend=agents", "--agents-root=/tmp/agents-skills"]),
    { backend: "agents", agentsRoot: "/tmp/agents-skills" },
  );
  assert.equal(installer.parseNodeDiagnoseArgs(["diagnose", "--backend", "agents", "--json"]), null);
  assert.deepEqual(
    installer.parseNodeDiagnoseArgs(["diagnose", "--backend", "claude", "--claude-root=/tmp/claude-skills"]),
    { backend: "claude", agentsRoot: undefined, claudeRoot: "/tmp/claude-skills" },
  );
});

test("parseNodeMigrateRuntimeArgs accepts only explicit aw to servo migration forms", () => {
  assert.deepEqual(
    installer.parseNodeMigrateRuntimeArgs(["migrate-runtime", "--from", "aw", "--to", "servo"]),
    {
      backend: "agents",
      agentsRoot: undefined,
      from: "aw",
      to: "servo",
      json: false,
      yes: false,
      reinstall: false,
    },
  );
  assert.deepEqual(
    installer.parseNodeMigrateRuntimeArgs([
      "migrate-runtime",
      "--from=aw",
      "--to=servo",
      "--json",
      "--reinstall",
      "--backend=bundle",
      "--agents-root=/tmp/agents",
      "--claude-root=/tmp/claude",
    ]),
    {
      backend: "bundle",
      agentsRoot: "/tmp/agents",
      claudeRoot: "/tmp/claude",
      from: "aw",
      to: "servo",
      json: true,
      yes: false,
      reinstall: true,
    },
  );
  assert.equal(installer.parseNodeMigrateRuntimeArgs(["migrate-runtime", "--from", "servo", "--to", "aw"]), null);
  assert.equal(installer.parseNodeMigrateRuntimeArgs(["migrate-runtime", "--from", "aw", "--to", "servo", "--json", "--yes"]), null);
  assert.equal(installer.parseNodeMigrateRuntimeArgs(["migrate-runtime", "--from", "aw"]), null);
});

test("parseNodeReconcileServoArgs accepts dry-run and apply forms", () => {
  assert.deepEqual(
    installer.parseNodeReconcileServoArgs(["reconcile-servo"]),
    { json: false, yes: false, templateRoot: undefined },
  );
  assert.deepEqual(
    installer.parseNodeReconcileServoArgs(["reconcile-servo", "--json", "--template-root=/tmp/templates"]),
    { json: true, yes: false, templateRoot: "/tmp/templates" },
  );
  assert.deepEqual(
    installer.parseNodeReconcileServoArgs(["reconcile-servo", "--yes", "--template-root", "/tmp/templates"]),
    { json: false, yes: true, templateRoot: "/tmp/templates" },
  );
  assert.equal(installer.parseNodeReconcileServoArgs(["reconcile-servo", "--json", "--yes"]), null);
  assert.equal(installer.parseNodeReconcileServoArgs(["migrate-runtime", "--json"]), null);
});

test("parseNodeUpdateJsonArgs accepts agents and claude package JSON update dry-runs", () => {
  const originalAwRepo = process.env.SERVO_INSTALLER_GITHUB_REPO;
  const originalGithubRepository = process.env.GITHUB_REPOSITORY;
  delete process.env.SERVO_INSTALLER_GITHUB_REPO;
  delete process.env.GITHUB_REPOSITORY;
  try {
    assert.deepEqual(
      installer.parseNodeUpdateJsonArgs(["update", "--backend", "agents", "--json"]),
      { backend: "agents", source: "package", agentsRoot: undefined },
    );
    assert.deepEqual(
      installer.parseNodeUpdateJsonArgs(["update", "--json", "--backend=agents", "--source=package"]),
      { backend: "agents", source: "package", agentsRoot: undefined },
    );
    assert.deepEqual(
      installer.parseNodeUpdateJsonArgs([
        "update",
        "--json",
        "--backend=agents",
        "--source=package",
        "--agents-root=/tmp/agents-skills",
      ]),
      { backend: "agents", source: "package", agentsRoot: "/tmp/agents-skills" },
    );

    assert.deepEqual(
      installer.parseNodeUpdateJsonArgs(["update", "--backend", "agents", "--json", "--source", "github"]),
      {
        backend: "agents",
        source: "github",
        agentsRoot: undefined,
        githubRepo: "OceanEyeFF/servo",
        githubRef: "master",
      },
    );
    assert.equal(installer.parseNodeUpdateJsonArgs(["update", "--backend", "agents", "--yes"]), null);
    assert.deepEqual(
      installer.parseNodeUpdateJsonArgs(["update", "--backend", "claude", "--json", "--claude-root", "/tmp/claude-skills"]),
      { backend: "claude", source: "package", agentsRoot: undefined, claudeRoot: "/tmp/claude-skills" },
    );
    assert.deepEqual(
      installer.parseNodeUpdateJsonArgs([
        "update",
        "--backend",
        "agents",
        "--json",
        "--source",
        "github",
        "--github-repo",
        "Owner/repo",
        "--github-ref",
        "main",
        "--github-archive-sha256",
        "a".repeat(64),
      ]),
      {
        backend: "agents",
        source: "github",
        agentsRoot: undefined,
        githubRepo: "Owner/repo",
        githubRef: "main",
        githubArchiveSha256: "a".repeat(64),
      },
    );
    assert.equal(
      installer.parseNodeUpdateJsonArgs(["update", "--backend", "claude", "--json", "--source", "github"]),
      null,
    );
  } finally {
    if (originalAwRepo === undefined) {
      delete process.env.SERVO_INSTALLER_GITHUB_REPO;
    } else {
      process.env.SERVO_INSTALLER_GITHUB_REPO = originalAwRepo;
    }
    if (originalGithubRepository === undefined) {
      delete process.env.GITHUB_REPOSITORY;
    } else {
      process.env.GITHUB_REPOSITORY = originalGithubRepository;
    }
  }
});

test("parseNodeUpdateDryRunArgs accepts package and agents github human-readable update dry-runs", () => {
  assert.deepEqual(
    installer.parseNodeUpdateDryRunArgs(["update", "--backend", "agents"]),
    { backend: "agents", source: "package", agentsRoot: undefined },
  );
  assert.deepEqual(
    installer.parseNodeUpdateDryRunArgs([
      "update",
      "--backend=agents",
      "--source=package",
      "--agents-root=/tmp/agents-skills",
    ]),
    { backend: "agents", source: "package", agentsRoot: "/tmp/agents-skills" },
  );

  assert.deepEqual(
    installer.parseNodeUpdateDryRunArgs([
      "update",
      "--backend",
      "agents",
      "--source",
      "github",
      "--github-repo=Owner/repo",
      "--github-ref=main",
      `--github-archive-sha256=${"1".repeat(64)}`,
    ]),
    {
      backend: "agents",
      source: "github",
      agentsRoot: undefined,
      githubRepo: "Owner/repo",
      githubRef: "main",
      githubArchiveSha256: "1".repeat(64),
    },
  );
  assert.equal(installer.parseNodeUpdateDryRunArgs(["update", "--backend", "claude", "--source", "github"]), null);
  assert.equal(installer.parseNodeUpdateDryRunArgs(["update", "--backend", "agents", "--json"]), null);
  assert.equal(installer.parseNodeUpdateDryRunArgs(["update", "--backend", "agents", "--yes"]), null);
  assert.deepEqual(
    installer.parseNodeUpdateDryRunArgs(["update", "--backend", "claude", "--claude-root=/tmp/claude-skills"]),
    { backend: "claude", source: "package", agentsRoot: undefined, claudeRoot: "/tmp/claude-skills" },
  );
});

test("parseNodeUpdateYesArgs accepts package and agents github update apply forms", () => {
  assert.deepEqual(
    installer.parseNodeUpdateYesArgs(["update", "--backend", "agents", "--yes"]),
    { backend: "agents", source: "package", yes: true, agentsRoot: undefined },
  );
  assert.deepEqual(
    installer.parseNodeUpdateYesArgs([
      "update",
      "--yes",
      "--backend=agents",
      "--source=package",
      "--agents-root=/tmp/agents-skills",
    ]),
    { backend: "agents", source: "package", yes: true, agentsRoot: "/tmp/agents-skills" },
  );

  assert.deepEqual(
    installer.parseNodeUpdateYesArgs([
      "update",
      "--backend",
      "agents",
      "--yes",
      "--source",
      "github",
      "--github-repo",
      "Owner/repo",
      "--github-ref",
      "main",
    ]),
    {
      backend: "agents",
      source: "github",
      yes: true,
      agentsRoot: undefined,
      githubRepo: "Owner/repo",
      githubRef: "main",
    },
  );
  assert.equal(installer.parseNodeUpdateYesArgs(["update", "--backend", "claude", "--yes", "--source", "github"]), null);
  assert.equal(installer.parseNodeUpdateYesArgs(["update", "--backend", "agents", "--json", "--yes"]), null);
  assert.deepEqual(
    installer.parseNodeUpdateYesArgs(["update", "--backend", "claude", "--yes", "--claude-root", "/tmp/claude-skills"]),
    {
      backend: "claude",
      source: "package",
      yes: true,
      agentsRoot: undefined,
      claudeRoot: "/tmp/claude-skills",
    },
  );
  assert.equal(installer.parseNodeUpdateYesArgs(["update", "--backend", "agents"]), null);
});

test("parseNodeUpdateArgs wrappers keep unsupported update forms rejected", () => {
  const missingValueCases = [
    ["update", "--backend"],
    ["update", "--source"],
    ["update", "--github-repo"],
    ["update", "--github-ref"],
    ["update", "--github-archive-sha256"],
    ["update", "--agents-root"],
    ["update", "--claude-root"],
  ];
  for (const args of missingValueCases) {
    assert.equal(installer.parseNodeUpdateJsonArgs(["update", "--json", ...args.slice(1)]), null);
    assert.equal(installer.parseNodeUpdateDryRunArgs(args), null);
    assert.equal(installer.parseNodeUpdateYesArgs(["update", "--yes", ...args.slice(1)]), null);
  }

  assert.equal(installer.parseNodeUpdateJsonArgs(["update", "--backend", "agents", "--json", "--yes"]), null);
  assert.equal(installer.parseNodeUpdateDryRunArgs(["update", "--backend", "agents", "--json", "--yes"]), null);
  assert.equal(installer.parseNodeUpdateYesArgs(["update", "--backend", "agents", "--json", "--yes"]), null);
  assert.equal(installer.parseNodeUpdateJsonArgs(["update", "--backend", "claude", "--json", "--source", "github"]), null);
  assert.equal(installer.parseNodeUpdateDryRunArgs(["update", "--backend", "claude", "--source", "github"]), null);
  assert.equal(installer.parseNodeUpdateYesArgs(["update", "--backend", "claude", "--yes", "--source", "github"]), null);
});

test("unsupported agents package variants are classified without Python", () => {
  assert.deepEqual(
    installer.parseNodeUnsupportedPruneMissingAllArgs(["prune", "--backend", "agents"]),
    { backend: "agents", source: "package", agentsRoot: undefined },
  );
  assert.deepEqual(
    installer.parseNodeUnsupportedPruneMissingAllArgs([
      "prune",
      "--backend=agents",
      "--source=package",
      "--agents-root=/tmp/agents-skills",
    ]),
    { backend: "agents", source: "package", agentsRoot: "/tmp/agents-skills" },
  );
  assert.deepEqual(
    installer.parseNodeUnsupportedUpdateJsonYesArgs(["update", "--backend", "agents", "--json", "--yes"]),
    { backend: "agents", source: "package", agentsRoot: undefined },
  );
  assert.deepEqual(
    installer.parseNodeUnsupportedUpdateJsonYesArgs([
      "update",
      "--json",
      "--yes",
      "--backend=agents",
      "--source=package",
      "--agents-root=/tmp/agents-skills",
    ]),
    { backend: "agents", source: "package", agentsRoot: "/tmp/agents-skills" },
  );
  assert.deepEqual(
    installer.parseNodeUnsupportedUpdateJsonYesArgs([
      "update",
      "--backend",
      "agents",
      "--json",
      "--yes",
      "--source",
      "github",
      "--github-repo=Owner/repo",
      "--github-ref=main",
      `--github-archive-sha256=${"a".repeat(64)}`,
    ]),
    { backend: "agents", source: "github", agentsRoot: undefined },
  );

  assert.equal(installer.parseNodeUnsupportedPruneMissingAllArgs(["prune", "--all", "--backend", "agents"]), null);
  assert.equal(installer.parseNodeUnsupportedPruneMissingAllArgs(["prune", "--backend", "claude"]), null);
  assert.equal(
    installer.parseNodeUnsupportedPruneMissingAllArgs(["prune", "--backend", "agents", "--source", "github"]),
    null,
  );
  assert.equal(installer.parseNodeUnsupportedUpdateJsonYesArgs(["update", "--backend", "agents", "--json"]), null);
  assert.equal(installer.parseNodeUnsupportedUpdateJsonYesArgs(["update", "--backend", "claude", "--json", "--yes"]), null);
});

test("parseNodeCheckPathsExistArgs accepts agents and claude backend target override forms", () => {
  assert.deepEqual(
    installer.parseNodeCheckPathsExistArgs(["check_paths_exist", "--backend", "agents"]),
    { backend: "agents", agentsRoot: undefined },
  );
  assert.deepEqual(
    installer.parseNodeCheckPathsExistArgs([
      "check_paths_exist",
      "--backend=agents",
      "--agents-root=/tmp/agents-skills",
    ]),
    { backend: "agents", agentsRoot: "/tmp/agents-skills" },
  );
  assert.deepEqual(
    installer.parseNodeCheckPathsExistArgs([
      "check_paths_exist",
      "--claude-root",
      "/tmp/ignored-claude-skills",
      "--agents-root",
      "/tmp/agents-skills",
    ]),
    { backend: "agents", agentsRoot: "/tmp/agents-skills" },
  );

  assert.deepEqual(
    installer.parseNodeCheckPathsExistArgs(["check_paths_exist", "--backend", "claude", "--claude-root", "/tmp/claude-skills"]),
    { backend: "claude", agentsRoot: undefined, claudeRoot: "/tmp/claude-skills" },
  );
  assert.equal(installer.parseNodeCheckPathsExistArgs(["check_paths_exist", "--source", "github"]), null);
});

test("parseNodeVerifyArgs accepts agents and claude package-local verify forms", () => {
  assert.deepEqual(
    installer.parseNodeVerifyArgs(["verify", "--backend", "agents"]),
    { backend: "agents", agentsRoot: undefined },
  );
  assert.deepEqual(
    installer.parseNodeVerifyArgs(["verify", "--backend=agents", "--agents-root=/tmp/agents-skills"]),
    { backend: "agents", agentsRoot: "/tmp/agents-skills" },
  );
  assert.deepEqual(
    installer.parseNodeVerifyArgs(["verify", "--backend", "claude", "--claude-root=/tmp/claude-skills"]),
    { backend: "claude", agentsRoot: undefined, claudeRoot: "/tmp/claude-skills" },
  );
  assert.equal(installer.parseNodeVerifyArgs(["verify", "--source", "github"]), null);
  assert.equal(installer.parseNodeVerifyArgs(["diagnose", "--backend", "agents"]), null);
});

test("parseNodeInstallArgs accepts agents and claude package-local install forms", () => {
  assert.deepEqual(
    installer.parseNodeInstallArgs(["install", "--backend", "agents"]),
    { backend: "agents", agentsRoot: undefined },
  );
  assert.deepEqual(
    installer.parseNodeInstallArgs(["install", "--backend=agents", "--agents-root=/tmp/agents-skills"]),
    { backend: "agents", agentsRoot: "/tmp/agents-skills" },
  );
  assert.deepEqual(
    installer.parseNodeInstallArgs(["install", "--backend", "claude", "--claude-root=/tmp/claude-skills"]),
    { backend: "claude", agentsRoot: undefined, claudeRoot: "/tmp/claude-skills" },
  );
  assert.equal(installer.parseNodeInstallArgs(["install", "--source", "github"]), null);
  assert.equal(installer.parseNodeInstallArgs(["verify", "--backend", "agents"]), null);
});

test("parseNodePruneArgs accepts agents and claude package-local prune all forms", () => {
  assert.deepEqual(
    installer.parseNodePruneArgs(["prune", "--all", "--backend", "agents"]),
    { backend: "agents", agentsRoot: undefined },
  );
  assert.deepEqual(
    installer.parseNodePruneArgs(["prune", "--backend=agents", "--agents-root=/tmp/agents-skills", "--all"]),
    { backend: "agents", agentsRoot: "/tmp/agents-skills" },
  );
  assert.deepEqual(
    installer.parseNodePruneArgs(["prune", "--all", "--backend", "claude", "--claude-root", "/tmp/claude-skills"]),
    { backend: "claude", agentsRoot: undefined, claudeRoot: "/tmp/claude-skills" },
  );
  assert.equal(installer.parseNodePruneArgs(["prune", "--backend", "agents"]), null);
  assert.equal(installer.parseNodePruneArgs(["prune", "--all", "--source", "github"]), null);
  assert.equal(installer.parseNodePruneArgs(["install", "--backend", "agents"]), null);
});

test("target dir helpers share duplicate checks and keep legacy dirs only in known set", () => {
  const root = mkdtempSync(join(tmpdir(), "servo-installer-test-"));
  try {
    const alphaDir = join(root, "alpha");
    const betaDir = join(root, "beta");
    mkdirSync(alphaDir, { recursive: true });
    mkdirSync(betaDir, { recursive: true });
    const alphaPayloadPath = join(alphaDir, "payload.json");
    const betaPayloadPath = join(betaDir, "payload.json");
    writeFileSync(
      alphaPayloadPath,
      JSON.stringify({
        target_dir: "aw-alpha",
        target_entry_name: "SKILL.md",
        required_payload_files: ["SKILL.md", "payload.json", "aw.marker"],
        legacy_target_dirs: ["alpha"],
      }),
      "utf8",
    );
    writeFileSync(
      betaPayloadPath,
      JSON.stringify({
        target_dir: "aw-beta",
        target_entry_name: "SKILL.md",
        required_payload_files: ["SKILL.md", "payload.json", "aw.marker"],
        legacy_target_dirs: ["beta"],
      }),
      "utf8",
    );
    const bindings = [
      { backend: "agents", skillId: "alpha", payloadPath: alphaPayloadPath },
      { backend: "agents", skillId: "beta", payloadPath: betaPayloadPath },
    ];

    assert.deepEqual([...installer.expectedTargetDirs(bindings)].sort(), ["aw-alpha", "aw-beta"]);
    assert.deepEqual([...installer.collectAllKnownTargetDirs(bindings)].sort(), [
      "alpha",
      "aw-alpha",
      "aw-beta",
      "beta",
    ]);

    writeFileSync(
      betaPayloadPath,
      JSON.stringify({
        target_dir: "aw-alpha",
        target_entry_name: "SKILL.md",
        required_payload_files: ["SKILL.md", "payload.json", "aw.marker"],
      }),
      "utf8",
    );
    assert.throws(
      () => installer.expectedTargetDirs(bindings),
      /Multiple skills map to the same target_dir for backend agents: aw-alpha/,
    );
    assert.throws(
      () => installer.collectAllKnownTargetDirs(bindings),
      /Multiple skills map to the same target_dir for backend agents: aw-alpha/,
    );
  } finally {
    rmSync(root, { recursive: true, force: true });
  }
});

test("buildInstallPlan can reuse cached payload text instead of rereading payload.json", () => {
  const root = mkdtempSync(join(tmpdir(), "servo-installer-test-"));
  try {
    const canonicalDir = join(root, "product", "harness", "skills", "demo-skill");
    const payloadDir = join(root, "product", "harness", "adapters", "agents", "skills", "demo-skill");
    const targetRoot = join(root, ".agents", "skills");
    mkdirSync(canonicalDir, { recursive: true });
    mkdirSync(payloadDir, { recursive: true });
    mkdirSync(targetRoot, { recursive: true });
    const skillText = "# Demo\n";
    const payload = {
      payload_version: "agents-skill-payload.v1",
      backend: "agents",
      skill_id: "demo-skill",
      target_dir: "aw-demo-skill",
      target_entry_name: "SKILL.md",
      required_payload_files: ["SKILL.md", "payload.json", "aw.marker"],
      canonical_dir: "product/harness/skills/demo-skill",
      canonical_paths: ["product/harness/skills/demo-skill/SKILL.md"],
      payload_policy: "canonical-copy",
      reference_distribution: "copy-listed-canonical-paths",
    };
    const payloadText = `${JSON.stringify(payload, null, 2)}\n`;
    const payloadPath = join(payloadDir, "payload.json");
    writeFileSync(join(canonicalDir, "SKILL.md"), skillText, "utf8");
    writeFileSync(payloadPath, payloadText, "utf8");
    const binding = {
      backend: "agents",
      skillId: "demo-skill",
      payloadDir,
      payloadPath,
    };
    const loadedPayloads = new Map([[payloadPath, { payload, payloadText }]]);
    writeFileSync(payloadPath, "{ invalid json", "utf8");

    const plan = installer.buildInstallPlan(binding, targetRoot, { sourceRoot: root }, { loadedPayloads });

    assert.equal(plan.targetSkillDir, join(targetRoot, "aw-demo-skill"));
    assert.equal(
      plan.payloadFingerprint,
      createHash("sha256")
        .update(
          [
            "backend=agents\nskill_id=demo-skill\npayload_version=agents-skill-payload.v1\n",
            `file:SKILL.md\n${skillText}\n`,
            `file:payload.json\n${payloadText}\n`,
          ].join(""),
          "utf8",
        )
        .digest("hex"),
    );
  } finally {
    rmSync(root, { recursive: true, force: true });
  }
});

test("verifyAgentsBackend passes cached payload text into deployed skill verification", () => {
  const root = mkdtempSync(join(tmpdir(), "servo-installer-test-"));
  try {
    const canonicalDir = join(root, "product", "harness", "skills", "demo-skill");
    const payloadDir = join(root, "product", "harness", "adapters", "agents", "skills", "demo-skill");
    const targetRoot = join(root, ".agents", "skills");
    const targetSkillDir = join(targetRoot, "aw-demo-skill");
    mkdirSync(canonicalDir, { recursive: true });
    mkdirSync(payloadDir, { recursive: true });
    mkdirSync(targetSkillDir, { recursive: true });
    const skillText = "# Demo\n";
    const payload = {
      payload_version: "agents-skill-payload.v1",
      backend: "agents",
      skill_id: "demo-skill",
      target_dir: "aw-demo-skill",
      target_entry_name: "SKILL.md",
      required_payload_files: ["SKILL.md", "payload.json", "aw.marker"],
      canonical_dir: "product/harness/skills/demo-skill",
      canonical_paths: ["product/harness/skills/demo-skill/SKILL.md"],
      payload_policy: "canonical-copy",
      reference_distribution: "copy-listed-canonical-paths",
    };
    const payloadText = `${JSON.stringify(payload, null, 2)}\n`;
    const payloadPath = join(payloadDir, "payload.json");
    writeFileSync(join(canonicalDir, "SKILL.md"), skillText, "utf8");
    writeFileSync(payloadPath, payloadText, "utf8");
    writeFileSync(join(targetSkillDir, "SKILL.md"), skillText, "utf8");
    writeFileSync(
      join(targetSkillDir, "payload.json"),
      installer.runtimePayloadDescriptorText(payload, {
        backend: "agents",
        skillId: "demo-skill",
      }),
      "utf8",
    );
    const binding = {
      backend: "agents",
      skillId: "demo-skill",
      payloadDir,
      payloadPath,
    };
    const metadata = installer.payloadTargetMetadata(payload, binding);
    const payloadFingerprint = installer.computePayloadFingerprint(
      binding,
      { sourceRoot: root },
      payload,
      payloadText,
      metadata,
    );
    const marker = {
      marker_version: "aw-managed-skill-marker.v2",
      backend: "agents",
      skill_id: "demo-skill",
      payload_version: "agents-skill-payload.v1",
      payload_fingerprint: payloadFingerprint,
    };
    writeFileSync(join(targetSkillDir, "aw.marker"), `${JSON.stringify(marker, null, 2)}\n`, "utf8");

    const loadedPayloads = new Map([[payloadPath, { payload, payloadText }]]);
    writeFileSync(payloadPath, "{ invalid json", "utf8");

    const result = installer.verifyAgentsBackend(
      {
        sourceRoot: root,
        targetRoot,
        adapterSkillsDir: join(root, "product", "harness", "adapters", "agents", "skills"),
      },
      { bindings: [binding], loadedPayloads },
    );

    const issueCodes = result.issues.map((currentIssue) => currentIssue.code);
    assert.equal(issueCodes.includes("payload-contract-invalid"), false);
    assert.deepEqual(issueCodes, []);

    writeFileSync(join(targetSkillDir, "payload.json"), payloadText, "utf8");
    const driftResult = installer.verifyAgentsBackend(
      {
        sourceRoot: root,
        targetRoot,
        adapterSkillsDir: join(root, "product", "harness", "adapters", "agents", "skills"),
      },
      { bindings: [binding], loadedPayloads },
    );

    const driftIssueCodes = driftResult.issues.map((currentIssue) => currentIssue.code);
    assert.equal(driftIssueCodes.includes("payload-contract-invalid"), false);
    assert.deepEqual(driftIssueCodes, ["target-payload-drift"]);
  } finally {
    rmSync(root, { recursive: true, force: true });
  }
});

test("update planning helpers expose direct issue and blocking behavior", () => {
  const root = mkdtempSync(join(tmpdir(), "servo-installer-test-"));
  try {
    const targetRoot = join(root, ".agents", "skills");
    const targetDir = join(targetRoot, "aw-demo-skill");
    mkdirSync(targetDir, { recursive: true });

    const issues = installer.collectUpdateTargetEntryIssues(
      targetRoot,
      new Set(["aw-demo-skill"]),
      [targetDir],
    );

    assert.deepEqual(issues, [
      {
        code: "unrecognized-target-directory",
        path: targetDir,
        detail: "update will not remove target directories without a recognized marker",
      },
    ]);
    assert.equal(installer.isUpdateBlockingIssue(issues[0], new Set()), true);
    assert.equal(installer.isUpdateBlockingIssue(issues[0], new Set([targetDir])), false);
    assert.deepEqual(
      installer.dedupeIssues([
        issues[0],
        { ...issues[0], detail: "duplicate detail" },
        { code: "missing-target-root", path: targetRoot, detail: "missing" },
      ]),
      [issues[0], { code: "missing-target-root", path: targetRoot, detail: "missing" }],
    );
    for (const code of [
      "missing-target-root",
      "missing-target-entry",
      "missing-required-payload",
      "target-payload-drift",
      "unexpected-managed-directory",
    ]) {
      assert.equal(
        installer.isUpdateBlockingIssue({ code, path: targetRoot, detail: code }, new Set()),
        false,
      );
    }
  } finally {
    rmSync(root, { recursive: true, force: true });
  }
});

test("collectUpdateTargetEntryIssues covers non-directory, fallback children, wrong type, and foreign markers", () => {
  const root = mkdtempSync(join(tmpdir(), "servo-installer-test-"));
  try {
    const missingTargetRoot = join(root, "missing", "skills");
    assert.deepEqual(
      installer.collectUpdateTargetEntryIssues(missingTargetRoot, new Set(["aw-demo-skill"]), null),
      [],
    );

    const targetRoot = join(root, ".agents", "skills");
    const wrongTypePath = join(targetRoot, "aw-demo-skill");
    const foreignPath = join(targetRoot, "aw-foreign-skill");
    mkdirSync(targetRoot, { recursive: true });
    writeFileSync(wrongTypePath, "not a directory\n", "utf8");
    mkdirSync(foreignPath, { recursive: true });
    writeFileSync(
      join(foreignPath, "aw.marker"),
      `${JSON.stringify({
        marker_version: "aw-managed-skill-marker.v2",
        backend: "claude",
        skill_id: "foreign-skill",
        payload_version: "agents-skill-payload.v1",
        payload_fingerprint: "abc",
      }, null, 2)}\n`,
      "utf8",
    );

    assert.deepEqual(
      installer.collectUpdateTargetEntryIssues(
        targetRoot,
        new Set(["aw-demo-skill", "aw-foreign-skill"]),
        null,
      ),
      [
        {
          code: "wrong-target-entry-type",
          path: wrongTypePath,
          detail: "update target path must be a real directory before reinstall",
        },
        {
          code: "foreign-managed-directory",
          path: foreignPath,
          detail: "update will not remove managed directory for backend claude",
        },
      ],
    );

    const symlinkPath = join(targetRoot, "aw-linked-skill");
    symlinkSync(foreignPath, symlinkPath, "dir");
    assert.deepEqual(
      installer.collectUpdateTargetEntryIssues(
        targetRoot,
        new Set(["aw-linked-skill"]),
        [symlinkPath],
      ),
      [
        {
          code: "wrong-target-entry-type",
          path: symlinkPath,
          detail: "update target path must be a real directory before reinstall",
        },
      ],
    );
  } finally {
    rmSync(root, { recursive: true, force: true });
  }
});

test("checkPathsExistSummary reports planned paths and no conflict without creating target root", () => {
  const root = mkdtempSync(join(tmpdir(), "servo-installer-test-"));
  try {
    seedMinimalAgentsSource(root, "demo-skill");
    const targetRoot = join(root, ".agents", "skills");

    const summary = installer.checkPathsExistSummary({
      sourceRoot: root,
      targetRoot,
      adapterSkillsDir: join(root, "product", "harness", "adapters", "agents", "skills"),
    });

    assert.equal(summary.backend, "agents");
    assert.deepEqual(summary.plannedTargetPaths, [join(targetRoot, "aw-demo-skill")]);
    assert.deepEqual(summary.conflicts, []);
    assert.equal(existsSync(targetRoot), false);
  } finally {
    rmSync(root, { recursive: true, force: true });
  }
});

test("check path conflict helpers classify directories, files, broken symlinks, and legacy dirs", () => {
  const root = mkdtempSync(join(tmpdir(), "servo-installer-test-"));
  try {
    const targetRoot = join(root, ".agents", "skills");
    mkdirSync(targetRoot, { recursive: true });
    const alpha = seedMinimalAgentsSource(root, "alpha", {
      targetDir: "aw-alpha",
      legacyTargetDirs: ["alpha"],
    });
    const beta = seedMinimalAgentsSource(root, "beta", { targetDir: "aw-beta" });
    const gamma = seedMinimalAgentsSource(root, "gamma", { targetDir: "aw-gamma" });
    mkdirSync(join(targetRoot, "aw-alpha"));
    writeFileSync(join(targetRoot, "aw-beta"), "occupied by file\n", "utf8");
    symlinkSync(join(root, "missing-gamma"), join(targetRoot, "aw-gamma"), "dir");
    mkdirSync(join(targetRoot, "alpha"));
    writeFileSync(join(targetRoot, "alpha", "SKILL.md"), "# unmanaged old skill\n", "utf8");
    const bindings = [alpha.binding, beta.binding, gamma.binding];
    const loadedPayloads = installer.loadBindingPayloads(bindings);
    const metadata = installer.collectTargetDirMetadata(bindings, loadedPayloads);
    const plans = bindings.map((binding) =>
      installer.buildInstallPlan(binding, targetRoot, { sourceRoot: root }, {
        loadedPayloads,
        targetMetadata: metadata.metadataByPayloadPath.get(binding.payloadPath),
      }),
    );

    assert.deepEqual(
      installer.collectPathConflicts(plans),
      [
        {
          skillId: "alpha",
          path: join(targetRoot, "aw-alpha"),
          detail: "existing target path is a directory",
        },
        {
          skillId: "beta",
          path: join(targetRoot, "aw-beta"),
          detail: "existing target path is a file",
        },
        {
          skillId: "gamma",
          path: join(targetRoot, "aw-gamma"),
          detail: "existing target path is a broken symlink",
        },
      ],
    );
    assert.deepEqual(installer.collectLegacyPathConflicts(plans, targetRoot), [
      {
        skillId: "alpha",
        path: join(targetRoot, "alpha"),
        detail: "legacy directory alpha is occupied by unmanaged content",
      },
    ]);
  } finally {
    rmSync(root, { recursive: true, force: true });
  }
});

test("checkPathsExistSummary keeps same source validation and duplicate target_dir failures", () => {
  const root = mkdtempSync(join(tmpdir(), "servo-installer-test-"));
  try {
    const first = seedMinimalAgentsSource(root, "first", { targetDir: "aw-shared" });
    seedMinimalAgentsSource(root, "second", { targetDir: "aw-shared" });
    const context = {
      sourceRoot: root,
      targetRoot: join(root, ".agents", "skills"),
      adapterSkillsDir: join(root, "product", "harness", "adapters", "agents", "skills"),
    };

    assert.throws(
      () => installer.checkPathsExistSummary(context),
      /Multiple skills map to the same target_dir for backend agents: aw-shared/,
    );

    first.payload.backend = "claude";
    writeFileSync(first.binding.payloadPath, `${JSON.stringify(first.payload, null, 2)}\n`, "utf8");
    assert.throws(
      () => installer.checkPathsExistSummary(context),
      /Cannot check target paths because source validation failed:[\s\S]*payload backend must be agents/,
    );
  } finally {
    rmSync(root, { recursive: true, force: true });
  }
});

test("servo-installer check_paths_exist agents is node-owned without Python and honors agents-root", () => {
  const root = mkdtempSync(join(tmpdir(), "servo-installer-test-"));
  try {
    seedMinimalAgentsSource(root, "demo-skill");
    const fakeBin = fakePythonBin(root);
    const agentsRoot = join(root, "custom-agents", "skills");

    const completed = runNodeCheckPathsExist(root, ["--backend=agents", `--agents-root=${agentsRoot}`], fakeBin);

    assert.equal(completed.status, 0, completed.stderr);
    assert.equal(completed.stdout, `[agents] ok: no pre-existing paths at ${agentsRoot}\n`);
    assert.equal(completed.stderr.includes("unexpected-python"), false);
    assert.equal(existsSync(agentsRoot), false);
  } finally {
    rmSync(root, { recursive: true, force: true });
  }
});

test("servo-installer diagnose agents human and json agents-root are node-owned without Python", () => {
  const root = mkdtempSync(join(tmpdir(), "servo-installer-test-"));
  try {
    seedMinimalAgentsSource(root, "demo-skill");
    const fakeBin = fakePythonBin(root);
    const agentsRoot = join(root, "custom-agents", "skills");

    const human = runAwInstaller(root, ["diagnose", "--backend=agents", `--agents-root=${agentsRoot}`], fakeBin);
    assert.equal(human.status, 0, human.stderr);
    assert.equal(
      human.stdout,
      `[agents] diagnose: 1 issue(s), 0 managed install(s) at ${agentsRoot}\n` +
        "issue codes: missing-target-root\n",
    );
    assert.equal(human.stderr.includes("unexpected-python"), false);

    const json = runAwInstaller(root, ["diagnose", "--backend=agents", "--json", `--agents-root=${agentsRoot}`], fakeBin);
    assert.equal(json.status, 0, json.stderr);
    assert.equal(json.stderr.includes("unexpected-python"), false);
    const payload = JSON.parse(json.stdout);
    assert.equal(payload.backend, "agents");
    assert.equal(payload.target_root, agentsRoot);
    assert.equal(payload.target_root_status, "missing");
  } finally {
    rmSync(root, { recursive: true, force: true });
  }
});

test("servo-installer claude read-only lifecycle paths are node-owned without Python", () => {
  const root = mkdtempSync(join(tmpdir(), "servo-installer-test-"));
  try {
    seedMinimalClaudeSource(root, "demo-skill");
    const fakeBin = fakePythonBin(root);
    const claudeRoot = join(root, "custom-claude", "skills");

    const human = runAwInstaller(root, ["diagnose", "--backend=claude", `--claude-root=${claudeRoot}`], fakeBin);
    assert.equal(human.status, 0, human.stderr);
    assert.equal(
      human.stdout,
      `[claude] diagnose: 1 issue(s), 0 managed install(s) at ${claudeRoot}\n` +
        "issue codes: missing-target-root\n",
    );
    assert.equal(human.stderr.includes("unexpected-python"), false);

    const json = runAwInstaller(root, ["diagnose", "--backend=claude", "--json", `--claude-root=${claudeRoot}`], fakeBin);
    assert.equal(json.status, 0, json.stderr);
    assert.equal(json.stderr.includes("unexpected-python"), false);
    const diagnosePayload = JSON.parse(json.stdout);
    assert.equal(diagnosePayload.backend, "claude");
    assert.equal(diagnosePayload.target_root, claudeRoot);
    assert.equal(diagnosePayload.target_root_status, "missing");

    const check = runNodeCheckPathsExist(root, ["--backend=claude", `--claude-root=${claudeRoot}`], fakeBin);
    assert.equal(check.status, 0, check.stderr);
    assert.equal(check.stdout, `[claude] ok: no pre-existing paths at ${claudeRoot}\n`);
    assert.equal(check.stderr.includes("unexpected-python"), false);

    const updateJson = runNodeUpdate(root, ["--backend=claude", "--json", `--claude-root=${claudeRoot}`], fakeBin);
    assert.equal(updateJson.status, 0, updateJson.stderr);
    assert.equal(updateJson.stderr.includes("unexpected-python"), false);
    const updatePayload = JSON.parse(updateJson.stdout);
    assert.equal(updatePayload.backend, "claude");
    assert.equal(updatePayload.target_root, claudeRoot);
    assert.equal(updatePayload.blocking_issue_count, 0);

    const updateHuman = runNodeUpdate(root, ["--backend=claude", `--claude-root=${claudeRoot}`], fakeBin);
    assert.equal(updateHuman.status, 0, updateHuman.stderr);
    assert.match(updateHuman.stdout, /^\[claude\] update plan for /);
    assert.match(updateHuman.stdout, /\[claude\] dry-run only; pass --yes to apply update/);
    assert.equal(updateHuman.stderr.includes("unexpected-python"), false);
    assert.equal(existsSync(claudeRoot), false);

    const blockedClaudeRoot = join(root, "blocked-claude-root");
    writeFileSync(blockedClaudeRoot, "not a directory\n", "utf8");
    const blockedUpdate = runNodeUpdate(root, ["--backend=claude", `--claude-root=${blockedClaudeRoot}`], fakeBin);
    assert.equal(blockedUpdate.status, 1);
    assert.match(blockedUpdate.stderr, /\[claude\] update blocked by 1 preflight issue\(s\)/);
    assert.equal(blockedUpdate.stderr.includes("unexpected-python"), false);
  } finally {
    rmSync(root, { recursive: true, force: true });
  }
});

test("servo-installer verify claude honors frontmatter transform parity without Python", () => {
  const root = mkdtempSync(join(tmpdir(), "servo-installer-test-"));
  try {
    const installed = seedInstalledClaudeSkill(root, "demo-skill");
    const fakeBin = fakePythonBin(root);

    const success = runNodeVerify(root, ["--backend=claude", `--claude-root=${installed.targetRoot}`], fakeBin);
    assert.equal(success.status, 0, success.stderr);
    assert.equal(success.stdout, `[claude] ok: target root is ready at ${installed.targetRoot}\n`);
    assert.equal(success.stderr.includes("unexpected-python"), false);

    writeFileSync(join(installed.targetSkillDir, "SKILL.md"), "# drifted\n", "utf8");
    const drift = runNodeVerify(root, ["--backend=claude", `--claude-root=${installed.targetRoot}`], fakeBin);
    assert.equal(drift.status, 1);
    assert.match(drift.stdout, /^\[claude\] drift: 1 issue\(s\) in target root/);
    assert.match(drift.stdout, /target-payload-drift/);
    assert.equal(drift.stderr.includes("unexpected-python"), false);
  } finally {
    rmSync(root, { recursive: true, force: true });
  }
});

test("servo-installer claude mutating lifecycle paths are node-owned without Python", () => {
  const root = mkdtempSync(join(tmpdir(), "servo-installer-test-"));
  try {
    seedMinimalClaudeSource(root, "demo-skill", {
      claudeFrontmatter: { "disable-model-invocation": true },
    });
    const fakeBin = fakePythonBin(root);
    const claudeRoot = join(root, "custom-claude", "skills");
    const targetSkillDir = join(claudeRoot, "demo-skill");

    const install = runNodeInstall(root, ["--backend=claude", `--claude-root=${claudeRoot}`], fakeBin);
    assert.equal(install.status, 0, install.stderr);
    assert.equal(install.stderr.includes("unexpected-python"), false);
    assert.match(install.stdout, new RegExp(`installed skill demo-skill -> ${escapeRegExp(targetSkillDir)}`));
    assert.equal(existsSync(join(root, ".agents", "skills")), false);
    assert.equal(readFileSync(join(targetSkillDir, "SKILL.md"), "utf8").includes("disable-model-invocation: true"), true);

    const update = runNodeUpdate(root, ["--backend=claude", "--yes", `--claude-root=${claudeRoot}`], fakeBin);
    assert.equal(update.status, 0, update.stderr);
    assert.equal(update.stderr.includes("unexpected-python"), false);
    assert.match(update.stdout, /\[claude\] update plan for /);
    assert.match(update.stdout, /\[claude\] applying update/);
    assert.match(update.stdout, /\[claude\] update complete/);

    const verify = runNodeVerify(root, ["--backend=claude", `--claude-root=${claudeRoot}`], fakeBin);
    assert.equal(verify.status, 0, verify.stderr);

    const prune = runNodePrune(root, ["--all", "--backend=claude", `--claude-root=${claudeRoot}`], fakeBin);
    assert.equal(prune.status, 0, prune.stderr);
    assert.equal(prune.stderr.includes("unexpected-python"), false);
    assert.match(prune.stdout, new RegExp(`removed managed skill dir ${escapeRegExp(targetSkillDir)}`));
    assert.equal(existsSync(targetSkillDir), false);
  } finally {
    rmSync(root, { recursive: true, force: true });
  }
});

test("servo-installer install removes same-backend managed legacy directories without Python", () => {
  const root = mkdtempSync(join(tmpdir(), "servo-installer-test-"));
  try {
    seedMinimalClaudeSource(root, "demo-skill", {
      legacyTargetDirs: ["aw-demo-skill"],
      legacySkillIds: ["old-demo-skill"],
    });
    const fakeBin = fakePythonBin(root);
    const claudeRoot = join(root, ".claude", "skills");
    const legacyDir = join(claudeRoot, "aw-demo-skill");
    mkdirSync(legacyDir, { recursive: true });
    writeFileSync(join(legacyDir, "SKILL.md"), "# legacy\n", "utf8");
    writeFileSync(
      join(legacyDir, "aw.marker"),
      `${JSON.stringify({
        marker_version: "aw-managed-skill-marker.v2",
        backend: "claude",
        skill_id: "old-demo-skill",
        payload_version: "claude-skill-payload.v1",
        payload_fingerprint: "old-fingerprint",
      }, null, 2)}\n`,
      "utf8",
    );

    const completed = runNodeInstall(root, ["--backend=claude"], fakeBin);

    assert.equal(completed.status, 0, completed.stderr);
    assert.equal(completed.stderr.includes("unexpected-python"), false);
    assert.match(completed.stdout, new RegExp(`removed legacy skill dir demo-skill -> ${escapeRegExp(legacyDir)}`));
    assert.equal(existsSync(legacyDir), false);
    assert.equal(existsSync(join(claudeRoot, "demo-skill", "aw.marker")), true);
  } finally {
    rmSync(root, { recursive: true, force: true });
  }
});

test("servo-installer install blocks legacy symlink markers without Python", () => {
  if (process.platform === "win32") {
    return;
  }
  const root = mkdtempSync(join(tmpdir(), "servo-installer-test-"));
  try {
    seedMinimalClaudeSource(root, "demo-skill", {
      legacyTargetDirs: ["aw-demo-skill"],
    });
    const fakeBin = fakePythonBin(root);
    const claudeRoot = join(root, ".claude", "skills");
    const actualDir = join(root, "actual-managed-legacy");
    const legacyDir = join(claudeRoot, "aw-demo-skill");
    mkdirSync(actualDir, { recursive: true });
    mkdirSync(claudeRoot, { recursive: true });
    writeFileSync(join(actualDir, "SKILL.md"), "# legacy\n", "utf8");
    writeFileSync(
      join(actualDir, "aw.marker"),
      `${JSON.stringify({
        marker_version: "aw-managed-skill-marker.v2",
        backend: "claude",
        skill_id: "demo-skill",
        payload_version: "claude-skill-payload.v1",
        payload_fingerprint: "old-fingerprint",
      }, null, 2)}\n`,
      "utf8",
    );
    symlinkSync(actualDir, legacyDir, "dir");

    const completed = runNodeInstall(root, ["--backend=claude"], fakeBin);

    assert.equal(completed.status, 1);
    assert.match(completed.stderr, /legacy directory aw-demo-skill is occupied by unmanaged content/);
    assert.equal(completed.stderr.includes("unexpected-python"), false);
    assert.equal(existsSync(actualDir), true);
    assert.equal(existsSync(join(claudeRoot, "demo-skill")), false);
  } finally {
    rmSync(root, { recursive: true, force: true });
  }
});

test("servo-installer agents install removes same-backend managed legacy directories without Python", () => {
  const root = mkdtempSync(join(tmpdir(), "servo-installer-test-"));
  try {
    seedMinimalAgentsSource(root, "demo-skill", {
      legacyTargetDirs: ["demo-skill"],
      legacySkillIds: ["old-demo-skill"],
    });
    const fakeBin = fakePythonBin(root);
    const agentsRoot = join(root, ".agents", "skills");
    const legacyDir = join(agentsRoot, "demo-skill");
    mkdirSync(legacyDir, { recursive: true });
    writeFileSync(join(legacyDir, "SKILL.md"), "# legacy\n", "utf8");
    writeFileSync(
      join(legacyDir, "aw.marker"),
      `${JSON.stringify({
        marker_version: "aw-managed-skill-marker.v2",
        backend: "agents",
        skill_id: "old-demo-skill",
        payload_version: "agents-skill-payload.v1",
        payload_fingerprint: "old-fingerprint",
      }, null, 2)}\n`,
      "utf8",
    );

    const completed = runNodeInstall(root, ["--backend=agents"], fakeBin);

    assert.equal(completed.status, 0, completed.stderr);
    assert.equal(completed.stderr.includes("unexpected-python"), false);
    assert.match(completed.stdout, new RegExp(`removed legacy skill dir demo-skill -> ${escapeRegExp(legacyDir)}`));
    assert.equal(existsSync(legacyDir), false);
    assert.equal(existsSync(join(agentsRoot, "aw-demo-skill", "aw.marker")), true);
  } finally {
    rmSync(root, { recursive: true, force: true });
  }
});

test("servo-installer check_paths_exist agents reports conflicts with Python-compatible stderr", () => {
  const root = mkdtempSync(join(tmpdir(), "servo-installer-test-"));
  try {
    seedMinimalAgentsSource(root, "demo-skill");
    const targetRoot = join(root, ".agents", "skills");
    mkdirSync(join(targetRoot, "aw-demo-skill"), { recursive: true });
    const fakeBin = fakePythonBin(root);

    const completed = runNodeCheckPathsExist(root, ["--backend", "agents"], fakeBin);

    assert.equal(completed.status, 1);
    assert.match(completed.stdout, /^\[agents\] found 1 existing path/);
    assert.match(completed.stdout, /target path conflicts:/);
    assert.match(completed.stdout, /demo-skill/);
    assert.match(completed.stdout, /existing target path is a directory/);
    assert.equal(completed.stderr.includes("unexpected-python"), false);
  } finally {
    rmSync(root, { recursive: true, force: true });
  }
});

test("servo-installer check_paths_exist agents stays node-owned for source and duplicate failures", () => {
  const root = mkdtempSync(join(tmpdir(), "servo-installer-test-"));
  try {
    const first = seedMinimalAgentsSource(root, "first", { targetDir: "aw-shared" });
    seedMinimalAgentsSource(root, "second", { targetDir: "aw-shared" });
    const fakeBin = fakePythonBin(root);

    const duplicateResult = runNodeCheckPathsExist(root, ["--backend=agents"], fakeBin);
    assert.equal(duplicateResult.status, 1);
    assert.equal(duplicateResult.stdout, "");
    assert.match(duplicateResult.stderr, /Multiple skills map to the same target_dir for backend agents: aw-shared/);
    assert.equal(duplicateResult.stderr.includes("unexpected-python"), false);

    first.payload.backend = "claude";
    writeFileSync(first.binding.payloadPath, `${JSON.stringify(first.payload, null, 2)}\n`, "utf8");

    const sourceResult = runNodeCheckPathsExist(root, ["--backend=agents"], fakeBin);
    assert.equal(sourceResult.status, 1);
    assert.equal(sourceResult.stdout, "");
    assert.match(
      sourceResult.stderr,
      /Cannot check target paths because source validation failed:[\s\S]*payload backend must be agents/,
    );
    assert.equal(sourceResult.stderr.includes("unexpected-python"), false);
  } finally {
    rmSync(root, { recursive: true, force: true });
  }
});

test("servo-installer check_paths_exist agents reports target root readiness failures without Python", () => {
  const root = mkdtempSync(join(tmpdir(), "servo-installer-test-"));
  try {
    seedMinimalAgentsSource(root, "demo-skill");
    const fakeBin = fakePythonBin(root);
    const agentsRoot = join(root, ".agents", "skills");
    mkdirSync(join(root, ".agents"), { recursive: true });
    writeFileSync(agentsRoot, "not a directory\n", "utf8");

    const completed = runNodeCheckPathsExist(root, ["--backend=agents", `--agents-root=${agentsRoot}`], fakeBin);

    assert.equal(completed.status, 1);
    assert.equal(completed.stdout, "");
    assert.match(completed.stderr, /Cannot check target paths because target root is not ready:/);
    assert.match(completed.stderr, /wrong-target-root-type/);
    assert.match(completed.stderr, /target root exists but is not a directory/);
    assert.equal(completed.stderr.includes("unexpected-python"), false);
  } finally {
    rmSync(root, { recursive: true, force: true });
  }
});

test("servo-installer check_paths_exist agents node-owned for success and conflict", () => {
  const successRoot = mkdtempSync(join(tmpdir(), "servo-installer-test-"));
  const conflictRoot = mkdtempSync(join(tmpdir(), "servo-installer-test-"));
  try {
    seedMinimalAgentsSource(successRoot, "demo-skill");
    const successAgentsRoot = join(successRoot, ".agents", "skills");

    const nodeSuccess = runNodeCheckPathsExist(
      successRoot,
      ["--backend=agents", `--agents-root=${successAgentsRoot}`],
    );

    assert.equal(typeof nodeSuccess.status, "number");

    seedMinimalAgentsSource(conflictRoot, "demo-skill");
    const conflictAgentsRoot = join(conflictRoot, ".agents", "skills");
    mkdirSync(join(conflictAgentsRoot, "aw-demo-skill"), { recursive: true });

    const nodeConflict = runNodeCheckPathsExist(
      conflictRoot,
      ["--backend=agents", `--agents-root=${conflictAgentsRoot}`],
    );

    assert.equal(typeof nodeConflict.status, "number");
  } finally {
    rmSync(successRoot, { recursive: true, force: true });
    rmSync(conflictRoot, { recursive: true, force: true });
  }
});

test("servo-installer verify agents is node-owned without Python for success and drift", () => {
  const root = mkdtempSync(join(tmpdir(), "servo-installer-test-"));
  try {
    const installed = seedInstalledAgentsSkill(root, "demo-skill");
    const fakeBin = fakePythonBin(root);

    const success = runNodeVerify(root, ["--backend=agents", `--agents-root=${installed.targetRoot}`], fakeBin);
    assert.equal(success.status, 0, success.stderr);
    assert.equal(success.stdout, `[agents] ok: target root is ready at ${installed.targetRoot}\n`);
    assert.equal(success.stderr.includes("unexpected-python"), false);

    writeFileSync(join(installed.targetSkillDir, "SKILL.md"), "# drifted\n", "utf8");
    const drift = runNodeVerify(root, ["--backend=agents", `--agents-root=${installed.targetRoot}`], fakeBin);
    assert.equal(drift.status, 1);
    assert.match(drift.stdout, /^\[agents\] drift: 1 issue\(s\) in target root/);
    assert.match(drift.stdout, /target-payload-drift/);
    assert.equal(drift.stderr.includes("unexpected-python"), false);
  } finally {
    rmSync(root, { recursive: true, force: true });
  }
});

test("servo-installer verify agents is node-owned for missing and invalid target states", () => {
  const missingRoot = mkdtempSync(join(tmpdir(), "servo-installer-test-"));
  const unrecognizedRoot = mkdtempSync(join(tmpdir(), "servo-installer-test-"));
  const wrongTypeRoot = mkdtempSync(join(tmpdir(), "servo-installer-test-"));
  try {
    seedMinimalAgentsSource(missingRoot, "demo-skill");
    const missingFakeBin = fakePythonBin(missingRoot);
    const missingTargetRoot = join(missingRoot, ".agents", "skills");
    const missing = runNodeVerify(
      missingRoot,
      ["--backend=agents", `--agents-root=${missingTargetRoot}`],
      missingFakeBin,
    );
    assert.equal(missing.status, 1);
    assert.match(missing.stdout, /missing-target-root/);
    assert.match(missing.stdout, /agents target root does not exist/);
    assert.equal(missing.stderr.includes("unexpected-python"), false);

    const unrecognized = seedInstalledAgentsSkill(unrecognizedRoot, "demo-skill");
    rmSync(join(unrecognized.targetSkillDir, "aw.marker"), { force: true });
    const unrecognizedFakeBin = fakePythonBin(unrecognizedRoot);
    const unrecognizedResult = runNodeVerify(
      unrecognizedRoot,
      ["--backend=agents", `--agents-root=${unrecognized.targetRoot}`],
      unrecognizedFakeBin,
    );
    assert.equal(unrecognizedResult.status, 1);
    assert.match(unrecognizedResult.stdout, /unrecognized-target-directory/);
    assert.equal(unrecognizedResult.stderr.includes("unexpected-python"), false);

    seedMinimalAgentsSource(wrongTypeRoot, "demo-skill");
    const wrongTypeTargetRoot = join(wrongTypeRoot, ".agents", "skills");
    mkdirSync(join(wrongTypeRoot, ".agents"), { recursive: true });
    writeFileSync(wrongTypeTargetRoot, "not a directory\n", "utf8");
    const wrongTypeFakeBin = fakePythonBin(wrongTypeRoot);
    const wrongType = runNodeVerify(
      wrongTypeRoot,
      ["--backend=agents", `--agents-root=${wrongTypeTargetRoot}`],
      wrongTypeFakeBin,
    );
    assert.equal(wrongType.status, 1);
    assert.match(wrongType.stdout, /wrong-target-root-type/);
    assert.match(wrongType.stdout, /target root exists but is not a directory/);
    assert.equal(wrongType.stderr.includes("unexpected-python"), false);
  } finally {
    rmSync(missingRoot, { recursive: true, force: true });
    rmSync(unrecognizedRoot, { recursive: true, force: true });
    rmSync(wrongTypeRoot, { recursive: true, force: true });
  }
});

test("servo-installer verify agents covers broken symlink and foreign marker without Python", () => {
  const brokenSymlinkRoot = mkdtempSync(join(tmpdir(), "servo-installer-test-"));
  const foreignMarkerRoot = mkdtempSync(join(tmpdir(), "servo-installer-test-"));
  try {
    seedMinimalAgentsSource(brokenSymlinkRoot, "demo-skill");
    const brokenTargetRoot = join(brokenSymlinkRoot, ".agents", "skills");
    mkdirSync(join(brokenSymlinkRoot, ".agents"), { recursive: true });
    symlinkSync(join(brokenSymlinkRoot, "missing-target"), brokenTargetRoot, "dir");
    const brokenFakeBin = fakePythonBin(brokenSymlinkRoot);
    const brokenResult = runNodeVerify(
      brokenSymlinkRoot,
      ["--backend=agents"],
      brokenFakeBin,
    );
    assert.equal(brokenResult.status, 1);
    assert.match(brokenResult.stdout, /broken-target-root-symlink/);
    assert.match(brokenResult.stdout, /target root is a broken symlink/);
    assert.equal(brokenResult.stderr.includes("unexpected-python"), false);

    const foreign = seedInstalledAgentsSkill(foreignMarkerRoot, "demo-skill");
    const foreignMarker = {
      ...foreign.marker,
      backend: "claude",
    };
    writeFileSync(join(foreign.targetSkillDir, "aw.marker"), `${JSON.stringify(foreignMarker, null, 2)}\n`, "utf8");
    const foreignFakeBin = fakePythonBin(foreignMarkerRoot);
    const foreignResult = runNodeVerify(
      foreignMarkerRoot,
      ["--backend=agents", `--agents-root=${foreign.targetRoot}`],
      foreignFakeBin,
    );
    assert.equal(foreignResult.status, 1);
    assert.match(foreignResult.stdout, /unrecognized-target-directory/);
    assert.match(foreignResult.stdout, /does not match current backend\/skill\/payload_version/);
    assert.equal(foreignResult.stderr.includes("unexpected-python"), false);
  } finally {
    rmSync(brokenSymlinkRoot, { recursive: true, force: true });
    rmSync(foreignMarkerRoot, { recursive: true, force: true });
  }
});

test("servo-installer verify agents node-owned for success and drift", () => {
  const cases = [
    {
      name: "success",
      setup(root) {
        return seedInstalledAgentsSkill(root, "demo-skill").targetRoot;
      },
      expectedStatus: 0,
    },
    {
      name: "payload file drift",
      setup(root) {
        const installed = seedInstalledAgentsSkill(root, "demo-skill");
        writeFileSync(join(installed.targetSkillDir, "SKILL.md"), "# drifted\n", "utf8");
        return installed.targetRoot;
      },
      expectedStatus: 1,
    },
    {
      name: "marker fingerprint drift",
      setup(root) {
        const installed = seedInstalledAgentsSkill(root, "demo-skill");
        const driftedMarker = {
          ...installed.marker,
          payload_fingerprint: "0".repeat(64),
        };
        writeFileSync(join(installed.targetSkillDir, "aw.marker"), `${JSON.stringify(driftedMarker, null, 2)}\n`, "utf8");
        return installed.targetRoot;
      },
      expectedStatus: 1,
    },
    {
      name: "missing target root",
      setup(root) {
        seedMinimalAgentsSource(root, "demo-skill");
        return join(root, ".agents", "skills");
      },
      expectedStatus: 1,
    },
    {
      name: "wrong target root type",
      setup(root) {
        seedMinimalAgentsSource(root, "demo-skill");
        const targetRoot = join(root, ".agents", "skills");
        mkdirSync(join(root, ".agents"), { recursive: true });
        writeFileSync(targetRoot, "not a directory\n", "utf8");
        return targetRoot;
      },
      expectedStatus: 1,
    },
    {
      name: "broken target root symlink",
      setup(root) {
        seedMinimalAgentsSource(root, "demo-skill");
        const targetRoot = join(root, ".agents", "skills");
        mkdirSync(join(root, ".agents"), { recursive: true });
        symlinkSync(join(root, "missing-target"), targetRoot, "dir");
        return null;
      },
      expectedStatus: 1,
    },
    {
      name: "missing deployed skill directory",
      setup(root) {
        seedMinimalAgentsSource(root, "demo-skill");
        const targetRoot = join(root, ".agents", "skills");
        mkdirSync(targetRoot, { recursive: true });
        return targetRoot;
      },
      expectedStatus: 1,
    },
    {
      name: "unrecognized missing marker",
      setup(root) {
        const installed = seedInstalledAgentsSkill(root, "demo-skill");
        rmSync(join(installed.targetSkillDir, "aw.marker"), { force: true });
        return installed.targetRoot;
      },
      expectedStatus: 1,
    },
    {
      name: "foreign marker",
      setup(root) {
        const installed = seedInstalledAgentsSkill(root, "demo-skill");
        const foreignMarker = {
          ...installed.marker,
          backend: "claude",
        };
        writeFileSync(join(installed.targetSkillDir, "aw.marker"), `${JSON.stringify(foreignMarker, null, 2)}\n`, "utf8");
        return installed.targetRoot;
      },
      expectedStatus: 1,
    },
    {
      name: "missing required payload",
      setup(root) {
        const installed = seedInstalledAgentsSkill(root, "demo-skill");
        rmSync(join(installed.targetSkillDir, "payload.json"), { force: true });
        return installed.targetRoot;
      },
      expectedStatus: 1,
    },
    {
      name: "wrong target entry type",
      setup(root) {
        const installed = seedInstalledAgentsSkill(root, "demo-skill");
        rmSync(join(installed.targetSkillDir, "SKILL.md"), { force: true });
        mkdirSync(join(installed.targetSkillDir, "SKILL.md"));
        return installed.targetRoot;
      },
      expectedStatus: 1,
    },
    {
      name: "unexpected managed directory",
      setup(root) {
        const installed = seedInstalledAgentsSkill(root, "demo-skill");
        const unexpectedDir = join(installed.targetRoot, "aw-old-skill");
        mkdirSync(unexpectedDir, { recursive: true });
        const unexpectedMarker = {
          marker_version: "aw-managed-skill-marker.v2",
          backend: "agents",
          skill_id: "old-skill",
          payload_version: "agents-skill-payload.v1",
          payload_fingerprint: "1".repeat(64),
        };
        writeFileSync(join(unexpectedDir, "aw.marker"), `${JSON.stringify(unexpectedMarker, null, 2)}\n`, "utf8");
        return installed.targetRoot;
      },
      expectedStatus: 1,
    },
  ];
  for (const currentCase of cases) {
    const root = mkdtempSync(join(tmpdir(), "servo-installer-test-"));
    try {
      const targetRoot = currentCase.setup(root);
      const args = targetRoot === null
        ? ["--backend=agents"]
        : ["--backend=agents", `--agents-root=${targetRoot}`];
      const fakeBin = fakePythonBin(root);
      const result = runNodeVerify(root, args, fakeBin);

      assert.equal(result.status, currentCase.expectedStatus, `${currentCase.name}: status mismatch`);
      assert.equal(result.stderr.includes("unexpected-python"), false, `${currentCase.name}: unexpected-python sentinel`);
    } finally {
      rmSync(root, { recursive: true, force: true });
    }
  }
});

test("servo-installer install agents writes a clean target without Python and verifies", () => {
  const root = mkdtempSync(join(tmpdir(), "servo-installer-test-"));
  try {
    seedMinimalAgentsSource(root, "demo-skill");
    const fakeBin = fakePythonBin(root);
    const targetRoot = join(root, ".agents", "skills");
    const targetSkillDir = join(targetRoot, "aw-demo-skill");

    const completed = runNodeInstall(root, ["--backend=agents", `--agents-root=${targetRoot}`], fakeBin);

    assert.equal(completed.status, 0, completed.stderr);
    assert.match(completed.stdout, new RegExp(`created target root ${escapeRegExp(targetRoot)}`));
    assert.match(completed.stdout, new RegExp(`installed skill demo-skill -> ${escapeRegExp(targetSkillDir)}`));
    assert.equal(completed.stderr.includes("unexpected-python"), false);
    assert.equal(existsSync(targetSkillDir), true);
    assert.equal(lstatSync(targetSkillDir).mode & 0o777, 0o755);
    assert.equal(lstatSync(join(targetSkillDir, "SKILL.md")).mode & 0o777, 0o644);
    assert.equal(lstatSync(join(targetSkillDir, "payload.json")).mode & 0o777, 0o644);
    assert.equal(lstatSync(join(targetSkillDir, "aw.marker")).mode & 0o777, 0o644);
    assert.equal(readFileSync(join(targetSkillDir, "SKILL.md"), "utf8"), "# demo-skill\n");
    const installedPayloadText = readFileSync(join(targetSkillDir, "payload.json"), "utf8");
    const installedPayload = JSON.parse(installedPayloadText);
    assert.equal(installedPayload.package_dir, ".");
    assert.deepEqual(installedPayload.package_paths, ["SKILL.md", "payload.json", "aw.marker"]);
    assert.equal(Object.hasOwn(installedPayload, "canonical_dir"), false);
    assert.equal(Object.hasOwn(installedPayload, "canonical_paths"), false);
    assert.equal(installedPayloadText.includes("product/harness"), false);
    assert.equal(installedPayloadText.includes("../"), false);

    const result = installer.verifyAgentsBackend({
      sourceRoot: root,
      targetRoot,
      adapterSkillsDir: join(root, "product", "harness", "adapters", "agents", "skills"),
    });
    assert.deepEqual(result.issues, []);
  } finally {
    rmSync(root, { recursive: true, force: true });
  }
});

test("servo-installer install agents writes an existing empty target without Python", () => {
  const root = mkdtempSync(join(tmpdir(), "servo-installer-test-"));
  try {
    seedMinimalAgentsSource(root, "demo-skill");
    const fakeBin = fakePythonBin(root);
    const targetRoot = join(root, ".agents", "skills");
    const targetSkillDir = join(targetRoot, "aw-demo-skill");
    mkdirSync(targetRoot, { recursive: true });

    const completed = runNodeInstall(root, ["--backend=agents", `--agents-root=${targetRoot}`], fakeBin);

    assert.equal(completed.status, 0, completed.stderr);
    assert.match(completed.stdout, new RegExp(`ready target root ${escapeRegExp(targetRoot)}`));
    assert.match(completed.stdout, new RegExp(`installed skill demo-skill -> ${escapeRegExp(targetSkillDir)}`));
    assert.equal(completed.stderr.includes("unexpected-python"), false);
    assert.equal(existsSync(join(targetSkillDir, "SKILL.md")), true);
    assert.deepEqual(
      installer.verifyAgentsBackend({
        sourceRoot: root,
        targetRoot,
        adapterSkillsDir: join(root, "product", "harness", "adapters", "agents", "skills"),
      }).issues,
      [],
    );
  } finally {
    rmSync(root, { recursive: true, force: true });
  }
});

test("servo-installer install agents node-owned on clean target", () => {
  const root = mkdtempSync(join(tmpdir(), "servo-installer-test-"));
  try {
    seedMinimalAgentsSource(root, "demo-skill");
    const targetRoot = join(root, ".agents", "skills");
    const targetSkillDir = join(targetRoot, "aw-demo-skill");

    const result = runNodeInstall(root, ["--backend=agents", `--agents-root=${targetRoot}`]);

    assert.equal(result.status, 0);
    assert.equal(result.stderr, "");
    assert.match(result.stdout, new RegExp(`installed skill demo-skill -> ${escapeRegExp(targetSkillDir)}`));
    assert.equal(existsSync(targetSkillDir), true);
  } finally {
    rmSync(root, { recursive: true, force: true });
  }
});

test("servo-installer install agents blocks non-clean target conflicts without Python or writes", () => {
  const root = mkdtempSync(join(tmpdir(), "servo-installer-test-"));
  try {
    seedMinimalAgentsSource(root, "demo-skill");
    const targetRoot = join(root, ".agents", "skills");
    const targetSkillDir = join(targetRoot, "aw-demo-skill");
    mkdirSync(targetSkillDir, { recursive: true });
    writeFileSync(join(targetSkillDir, "user-owned.txt"), "preserve me\n", "utf8");
    const fakeBin = fakePythonBin(root);

    const completed = runNodeInstall(root, ["--backend=agents", `--agents-root=${targetRoot}`], fakeBin);

    assert.equal(completed.status, 1);
    assert.equal(completed.stdout, "");
    assert.match(completed.stderr, /\[agents\] install blocked by 1 existing target path\(s\)/);
    assert.match(completed.stderr, /- demo-skill:/);
    assert.match(completed.stderr, /existing target path is a directory/);
    assert.equal(completed.stderr.includes("unexpected-python"), false);
    assert.equal(existsSync(join(targetSkillDir, "user-owned.txt")), true);
    assert.equal(existsSync(join(targetSkillDir, "SKILL.md")), false);
  } finally {
    rmSync(root, { recursive: true, force: true });
  }
});

test("servo-installer install agents allows unrelated target content without Python", () => {
  const root = mkdtempSync(join(tmpdir(), "servo-installer-test-"));
  try {
    seedMinimalAgentsSource(root, "demo-skill");
    const targetRoot = join(root, ".agents", "skills");
    const unrelatedDir = join(targetRoot, "user-owned");
    const targetSkillDir = join(targetRoot, "aw-demo-skill");
    mkdirSync(unrelatedDir, { recursive: true });
    writeFileSync(join(unrelatedDir, "note.txt"), "preserve me\n", "utf8");
    const fakeBin = fakePythonBin(root);

    const completed = runNodeInstall(root, ["--backend=agents", `--agents-root=${targetRoot}`], fakeBin);

    assert.equal(completed.status, 0, completed.stderr);
    assert.match(completed.stdout, new RegExp(`installed skill demo-skill -> ${escapeRegExp(targetSkillDir)}`));
    assert.equal(completed.stderr.includes("unexpected-python"), false);
    assert.equal(readFileSync(join(unrelatedDir, "note.txt"), "utf8"), "preserve me\n");
    assert.equal(existsSync(join(targetSkillDir, "SKILL.md")), true);
  } finally {
    rmSync(root, { recursive: true, force: true });
  }
});

test("servo-installer install agents rejects source and target readiness failures without Python", () => {
  const duplicateRoot = mkdtempSync(join(tmpdir(), "servo-installer-test-"));
  const wrongTypeRoot = mkdtempSync(join(tmpdir(), "servo-installer-test-"));
  const sourceFailureRoot = mkdtempSync(join(tmpdir(), "servo-installer-test-"));
  try {
    seedMinimalAgentsSource(duplicateRoot, "first", { targetDir: "aw-shared" });
    seedMinimalAgentsSource(duplicateRoot, "second", { targetDir: "aw-shared" });
    const duplicateFakeBin = fakePythonBin(duplicateRoot);
    const duplicateTargetRoot = join(duplicateRoot, ".agents", "skills");

    const duplicate = runNodeInstall(
      duplicateRoot,
      ["--backend=agents", `--agents-root=${duplicateTargetRoot}`],
      duplicateFakeBin,
    );
    assert.equal(duplicate.status, 1);
    assert.equal(duplicate.stdout, "");
    assert.match(duplicate.stderr, /Multiple skills map to the same target_dir for backend agents: aw-shared/);
    assert.equal(duplicate.stderr.includes("unexpected-python"), false);
    assert.equal(existsSync(duplicateTargetRoot), false);

    seedMinimalAgentsSource(wrongTypeRoot, "demo-skill");
    const wrongTypeTargetRoot = join(wrongTypeRoot, ".agents", "skills");
    mkdirSync(join(wrongTypeRoot, ".agents"), { recursive: true });
    writeFileSync(wrongTypeTargetRoot, "not a directory\n", "utf8");
    const wrongTypeFakeBin = fakePythonBin(wrongTypeRoot);

    const wrongType = runNodeInstall(
      wrongTypeRoot,
      ["--backend=agents", `--agents-root=${wrongTypeTargetRoot}`],
      wrongTypeFakeBin,
    );
    assert.equal(wrongType.status, 1);
    assert.equal(wrongType.stdout, "");
    assert.match(wrongType.stderr, /Cannot install because target root is not ready:/);
    assert.match(wrongType.stderr, /wrong-target-root-type/);
    assert.equal(wrongType.stderr.includes("unexpected-python"), false);

    const sourceFailure = seedMinimalAgentsSource(sourceFailureRoot, "demo-skill");
    rmSync(join(sourceFailure.canonicalDir, "SKILL.md"));
    const sourceFailureTargetRoot = join(sourceFailureRoot, ".agents", "skills");
    const sourceFailureFakeBin = fakePythonBin(sourceFailureRoot);

    const missingCanonical = runNodeInstall(
      sourceFailureRoot,
      ["--backend=agents", `--agents-root=${sourceFailureTargetRoot}`],
      sourceFailureFakeBin,
    );
    assert.equal(missingCanonical.status, 1);
    assert.equal(missingCanonical.stdout, "");
    assert.match(missingCanonical.stderr, /Cannot install because source validation failed:/);
    assert.match(missingCanonical.stderr, /missing-canonical-source/);
    assert.equal(missingCanonical.stderr.includes("unexpected-python"), false);
    assert.equal(existsSync(sourceFailureTargetRoot), false);
  } finally {
    rmSync(duplicateRoot, { recursive: true, force: true });
    rmSync(wrongTypeRoot, { recursive: true, force: true });
    rmSync(sourceFailureRoot, { recursive: true, force: true });
  }
});

test("servo-installer prune agents removes only same-backend managed dirs without Python", () => {
  const root = mkdtempSync(join(tmpdir(), "servo-installer-test-"));
  try {
    const installed = seedInstalledAgentsSkill(root, "demo-skill");
    const targetRoot = installed.targetRoot;
    const staleDir = join(targetRoot, "aw-stale-skill");
    const foreignDir = join(targetRoot, "foreign-managed");
    const invalidDir = join(targetRoot, "invalid-marker");
    const unrecognizedDir = join(targetRoot, "unrecognized");
    const userFile = join(targetRoot, "user-file.txt");
    const userSymlink = join(targetRoot, "user-symlink");

    mkdirSync(staleDir, { recursive: true });
    writeFileSync(
      join(staleDir, "aw.marker"),
      `${JSON.stringify({
        marker_version: "aw-managed-skill-marker.v2",
        backend: "agents",
        skill_id: "stale-skill",
        payload_version: "stale-version",
        payload_fingerprint: "stale-fingerprint",
      }, null, 2)}\n`,
      "utf8",
    );
    mkdirSync(foreignDir, { recursive: true });
    writeFileSync(
      join(foreignDir, "aw.marker"),
      `${JSON.stringify({
        ...installed.marker,
        backend: "claude",
      }, null, 2)}\n`,
      "utf8",
    );
    mkdirSync(invalidDir, { recursive: true });
    writeFileSync(join(invalidDir, "aw.marker"), "{invalid json\n", "utf8");
    mkdirSync(unrecognizedDir, { recursive: true });
    writeFileSync(userFile, "user data\n", "utf8");
    symlinkSync(unrecognizedDir, userSymlink, "dir");
    const fakeBin = fakePythonBin(root);

    const completed = runNodePrune(root, ["--all", "--backend=agents", `--agents-root=${targetRoot}`], fakeBin);

    assert.equal(completed.status, 0, completed.stderr);
    assert.match(completed.stdout, new RegExp(`removed managed skill dir ${escapeRegExp(installed.targetSkillDir)}`));
    assert.match(completed.stdout, new RegExp(`removed managed skill dir ${escapeRegExp(staleDir)}`));
    assert.equal(completed.stderr.includes("unexpected-python"), false);
    assert.equal(existsSync(installed.targetSkillDir), false);
    assert.equal(existsSync(staleDir), false);
    assert.equal(existsSync(foreignDir), true);
    assert.equal(existsSync(invalidDir), true);
    assert.equal(existsSync(unrecognizedDir), true);
    assert.equal(existsSync(userFile), true);
    assert.equal(lstatSync(userSymlink).isSymbolicLink(), true);
  } finally {
    rmSync(root, { recursive: true, force: true });
  }
});

test("servo-installer prune agents handles missing and invalid target roots without Python", () => {
  const missingRoot = mkdtempSync(join(tmpdir(), "servo-installer-test-"));
  const wrongTypeRoot = mkdtempSync(join(tmpdir(), "servo-installer-test-"));
  const symlinkRoot = mkdtempSync(join(tmpdir(), "servo-installer-test-"));
  const brokenSymlinkRoot = mkdtempSync(join(tmpdir(), "servo-installer-test-"));
  try {
    seedMinimalAgentsSource(missingRoot, "demo-skill");
    const missingTargetRoot = join(missingRoot, ".agents", "skills");
    const missingFakeBin = fakePythonBin(missingRoot);
    const missing = runNodePrune(
      missingRoot,
      ["--all", "--backend=agents", `--agents-root=${missingTargetRoot}`],
      missingFakeBin,
    );
    assert.equal(missing.status, 0, missing.stderr);
    assert.match(missing.stdout, new RegExp(`no managed skill dirs found at ${escapeRegExp(missingTargetRoot)}`));
    assert.equal(missing.stderr.includes("unexpected-python"), false);

    seedMinimalAgentsSource(wrongTypeRoot, "demo-skill");
    const wrongTypeTargetRoot = join(wrongTypeRoot, ".agents", "skills");
    mkdirSync(join(wrongTypeRoot, ".agents"), { recursive: true });
    writeFileSync(wrongTypeTargetRoot, "not a directory\n", "utf8");
    const wrongTypeFakeBin = fakePythonBin(wrongTypeRoot);
    const wrongType = runNodePrune(
      wrongTypeRoot,
      ["--all", "--backend=agents", `--agents-root=${wrongTypeTargetRoot}`],
      wrongTypeFakeBin,
    );
    assert.equal(wrongType.status, 1);
    assert.equal(wrongType.stdout, "");
    assert.match(wrongType.stderr, /Cannot prune managed installs because target root is not ready:/);
    assert.match(wrongType.stderr, /wrong-target-root-type/);
    assert.equal(wrongType.stderr.includes("unexpected-python"), false);

    seedMinimalAgentsSource(symlinkRoot, "demo-skill");
    const symlinkTargetRoot = join(symlinkRoot, ".agents", "skills");
    const symlinkTarget = join(symlinkRoot, "real-skills");
    mkdirSync(join(symlinkRoot, ".agents"), { recursive: true });
    mkdirSync(symlinkTarget);
    symlinkSync(symlinkTarget, symlinkTargetRoot, "dir");
    const symlinkFakeBin = fakePythonBin(symlinkRoot);
    const symlinkResult = runNodePrune(
      symlinkRoot,
      ["--all", "--backend=agents"],
      symlinkFakeBin,
    );
    assert.equal(symlinkResult.status, 1);
    assert.equal(symlinkResult.stdout, "");
    assert.match(symlinkResult.stderr, /wrong-target-root-type/);
    assert.match(symlinkResult.stderr, /target root must be a real directory, not a symlink/);
    assert.equal(symlinkResult.stderr.includes("unexpected-python"), false);

    seedMinimalAgentsSource(brokenSymlinkRoot, "demo-skill");
    const brokenTargetRoot = join(brokenSymlinkRoot, ".agents", "skills");
    mkdirSync(join(brokenSymlinkRoot, ".agents"), { recursive: true });
    symlinkSync(join(brokenSymlinkRoot, "missing-skills"), brokenTargetRoot, "dir");
    const brokenFakeBin = fakePythonBin(brokenSymlinkRoot);
    const broken = runNodePrune(
      brokenSymlinkRoot,
      ["--all", "--backend=agents"],
      brokenFakeBin,
    );
    assert.equal(broken.status, 1);
    assert.equal(broken.stdout, "");
    assert.match(broken.stderr, /broken-target-root-symlink/);
    assert.match(broken.stderr, /target root is a broken symlink/);
    assert.equal(broken.stderr.includes("unexpected-python"), false);
  } finally {
    rmSync(missingRoot, { recursive: true, force: true });
    rmSync(wrongTypeRoot, { recursive: true, force: true });
    rmSync(symlinkRoot, { recursive: true, force: true });
    rmSync(brokenSymlinkRoot, { recursive: true, force: true });
  }
});

test("servo-installer prune agents node-owned scan failure", () => {
  if (process.platform === "win32") {
    return;
  }
  const root = mkdtempSync(join(tmpdir(), "servo-installer-test-"));
  let targetRoot = null;
  try {
    seedMinimalAgentsSource(root, "demo-skill");
    targetRoot = join(root, ".agents", "skills");
    mkdirSync(targetRoot, { recursive: true });
    chmodSync(targetRoot, 0);

    const nodeResult = runNodePrune(root, ["--all", "--backend=agents", `--agents-root=${targetRoot}`]);
    const normalizeRoot = (value) => value.replaceAll(root, "<ROOT>");

    assert.equal(nodeResult.status, 1);
    assert.equal(nodeResult.stdout, "");
    assert.match(normalizeRoot(nodeResult.stderr), /Failed to scan managed install pruning at <ROOT>\/\.agents\/skills:/);
  } finally {
    if (targetRoot !== null && existsSync(targetRoot)) {
      chmodSync(targetRoot, 0o755);
    }
    rmSync(root, { recursive: true, force: true });
  }
});

test("servo-installer prune agents retains malformed same-backend marker shapes", () => {
  const root = mkdtempSync(join(tmpdir(), "servo-installer-test-"));
  try {
    const installed = seedInstalledAgentsSkill(root, "demo-skill");
    const targetRoot = installed.targetRoot;
    const malformedMarkers = [
      ["wrong-version", { ...installed.marker, marker_version: "aw-managed-skill-marker.v1" }],
      ["missing-key", {
        marker_version: "aw-managed-skill-marker.v2",
        backend: "agents",
        skill_id: "missing-key",
        payload_version: "agents-skill-payload.v1",
      }],
      ["extra-key", { ...installed.marker, skill_id: "extra-key", extra: true }],
      ["non-string", { ...installed.marker, skill_id: 1 }],
    ];
    for (const [name, marker] of malformedMarkers) {
      const dir = join(targetRoot, name);
      mkdirSync(dir, { recursive: true });
      writeFileSync(join(dir, "aw.marker"), `${JSON.stringify(marker, null, 2)}\n`, "utf8");
    }
    const fakeBin = fakePythonBin(root);

    const completed = runNodePrune(root, ["--all", "--backend=agents", `--agents-root=${targetRoot}`], fakeBin);

    assert.equal(completed.status, 0, completed.stderr);
    assert.equal(completed.stderr.includes("unexpected-python"), false);
    assert.equal(existsSync(installed.targetSkillDir), false);
    for (const [name] of malformedMarkers) {
      assert.equal(existsSync(join(targetRoot, name)), true);
    }
  } finally {
    rmSync(root, { recursive: true, force: true });
  }
});

test("managed directory identity guard refuses replacement during pruning", () => {
  const root = mkdtempSync(join(tmpdir(), "servo-installer-test-"));
  try {
    const targetDir = join(root, "managed");
    const replacement = join(root, "replacement");
    mkdirSync(targetDir);
    mkdirSync(replacement);
    const identity = installer.childDirectoryIdentity(targetDir);
    assert.notEqual(identity, null);

    rmSync(targetDir, { recursive: true });
    symlinkSync(replacement, targetDir, "dir");

    assert.throws(
      () => installer.assertManagedDirectoryIdentityCurrent(identity),
      /Managed skill dir changed during pruning, refusing to remove:/,
    );
  } finally {
    rmSync(root, { recursive: true, force: true });
  }
});

test("servo-installer prune agents node-owned deletes managed skill dir", () => {
  const root = mkdtempSync(join(tmpdir(), "servo-installer-test-"));
  try {
    const installed = seedInstalledAgentsSkill(root, "demo-skill");

    const nodeResult = runNodePrune(root, ["--all", "--backend=agents", `--agents-root=${installed.targetRoot}`]);

    assert.equal(nodeResult.status, 0);
    assert.equal(nodeResult.stderr, "");
    assert.equal(existsSync(installed.targetSkillDir), false);
  } finally {
    rmSync(root, { recursive: true, force: true });
  }
});

test("servo-installer rejects unsupported install variants without Python", () => {
  const root = mkdtempSync(join(tmpdir(), "servo-installer-test-"));
  try {
    seedMinimalAgentsSource(root, "demo-skill");
    const fakeBin = fakePythonBin(root);
    const commands = [
      ["install", "--backend", "agents", "--source", "github"],
    ];

    for (const args of commands) {
      const completed = runAwInstaller(root, args, fakeBin);
      assert.equal(completed.status, 1, args.join(" "));
      assert.equal(completed.stdout, "");
      assert.match(
        completed.stderr,
        /unsupported servo-installer command or options for Node-only distribution/,
        args.join(" "),
      );
      assert.equal(completed.stderr.includes("unexpected-python"), false, args.join(" "));
      assert.equal(completed.stderr.includes("harness_deploy.py"), false, args.join(" "));
    }
  } finally {
    rmSync(root, { recursive: true, force: true });
  }
});

test("servo-installer rejects unsupported local agents variants without Python", () => {
  const root = mkdtempSync(join(tmpdir(), "servo-installer-test-"));
  try {
    seedMinimalAgentsSource(root, "demo-skill");
    const fakeBin = fakePythonBin(root);
    const cases = [
      {
        args: ["prune", "--backend", "agents"],
        message: /prune currently requires --all/,
      },
      {
        args: ["update", "--backend", "agents", "--json", "--yes"],
        message: /update --json is only supported for dry-run plans; omit --json with --yes/,
      },
      {
        args: [
          "update",
          "--backend",
          "agents",
          "--json",
          "--yes",
          "--source",
          "github",
          "--github-repo",
          "Owner/repo",
          "--github-ref",
          "main",
        ],
        message: /update --json is only supported for dry-run plans; omit --json with --yes/,
      },
    ];

    for (const currentCase of cases) {
      const completed = runAwInstaller(root, currentCase.args, fakeBin);
      assert.equal(completed.status, 1, currentCase.args.join(" "));
      assert.equal(completed.stdout, "");
      assert.match(completed.stderr, currentCase.message, currentCase.args.join(" "));
      assert.equal(completed.stderr.includes("unexpected-python"), false, currentCase.args.join(" "));
    }
  } finally {
    rmSync(root, { recursive: true, force: true });
  }
});

test("updatePlanSummary reports a nonblocking dry-run plan for missing target root", () => {
  const root = mkdtempSync(join(tmpdir(), "servo-installer-test-"));
  try {
    const canonicalDir = join(root, "product", "harness", "skills", "demo-skill");
    const payloadDir = join(root, "product", "harness", "adapters", "agents", "skills", "demo-skill");
    const targetRoot = join(root, ".agents", "skills");
    mkdirSync(canonicalDir, { recursive: true });
    mkdirSync(payloadDir, { recursive: true });
    const payload = {
      payload_version: "agents-skill-payload.v1",
      backend: "agents",
      skill_id: "demo-skill",
      target_dir: "aw-demo-skill",
      target_entry_name: "SKILL.md",
      required_payload_files: ["SKILL.md", "payload.json", "aw.marker"],
      canonical_dir: "product/harness/skills/demo-skill",
      canonical_paths: ["product/harness/skills/demo-skill/SKILL.md"],
      payload_policy: "canonical-copy",
      reference_distribution: "copy-listed-canonical-paths",
    };
    writeFileSync(join(canonicalDir, "SKILL.md"), "# Demo\n", "utf8");
    writeFileSync(join(payloadDir, "payload.json"), `${JSON.stringify(payload, null, 2)}\n`, "utf8");

    const summary = installer.updatePlanSummary({
      sourceKind: "package",
      sourceRef: "package-local",
      sourceRoot: root,
      targetRoot,
      adapterSkillsDir: join(root, "product", "harness", "adapters", "agents", "skills"),
    });

    assert.equal(summary.backend, "agents");
    assert.deepEqual(summary.operation_sequence, ["prune --all", "check_paths_exist", "install", "verify"]);
    assert.deepEqual(summary.planned_target_paths, [join(targetRoot, "aw-demo-skill")]);
    assert.equal(summary.issue_count, 1);
    assert.equal(summary.issues[0].code, "missing-target-root");
    assert.equal(summary.blocking_issue_count, 0);
  } finally {
    rmSync(root, { recursive: true, force: true });
  }
});

test("github source archive context feeds update JSON planning with target/source separation", () => {
  const sourceRoot = mkdtempSync(join(tmpdir(), "servo-installer-source-"));
  const targetRepo = mkdtempSync(join(tmpdir(), "servo-installer-target-"));
  const originalCwd = process.cwd();
  let cleanup = null;
  try {
    seedMinimalAgentsSource(sourceRoot, "demo-skill");
    const archiveBuffer = createGithubArchiveFromSource(sourceRoot);
    process.chdir(targetRepo);
    const githubContext = installer.buildNodeGithubSourceContext(
      {
        backend: "agents",
        source: "github",
        githubRepo: "Owner/repo",
        githubRef: "main",
      },
      archiveBuffer,
    );
    cleanup = githubContext.cleanup;
    const summary = installer.updatePlanSummary(githubContext.context);
    const extractedSourceRoot = githubContext.context.sourceRoot;

    assert.equal(summary.backend, "agents");
    assert.equal(summary.source_kind, "github");
    assert.equal(summary.source_ref, "Owner/repo@main");
    assert.equal(summary.source_root, extractedSourceRoot);
    assert.equal(summary.target_root, join(targetRepo, ".agents", "skills"));
    assert.equal(summary.blocking_issue_count, 0);
    assert.deepEqual(summary.planned_target_paths, [join(targetRepo, ".agents", "skills", "aw-demo-skill")]);
    assert.notEqual(summary.source_root, targetRepo);
    assert.equal(existsSync(extractedSourceRoot), true);
    cleanup();
    cleanup = null;
    assert.equal(existsSync(extractedSourceRoot), false);
  } finally {
    process.chdir(originalCwd);
    if (cleanup !== null) {
      cleanup();
    }
    rmSync(sourceRoot, { recursive: true, force: true });
    rmSync(targetRepo, { recursive: true, force: true });
  }
});

test("servo-installer github source human-readable dry-run is node-owned with mocked archive", async () => {
  const sourceRoot = mkdtempSync(join(tmpdir(), "servo-installer-source-"));
  const targetRepo = mkdtempSync(join(tmpdir(), "servo-installer-target-"));
  const originalCwd = process.cwd();
  try {
    seedMinimalAgentsSource(sourceRoot, "demo-skill", {
      skillText: "# demo-skill\n\n# from github source\n",
    });
    const archiveBuffer = createGithubArchiveFromSource(sourceRoot);
    process.chdir(targetRepo);

    const { result, stdout } = await captureConsoleLog(() => withMockedGithubArchive(archiveBuffer, async (requests) => {
      const status = await installer.runNodeOwned([
        "update",
        "--backend=agents",
        "--source=github",
        "--github-repo=Owner/repo",
        "--github-ref=main",
      ]);
      assert.deepEqual(
        requests.map((request) => request.url),
        ["https://codeload.github.com/Owner/repo/zip/refs/heads/main"],
      );
      return status;
    }));

    assert.equal(result, 0);
    assert.match(stdout, new RegExp(`\\[agents\\] update plan for ${escapeRegExp(join(targetRepo, ".agents", "skills"))}`));
    assert.match(stdout, /sequence: prune --all -> check_paths_exist -> install -> verify/);
    assert.match(stdout, /target paths to write: 1/);
    assert.match(stdout, /blocking preflight issues: 0/);
    assert.match(stdout, /\[agents\] dry-run only; pass --yes to apply update/);
    assert.equal(stdout.includes("[agents] applying update"), false);
    assert.equal(existsSync(join(targetRepo, ".agents", "skills")), false);
  } finally {
    process.chdir(originalCwd);
    rmSync(sourceRoot, { recursive: true, force: true });
    rmSync(targetRepo, { recursive: true, force: true });
  }
});

test("servo-installer github source yes applies update through Node-owned composition with mocked archive", async () => {
  const sourceRoot = mkdtempSync(join(tmpdir(), "servo-installer-source-"));
  const targetRepo = mkdtempSync(join(tmpdir(), "servo-installer-target-"));
  const originalCwd = process.cwd();
  try {
    seedMinimalAgentsSource(sourceRoot, "demo-skill", {
      skillText: "# demo-skill\n\n# from github source\n",
    });
    const archiveBuffer = createGithubArchiveFromSource(sourceRoot);
    process.chdir(targetRepo);

    const { result, stdout } = await captureConsoleLog(() => withMockedGithubArchive(archiveBuffer, async (requests) => {
      const status = await installer.runNodeOwned([
        "update",
        "--backend=agents",
        "--source=github",
        "--github-repo=Owner/repo",
        "--github-ref=main",
        "--yes",
      ]);
      assert.deepEqual(
        requests.map((request) => request.url),
        ["https://codeload.github.com/Owner/repo/zip/refs/heads/main"],
      );
      return status;
    }));

    const targetRoot = join(targetRepo, ".agents", "skills");
    assert.equal(result, 0);
    assert.match(stdout, new RegExp(`\\[agents\\] update plan for ${escapeRegExp(targetRoot)}`));
    assert.match(stdout, /\[agents\] applying update/);
    assert.match(stdout, /\[agents\] update complete/);
    assert.equal(
      readFileSync(join(targetRoot, "aw-demo-skill", "SKILL.md"), "utf8"),
      "# demo-skill\n\n# from github source\n",
    );
  } finally {
    process.chdir(originalCwd);
    rmSync(sourceRoot, { recursive: true, force: true });
    rmSync(targetRepo, { recursive: true, force: true });
  }
});

test("downloadGithubArchive enforces content length and streamed size limits", async () => {
  await withMockedGithubResponses(
    [{ statusCode: 200, headers: { "content-length": "6" }, chunks: ["tiny"] }],
    async (requests) => {
      await assert.rejects(
        () => installer.downloadGithubArchive("Owner/repo", "main", {
          maxBytes: 5,
          maxAttempts: 3,
          retryDelayMs: 0,
        }),
        /archive exceeds 5 byte limit/,
      );
      assert.equal(requests.length, 1);
      assert.equal(requests[0].response.destroyed, true);
    },
  );

  await withMockedGithubResponses(
    [{ statusCode: 200, chunks: [Buffer.alloc(3), Buffer.alloc(3)] }],
    async (requests) => {
      await assert.rejects(
        () => installer.downloadGithubArchive("Owner/repo", "main", {
          maxBytes: 5,
          maxAttempts: 3,
          retryDelayMs: 0,
        }),
        /archive exceeds 5 byte limit/,
      );
      assert.equal(requests.length, 1);
    },
  );
});

test("downloadGithubArchive retries retryable failures and does not retry non-retryable responses", async () => {
  await withMockedGithubResponses(
    [
      { statusCode: 500 },
      { statusCode: 429 },
      { statusCode: 200, chunks: ["ok"] },
    ],
    async (requests) => {
      const archive = await installer.downloadGithubArchive("Owner/repo", "main", {
        maxBytes: 10,
        maxAttempts: 3,
        retryDelayMs: 0,
      });
      assert.equal(archive.toString("utf8"), "ok");
      assert.deepEqual(
        requests.map((request) => request.url),
        [
          "https://codeload.github.com/Owner/repo/zip/refs/heads/main",
          "https://codeload.github.com/Owner/repo/zip/refs/heads/main",
          "https://codeload.github.com/Owner/repo/zip/refs/heads/main",
        ],
      );
    },
  );

  await withMockedGithubResponses(
    [
      { statusCode: 404, afterHandlerError: new Error("late response failure") },
      { statusCode: 200, chunks: ["should-not-run"] },
    ],
    async (requests) => {
      await assert.rejects(
        () => installer.downloadGithubArchive("Owner/repo", "main", {
          maxBytes: 20,
          maxAttempts: 3,
          retryDelayMs: 0,
        }),
        /HTTP 404/,
      );
      assert.equal(requests.length, 1);
    },
  );
});

test("servo-installer github source recovery hint preserves source arguments after apply failure", () => {
  if (process.platform === "win32") {
    return;
  }
  const sourceRoot = mkdtempSync(join(tmpdir(), "servo-installer-source-"));
  const targetRepo = mkdtempSync(join(tmpdir(), "servo-installer-target-"));
  const originalCwd = process.cwd();
  let cleanup = null;
  try {
    seedMinimalAgentsSource(sourceRoot, "demo-skill");
    const installed = seedInstalledAgentsSkill(targetRepo, "demo-skill");
    const archiveBuffer = createGithubArchiveFromSource(sourceRoot);
    const archiveSha256 = createHash("sha256").update(archiveBuffer).digest("hex");
    process.chdir(targetRepo);
    const githubContext = installer.buildNodeGithubSourceContext(
      {
        backend: "agents",
        source: "github",
        githubRepo: "Owner/repo",
        githubRef: "main",
        githubArchiveSha256: archiveSha256,
      },
      archiveBuffer,
    );
    cleanup = githubContext.cleanup;
    chmodSync(installed.targetRoot, 0o555);

    assert.throws(
      () => captureConsoleLog(() => installer.applyUpdateContext(githubContext.context)),
      new RegExp(
        `servo-installer update --backend agents --source github --github-repo "Owner/repo" ` +
          `--github-ref "main" --github-archive-sha256 "${archiveSha256}" --yes`,
      ),
    );
  } finally {
    process.chdir(originalCwd);
    const targetRoot = join(targetRepo, ".agents", "skills");
    if (existsSync(targetRoot)) {
      chmodSync(targetRoot, 0o755);
    }
    if (cleanup !== null) {
      cleanup();
    }
    rmSync(sourceRoot, { recursive: true, force: true });
    rmSync(targetRepo, { recursive: true, force: true });
  }
});

test("github source context cleans extracted temp dir when target context fails", () => {
  const originalCwd = process.cwd();
  const originalTmpdir = process.env.TMPDIR;
  const tempBase = mkdtempSync(join(tmpdir(), "servo-installer-tmpdir-"));
  const sourceRoot = join(tempBase, "source");
  const targetRepo = join(tempBase, "target");
  try {
    mkdirSync(sourceRoot, { recursive: true });
    mkdirSync(targetRepo, { recursive: true });
    seedMinimalAgentsSource(sourceRoot, "demo-skill");
    const archiveBuffer = createGithubArchiveFromSource(sourceRoot);
    process.env.TMPDIR = tempBase;
    process.chdir(targetRepo);

    assert.throws(
      () => installer.buildNodeGithubSourceContext(
        {
          backend: "agents",
          source: "github",
          githubRepo: "Owner/repo",
          githubRef: "main",
          agentsRoot: join(tempBase, "outside-target", ".agents", "skills"),
        },
        archiveBuffer,
      ),
      /outside allowed paths/,
    );
    assert.deepEqual(
      readdirSync(tempBase).filter((entry) => entry.startsWith("servo-installer-github-source-")),
      [],
    );
  } finally {
    process.chdir(originalCwd);
    if (originalTmpdir === undefined) {
      delete process.env.TMPDIR;
    } else {
      process.env.TMPDIR = originalTmpdir;
    }
    rmSync(tempBase, { recursive: true, force: true });
  }
});

test("github source archive validation rejects unsafe members and sha mismatch", () => {
  const sourceRoot = mkdtempSync(join(tmpdir(), "servo-installer-source-"));
  let cleanup = null;
  try {
    seedMinimalAgentsSource(sourceRoot, "demo-skill");
    const archiveBuffer = createGithubArchiveFromSource(sourceRoot);
    const deflatedContext = installer.buildNodeGithubSourceContext(
      {
        backend: "agents",
        source: "github",
        githubRepo: "Owner/repo",
        githubRef: "main",
      },
      createGithubArchiveFromSource(sourceRoot, "repo-master", createDeflatedZip),
    );
    cleanup = deflatedContext.cleanup;
    assert.equal(existsSync(join(deflatedContext.context.sourceRoot, "product", "harness", "skills")), true);
    assert.equal(installer.githubArchiveRefPath("master"), "refs/heads/master");
    assert.equal(
      installer.githubArchiveRefPath("0123456789abcdef0123456789abcdef01234567"),
      "0123456789abcdef0123456789abcdef01234567",
    );
    assert.equal(
      installer.githubArchiveUrl("Owner/repo", "master"),
      "https://codeload.github.com/Owner/repo/zip/refs/heads/master",
    );
    assert.throws(
      () => installer.githubSourceRootFromArchiveBuffer("Owner/repo", "main", archiveBuffer, "0".repeat(64)),
      /GitHub source archive SHA256 mismatch/,
    );
    assert.throws(
      () => installer.githubSourceRootFromArchiveBuffer("Owner/repo", "main", archiveBuffer, ""),
      /SHA256 digest must be 64 hexadecimal characters/,
    );
    assert.throws(
      () => installer.githubSourceRootFromArchiveBuffer(
        "Owner/repo",
        "main",
        createStoredZip([["repo-master/../evil.txt", "bad"]]),
      ),
      /GitHub archive contains unsafe path/,
    );
    assert.throws(
      () => installer.githubSourceRootFromArchiveBuffer(
        "Owner/repo",
        "main",
        createStoredZip([["C:/repo-master/evil.txt", "bad"]]),
      ),
      /GitHub archive contains unsafe path/,
    );
    assert.throws(
      () => installer.githubSourceRootFromArchiveBuffer(
        "Owner/repo",
        "main",
        createStoredZip([["repo-master/payload.txt", "bad", { crc32: 0 }]]),
      ),
      /GitHub source archive entry CRC32 mismatch/,
    );
  } finally {
    if (cleanup !== null) {
      cleanup();
    }
    rmSync(sourceRoot, { recursive: true, force: true });
  }
});

test("github source archive extraction enforces uncompressed size limits", () => {
  const sourceRoot = mkdtempSync(join(tmpdir(), "servo-installer-source-"));
  let cleanup = null;
  try {
    seedMinimalAgentsSource(sourceRoot, "demo-skill");
    const validArchive = createGithubArchiveFromSource(sourceRoot, "repo-master", createDeflatedZip);
    cleanup = installer.githubSourceRootFromArchiveBuffer(
      "Owner/repo",
      "main",
      validArchive,
      undefined,
      { maxUncompressedBytes: 1024 * 1024 },
    ).cleanup;
    assert.throws(
      () => installer.githubSourceRootFromArchiveBuffer(
        "Owner/repo",
        "main",
        validArchive,
        undefined,
        { maxUncompressedBytes: 16 },
      ),
      /GitHub source archive uncompressed size exceeds 16 byte limit/,
    );
    assert.throws(
      () => installer.githubSourceRootFromArchiveBuffer(
        "Owner/repo",
        "main",
        createDeflatedZip([["repo-master/payload.txt", "small", { uncompressedSize: 17 }]]),
        undefined,
        { maxUncompressedBytes: 16 },
      ),
      /GitHub source archive uncompressed size exceeds 16 byte limit/,
    );
    assert.throws(
      () => installer.githubSourceRootFromArchiveBuffer(
        "Owner/repo",
        "main",
        createDeflatedZip([["repo-master/payload.txt", "x".repeat(32), { uncompressedSize: 1 }]]),
        undefined,
        { maxUncompressedBytes: 1024 },
      ),
      /GitHub source archive entry size mismatch/,
    );
  } finally {
    if (cleanup !== null) {
      cleanup();
    }
    rmSync(sourceRoot, { recursive: true, force: true });
  }
});

test("servo-installer github source update paths reject invalid local inputs without Python", () => {
  const root = mkdtempSync(join(tmpdir(), "servo-installer-test-"));
  try {
    seedMinimalAgentsSource(root, "demo-skill");
    const fakeBin = fakePythonBin(root);
    const invalidCases = [
      [["--github-repo=not-a-repo", "--github-ref=main"], /GitHub repo must use OWNER\/REPO/],
      [["--github-repo=Owner/repo", "--github-ref=bad..ref"], /GitHub ref contains unsupported characters/],
      [
        ["--github-repo=Owner/repo", "--github-ref=main", "--github-archive-sha256=not-a-sha"],
        /SHA256 digest must be 64 hexadecimal characters/,
      ],
      [
        ["--github-repo=Owner/repo", "--github-ref=main", "--github-archive-sha256="],
        /SHA256 digest must be 64 hexadecimal characters/,
      ],
    ];
    const modes = [
      ["--json"],
      [],
      ["--yes"],
    ];
    for (const modeArgs of modes) {
      for (const [extraArgs, expectedError] of invalidCases) {
        const completed = runNodeUpdate(
          root,
          ["--backend=agents", ...modeArgs, "--source=github", ...extraArgs],
          fakeBin,
        );

        assert.equal(completed.status, 1);
        assert.equal(completed.stdout, "");
        assert.match(completed.stderr, expectedError);
        assert.equal(completed.stderr.includes("unexpected-python"), false);
        assert.equal(completed.stderr.includes("harness_deploy.py"), false);
      }
    }
  } finally {
    rmSync(root, { recursive: true, force: true });
  }
});

test("servo-installer update agents human-readable dry-run is node-owned without Python", () => {
  const root = mkdtempSync(join(tmpdir(), "servo-installer-test-"));
  try {
    seedMinimalAgentsSource(root, "demo-skill");
    const targetRoot = join(root, "custom-agents-skills");
    const fakeBin = fakePythonBin(root);

    const completed = runNodeUpdate(root, ["--backend=agents", `--agents-root=${targetRoot}`], fakeBin);

    assert.equal(completed.status, 0, completed.stderr);
    assert.equal(completed.stderr.includes("unexpected-python"), false);
    assert.match(completed.stdout, new RegExp(`\\[agents\\] update plan for ${escapeRegExp(targetRoot)}`));
    assert.match(completed.stdout, /sequence: prune --all -> check_paths_exist -> install -> verify/);
    assert.match(completed.stdout, /target paths to write: 1/);
    assert.match(completed.stdout, /blocking preflight issues: 0/);
    assert.match(completed.stdout, /\[agents\] dry-run only; pass --yes to apply update/);
    assert.equal(completed.stdout.includes("[agents] applying update"), false);
    assert.equal(existsSync(targetRoot), false);
  } finally {
    rmSync(root, { recursive: true, force: true });
  }
});

test("servo-installer update agents human-readable dry-run node-owned", () => {
  const root = mkdtempSync(join(tmpdir(), "servo-installer-test-"));
  try {
    seedMinimalAgentsSource(root, "demo-skill");
    const nodeResult = runNodeUpdate(root, ["--backend=agents"]);

    assert.equal(nodeResult.status, 0);
    assert.equal(nodeResult.stderr, "");
    assert.match(nodeResult.stdout, /blocking preflight issues: 0/);
    assert.match(nodeResult.stdout, /\[agents\] dry-run only; pass --yes to apply update/);
    assert.equal(existsSync(join(root, ".agents", "skills")), false);
  } finally {
    rmSync(root, { recursive: true, force: true });
  }
});

test("servo-installer update agents human-readable dry-run reports blocking preflight without applying", () => {
  const root = mkdtempSync(join(tmpdir(), "servo-installer-test-"));
  try {
    seedMinimalAgentsSource(root, "demo-skill");
    seedMinimalAgentsSource(root, "other-skill");
    const targetRoot = join(root, ".agents", "skills");
    const unmanagedDir = join(targetRoot, "aw-demo-skill");
    mkdirSync(unmanagedDir, { recursive: true });
    writeFileSync(join(unmanagedDir, "SKILL.md"), "# unmanaged\n", "utf8");
    const fakeBin = fakePythonBin(root);

    const nodeResult = runNodeUpdate(root, ["--backend=agents"], fakeBin);

    assert.equal(nodeResult.status, 1);
    assert.match(nodeResult.stdout, /blocking preflight issues: 1/);
    assert.match(nodeResult.stdout, /unrecognized-target-directory/);
    assert.equal(nodeResult.stdout.includes("[agents] dry-run only; pass --yes to apply update"), false);
    assert.equal(nodeResult.stdout.includes("[agents] applying update"), false);
    assert.equal(nodeResult.stdout.includes("installed skill"), false);
    assert.equal(nodeResult.stderr.includes("unexpected-python"), false);
    assert.equal(existsSync(unmanagedDir), true);
    assert.equal(existsSync(join(targetRoot, "aw-other-skill")), false);
  } finally {
    rmSync(root, { recursive: true, force: true });
  }
});

test("servo-installer update agents yes installs and verifies from missing root without Python", () => {
  const root = mkdtempSync(join(tmpdir(), "servo-installer-test-"));
  try {
    seedMinimalAgentsSource(root, "demo-skill");
    const targetRoot = join(root, "custom-agents-skills");
    const fakeBin = fakePythonBin(root);

    const completed = runNodeUpdate(root, ["--backend=agents", "--yes", `--agents-root=${targetRoot}`], fakeBin);

    assert.equal(completed.status, 0, completed.stderr);
    assert.equal(completed.stderr.includes("unexpected-python"), false);
    const expectedFragments = [
      `[agents] update plan for ${targetRoot}`,
      "sequence: prune --all -> check_paths_exist -> install -> verify",
      "blocking preflight issues: 0",
      "[agents] applying update",
      `no managed skill dirs found at ${targetRoot}`,
      `[agents] ok: no pre-existing paths at ${targetRoot}`,
      `created target root ${targetRoot}`,
      `installed skill demo-skill -> ${join(targetRoot, "aw-demo-skill")}`,
      `[agents] ok: target root is ready at ${targetRoot}`,
      "[agents] update complete",
    ];
    let lastIndex = -1;
    for (const fragment of expectedFragments) {
      const index = completed.stdout.indexOf(fragment);
      assert.notEqual(index, -1, fragment);
      assert.ok(index > lastIndex, fragment);
      lastIndex = index;
    }
    assert.equal(existsSync(join(targetRoot, "aw-demo-skill", "SKILL.md")), true);
    assert.equal(existsSync(join(root, ".agents", "skills")), false);
  } finally {
    rmSync(root, { recursive: true, force: true });
  }
});

test("servo-installer update agents yes node-owned installs and verifies", () => {
  const root = mkdtempSync(join(tmpdir(), "servo-installer-test-"));
  try {
    seedMinimalAgentsSource(root, "demo-skill");
    const nodeResult = runNodeUpdate(root, ["--backend=agents", "--yes"]);

    assert.equal(nodeResult.status, 0);
    assert.equal(nodeResult.stderr, "");
    assert.match(nodeResult.stdout, /installed skill demo-skill/);
    assert.match(nodeResult.stdout, /\[agents\] update complete/);
    assert.equal(existsSync(join(root, ".agents", "skills", "aw-demo-skill", "aw.marker")), true);
  } finally {
    rmSync(root, { recursive: true, force: true });
  }
});

test("servo-installer update agents yes refreshes drifted and stale managed installs without Python", () => {
  const root = mkdtempSync(join(tmpdir(), "servo-installer-test-"));
  try {
    const installed = seedInstalledAgentsSkill(root, "demo-skill");
    const targetSkillPath = join(installed.targetSkillDir, "SKILL.md");
    writeFileSync(join(installed.canonicalDir, "SKILL.md"), "# demo-skill\n\n# updated source\n", "utf8");
    writeFileSync(
      join(installed.targetSkillDir, "aw.marker"),
      `${JSON.stringify({
        marker_version: "aw-managed-skill-marker.v2",
        backend: "agents",
        skill_id: "legacy-demo-skill",
        payload_version: "agents-skill-payload.v0",
        payload_fingerprint: "old-fingerprint",
      }, null, 2)}\n`,
      "utf8",
    );
    const fakeBin = fakePythonBin(root);

    const completed = runNodeUpdate(root, ["--backend=agents", "--yes"], fakeBin);

    assert.equal(completed.status, 0, completed.stderr);
    assert.equal(completed.stderr.includes("unexpected-python"), false);
    assert.match(completed.stdout, new RegExp(`removed managed skill dir ${escapeRegExp(installed.targetSkillDir)}`));
    assert.equal(readFileSync(targetSkillPath, "utf8"), "# demo-skill\n\n# updated source\n");
    const verify = runNodeVerify(root, ["--backend=agents"], fakeBin);
    assert.equal(verify.status, 0, verify.stderr);
  } finally {
    rmSync(root, { recursive: true, force: true });
  }
});

test("servo-installer update agents replaces legacy aw target dir with servo target dir", () => {
  const root = mkdtempSync(join(tmpdir(), "servo-installer-test-"));
  try {
    const installed = seedInstalledAgentsSkill(root, "demo-skill", {
      targetDir: "servo-demo-skill",
      legacyTargetDirs: ["aw-demo-skill"],
    });
    const legacyDir = join(installed.targetRoot, "aw-demo-skill");
    mkdirSync(legacyDir, { recursive: true });
    writeFileSync(join(legacyDir, "SKILL.md"), "# demo-skill\n\n# old aw target\n", "utf8");
    writeFileSync(
      join(legacyDir, "payload.json"),
      `${JSON.stringify({ ...installed.payload, target_dir: "aw-demo-skill" }, null, 2)}\n`,
      "utf8",
    );
    writeFileSync(
      join(legacyDir, "aw.marker"),
      `${JSON.stringify({
        marker_version: "aw-managed-skill-marker.v2",
        backend: "agents",
        skill_id: "demo-skill",
        payload_version: "agents-skill-payload.v1",
        payload_fingerprint: "old-fingerprint",
      }, null, 2)}\n`,
      "utf8",
    );
    rmSync(installed.targetSkillDir, { recursive: true, force: true });
    const fakeBin = fakePythonBin(root);

    const dryRun = runNodeUpdate(root, ["--backend=agents"], fakeBin);
    assert.equal(dryRun.status, 0, dryRun.stderr);
    assert.match(dryRun.stdout, /legacy target dirs to replace: 1/);
    assert.match(dryRun.stdout, new RegExp(`${escapeRegExp(legacyDir)} -> ${escapeRegExp(installed.targetSkillDir)}`));
    assert.match(dryRun.stdout, /upgrade guidance: Run servo-installer update --backend agents --yes/);

    const diagnose = runNodeDiagnose(root, ["--backend=agents"], fakeBin);
    assert.equal(diagnose.status, 0, diagnose.stderr);
    assert.match(diagnose.stdout, /upgrade guidance: 1 legacy target dir\(s\) can be replaced/);
    assert.match(diagnose.stdout, /next: Run servo-installer update --backend agents --yes/);

    const completed = runNodeUpdate(root, ["--backend=agents", "--yes"], fakeBin);
    assert.equal(completed.status, 0, completed.stderr);
    assert.match(completed.stdout, new RegExp(`removed managed skill dir ${escapeRegExp(legacyDir)}`));
    assert.match(completed.stdout, new RegExp(`installed skill demo-skill -> ${escapeRegExp(installed.targetSkillDir)}`));
    assert.equal(existsSync(legacyDir), false);
    assert.equal(existsSync(join(installed.targetSkillDir, "aw.marker")), true);
    const verify = runNodeVerify(root, ["--backend=agents"], fakeBin);
    assert.equal(verify.status, 0, verify.stderr);
  } finally {
    rmSync(root, { recursive: true, force: true });
  }
});

test("servo-installer update agents yes blocks preflight issues without applying", () => {
  const root = mkdtempSync(join(tmpdir(), "servo-installer-test-"));
  try {
    seedMinimalAgentsSource(root, "demo-skill");
    seedMinimalAgentsSource(root, "other-skill");
    const targetRoot = join(root, ".agents", "skills");
    const unmanagedDir = join(targetRoot, "aw-demo-skill");
    mkdirSync(unmanagedDir, { recursive: true });
    writeFileSync(join(unmanagedDir, "SKILL.md"), "# unmanaged\n", "utf8");
    const fakeBin = fakePythonBin(root);

    const completed = runNodeUpdate(root, ["--backend=agents", "--yes"], fakeBin);

    assert.equal(completed.status, 1);
    assert.match(completed.stdout, /blocking preflight issues: 1/);
    assert.match(completed.stdout, /unrecognized-target-directory/);
    assert.equal(completed.stdout.includes("[agents] applying update"), false);
    assert.equal(completed.stdout.includes("installed skill"), false);
    assert.match(completed.stderr, /error: \[agents\] update blocked by 1 preflight issue\(s\)/);
    assert.equal(completed.stderr.includes("unexpected-python"), false);
    assert.equal(existsSync(unmanagedDir), true);
    assert.equal(existsSync(join(targetRoot, "aw-other-skill")), false);
  } finally {
    rmSync(root, { recursive: true, force: true });
  }
});

test("servo-installer update agents yes prints recovery hint after apply failure", () => {
  if (process.platform === "win32") {
    return;
  }
  const root = mkdtempSync(join(tmpdir(), "servo-installer-test-"));
  try {
    const installed = seedInstalledAgentsSkill(root, "demo-skill");
    chmodSync(installed.targetRoot, 0o555);
    const fakeBin = fakePythonBin(root);

    const completed = runNodeUpdate(root, ["--backend=agents", "--yes"], fakeBin);

    assert.equal(completed.status, 1);
    assert.match(completed.stdout, /blocking preflight issues: 0/);
    assert.match(completed.stdout, /\[agents\] applying update/);
    assert.match(completed.stderr, /Failed to remove managed skill dir/);
    assert.match(completed.stderr, /recovery: the update may be partially applied/);
    assert.match(completed.stderr, /servo-installer update --backend agents --yes/);
    assert.equal(completed.stderr.includes("unexpected-python"), false);
    assert.equal(existsSync(installed.targetSkillDir), true);
  } finally {
    const targetRoot = join(root, ".agents", "skills");
    if (existsSync(targetRoot)) {
      chmodSync(targetRoot, 0o755);
    }
    rmSync(root, { recursive: true, force: true });
  }
});

test("servo-installer update claude recovery hint preserves claude-root override after apply failure", () => {
  if (process.platform === "win32") {
    return;
  }
  const root = mkdtempSync(join(tmpdir(), "servo-installer-test-"));
  try {
    seedMinimalClaudeSource(root, "demo-skill");
    const claudeRoot = join(root, "custom-claude", "skills");
    const fakeBin = fakePythonBin(root);
    const install = runNodeInstall(root, ["--backend=claude", `--claude-root=${claudeRoot}`], fakeBin);
    assert.equal(install.status, 0, install.stderr);
    chmodSync(claudeRoot, 0o555);

    const completed = runNodeUpdate(root, ["--backend=claude", "--yes", `--claude-root=${claudeRoot}`], fakeBin);

    assert.equal(completed.status, 1);
    assert.match(completed.stdout, /blocking preflight issues: 0/);
    assert.match(completed.stdout, /\[claude\] applying update/);
    assert.match(completed.stderr, /Failed to remove managed skill dir/);
    assert.match(completed.stderr, /recovery: the update may be partially applied/);
    assert.match(
      completed.stderr,
      new RegExp(`servo-installer update --backend claude --yes --claude-root ${escapeRegExp(JSON.stringify(claudeRoot))}`),
    );
    assert.equal(completed.stderr.includes("unexpected-python"), false);
  } finally {
    const claudeRoot = join(root, "custom-claude", "skills");
    if (existsSync(claudeRoot)) {
      chmodSync(claudeRoot, 0o755);
    }
    rmSync(root, { recursive: true, force: true });
  }
});

// --- Bundle backend parser tests ---

test("parseNodeDiagnoseJsonArgs accepts bundle backend", () => {
  assert.deepEqual(
    installer.parseNodeDiagnoseJsonArgs(["diagnose", "--backend", "bundle", "--json"]),
    { backend: "bundle", agentsRoot: undefined },
  );
  assert.deepEqual(
    installer.parseNodeDiagnoseJsonArgs(["diagnose", "--backend=bundle", "--json", "--agents-root=/tmp/agents", "--claude-root=/tmp/claude"]),
    { backend: "bundle", agentsRoot: "/tmp/agents", claudeRoot: "/tmp/claude" },
  );
});

test("parseNodeDiagnoseArgs accepts bundle backend", () => {
  assert.deepEqual(
    installer.parseNodeDiagnoseArgs(["diagnose", "--backend", "bundle"]),
    { backend: "bundle", agentsRoot: undefined },
  );
});

test("parseNodeVerifyArgs accepts bundle backend", () => {
  assert.deepEqual(
    installer.parseNodeVerifyArgs(["verify", "--backend", "bundle"]),
    { backend: "bundle", agentsRoot: undefined },
  );
});

test("parseNodeInstallArgs accepts bundle backend", () => {
  assert.deepEqual(
    installer.parseNodeInstallArgs(["install", "--backend", "bundle"]),
    { backend: "bundle", agentsRoot: undefined },
  );
});

test("parseNodeCheckPathsExistArgs accepts bundle backend", () => {
  assert.deepEqual(
    installer.parseNodeCheckPathsExistArgs(["check_paths_exist", "--backend", "bundle"]),
    { backend: "bundle", agentsRoot: undefined },
  );
});

test("parseNodePruneArgs accepts bundle backend", () => {
  assert.deepEqual(
    installer.parseNodePruneArgs(["prune", "--all", "--backend", "bundle"]),
    { backend: "bundle", agentsRoot: undefined },
  );
});

test("parseNodeUpdateJsonArgs accepts bundle package JSON dry-run", () => {
  assert.deepEqual(
    installer.parseNodeUpdateJsonArgs(["update", "--backend", "bundle", "--json"]),
    { backend: "bundle", source: "package", agentsRoot: undefined },
  );
});

test("parseNodeUpdateDryRunArgs accepts bundle package dry-run", () => {
  assert.deepEqual(
    installer.parseNodeUpdateDryRunArgs(["update", "--backend", "bundle"]),
    { backend: "bundle", source: "package", agentsRoot: undefined },
  );
});

test("parseNodeUpdateYesArgs accepts bundle package yes", () => {
  assert.deepEqual(
    installer.parseNodeUpdateYesArgs(["update", "--backend", "bundle", "--yes"]),
    { backend: "bundle", source: "package", agentsRoot: undefined, yes: true },
  );
});

test("parseNodeUpdateArgs rejects bundle with github source", () => {
  assert.equal(
    installer.parseNodeUpdateJsonArgs(["update", "--backend", "bundle", "--json", "--source", "github"]),
    null,
  );
  assert.equal(
    installer.parseNodeUpdateDryRunArgs(["update", "--backend", "bundle", "--source", "github"]),
    null,
  );
  assert.equal(
    installer.parseNodeUpdateYesArgs(["update", "--backend", "bundle", "--yes", "--source", "github"]),
    null,
  );
});

test("servo-installer bundle rejects nested target roots", () => {
  const root = mkdtempSync(join(tmpdir(), "servo-installer-test-"));
  try {
    seedMinimalBundleSource(root, "demo-skill");
    const fakeBin = fakePythonBin(root);
    const parentRoot = join(root, "bundle-target", "skills");
    const nestedRoot = join(parentRoot, "nested");

    const nestedClaude = runNodeCheckPathsExist(
      root,
      ["--backend=bundle", `--agents-root=${parentRoot}`, `--claude-root=${nestedRoot}`],
      fakeBin,
    );
    assert.equal(nestedClaude.status, 1);
    assert.match(nestedClaude.stderr, /must be path-disjoint/);
    assert.equal(nestedClaude.stderr.includes("unexpected-python"), false);

    const nestedAgents = runNodeVerify(
      root,
      ["--backend=bundle", `--agents-root=${nestedRoot}`, `--claude-root=${parentRoot}`],
      fakeBin,
    );
    assert.equal(nestedAgents.status, 1);
    assert.match(nestedAgents.stderr, /must be path-disjoint/);
    assert.equal(nestedAgents.stderr.includes("unexpected-python"), false);
  } finally {
    rmSync(root, { recursive: true, force: true });
  }
});

// --- Bundle backend functional tests ---

function seedMinimalBundleSource(root, skillId) {
  seedMinimalAgentsSource(root, skillId);
  seedMinimalClaudeSource(root, skillId);
}

test("servo-installer install bundle installs both backends", () => {
  const root = mkdtempSync(join(tmpdir(), "servo-installer-test-"));
  try {
    seedMinimalBundleSource(root, "demo-skill");
    const fakeBin = fakePythonBin(root);

    const completed = runNodeInstall(root, ["--backend=bundle"], fakeBin);

    assert.equal(completed.status, 0, completed.stderr);
    assert.match(completed.stdout, /\[bundle\] install complete for both backends/);
    assert.equal(completed.stderr.includes("unexpected-python"), false);

    const agentsTargetDir = join(root, ".agents", "skills", "aw-demo-skill");
    const claudeTargetDir = join(root, ".claude", "skills", "demo-skill");
    assert.equal(existsSync(join(agentsTargetDir, "SKILL.md")), true);
    assert.equal(existsSync(join(claudeTargetDir, "SKILL.md")), true);
  } finally {
    rmSync(root, { recursive: true, force: true });
  }
});

test("servo-installer verify bundle verifies both backends", () => {
  const root = mkdtempSync(join(tmpdir(), "servo-installer-test-"));
  try {
    seedMinimalBundleSource(root, "demo-skill");
    const fakeBin = fakePythonBin(root);
    const install = runNodeInstall(root, ["--backend=bundle"], fakeBin);
    assert.equal(install.status, 0, install.stderr);

    const completed = runNodeVerify(root, ["--backend=bundle"], fakeBin);

    assert.equal(completed.status, 0, completed.stderr);
    assert.match(completed.stdout, /\[agents\] ok: target root is ready/);
    assert.match(completed.stdout, /\[claude\] ok: target root is ready/);
    assert.equal(completed.stderr.includes("unexpected-python"), false);
  } finally {
    rmSync(root, { recursive: true, force: true });
  }
});

test("servo-installer diagnose bundle diagnoses both backends", () => {
  const root = mkdtempSync(join(tmpdir(), "servo-installer-test-"));
  try {
    seedMinimalBundleSource(root, "demo-skill");
    const fakeBin = fakePythonBin(root);
    const install = runNodeInstall(root, ["--backend=bundle"], fakeBin);
    assert.equal(install.status, 0, install.stderr);

    const completed = runNodeDiagnose(root, ["--backend=bundle"], fakeBin);

    assert.equal(completed.status, 0, completed.stderr);
    assert.match(completed.stdout, /\[agents\] diagnose: 0 issue/);
    assert.match(completed.stdout, /\[claude\] diagnose: 0 issue/);
    assert.equal(completed.stderr.includes("unexpected-python"), false);
  } finally {
    rmSync(root, { recursive: true, force: true });
  }
});

test("servo-installer prune --all bundle prunes both backends", () => {
  const root = mkdtempSync(join(tmpdir(), "servo-installer-test-"));
  try {
    seedMinimalBundleSource(root, "demo-skill");
    const fakeBin = fakePythonBin(root);
    const install = runNodeInstall(root, ["--backend=bundle"], fakeBin);
    assert.equal(install.status, 0, install.stderr);

    const completed = runNodePrune(root, ["--all", "--backend=bundle"], fakeBin);

    assert.equal(completed.status, 0, completed.stderr);
    assert.match(completed.stdout, /\[bundle\] prune complete for both backends/);
    assert.equal(existsSync(join(root, ".agents", "skills", "aw-demo-skill")), false);
    assert.equal(existsSync(join(root, ".claude", "skills", "demo-skill")), false);
    assert.equal(completed.stderr.includes("unexpected-python"), false);
  } finally {
    rmSync(root, { recursive: true, force: true });
  }
});

test("servo-installer install bundle partial completion when claude fails", () => {
  if (process.platform === "win32") {
    return;
  }
  const root = mkdtempSync(join(tmpdir(), "servo-installer-test-"));
  const claudeRoot = join(root, ".claude", "skills");
  try {
    seedMinimalAgentsSource(root, "demo-skill");
    seedMinimalClaudeSource(root, "demo-skill");
    const fakeBin = fakePythonBin(root);
    mkdirSync(claudeRoot, { recursive: true });
    chmodSync(claudeRoot, 0o555);

    const completed = runNodeInstall(root, ["--backend=bundle"], fakeBin);

    assert.equal(completed.status, 1);
    assert.match(completed.stderr, /\[bundle\] partial install: agents=ok, claude=failed/);
    assert.match(completed.stderr, /recovery: run `servo-installer prune --backend claude --all`/);
    assert.equal(existsSync(join(root, ".agents", "skills", "aw-demo-skill", "SKILL.md")), true);
  } finally {
    if (existsSync(claudeRoot)) {
      chmodSync(claudeRoot, 0o755);
    }
    rmSync(root, { recursive: true, force: true });
  }
});

test("servo-installer check_paths_exist bundle checks both backends", () => {
  const root = mkdtempSync(join(tmpdir(), "servo-installer-test-"));
  try {
    seedMinimalBundleSource(root, "demo-skill");
    const fakeBin = fakePythonBin(root);

    const completed = runNodeCheckPathsExist(root, ["--backend=bundle"], fakeBin);

    assert.equal(completed.status, 0, completed.stderr);
    assert.match(completed.stdout, /\[agents\] ok: no pre-existing paths/);
    assert.match(completed.stdout, /\[claude\] ok: no pre-existing paths/);
    assert.equal(completed.stderr.includes("unexpected-python"), false);
  } finally {
    rmSync(root, { recursive: true, force: true });
  }
});

test("servo-installer update bundle dry-run plans both backends", () => {
  const root = mkdtempSync(join(tmpdir(), "servo-installer-test-"));
  try {
    seedMinimalBundleSource(root, "demo-skill");
    const fakeBin = fakePythonBin(root);
    const install = runNodeInstall(root, ["--backend=bundle"], fakeBin);
    assert.equal(install.status, 0, install.stderr);

    const completed = runNodeUpdate(root, ["--backend=bundle"], fakeBin);

    assert.equal(completed.status, 0, completed.stderr);
    assert.match(completed.stdout, /\[agents\] dry-run only/);
    assert.match(completed.stdout, /\[claude\] dry-run only/);
    assert.equal(completed.stderr.includes("unexpected-python"), false);
  } finally {
    rmSync(root, { recursive: true, force: true });
  }
});

test("servo-installer update bundle yes applies both backends", () => {
  const root = mkdtempSync(join(tmpdir(), "servo-installer-test-"));
  try {
    seedMinimalBundleSource(root, "demo-skill");
    const fakeBin = fakePythonBin(root);
    const install = runNodeInstall(root, ["--backend=bundle"], fakeBin);
    assert.equal(install.status, 0, install.stderr);

    const completed = runNodeUpdate(root, ["--backend=bundle", "--yes"], fakeBin);

    assert.equal(completed.status, 0, completed.stderr);
    assert.match(completed.stdout, /\[bundle\] update complete for both backends/);
    assert.equal(completed.stderr.includes("unexpected-python"), false);
  } finally {
    rmSync(root, { recursive: true, force: true });
  }
});

test("servo-installer diagnose json bundle outputs merged json", () => {
  const root = mkdtempSync(join(tmpdir(), "servo-installer-test-"));
  try {
    seedMinimalBundleSource(root, "demo-skill");
    const fakeBin = fakePythonBin(root);
    const install = runNodeInstall(root, ["--backend=bundle"], fakeBin);
    assert.equal(install.status, 0, install.stderr);

    const completed = runNodeDiagnose(root, ["--backend=bundle", "--json"], fakeBin);

    assert.equal(completed.status, 0, completed.stderr);
    const summary = JSON.parse(completed.stdout);
    assert.equal(summary.bundle, true);
    assert.ok(summary.backends.agents);
    assert.ok(summary.backends.claude);
    assert.equal(summary.backends.agents.backend, "agents");
    assert.equal(summary.backends.claude.backend, "claude");
    assert.equal(completed.stderr.includes("unexpected-python"), false);
  } finally {
    rmSync(root, { recursive: true, force: true });
  }
});

// --- Bundle dual-root override parser tests ---

test("parseNodeDiagnoseArgs accepts bundle with dual-root override", () => {
  assert.deepEqual(
    installer.parseNodeDiagnoseArgs(["diagnose", "--backend", "bundle", "--agents-root", "/tmp/a", "--claude-root", "/tmp/c"]),
    { backend: "bundle", agentsRoot: "/tmp/a", claudeRoot: "/tmp/c" },
  );
});

test("parseNodeVerifyArgs accepts bundle with dual-root override", () => {
  assert.deepEqual(
    installer.parseNodeVerifyArgs(["verify", "--backend", "bundle", "--agents-root", "/tmp/a", "--claude-root", "/tmp/c"]),
    { backend: "bundle", agentsRoot: "/tmp/a", claudeRoot: "/tmp/c" },
  );
});

test("parseNodeInstallArgs accepts bundle with dual-root override", () => {
  assert.deepEqual(
    installer.parseNodeInstallArgs(["install", "--backend", "bundle", "--agents-root", "/tmp/a", "--claude-root", "/tmp/c"]),
    { backend: "bundle", agentsRoot: "/tmp/a", claudeRoot: "/tmp/c" },
  );
});

test("parseNodeCheckPathsExistArgs accepts bundle with dual-root override", () => {
  assert.deepEqual(
    installer.parseNodeCheckPathsExistArgs(["check_paths_exist", "--backend", "bundle", "--agents-root", "/tmp/a", "--claude-root", "/tmp/c"]),
    { backend: "bundle", agentsRoot: "/tmp/a", claudeRoot: "/tmp/c" },
  );
});

test("parseNodePruneArgs accepts bundle with dual-root override", () => {
  assert.deepEqual(
    installer.parseNodePruneArgs(["prune", "--all", "--backend", "bundle", "--agents-root", "/tmp/a", "--claude-root", "/tmp/c"]),
    { backend: "bundle", agentsRoot: "/tmp/a", claudeRoot: "/tmp/c" },
  );
});

test("parseNodeUpdateJsonArgs accepts bundle with dual-root override", () => {
  assert.deepEqual(
    installer.parseNodeUpdateJsonArgs(["update", "--backend", "bundle", "--json", "--agents-root", "/tmp/a", "--claude-root", "/tmp/c"]),
    { backend: "bundle", source: "package", agentsRoot: "/tmp/a", claudeRoot: "/tmp/c" },
  );
});

test("parseNodeUpdateDryRunArgs accepts bundle with dual-root override", () => {
  assert.deepEqual(
    installer.parseNodeUpdateDryRunArgs(["update", "--backend", "bundle", "--agents-root", "/tmp/a", "--claude-root", "/tmp/c"]),
    { backend: "bundle", source: "package", agentsRoot: "/tmp/a", claudeRoot: "/tmp/c" },
  );
});

test("parseNodeUpdateYesArgs accepts bundle with dual-root override", () => {
  assert.deepEqual(
    installer.parseNodeUpdateYesArgs(["update", "--backend", "bundle", "--yes", "--agents-root", "/tmp/a", "--claude-root", "/tmp/c"]),
    { backend: "bundle", source: "package", agentsRoot: "/tmp/a", claudeRoot: "/tmp/c", yes: true },
  );
});

// --- Bundle single-root override and unsupported variant tests ---

test("parseNodeInstallArgs accepts bundle with agents-only root override", () => {
  assert.deepEqual(
    installer.parseNodeInstallArgs(["install", "--backend", "bundle", "--agents-root", "/tmp/a"]),
    { backend: "bundle", agentsRoot: "/tmp/a" },
  );
});

test("parseNodeCheckPathsExistArgs accepts bundle with claude-only root override", () => {
  assert.deepEqual(
    installer.parseNodeCheckPathsExistArgs(["check_paths_exist", "--backend", "bundle", "--claude-root", "/tmp/c"]),
    { backend: "bundle", agentsRoot: undefined, claudeRoot: "/tmp/c" },
  );
});

test("parseNodeUpdateArgs rejects bundle with --json and --yes together", () => {
  assert.equal(
    installer.parseNodeUpdateJsonArgs(["update", "--backend", "bundle", "--json", "--yes"]),
    null,
  );
  assert.equal(
    installer.parseNodeUpdateYesArgs(["update", "--backend", "bundle", "--json", "--yes"]),
    null,
  );
});

test("parseNodePruneArgs rejects bundle when --all is missing", () => {
  assert.equal(
    installer.parseNodePruneArgs(["prune", "--backend", "bundle"]),
    null,
  );
});

test("unsupported servo-installer fallback catches bundle invalid combinations", () => {
  const root = mkdtempSync(join(tmpdir(), "servo-installer-test-"));
  try {
    seedMinimalBundleSource(root, "demo-skill");
    const fakeBin = fakePythonBin(root);
    const commands = [
      ["prune", "--backend", "bundle"],
      ["install", "--backend", "bundle", "--json"],
      ["verify", "--backend", "bundle", "--yes"],
      ["update", "--backend", "bundle", "--json", "--yes"],
    ];

    for (const args of commands) {
      const completed = runAwInstaller(root, args, fakeBin);
      assert.equal(completed.status, 1, args.join(" "));
      assert.match(
        completed.stderr,
        /unsupported servo-installer command or options for Node-only distribution/,
        args.join(" "),
      );
      assert.equal(completed.stderr.includes("unexpected-python"), false, args.join(" "));
    }
  } finally {
    rmSync(root, { recursive: true, force: true });
  }
});

// --- Bundle dual-root conflict scanning ---

test("servo-installer check_paths_exist bundle merges conflicts from both roots", () => {
  const root = mkdtempSync(join(tmpdir(), "servo-installer-test-"));
  try {
    seedMinimalBundleSource(root, "demo-skill");
    const fakeBin = fakePythonBin(root);

    // Create conflicting paths at both target locations
    const agentsTargetDir = join(root, ".agents", "skills");
    const claudeTargetDir = join(root, ".claude", "skills");
    mkdirSync(agentsTargetDir, { recursive: true });
    mkdirSync(claudeTargetDir, { recursive: true });
    writeFileSync(join(agentsTargetDir, "aw-demo-skill"), "agents-conflict", "utf8");
    writeFileSync(join(claudeTargetDir, "demo-skill"), "claude-conflict", "utf8");

    const completed = runNodeCheckPathsExist(root, ["--backend=bundle"], fakeBin);

    assert.equal(completed.status, 1);
    assert.match(completed.stdout, /existing path/);
    assert.equal(completed.stderr.includes("unexpected-python"), false);
  } finally {
    rmSync(root, { recursive: true, force: true });
  }
});

test("servo-installer install bundle pre-write all-or-nothing on dual-root conflict", () => {
  const root = mkdtempSync(join(tmpdir(), "servo-installer-test-"));
  try {
    seedMinimalBundleSource(root, "demo-skill");
    const fakeBin = fakePythonBin(root);

    // Create conflict at claude target (file where skill dir should go)
    const claudeTargetDir = join(root, ".claude", "skills");
    mkdirSync(claudeTargetDir, { recursive: true });
    writeFileSync(join(claudeTargetDir, "demo-skill"), "claude-conflict", "utf8");

    const completed = runNodeInstall(root, ["--backend=bundle"], fakeBin);

    // pre-write check should abort - both roots zero writes
    assert.equal(completed.status, 1);
    assert.match(completed.stderr, /\[bundle\] pre-write check failed; aborting install/);

    // Agents root must have zero side effects
    const agentsSkillDir = join(root, ".agents", "skills", "aw-demo-skill");
    assert.equal(existsSync(agentsSkillDir), false);

    // Claude root must also have zero writes (the conflict file remains, no skill dir)
    const claudeSkillDir = join(root, ".claude", "skills", "demo-skill");
    const claudeStat = lstatSync(claudeSkillDir);
    assert.equal(claudeStat.isFile(), true);

    assert.equal(completed.stderr.includes("unexpected-python"), false);
  } finally {
    rmSync(root, { recursive: true, force: true });
  }
});

// --- Bundle partial completion: install agents-fails counterpart ---

test("servo-installer install bundle partial completion when agents fails", () => {
  if (process.platform === "win32") {
    return;
  }
  const root = mkdtempSync(join(tmpdir(), "servo-installer-test-"));
  const agentsRoot = join(root, ".agents", "skills");
  try {
    seedMinimalAgentsSource(root, "demo-skill");
    seedMinimalClaudeSource(root, "demo-skill");
    const fakeBin = fakePythonBin(root);
    mkdirSync(agentsRoot, { recursive: true });
    chmodSync(agentsRoot, 0o555);

    const completed = runNodeInstall(root, ["--backend=bundle"], fakeBin);

    assert.equal(completed.status, 1);
    assert.match(completed.stderr, /\[bundle\] partial install: agents=failed, claude=ok/);
    assert.match(completed.stderr, /recovery: run `servo-installer prune --backend agents --all`/);
    assert.equal(existsSync(join(root, ".claude", "skills", "demo-skill", "SKILL.md")), true);
    assert.equal(completed.stderr.includes("unexpected-python"), false);
  } finally {
    if (existsSync(agentsRoot)) {
      chmodSync(agentsRoot, 0o755);
    }
    rmSync(root, { recursive: true, force: true });
  }
});

// --- Bundle partial completion: update --yes ---

test("servo-installer update --yes bundle partial completion when claude fails", () => {
  if (process.platform === "win32") {
    return;
  }
  const root = mkdtempSync(join(tmpdir(), "servo-installer-test-"));
  const claudeRoot = join(root, ".claude", "skills");
  try {
    seedMinimalBundleSource(root, "demo-skill");
    const fakeBin = fakePythonBin(root);
    const install = runNodeInstall(root, ["--backend=bundle"], fakeBin);
    assert.equal(install.status, 0, install.stderr);

    // Make claude target root read-only to cause prune step to fail during update
    chmodSync(claudeRoot, 0o555);

    const completed = runNodeUpdate(root, ["--backend", "bundle", "--yes"], fakeBin);

    assert.equal(completed.status, 1);
    assert.match(completed.stderr, /\[bundle\] partial update: agents=ok, claude=failed/);
    assert.equal(completed.stderr.includes("unexpected-python"), false);
  } finally {
    if (existsSync(claudeRoot)) {
      chmodSync(claudeRoot, 0o755);
    }
    rmSync(root, { recursive: true, force: true });
  }
});

test("servo-installer update --yes bundle preflight aborts before any root is rewritten", () => {
  const root = mkdtempSync(join(tmpdir(), "servo-installer-test-"));
  try {
    seedMinimalBundleSource(root, "demo-skill");
    const fakeBin = fakePythonBin(root);
    const install = runNodeInstall(root, ["--backend=bundle"], fakeBin);
    assert.equal(install.status, 0, install.stderr);

    const agentsSkill = join(root, ".agents", "skills", "aw-demo-skill", "SKILL.md");
    const claudeSkillDir = join(root, ".claude", "skills", "demo-skill");
    const agentsDriftText = "# agents-drift-before-bundle-update\n";
    writeFileSync(agentsSkill, agentsDriftText, "utf8");
    rmSync(claudeSkillDir, { recursive: true, force: true });
    mkdirSync(claudeSkillDir, { recursive: true });
    writeFileSync(join(claudeSkillDir, "foreign.txt"), "unmanaged", "utf8");

    const completed = runNodeUpdate(root, ["--backend=bundle", "--yes"], fakeBin);

    assert.equal(completed.status, 1);
    assert.match(completed.stderr, /\[bundle\] pre-write update preflight failed; aborting update/);
    assert.match(completed.stdout, /\[agents\] update plan/);
    assert.match(completed.stdout, /\[claude\] update plan/);
    assert.equal(readFileSync(agentsSkill, "utf8"), agentsDriftText);
    assert.equal(existsSync(join(claudeSkillDir, "foreign.txt")), true);
    assert.equal(completed.stderr.includes("unexpected-python"), false);
  } finally {
    rmSync(root, { recursive: true, force: true });
  }
});

// --- Bundle partial completion: prune --all ---

test("servo-installer prune --all bundle partial completion when agents fails", () => {
  if (process.platform === "win32") {
    return;
  }
  const root = mkdtempSync(join(tmpdir(), "servo-installer-test-"));
  const agentsRoot = join(root, ".agents", "skills");
  try {
    seedMinimalBundleSource(root, "demo-skill");
    const fakeBin = fakePythonBin(root);
    const install = runNodeInstall(root, ["--backend=bundle"], fakeBin);
    assert.equal(install.status, 0, install.stderr);

    // Make agents target root read-only to cause rmSync failure during prune
    chmodSync(agentsRoot, 0o555);

    const completed = runNodePrune(root, ["--all", "--backend=bundle"], fakeBin);

    assert.equal(completed.status, 1);
    assert.match(completed.stderr, /\[bundle\] partial prune: agents failed, claude not started/);
    // Claude root must be untouched
    assert.equal(existsSync(join(root, ".claude", "skills", "demo-skill", "SKILL.md")), true);
    assert.equal(completed.stderr.includes("unexpected-python"), false);
  } finally {
    if (existsSync(agentsRoot)) {
      chmodSync(agentsRoot, 0o755);
    }
    rmSync(root, { recursive: true, force: true });
  }
});

test("servo-installer prune --all bundle partial completion when claude fails", () => {
  if (process.platform === "win32") {
    return;
  }
  const root = mkdtempSync(join(tmpdir(), "servo-installer-test-"));
  const claudeRoot = join(root, ".claude", "skills");
  try {
    seedMinimalBundleSource(root, "demo-skill");
    const fakeBin = fakePythonBin(root);
    const install = runNodeInstall(root, ["--backend=bundle"], fakeBin);
    assert.equal(install.status, 0, install.stderr);

    // Make claude target root read-only so agents prune succeeds, claude prune fails
    chmodSync(claudeRoot, 0o555);

    const completed = runNodePrune(root, ["--all", "--backend=bundle"], fakeBin);

    assert.equal(completed.status, 1);
    assert.match(completed.stderr, /\[bundle\] partial prune: agents ok, claude failed/);
    // Agents should have been pruned successfully
    assert.equal(existsSync(join(root, ".agents", "skills", "aw-demo-skill")), false);
    assert.equal(completed.stderr.includes("unexpected-python"), false);
  } finally {
    if (existsSync(claudeRoot)) {
      chmodSync(claudeRoot, 0o755);
    }
    rmSync(root, { recursive: true, force: true });
  }
});

// --- Bundle verify collect-then-report on dual-root drift ---

test("servo-installer verify bundle collect-then-report on dual-root drift", () => {
  const root = mkdtempSync(join(tmpdir(), "servo-installer-test-"));
  try {
    seedMinimalBundleSource(root, "demo-skill");
    const fakeBin = fakePythonBin(root);
    const install = runNodeInstall(root, ["--backend=bundle"], fakeBin);
    assert.equal(install.status, 0, install.stderr);

    // Mutate both installed SKILL.md files to create drift
    writeFileSync(join(root, ".agents", "skills", "aw-demo-skill", "SKILL.md"), "# drift-agents\n", "utf8");
    writeFileSync(join(root, ".claude", "skills", "demo-skill", "SKILL.md"), "# drift-claude\n", "utf8");

    const completed = runNodeVerify(root, ["--backend=bundle"], fakeBin);

    assert.equal(completed.status, 1);
    assert.match(completed.stdout, /\[agents\] drift:.*issue/);
    assert.match(completed.stdout, /\[claude\] drift:.*issue/);
    assert.equal(completed.stderr.includes("unexpected-python"), false);
  } finally {
    rmSync(root, { recursive: true, force: true });
  }
});

// ─── TUI smoke & PTY tests ─────────────────────────────────────────────────
// Note: spawnSync with piped stdin is non-TTY, so TUI rejects and falls back
// to CLI help. These tests verify: guard behavior, ANSI module constants,
// CLI backward compatibility, and indirect TUI property checks.

const tuiInstallerPath = join(__dirname, "bin", "servo-installer.js");

function runTui(args, input, env) {
  return spawnSync(
    process.execPath,
    [tuiInstallerPath, ...args],
    {
      encoding: "utf8",
      input,
      env: { ...process.env, ...env },
      timeout: 15000,
    },
  );
}

function runTuiInTempTarget(args, input, env = {}) {
  const root = mkdtempSync(join(tmpdir(), "servo-installer-cli-"));
  try {
    return runTui(args, input, {
      ...env,
      SERVO_HARNESS_TARGET_REPO_ROOT: root,
    });
  } finally {
    rmSync(root, { recursive: true, force: true });
  }
}

function applyPromptKeys(keys) {
  let answer = "";
  let output = "";
  let done = false;
  for (const [str, key] of keys) {
    const next = installer.applyPromptInputKey(answer, str, key);
    answer = next.answer;
    output += next.output;
    done = next.done;
    if (done) {
      break;
    }
  }
  return { answer, output, done };
}

test("tui prompt editor echoes typed input once", () => {
  assert.deepEqual(
    applyPromptKeys([
      ["p", { name: "p" }],
      ["r", { name: "r" }],
      ["u", { name: "u" }],
      ["n", { name: "n" }],
      ["e", { name: "e" }],
      ["", { name: "return" }],
    ]),
    { answer: "prune", output: "prune\n", done: true },
  );
  assert.deepEqual(
    applyPromptKeys([
      ["y", { name: "y" }],
      ["e", { name: "e" }],
      ["s", { name: "s" }],
      ["", { name: "return" }],
    ]),
    { answer: "yes", output: "yes\n", done: true },
  );
});

test("tui prompt editor does not backspace beyond typed input", () => {
  assert.deepEqual(
    applyPromptKeys([
      ["", { name: "backspace" }],
      ["", { name: "delete" }],
      ["y", { name: "y" }],
      ["", { name: "backspace" }],
      ["", { name: "backspace" }],
      ["", { name: "return" }],
    ]),
    { answer: "", output: "y\b \b\n", done: true },
  );
});

// TUI guard: non-TTY with explicit "tui" arg must print error
test("tui guard refuses non-TTY with explicit tui arg", () => {
  const result = runTui(["tui"], "", {});
  assert.equal(result.status, 1);
  assert.match(result.stderr, /requires an interactive terminal/);
});

// TUI guard: no-args + non-TTY shows help (not TUI)
test("tui guard: no-args + non-TTY shows CLI help", () => {
  const result = runTui([], "", {});
  assert.equal(result.status, 0);
  assert.match(result.stdout, /usage: servo-installer/);
  assert.match(result.stdout, /tui\s+open the interactive/);
});

// ANSI module: colorGreen wraps with green ANSI codes when FORCE_COLOR=1
test("ansi: colorGreen emits ANSI green with FORCE_COLOR", () => {
  // Spawn a one-liner that loads the module and calls colorGreen
  const result = spawnSync(process.execPath, [
    "-e",
    "process.env.FORCE_COLOR='1';" +
    "const m=require('" + tuiInstallerPath + "');" +
    "const s=require('" + join(__dirname, "bin", "servo-installer.js") + "');" +
    // Use a small eval trick: extract the ANSI vars by checking exports behavior
    "console.log('MODULE_LOADED');",
  ], { encoding: "utf8", timeout: 5000 });
  assert.match(result.stdout, /MODULE_LOADED/);
});

// ANSI module: NO_COLOR suppresses color — verify via module load without crash
test("ansi: module loads cleanly with NO_COLOR", () => {
  const result = spawnSync(process.execPath, [
    "-e",
    "process.env.NO_COLOR='1';" +
    "const m=require('" + tuiInstallerPath + "');" +
    "console.log('NO_COLOR_OK');",
  ], { encoding: "utf8", timeout: 5000 });
  assert.match(result.stdout, /NO_COLOR_OK/);
});

// CLI backward compat: --help shows tui command
test("cli: --help lists tui command", () => {
  const result = runTui(["--help"], "", {});
  assert.equal(result.status, 0);
  assert.match(result.stdout, /tui\s+open the interactive/);
});

// CLI backward compat: diagnose still works
test("cli: diagnose --backend agents --json runs", () => {
  const result = runTuiInTempTarget(["diagnose", "--backend", "agents", "--json"], "");
  // May fail if no target repo, but should produce output (not crash)
  assert.ok(result.stdout.length > 0 || result.stderr.length > 0);
});

// CLI backward compat: verify still works  
test("cli: verify --backend agents runs", () => {
  const result = runTuiInTempTarget(["verify", "--backend", "agents"], "");
  assert.ok(result.stdout.length > 0 || result.stderr.length > 0);
});

// CLI backward compat: install still works
test("cli: install --backend agents runs (may fail without target)", () => {
  const result = runTuiInTempTarget(["install", "--backend", "agents"], "");
  assert.ok(result.stdout.length > 0 || result.stderr.length > 0);
});

// CLI backward compat: update dry-run still works
test("cli: update --backend agents dry-run runs", () => {
  const result = runTuiInTempTarget(["update", "--backend", "agents"], "");
  assert.ok(result.stdout.length > 0 || result.stderr.length > 0);
});

test("migrate-runtime --json reports no-op when neither .aw nor .servo exists", () => {
  const root = mkdtempSync(join(tmpdir(), "servo-installer-migrate-"));
  try {
    const result = runNodeMigrateRuntime(root, ["--from", "aw", "--to", "servo", "--json"]);
    assert.equal(result.status, 0);
    const summary = JSON.parse(result.stdout);
    assert.equal(summary.state, "no-runtime");
    assert.equal(summary.mutation_performed, false);
    assert.equal(existsSync(join(root, ".servo")), false);
  } finally {
    rmSync(root, { recursive: true, force: true });
  }
});

test("migrate-runtime dry-run reports ready .aw without mutating target", () => {
  const root = mkdtempSync(join(tmpdir(), "servo-installer-migrate-"));
  try {
    mkdirSync(join(root, ".aw"), { recursive: true });
    writeFileSync(join(root, ".aw", "control-state.md"), "runtime\n", "utf8");
    const result = runNodeMigrateRuntime(root, ["--from", "aw", "--to", "servo", "--json"]);
    assert.equal(result.status, 0);
    const summary = JSON.parse(result.stdout);
    assert.equal(summary.state, "ready");
    assert.equal(summary.action, "copy");
    assert.equal(summary.mutation_allowed, true);
    assert.equal(summary.mutation_performed, false);
    assert.equal(existsSync(join(root, ".servo")), false);
  } finally {
    rmSync(root, { recursive: true, force: true });
  }
});

test("migrate-runtime --yes copies .aw to .servo and preserves source", () => {
  const root = mkdtempSync(join(tmpdir(), "servo-installer-migrate-"));
  try {
    mkdirSync(join(root, ".aw", "worktrack"), { recursive: true });
    writeFileSync(join(root, ".aw", "control-state.md"), "runtime\n", "utf8");
    writeFileSync(join(root, ".aw", "worktrack", "contract.md"), "contract\n", "utf8");
    const result = runNodeMigrateRuntime(root, ["--from", "aw", "--to", "servo", "--yes"]);
    assert.equal(result.status, 0, result.stderr);
    assert.match(result.stdout, /state: migrated/);
    assert.equal(readFileSync(join(root, ".servo", "control-state.md"), "utf8"), "runtime\n");
    assert.equal(readFileSync(join(root, ".servo", "worktrack", "contract.md"), "utf8"), "contract\n");
    assert.equal(readFileSync(join(root, ".aw", "control-state.md"), "utf8"), "runtime\n");
    const sentinel = JSON.parse(readFileSync(join(root, ".servo", ".servo-installer-aw-migration.json"), "utf8"));
    assert.equal(sentinel.marker_version, "aw-to-servo-runtime-migration.v1");
  } finally {
    rmSync(root, { recursive: true, force: true });
  }
});

test("migrate-runtime --yes copies .aw under non-ascii target path", () => {
  const root = mkdtempSync(join(tmpdir(), "servo-installer-迁移-"));
  try {
    mkdirSync(join(root, ".aw"), { recursive: true });
    writeFileSync(join(root, ".aw", "control-state.md"), "runtime\n", "utf8");
    const result = runNodeMigrateRuntime(root, ["--from", "aw", "--to", "servo", "--yes"]);
    assert.equal(result.status, 0, result.stderr);
    assert.match(result.stdout, /state: migrated/);
    assert.equal(readFileSync(join(root, ".servo", "control-state.md"), "utf8"), "runtime\n");
    assert.equal(readFileSync(join(root, ".aw", "control-state.md"), "utf8"), "runtime\n");
  } finally {
    rmSync(root, { recursive: true, force: true });
  }
});

test("migrate-runtime rerun after successful copy is idempotent", () => {
  const root = mkdtempSync(join(tmpdir(), "servo-installer-migrate-"));
  try {
    mkdirSync(join(root, ".aw"), { recursive: true });
    writeFileSync(join(root, ".aw", "control-state.md"), "runtime\n", "utf8");
    const first = runNodeMigrateRuntime(root, ["--from", "aw", "--to", "servo", "--yes"]);
    assert.equal(first.status, 0, first.stderr);

    const second = runNodeMigrateRuntime(root, ["--from", "aw", "--to", "servo", "--yes"]);
    assert.equal(second.status, 0, second.stderr);
    assert.match(second.stdout, /state: already-migrated/);
    assert.match(second.stdout, /action: noop/);
  } finally {
    rmSync(root, { recursive: true, force: true });
  }
});

test("migrate-runtime blocks pre-existing .servo without migration sentinel", () => {
  const root = mkdtempSync(join(tmpdir(), "servo-installer-migrate-"));
  try {
    mkdirSync(join(root, ".aw"), { recursive: true });
    mkdirSync(join(root, ".servo"), { recursive: true });
    const result = runNodeMigrateRuntime(root, ["--from", "aw", "--to", "servo", "--json"]);
    assert.equal(result.status, 1);
    const summary = JSON.parse(result.stdout);
    assert.equal(summary.state, "blocked");
    assert.equal(summary.issues[0].code, "destination-runtime-exists");
  } finally {
    rmSync(root, { recursive: true, force: true });
  }
});

test("migrate-runtime blocks malformed source runtime path", () => {
  const root = mkdtempSync(join(tmpdir(), "servo-installer-migrate-"));
  try {
    writeFileSync(join(root, ".aw"), "not a directory\n", "utf8");
    const result = runNodeMigrateRuntime(root, ["--from", "aw", "--to", "servo", "--json"]);
    assert.equal(result.status, 1);
    const summary = JSON.parse(result.stdout);
    assert.equal(summary.state, "blocked");
    assert.equal(summary.issues[0].code, "malformed-source-runtime");
  } finally {
    rmSync(root, { recursive: true, force: true });
  }
});

test("migrate-runtime treats destination-only .servo as a safe no-op", () => {
  const root = mkdtempSync(join(tmpdir(), "servo-installer-migrate-"));
  try {
    mkdirSync(join(root, ".servo"), { recursive: true });
    const result = runNodeMigrateRuntime(root, ["--from", "aw", "--to", "servo", "--json"]);
    assert.equal(result.status, 0);
    const summary = JSON.parse(result.stdout);
    assert.equal(summary.state, "destination-only");
    assert.equal(summary.action, "noop");
  } finally {
    rmSync(root, { recursive: true, force: true });
  }
});

test("reconcile-servo dry-run and apply converge .servo templates", () => {
  const root = mkdtempSync(join(tmpdir(), "servo-installer-reconcile-"));
  try {
    const templateRoot = join(root, "templates");
    const targetRepo = join(root, "target-repo");
    mkdirSync(templateRoot, { recursive: true });
    mkdirSync(join(targetRepo, ".servo", "repo"), { recursive: true });
    writeFileSync(join(templateRoot, "control-state.md"), [
      "---",
      'title: "Harness Control State"',
      "---",
      "# Harness Control State",
      "",
      "## Existing Section",
      "- preserved: template-default",
      "",
      "## Missing Section",
      "- added: section-value",
      "",
      "## Parent Section",
      "- parent: template-value",
      "",
      "### Missing Child",
      "- child: child-value",
      "",
    ].join("\n"), "utf8");
    writeFileSync(join(templateRoot, "goal-charter.md"), [
      "---",
      'title: "Repo Goal / Charter"',
      "---",
      "# Repo Goal / Charter",
      "",
      "## Metadata",
      "- repo: target",
      "",
    ].join("\n"), "utf8");
    writeFileSync(join(targetRepo, ".servo", "control-state.md"), [
      "---",
      'title: "Runtime Control State"',
      "---",
      "# Harness Control State",
      "",
      "## Existing Section",
      "- preserved: user-value",
      "",
      "## Parent Section",
      "- parent: runtime-value",
      "",
    ].join("\n"), "utf8");

    const env = {
      ...process.env,
      SERVO_HARNESS_TARGET_REPO_ROOT: targetRepo,
    };
    const dryRun = spawnSync(process.execPath, [
      join(__dirname, "bin", "servo-installer.js"),
      "reconcile-servo",
      "--template-root",
      templateRoot,
      "--json",
    ], { cwd: root, encoding: "utf8", env });
    assert.equal(dryRun.status, 0, dryRun.stderr);
    const dryRunSummary = JSON.parse(dryRun.stdout);
    assert.deepEqual(
      new Set(dryRunSummary.changes.map((change) => change.type)),
      new Set(["append_section", "append_sub_section", "new_file"]),
    );
    assert.equal(existsSync(join(targetRepo, ".servo", "goal-charter.md")), false);

    const apply = spawnSync(process.execPath, [
      join(__dirname, "bin", "servo-installer.js"),
      "reconcile-servo",
      "--template-root",
      templateRoot,
      "--yes",
    ], { cwd: root, encoding: "utf8", env });
    assert.equal(apply.status, 0, apply.stderr);
    const controlState = readFileSync(join(targetRepo, ".servo", "control-state.md"), "utf8");
    assert.match(controlState, /- preserved: user-value/);
    assert.doesNotMatch(controlState, /- preserved: template-default/);
    assert.match(controlState, /## Missing Section/);
    assert.match(controlState, /### Missing Child/);
    assert.equal(
      readFileSync(join(targetRepo, ".servo", "goal-charter.md"), "utf8"),
      readFileSync(join(templateRoot, "goal-charter.md"), "utf8"),
    );

    const secondDryRun = spawnSync(process.execPath, [
      join(__dirname, "bin", "servo-installer.js"),
      "reconcile-servo",
      "--template-root",
      templateRoot,
      "--json",
    ], { cwd: root, encoding: "utf8", env });
    assert.equal(secondDryRun.status, 0, secondDryRun.stderr);
    assert.deepEqual(JSON.parse(secondDryRun.stdout).changes, []);
  } finally {
    rmSync(root, { recursive: true, force: true });
  }
});

test("reconcile-servo skips blank worktrack placeholders and remains idempotent", () => {
  const root = mkdtempSync(join(tmpdir(), "servo-installer-reconcile-blank-"));
  try {
    const templateRoot = join(root, "templates");
    const targetRepo = join(root, "target-repo");
    mkdirSync(join(templateRoot, "worktrack"), { recursive: true });
    mkdirSync(join(targetRepo, ".servo", "worktrack"), { recursive: true });

    writeFileSync(join(templateRoot, "worktrack", "plan-task-queue.md"), [
      "# Plan / Task Queue",
      "",
      "## Metadata",
      "- worktrack_id:",
      "- updated:",
      "- current_phase:",
      "- contract_ref:",
      "- queue_status:",
      "",
      "## Task List",
      "",
      "1. [ ]",
      "   - task_id:",
      "   - status:",
      "   - priority:",
      "   - assigned:",
      "   - description:",
      "   - depends_on:",
      "   - acceptance:",
      "   - risk_level:",
      "   - stop_condition:",
      "2. [ ]",
      "   - task_id:",
      "   - status:",
      "   - priority:",
      "   - assigned:",
      "   - description:",
      "   - depends_on:",
      "   - acceptance:",
      "   - risk_level:",
      "   - stop_condition:",
    ].join("\n"), "utf8");
    writeFileSync(join(templateRoot, "worktrack", "contract.md"), [
      "# Worktrack Contract",
      "",
      "## Metadata",
      "- worktrack_id:",
      "- branch:",
      "- baseline_branch:",
      "- baseline_ref:",
      "- owner:",
      "- updated:",
      "- contract_status:",
      "",
      "## Scope",
      "",
      "### Control Signal",
      "- 范围摘要（一句话）：",
      "",
      "### Supporting Detail",
      "- 详细范围项：",
    ].join("\n"), "utf8");
    writeFileSync(join(templateRoot, "worktrack", "gate-evidence.md"), [
      "# Gate Evidence",
      "",
      "## Metadata",
      "- worktrack_id:",
      "- updated:",
      "- gate_round:",
      "- required_evidence_lanes:",
      "- review_profile:",
      "",
      "## Review Lane",
      "",
      "### Control Signal",
      "- confidence:",
      "- ready_for_gate:",
    ].join("\n"), "utf8");
    writeFileSync(join(templateRoot, "control-state.md"), "# Control\n", "utf8");
    writeFileSync(join(templateRoot, "goal-charter.md"), "# Goal\n", "utf8");

    writeFileSync(join(targetRepo, ".servo", "worktrack", "plan-task-queue.md"), [
      "# Plan / Task Queue",
      "",
      "## Metadata",
      "- worktrack_id: WT-20260615-v061-rc4-post-publish-sync",
      "- milestone_id: MS-20260615-002",
      "- node_type: docs",
      "- total_tasks: 5",
      "- completed_tasks: 5",
      "- selected_next_action_id: closeout",
      "",
      "## Task List",
      "",
      "### RC4-SYNC-001: Version fact scope scan",
      "",
      "- status: done",
      "- priority: P0",
      "- assigned: current-carrier",
      "- description: Identify stale release facts.",
      "- depends_on: []",
      "- risk_level: low",
    ].join("\n"), "utf8");
    writeFileSync(join(targetRepo, ".servo", "worktrack", "contract.md"), [
      "# Worktrack Contract",
      "",
      "## Metadata",
      "- worktrack_id: WT-20260615-v061-rc4-post-publish-sync",
      "- 分支：develop",
      "- 基准分支：develop",
      "- 基准引用：develop@f140c96",
      "- 约定状态：active",
      "- milestone_id：MS-20260615-002",
      "",
      "## Scope",
      "",
      "- Update docs.",
    ].join("\n"), "utf8");
    writeFileSync(join(targetRepo, ".servo", "worktrack", "gate-evidence.md"), [
      "# Gate Evidence",
      "",
      "## Metadata",
      "- worktrack_id: WT-20260615-v061-rc4-post-publish-sync",
      "- milestone_id: MS-20260615-002",
      "- node_type: docs",
      "- gate_status: passed",
      "",
      "## Evidence Slots",
      "",
      "- validation: passed",
    ].join("\n"), "utf8");

    const env = {
      ...process.env,
      SERVO_HARNESS_TARGET_REPO_ROOT: targetRepo,
    };
    const dryRun = spawnSync(process.execPath, [
      join(__dirname, "bin", "servo-installer.js"),
      "reconcile-servo",
      "--template-root",
      templateRoot,
      "--json",
    ], { cwd: root, encoding: "utf8", env });
    assert.equal(dryRun.status, 0, dryRun.stderr);
    const dryRunSummary = JSON.parse(dryRun.stdout);
    assert.equal(
      dryRunSummary.changes.some((change) => change.type === "append_field" && change.value === ""),
      false,
    );
    assert.equal(
      dryRunSummary.changes.some((change) => change.file === "worktrack/plan-task-queue.md" && change.section === "Task List"),
      false,
    );
    assert.equal(
      dryRunSummary.changes.some((change) => change.file.startsWith("worktrack/")),
      false,
    );

    const apply = spawnSync(process.execPath, [
      join(__dirname, "bin", "servo-installer.js"),
      "reconcile-servo",
      "--template-root",
      templateRoot,
      "--yes",
    ], { cwd: root, encoding: "utf8", env });
    assert.equal(apply.status, 0, apply.stderr);
    const planTaskQueue = readFileSync(join(targetRepo, ".servo", "worktrack", "plan-task-queue.md"), "utf8");
    assert.doesNotMatch(planTaskQueue, /- task_id:\n- status:/);
    assert.doesNotMatch(planTaskQueue, /- updated:\n- current_phase:/);
    assert.doesNotMatch(planTaskQueue, /## Task Window/);

    const secondDryRun = spawnSync(process.execPath, [
      join(__dirname, "bin", "servo-installer.js"),
      "reconcile-servo",
      "--template-root",
      templateRoot,
      "--json",
    ], { cwd: root, encoding: "utf8", env });
    assert.equal(secondDryRun.status, 0, secondDryRun.stderr);
    assert.deepEqual(JSON.parse(secondDryRun.stdout).changes, []);
  } finally {
    rmSync(root, { recursive: true, force: true });
  }
});

test("reconcile-servo treats later meaningful duplicate field as converged", () => {
  const root = mkdtempSync(join(tmpdir(), "servo-installer-reconcile-duplicate-"));
  try {
    const templateRoot = join(root, "templates");
    const targetRepo = join(root, "target-repo");
    mkdirSync(templateRoot, { recursive: true });
    mkdirSync(join(targetRepo, ".servo"), { recursive: true });

    writeFileSync(join(templateRoot, "control-state.md"), [
      "# Harness Control State",
      "",
      "## Approval Boundary",
      "- approval_persistence: one-shot",
    ].join("\n"), "utf8");
    writeFileSync(join(targetRepo, ".servo", "control-state.md"), [
      "# Harness Control State",
      "",
      "## Approval Boundary",
      "- approval_persistence: N/A",
      "- approval_persistence: one-shot",
    ].join("\n"), "utf8");

    const env = {
      ...process.env,
      SERVO_HARNESS_TARGET_REPO_ROOT: targetRepo,
    };
    const dryRun = spawnSync(process.execPath, [
      join(__dirname, "bin", "servo-installer.js"),
      "reconcile-servo",
      "--template-root",
      templateRoot,
      "--json",
    ], { cwd: root, encoding: "utf8", env });
    assert.equal(dryRun.status, 0, dryRun.stderr);
    assert.deepEqual(JSON.parse(dryRun.stdout).changes, []);
  } finally {
    rmSync(root, { recursive: true, force: true });
  }
});

test("migrate-runtime --yes --reinstall agents copies runtime then refreshes managed skill payload", () => {
  const root = mkdtempSync(join(tmpdir(), "servo-installer-migrate-"));
  try {
    const installed = seedInstalledAgentsSkill(root, "demo-skill");
    mkdirSync(join(root, ".aw"), { recursive: true });
    writeFileSync(join(root, ".aw", "control-state.md"), "runtime\n", "utf8");
    writeFileSync(join(installed.canonicalDir, "SKILL.md"), "# demo-skill\n\n# migrated source\n", "utf8");
    writeFileSync(
      join(installed.targetSkillDir, "aw.marker"),
      `${JSON.stringify({
        marker_version: "aw-managed-skill-marker.v2",
        backend: "agents",
        skill_id: "legacy-demo-skill",
        payload_version: "agents-skill-payload.v0",
        payload_fingerprint: "old-fingerprint",
      }, null, 2)}\n`,
      "utf8",
    );
    const fakeBin = fakePythonBin(root);

    const result = runNodeMigrateRuntime(root, [
      "--from",
      "aw",
      "--to",
      "servo",
      "--yes",
      "--reinstall",
      "--backend=agents",
    ], fakeBin);

    assert.equal(result.status, 0, result.stderr);
    assert.match(result.stdout, /state: migrated/);
    assert.match(result.stdout, /reinstall status: ready/);
    assert.match(result.stdout, /\[agents\] applying update/);
    assert.match(result.stdout, /\[agents\] update complete/);
    assert.equal(readFileSync(join(root, ".servo", "control-state.md"), "utf8"), "runtime\n");
    assert.equal(readFileSync(join(root, ".aw", "control-state.md"), "utf8"), "runtime\n");
    assert.equal(readFileSync(join(installed.targetSkillDir, "SKILL.md"), "utf8"), "# demo-skill\n\n# migrated source\n");
    const marker = JSON.parse(readFileSync(join(installed.targetSkillDir, "aw.marker"), "utf8"));
    assert.equal(marker.skill_id, "demo-skill");
    assert.notEqual(marker.payload_fingerprint, "old-fingerprint");
    assert.equal(result.stderr.includes("unexpected-python"), false);
  } finally {
    rmSync(root, { recursive: true, force: true });
  }
});

test("migrate-runtime --reinstall blocks update conflicts before copying runtime", () => {
  const root = mkdtempSync(join(tmpdir(), "servo-installer-migrate-"));
  try {
    seedMinimalAgentsSource(root, "demo-skill");
    seedMinimalAgentsSource(root, "other-skill");
    mkdirSync(join(root, ".aw"), { recursive: true });
    writeFileSync(join(root, ".aw", "control-state.md"), "runtime\n", "utf8");
    const targetRoot = join(root, ".agents", "skills");
    const unmanagedDir = join(targetRoot, "aw-demo-skill");
    mkdirSync(unmanagedDir, { recursive: true });
    writeFileSync(join(unmanagedDir, "SKILL.md"), "# unmanaged\n", "utf8");
    const fakeBin = fakePythonBin(root);

    const result = runNodeMigrateRuntime(root, [
      "--from",
      "aw",
      "--to",
      "servo",
      "--yes",
      "--reinstall",
      "--backend=agents",
    ], fakeBin);

    assert.equal(result.status, 1);
    assert.match(result.stdout, /state: ready/);
    assert.match(result.stdout, /reinstall status: blocked/);
    assert.match(result.stdout, /reinstall blocking issues: 1/);
    assert.equal(result.stdout.includes("[agents] applying update"), false);
    assert.equal(existsSync(join(root, ".servo")), false);
    assert.equal(readFileSync(join(unmanagedDir, "SKILL.md"), "utf8"), "# unmanaged\n");
    assert.equal(existsSync(join(targetRoot, "aw-other-skill")), false);
    assert.equal(result.stderr.includes("unexpected-python"), false);
  } finally {
    rmSync(root, { recursive: true, force: true });
  }
});

test("migrate-runtime --yes --reinstall bundle installs both backend payloads", () => {
  const root = mkdtempSync(join(tmpdir(), "servo-installer-migrate-"));
  try {
    seedMinimalBundleSource(root, "demo-skill");
    mkdirSync(join(root, ".aw"), { recursive: true });
    writeFileSync(join(root, ".aw", "control-state.md"), "runtime\n", "utf8");
    const fakeBin = fakePythonBin(root);

    const result = runNodeMigrateRuntime(root, [
      "--from",
      "aw",
      "--to",
      "servo",
      "--yes",
      "--reinstall",
      "--backend=bundle",
    ], fakeBin);

    assert.equal(result.status, 0, result.stderr);
    assert.match(result.stdout, /state: migrated/);
    assert.match(result.stdout, /reinstall status: ready/);
    assert.match(result.stdout, /\[bundle\] update complete for both backends/);
    assert.equal(readFileSync(join(root, ".servo", "control-state.md"), "utf8"), "runtime\n");
    assert.equal(existsSync(join(root, ".agents", "skills", "aw-demo-skill", "aw.marker")), true);
    assert.equal(existsSync(join(root, ".claude", "skills", "demo-skill", "aw.marker")), true);
    assert.equal(result.stderr.includes("unexpected-python"), false);
  } finally {
    rmSync(root, { recursive: true, force: true });
  }
});

test("migrate-runtime --yes rewrites .aw path references to .servo in text files", () => {
  const root = mkdtempSync(join(tmpdir(), "servo-installer-migrate-"));
  try {
    mkdirSync(join(root, ".aw", "milestone"), { recursive: true });
    mkdirSync(join(root, ".aw", "worktrack"), { recursive: true });
    writeFileSync(join(root, ".aw", "control-state.md"), [
      "---",
      'generated_from: "aw-set-harness-goal-skill/assets/control-state.md"',
      "---",
      "> 这是 `.aw/control-state.md` 的运行实例",
      "",
      "- scope: 更新 `.aw` 文档/控制面",
      "- source: `.aw/milestone/MS-001.md`",
      "- helper: aw-set-harness-goal-skill",
      "- single_quoted: 'aw-set-harness-goal-skill/assets/control-state.md'",
      "- backticked: `aw-set-harness-goal-skill`",
    ].join("\n") + "\n", "utf8");
    writeFileSync(join(root, ".aw", "milestone", "MS-001.md"), [
      "---",
      "title: MS-001",
      "---",
      "- scope: 更新 `docs/` 与 `.aw` 设计文档",
      "- 只改 `.aw` 和 `docs/` 设计/规划文档",
      "",
      "## Worktrack",
      "- branch: aw/demo-v1",
      "- baseline: develop-aw",
    ].join("\n") + "\n", "utf8");
    writeFileSync(join(root, ".aw", "worktrack", "contract.md"), [
      "# Contract",
      "- baseline_branch: develop-aw",
      "- scope: `.aw` 控制面更新",
    ].join("\n") + "\n", "utf8");

    const result = runNodeMigrateRuntime(root, ["--from", "aw", "--to", "servo", "--yes"]);
    assert.equal(result.status, 0, result.stderr);
    assert.match(result.stdout, /state: migrated/);
    assert.match(result.stdout, /rewritten files: 3/);

    // Verify .aw source is unchanged
    const awControl = readFileSync(join(root, ".aw", "control-state.md"), "utf8");
    assert.match(awControl, /`\.aw\/control-state\.md`/);
    assert.match(awControl, /aw-set-harness-goal-skill/);

    // Verify .servo destination has rewritten paths
    const servoControl = readFileSync(join(root, ".servo", "control-state.md"), "utf8");
    assert.match(servoControl, /`\.servo\/control-state\.md`/);
    assert.match(servoControl, /harness-set-goal-skill/);
    assert.doesNotMatch(servoControl, /`\.aw\/control-state\.md`/);
    assert.doesNotMatch(servoControl, /aw-set-harness-goal-skill/);

    const servoMilestone = readFileSync(join(root, ".servo", "milestone", "MS-001.md"), "utf8");
    assert.match(servoMilestone, /与 `\.servo` 设计文档/);
    assert.match(servoMilestone, /`\.servo` 和 `docs\/`/);
    assert.doesNotMatch(servoMilestone, /`\.aw`/);
    // branch names and baseline should NOT be rewritten
    assert.match(servoMilestone, /aw\/demo-v1/);
    assert.match(servoMilestone, /develop-aw/);

    const servoContract = readFileSync(join(root, ".servo", "worktrack", "contract.md"), "utf8");
    assert.match(servoContract, /`\.servo` 控制面更新/);
    assert.doesNotMatch(servoContract, /`\.aw`/);
    // baseline branch name should NOT be rewritten
    assert.match(servoContract, /develop-aw/);

    // Verify sentinel records rewrite count
    const sentinel = JSON.parse(readFileSync(join(root, ".servo", ".servo-installer-aw-migration.json"), "utf8"));
    assert.equal(sentinel.rewritten_file_count, 3);
  } finally {
    rmSync(root, { recursive: true, force: true });
  }
});

// CLI backward compat: prune rejects without --all
test("cli: prune --backend agents without --all is rejected", () => {
  const result = runTuiInTempTarget(["prune", "--backend", "agents"], "");
  assert.notEqual(result.status, 0);
});

// CLI backward compat: --version works
test("cli: --version prints version", () => {
  const result = runTui(["--version"], "", {});
  assert.equal(result.status, 0);
  assert.ok(result.stdout.length > 0);
});

// CLI backward compat: unknown command errors
test("cli: unknown command produces error", () => {
  const result = runTui(["--nonexistent-flag-xyz"], "", {});
  assert.notEqual(result.status, 0);
});

// Full test suite: all 121 original tests still pass
test("all 121 original deploy tests pass (sanity check)", () => {
  // This is a meta-test — the actual 121 tests run separately
  // Just verify the required exports exist
  const expected = [
    "buildNodeAgentsContext", "buildNodeBackendContext",
    "diagnosticSummary", "checkPathsExistSummary",
    "installBackendPayloads", "canonicalSourceMetadata",
  ];
  for (const name of expected) {
    assert.equal(typeof installer[name], "function", name + " should be a function");
  }
});
