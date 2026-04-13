from app.services.slide_manifest import build_slide_manifest


def test_manifest_detects_data_slide_nodes() -> None:
    html = b"""<!doctype html><html><body>
    <section data-slide data-title="One"></section>
    <section data-slide data-title="Two"></section>
    </body></html>"""
    manifest = build_slide_manifest(html)
    assert len(manifest) == 2
    assert manifest[0]["selector"] == "[data-slide]"
    assert manifest[0]["title"] == "One"


def test_manifest_detects_slide_class_articles() -> None:
    html = b"""<!doctype html><html><body><main>
    <article class="slide" title="A"></article>
    <article class="slide" title="B"></article>
    <article class="slide" title="C"></article>
    </main></body></html>"""
    manifest = build_slide_manifest(html)
    assert len(manifest) == 3
    assert manifest[0]["selector"] == "main > article.slide"
    assert manifest[1]["title"] == "B"


def test_manifest_uses_counter_fallback_when_no_slide_nodes() -> None:
    html = b"""<!doctype html><html><body>
    <div class="chrome">1 / 6</div>
    <div>not a slide container</div>
    </body></html>"""
    manifest = build_slide_manifest(html)
    assert len(manifest) == 6
    assert manifest[0]["selector"] == "virtual-counter"
