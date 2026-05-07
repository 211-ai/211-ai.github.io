#!/usr/bin/env node

const { spawnSync } = require("node:child_process");

const args = process.argv.slice(2).filter((arg) => arg !== "--runInBand");
const result = spawnSync("playwright", ["test", ...args], {
  stdio: "inherit",
  shell: process.platform === "win32",
});

process.exit(result.status ?? 1);
