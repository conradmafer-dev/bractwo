# Publishing the bilingual MMO blog

The blog is available in Polish at `/blog` and in English at `/en/blog`. This workflow applies to the blog index and every article, including D&D articles in the blog. Game screens and the separate `/poradniki/` section have their own scope.

## Add or update an article

1. Prepare the Polish template in `web/blog/` and its `PublicPage` entry in `server/seo.py`.
2. Write the complete English translation in `web/en/blog/` with `lang="en"`, one H1 and the shared `SEO_HEAD` and `PUBLIC_HEADER` markers. Retain the source evidence, tables, image attribution and the distinction between actual screenshots and illustrations.
3. Add its English metadata to `server/blog_en.json`, keyed by the Polish canonical path. Required fields are `path`, `title`, `description`, `name`, `category`, `image_alt`, `card_kicker` and `card_description` and `modified_date` (the actual English translation or update date). The English `name` must match the visible H1, and `image_alt` must match the hero's alt text. The English page reuses the original image asset with a translated description.
4. Add a card to each blog index in the same order. Link English blog pages to English equivalents, including related articles. A link to a Polish-only game page or guide should say that the destination is in Polish.
5. Keep original publication and source dates visible. Label the date of the English version separately. For later translations, set `modified_date` in the English metadata JSON to the actual translation or update date; do not present historical announcements as breaking news. Refresh time-sensitive facts in both languages when changing the substance.
6. Run `python -m unittest tests.test_seo` and `git diff --check`. Verify the live Polish/English index and at least one translated article after deployment.

## SEO behavior

Each version has its own canonical URL and full server-rendered content. Reciprocal `hreflang="pl"` and `hreflang="en"` links in the head identify equivalent pages and include self-references. These annotations use absolute URLs. English is targeted by language, without limiting it to one country.

Both languages are listed in the sitemap. `Content-Language`, HTML `lang`, Open Graph labels, structured data and the blog collection follow the selected language. The language switch points to the matching article. Untranslated game pages are not advertised as English equivalents. Language selection is explicit through links; crawlers and readers receive the same content at a given URL.

Google references:
- https://developers.google.com/search/docs/specialty/international/localized-versions
- https://developers.google.com/search/docs/specialty/international/managing-multi-regional-sites
