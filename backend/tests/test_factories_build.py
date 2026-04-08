from __future__ import annotations

from tests.factories import UserFactory


def test_user_factory_builds_model() -> None:
    u = UserFactory.build()
    assert u.email.endswith("@example.com")
    assert u.role.value == "editor"
