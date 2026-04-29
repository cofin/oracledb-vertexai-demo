// Copyright 2026 Google LLC
// SPDX-License-Identifier: Apache-2.0

import "htmx.org"
import Alpine from "alpinejs"
import ApexCharts from "apexcharts"
import { registerHtmxExtension } from "litestar-vite-plugin/helpers"
import "./styles.css"

window.Alpine = Alpine
window.ApexCharts = ApexCharts
Alpine.start()
registerHtmxExtension()
