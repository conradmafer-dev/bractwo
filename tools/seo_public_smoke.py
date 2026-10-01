"""Check public SEO pages in Chromium against an isolated in-memory server.

Run: python tools/seo_public_smoke.py --output /tmp/bractwo-seo-browser
Requires Playwright and Chromium. No production requests or credentials.
"""
from __future__ import annotations

import argparse
import asyncio
import json
from pathlib import Path
import shutil
import sys
from urllib.parse import urlsplit

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from aiohttp import web
from playwright.async_api import async_playwright
from server.server import create_app

PAGES = ("/", "/poradniki/jak-zaczac", "/poradniki/klasy-postaci", "/poradniki/swiat-i-wyprawy")


async def main(output):
    output.mkdir(parents=True, exist_ok=True)
    runner = web.AppRunner(create_app(":memory:"))
    await runner.setup()
    site = web.TCPSite(runner, "127.0.0.1", 0)
    await site.start()
    origin = f"http://127.0.0.1:{site._server.sockets[0].getsockname()[1]}"
    results, errors, destinations, assets = [], [], set(), set()
    try:
        async with async_playwright() as playwright:
            browser = await playwright.chromium.launch(executable_path=shutil.which("chromium"), args=["--no-sandbox"])
            try:
                for javascript in (False, True):
                    for width in (1440, 390, 320):
                        context = await browser.new_context(java_script_enabled=javascript, viewport={"width": width, "height": 900})
                        page = await context.new_page()
                        page.on("pageerror", lambda error: errors.append(str(error)))
                        titles, descriptions = set(), set()
                        for path in PAGES:
                            response = await page.goto(origin + path, wait_until="networkidle")
                            assert response.status == 200, (path, response.status)
                            assert await page.locator("html").get_attribute("lang") == "pl"
                            assert await page.locator("h1").count() == 1
                            assert await page.locator("title").count() == 1
                            title = await page.title()
                            assert title and title not in titles, (path, title)
                            titles.add(title)
                            meta = page.locator('meta[name="description"]')
                            assert await meta.count() == 1
                            description = await meta.get_attribute("content")
                            assert description and description not in descriptions
                            descriptions.add(description)
                            canonical = page.locator('link[rel="canonical"]')
                            assert await canonical.count() == 1
                            assert urlsplit(await canonical.get_attribute("href")).path == path
                            assert "noindex" not in await page.locator('meta[name="robots"]').get_attribute("content")
                            structured = await page.locator('script[type="application/ld+json"]').all_text_contents()
                            assert structured and all(json.loads(item)["@graph"] for item in structured)
                            overflow = await page.evaluate("""() => {
                                const main = document.querySelector('#authScreen') || document.documentElement;
                                return main.scrollWidth > main.clientWidth + 1;
                            }""")
                            assert not overflow, (path, width, "horizontal overflow")
                            assert await page.locator("main").inner_text()
                            links = await page.locator('a[href]').evaluate_all("nodes => nodes.map(node => node.getAttribute('href'))")
                            resources = await page.locator('link[href], script[src], img[src]').evaluate_all("nodes => nodes.map(node => node.href || node.src)")
                            assets.update(resource for resource in resources if resource.startswith(origin + "/"))
                            for href in links:
                                if href.startswith("/") and not href.startswith("//"):
                                    destinations.add(href)
                                elif href.startswith("#"):
                                    assert await page.locator(href).count(), (path, href)
                            if path != "/":
                                assert not await page.locator("script[src]").count(), "Guides should not load game code"
                            results.append({"path": path, "width": width, "javascript": javascript, "title": title, "ok": True})
                            if javascript and width in (1440, 390):
                                name = "home" if path == "/" else path.rsplit("/", 1)[1]
                                await page.screenshot(path=str(output / f"{name}-{width}.png"), full_page=path != "/")
                        await context.close()
                for destination in sorted(destinations):
                    response = await browser.new_page()
                    result = await response.goto(origin + destination, wait_until="domcontentloaded")
                    assert result.status == 200, destination
                    fragment = urlsplit(destination).fragment
                    if fragment:
                        assert await response.locator("#" + fragment).count(), destination
                    await response.close()
                client = await playwright.request.new_context()
                try:
                    for asset in sorted(assets):
                        response = await client.get(asset)
                        assert response.status == 200, (asset, response.status)
                finally:
                    await client.dispose()
                assert not errors, errors
            finally:
                await browser.close()
    finally:
        await runner.cleanup()
    report = {"ok": True, "checks": results, "local_links": sorted(destinations),
              "asset_count": len(assets), "javascript_errors": errors,
              "limitations": ["Local Chromium checks only; no production indexing or field Core Web Vitals measurement."]}
    (output / "report.json").write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"PASS: {len(results)} page/viewport/JavaScript checks; {len(destinations)} local links; {len(assets)} assets; no JavaScript errors")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=Path("/tmp/bractwo-seo-browser"))
    asyncio.run(main(parser.parse_args().output))
