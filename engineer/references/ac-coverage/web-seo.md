# Web / SEO / meta coverage checklist

Use when a feature touches a public web surface (HTML pages, marketing site, docs site, anything indexable). Surface these as a batched opt-in/out during discover-acs Step 3 (cross-cutting pass).

## Per-page meta coverage

- [ ] **Every page has a `<title>`** appropriate to its content (not the same title repeated everywhere).
- [ ] **Every page has a meta description.** Length 50–160 chars.
- [ ] **Every page has a canonical link** (`<link rel="canonical">`) pointing at the production URL.
- [ ] **Every page has a default `og:image`** even when the page hasn't declared one explicitly. image-titler shipped without this; pages on social previews were broken.
- [ ] **Every page has `og:title`, `og:description`, `og:url`, `og:type`.**
- [ ] **Every page has Twitter Card meta** (`twitter:card`, `twitter:site`, `twitter:title`, `twitter:description`, `twitter:image`).
- [ ] **`robots` meta** is correct per environment (staging/preview = `noindex,nofollow`; production = `index,follow` unless intentionally hidden).

## Site-wide

- [ ] **`robots.txt`** exists and matches environment policy.
- [ ] **`sitemap.xml`** exists, is referenced from `robots.txt`, and is regenerated when pages change.
- [ ] **Favicon + apple-touch-icon** present in expected sizes.
- [ ] **Structured data (JSON-LD)** for at least the primary entity types (Organization, Article, BreadcrumbList) — if the project surfaces in Google rich results.
- [ ] **Open Graph default fallback image** is set at the layout level so individual pages opt into a specific one rather than opting in to having one at all.

## Verification

- [ ] **Lighthouse / pa11y SEO score** on every page above a charter-set threshold (default ≥ 90).
- [ ] **Pre-deploy meta validator** runs against the build output to catch missing fields before they ship — mmc-style production-time validation is too late.

## When NOT to use this checklist

- API-only feature (no HTML output).
- Internal admin tool behind auth (not indexable).
- Single-page application that doesn't pre-render — different SEO model (server-rendered meta, hydration timing) deserves its own checklist (not yet written).
