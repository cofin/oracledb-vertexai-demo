# Flow: Store Maps Security and Docs (store-maps-security-docs_20260501)

*Chapter 5 of [store-location-inventory-chat_20260501](../store-location-inventory-chat_20260501/prd.md)*
*Beads: TBD*

---

## Objective

Harden and document the store/maps feature, including browser-location privacy behavior, optional Maps Embed key setup, and final implementation verification.

---

## Dependencies

- Requires `browser-location-maps-ui_20260501`.
- Coordinates with docs/cleanup specs but owns maps/location documentation.

---

## Scope

### Security Headers and Settings

- Add settings:
  - `MAPS_ENABLE_EMBED=false`
  - `GOOGLE_MAPS_EMBED_API_KEY`
- Add or update response headers:
  - `Permissions-Policy: geolocation=(self)`
  - CSP frame allowances only when embed is enabled.
- Do not grant geolocation to the Google iframe.
- Do not include embed URLs in response cache.

### Key Script

Add `tools/scripts/create-maps-embed-key.sh`:

- supports `--project`, repeated `--referrer`, `--dry-run`, `--env-file`, and `--reuse-existing`
- enables `maps-embed-backend.googleapis.com`
- creates or reuses `oracledb-vertexai-demo-maps-embed`
- restricts the key to allowed HTTP referrers
- restricts the key to Maps Embed API only
- prints:

```bash
export GOOGLE_MAPS_EMBED_API_KEY="<returned-key-string>"
export MAPS_ENABLE_EMBED="true"
```

Safeguards:

- never creates unrestricted keys
- never reads or reuses Gemini/Vertex keys
- never writes secrets to tracked files
- refuses `--env-file` targets that are tracked by git

### Documentation

Document:

- no-key Maps URL baseline
- optional Maps Embed setup
- separate Maps Embed key requirement
- Google Cloud key restrictions
- browser-location privacy behavior
- Dallas manual demo prompts

### Verification

Final gates:

```bash
make lint
make test
```

Manual prompts:

- "Find a store near Dallas"
- "Directions to the Dallas store"
- "Is cold brew available in Dallas?"
- "Use my location to find the nearest store"

---

## Tests

- Unit tests for settings defaults.
- Unit tests for security headers if header ownership exists in app code.
- Shell/script tests or dry-run contract tests for `create-maps-embed-key.sh`.
- Regression tests proving raw browser coordinates are not persisted.
- Frontend tests proving missing embed key falls back to links.

---

## Acceptance Criteria

- Full feature works without any Google Maps key through Maps URLs.
- Embedded maps require explicit env/settings and a separate restricted Maps Embed key.
- `create-maps-embed-key.sh --dry-run` shows restricted key commands without creating resources.
- Script refuses unrestricted key creation and tracked secret writes.
- Docs state Gemini keys are not required for Maps URLs or Maps Embed.
- Final implementation passes `make lint` and `make test`.
