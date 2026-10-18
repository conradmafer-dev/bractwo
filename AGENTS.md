# Blog publishing

The MMO blog is published in Polish and English. For every new blog post or substantive update, prepare both language versions in the same change.

- Keep the established Polish URL and add a descriptive English URL under `/en/blog/`.
- Store full English article templates in `web/en/blog/` and pair them with Polish entries through `server/blog_en.json`.
- Translate titles, descriptions, headings, article text, image alt text, captions and navigation. Preserve source links and distinguish original publication dates from translation dates.
- Keep internal blog links in the reader's language. The PL/EN switch must link to the equivalent article.
- Update both blog indexes. Existing shared rendering supplies self-referencing canonicals, reciprocal language alternates, localized structured data and sitemap coverage.
- Run `python -m unittest tests.test_seo` before publication. Its coverage checks require a matching English version for every Polish blog article.

See `docs/blog-publishing.md` for the metadata and verification workflow.
