#!/usr/bin/env node
"use strict";

const fs = require("node:fs");
const os = require("node:os");
const path = require("node:path");
const { spawnSync } = require("node:child_process");

const USAGE = `usage: servo_installer_registry_npx_smoke.js [--output-dir DIR] [--skip-remote] [--package SELECTOR]

Runs the published registry servo-installer package through npx against multiple
isolated temporary target workdirs, and writes per-target feedback logs.

Defaults:
  --package servo-installer

Default targets:
  - empty-local temporary git repo
  - temporary clone of https://github.com/OceanEyeFF/T1.AI
  - temporary clone of https://github.com/OceanEyeFF/novel-agents

Use --skip-remote to run only generated local temporary targets.
`;

function commandName(name) {
  if (process.platform !== "win32") {
    return name;
  }
  if (name === "npm" || name === "npx") {
    return `${name}.cmd`;
  }
  return name;
}

function parseArgs(argv) {
  const args = {
    outputDir: "",
    skipRemote: false,
    packageSelector: "servo-installer",
  };
  for (let index = 0; index < argv.length; ) {
    const arg = argv[index];
    if (arg === "--output-dir") {
      args.outputDir = argv[index + 1] || "";
      if (!args.outputDir) {
        throw new Error("--output-dir requires a value");
      }
      index += 2;
    } else if (arg === "--skip-remote") {
      args.skipRemote = true;
      index += 1;
    } else if (arg === "--package") {
      args.packageSelector = argv[index + 1] || "";
      if (!args.packageSelector) {
        throw new Error("--package requires a value");
      }
      index += 2;
    } else if (arg === "-h" || arg === "--help") {
      process.stdout.write(USAGE);
      process.exit(0);
    } else {
      throw new Error(`unknown argument: ${arg}`);
    }
  }
  return args;
}

function ensureDir(dirPath) {
  fs.mkdirSync(dirPath, { recursive: true });
}

function writeFile(filePath, content) {
  ensureDir(path.dirname(filePath));
  fs.writeFileSync(filePath, content, "utf8");
}

function appendFile(filePath, content) {
  ensureDir(path.dirname(filePath));
  fs.appendFileSync(filePath, content, "utf8");
}

function run(command, args, options = {}) {
  const result = spawnSync(commandName(command), args, {
    cwd: options.cwd || process.cwd(),
    env: options.env || process.env,
    encoding: "utf8",
    maxBuffer: 20 * 1024 * 1024,
    shell: false,
  });
  if (result.error) {
    throw result.error;
  }
  return {
    status: result.status === null ? 1 : result.status,
    stdout: result.stdout || "",
    stderr: result.stderr || "",
  };
}

function runRequired(command, args, options = {}) {
  const result = run(command, args, options);
  if (result.status !== 0) {
    const rendered = [command, ...args].join(" ");
    throw new Error(`command failed (${result.status}): ${rendered}\n${result.stderr}`);
  }
  return result;
}

function quoteArg(value) {
  if (/^[A-Za-z0-9_@%+=:,./\\-]+$/.test(value)) {
    return value;
  }
  return JSON.stringify(value);
}

function isInside(child, parent) {
  const relative = path.relative(path.resolve(parent), path.resolve(child));
  return relative === "" || (!relative.startsWith("..") && !path.isAbsolute(relative));
}

function fail(message) {
  throw new Error(message);
}

