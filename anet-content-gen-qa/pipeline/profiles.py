"""
Workspaces by person.
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Everyone works on the same content library but keeps their own workspace, so
drafts don't collide and finished work carries a name.

    output/
      profiles.json                      the roster
      mikayla/                            one folder per person
        va-grade3-unit8-lesson15/         lessons, exactly as before

This is separation and attribution, not access control: the roster is a
plain list and anyone using the app can select any name on it. That is the
agreed design — a collaborating team that wants its own desks — and it must
not be described to anyone as privacy.

A name is stored once. Matching is case- and whitespace-insensitive so
"mikayla", "Mikayla" and " Mikayla " are the same person, and the display
name keeps whatever capitalisation was typed first.
"""

from __future__ import annotations

import datetime
import json
import pathlib
import re
import shutil


ROSTER_NAME = "profiles.json"


def _roster_path(output_root: pathlib.Path) -> pathlib.Path:
    return pathlib.Path(output_root) / ROSTER_NAME


def slugify_name(name: str) -> str:
    s = re.sub(r"[^a-z0-9]+", "-", (name or "").strip().lower()).strip("-")
    return s or "unnamed"


def normalize(name: str) -> str:
    """The key two names are compared on."""
    return re.sub(r"\s+", " ", (name or "").strip()).casefold()


def load_profiles(output_root: pathlib.Path) -> list:
    p = _roster_path(output_root)
    if not p.exists():
        return []
    try:
        data = json.loads(p.read_text(encoding="utf-8"))
    except Exception:
        return []
    items = data.get("profiles", []) if isinstance(data, dict) else []
    return [x for x in items if isinstance(x, dict) and x.get("name") and x.get("slug")]


def save_profiles(output_root: pathlib.Path, profiles: list) -> None:
    p = _roster_path(output_root)
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps({"profiles": profiles}, indent=2), encoding="utf-8")


def find_profile(profiles: list, name: str) -> dict | None:
    key = normalize(name)
    return next((x for x in profiles if normalize(x["name"]) == key), None)


def add_profile(output_root: pathlib.Path, name: str) -> tuple:
    """(profile, error). Refuses blanks and anyone already on the roster."""
    clean = re.sub(r"\s+", " ", (name or "").strip())
    if not clean:
        return None, "Enter a name."
    if len(clean) > 60:
        return None, "That name is too long (60 characters max)."

    profiles = load_profiles(output_root)
    existing = find_profile(profiles, clean)
    if existing is not None:
        return None, f"“{existing['name']}” is already on the list — pick that name instead."

    slug = slugify_name(clean)
    taken = {x["slug"] for x in profiles}
    if slug in taken:                                  # different name, same slug
        n = 2
        while f"{slug}-{n}" in taken:
            n += 1
        slug = f"{slug}-{n}"

    profile = {
        "name": clean,
        "slug": slug,
        "created": datetime.datetime.now().isoformat(timespec="seconds"),
    }
    profiles.append(profile)
    profiles.sort(key=lambda x: normalize(x["name"]))
    save_profiles(output_root, profiles)
    workspace_dir(output_root, profile).mkdir(parents=True, exist_ok=True)
    return profile, None


def workspace_dir(output_root: pathlib.Path, profile: dict) -> pathlib.Path:
    return pathlib.Path(output_root) / profile["slug"]


def legacy_lesson_dirs(output_root: pathlib.Path) -> list:
    """Lesson folders sitting directly under output/ from before workspaces
    existed. A lesson folder is identifiable by its identity.json; a
    workspace folder never has one."""
    root = pathlib.Path(output_root)
    if not root.exists():
        return []
    known = {x["slug"] for x in load_profiles(root)}
    return sorted(
        d for d in root.iterdir()
        if d.is_dir() and d.name not in known and (d / "identity.json").exists()
    )


def adopt_legacy_lessons(output_root: pathlib.Path, profile: dict) -> list:
    """Move pre-workspace lessons into a workspace. Returns what moved.
    Never overwrites: a name already present in the destination is skipped."""
    dest = workspace_dir(output_root, profile)
    dest.mkdir(parents=True, exist_ok=True)
    moved = []
    for d in legacy_lesson_dirs(output_root):
        target = dest / d.name
        if target.exists():
            continue
        shutil.move(str(d), str(target))
        moved.append(d.name)
    return moved
