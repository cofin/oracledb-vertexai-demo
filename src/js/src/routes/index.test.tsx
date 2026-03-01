import { describe, expect, it } from "bun:test"

import { LandingPage, Route } from "./index"

describe("LandingPage", () => {
  it("defines the landing component", () => {
    expect(Route.options.component).toBe(LandingPage)
  })
})
