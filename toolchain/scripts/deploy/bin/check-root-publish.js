#!/usr/bin/env node
"use strict";

const { existsSync, readFileSync } = require("node:fs");
const { join } = require("node:path");

const semverPattern =
  /^(0|[1-9]\d*)\.(0|[1-9]\d*)\.(0|[1-9]\d*)(?:-([0-9A-Za-z-]+(?:\.[0-9A-Za-z-]+)*))?(?:\+[0-9A-Za-z-]+(?:\.[0-9A-Za-z-]+)*)?$/;

function deriveReleaseChannelFromTag(tag, packageVersion, packagePrerelease) {
  if (tag !== `v${packageVersion}`) {
    return "";
  }
  if (/(^|\.)canary(\.|$)/.test(packagePrerelease)) {
    return "canary";
  }
  if (/^(alpha|beta|rc)(\.|$)/.test(packagePrerelease)) {
    return "next";
  }
  if (!packagePrerelease) {
    return "latest";
  }
  return "";
}

function fail(message) {
  throw new Error(message);
}

function runChecks(checks) {
  for (const check of checks) {
    if (!check.test()) {
      fail(check.message());
    }
  }
}

function readPackageMetadata(packagePath) {
  return JSON.parse(readFileSync(packagePath, "utf8"));
}

function rootFilesCoverScaffoldFiles(rootFiles, scaffoldFiles) {
  return scaffoldFiles.every((scaffoldFile) => {
    const mappedFile = `toolchain/scripts/deploy/${scaffoldFile}`;
    return rootFiles.some((rootFile) => {
      const normalizedRootFile = rootFile.replace(/\/$/, "");
      return mappedFile === normalizedRootFile || mappedFile.startsWith(`${normalizedRootFile}/`);
    });
  });
}

