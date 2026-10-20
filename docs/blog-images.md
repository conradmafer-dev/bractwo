# Blog image assets

Added 2026-10-05. Guide illustrations are existing Bractwo Krain screenshots, visibly identified as an earlier game version. Their original PNGs and responsive WebP variants remain at the same asset URLs.

The four news illustrations are original AI-generated editorial artwork, created with the built-in ImageGen tool. They do not depict the actual games, interfaces, future systems, or confirmed locations. Each article explicitly identifies the illustration as AI-generated; alt text describes visible content and its editorial context. Official web images were researched with Firecrawl, but are not copied or modified in these assets.

## Generated deliverables

Each stem has `-1200.webp` (1200×675, article/schema/social image) and `-640.webp` (640×360, card/mobile image) in `web/assets/blog/`. Outputs were downscaled and encoded to WebP at quality 85 for delivery; their compositions were not altered.

| Article | Asset stem |
| --- | --- |
| `/blog/runescape-4-zapowiedz` | `runescape-4-wyprawa-ilustracja` |
| `/blog/runescape-pluginy-beta` | `runescape-pluginy-narzedzia-ilustracja` |
| `/blog/ddo-court-of-strahd` | `ddo-court-of-strahd-latarnia-ilustracja` |
| `/blog/pantheon-crafting-2027` | `pantheon-crafting-kuznia-ilustracja` |

## Generation prompts

### New world

Editorial concept illustration for a Polish MMORPG news article about a newly announced online fantasy world. Wide landscape 16:9, painterly high-quality digital fantasy art. A lone cloaked adventurer seen from behind at a weathered stone overlook, beyond is an immense volcanic valley with dramatic cliffs, glowing distant fissures and a pale dawn horizon. Quiet discovery, not active battle. Earthy muted greens, basalt charcoal and warm gold fit a dark forest-green editorial website. Image should feel rich, specific and professionally composed, cinematic atmospheric depth, fine natural stone detail. Completely original scene; not a screenshot, no game UI, no RuneScape characters or logos, no text, no watermark. It will be visibly labeled as an editorial illustration, not a view of the real game. Save project asset.

### Tools and plugins

Editorial concept illustration for a Polish MMORPG news article about game plugins and UI tools. Wide landscape 16:9, beautifully detailed fantasy workshop still life: neatly organized brass compass, small open wooden toolbox with engraving tools, a folded parchment quest map with simple nonverbal markings, a few interlocking brass modules on a worn oak desk. One soft blue magical glow lights the modular parts; warm window light balances it. Painterly polished digital art, elegant rather than cute. Earthy greens, aged brass, dark wood, rich tactile detail. No readable text, no logos, no letters, no game screenshot or fake UI. Completely original image, will be labeled editorial illustration.

### Lantern and mist

Editorial concept illustration for a Polish Dungeons & Dragons Online news article about a gothic fantasy event with magical lanterns and fog. Wide landscape 16:9. Close foreground: ornate old iron lantern held by a gloved hand, warm amber light cutting through thick blue-gray mist. Background: a winding cobblestone path leading toward distant pointed gothic castle towers barely visible through the fog; sparse bare branches. Atmospheric gothic fantasy digital painting, refined natural details, strong composition and contrast suitable for an article hero. Dark forest green and desaturated blue with a single gold warm light. Completely original scene, not a screenshot of DDO or a representation of confirmed event locations, no recognizable copyrighted characters, no text, logos or watermark. Will be labeled editorial illustration.

### Crafting

Editorial concept illustration for a Polish MMORPG news article about planned crafting systems. Wide landscape 16:9. An inviting medieval fantasy forge workbench: smith's hammer and tongs, neatly arranged iron ingots, leather straps, partly finished unadorned sword, a small bundle of herbs; a banked forge glows warm orange in the background. Emphasize tangible making and unfinished work, sophisticated detailed painterly digital art, restrained palette of charcoal, dark wood and warm gold with muted moss green. Eye-level three-quarter composition, clear hierarchy and realistic materials. Original illustration, not a screenshot or mockup of Pantheon game or any actual game system; no UI, no text, no logos or watermark. Will be clearly labeled editorial illustration.

## SEO maintenance

