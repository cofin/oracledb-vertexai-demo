---
type: Guide
title: Product Guidelines
description: Brand voice, visual identity, privacy rules, and UI/UX design principles
tags:
  - design
  - guidelines
---

# Product Guidelines

<!-- truth: start -->
## Brand Voice and Tone
- **Friendly & Approachable:** The AI Barista communicates in a warm, welcoming, and encouraging manner. Avoid unnecessary technical jargon in customer-facing replies and prioritize a conversational flow that reflects a specialty cafe experience.
- **Helpful & Grounded:** Provide clear recommendations and rationale grounded strictly in Cymbal Coffee catalog products, store hours, and real-time `store_product_inventory` rows.

## Visual Identity
- **Warm & Modern Aesthetics:** Utilize coffee-inspired, earthy tones (browns, creams, warm grays) paired with clean, modern typography to create an inviting atmosphere.
- **Clean Interfaces:** Keep the chat and vector exploration interfaces uncluttered, prioritizing readability and ease of interaction. Use Tailwind CSS v4 for consistent spacing and rounded UI components, and Oracle APEX 26.1 Universal Theme conventions across `src/apex/cymbal-coffee-ops/`.

## UI/UX & Privacy Principles
- **Responsive Design:** Web pages must function cleanly across desktop and mobile viewports.
- **Interactive Feedback:** Use HTMX (`litestar-htmx`), Vite (`litestar-vite`), and Jinja2 templates for fluid server-driven interactions, with TypeScript/vanilla JS reserved for client-only widgets (SSE streaming, ApexCharts, geolocation prompts).
- **Privacy by Default:** Browser geolocation (`latitude`, `longitude`, `radius_miles`) is opt-in and request-scoped, never persisted to database tables, caches, or logs, and outbound map links use keyless Google Maps URLs.
- **Clear Actions:** Make it easy for users to start a new chat, inspect vector similarity and `DBMS_XPLAN` execution plans, or find nearby store locations and stock.
<!-- truth: end -->
