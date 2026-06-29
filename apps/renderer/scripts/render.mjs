#!/usr/bin/env node
/**
 * Programmatic render — reads config/example.json (or --config path arg),
 * bundles the Remotion project, and renders to dist/.
 *
 * Usage:
 *   node scripts/render.mjs
 *   node scripts/render.mjs --config config/my-channel.json
 *   node scripts/render.mjs --template split-screen
 *
 * Template resolution order: --template flag > config.templateId > "split-screen".
 * The chosen id is both the Remotion composition id and injected into inputProps.
 */

import { bundle } from "@remotion/bundler";
import { renderMedia, selectComposition } from "@remotion/renderer";
import { readFile } from "fs/promises";
import { fileURLToPath } from "url";
import path from "path";

const __dirname = path.dirname(fileURLToPath(import.meta.url));
const root = path.resolve(__dirname, "..");

function flag(name) {
  const i = process.argv.indexOf(name);
  return i !== -1 ? process.argv[i + 1] : undefined;
}

const configPath = flag("--config")
  ? path.resolve(flag("--config"))
  : path.join(root, "config", "example.json");

const channelData = JSON.parse(await readFile(configPath, "utf-8"));

// Template id: CLI flag wins, then config, then default.
const templateId = flag("--template") ?? channelData.templateId ?? "split-screen";
const inputProps = { ...channelData, templateId };

const outputPath = path.join(
  root,
  channelData.outputPath ?? "dist/channel-template.mp4"
);

console.log("Bundling Remotion project…");
const bundled = await bundle({
  entryPoint: path.join(root, "src", "index.tsx"),
  webpackOverride: (config) => config,
  publicDir: path.join(root, "public"),
});

console.log(`Selecting composition "${templateId}"…`);
const composition = await selectComposition({
  serveUrl: bundled,
  id: templateId,
  inputProps,
});

console.log(`Rendering ${composition.durationInFrames} frames to ${outputPath}…`);
await renderMedia({
  composition,
  serveUrl: bundled,
  codec: "h264",
  outputLocation: outputPath,
  inputProps,
  pixelFormat: "yuv420p",
  crf: 20,
  ffmpegExecutable: process.env.FFMPEG_PATH ?? "ffmpeg",
  onProgress: ({ progress }) => {
    process.stdout.write(`\r  ${Math.round(progress * 100)}%`);
  },
});

console.log(`\nDone → ${outputPath}`);
