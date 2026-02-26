import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";
import tailwindcss from "@tailwindcss/vite";
import litestar from "litestar-vite-plugin";
import tsconfigPaths from "vite-tsconfig-paths";
import { resolve } from "node:path";

const ASSET_URL = process.env.ASSET_URL ?? "/static/dist/";
const BUNDLE_DIR = resolve(__dirname, "../py/app/server/static/dist");

export default defineConfig({
  plugins: [
    react(),
    tailwindcss(),
    tsconfigPaths(),
    litestar({
      input: ["index.html", "src/main.tsx"],
      bundleDir: BUNDLE_DIR,
      hotFile: "hot",
      assetUrl: ASSET_URL,
    }),
  ],
  server: {
    host: "0.0.0.0",
    port: 5173,
    cors: true,
  },
  build: {
    emptyOutDir: true,
  },
});
