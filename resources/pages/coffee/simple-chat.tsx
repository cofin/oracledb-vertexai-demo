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

import { Head } from "@inertiajs/react"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { Container } from "@/components/container"
import ChatPanel from "./partials/chat"
import { DefaultLayout } from "@/layouts/default"
export default function SimpleChat() {
  return (
    <>
      <Head title="Cymbal Chat" />
      <Container className="pt-10">
        <Card>
          <CardHeader>
            <CardTitle>Hi! How can I help you today?</CardTitle>
          </CardHeader>
          <CardContent>
            <ChatPanel />
          </CardContent>
        </Card>
      </Container>
    </>
  )
}

SimpleChat.layout = (page: any) => <DefaultLayout children={page} />
