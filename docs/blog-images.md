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
