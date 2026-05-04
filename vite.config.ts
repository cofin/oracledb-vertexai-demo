// SPDX-FileCopyrightText: 2026 Google LLC
// SPDX-License-Identifier: Apache-2.0

import tailwindcss from "@tailwindcss/vite"
import litestar from "litestar-vite-plugin"
import { defineConfig, version } from "vite"

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