`server/seo.py` owns the canonical article image, dimensions and alt text. Keep those values synchronized with the visible figure. The same image is used by Article/NewsArticle, ImageObject, Open Graph, Twitter and the image sitemap. The server sets the WebP Content-Type explicitly for minimal deployment environments. Keep descriptive filenames stable and use responsive variants of the same image rather than duplicates with different names.

Reference: https://developers.google.com/search/docs/appearance/google-images

## AION 2 launch illustration — 2026-10-05

Built-in ImageGen output, published as `web/assets/blog/aion-2-start-skrzydla-ilustracja-1200.webp` (1200×675) and `web/assets/blog/aion-2-start-skrzydla-ilustracja-640.webp` (640×360), WebP quality 85. The article explicitly labels it an AI-generated editorial illustration, not a game screenshot. No official artwork was used as an input.

Prompt:

Use case: stylized-concept. Create an original editorial hero illustration for a Polish MMO blog article about the global launch of AION 2. Wide 16:9 composition, high-quality atmospheric fantasy digital painting with finely detailed painterly textures. A winged humanoid adventurer viewed from behind glides above a sea of clouds toward a grand airy citadel on a floating rocky island, warm dawn sunlight, immense sense of altitude, detailed pale stone spires, luminous sky and soft mist. A refined restrained palette of desaturated blue, warm gold and forest green, matching a dark-green gaming editorial website. Wing anatomy coherent, two wings attached to the character's upper back, clear elegant silhouette. No text, logos, interface, fake screenshot, or recognizable official game characters or locations. This is a conceptual editorial illustration and will be visibly labeled AI-generated, not actual gameplay. No elements from any supplied official promotional artwork.

## AION 2 account restrictions — 2026-10-11

Official editorial image from NC's Steam announcement, **Account Restrictions — Operation Policy Violations and Temporary Security Locks**. The page's Open Graph metadata points to this artwork; it shows the AION 2 logo beside a tall ruined tower, not an account ban interface or a depiction of cheating.

- Announcement: https://store.steampowered.com/news/app/3393110/view/712288859283524485
- Original image: https://clan.fastly.steamstatic.com/images/46074831/bdbc6a516755d3ba1d4f644f5254f69cee2f972f.png
- Downloaded and visually inspected: 2026-10-11. Original PNG dimensions: 800×450.
- Local hero: `web/assets/blog/aion-2-komunikat-ograniczenia-kont-800.webp` (800×450).
- Responsive card: `web/assets/blog/aion-2-komunikat-ograniczenia-kont-640.webp` (640×360).
- Processing: WebP quality 85; only encoding and proportional downscaling, with no crop, retouching or added elements.
- Suggested alt: `Logo AION 2 na tle wysokiej zrujnowanej wieży — oficjalna grafika NC`.
- Visible caption should identify it as NC's official artwork accompanying the account-restrictions announcement and link to the source. This is attributed publisher artwork, not original or public-domain artwork.

The PLAYNC notice also includes an 1800×150 “Announcements” banner. It was inspected but not used for the article hero because its very wide aspect ratio would require inappropriate cropping or distortion.

## RuneScape 2027 roadmap — 2026-10-12

Official Jagex editorial artwork accompanying **RuneScape 2027 Roadmap**, published on 3 October 2026. The three-panel composition shows a golden dragon, the gnome city, and adventurers exploring a jungle; it is concept artwork, not a gameplay screenshot.

- Announcement: https://secure.runescape.com/m=news/runescape-2027-roadmap-
- Original image: https://cdn.runescape.com/assets/img/external/news/2026/10/blogB5456/BigThumb.jpg
- Downloaded and visually inspected: 2026-10-12. Original JPEG dimensions: 1920×1080.
- Local hero: `web/assets/blog/runescape-2027-roadmap-1200.webp` (1200×675).
- Responsive card: `web/assets/blog/runescape-2027-roadmap-640.webp` (640×360).
- Processing: WebP quality 85; proportional downscaling and format conversion only, with no crop, retouching or added elements.
- Suggested alt: `Złoty smok, miasto gnomów i wyprawa w dżungli — oficjalna ilustracja planów RuneScape na 2027 rok`.
- Visible caption should identify this as official Jagex concept artwork accompanying the 2027 roadmap and link to the source. This is attributed publisher artwork, not original or public-domain artwork.

## Alien Colonies — three races, 2026-10-15

