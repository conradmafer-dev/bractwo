# Blog publishing

Publish every new MMO blog post in Polish, English, Spanish and Brazilian Portuguese in the same change. Update all published versions together when the substance changes.

- Keep the Polish URL and add descriptive localized URLs under `/en/blog/`, `/es/blog/` and `/pt-br/blog/`.
- Store complete localized templates in the matching `web` directories and pair them through `server/blog_en.json`, `server/blog_es.json` and `server/blog_pt_br.json`, keyed by the Polish URL.
- Translate titles, descriptions, headings, article text, image alt text, captions and navigation. Preserve source links and label original dates and translation dates clearly.
- Use the equivalent local article when available. Identify the destination language of links to older articles that have fewer translations.
- Update all four indexes for a new post. Shared rendering provides separate canonicals, reciprocal language alternates, localized structured data and sitemap coverage for the published versions.
- Check an older article's facts and usefulness before adding translations. Expired previews and superseded announcements can remain in their existing languages.
- Run `python -m unittest tests.test_seo` before publication.

See `docs/blog-publishing.md` for the metadata and verification workflow.
