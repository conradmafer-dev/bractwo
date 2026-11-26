# Publishing the MMO blog in four languages

New posts are published together in Polish (`pl`), English (`en`), Spanish (`es`) and Brazilian Portuguese (`pt-BR`). This applies to the blog, including its D&D articles. The game screens and the separate `/poradniki/` guides have their own scope.

| Language | Index | Article templates | Metadata |
| --- | --- | --- | --- |
| Polish | `/blog` | `web/blog/` | `PublicPage` in `server/seo.py` |
| English | `/en/blog` | `web/en/blog/` | `server/blog_en.json` |
| Spanish | `/es/blog` | `web/es/blog/` | `server/blog_es.json` |
| Brazilian Portuguese | `/pt-br/blog` | `web/pt-br/blog/` | `server/blog_pt_br.json` |

1. Verify the source material and write the Polish article and its `PublicPage` entry. Give each translation a descriptive URL, the same publication date and a complete template with one H1 plus the `SEO_HEAD` and `PUBLIC_HEADER` markers.
2. Key each translation's metadata by the Polish canonical path. Supply `path`, `title`, `description`, `name`, `category`, `image_alt` when the article has a hero image, and `modified_date`. Match `name` to the visible H1 and `image_alt` to the hero. Use `card_kicker` and `card_description` for the index copy.
3. Translate the complete content, including image descriptions, captions, tables, navigation and link labels. Preserve original publication dates, source dates and image attribution. Show the translation or update date separately and make `modified_date` match it. Keep official product, item and interface names when readers need them to find the feature.
4. Link each article from its language index. Use localized equivalents for related links. When an older link leads to a different language, identify that language in the link text. Review all existing versions when an article needs a factual correction.
5. For existing articles that have fewer languages, check that the advice still applies before translating. Keep expired or superseded announcements in their existing editions.
6. Run `python -m unittest tests.test_seo` and `git diff --check`. After deployment, verify the four indexes and the language links on the new article.

## Search metadata

Each published version has a canonical URL, server-rendered text, `Content-Language`, HTML `lang`, Open Graph labels and structured data in its own language. Reciprocal `hreflang` annotations and the visible language switch list the versions available for that article. The sitemap includes their canonical URLs. Spanish uses the language code `es` for readers across regions, while Brazilian Portuguese uses `pt-BR`.

[Google Search Central guidance on localized pages](https://developers.google.com/search/docs/specialty/international/localized-versions)
