from __future__ import annotations

import re

_MANAGED_ATTR = r'data-promptdeck-managed\s*=\s*["\']{value}["\']'
_MANAGED_CSS_RE = re.compile(
    rf"<style\b(?=[^>]*{_MANAGED_ATTR.format(value='code-css')})[^>]*>(.*?)</style>",
    re.IGNORECASE | re.DOTALL,
)
_MANAGED_JS_RE = re.compile(
    rf"<script\b(?=[^>]*{_MANAGED_ATTR.format(value='code-js')})[^>]*>(.*?)</script>",
    re.IGNORECASE | re.DOTALL,
)


def extract_managed_code(html: str) -> tuple[str, str]:
    css_match = _MANAGED_CSS_RE.search(html)
    js_match = _MANAGED_JS_RE.search(html)
    css = css_match.group(1).strip() if css_match else ""
    js = js_match.group(1).strip() if js_match else ""
    return css, js


def merge_managed_code(
    *,
    html: str,
    css: str,
    js: str,
) -> str:
    merged = _MANAGED_CSS_RE.sub("", html)
    merged = _MANAGED_JS_RE.sub("", merged)

    css_value = css.strip()
    if css_value:
        css_block = f'<style data-promptdeck-managed="code-css">\n{css_value}\n</style>'
        merged = _insert_before_tag(merged, "head", css_block)

    js_value = js.strip()
    if js_value:
        js_block = f'<script data-promptdeck-managed="code-js">\n{js_value}\n</script>'
        merged = _insert_before_tag(merged, "body", js_block)

    return merged


def _insert_before_tag(html: str, tag: str, block: str) -> str:
    close_tag = re.compile(rf"</{tag}\s*>", re.IGNORECASE)
    match = close_tag.search(html)
    if match is None:
        return f"{html.rstrip()}\n{block}\n"
    before = html[: match.start()].rstrip()
    after = html[match.start() :]
    return f"{before}\n{block}\n{after}"
