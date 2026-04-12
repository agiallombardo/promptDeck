"""Minimal single-file HTML seeded before an LLM generation job runs."""

from __future__ import annotations

STARTER_DECK_HTML_BYTES = b"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Starter</title>
</head>
<body>
<section data-slide data-title="Starting slide">
<p>This placeholder will be replaced when AI generation finishes.</p>
</section>
</body>
</html>
"""
