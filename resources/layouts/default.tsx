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

import { PropsWithChildren, ReactNode } from "react"

interface DefaultLayoutProps {
  header?: string | null
  description?: string | ReactNode | null
}

export function DefaultLayout({
  description = null,
  header = null,
  children,
}: PropsWithChildren<DefaultLayoutProps>) {
  return (
    <div className="container relative flex flex-col min-h-full grow items-center justify-center md:grid lg:max-w-none lg:grid-cols-2 lg:px-0">
      {children}
    </div>
  )
}
