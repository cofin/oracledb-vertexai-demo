import { describe, expect, it } from "bun:test"

import { Route, VectorDemoPage } from "./vector-demo"

describe("VectorDemoPage", () => {
  it("defines the vector demo component", () => {
    expect(Route.options.component).toBe(VectorDemoPage)
  })
})
