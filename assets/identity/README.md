# rastro · brand guide

**rastro** is Portuguese for *trail*. The mark is the investigation itself: four stops that
grow as the evidence builds (complaint, delivery, batch, machine) and end in the target, in
amber, where the cause is.

| Element | Meaning |
|---|---|
| Three ink dots, growing | complaint → delivery → batch |
| Dashed line | the trail through the records |
| Amber target | the equipment and the cause |

## Files (`svg/` is the source of truth)

| File | Use |
|---|---|
| `rastro-logo-color.svg` | mark + wordmark on light backgrounds (README, slides) |
| `rastro-logo-inverse.svg` | mark + wordmark on dark backgrounds |
| `rastro-mark-color.svg` | mark alone, 48 px and up |
| `rastro-mark-inverse.svg` | mark alone on dark backgrounds |
| `rastro-mark-mono.svg` | one-colour print |
| `rastro-favicon.svg` | 16 to 32 px: thicker dots, no dash detail |
| `rastro-banner-light.svg` / `-dark.svg` | repository and social banner, 1280×320 |

`png/` has renders of the banners and a 512 px mark for places that do not take SVG.
`_source/options.png` records the three concepts considered (gemba, rastro, fishbone).

## Minimum sizes

| Piece | Minimum | Below that |
|---|---|---|
| Logo (mark + wordmark) | 120 px wide | use the mark |
| Mark | 32 px | use the favicon |
| Favicon | 16 px | — |

## Palette

| Colour | Hex | Role |
|---|---|---|
| Ink | `#1F2A37` | mark and text on light |
| Paper | `#F5F4F0` | light background |
| Night | `#14181D` | dark background |
| Light | `#EDEDED` | mark and text on dark |
| Steel | `#5B7083` | secondary text, tagline |
| Amber | `#E8A317` | the target only; never for body text |

Amber is used once per composition: it marks the cause. Everything else stays ink or steel.

## Type

| Role | Font |
|---|---|
| Wordmark and headings | IBM Plex Sans SemiBold |
| Tagline, labels, code | IBM Plex Mono Medium, uppercase, letter spacing 0.16 em |

Both are open source (OFL). The SVGs fall back to Inter, Segoe UI or Helvetica when Plex is
not installed.