function validateTarget(repoRoot, targetRepo, beforePath, dryRunPath, afterPath) {
  const before = JSON.parse(fs.readFileSync(beforePath, "utf8"));
  const dryRun = JSON.parse(fs.readFileSync(dryRunPath, "utf8"));
  const after = JSON.parse(fs.readFileSync(afterPath, "utf8"));
  const expectedBindingCount = before.binding_count;

  if (!Number.isInteger(expectedBindingCount) || expectedBindingCount <= 0) {
    fail(`diagnose before must report a positive binding_count, got ${expectedBindingCount}`);
  }
  if (before.target_root_exists !== false || before.target_root_status !== "missing") {
    fail(`diagnose before must prove missing target root, got exists=${before.target_root_exists} status=${before.target_root_status}`);
  }
  if (!Array.isArray(before.issue_codes) || !before.issue_codes.includes("missing-target-root")) {
    fail(`diagnose before must include missing-target-root, got ${JSON.stringify(before.issue_codes)}`);
  }
  if (dryRun.blocking_issue_count !== 0) {
    fail(`update dry-run must not block on missing target root, got blocking_issue_count=${dryRun.blocking_issue_count}`);
  }
  const dryRunIssueCodes = Array.isArray(dryRun.issue_codes)
    ? dryRun.issue_codes
    : Array.isArray(dryRun.issues)
      ? dryRun.issues.map((issue) => issue.code)
      : [];
  if (!dryRunIssueCodes.includes("missing-target-root")) {
    fail(`update dry-run must carry missing-target-root as a non-blocking issue, got ${JSON.stringify(dryRunIssueCodes)}`);
  }
  if (Number.isInteger(after.binding_count) && after.binding_count !== expectedBindingCount) {
    fail(`expected final binding_count ${expectedBindingCount}, got ${after.binding_count}`);
  }
  if (after.managed_install_count !== expectedBindingCount) {
    fail(`expected ${expectedBindingCount} managed installs after install/update, got ${after.managed_install_count}`);
  }
  if (after.conflict_count !== 0 || after.unrecognized_count !== 0) {
    fail(`expected no conflicts/unrecognized entries after install/update, got conflicts=${after.conflict_count} unrecognized=${after.unrecognized_count}`);
  }
  if (!isInside(after.target_root, targetRepo)) {
    fail(`target_root ${after.target_root} is not inside target repo ${targetRepo}`);
  }
  if (isInside(after.source_root, repoRoot)) {
    fail(`source_root ${after.source_root} unexpectedly resolved inside source checkout ${repoRoot}`);
  }
  if (isInside(after.source_root, targetRepo)) {
    fail(`source_root ${after.source_root} unexpectedly resolved inside target repo ${targetRepo}`);
  }
  if (path.resolve(after.source_root) === path.resolve(after.target_root)) {
    fail(`source_root ${after.source_root} unexpectedly equals target_root ${after.target_root}`);
  }
  if (!Array.isArray(dryRun.planned_target_paths) || dryRun.planned_target_paths.length !== expectedBindingCount) {
    fail(`expected ${expectedBindingCount} dry-run planned target paths, got ${dryRun.planned_target_paths && dryRun.planned_target_paths.length}`);
  }
  for (const targetPath of dryRun.planned_target_paths) {
    if (!isInside(targetPath, targetRepo)) {
      fail(`planned target path ${targetPath} is not inside target repo ${targetRepo}`);
    }
  }
  if (!before.source_root || !after.source_root) {
    fail("diagnose output must include source_root before and after install");
  }
}

function writeExistingWorkFixture(targetRepo) {
  writeFile(path.join(targetRepo, "README.md"), "# Existing Work Fixture\n\nThis file must survive servo-installer install/update.\n");
  writeFile(
    path.join(targetRepo, "package.json"),
    JSON.stringify({ name: "existing-work-fixture", private: true, scripts: { test: "node -e \"process.exit(0)\"" } }, null, 2) + "\n",
  );
  writeFile(path.join(targetRepo, "src", "index.js"), "console.log('existing project file');\n");
}

function snapshotExistingWork(targetRepo) {
  const files = ["README.md", "package.json", path.join("src", "index.js")];
  const snapshot = {};
  for (const file of files) {
    const filePath = path.join(targetRepo, file);
    if (fs.existsSync(filePath)) {
      snapshot[file] = fs.readFileSync(filePath, "utf8");
    }
  }
  return snapshot;
}

function validateExistingWorkPreserved(targetRepo, beforeSnapshot) {
  for (const [file, expectedContent] of Object.entries(beforeSnapshot)) {
    const filePath = path.join(targetRepo, file);
    if (!fs.existsSync(filePath)) {
      fail(`existing project file was removed: ${filePath}`);
    }
    const actualContent = fs.readFileSync(filePath, "utf8");
    if (actualContent !== expectedContent) {
      fail(`existing project file changed unexpectedly: ${filePath}`);
    }
  }
}

function makeNpmEnv(npmStateRoot) {
  return {
    ...process.env,
    HOME: path.join(npmStateRoot, "home"),
    USERPROFILE: path.join(npmStateRoot, "home"),
    NPM_CONFIG_CACHE: path.join(npmStateRoot, "cache"),
    NPM_CONFIG_TMP: path.join(npmStateRoot, "tmp"),
    NPM_CONFIG_USERCONFIG: path.join(npmStateRoot, "npmrc"),
    AW_HARNESS_REPO_ROOT: "",
    AW_HARNESS_TARGET_REPO_ROOT: "",
  };
}

