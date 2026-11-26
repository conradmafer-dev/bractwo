"""Crawlable documents, canonical URLs, indexing policy and HTTP delivery."""
from dataclasses import replace
import gzip
from html import escape
from html.parser import HTMLParser
import json
from pathlib import Path
import sys
import unittest
from unittest.mock import patch
from urllib.parse import urljoin, urlsplit
import xml.etree.ElementTree as ET

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from aiohttp.test_utils import TestClient, TestServer
from server import seo
from server.server import create_app


LEGACY_BILINGUAL_ARTICLES = {
    "/blog/aion-2-boty-rmt-4996-kont-11-pazdziernika",
    "/blog/aion-2-nowe-serwery-eu-nathara-tassin",
    "/blog/aion-2-rekord-steam-nagrody",
    "/blog/aion-2-start-polska",
    "/blog/aion-2-world-market-world-exchange-25-listopada",
    "/blog/albion-online-dragonfire-patch-5-26-listopada",
    "/blog/alien-colonies-gra-podobna-do-ogame-android",
    "/blog/archeage-chronicles-demo-klasy-walka",
    "/blog/atuty-rozwoj-postaci",
    "/blog/black-desert-poziom-75-exp-8-pazdziernika",
    "/blog/ddo-court-of-strahd",
    "/blog/dnd-online",
    "/blog/eve-online-fractured-skies-dodatek",
    "/blog/eve-online-fractured-skies-jak-zaczac",
    "/blog/guild-wars-afterlife-premiera-cena-unformed",
    "/blog/magia-kregi-czarow",
    "/blog/pantheon-crafting-2027",
    "/blog/runescape-3-nowe-pluginy-listopad-2026",
    "/blog/runescape-pluginy-beta",
    "/blog/vampir-crest-skirmish-listopad-2026",
    "/blog/walka-k20",
    "/blog/wow-forever-alterac-valley-zmiany-25-listopada",
    "/blog/wow-forever-balance-druid-zmiany-25-listopada",
    "/blog/wow-forever-jak-zaczac-tryby",
}


class Document(HTMLParser):
    def __init__(self, source):
        super().__init__()
        self.tags = []
        self.schemas = []
        self.headlines = []
        self._schema = None
        self._headline = None
        self.feed(source)

    def handle_starttag(self, tag, attributes):
        attributes = dict(attributes)
        self.tags.append((tag, attributes))
        if tag == "script" and attributes.get("type") == "application/ld+json":
            self._schema = ""
        if tag == "h1":
            self._headline = ""

    def handle_data(self, data):
        if self._schema is not None:
            self._schema += data
        if self._headline is not None:
            self._headline += data

    def handle_endtag(self, tag):
        if tag == "script" and self._schema is not None:
            self.schemas.append(json.loads(self._schema))
            self._schema = None
        if tag == "h1" and self._headline is not None:
            self.headlines.append(self._headline.strip())
            self._headline = None

    def find(self, tag, **attributes):
        return [attrs for name, attrs in self.tags
                if name == tag and all(attrs.get(key) == value for key, value in attributes.items())]


