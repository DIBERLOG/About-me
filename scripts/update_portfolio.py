"""Refresh public portfolio data using only the Python standard library."""
import argparse
from collections import Counter
from datetime import datetime, timezone
from html import escape
import json
import os
from pathlib import Path
from urllib.request import Request, urlopen

ROOT = Path(__file__).resolve().parents[1]
OWNER = "DIBERLOG"
EXCLUDED = {"About-me", "Farm-bot"}


def fetch_repositories():
    repositories = []
    for page in range(1, 100):
        request = Request(
            f"https://api.github.com/users/{OWNER}/repos?type=owner&per_page=100&page={page}",
            headers={"Accept": "application/vnd.github+json", "User-Agent": "About-me-portfolio"},
        )
        if os.environ.get("GITHUB_TOKEN"):
            request.add_header("Authorization", f"Bearer {os.environ['GITHUB_TOKEN']}")
        with urlopen(request, timeout=30) as response:
            batch = json.load(response)
        repositories.extend(batch)
        if len(batch) < 100:
            return repositories
    raise RuntimeError("Repository pagination exceeded its limit")


def visible(repositories):
    return sorted(
        (r for r in repositories if not r.get("private") and r["name"] not in EXCLUDED),
        key=lambda r: (r.get("fork", False), r.get("archived", False), r["name"].lower()),
    )


def cell(value):
    return escape(str(value or "—")).replace("|", "&#124;").replace("\n", " ").replace("\r", " ")


def render_catalog(repositories):
    rows = ["| Проект | Основной язык | Описание | Статус |", "| --- | --- | --- | --- |"]
    for r in visible(repositories):
        name = r["name"]
        status = "Архив" if r.get("archived") else "Публичный"
        if r.get("fork"):
            status += " · форк"
        description = r.get("description") or "Описание и инструкции — в репозитории."
        rows.append(f"| [{cell(name)}](https://github.com/{OWNER}/{name}) | {cell(r.get('language'))} | {cell(description)} | {status} |")
    return "\n".join(rows)


def render_stats(repositories, date):
    projects = [r for r in visible(repositories) if not r.get("fork")]
    languages = Counter(r["language"] for r in projects if r.get("language"))
    lines = [
        "GITHUB / DIBERLOG",
        f"Проекты: {len(projects)}    Звёзды: {sum(r.get('stargazers_count', 0) for r in projects)}    Форки проектов: {sum(r.get('forks_count', 0) for r in projects)}",
        "Основной язык репозиториев (не доля кода):",
        *[f"{language}: {count}" for language, count in languages.most_common()],
        f"Обновлено: {date} UTC · публичные проекты портфолио, без форков",
    ]
    height = 76 + len(lines) * 30
    text = "\n".join(f'<text x="28" y="{48 + i * 30}" fill="{"#35d4cf" if i == 0 else "#e6edf3"}" font-size="{20 if i == 0 else 14}">{escape(line)}</text>' for i, line in enumerate(lines))
    return f'<svg xmlns="http://www.w3.org/2000/svg" width="900" height="{height}" viewBox="0 0 900 {height}" role="img" aria-labelledby="title"><title id="title">Статистика публичных проектов DIBERLOG</title><rect x="1" y="1" width="898" height="{height-2}" rx="16" fill="#0d1117" stroke="#35d4cf"/><g font-family="Segoe UI,Arial,sans-serif">{text}</g></svg>\n'


def replace_section(readme, name, content):
    start, end = f"<!-- {name}:START -->", f"<!-- {name}:END -->"
    if readme.count(start) != 1 or readme.count(end) != 1:
        raise ValueError(f"Expected exactly one pair of {name} markers")
    before, remaining = readme.split(start)
    _, after = remaining.split(end)
    return before + start + "\n" + content + "\n" + end + after


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--snapshot", type=Path, help="Use a saved API response instead of the network")
    args = parser.parse_args()
    repositories = json.loads(args.snapshot.read_text(encoding="utf-8-sig")) if args.snapshot else fetch_repositories()
    if not repositories:
        raise ValueError("Empty response: refusing to erase portfolio data")
    date = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    readme_path = ROOT / "README.md"
    updated = replace_section(readme_path.read_text(encoding="utf-8"), "PROJECTS", render_catalog(repositories))
    updated = replace_section(updated, "STATS", f"![Статистика публичных проектов](assets/github-stats.svg)\n\nДанные на {date} (UTC). Считаются публичные проекты портфолио без форков. Языки — число репозиториев по основному языку, а не доля кода.")
    (ROOT / "assets").mkdir(exist_ok=True)
    (ROOT / "assets/github-stats.svg").write_text(render_stats(repositories, date), encoding="utf-8")
    readme_path.write_text(updated, encoding="utf-8")


if __name__ == "__main__":
    main()
