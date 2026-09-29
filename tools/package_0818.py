#!/usr/bin/env python3
"""Build both 0.8.18 release ZIPs using only the Python standard library.

Run this file after release documentation and QA reports are final. The two ZIPs
are written beside the project directory. Existing archives are never replaced.
SOURCE_MANIFEST.json in the working tree is neither read nor modified: each ZIP
receives a manifest for its own exact contents, including report references.
"""

from __future__ import annotations

import fnmatch
import hashlib
import json
import os
import stat
import sys
import uuid
import zipfile
from contextlib import ExitStack
from datetime import datetime, timezone
from pathlib import Path, PurePosixPath


VERSION = "0.8.18"
ARCHIVE_STEM = "BRACTWO_0.8.18_UI_19"
MANIFEST_NAME = "SOURCE_MANIFEST.json"
REPORT_DIRECTORY = "docs/qa_0.8.18/"
EXCLUDED_DIRECTORIES = {
    ".qa-python", "__pycache__", ".git", "data", "backups", ".venv",
    "node_modules", ".godot", ".pytest_cache", ".mypy_cache", ".ruff_cache",
}
EXCLUDED_PATTERNS = (
    "*.sqlite*", "*.db*", "credentials*", ".env*", "*.zip", "*.log",
    "*.tmp", "*.pyc", "*.pyo", "*.partial-*", "npm-debug*", "yarn-error*",
    "export_credentials.cfg", "*.keystore",
)
READY_ROOT_PATTERNS = (
    "Dockerfile", "run.py", "requirements.txt", "start_*.sh", "start_*.bat",
    "LICENSE*", "RAILWAY_VARIABLES*", ".gitignore", ".dockerignore", "README.md",
)
REQUIRED_FILES = {
    "server/continent_world.py", "server/adventure_content.py", "server/adventure_combat.py", "server/magic_items.py",
    "web/adventure_ui.js", "web/adventure_ui.css", "web/world_geometry.js", "docs/UI_19_WORLD.md", "docs/qa_0.8.18/ui19/summary.json",
    "Dockerfile", "run.py", "requirements.txt", "README.md", ".gitignore",
    ".dockerignore", "server/server.py", "server/dnd_game.py", "server/discovery_rules.py", "web/index.html",
    "web/game.js", "web/mobile.js", "web/mobile.css", "web/rest_ui.js", "web/rest_ui.css", "web/app_shell.js",
    "web/app_shell.css", "web/manifest.webmanifest", "web/sw.js",
    "web/offline.html", "web/icons/icon-192.png", "web/icons/icon-512.png",
    "web/icons/apple-touch-icon.png", "web/assets/monsters/crocodile.svg", "docs/RELEASE_0.8.18.md",
    "server/rest_rules.py", "server/druid_circles.py", "server/druid_circle_game.py",
    "server/druid_circle_spells.py", "server/druid_beasts.py", "server/environment_rules.py",
    "web/circle_spell_ui.js", "web/circle_vfx.js", "docs/DRUID_CIRCLES_0.8.18.md",
    "web/assets/feats/tough.svg", "web/assets/feats/savage_attacker.svg",
    "web/assets/feats/ability_score_improvement.svg", "web/assets/feats/heavy_armor_master.svg",
    "web/assets/feats/medium_armor_master.svg",
    "docs/HP_0.8.18_UI_12.md",
    "web/hotbar_ui.js", "web/hotbar_ui.css", "docs/HOTBAR_0.8.18_UI_13.md", "docs/UI_16_SPELLBOOK.md", "docs/UI_17_GUIDING_BOLT_GROWTH.md", "docs/UI_18_RESPAWN_CITY.md", "docs/UI_14_DRUID_FULLSCREEN.md", "web/assets/spells/guidance.svg", "web/assets/spells/guiding_bolt.svg",
}


def excluded_name(name: str) -> bool:
    lowered = name.lower()
    return lowered in EXCLUDED_DIRECTORIES or any(
        fnmatch.fnmatchcase(lowered, pattern) for pattern in EXCLUDED_PATTERNS
    )


def is_link_or_reparse(path: Path) -> bool:
    """Do not follow symlinks, Windows junctions or other reparse points."""
    attributes = path.lstat()
    return stat.S_ISLNK(attributes.st_mode) or bool(
        getattr(attributes, "st_file_attributes", 0) & 0x400
    )