class SEOConfigTests(unittest.TestCase):
    def test_new_blog_documents_have_all_four_language_versions(self):
        originals = {page.path: page for page in (seo.BLOG_PAGE, *seo.ALL_BLOG_ARTICLES)}
        pages = {page.path: page for page in seo.PUBLIC_PAGES}
        self.assertEqual(set(seo.BLOG_INDEXES), {"pl", "en", "es", "pt-BR"})
        for tag in ("en", "es", "pt-BR"):
            filename = f"blog_{tag.lower().replace('-', '_')}.json"
            metadata = json.loads((ROOT / "server" / filename).read_text(encoding="utf-8"))
            allowed_missing = set() if tag == "en" else LEGACY_BILINGUAL_ARTICLES
            self.assertLessEqual(originals.keys() - metadata.keys(), allowed_missing, filename)
            self.assertLessEqual(metadata.keys(), originals.keys(), filename)
            self.assertEqual(len({entry["path"] for entry in metadata.values()}), len(metadata))
            for path, entry in metadata.items():
                with self.subTest(path=path, language=tag):
                    original, translated = originals[path], pages[entry["path"]]
                    self.assertEqual(translated.language, tag)
                    self.assertTrue(translated.path.startswith(f"/{tag.lower()}/blog"))
                    self.assertEqual(translated.published_date, original.published_date)
                    self.assertEqual(translated.article_kind, original.article_kind)
                    self.assertNotEqual(translated.title, original.title)
                    self.assertNotEqual(translated.description, original.description)
                    self.assertEqual(seo.BLOG_LANGUAGE_PATHS[path][tag], translated.path)

    def test_vampir_class_guide_titles_cover_the_target_query(self):
        versions = seo.BLOG_LANGUAGE_PATHS["/blog/vampir-swiat-klasy-mechaniki"]
        self.assertEqual(set(versions), {"pl", "en", "es", "pt-BR"})
        pages = {page.path: page for page in seo.PUBLIC_PAGES}
        for path in versions.values():
            with self.subTest(path=path):
                self.assertIn("best class in vampir", pages[path].title)
                self.assertIn("best class in vampir", pages[path].name)

    def test_normalized_origins(self):
        for given, expected in {
            " https://EXAMPLE.org:443/ ": "https://example.org",
            "http://localhost:8080": "http://localhost:8080",
            "http://127.0.0.1:80/": "http://127.0.0.1",
            "https://[2001:db8::1]:444/": "https://[2001:db8::1]:444",
            "https://żółw.pl/": "https://xn--w-uga1v8h.pl",
        }.items():
            with self.subTest(origin=given):
                self.assertEqual(seo.public_origin(given), expected)

    def test_reject_unsafe_or_non_origin_configuration(self):
        for origin in (None, "", "javascript:alert(1)", "//example.org", "https://user:pass@example.org",
                       "https://example.org/path", "https://example.org/?q=1", "https://example.org/#x",
                       "https://example.org?", "https://example.org#", "https://example.org:70000",
                       "https://example.org\\evil", "https://exa mple.org", "https://example.org\nx",
                       'https://evil\".example.org', "https://[fe80::1%25eth0]"):
            with self.subTest(origin=origin):
                self.assertEqual(seo.public_origin(origin), seo.DEFAULT_ORIGIN)

    def test_verification_token_cannot_add_markup(self):
        token = '"><script>alert(1)</script>&'
        output = seo.metadata_head(seo.SEOConfig(google_verification=token))
        document = Document(output)
        self.assertEqual(document.find("meta", name="google-site-verification")[0]["content"], token)
        self.assertEqual(len(document.find("script")), 1)
        self.assertNotIn("<script>alert(1)</script>", output)

    def test_structured_data_escapes_script_terminators(self):
        page = seo.PublicPage("/example", "example.html", "</script><script>alert(1)</script>",
                              "A & B < C", "Example")
        output = seo.metadata_head(seo.SEOConfig(), page)
        document = Document(output)
        self.assertEqual(len(document.find("script")), 1)
        self.assertEqual(document.schemas[0]["@graph"][0]["name"], page.title)
        self.assertNotIn("<script>alert(1)</script>", output)

    def test_news_uses_only_its_explicit_image_without_game_topic_fallback(self):
        page = replace(seo.NEWS_ARTICLES[0], image=None)
        document = Document(seo.metadata_head(seo.SEOConfig(), page))
        graph = document.schemas[0]["@graph"]
        article = next(item for item in graph if item["@type"] == "NewsArticle")
        webpage = next(item for item in graph if item["@type"] == "WebPage")
        self.assertNotIn("image", article)
        self.assertNotIn("primaryImageOfPage", webpage)
        self.assertNotIn("about", webpage)
        self.assertFalse(document.find("meta", property="og:image"))
        self.assertFalse(document.find("meta", name="twitter:image"))
        self.assertEqual(document.find("meta", name="twitter:card")[0]["content"], "summary")

        image = seo.PageImage("/assets/news/strahd.webp", "Ravenloft — widok zamku", 1600, 900)
        page = replace(page, image=image)
        document = Document(seo.metadata_head(seo.SEOConfig(), page))
        graph = document.schemas[0]["@graph"]
        article = next(item for item in graph if item["@type"] == "NewsArticle")
        webpage = next(item for item in graph if item["@type"] == "WebPage")
        image_object = next(item for item in graph if item["@type"] == "ImageObject")
        self.assertEqual(article["image"], seo.DEFAULT_ORIGIN + image.path)
        self.assertEqual(image_object["url"], article["image"])
        self.assertEqual(webpage["primaryImageOfPage"]["@id"], image_object["@id"])
        self.assertNotIn("about", webpage)
        self.assertEqual(document.find("meta", name="twitter:card")[0]["content"], "summary_large_image")
        self.assertEqual(document.find("meta", property="og:image:type")[0]["content"], "image/webp")


class SEOHTTPTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.origin = "https://example.org"
        with patch.dict("os.environ", {"PUBLIC_SITE_URL": self.origin,
                                       "GOOGLE_SITE_VERIFICATION": "seo-test-token"}):
            self.client = TestClient(TestServer(create_app(":memory:")))
        await self.client.start_server()

    async def asyncTearDown(self):
        await self.client.close()

    async def test_public_pages_are_rendered_with_unique_metadata(self):
        titles = set()
        descriptions = set()
        for page in seo.PUBLIC_PAGES:
            with self.subTest(path=page.path):
                response = await self.client.get(page.path + "?utm_source=test", headers={"Host": "untrusted.example"})
                self.assertEqual(response.status, 200)
                self.assertEqual(response.content_type, "text/html")
                self.assertEqual(response.headers["Content-Language"], page.language)
                self.assertNotIn("X-Robots-Tag", response.headers)
                source = await response.text()
                document = Document(source)
                self.assertNotIn(seo.HEAD_MARKER, source)
                self.assertEqual(len(document.find("title")), 1)
                self.assertIn("<title>" + escape(page.title) + "</title>", source)
                self.assertEqual(len(document.find("h1")), 1)
                self.assertEqual(document.find("html")[0]["lang"], page.language)
                description = document.find("meta", name="description")
                self.assertEqual([meta["content"] for meta in description], [page.description])
                self.assertEqual(document.find("link", rel="canonical"),
                                 [{"rel": "canonical", "href": self.origin + page.path}])
                self.assertEqual(document.find("meta", property="og:url")[0]["content"], self.origin + page.path)
                self.assertEqual(document.find("meta", property="og:title")[0]["content"], page.title)
                self.assertEqual(document.find("meta", name="twitter:card")[0]["content"],
                                 "summary" if page.article_kind == "NewsArticle" and not page.image
                                 else "summary_large_image")
                self.assertEqual(len(document.find("meta", name="robots")), 1)
                self.assertEqual(len(document.schemas), 1)
                graph = document.schemas[0]["@graph"]
                webpage = next(item for item in graph if item["@type"] == "WebPage")
                self.assertEqual(webpage["url"], self.origin + page.path)
                self.assertEqual(webpage["inLanguage"], seo.PUBLIC_LANGUAGES[page.language].tag)
                self.assertEqual(webpage["isPartOf"]["@id"], self.origin + "/#website")
                if page.path != "/":
                    breadcrumbs = next(item for item in graph if item["@type"] == "BreadcrumbList")
                    expected_paths = ["/"]
                    if page.published_date:
                        expected_paths.append(seo.BLOG_INDEXES[page.language].path)
                    expected_paths.append(page.path)
                    self.assertEqual([item["item"] for item in breadcrumbs["itemListElement"]],
                                     [self.origin + path for path in expected_paths])
                titles.add(page.title)
                descriptions.add(page.description)
        self.assertEqual(len(titles), len(seo.PUBLIC_PAGES))
        self.assertEqual(len(descriptions), len(seo.PUBLIC_PAGES))

    async def test_blog_index_collection_links_to_every_published_article(self):
        for language, index in seo.BLOG_INDEXES.items():
            published = seo.BLOG_ARTICLES_BY_LANGUAGE[language]
            with self.subTest(path=index.path):
                response = await self.client.get(index.path)
                self.assertEqual(response.status, 200)
                document = Document(await response.text())
                graph = document.schemas[0]["@graph"]
                webpage = next(item for item in graph if item["@type"] == "WebPage")
                collection = next(item for item in graph if item["@type"] == "CollectionPage")
                articles = next(item for item in graph if item["@type"] == "ItemList")
                self.assertEqual(webpage["mainEntity"]["@id"], collection["@id"])
                self.assertEqual(collection["url"], self.origin + index.path)
                self.assertEqual(collection["inLanguage"], seo.PUBLIC_LANGUAGES[language].tag)
                self.assertEqual(document.headlines, [index.name])
                self.assertEqual(collection["mainEntity"]["@id"], articles["@id"])
                self.assertEqual(document.find("meta", property="og:type")[0]["content"], "website")
                self.assertEqual([item["url"] for item in articles["itemListElement"]],
                                 [self.origin + page.path for page in published])
                self.assertEqual([item["position"] for item in articles["itemListElement"]],
                                 list(range(1, len(published) + 1)))
                visible_links = {link.get("href") for link in document.find("a")}
                self.assertTrue({page.path for page in published}.issubset(visible_links))
                self.assertFalse(any(item["@type"] in ("BlogPosting", "NewsArticle") for item in graph))

    async def test_article_schema_matches_visible_headline_author_date_and_breadcrumbs(self):
        for page in (page for page in seo.PUBLIC_PAGES if page.published_date):
            with self.subTest(path=page.path):
                response = await self.client.get(page.path)
                self.assertEqual(response.status, 200)
                source = await response.text()
                document = Document(source)
                graph = document.schemas[0]["@graph"]
                webpage = next(item for item in graph if item["@type"] == "WebPage")
                article = next(item for item in graph if item["@type"] == page.article_kind)
                breadcrumbs = next(item for item in graph if item["@type"] == "BreadcrumbList")
                self.assertEqual(article["headline"], page.name)
                language = seo.PUBLIC_LANGUAGES[page.language]
                self.assertEqual(article["inLanguage"], language.tag)
                self.assertEqual(document.headlines, [article["headline"]])
                self.assertEqual(article["url"], self.origin + page.path)
                self.assertEqual(article["mainEntityOfPage"]["@id"], webpage["@id"])
                self.assertEqual(webpage["mainEntity"]["@id"], article["@id"])
                self.assertEqual(article["datePublished"], page.published_date)
                if page.modified_date:
                    self.assertEqual(article["dateModified"], page.modified_date)
                    self.assertTrue(document.find("time", datetime=page.modified_date))
                    self.assertEqual(document.find("meta", property="article:modified_time")[0]["content"],
                                     page.modified_date)
                else:
                    self.assertNotIn("dateModified", article)
                self.assertTrue(document.find("time", datetime=article["datePublished"]))
                self.assertEqual(article["author"], {"@type": "Organization",
                                 "name": language.author, "url": self.origin + "/"})
                self.assertEqual(article["publisher"], article["author"])
                self.assertIn(article["author"]["name"], source)
                if page.article_kind == "NewsArticle":
                    self.assertNotIn("about", webpage)
                else:
                    self.assertEqual(webpage["about"]["@id"], self.origin + "/#game")
                if page.image:
                    self.assertEqual(article["image"], self.origin + page.image.path)
                    self.assertEqual(webpage["primaryImageOfPage"]["@id"], self.origin + page.path + "#image")
                elif page.article_kind == "NewsArticle":
                    self.assertNotIn("image", article)
                    self.assertNotIn("primaryImageOfPage", webpage)
                    self.assertFalse(document.find("meta", property="og:image"))
                    self.assertFalse(document.find("meta", name="twitter:image"))
                else:
                    self.assertEqual(article["image"], self.origin + seo.IMAGE_PATH)
                self.assertEqual(article["articleSection"], page.category)
                self.assertEqual(document.find("meta", property="og:type")[0]["content"], "article")
                self.assertEqual(document.find("meta", property="article:published_time")[0]["content"],
                                 article["datePublished"])
                self.assertEqual([item["position"] for item in breadcrumbs["itemListElement"]], [1, 2, 3])
                self.assertEqual([item["item"] for item in breadcrumbs["itemListElement"]],
                                 [self.origin + "/", self.origin + seo.BLOG_INDEXES[page.language].path,
                                  self.origin + page.path])
                if page.language != "pl":
                    original_url = self.origin + seo.BLOG_LANGUAGE_PATHS[page.path]["pl"]
                    self.assertEqual(article["translationOfWork"]["url"], original_url)

    async def test_article_image_matches_visible_figure_metadata_and_public_asset(self):
        for page in (page for page in seo.PUBLIC_PAGES if page.published_date):
            if page.image is None:
                continue
            with self.subTest(path=page.path):
                response = await self.client.get(page.path)
                self.assertEqual(response.status, 200)
                document = Document(await response.text())
                visible_images = document.find("img", src=page.image.path)
                self.assertTrue(visible_images, "The article image must be visible in the document")
                self.assertEqual(visible_images[0]["alt"], page.image.alt)
                image_url = self.origin + page.image.path
                self.assertEqual(document.find("meta", property="og:image")[0]["content"], image_url)
                self.assertEqual(document.find("meta", property="og:image:alt")[0]["content"], page.image.alt)
                self.assertEqual(document.find("meta", property="og:image:type")[0]["content"], page.image.mime_type)
                self.assertEqual(document.find("meta", property="og:image:width")[0]["content"], str(page.image.width))
                self.assertEqual(document.find("meta", property="og:image:height")[0]["content"], str(page.image.height))
                self.assertEqual(document.find("meta", name="twitter:image")[0]["content"], image_url)
                self.assertEqual(document.find("meta", name="twitter:image:alt")[0]["content"], page.image.alt)
                image_object = next(item for item in document.schemas[0]["@graph"]
                                    if item["@type"] == "ImageObject")
                self.assertEqual(image_object["@id"], self.origin + page.path + "#image")
                self.assertEqual(image_object["url"], image_url)
                self.assertEqual(image_object["contentUrl"], image_url)
                self.assertEqual(image_object["caption"], page.image.alt)
                self.assertEqual(image_object["width"], page.image.width)
                self.assertEqual(image_object["height"], page.image.height)
                self.assertEqual(image_object["encodingFormat"], page.image.mime_type)
                asset = await self.client.get(page.image.path)
                self.assertEqual(asset.status, 200)
                self.assertEqual(asset.content_type, page.image.mime_type)
                self.assertNotIn("X-Robots-Tag", asset.headers)
                self.assertTrue(await asset.read())

    async def test_blog_languages_have_reciprocal_alternates_and_visible_switches(self):
        for page in seo.PUBLIC_PAGES:
            variants = seo.BLOG_LANGUAGE_PATHS.get(page.path)
            if not variants:
                continue
            with self.subTest(path=page.path):
                other_language = "pl" if page.language == "en" else "en"
                response = await self.client.get(page.path, headers={"Accept-Language": other_language})
                self.assertEqual(response.status, 200)
                self.assertEqual(response.headers["Content-Language"], page.language)
                document = Document(await response.text())
                alternates = document.find("link", rel="alternate")
                self.assertEqual(len(alternates), len(variants))
                self.assertEqual({link["hreflang"]: link["href"] for link in alternates},
                                 {tag: self.origin + target for tag, target in variants.items()})
                self.assertEqual({link["content"] for link in document.find("meta", property="og:locale:alternate")},
                                 {seo.PUBLIC_LANGUAGES[tag].open_graph for tag in variants if tag != page.language})
                self.assertEqual(seo.BLOG_LANGUAGE_PATHS[variants["pl"]], variants)
                for tag, target in variants.items():
                    switches = document.find("a", href=target, hreflang=tag, lang=tag)
                    self.assertTrue(switches, "The language switch must link to the equivalent article or index")
                    self.assertEqual(switches[0].get("aria-current"), "true" if tag == page.language else None)
                locale = seo.PUBLIC_LANGUAGES[page.language]
                self.assertTrue(document.find("nav", **{"aria-label": locale.navigation_label}))
                self.assertTrue(document.find("a", **{"aria-label": locale.home_label}))
                self.assertIn(locale.blog_label, seo.public_header(page))
                self.assertIn(locale.count_label, seo.public_header(page))

    async def test_blog_navigation_uses_registered_locale_paths_and_fragments(self):
        pages = {page.path: page for page in seo.PUBLIC_PAGES if page.path in seo.BLOG_LANGUAGE_PATHS}
        blog_prefixes = tuple(index.path + "/" for index in seo.BLOG_INDEXES.values())
        documents = {}
        for path in pages:
            response = await self.client.get(path)
            self.assertEqual(response.status, 200)
            documents[path] = Document(await response.text())
        internal_hosts = {urlsplit(self.origin).netloc, urlsplit(seo.DEFAULT_ORIGIN).netloc}
        for page in pages.values():
            for link in documents[page.path].find("a"):
                href = link.get("href", "")
                target = urlsplit(urljoin(self.origin + page.path, href))
                if target.netloc not in internal_hosts:
                    continue
                with self.subTest(page=page.path, href=href):
                    if target.path not in pages:
                        self.assertFalse(target.path.startswith(blog_prefixes), "Unknown article URL")
                        continue
                    destination = pages[target.path]
                    if destination.language != page.language:
                        self.assertEqual(link.get("hreflang"), destination.language)
                        if link.get("lang"):
                            self.assertEqual(target.path, seo.BLOG_LANGUAGE_PATHS[page.path][destination.language])
                        else:
                            self.assertNotIn(page.language, seo.BLOG_LANGUAGE_PATHS[destination.path])
                    if target.fragment:
                        target_document = documents[target.path]
                        ids = {attrs.get("id") for _, attrs in target_document.tags}
                        ids.update(anchor.get("name") for anchor in target_document.find("a"))
                        self.assertIn(target.fragment, ids, "The destination must retain its link anchor")

    async def test_translations_preserve_article_images_with_localized_descriptions(self):
        pages = {page.path: page for page in seo.PUBLIC_PAGES}
        for page in seo.PUBLIC_PAGES:
            if page.language == "pl" or (not page.published_date and page.language != "en"):
                continue
            polish = pages[seo.BLOG_LANGUAGE_PATHS[page.path]["pl"]]
            with self.subTest(path=page.path):
                polish_response = await self.client.get(polish.path)
                translated_response = await self.client.get(page.path)
                self.assertEqual(translated_response.status, 200)
                polish_images = Document(await polish_response.text()).find("img")
                translated_images = Document(await translated_response.text()).find("img")
                self.assertEqual([image.get("src") for image in translated_images],
                                 [image.get("src") for image in polish_images])
                for original, translated in zip(polish_images, translated_images):
                    self.assertTrue(translated.get("alt", "").strip(), "Content images need descriptive localized alt text")
                    self.assertNotEqual(translated["alt"], original["alt"])
                    self.assertEqual(translated.get("srcset"), original.get("srcset"))
                    sources = [translated["src"]]
                    sources.extend(item.strip().split()[0] for item in translated.get("srcset", "").split(",") if item.strip())
                    for source in sources:
                        if source.startswith("/"):
                            self.assertTrue((ROOT / "web" / source.lstrip("/")).is_file(), source)

    async def test_raw_blog_index_aliases_cannot_be_indexed_as_duplicates(self):
        for index in seo.BLOG_INDEXES.values():
            with self.subTest(path=index.path):
                response = await self.client.get(index.path + "/index.html", allow_redirects=False)
                if response.status in (301, 308):
                    self.assertEqual(response.headers["Location"], index.path)
                else:
                    self.assertIn(response.status, (200, 404))
                    self.assertIn("noindex", response.headers.get("X-Robots-Tag", ""))
                    if response.status == 200:
                        document = Document(await response.text())
                        self.assertEqual(document.find("link", rel="canonical"),
                                         [{"rel": "canonical", "href": self.origin + index.path}])

    async def test_sitemap_lists_only_successful_canonical_documents(self):
        response = await self.client.get("/sitemap.xml")
        self.assertEqual(response.status, 200)
        self.assertEqual(response.content_type, "application/xml")
        root = ET.fromstring(await response.text())
        locations = [element.text for element in root.findall("{*}url/{*}loc")]
        self.assertEqual(locations, [self.origin + page.path for page in seo.PUBLIC_PAGES])
        self.assertEqual(len(locations), len(set(locations)))
        self.assertEqual([element.text for element in root.findall("{*}url/{*}lastmod")],
                         [page.modified_date for page in seo.PUBLIC_PAGES if page.modified_date])
        image_namespace = "http://www.google.com/schemas/sitemap-image/1.1"
        for element, page in zip(root.findall("{*}url"), seo.PUBLIC_PAGES):
            with self.subTest(path=page.path):
                image_locations = [image.text for image in element.findall(
                    "{" + image_namespace + "}image/{" + image_namespace + "}loc")]
                self.assertEqual(image_locations,
                                 [self.origin + page.image.path] if page.image else [])
        for location in locations:
            result = await self.client.head(urlsplit(location).path)
            self.assertEqual(result.status, 200)
            self.assertNotIn("X-Robots-Tag", result.headers)

    async def test_duplicate_paths_permanently_redirect_preserving_query(self):
        aliases = [("/index.html", "/")]
        for page in seo.PUBLIC_PAGES[1:]:
            aliases.extend([(page.path + "/", page.path), (page.path + ".html", page.path)])
        for alias, canonical in aliases:
            with self.subTest(path=alias):
                response = await self.client.get(alias + "?utm_source=test", allow_redirects=False)
                self.assertEqual(response.status, 301)
                self.assertEqual(response.headers["Location"], canonical + "?utm_source=test")

    async def test_robots_allows_crawling_noindex_and_render_resources(self):
        response = await self.client.get("/robots.txt")
        self.assertEqual(response.status, 200)
        self.assertEqual(response.content_type, "text/plain")
        text = await response.text()
        self.assertIn("User-agent: *\nAllow: /", text)
        self.assertNotIn("Disallow:", text)
        self.assertIn("Sitemap: " + self.origin + "/sitemap.xml", text)

    async def test_technical_endpoints_and_errors_are_noindex(self):
        for path, status in (("/health", 200), ("/ranking", 200), ("/auth/google/config", 200),
                             ("/offline.html", 200), ("/missing-page", 404),
                             ("/poradniki/missing-guide", 404), ("/blog/missing-article", 404),
                             ("/en/blog/missing-article", 404),
                             ("/assets/missing.png", 404)):
            with self.subTest(path=path):
                response = await self.client.get(path)
                self.assertEqual(response.status, status)
                self.assertEqual(response.headers["X-Robots-Tag"], "noindex, nofollow")
        websocket = await self.client.get("/ws")
        # An ordinary HTTP request cannot open the socket; with unconfigured
        # Google authentication the existing game returns 503 before upgrading.
        self.assertGreaterEqual(websocket.status, 400)
        self.assertEqual(websocket.headers["X-Robots-Tag"], "noindex, nofollow")
        response = await self.client.post("/")
        self.assertEqual(response.status, 405)
        self.assertIn("noindex", response.headers["X-Robots-Tag"])

    async def test_gzip_negotiation_head_and_conditional_cache(self):
        languages = {page.path: page.language for page in seo.PUBLIC_PAGES}
        for path in ("/", *(index.path for index in seo.BLOG_INDEXES.values()), "/robots.txt", "/sitemap.xml"):
            with self.subTest(path=path):
                plain = await self.client.get(path, headers={"Accept-Encoding": "identity"})
                source = await plain.read()
                self.assertNotIn("Content-Encoding", plain.headers)
                compressed = await self.client.get(path, headers={"Accept-Encoding": "gzip"}, auto_decompress=False)
                self.assertEqual(compressed.headers["Content-Encoding"], "gzip")
                self.assertEqual(gzip.decompress(await compressed.read()), source)
                self.assertEqual(compressed.headers["ETag"], plain.headers["ETag"])
                self.assertIn("Accept-Encoding", plain.headers["Vary"])
                self.assertIn("Accept-Encoding", compressed.headers["Vary"])
                not_modified = await self.client.get(path, headers={"If-None-Match": plain.headers["ETag"]})
                self.assertEqual(not_modified.status, 304)
                self.assertEqual(await not_modified.read(), b"")
                head = await self.client.head(path, headers={"Accept-Encoding": "identity"})
                self.assertEqual(head.status, 200)
                self.assertEqual(await head.read(), b"")
                self.assertEqual(head.headers["ETag"], plain.headers["ETag"])
                self.assertEqual(int(head.headers["Content-Length"]), len(source))
                if plain.content_type == "text/html":
                    expected_language = languages[path]
                    self.assertEqual(head.headers["Content-Language"], expected_language)
                    self.assertEqual(not_modified.headers["Content-Language"], expected_language)
        for header in ("gzip;q=0", "gzip;q=0, *;q=1", "gzip;q=invalid", "gzip;q=-1"):
            response = await self.client.get("/", headers={"Accept-Encoding": header})
            self.assertNotIn("Content-Encoding", response.headers)

    async def test_public_styles_and_preview_image_are_available(self):
        for path, content_type in (("/landing.css", "text/css"), ("/guide.css", "text/css"),
                                   ("/blog.css", "text/css"),
                                   (seo.IMAGE_PATH, "image/png")):
            response = await self.client.get(path)
            self.assertEqual(response.status, 200)
            self.assertEqual(response.content_type, content_type)
            self.assertNotIn("X-Robots-Tag", response.headers)
            self.assertTrue(await response.read())


if __name__ == "__main__":
    unittest.main()
