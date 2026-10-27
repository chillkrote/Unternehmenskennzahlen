// Ohne Apple-Entwicklerkonto: ad-hoc signieren, damit die App auf Apple-Silicon überhaupt startet.
const { execFileSync } = require("child_process");
const path = require("path");

exports.default = async function (ctx) {
  if (ctx.electronPlatformName !== "darwin") return;
  const app = path.join(ctx.appOutDir, `${ctx.packager.appInfo.productFilename}.app`);
  execFileSync("codesign", ["--force", "--deep", "--sign", "-", app], { stdio: "inherit" });
};