def source_files(project: Path) -> list[tuple[str, Path]]:
    selected = []
    for directory, subdirectories, filenames in os.walk(project, followlinks=False):
        current = Path(directory)
        subdirectories[:] = sorted(
            name for name in subdirectories
            if not excluded_name(name) and not is_link_or_reparse(current / name)
        )
        for name in sorted(filenames):
            source = current / name
            if excluded_name(name) or is_link_or_reparse(source) or not source.is_file():
                continue
            source.resolve().relative_to(project)  # Reject paths outside the checkout.
            relative = source.relative_to(project).as_posix()
            if relative == MANIFEST_NAME:
                continue
            selected.append((relative, source))
    return sorted(selected)


def ready_file(relative: str) -> bool:
    parts = PurePosixPath(relative).parts
    if relative.startswith("docs/UI_19_"):return True
    if parts[0] in {"server", "web"}:
        return True
    if len(parts) == 1:
        return any(fnmatch.fnmatchcase(relative, pattern) for pattern in READY_ROOT_PATTERNS)
    if relative in {"docs/RELEASE_0.8.18.md", "docs/DRUID_CIRCLES_0.8.18.md", "docs/HP_0.8.18_UI_12.md", "docs/HOTBAR_0.8.18_UI_13.md", "docs/UI_16_SPELLBOOK.md", "docs/UI_17_GUIDING_BOLT_GROWTH.md", "docs/UI_18_RESPAWN_CITY.md", "docs/UI_14_DRUID_FULLSCREEN.md"}:
        return True
    if relative.startswith((REPORT_DIRECTORY + "ui17/", REPORT_DIRECTORY + "ui19/")):
        return PurePosixPath(relative).suffix.lower() in {".json", ".txt"}
    return (
        len(parts) == 3 and relative.startswith(REPORT_DIRECTORY)
        and PurePosixPath(relative).suffix.lower() in {".json", ".txt"}
    )


def manifest_bytes(kind: str, prefix: str, hashes: dict[str, str], built_at: str) -> bytes:
    reports = sorted(
        name for name in hashes
        if name.startswith(REPORT_DIRECTORY)
        and PurePosixPath(name).suffix.lower() in {".json", ".txt"}
    )
    manifest = {
        "version": VERSION,
        "based_on": "BRACTWO_0.8.18_UI_18_FULL_SOURCE.zip",
        "ui_revision": "UI_19",
        "built_at": built_at,
        "package": kind,
        "archive_root": prefix,
        "release_notes": "docs/UI_19_WORLD.md",
        "hash_algorithm": "SHA-256",
        "hash_scope": "Exact uncompressed bytes of every packaged file except SOURCE_MANIFEST.json; file keys are relative to archive_root.",
        "tests": {
            "reports": reports,
            "current_revision_directory": "docs/qa_0.8.18/ui19/",
            "current_revision_summary": "docs/qa_0.8.18/ui19/summary.json",
            "status": "Consult the included reports. The packager does not infer test counts or success.",
        },
        "packaged_file_count": len(hashes) + 1,
        "files": dict(sorted(hashes.items())),
    }
    return (json.dumps(manifest, ensure_ascii=False, indent=2) + "\n").encode("utf-8")


def zip_entry(name: str) -> zipfile.ZipInfo:
    entry = zipfile.ZipInfo(name, datetime.now().timetuple()[:6])
    entry.compress_type = zipfile.ZIP_DEFLATED
    # Consistent content permissions; shell launchers retain executable mode.
    entry.create_system = 3
    mode = 0o755 if name.endswith(".sh") else 0o644
    entry.external_attr = (stat.S_IFREG | mode) << 16
    return entry


def verify_archive(archive: Path, prefix: str) -> dict:
    """Read every archived byte back and compare to the per-package manifest."""
    with zipfile.ZipFile(archive, "r") as package:
        entries = package.namelist()
        if len(entries) != len(set(entries)):
            raise RuntimeError(f"Duplicate ZIP entries: {archive.name}")
        manifest = json.loads(package.read(prefix + MANIFEST_NAME))
        expected = {prefix + name for name in manifest["files"]}
        expected.add(prefix + MANIFEST_NAME)
        if set(entries) != expected or len(entries) != manifest["packaged_file_count"]:
            raise RuntimeError(f"ZIP contents differ from manifest: {archive.name}")
        for relative, expected_hash in manifest["files"].items():
            digest = hashlib.sha256()
            with package.open(prefix + relative) as member:
                while chunk := member.read(1024 * 1024):
                    digest.update(chunk)
            if digest.hexdigest() != expected_hash:
                raise RuntimeError(f"ZIP hash mismatch: {relative}")
        return manifest


