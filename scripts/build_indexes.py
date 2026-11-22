#!/usr/bin/env python3
"""Rebuild the generated index in memory/AGENTS.md, plans/AGENTS.md and scripts/AGENTS.md.

Run me when: I added, renamed, deleted or changed the gist of a memory, a plan or a script, and before every pull request.

Rules:
- memory/*.md (not AGENTS.md): front matter key `gist: "Read me when: ..."`.
- plans/<plan>/plan.md: front matter key `gist: "Read me when: ..."`.
- scripts/*: a line `Run me when: ...` in the first 25 lines (any comment style).
- README.md files with context index markers keep their recursive Markdown routing.
- Only the text between the BEGIN and END markers changes. The text above is fixed.
- The old wording `Read when:` is accepted as a gist.

Usage: build_indexes.py [--check] [ROOT]   (--check changes nothing; exit 1 if stale)
"""
from __future__ import annotations

import re
import sys
from pathlib import Path

from ctx_common import BEGIN, END, README_BEGIN, README_END, SKIP_DIRS, repo_root, split_frontmatter

RUN_ME = re.compile(r"Run me when:\s*(.+?)\s*(?:\*/|#>|-->|\"\"\")?\s*$")
PLAN_SKIP = {"archive"}


def md_gist(path: Path, errors: list[str]) -> str | None:
    meta, _ = split_frontmatter(path.read_text(encoding="utf-8"))
    gist = meta.get("gist")
    if not isinstance(gist, str) or not gist.strip():
        errors.append(f"{path}: missing 'gist' front matter")
        return None
    return gist.strip()


def script_gist(path: Path, errors: list[str]) -> str | None:
    try:
        lines = path.read_text(encoding="utf-8").split("\n")[:25]
    except UnicodeDecodeError:
        errors.append(f"{path}: not a text file")
        return None
    for line in lines:
        found = RUN_ME.search(line)
        if found:
            return "Run me when: " + found.group(1)
    errors.append(f"{path}: missing 'Run me when:' line in the first 25 lines")
    return None


def has_readme_index(path: Path) -> bool:
    return path.is_file() and README_BEGIN in path.read_text(encoding="utf-8")


def routed_markdown(folder: Path, exclude: set[str]) -> list[Path]:
    paths = []
    for child in sorted(folder.iterdir()):
        if child.name in SKIP_DIRS | exclude:
            continue
        if child.is_dir():
            index = child / "README.md"
            if has_readme_index(index):
                paths.append(index)
            else:
                paths.extend(routed_markdown(child, exclude))
        elif child.suffix == ".md" and child.name != "README.md":
            paths.append(child)
    return paths


def readme_entries(index: Path, text: str, errors: list[str]) -> list[tuple[str, str]]:
    match = re.search(r"<!--\s*index-exclude:\s*(.*?)\s*-->", text)
    excluded = {name.strip() for name in match.group(1).split(",")} if match else set()
    paths = routed_markdown(index.parent, set())
    out = []
    for path in sorted(paths):
        name = path.relative_to(index.parent).as_posix()
        if name not in excluded and (gist := md_gist(path, errors)):
            out.append((name, gist))
    return out


def entries(folder: Path, errors: list[str]) -> list[tuple[str, str]]:
    kind = folder.name
    out: list[tuple[str, str]] = []
    if kind == "memory":
        for p in sorted(routed_markdown(folder, {"AGENTS.md"})):
            if g := md_gist(p, errors):
                out.append((p.relative_to(folder).as_posix(), g))
    elif kind == "plans":
        for d in sorted(x for x in folder.iterdir() if x.is_dir() and x.name not in PLAN_SKIP | SKIP_DIRS):
            if (d / "plan.md").exists():
                if g := md_gist(d / "plan.md", errors):
                    out.append((f"{d.name}/plan.md", g))
            else:
                errors.append(f"{d}: plan folder has no plan.md")
    elif kind == "scripts":
        for p in sorted(folder.iterdir()):
            if p.is_file() and p.name not in {"AGENTS.md", "README.md"} and not p.name.startswith("."):
                if g := script_gist(p, errors):
                    out.append((p.name, g))
    return out


def render(items: list[tuple[str, str]], readme: bool = False) -> str:
    if not items:
        return "<!-- No routed files yet. -->" if readme else "<!-- Nothing to list yet. -->"
    suffix = "." if readme else ""
    return "\n".join(f"* [{name}](./{name}){suffix}\n  {gist}" for name, gist in items)


def replace_block(text: str, begin: str, end: str, content: str) -> str:
    head, _, rest = text.partition(begin)
    _, _, tail = rest.partition(end)
    return f"{head}{begin}\n\n{content}\n\n{end}{tail}"


def main(argv: list[str]) -> int:
    check = "--check" in argv
    args = [a for a in argv if not a.startswith("--")]
    root = repo_root(Path(args[0]) if args else None)
    errors: list[str] = []
    stale: list[str] = []
    indexes = [root / name / "AGENTS.md" for name in ("memory", "plans", "scripts")]
    indexes.extend(
        path for path in sorted(root.rglob("README.md"))
        if not SKIP_DIRS & set(path.relative_to(root).parts) and has_readme_index(path)
    )
    for index in indexes:
        if not index.parent.is_dir():
            continue

        if not index.is_file():
            errors.append(f"{index}: missing index")
            continue

        text = index.read_text(encoding="utf-8")
        is_readme = index.name == "README.md"
        begin, end = (README_BEGIN, README_END) if is_readme else (BEGIN, END)
        if begin not in text or end not in text.partition(begin)[2]:
            errors.append(f"{index}: missing or out-of-order index markers")
            continue
        items = readme_entries(index, text, errors) if is_readme else entries(index.parent, errors)
        new = replace_block(text, begin, end, render(items, readme=is_readme))
        if new != text:
            stale.append(index.relative_to(root).as_posix())
            if not check:
                index.write_text(new, encoding="utf-8")
    for err in errors:
        print(f"ERROR {err}")
    if check and stale:
        print("STALE index (run: python3 scripts/build_indexes.py): " + ", ".join(stale))
    return 1 if errors or (check and stale) else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
