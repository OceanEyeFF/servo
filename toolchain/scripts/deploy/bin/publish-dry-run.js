#!/usr/bin/env node
"use strict";

const { spawnSync } = require("node:child_process");

const allowedReleaseChannels = new Set(["latest", "next", "canary"]);

function resolveReleaseChannel(env = process.env) {
  const releaseChannel = env.SERVO_INSTALLER_RELEASE_CHANNEL || env.npm_config_tag || "next";
  if (!allowedReleaseChannels.has(releaseChannel)) {
    throw new Error(
      `unsupported servo-installer release channel: ${releaseChannel}; expected latest, next, or canary`,
    );
  }
  return releaseChannel;
}

function main() {
  let releaseChannel;
  try {
    releaseChannel = resolveReleaseChannel();
  } catch (error) {
    console.error(error.message);
    return 1;
  }

  const npmCommand = process.platform === "win32" ? "npm.cmd" : "npm";
  const completed = spawnSync(
    npmCommand,
    ["publish", "--dry-run", "--json", "--tag", releaseChannel],
    {
      cwd: process.cwd(),
      env: process.env,
      shell: false,
      stdio: "inherit",
    },
  );

  if (completed.error) {
    console.error(completed.error.message);
    return 1;
  }

  if (completed.status === null) {
    console.error(
      `npm publish --dry-run terminated by signal ${completed.signal || "<unknown>"}`,
    );
    return 1;
  }
  return completed.status;
}

if (require.main === module) {
  process.exit(main());
}

module.exports = {
  main,
  resolveReleaseChannel,
};
