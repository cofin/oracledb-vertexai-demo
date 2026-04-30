// Copyright 2026 Google LLC
// SPDX-License-Identifier: Apache-2.0

import tailwindcss from "@tailwindcss/vite"
import litestar from "litestar-vite-plugin"
import { defineConfig, version } from "vite"

const bundlerKey = Number(version.split(".")[0]) >= 8 ? "rolldownOptions" : "rollupOptions"
type BundlerWarning = { code?: string; id?: string }

export default defineConfig({
  // Vite copies project-root publicDir into bundleDir at build time. Brand assets
  // live alongside the JS/CSS sources under src/resources/public/, so point Vite there.
  publicDir: "src/resources/public",
  plugins: [
    tailwindcss(),
    litestar({
      input: ["src/resources/main.js", "src/resources/styles.css"],
      bundleDir: "src/app/domain/web/static/dist",
      hotFile: "src/app/domain/web/static/dist/hot",
      assetUrl: "/static/dist/",
      resourceDir: "src/resources",
    }),
  ],
  server: {
    cors: true,
  },
  build: {
    [bundlerKey]: {
      onwarn(warning: BundlerWarning, warn: (warning: BundlerWarning) => void) {
        if (warning.code === "EVAL" && warning.id?.includes("htmx")) {
          return
        }
        warn(warning)
      },
    },
  },
})
