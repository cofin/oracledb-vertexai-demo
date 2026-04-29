# Plan: Light/Dark Logos and Landing Page Redesign

## Objective
1. Create light and dark focused variants of the new Cymbal Coffee SVGs and integrate them into the React application natively (supporting dynamic theming).
2. Re-imagine the landing page (`src/js/src/routes/index.tsx`) to improve its visual appeal, replace/remove the "Demo Control Plane" heading, and feature Google and Oracle SVG logos to highlight the architecture.

## Key Files
- `src/js/public/cymbal-coffee-logo-light.svg` & `src/js/public/cymbal-coffee-logo-dark.svg` (new)
- `src/js/public/cymbal-coffee-text-light.svg` & `src/js/public/cymbal-coffee-text-dark.svg` (new)
- `src/js/src/components/CymbalLogo.tsx` (new)
- `src/js/src/components/GoogleLogo.tsx` (new)
- `src/js/src/components/OracleLogo.tsx` (new)
- `src/js/src/routes/__root.tsx` (modifying logo usage)
- `src/js/src/routes/index.tsx` (landing page redesign)

## Implementation Steps

### 1. Static Asset Variants
- Copy the newly generated vector-traced SVGs to create explicit `-light.svg` (black text `#000000`) and `-dark.svg` (white text `#FFFFFF`) versions in `src/js/public/`. 

### 2. React Components for Logos
- Create `src/js/src/components/CymbalLogo.tsx` containing an inline version of the SVG with `fill="currentColor"` for the text path. This allows it to adapt to the light/dark theme seamlessly.
- Create `src/js/src/components/GoogleLogo.tsx` with a standard Google SVG logo.
- Create `src/js/src/components/OracleLogo.tsx` with a standard Oracle SVG logo.

### 3. Update Root Layout (`__root.tsx`)
- Replace the hardcoded `<img>` with the new `CymbalLogo` component.
- Remove the `bg-white`, `border`, and `overflow-hidden` utility classes from its parent `<span>` so it looks native in the header.

### 4. Re-imagine the Landing Page (`index.tsx`)
- Remove or rewrite the "Demo Control Plane" eyebrow heading to be more relevant (e.g., "Architecture Showcase").
- Update the hero section to be more modern and impactful.
- Incorporate the `GoogleLogo` and `OracleLogo` into the header or as a "Powered by" section near the title to emphasize the tech stack (Oracle 26AI + Google Gemini).
- Improve the layout, typography, and visual hierarchy of the main landing tiles.

## Verification
- Toggle the dark/light mode button in the application to verify the Cymbal logo text adapts perfectly.
- Ensure the Google and Oracle logos render correctly on the landing page.
