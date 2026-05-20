#!/usr/bin/env node
"use strict";

const { appendFileSync, readFileSync } = require("node:fs");
const { join } = require("node:path");

const { deriveReleaseChannelFromTag, semverPattern } = require("./check-root-publish.js");

function isGithubReleasePrerelease(value) {
  return (
    value === true ||
    (typeof value === "string" && value.trim().toLowerCase() === "true")
  );
}

function deriveReleaseMetadata({ version, releaseTag, releasePrerelease, releaseBody }) {
  const match = (version || "").match(semverPattern);
  if (!match) {
    throw new Error(`package version ${version || "<missing>"} is not valid semver`);
  }

  if (releaseTag !== `v${version}`) {
    throw new Error(`release tag ${releaseTag || "<missing>"} must match package version v${version}`);
  }

  const prerelease = match[4] || "";
  const channel = deriveReleaseChannelFromTag(releaseTag, version, prerelease);
  if (!channel) {
    throw new Error(
      `package prerelease segment ${prerelease || "<none>"} does not map to a release channel`,
    );
  }

  const isGithubPrerelease = isGithubReleasePrerelease(releasePrerelease);
  if (isGithubPrerelease && channel === "latest") {
    throw new Error("GitHub prerelease releases cannot publish to latest");
  }
  if (!isGithubPrerelease && channel !== "latest") {
    throw new Error(`GitHub stable releases cannot publish prerelease channel ${channel}`);
  }

  const approvalMarker = `servo-installer-publish-approved: ${releaseTag}`;
  if (!(releaseBody || "").includes(approvalMarker)) {
    throw new Error(`release body must include explicit approval marker: ${approvalMarker}`);
  }

  return {
    releaseTag,
    releaseChannel: channel,
    npmConfigTag: channel,
    packageVersion: version,
    approvalMarker,
  };
}

function readPackageMetadata(packagePath) {
  return JSON.parse(readFileSync(packagePath, "utf8"));
}

function writeGithubEnv(githubEnvPath, metadata) {
  appendFileSync(githubEnvPath, formatGithubEnv(metadata));
}

function formatGithubEnv(metadata) {
  return [
    `SERVO_INSTALLER_RELEASE_GIT_TAG=${metadata.releaseTag}`,
    `SERVO_INSTALLER_RELEASE_CHANNEL=${metadata.releaseChannel}`,
    `NPM_CONFIG_TAG=${metadata.npmConfigTag}`,
    "",
  ].join("\n");
}

function main() {
  const packagePath = join(__dirname, "..", "..", "..", "..", "package.json");
  const packageMetadata = readPackageMetadata(packagePath);
  const metadata = deriveReleaseMetadata({
    version: packageMetadata.version || "",
    releaseTag: process.env.GITHUB_RELEASE_TAG || "",
    releasePrerelease: process.env.GITHUB_RELEASE_PRERELEASE || "",
    releaseBody: process.env.GITHUB_RELEASE_BODY || "",
  });

  if (process.env.GITHUB_ENV) {
    writeGithubEnv(process.env.GITHUB_ENV, metadata);
  }

  console.log(
    `resolved servo-installer release ${metadata.releaseTag} -> npm dist-tag ${metadata.releaseChannel}`,
  );
  return 0;
}

if (require.main === module) {
  try {
    process.exit(main());
  } catch (error) {
    console.error(error.message || String(error));
    process.exit(1);
  }
}

module.exports = {
  deriveReleaseMetadata,
  formatGithubEnv,
  isGithubReleasePrerelease,
  writeGithubEnv,
};
