# HULA drone — marketing / competition research

Research pass on the HighGreat **HULA** educational drone ecosystem: the
product itself, the competitions it's flown in (especially Singapore), and
the plugins/apps/docs people use to program it. Gathered 2026-09-22.

## Who makes it

**HighGreat** (Shenzhen HighGreat Innovation Technology Development Co.,
Ltd. / 深圳市高科新农技术有限公司's drone arm) -- a Chinese drone maker,
official sites [en.hg-fly.com](https://en.hg-fly.com) and
[highgreatdrone.com](https://www.highgreatdrone.com/hula). HULA is their
educational/AI-coding line: <120g quadcopter, block/Python programmable,
laser "battle" modes, swarm formation flight, QR/AI vision, infrared
obstacle avoidance. It ran a [Kickstarter
campaign](https://www.kickstarter.com/projects/highgreat/hula-an-entertaining-and-educational-toy-drone-for-everyone)
(105 backers, HK$211,036 pledged against a HK$50,000 goal, updated May
2025).

This repo's own SDK (`hula_sdk/`, see the top-level README) is an
independent, unofficial Python wrapper around HighGreat's `pyhula`
package -- unrelated to HighGreat itself, but the same physical drone.

## Singapore competitions

The main organizer running HULA-based competitions in Singapore is
**65Drones Pte Ltd** ([65drones.com](https://www.65drones.com), the
Singapore reseller of the HULA and organiser of **Air Land Conquest**),
not HighGreat directly.

### Air Land Conquest 2026

- **Dates:** 31 Aug -- 1 Sep 2026, **Venue:** NTU@one-north, 11 Slim
  Barracks Rise, Singapore 138664. Organiser: 65Drones Pte Ltd
  (admin@65drones.com, +65 9073 5988 / +65 8720 4983).
- **AI Alliance Drone Challenge** -- teams of ≤3, MOE schools only, ≤18
  y/o. One autonomous HULA + one manually-piloted HULA cooperate through a
  6m x 5m obstacle course (line-patrol track + crossing track) printed on
  a custom carpet mat, within a 6-minute run. Full rules, scoring, and the
  obstacle/mat diagrams: [`competitions/AI_Alliance_Challenge_rulebook_V2_July2026.pdf`](competitions/AI_Alliance_Challenge_rulebook_V2_July2026.pdf).
- **Drone Swarm Challenge** -- teams of ≤5, MOE schools only, 8-18 y/o.
  Program 7-9 HULA drones to perform a synchronized "swarm dance" to music
  in a 5m x 5m x 2.5m volume. Rules: [`competitions/Drone_Swarm_Challenge_rulebook_July2026.pdf`](competitions/Drone_Swarm_Challenge_rulebook_July2026.pdf).
- Source page (has the current-year updates and registration form):
  [65drones.com/pages/air-land-conquest-2026](https://www.65drones.com/pages/air-land-conquest-2026).
- [`competitions/ai_alliance_brief.pptx`](competitions/ai_alliance_brief.pptx)
  is the organiser's own briefing slide deck (41 images extracted to
  [`tracks/air_land_conquest_2026_brief_images/`](tracks/air_land_conquest_2026_brief_images/)).

### Other Singapore drone competitions (found, not HULA-specific)

Checked and **not** tied to the HULA drone specifically, but part of the
same Singapore drone-education scene: [Asia Drone
Championship](https://www.science.edu.sg/whats-on/competitions/asia-drone-championship)
(Science Centre Singapore, general FPV racing) and the [Singapore Amazing
Flying Machine Competition](https://www.safmc.com.sg/) (SAFMC, general
UAV design challenge). No evidence either uses the HULA platform.

## The competition mat / track

The course is "a special customized carpet, with visual characteristic
patterns printed on it for drone positioning" (rulebook, p.5) -- not a
separately-sold product, it's provided by 65Drones at the competition
venue. Its full layout and every obstacle's dimensions are in the
rulebook; the diagram pages are also extracted standalone as high-res
PNGs in [`mats/`](mats/):

- `air_land_conquest_2026_track_mat_layout.png` -- the full 6m x 5m course
  layout (16 numbered stations: take-off pads, line-patrol/crossing
  tracks, rings, arches, "knife flags", password wall, landing zones).
- `air_land_conquest_2026_obstacle_arch_knifeflag.png` -- arch (100cm h x
  80cm w) and knife flag (180cm h) dimensions.
- `air_land_conquest_2026_obstacle_ring.png` -- ring obstacle (180cm h,
  80cm inner diameter; vertical variant 120cm h).
- `air_land_conquest_2026_obstacle_collab_door.png` -- the laser-activated
  collaborative obstacle door (150cm h x 80cm w).
- `air_land_conquest_2026_obstacle_password_wall.png` -- the QR
  password-acquisition point and 9-key password wall.

## Plugins / SDKs / dev tooling

HighGreat's own stack:

- **`pyhula`** -- the official Python SDK, [on
  PyPI](https://pypi.org/project/pyhula/) (`pip install pyhula`, Windows +
  Python 3.6 only, `cp36` wheels). What this repo's `hula_sdk/` wraps and
  patches.
- **HULA App** ("HuLa EDU") -- the official mobile/PC control + block
  coding app. Android/iOS/PC download portal:
  [hg-fly.com/educational/3208.html](https://www.hg-fly.com/educational/3208.html);
  iOS listing: [App
  Store](https://apps.apple.com/app/hula-edu/id6474287372). Supports
  Scratch-style block coding with 3D flight-simulation preview, plus
  Python. (Third-party Android APK mirrors exist -- APKPure, APKCombo,
  PGYer -- deliberately **not** downloaded here; those aren't
  first-party distribution channels and running an APK from an
  unverified mirror is a real risk. Get it from the official app stores
  above or the vendor portal instead.)
- **Official user manual** -- [`docs/hula_app_manual/Hula_User_Manual_Official.pdf`](docs/hula_app_manual/Hula_User_Manual_Official.pdf)
  (9.6MB, HighGreat's own PDF) plus the mirrored manual webpage
  ([`docs/hula_app_manual/Hula_EN.html`](docs/hula_app_manual/Hula_EN.html)
  + its 36 diagram images in `docs/hula_app_manual/img/`) from
  [ds-api.hg-fly.net/manuals/Hula_EN.html](https://ds-api.hg-fly.net/manuals/Hula_EN.html).
- **65Drones V1 Troubleshooting Guide** --
  [`docs/V1_Troubleshooting_Guide.pdf`](docs/V1_Troubleshooting_Guide.pdf)
  (15 pages), from the [65Drones support
  page](https://www.65drones.com/pages/troubleshooting-guide-to-hula-drone).

Third-party / community, cloned into [`plugins/`](plugins/) (all public
GitHub repos, unofficial, by **Osaka Institute of Technology's drone
project** -- documentation and setup guides, not packaged
extensions/marketplace plugins):

- `oit-droneproject_hula` -- general HULA drone documentation.
- `oit-droneproject_hula_install` -- `pyhula` + Python environment setup
  guide.
- `oit-droneproject_vscode` -- VS Code setup/config guide for
  programming the HULA drone in Python.
- `oit-droneproject_hula_camera`, `oit-droneproject_hula_control`,
  `oit-droneproject_hula_thread` -- camera, motion-control API, and
  threading sample code/docs.
- `oit-droneproject_home` -- the org's index page.

`oit-droneproject_hula`'s own README and unboxing photo
(`image/hula.PNG`) are in Japanese. Added locally (not upstream) inside
that folder: [`README_EN.md`](plugins/oit-droneproject_hula/README_EN.md)
(translation) and
[`image/hula_EN.png`](plugins/oit-droneproject_hula/image/hula_EN.png)
(the same unboxing photo with every label re-rendered in English at its
original position -- battery, charger, spare QR/number cards, USB cable,
screwdriver/removal tool/spare propellers, certificate, drone body). The
original Japanese files are left untouched for attribution.

No dedicated VS Code Marketplace extension, Scratch/Blockly extension
gallery entry, or Node-RED plugin was found published anywhere for HULA
-- the block-coding editor lives inside the official HULA App itself,
not as a separate installable plugin.

## Parts / exploded-view diagrams

No manufacturer "spare parts catalog" exists as a standalone document, but
the official manual has full numbered exploded-view diagrams of the
airframe plus step-by-step assembly photos, pulled out individually in
[`docs/hula_app_manual/img/Hula/`](docs/hula_app_manual/img/Hula/):

- `body.png` / `body2.png` -- full 15-point exploded-view diagrams
  (motors, prop guards, camera/gimbal, battery bay, PCB, antenna, etc.,
  each numbered and callout-lined).
- `installpaddle1/2/3.png` -- propeller mount/removal steps.
- `installBattery.png`, `batterycharge.png` / `batterycharge2.png` --
  battery install and the 2-battery charging hub.
- `obstacleavoidance.png` / `2.png`, `connectdrone1/2/3.png`,
  `reset.png`, `pulldowndirection.png` -- sensor placement and
  connection/reset diagrams.

## Retail packaging (box)

**No public retail box/packaging photo was found.** Checked the
manufacturer site, 65Drones, Kickstarter (main page, all 5 public
updates, and the rewards tier list), AUAV Store (domain no longer
resolves), Aerise.cc, and press coverage -- none show the physical
shipping box. This tracks with the product's status: it funded on
Kickstarter in Nov 2024 and was still working through backer shipping as
of the last update (May 2025), so retail packaging photography may not
be public yet. The closest thing found is a real-world event photo of a
"Hula" cardboard *display standee* (not the retail box) at
`images/65drones_hula_product_main.jpg`.

## Images

- [`images/highgreat_official/`](images/highgreat_official/) -- 32
  official product photos/renders from
  [highgreatdrone.com/hula](https://www.highgreatdrone.com/hula) (`.webp`)
  -- hero shots, in-classroom lifestyle photos, game-mode concept art,
  app screenshots, and event/competition photos (a full arena setup, a
  coaching session, a drone-club space). No box or parts shots among
  them, confirmed by inspection.
- [`images/kickstarter/`](images/kickstarter/) -- 17 campaign
  images/GIFs from the [Kickstarter
  page](https://www.kickstarter.com/projects/highgreat/hula-an-entertaining-and-educational-toy-drone-for-everyone).
- [`images/kickstarter_updates/`](images/kickstarter_updates/) -- 11
  images from the campaign's public updates: Update #2 "Latest KOL
  Review" (4 images, third-party influencer coverage), Update #3 "Media
  Outlets Features" (5 images, press-logo roundup), Update #4 "100%
  funded" milestone (2 images). (Updates #5-8 are backers-only and
  weren't accessible.)
- [`images/press_techreviewer_de/`](images/press_techreviewer_de/) -- 6
  images from a German review site's coverage
  ([en.techreviewer.de](https://en.techreviewer.de/hula-drohne-lass-deine-kids-programmieren-fliegen-und-staunen/)).
- [`images/press_aerise/`](images/press_aerise/) -- 1 product image from
  reseller [aerise.cc](https://aerise.cc/product-store/other-products/highgreat/hula-drone/).
- [`images/youtube_thumbnails/`](images/youtube_thumbnails/) -- 4
  thumbnails: a third-party "upgrade to the Tello" review video, the Air
  Land Conquest walkthrough linked from the rulebook, and the two Asia
  Academic Challenge (EN/TH) videos.
- [`images/`](images/) (top level) -- 8 product photos + 2 spec-sheet
  scans from [65drones.com/products/hula-drone](https://www.65drones.com/products/hula-drone).

## Sources

- [en.hg-fly.com](https://en.hg-fly.com) / [highgreatdrone.com](https://www.highgreatdrone.com/hula) -- manufacturer
- [65drones.com](https://www.65drones.com) -- Singapore reseller + Air Land Conquest organiser
- [Kickstarter campaign](https://www.kickstarter.com/projects/highgreat/hula-an-entertaining-and-educational-toy-drone-for-everyone) (main page + updates #2-4 + rewards tab)
- [pypi.org/project/pyhula](https://pypi.org/project/pyhula/)
- [github.com/oit-droneproject](https://github.com/oit-droneproject) (home, hula, hula_install, hula_camera, hula_control, hula_thread, vscode)
- [ds-api.hg-fly.net/manuals/Hula_EN.html](https://ds-api.hg-fly.net/manuals/Hula_EN.html)
- [en.techreviewer.de](https://en.techreviewer.de/hula-drohne-lass-deine-kids-programmieren-fliegen-und-staunen/) -- third-party German review
- [aerise.cc](https://aerise.cc/product-store/other-products/highgreat/hula-drone/) -- reseller listing
- [PR Newswire launch release](https://www.prnewswire.com/news-releases/the-ultimate-new-educational-partner-for-homes-and-schools-hula-smart--fun-drone-launches-on-kickstarter-for-a-limited-time-experience-302306887.html) (also syndicated on Yahoo Finance, Manila Times, TNGlobal)
- [Camera Jabber](https://camerajabber.com/highgreat-launches-hula-drone/) and [EdTech Innovation Hub](https://www.edtechinnovationhub.com/news/hula-drone-raises-over-17k-on-kickstarter) press coverage
- [science.edu.sg — Asia Drone Championship](https://www.science.edu.sg/whats-on/competitions/asia-drone-championship) (checked, not HULA-specific)
- [safmc.com.sg](https://www.safmc.com.sg/) (checked, not HULA-specific)
- Checked but no usable content found: `auavstore.com` (domain no longer
  resolves), Amazon/AliExpress (no HULA listings found by search),
  HighGreat's Instagram (@highgreat_drone) and Facebook
  (highgreatmedia) -- exist but weren't scraped for individual images.

## Not done on purpose

- Did not download the Android APK from third-party mirror sites
  (APKPure/APKCombo/PGYer) -- those are unofficial distribution channels
  for an installable binary, which is a different risk category than the
  documents/images/source-code gathered here. The official download
  portal and app-store links are above instead.
- Did not create accounts, sign in anywhere, or submit the Air Land
  Conquest interest/registration form.