function runAwCapture(context, targetRepo, targetEvidence, stepName, expectedStatus, awArgs) {
  const stdoutFile = path.join(targetEvidence, `${stepName}.out`);
  const stderrFile = path.join(targetEvidence, `${stepName}.err`);
  const statusFile = path.join(targetEvidence, `${stepName}.status`);
  const feedbackLog = path.join(targetEvidence, "servo-installer-npx-run.log");
  const npxArgs = ["--yes", "--package", context.packageSelector, "--", "servo-installer", ...awArgs];

  appendFile(
    feedbackLog,
    `\n## step=${stepName}\n` +
      `timestamp_utc=${new Date().toISOString().replace(/\.\d{3}Z$/, "Z")}\n` +
      `target_repo=${targetRepo}\n` +
      `package_selector=${context.packageSelector}\n` +
      `command=npx ${npxArgs.map(quoteArg).join(" ")}\n` +
      "--- stdout ---\n",
  );

  const result = run("npx", npxArgs, {
    cwd: targetRepo,
    env: makeNpmEnv(context.npmStateRoot),
  });

  writeFile(stdoutFile, result.stdout);
  writeFile(stderrFile, result.stderr);
  appendFile(
    feedbackLog,
    result.stdout +
      "--- stderr ---\n" +
      result.stderr +
      "--- stderr file ---\n" +
      `${stderrFile}\n` +
      "--- exit status ---\n" +
      `${result.status}\n`,
  );
  writeFile(statusFile, `${result.status}\n`);

  if (result.status !== expectedStatus) {
    throw new Error(
      `expected ${stepName} to exit ${expectedStatus} for target ${targetRepo}, got ${result.status}\n` +
        `stdout: ${stdoutFile}\n` +
        `stderr: ${stderrFile}\n` +
        `feedback_log: ${feedbackLog}`,
    );
  }
}

