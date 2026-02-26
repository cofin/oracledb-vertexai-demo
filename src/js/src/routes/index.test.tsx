import { describe, expect, it } from "bun:test"

import { Route } from "./index"

describe("LandingPage", () => {
  it("defines the root dashboard route", () => {
    expect(Route.options.path).toBe("/")
  })
})
