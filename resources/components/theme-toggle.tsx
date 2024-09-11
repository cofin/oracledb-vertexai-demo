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

import { Button } from "@/components/ui/button"
import { useTheme } from "@/components/theme-provider"
import { cn } from "@/lib/utils"
import { MoonIcon, ServerIcon, SunIcon } from "lucide-react"

export function ThemeToggle() {
  const { theme, setTheme } = useTheme()

  return (
    <div className="flex items-center gap-x-1 [&_svg]:size-4 [&_button]:rounded-full">
      <Button
        size="icon"
        variant="ghost"
        className={cn(theme === "light" ? "bg-secondary" : "bg-background")}
        onClick={() => setTheme("light")}
      >
        <SunIcon />
      </Button>
      <Button
        size="icon"
        variant="ghost"
        className={cn(theme === "dark" ? "bg-secondary" : "bg-background")}
        onClick={() => setTheme("dark")}
      >
        <MoonIcon />
      </Button>
      <Button
        size="icon"
        variant="ghost"
        className={cn(theme === "system" ? "bg-secondary" : "bg-background")}
        onClick={() => setTheme("system")}
      >
        <ServerIcon />
      </Button>
    </div>
  )
}
