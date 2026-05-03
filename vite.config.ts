// SPDX-FileCopyrightText: 2026 Google LLC
// SPDX-License-Identifier: Apache-2.0

import tailwindcss from "@tailwindcss/vite"
import litestar from "litestar-vite-plugin"
import { defineConfig, version } from "vite"
declare const process: { env: Record<string, string | undefined> }
const ASSET_URL = process.env.DMA_ASSET_URL || process.env.ASSET_URL || "/static/"
const BUNDLE_DIR = "src/app/domain/web/static"
const bundlerKey = Number(version.split(".")[0]) >= 8 ? "rolldownOptions" : "rollupOptions"
type BundlerWarning = { code?: string; id?: string } 

export default defineConfig({
  clearScreen: false,
  logLevel: "warn",
  publicDir: "src/resources/public",
  plugins: [
    tailwindcss(),
    litestar({
      input: ["src/resources/main.js", "src/resources/styles.css"] 
    }),
  ],
  server: {
    cors: true,
    port: Number(process.env.VITE_PORT ?? 5173),
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