function main() {
  const args = parseArgs(process.argv.slice(2));
  const repoRoot = runRequired("git", ["rev-parse", "--show-toplevel"]).stdout.trim();
  const outputDir = args.outputDir
    ? path.resolve(args.outputDir)
    : fs.mkdtempSync(path.join(os.tmpdir(), "servo-installer-registry-npx-smoke-"));

  const targetsRoot = path.join(outputDir, "targets");
  const evidenceRoot = path.join(outputDir, "evidence");
  const npmStateRoot = path.join(outputDir, "npm-state");
  ensureDir(targetsRoot);
  ensureDir(evidenceRoot);
  ensureDir(path.join(npmStateRoot, "cache"));
  ensureDir(path.join(npmStateRoot, "tmp"));
  ensureDir(path.join(npmStateRoot, "home"));
  writeFile(path.join(npmStateRoot, "npmrc"), "audit=false\nfund=false\nupdate-notifier=false\n");

  const nodeVersion = process.version;
  const npmVersion = runRequired("npm", ["--version"]).stdout.trim();
  const gitBranch = runRequired("git", ["-C", repoRoot, "rev-parse", "--abbrev-ref", "HEAD"]).stdout.trim();
  const gitCommit = runRequired("git", ["-C", repoRoot, "rev-parse", "HEAD"]).stdout.trim();
  const registryVersion = runRequired("npm", ["view", args.packageSelector, "version"], {
    env: makeNpmEnv(npmStateRoot),
  });
  const registryDistTags = runRequired("npm", ["dist-tag", "ls", "servo-installer"], {
    env: makeNpmEnv(npmStateRoot),
  });

  writeFile(path.join(outputDir, "node.version"), `${nodeVersion}\n`);
  writeFile(path.join(outputDir, "npm.version"), `${npmVersion}\n`);
  writeFile(path.join(outputDir, "git.branch"), `${gitBranch}\n`);
  writeFile(path.join(outputDir, "git.commit"), `${gitCommit}\n`);
  writeFile(path.join(outputDir, "npm-view-version.out"), registryVersion.stdout);
  writeFile(path.join(outputDir, "npm-view-version.err"), registryVersion.stderr);
  writeFile(path.join(outputDir, "npm-dist-tags.out"), registryDistTags.stdout);
  writeFile(path.join(outputDir, "npm-dist-tags.err"), registryDistTags.stderr);

  const targetSpecs = [["empty-local", "empty"], ["existing-work-local", "existing-work"]];
  if (args.skipRemote) {
    targetSpecs.push(["empty-beta", "empty"]);
  } else {
    targetSpecs.push(
      ["t1-ai", "https://github.com/OceanEyeFF/T1.AI.git"],
      ["novel-agents", "https://github.com/OceanEyeFF/novel-agents.git"],
    );
  }

  const context = {
    packageSelector: args.packageSelector,
    npmStateRoot,
  };
  const summary = [];

  for (const [targetName, targetSource] of targetSpecs) {
    const targetRepo = path.join(targetsRoot, targetName);
    const targetEvidence = path.join(evidenceRoot, targetName);
    const feedbackLog = path.join(targetEvidence, "servo-installer-npx-run.log");
    const targetUrl = targetSource.startsWith("https://") ? targetSource : "";
    const targetShape = targetUrl ? "remote-existing-work" : targetSource;
    ensureDir(targetEvidence);
    writeFile(
      feedbackLog,
      "# servo-installer npx run log\n\n" +
        `target_alias=${targetName}\n` +
        `target_source=${targetUrl || targetShape}\n` +
        `target_shape=${targetShape}\n` +
        `package_selector=${args.packageSelector}\n` +
        `node_version=${nodeVersion}\n` +
        `npm_version=${npmVersion}\n` +
        `registry_version=${registryVersion.stdout.trim()}\n` +
        "registry_dist_tags_begin\n" +
        registryDistTags.stdout +
        "registry_dist_tags_end\n",
    );

    if (targetUrl) {
      const clone = run("git", ["clone", "--depth", "1", targetUrl, targetRepo]);
      writeFile(path.join(targetEvidence, "clone.out"), clone.stdout);
      writeFile(path.join(targetEvidence, "clone.err"), clone.stderr);
      if (clone.status !== 0) {
        throw new Error(`git clone failed for ${targetUrl}: ${clone.stderr}`);
      }
      const guard = run("git", ["-C", targetRepo, "remote", "set-url", "--push", "origin", "DISABLED_BY_AW_TEMP_SMOKE_NO_PUSH"]);
      writeFile(path.join(targetEvidence, "remote-push-guard.out"), guard.stdout);
      writeFile(path.join(targetEvidence, "remote-push-guard.err"), guard.stderr);
      if (guard.status !== 0) {
        throw new Error(`failed to disable push URL for ${targetRepo}: ${guard.stderr}`);
      }
      const remotes = runRequired("git", ["-C", targetRepo, "remote", "-v"]);
      writeFile(path.join(targetEvidence, "remotes.after-guard.out"), remotes.stdout);
    } else {
      ensureDir(targetRepo);
      if (targetShape === "existing-work") {
        writeExistingWorkFixture(targetRepo);
      }
      const init = run("git", ["-C", targetRepo, "init"]);
      writeFile(path.join(targetEvidence, "git-init.out"), init.stdout);
      writeFile(path.join(targetEvidence, "git-init.err"), init.stderr);
      if (init.status !== 0) {
        throw new Error(`git init failed for ${targetRepo}: ${init.stderr}`);
      }
    }

    const existingWorkBefore = targetShape === "existing-work" ? snapshotExistingWork(targetRepo) : {};

    runAwCapture(context, targetRepo, targetEvidence, "help", 0, ["--help"]);
    runAwCapture(context, targetRepo, targetEvidence, "version", 0, ["--version"]);
    runAwCapture(context, targetRepo, targetEvidence, "tui", 1, ["tui"]);
    if (fs.readFileSync(path.join(targetEvidence, "tui.out"), "utf8").length !== 0) {
      throw new Error(`expected tui stdout to be empty for ${targetName}`);
    }
    const tuiErr = fs.readFileSync(path.join(targetEvidence, "tui.err"), "utf8");
    if (!tuiErr.includes("servo-installer tui requires an interactive terminal")) {
      throw new Error(`expected tui guard message for ${targetName}`);
    }
    writeFile(path.join(targetEvidence, "tui.guard"), "servo-installer tui requires an interactive terminal\n");

    runAwCapture(context, targetRepo, targetEvidence, "diagnose.before", 0, ["diagnose", "--backend", "agents", "--json"]);
    fs.copyFileSync(path.join(targetEvidence, "diagnose.before.out"), path.join(targetEvidence, "diagnose.before.json"));
    runAwCapture(context, targetRepo, targetEvidence, "update.dry-run", 0, ["update", "--backend", "agents", "--json"]);
    fs.copyFileSync(path.join(targetEvidence, "update.dry-run.out"), path.join(targetEvidence, "update.dry-run.json"));
    runAwCapture(context, targetRepo, targetEvidence, "install", 0, ["install", "--backend", "agents"]);
    runAwCapture(context, targetRepo, targetEvidence, "verify", 0, ["verify", "--backend", "agents"]);
    runAwCapture(context, targetRepo, targetEvidence, "update.apply", 0, ["update", "--backend", "agents", "--yes"]);
    runAwCapture(context, targetRepo, targetEvidence, "diagnose.after", 0, ["diagnose", "--backend", "agents", "--json"]);
    fs.copyFileSync(path.join(targetEvidence, "diagnose.after.out"), path.join(targetEvidence, "diagnose.after.json"));

    validateTarget(
      repoRoot,
      targetRepo,
      path.join(targetEvidence, "diagnose.before.json"),
      path.join(targetEvidence, "update.dry-run.json"),
      path.join(targetEvidence, "diagnose.after.json"),
    );
    validateExistingWorkPreserved(targetRepo, existingWorkBefore);

    summary.push({
      targetName,
      targetUrl: targetUrl || targetShape,
      targetShape,
      targetRepo,
      result: "passed",
      feedbackLog,
    });
  }

  const summaryTsv =
    "target\turl\ttarget_repo\tresult\tfeedback_log\n" +
    summary.map((row) => `${row.targetName}\t${row.targetUrl}\t${row.targetRepo}\t${row.result}\t${row.feedbackLog}`).join("\n") +
    "\n";
  writeFile(path.join(outputDir, "summary.tsv"), summaryTsv);

  const reportLines = [
    "# servo-installer Registry npx Smoke Report",
    "",
    "## Candidate",
    "",
    `- package selector: ${args.packageSelector}`,
    `- registry version: ${registryVersion.stdout.trim()}`,
    "- registry dist-tags:",
    ...registryDistTags.stdout.trim().split(/\r?\n/).filter(Boolean).map((line) => `  - ${line}`),
    `- local git branch: ${gitBranch}`,
    `- local git commit: ${gitCommit}`,
    `- node version: ${nodeVersion}`,
    `- npm version: ${npmVersion}`,
    `- platform: ${process.platform}`,
    `- evidence dir: ${outputDir}`,
    `- npm state dir: ${npmStateRoot}`,
    `- skip remote: ${args.skipRemote}`,
    "",
    "## Target Summary",
    "",
    "| Target | Source | Shape | Target repo | Result | Feedback log |",
    "| --- | --- | --- | --- | --- | --- |",
    ...summary.map((row) => `| ${row.targetName} | ${row.targetUrl} | ${row.targetShape} | ${row.targetRepo} | ${row.result} | ${row.feedbackLog} |`),
    "",
    "## Verdict",
    "",
    "- result: passed",
    `- target_count: ${summary.length}`,
    "- source_root_checkout_leakage: not observed",
    "- source_root_target_repo_leakage: not observed",
    "- target_root_cross_workdir_leakage: not observed",
    "- missing_target_root_handling: diagnose reports missing-target-root before install; update dry-run treats it as non-blocking",
    "- existing_work_preserved: local existing-work fixture files unchanged after install/update",
    "- remote_mutation: not performed",
    "- remote_push_guard: remote clone push URLs set to DISABLED_BY_AW_TEMP_SMOKE_NO_PUSH",
    "- npm_publish_required: false",
    "- feedback_log_artifacts: per-target servo-installer-npx-run.log",
    "",
  ];
  writeFile(path.join(outputDir, "report.md"), reportLines.join("\n"));

  process.stdout.write(`package_selector=${args.packageSelector}\n`);
  process.stdout.write(`evidence_dir=${outputDir}\n`);
  process.stdout.write(`report=${path.join(outputDir, "report.md")}\n`);
}

try {
  main();
} catch (error) {
  process.stderr.write(`${error && error.stack ? error.stack : error}\n`);
  process.stderr.write(USAGE);
  process.exit(1);
}
