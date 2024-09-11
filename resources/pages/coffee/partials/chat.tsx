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

import { useState } from "react"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { ScrollArea } from "@/components/ui/scroll-area"
import { Send } from "lucide-react"
import { useForm, usePage } from "@inertiajs/react"
import { Transition } from "@headlessui/react"
import { InputError } from "@/components/input-error"
export default function ChatPanel() {
  const { content } = usePage<
    InertiaProps & {
      content?: {
        message: string
        answer: string
        messages: { message: string; source: string }[]
        points_of_interest: {
          id: string
          name: string
          address: string
          latitude: number
          longitude: number
        }[]
      }
    }
  >().props

  const { data, setData, post, errors, processing, recentlySuccessful } =
    useForm({
      message: "",
    })
  const [leftPaneWidth, setLeftPaneWidth] = useState(50) // percentage

  const handleSubmit = (e: { preventDefault: () => void }) => {
    e.preventDefault()
    post(route("simple-chat.send"), {
      preserveScroll: true,
      onSuccess: () => {
        console.log("Message sent")
      },
    })
  }
  const handleMouseDown = (e: any) => {
    e.preventDefault()
    document.addEventListener("mousemove", handleMouseMove)
    document.addEventListener("mouseup", handleMouseUp)
  }

  const handleMouseMove = (e: any) => {
    const newWidth = (e.clientX / window.innerWidth) * 100
    setLeftPaneWidth(Math.min(Math.max(newWidth, 30), 70))
  }

  const handleMouseUp = () => {
    document.removeEventListener("mousemove", handleMouseMove)
    document.removeEventListener("mouseup", handleMouseUp)
  }

  return (
    <div className="flex h-96 bg-background text-foreground">
      {/* Left Pane - Chat Interface */}
      <div className="flex flex-col" style={{ width: `${leftPaneWidth}%` }}>
        <ScrollArea className="flex-grow p-4">
          {(content?.messages ?? []).map((msg, index) => (
            <div
              key={index}
              className={`mb-4 ${msg.source === "human" ? "text-right" : ""}`}
            >
              <div
                className={`inline-block p-2 rounded-lg ${msg.source === "human" ? "bg-primary text-primary-foreground" : "bg-secondary"}`}
              >
                {msg.message}
              </div>
            </div>
          ))}
        </ScrollArea>
        <div className="p-4 border-t">
          <form onSubmit={handleSubmit}>
            <div className="flex space-x-2">
              <Input
                id="message"
                value={data.message}
                onChange={(e) => setData("message", e.target.value)}
                onKeyUp={(e) => e.key === "Enter" && handleSubmit(e)}
                placeholder="Chat with Cymbal..."
                className="flex-grow"
                autoFocus
              />
              <InputError className="mt-2" message={errors.message} />
              <Button disabled={processing}>
                <Send className="h-4 w-4" />
              </Button>
              <Transition
                show={recentlySuccessful}
                enterFrom="opacity-0"
                leaveTo="opacity-0"
                className="transition ease-in-out"
              >
                <p className="text-sm text-muted-foreground">Sent.</p>
              </Transition>
            </div>{" "}
          </form>
        </div>
      </div>

      {/* Resizable Divider */}
      <div
        className="w-1 bg-border cursor-col-resize"
        onMouseDown={handleMouseDown}
      />

      {/* Right Pane - Content Display */}
      <div
        className="flex flex-col"
        style={{ width: `${100 - leftPaneWidth}%` }}
      >
        <div className="flex-grow p-4">
          {/* Placeholder for Google Maps embed */}
          <div className="w-full h-full bg-secondary rounded-lg flex items-center justify-center">
            <p className="text-muted-foreground">
              Google Maps Embed Placeholder
            </p>
          </div>
        </div>
      </div>
    </div>
  )
}
