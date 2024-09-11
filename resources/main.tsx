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

import { createRoot, hydrateRoot } from "react-dom/client"
import { createInertiaApp } from "@inertiajs/react"
import { resolvePageComponent } from "litestar-vite-plugin/inertia-helpers"
import { ThemeProvider } from "@/components/theme-provider"
import axios from "axios"
import "./main.css"
const appName = import.meta.env.VITE_APP_NAME || "OracleDB Vertex AI Demo"
axios.defaults.withCredentials = true
createInertiaApp({
  title: (title) => `${title} - ${appName}`,
  resolve: (name) =>
    resolvePageComponent(
      `./pages/${name}.tsx`,
      import.meta.glob("./pages/**/*.tsx")
    ),
  setup({ el, App, props }) {
    const appElement = (
      <ThemeProvider defaultTheme="system" storageKey="ui-theme">
        <App {...props} />
      </ThemeProvider>
    )
    if (import.meta.env.DEV) {
      createRoot(el).render(appElement)
      return
    }

    hydrateRoot(el, appElement)
  },
  progress: {
    color: "#4B5563",
  },
})
