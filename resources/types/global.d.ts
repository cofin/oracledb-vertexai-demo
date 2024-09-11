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

import { AxiosInstance } from "axios"
import type { Page, PageProps, Errors, ErrorBag } from "@inertiajs/core"
interface FlashMessages {
  [category: string]: string[]
}

declare global {
  interface Window {
    axios: AxiosInstance
  }

  interface InertiaProps extends Page<PageProps> {
    flash: FlashMessages
    errors: Errors & ErrorBag
    csrf_token: string
    [key: string]: any
  }
}
