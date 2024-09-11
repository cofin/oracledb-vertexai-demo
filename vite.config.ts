/**
 * Copyright 2024 Google LLC
 *
 * Licensed under the Apache License, Version 2.0 (the "License");
 * you may not use this file except in compliance with the License.
 * You may obtain a copy of the License at
 *
 *     http://www.apache.org/licenses/LICENSE-2.0
 *
 * Unless required by applicable law or agreed to in writing, software
 * distributed under the License is distributed on an "AS IS" BASIS,
 * WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
 * See the License for the specific language governing permissions and
 * limitations under the License.
 */

import { defineConfig } from "vite"
import path from "path"
import litestar from "litestar-vite-plugin"
import react from "@vitejs/plugin-react"

const GOOGLE_MAPS_API_KEY = process.env.GOOGLE_MAPS_API_KEY || ""
const ASSET_URL = process.env.ASSET_URL || "/static/"
const VITE_PORT = process.env.VITE_PORT || "5173"
const VITE_HOST = process.env.VITE_HOST || "localhost"
export default defineConfig({
  base: `${ASSET_URL}`,
  clearScreen: false,
  publicDir: "public/",
  server: {
    host: "0.0.0.0",
    port: +`${VITE_PORT}`,
    cors: true,
    hmr: {
      host: `${VITE_HOST}`,
    },
  },
  plugins: [
    react(),
    litestar({
      input: ["resources/main.tsx", "resources/main.css"],
      assetUrl: `${ASSET_URL}`,
      bundleDirectory: "app/domain/web/public",
      resourceDirectory: "resources",
      hotFile: "app/domain/web/public/hot",
    }),
  ],
  resolve: {
    alias: {
      "@": path.resolve(__dirname, "resources"),
    },
  },
})
