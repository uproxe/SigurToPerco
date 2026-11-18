"""Версия в коде и CHANGELOG.md не должны расходиться."""
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "scripts"))

import release_notes  # noqa: E402


def test_changelog_has_current_version():
    version = release_notes.code_version()
    assert version, "не найден __version__ в sigur_perco/__init__.py"
    assert release_notes.changelog_section(version), "в CHANGELOG.md нет раздела для версии %s" % version


def test_changelog_has_version_link():
    version = release_notes.code_version()
    assert "[%s]: " % version in release_notes.read("CHANGELOG.md")