Original AI-generated promotional illustration made with the built-in ImageGen tool for `/blog/alien-colonies-gra-podobna-do-ogame-android`. No external art was used as input. It depicts a blue Zetan, a red Automaton and a green Symbiont against planets and a bright star. The visible article caption identifies it as promotional AI artwork, not gameplay.

- Hero/social image: `web/assets/blog/alien-colonies-trzy-rasy-planety-1200.webp` (1200×675, 255218 bytes).
- Responsive card/mobile image: `web/assets/blog/alien-colonies-trzy-rasy-planety-640.webp` (640×360, 87820 bytes).
- Source generation: 1672×941 PNG; proportional web conversion with the full composition preserved. No semantic retouching.
- Alt: `Zetan, Automaton i Symbiont — trzy rasy Alien Colonies na tle planet i jasnej gwiazdy`.
- Verified Android destination: https://play.google.com/store/apps/details?id=com.conradmafer.aliencolonies

Prompt:

Use case: ads-marketing
Asset type: Hero illustration for a Polish article introducing Alien Colonies, a new space empire strategy game. Original promotional concept art, not a screenshot.
Primary request: Three distinct science-fiction species in the foreground with beautiful planets and a luminous star in deep space behind them.
Scene/backdrop: Wide cinematic outer-space panorama, richly detailed Earth-size worlds with varied surfaces, a ringed planet farther back, brilliant warm white-gold star above the planetary horizon, delicate nebula haze and scattered stars. Keep the celestial bodies recognizable and separate, with depth and scale.
Subject: Exactly three principal figures seen from waist or chest up, each individually readable: a slender intelligent blue Zetan alien with smooth blue skin, an elongated elegant head and refined advanced technology; a strong red Automaton with heavy dark metallic robotic armor and glowing red energy details, unmistakably a machine; and a green Symbiont with organic living armor, graceful alien anatomy and green bioluminescent growth, unmistakably biological. Each occupies a balanced third of the composition with distinct silhouettes and no overlap of faces. Serious intriguing expressions.
Style/medium: Premium cinematic sci-fi painted illustration with convincing detailed materials, striking yet tasteful game cover art. Original character designs, sophisticated atmosphere, crisp focal details, not cartoon.
Composition/framing: Landscape 16:9 composition, characters medium close-up across the lower two thirds, planetary panorama and star clearly visible behind them in the upper third. Leave generous safe margins around all three heads, faces large enough to read in a thumbnail. Balanced blue, red, green accents against deep navy cosmic background.
Lighting/mood: Warm star rim light and subtle colored local illumination, sense of interstellar discovery and rivalry, strong clear forms, beautiful luminous space.
Constraints: No text, no lettering, no logo, no watermark, no interface, no borders. Not a gameplay screenshot. No recognizable existing franchise characters. Do not add extra foreground characters.

### Alien Colonies Android gameplay screenshots — 2026-10-15

Two authentic gameplay screenshots supplied by the game owner for this article. Original JPEGs copied without cropping, retouching, upscaling or changing the visible interface. Each is 720×1600. Article screenshots load lazily and link to the full-size image.

- `web/assets/blog/alien-colonies-android-rozwoj-kolonii.jpg`: colony Boreas 3, resource/energy values and infrastructure. Supplied as `Screenshot_2026-10-15-15-07-31-083_com.conradmafer.aliencolonies.jpg` (525190 bytes).
- `web/assets/blog/alien-colonies-android-mapa-galaktyki.jpg`: galaxy Aurora and star-system overview with players/Swarm markers. Supplied as `Screenshot_2026-10-15-15-07-22-747_com.conradmafer.aliencolonies.jpg` (312776 bytes).
- Visible captions identify both as Android gameplay. Alt text describes each actual screen; the separate AI hero remains explicitly labelled promotional illustration.


## VAMPIR — global launch, 2026-10-18