def build() -> list[dict]:
    project = Path(__file__).resolve().parent.parent
    workspace = project.parent
    specs = (
        ("full_source", "Bractwo_0.8.18/", ARCHIVE_STEM + "_FULL_SOURCE.zip"),
        ("railway_github_ready", "", ARCHIVE_STEM + "_RAILWAY_GITHUB_READY.zip"),
    )
    destinations = [workspace / filename for _, _, filename in specs]
    for destination in destinations:
        if destination.exists():
            raise FileExistsError(f"Archive already exists; refusing to replace it: {destination}")

    files = source_files(project)
    names = {relative for relative, _ in files}
    missing = REQUIRED_FILES - names
    if missing:
        raise RuntimeError("Required release files are missing: " + ", ".join(sorted(missing)))
    if not any(name.startswith(REPORT_DIRECTORY) and ready_file(name) for name in names):
        raise RuntimeError("No final .json/.txt QA reports found under " + REPORT_DIRECTORY)
    if not all(ready_file(name) for name in REQUIRED_FILES):
        raise RuntimeError("A required release file was excluded from the ready package")

    token = uuid.uuid4().hex
    temporary = [workspace / (path.name + ".partial-" + token) for path in destinations]
    hashes: list[dict[str, str]] = [{}, {}]
    published: list[Path] = []
    built_at = datetime.now(timezone.utc).isoformat()
    try:
        with ExitStack() as stack:
            archives = [
                stack.enter_context(zipfile.ZipFile(path, "x", compression=zipfile.ZIP_DEFLATED, compresslevel=6))
                for path in temporary
            ]
            for relative, source in files:
                package_indexes = (0, 1) if ready_file(relative) else (0,)
                digest = hashlib.sha256()
                before = source.stat()
                # The same chunks feed both ZIPs and SHA-256. Shared files cannot
                # diverge between packages if a working file changes mid-build.
                with ExitStack() as members:
                    outputs = [members.enter_context(archives[i].open(zip_entry(specs[i][1] + relative), "w")) for i in package_indexes]
                    with source.open("rb") as input_file:
                        while chunk := input_file.read(1024 * 1024):
                            digest.update(chunk)
                            for output in outputs:
                                output.write(chunk)
                after = source.stat()
                if (before.st_size, before.st_mtime_ns, before.st_ino) != (after.st_size, after.st_mtime_ns, after.st_ino):
                    raise RuntimeError(f"Source changed while packaging; wait for edits/tests to finish: {relative}")
                for index in package_indexes:
                    hashes[index][relative] = digest.hexdigest()

            for i, (kind, prefix, _) in enumerate(specs):
                archives[i].writestr(zip_entry(prefix + MANIFEST_NAME), manifest_bytes(kind, prefix, hashes[i], built_at))

        verified = [verify_archive(path, specs[i][1]) for i, path in enumerate(temporary)]
        # Hard-link publication is atomic and refuses a destination created by
        # another process, on both Windows and Unix. No old ZIP is overwritten.
        for temporary_path, destination in zip(temporary, destinations):
            os.link(temporary_path, destination)
            published.append(destination)
        return [
            {"archive": str(path), "bytes": path.stat().st_size,
             "files": verified[i]["packaged_file_count"], "sha256_verified": True,
             "reports": verified[i]["tests"]["reports"]}
            for i, path in enumerate(destinations)
        ]
    except BaseException:
        # Only exact output paths successfully created by this run are removed.
        for path in published:
            path.unlink(missing_ok=True)
        raise
    finally:
        for path in temporary:
            path.unlink(missing_ok=True)


if __name__ == "__main__":
    try:
        print(json.dumps(build(), ensure_ascii=False, indent=2))
    except (OSError, RuntimeError, zipfile.BadZipFile) as error:
        print(f"Package build failed: {error}", file=sys.stderr)
        raise SystemExit(1)
