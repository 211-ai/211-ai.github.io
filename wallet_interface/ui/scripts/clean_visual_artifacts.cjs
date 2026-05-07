const fs = require("fs");
const path = require("path");

const root = path.resolve(__dirname, "..", "artifacts", "ui-screenshots", "latest");

try {
  fs.rmSync(root, { recursive: true, force: true });
} catch (error) {
  if (error && (error.code === "EACCES" || error.code === "EPERM")) {
    process.stderr.write(
      `Skipping visual artifact cleanup for locked files at ${root}: ${error.code}\n`,
    );
  } else {
    throw error;
  }
}

fs.mkdirSync(root, { recursive: true });
