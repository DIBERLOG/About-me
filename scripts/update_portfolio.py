"""Refresh public portfolio data using only the Python standard library."""
import argparse
from collections import Counter
from datetime import datetime, timezone
from html import escape
import json
import os
from pathlib import Path
import re
import textwrap
from urllib.request import Request, urlopen

ROOT = Path(__file__).resolve().parents[1]
OWNER = "DIBERLOG"
EXCLUDED = {"About-me", "Farm-bot"}
TITLES = {
    "AI-Screenshot-Assistant-Ultimate-Multi-Provider-Edition": "AI Screenshot Assistant",
    "JARVIS_ALTRON": "JARVIS · ALTRON",
    "matreshka-master-wordpress": "Matreshka Master",
    "urban-blueprint_city-techplan": "Urban Blueprint · City Techplan",
    "New-Year-s-Gift-collection": "New Year's Gift Collection",
    "github-readme-stats-diberlog": "GitHub Readme Stats · fork",
}
COLORS = {"Python": "#3572A5", "JavaScript": "#f1e05a", "TypeScript": "#3178c6", "Vue": "#41b883", "Rust": "#dea584", "PHP": "#4F5D95"}


def svg_frame(width, height, title, content):
    return f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="0 0 {width} {height}" role="img" aria-labelledby="title"><title id="title">{escape(title)}</title><rect x="0.5" y="0.5" width="{width-1}" height="{height-1}" rx="5" fill="#0d1117" stroke="#00eaff"/><g font-family="Segoe UI,Arial,sans-serif">{content}</g></svg>\n'


def render_project_card(repo):
    title = TITLES.get(repo['name'], repo['name'])
    description = ' '.join((repo.get('description') or 'Описание и инструкции — в репозитории.').split())
    lines = textwrap.wrap(description, width=49)[:2]
    if len(textwrap.wrap(description, width=49)) > 2:
        lines[-1] = lines[-1].rstrip('., ') + '…'
    text = f'<path d="M22 21h12v15H22z M25 21v15 M22 33h12" fill="none" stroke="#00eaff" stroke-width="1.4"/><text x="44" y="34" fill="#00eaff" font-size="16" font-weight="600">{escape(title)}</text>'
    text += ''.join(f'<text x="22" y="{65+i*20}" fill="#ffffff" font-size="12">{escape(line)}</text>' for i, line in enumerate(lines))
    language = repo.get('language') or 'Markdown'
    text += f'<circle cx="27" cy="119" r="5" fill="{COLORS.get(language, "#8b949e")}"/><text x="39" y="123" fill="#ffffff" font-size="12">{escape(language)}</text><text x="205" y="123" fill="#ffffff" font-size="12">☆ {repo.get("stargazers_count", 0)}    ⑂ {repo.get("forks_count", 0)}</text>'
    return svg_frame(440, 145, title, text)


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
    lines = [
        "DIBERLOG · GitHub Статистика",
        f"Проекты: {len(projects)}",
        f"Звёзды: {sum(r.get('stargazers_count', 0) for r in projects)}",
        f"Форки проектов: {sum(r.get('forks_count', 0) for r in projects)}",
        f"Обновлено: {date} UTC",
    ]
    text = ''.join(f'<text x="24" y="{35 + i * 30}" fill="{"#00eaff" if i == 0 else "#ffffff"}" font-size="{17 if i == 0 else 13}" font-weight="{600 if i == 0 else 400}">{escape(line)}</text>' for i, line in enumerate(lines))
    text += f'<circle cx="365" cy="97" r="42" fill="none" stroke="#143b47" stroke-width="8"/><circle cx="365" cy="97" r="42" fill="none" stroke="#00eaff" stroke-width="8" stroke-dasharray="220 44" transform="rotate(-90 365 97)"/><text x="365" y="102" text-anchor="middle" font-size="24" fill="#00eaff">{len(projects)}</text><text x="365" y="162" text-anchor="middle" font-size="11" fill="#8b949e">проектов</text>'
    return svg_frame(440, 195, 'Статистика публичных проектов DIBERLOG', text)


def render_languages(repositories):
    languages = Counter(r['language'] for r in visible(repositories) if not r.get('fork') and r.get('language'))
    total = sum(languages.values())
    text = '<text x="24" y="35" fill="#00eaff" font-size="17" font-weight="600">Основные языки проектов</text>'
    offset = 0
    for i, (language, count) in enumerate(languages.most_common()):
        color = COLORS.get(language, '#8b949e')
        text += f'<circle cx="105" cy="110" r="46" fill="none" stroke="{color}" stroke-width="17" pathLength="100" stroke-dasharray="{count/total*100} {100-count/total*100}" stroke-dashoffset="{-offset}" transform="rotate(-90 105 110)"/>'
        text += f'<circle cx="211" cy="{65+i*18}" r="4" fill="{color}"/><text x="224" y="{69+i*18}" fill="#ffffff" font-size="12">{escape(language)}: {count}</text>'
        offset += count/total*100
    text += f'<text x="105" y="115" text-anchor="middle" fill="#ffffff" font-size="22">{total}</text><text x="24" y="180" fill="#8b949e" font-size="10">Число репозиториев по основному языку, не доля кода</text>'
    return svg_frame(440, 195, 'Основные языки публичных проектов', text)


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
    updated = replace_section(readme_path.read_text(encoding="utf-8"), "PROJECTS", '\n'.join(f'[![{cell(TITLES.get(r["name"], r["name"]))}](assets/cards/{r["name"]}.svg)](https://github.com/{OWNER}/{r["name"]})' for r in visible(repositories)))
    updated = replace_section(updated, "STATS", f"![Статистика публичных проектов](assets/github-stats.svg)\n![Основные языки проектов](assets/github-languages.svg)\n\nДанные на {date} (UTC). Считаются публичные проекты портфолио без форков. Языки — число репозиториев по основному языку, а не доля кода.")
    # Keep a project card next to each hand-written featured case.
    updated = re.sub(r'\n<!-- CARD:START -->.*?<!-- CARD:END -->\n', '', updated, flags=re.S)
    for repo in visible(repositories):
        name = repo['name']
        heading = re.compile(rf'(^### \[[^\n]+\]\(https://github.com/{OWNER}/{re.escape(name)}\)\n)', re.M)
        card = f'\n<!-- CARD:START -->\n[![{cell(TITLES.get(name, name))}](assets/cards/{name}.svg)](https://github.com/{OWNER}/{name})\n<!-- CARD:END -->\n'
        updated = heading.sub(lambda match: match.group(1) + card, updated)
    (ROOT / "assets").mkdir(exist_ok=True)
    (ROOT / 'assets/cards').mkdir(exist_ok=True)
    for repo in visible(repositories):
        (ROOT / f'assets/cards/{repo["name"]}.svg').write_text(render_project_card(repo), encoding='utf-8')
    (ROOT / "assets/github-stats.svg").write_text(render_stats(repositories, date), encoding="utf-8")
    (ROOT / "assets/github-languages.svg").write_text(render_languages(repositories), encoding="utf-8")
    readme_path.write_text(updated, encoding="utf-8")


if __name__ == "__main__":
    main()