Source page: https://vampirgb.netmarble.com/en/preorder
Asset source: https://sgimage.netmarble.com/images/netmarble/thered/20260812/sosz1786525938635.jpg
Retrieved: 2026-10-18
Source: public official Netmarble website og:image (metadata verified with live Firecrawl scrape).
Copyright: © 2025 Netmarble Corp. & Netmarble Neo Inc. All Rights Reserved (visible in original).
Original: 1200×630 JPEG, downloaded without authentication; no Games Press gated assets accessed.
Changes: resized to 640×336 for responsive display; original dimensions retained for 1200px version; converted to WebP quality 85. No crop, compositing, overlays, or content edits. Existing publisher logo, game title and copyright preserved.
Caption (PL): VAMPIR — oficjalna grafika promocyjna gry. Źródło: Netmarble.
Alt (PL): Bohaterowie VAMPIR na tle czerwonego księżyca — grafika promocyjna wampirzego MMORPG Netmarble.
Visual inspection: landscape artwork, five fantasy characters with weapons, red moon, bats, prominent VAMPIR wordmark; official Netmarble logo top-left and rights credit at bottom. Not gameplay screenshot.


## Four original MMO editorial illustrations — 2026-10-20

Created with built-in ImageGen without external reference artwork. These original concept illustrations accompany the English and Polish articles; visible captions identify AI-generated editorial art and distinguish it from actual gameplay and official artwork. All source images were visually inspected. The full composition was retained in the proportional WebP conversions (1200×675 hero and 640×360 card). No semantic edits were made.


### eve-fractured-skies-fleet

- Hero: `web/assets/blog/eve-fractured-skies-fleet-1200.webp` (1200×675).
- Responsive card: `web/assets/blog/eve-fractured-skies-fleet-640.webp` (640×360).
- Original generation: 1672×941 PNG.

Prompt:

Use case: stylized-concept
Asset type: original editorial hero illustration for a space MMO blog article.
Primary request: Create a cinematic, detailed, wide landscape illustration in a 16:9 composition, designed to accompany an analysis of a space MMO expansion called Fractured Skies.
Scene: A vast luminous deep-blue and teal nebula over the curved limb of a blue planet, with a broken ring of distant asteroid fragments and subtle starlight. Four powerful, original sleek battlecruisers emerge from the clouds above the planet.
Subject: Exactly four visually distinct spacecraft, all fully original designs: one long tapered blade-like cruiser with split forward prongs; one broad crescent-shaped armored cruiser; one vertical-fin cruiser with an asymmetric silhouette; and one compact geometric cruiser with swept outriggers. Clearly differentiated readable silhouettes, all coherent as sophisticated space warships without resembling named ships or exact designs from any existing game.
Composition: Cinematic panoramic establishing shot. Main ship at center left, three supporting ships at staggered depth to its right and behind, enough separation to count all four. Strong perspective and clear focal point, planet occupying the lower edge, breathing space around the fleet. Preserve the entire scene within the 16:9 frame, no cropped ship noses or fins.
Style: High-quality original painterly science-fiction concept illustration, sophisticated art direction, richly detailed hull surfaces and atmospheric scale, epic but restrained. Not a screenshot and not official game art.
Lighting: Cold blue/teal nebula light on metallic hulls, restrained warm amber engines and running lights, atmospheric volumetric light, crisp subject edges against cloud layers.
Palette: Deep midnight blue, teal, cool silver and small warm thruster accents.
Constraints: No text, letters, UI, logos, watermarks, labels, official characters, recognizable branded spacecraft, or game screenshot elements. Do not recreate EVE Online ships. No explosions, no giant weapons firing. Original editorial concept art only.


### archeage-chronicles-adventurers

- Hero: `web/assets/blog/archeage-chronicles-adventurers-1200.webp` (1200×675).
- Responsive card: `web/assets/blog/archeage-chronicles-adventurers-640.webp` (640×360).
- Original generation: 1672×941 PNG.

Prompt:

