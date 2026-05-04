# Cymbal Coffee Maps

Store lookup and product availability work without a Google Maps API key. Chat
responses return structured store rows plus `map_actions`; the browser renders
those actions as outbound Google Maps search links using only seeded store
address, coordinates, and optional Google Place IDs.

## Default Link Mode

No-key link mode is the default:

```bash
MAPS_ENABLE_EMBED=false
GOOGLE_MAPS_EMBED_API_KEY=
```

In this mode the app renders outbound Maps links only. Gemini, Vertex AI, and
Google AI API keys are not used for map links.

## Security Header Toggle

The stock UI does not render embedded map iframes. The settings below only
control the security headers for deployments that add a Maps Embed iframe:

```bash
export MAPS_ENABLE_EMBED="true"
export GOOGLE_MAPS_EMBED_API_KEY="<restricted-maps-embed-key>"
```

When both values are set, the app adds frame CSP allowances for Google Maps.
When they are disabled or missing, those frame allowances are omitted. The app
always sends
`Permissions-Policy: geolocation=(self)`, which permits the first-party app to
ask for browser location but does not grant geolocation to embedded Google
frames.

## Create A Restricted Key

Use the helper script to create or reuse the demo key:

```bash
tools/scripts/create-maps-embed-key.sh \
  --project "<google-cloud-project>" \
  --referrer "http://localhost:5006/*" \
  --referrer "https://<your-hostname>/*" \
  --reuse-existing
```

Preview the commands without touching Google Cloud:

```bash
tools/scripts/create-maps-embed-key.sh \
  --project "<google-cloud-project>" \
  --referrer "http://localhost:5006/*" \
  --dry-run
```

The script enables `maps-embed-backend.googleapis.com`, creates or updates the
`oracledb-vertexai-demo-maps-embed` key, restricts it to the supplied HTTP
referrers, and restricts it to the Maps Embed API. It refuses to create an
unrestricted key and refuses to write secrets to files tracked by git. It is not
needed for the default outbound-link mode.

## Browser Location Privacy

The chat UI asks for browser location only after the user selects **Use my
location**. Coordinates are sent on that request to rank nearby stores and
availability. Raw latitude and longitude are not returned in the final chat
payload and are not persisted in chat history, cache entries, metrics, or logs;
downstream chat state keeps only safe facts such as whether browser coordinates
were present and the reported accuracy.

Manual city, ZIP, and landmark prompts do not require browser geolocation.

## Demo Prompts

Use these prompts when checking the Dallas store route:

```text
Find a store near Dallas
Directions to the Dallas store
Is cold brew available in Dallas?
Use my location to find the nearest store
```