function main() {
  const packagePath = join(__dirname, "..", "..", "..", "..", "package.json");
  const scaffoldPackagePath = join(__dirname, "..", "package.json");
  const packageMetadata = readPackageMetadata(packagePath);
  const scaffoldPackageMetadata = existsSync(scaffoldPackagePath)
    ? readPackageMetadata(scaffoldPackagePath)
    : null;
  const packageJsonOverride = process.env.SERVO_INSTALLER_PACKAGE_JSON || "";
  const version = packageMetadata.version || "";
  const isDryRun = process.env.npm_config_dry_run === "true";
  const isLocalVersion = version === "0.0.0-local" || version.includes("-local");
  const prerelease = (version.match(semverPattern) || [])[4] || "";
  const releaseTag = process.env.SERVO_INSTALLER_RELEASE_GIT_TAG || "";
  const envReleaseChannel = process.env.SERVO_INSTALLER_RELEASE_CHANNEL || "";
  const derivedReleaseChannel = deriveReleaseChannelFromTag(releaseTag, version, prerelease);
  const releaseChannel = derivedReleaseChannel || envReleaseChannel;
  const npmDistTag = process.env.npm_config_tag || "latest";
  const publishApproved = process.env.SERVO_INSTALLER_PUBLISH_APPROVED === "1";
  const isCiRelease = process.env.CI === "true";
  const releaseApprovalMetadata = packageMetadata.servoInstallerRelease || {};
  const metadataPublishApproval = releaseApprovalMetadata.realPublishApproval || "";
  const metadataApprovedVersion = releaseApprovalMetadata.approvedVersion || "";
  const metadataApprovedGitTag = releaseApprovalMetadata.approvedGitTag || "";
  const metadataApprovedChannel = releaseApprovalMetadata.approvedChannel || "";

  runChecks([
    {
      test: () => packageMetadata.name === "servo-installer",
      message: () => `refusing to publish unexpected package ${packageMetadata.name || "<missing-name>"}`,
    },
    {
      test: () => !packageJsonOverride,
      message: () =>
        "refusing to publish servo-installer; SERVO_INSTALLER_PACKAGE_JSON override is not supported",
    },
    {
      test: () =>
        scaffoldPackageMetadata === null || scaffoldPackageMetadata.version === packageMetadata.version,
      message: () =>
        `refusing to publish servo-installer; root package version ${packageMetadata.version || "<missing-version>"} does not match local scaffold package version ${scaffoldPackageMetadata.version || "<missing-version>"}`,
    },
    {
      test: () =>
        scaffoldPackageMetadata === null ||
        rootFilesCoverScaffoldFiles(packageMetadata.files || [], scaffoldPackageMetadata.files || []),
      message: () =>
        "refusing to publish servo-installer; root package files must cover every local scaffold package file under toolchain/scripts/deploy/",
    },
  ]);

  if (isDryRun) {
    return 0;
  }

  runChecks([
    {
      test: () => !isLocalVersion,
      message: () =>
        `refusing to publish servo-installer ${version}; choose an approved non-local version first`,
    },
    {
      test: () => semverPattern.test(version),
      message: () => `refusing to publish servo-installer ${version}; version must be valid semver`,
    },
    {
      test: () => publishApproved,
      message: () =>
        "refusing to publish servo-installer; set SERVO_INSTALLER_PUBLISH_APPROVED=1 after release approval",
    },
    {
      test: () => metadataPublishApproval === "approved",
      message: () =>
        "refusing to publish servo-installer; package metadata realPublishApproval must be approved by the explicit publish worktrack",
    },
    {
      test: () => metadataApprovedVersion === version,
      message: () =>
        `refusing to publish servo-installer; package metadata approvedVersion ${metadataApprovedVersion || "<missing-version>"} must match ${version}`,
    },
    {
      test: () => metadataApprovedGitTag === releaseTag,
      message: () =>
        `refusing to publish servo-installer; package metadata approvedGitTag ${metadataApprovedGitTag || "<missing-tag>"} must match ${releaseTag || "<missing-tag>"}`,
    },
    {
      test: () => metadataApprovedChannel === releaseChannel,
      message: () =>
        `refusing to publish servo-installer; package metadata approvedChannel ${metadataApprovedChannel || "<missing-channel>"} must match ${releaseChannel || "<missing-channel>"}`,
    },
    {
      test: () => isCiRelease,
      message: () => "refusing to publish servo-installer; real publish must run from a CI release context",
    },
    {
      test: () => ["latest", "next", "canary"].includes(releaseChannel),
      message: () =>
        "refusing to publish servo-installer; release channel must derive from SERVO_INSTALLER_RELEASE_GIT_TAG or use SERVO_INSTALLER_RELEASE_CHANNEL latest, next, or canary",
    },
    {
      test: () => npmDistTag === releaseChannel,
      message: () =>
        `refusing to publish servo-installer; npm dist-tag ${npmDistTag} does not match release channel ${releaseChannel}`,
    },
    {
      test: () => releaseChannel !== "latest" || !prerelease,
      message: () => "refusing to publish servo-installer latest; latest releases must not use prerelease versions",
    },
    {
      test: () => releaseChannel !== "next" || /^(alpha|beta|rc)(\.|$)/.test(prerelease),
      message: () =>
        "refusing to publish servo-installer next; next releases must use alpha, beta, or rc prerelease versions",
    },
    {
      test: () => releaseChannel !== "canary" || /(^|\.)canary(\.|$)/.test(prerelease),
      message: () =>
        "refusing to publish servo-installer canary; canary releases must include a canary prerelease segment",
    },
    {
      test: () => releaseTag === `v${version}`,
      message: () => `refusing to publish servo-installer; SERVO_INSTALLER_RELEASE_GIT_TAG must be v${version}`,
    },
  ]);

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
  deriveReleaseChannelFromTag,
  fail,
  main,
  rootFilesCoverScaffoldFiles,
  runChecks,
  semverPattern,
};
