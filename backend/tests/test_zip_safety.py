import pytest
from app.services.zip_safety import is_safe_bundle_path


@pytest.mark.parametrize(
    "path,expected",
    [
        ("index.html", True),
        ("slides/01.html", True),
        ("folder/./nested/page.html", False),
        ("../etc/passwd", False),
        ("foo/../../secret", False),
        ("", False),
        ("/abs/path.html", False),
        (r"..\windows\file", False),
        ("normal\\backslash.html", True),
    ],
)
def test_is_safe_bundle_path(path: str, expected: bool) -> None:
    assert is_safe_bundle_path(path) is expected


def test_fuzz_like_paths() -> None:
    bad = [
        "..",
        "a/../b",
        "a//b",
        "....//....//etc/passwd",
    ]
    for p in bad:
        assert is_safe_bundle_path(p) is False