Use case: stylized-concept
Asset type: original editorial hero illustration for a fantasy MMO blog article.
Primary request: Create an original high-quality detailed cinematic painterly fantasy landscape in a wide 16:9 landscape composition, depicting a cooperative expedition setting out to explore a new world.
Scene: A vast sunlit green valley with terraced wildflower meadows, a winding river, dramatic distant blue mountains and a far-off busy medieval port at the coast. At the focal point in the middle distance, an enormous weathered ancient stone gateway stands over the path, carved with abstract non-letter geometric details and partially reclaimed by ivy. The gateway is architectural ruins, not a glowing magic portal.
Subjects: Exactly four original adult adventurers, viewed mostly from behind and in three-quarter profile in the lower foreground: a warrior with a round shield and sheathed sword; a ranger with a longbow and hood pushed back; a broad-shouldered berserker with a large axe carried safely over the shoulder; and a mage with a wooden staff and a deep-blue cloak. Distinct readable silhouettes and equipment, practical layered travel clothing, no masks, no recognizable existing characters. They look across the valley together, ready for a cooperative journey, with subtle varied body language.
Composition: The four travelers clustered loosely on a rocky grassy overlook across the lower left and center, separated enough to count. Valley path leads the eye to the ancient gateway, then the far port. Broad scenic view with attractive depth, clear focal point and full bodies visible. Preserve all important subjects within the 16:9 frame; no cropped heads, feet, bows or axes.
Style: Luminous sophisticated hand-painted fantasy concept art with a believable natural world, detailed foliage and stone texture, painterly edges and strong readable shapes, editorial illustration rather than photorealism. Not official game art or a gameplay screenshot.
Lighting: Warm early morning sun from upper right, soft golden rim light on the adventurers, light atmospheric haze, bright hopeful sense of discovery.
Palette: Rich natural greens, warm gold, pale blue mountains and a deep-blue cloak accent.
Constraints: No text, letters, UI, logos, watermarks, labels, official characters, branded costumes, huge weapons in combat poses, or game screenshot elements. No floating interface or icons. Entirely original scene, not a recreation of any specific game location.


### osrs-fractured-archive-raid

- Hero: `web/assets/blog/osrs-fractured-archive-raid-1200.webp` (1200×675).
- Responsive card: `web/assets/blog/osrs-fractured-archive-raid-640.webp` (640×360).
- Original generation: 1672×941 PNG.

Prompt:

Use case: stylized-concept. Asset type: original editorial hero illustration for a fantasy MMO blog article about a raid in a fractured magical archive. Create a premium, richly textured painterly fantasy illustration, landscape 16:9. Deep underground, an enormous ancient magical archive built from fractured stone arches and weathered carved pillars. A sealed circular relic vault stands at the far end, glowing with restrained amber light. Luminous teal and emerald crystals grow through cracks in the stone, reflected in faint mist over the floor. Exactly four small adventurers seen mostly from behind approach together in the lower foreground, each with a distinct readable silhouette: shield-bearing warrior, hooded archer, robed mage, and agile scout. A tall mysterious guardian silhouette waits near the vault, distant enough to feel monumental and unknown. Strong central composition, layered depth, clear focal point on the sealed vault and guardian, cinematic but believable light, jewel-like green and warm gold palette, tactile stone and fabric. Original conceptual fantasy art, suitable as editorial illustration; do not reproduce any existing RuneScape or Old School RuneScape creature, boss, character design or location. No text, letters, title, labels, logos, game UI, HUD, border, watermark or screenshot styling. Preserve full composition with room around the adventurers.


### runescape-plugin-hub-tools

- Hero: `web/assets/blog/runescape-plugin-hub-tools-1200.webp` (1200×675).
- Responsive card: `web/assets/blog/runescape-plugin-hub-tools-640.webp` (640×360).
- Original generation: 1672×941 PNG.

Prompt:

Use case: stylized-concept. Asset type: original editorial hero illustration for a fantasy MMO blog article about community plugins and navigation tools. Create a premium, richly textured painterly illustration, landscape 16:9, with tactile materials and a restrained emerald green and warm gold palette. Close three-quarter overhead view of an explorer's oak workbench in an atmospheric fantasy study. At the center lies a broad hand-drawn parchment map containing rivers, forests, mountain outlines and paths, completely without writing. Exactly five clearly distinguishable interlocking brass-and-crystal tool modules form a small elegant connected mechanism across the center of the map: a luminous crystal lens, a compass wheel, a faceted green prism, a brass gear ring, and a small amber crystal beacon. They should look like handcrafted physical instruments, not technology screens. A separate beautiful compass and a rolled parchment sit near the edges. Several subtle translucent emerald map-tile markers rise magically above the map, gently illuminated, suggesting community-made navigation and tools. Clear central focal point on the five connected modules, believable warm window light, luminous reflections, detailed wood grain, aged parchment and polished brass. Sophisticated editorial fantasy art, original conceptual illustration, no reproduction of any actual RuneScape item, character or location, no actual game screenshot. No readable text or letters, titles, labels, numbers, logos, game UI, HUD, screens, border or watermark. Compose the full map and apparatus inside the frame with breathing space.
