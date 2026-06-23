# Official Logo And Icon Assets

The documentation uses first-party assets where practical. Keep these files
unchanged, and use them only to identify the referenced products and platforms.

## Local Inventory

| File | Source | Notes |
| --- | --- | --- |
| `_static/logos/oracle-logo.svg` | `https://www.oracle.com/a/ocom/img/oracle-logo.svg` | Oracle-hosted SVG. Oracle logo use is governed by Oracle's third-party logo guidelines. |
| `_static/logos/google-cloud-logo-fullcolor.svg` | `https://www.gstatic.com/cgc/google-cloud-logo-fullcolor.svg` | Google Cloud wordmark from the official Google Cloud site assets. Use on light backgrounds. |
| `_static/logos/google-cloud-logo-reverse.svg` | Derived from `google-cloud-logo-fullcolor.svg` | Dark-background reverse lockup: identical colored mark with the wordmark set to white, following Google's reverse-logo guideline. Pair with the full-color asset for theme swapping. |
| `_static/logos/google-cloud-vertex-ai.svg` | `https://services.google.com/fh/files/misc/core-products-icons.zip` | Official Google Cloud product icon. |
| `_static/logos/google-cloud-bigquery.svg` | `https://services.google.com/fh/files/misc/core-products-icons.zip` | Official Google Cloud product icon. |
| `_static/logos/google-cloud-compute-engine.svg` | `https://services.google.com/fh/files/misc/core-products-icons.zip` | Official Google Cloud product icon. |
| `_static/logos/google-cloud-cloud-run.svg` | `https://services.google.com/fh/files/misc/core-products-icons.zip` | Official Google Cloud product icon. |
| `_static/logos/google-cloud-databases.svg` | `https://services.google.com/fh/files/misc/category-icons.zip` | Official Google Cloud category icon. |
| `_static/logos/google-cloud-ai-ml.svg` | `https://services.google.com/fh/files/misc/category-icons.zip` | Official Google Cloud category icon. |
| `_static/logos/google-cloud-agents.svg` | `https://services.google.com/fh/files/misc/category-icons.zip` | Official Google Cloud category icon. |
| `_static/logos/google-cloud-maps-geospatial.svg` | `https://services.google.com/fh/files/misc/category-icons.zip` | Official Google Cloud category icon. |
| `_static/logos/litestar-logo.svg` | `https://github.com/litestar-org/branding/blob/main/assets/Branding%20-%20SVG%20-%20Transparent/Badge%20-%20Blue%20and%20Yellow.svg` | Official Litestar standalone badge SVG from the Litestar branding repository; repository is MIT licensed. |
| `_static/logos/antigravity-logo.png` | `https://antigravity.google/assets/image/antigravity-logo.png` | Official Antigravity site asset. |
| `_static/logos/mcp-toolbox-logo.png` | `https://github.com/googleapis/mcp-toolbox/blob/main/logo.png` | First-party Google APIs repository asset; repository is Apache-2.0 licensed. |

## Source References

- [Google Cloud icon library](https://cloud.google.com/icons)
- [Google Cloud product icons overview](https://services.google.com/fh/files/misc/google-cloud-product-icons.pdf)
- [Litestar branding repository](https://github.com/litestar-org/branding)
- [Google Antigravity press assets](https://antigravity.google/press)
- [MCP Toolbox for Databases](https://github.com/googleapis/mcp-toolbox)
- [Oracle third-party logo guidelines](https://www.oracle.com/legal/logos/)

## Light And Dark Usage

Most marks here read on both the light (`default`) and dark (`slate`) doc
themes: the full-color product and category icons, the Oracle red wordmark, the
Litestar badge, the Antigravity gradient mark, and the MCP Toolbox lockup (its
white outline keeps it legible on dark).

The one mark that needs a theme-specific variant is the **Google Cloud
wordmark** — its near-black `#212226` "Cloud" text disappears on the dark
`slate` background. Show the full-color asset on light and the reverse lockup on
dark, swapped by the active color scheme:

```html
<img class="logo-light" src="_static/logos/google-cloud-logo-fullcolor.svg" alt="Google Cloud">
<img class="logo-dark" src="_static/logos/google-cloud-logo-reverse.svg" alt="Google Cloud">
```

```css
.logo-dark { display: none; }
[data-md-color-scheme="slate"] .logo-light { display: none; }
[data-md-color-scheme="slate"] .logo-dark { display: inline; }
```

The theme sets `data-md-color-scheme` on `<body>` (`default` for light, `slate`
for dark), so this same pattern covers any future logo that needs a
dark-background variant.

## Usage Notes

- Do not crop, distort, or combine vendor logos into new marks; use only
  brand-sanctioned variants (such as Google's full-color and reverse lockups)
  when adapting to light or dark backgrounds.
- Prefer generic Sphinx icon roles for UI decoration.
- Use product logos only where the surrounding text clearly identifies the
  corresponding technology.
- Keep source links current when refreshing assets.
