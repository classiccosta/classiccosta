"""Update the open source section of the profile README.

Finds merged PRs authored by USER in repos USER doesn't own, then writes:
- a summary line (total merged PRs, projects, since date)
- the last 3 PRs as linked light/dark SVG rows in assets/oss/
between the OSS:START / OSS:END markers. With 0 PRs the block is left empty.
"""
import json
import os
import pathlib
import urllib.parse
import urllib.request
from datetime import datetime
from html import escape

USER = "classiccosta"
SHOW = 3
ROOT = pathlib.Path(__file__).resolve().parent.parent
README = ROOT / "README.md"
OUT = ROOT / "assets" / "oss"
START, END = "<!-- OSS:START -->", "<!-- OSS:END -->"

SANS = "-apple-system, BlinkMacSystemFont, 'Segoe UI', Helvetica, Arial, sans-serif"
MONO = "ui-monospace, SFMono-Regular, 'SF Mono', Menlo, Consolas, monospace"
THEME = {
    "dark": dict(border="#30363d", icon="#97c459", muted="#9198a1", link="#4493f8"),
    "light": dict(border="#d1d9e0", icon="#3b6d11", muted="#59636e", link="#0969da"),
}
MERGE_ICON = (
    '<path d="M5 18a2 2 0 1 0 4 0a2 2 0 1 0 -4 0"/><path d="M5 6a2 2 0 1 0 4 0a2 2 0 1 0 -4 0"/>'
    '<path d="M15 12a2 2 0 1 0 4 0a2 2 0 1 0 -4 0"/><path d="M7 8l0 8"/><path d="M7 8a4 4 0 0 0 4 4h4"/>'
)


def fetch_merged_prs():
    query = f"is:pr author:{USER} is:merged -user:{USER}"
    headers = {"Accept": "application/vnd.github+json", "User-Agent": USER}
    if token := os.environ.get("GITHUB_TOKEN"):
        headers["Authorization"] = f"Bearer {token}"
    items, page = [], 1
    while True:
        url = "https://api.github.com/search/issues?" + urllib.parse.urlencode(
            {"q": query, "per_page": 100, "page": page}
        )
        with urllib.request.urlopen(urllib.request.Request(url, headers=headers)) as r:
            data = json.load(r)
        items += data["items"]
        if len(items) >= data["total_count"] or not data["items"]:
            break
        page += 1
    prs = []
    for it in items:
        merged = (it.get("pull_request") or {}).get("merged_at")
        if not merged:
            continue
        prs.append(
            dict(
                id=it["id"],
                repo=it["repository_url"].split("/repos/", 1)[1],
                title=it["title"],
                url=it["html_url"],
                merged=datetime.fromisoformat(merged.replace("Z", "+00:00")),
            )
        )
    return sorted(prs, key=lambda p: p["merged"], reverse=True)


def clip(text, n):
    return text if len(text) <= n else text[: n - 1].rstrip() + "…"


def row_svg(pr, c):
    w, h = 640, 34
    return (
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{w}" height="{h}" viewBox="0 0 {w} {h}">'
        f'<rect x=".5" y=".5" width="{w - 1}" height="{h - 1}" rx="8" fill="none" stroke="{c["border"]}"/>'
        f'<g transform="translate(12 9) scale(.667)" fill="none" stroke="{c["icon"]}" stroke-width="2" '
        f'stroke-linecap="round" stroke-linejoin="round">{MERGE_ICON}</g>'
        f'<text x="36" y="21.5" style="font:400 12px {MONO}" fill="{c["muted"]}">{escape(clip(pr["repo"], 22))}</text>'
        f'<text x="214" y="21.5" style="font:400 13px {SANS}" fill="{c["link"]}">{escape(clip(pr["title"], 48))}</text>'
        f'<text x="{w - 12}" y="21.5" text-anchor="end" style="font:400 12px {SANS}" fill="{c["muted"]}">'
        f'{pr["merged"].strftime("%b %Y")}</text></svg>'
    )


def build_block(prs):
    for f in OUT.glob("*.svg"):
        f.unlink()
    if not prs:
        return ""
    OUT.mkdir(parents=True, exist_ok=True)
    projects = len({p["repo"] for p in prs})
    since = prs[-1]["merged"].strftime("%b %Y")
    s = lambda n, word: f"{n} {word}{'' if n == 1 else 's'}"
    rows = []
    for pr in prs[:SHOW]:
        for mode, c in THEME.items():
            (OUT / f"{pr['id']}-{mode}.svg").write_text(row_svg(pr, c))
        rows.append(
            f'<a href="{pr["url"]}"><picture>'
            f'<source media="(prefers-color-scheme: dark)" srcset="assets/oss/{pr["id"]}-dark.svg">'
            f'<img alt="{escape(pr["repo"])}: {escape(pr["title"])}" src="assets/oss/{pr["id"]}-light.svg" width="640">'
            f"</picture></a><br>"
        )
    search = "https://github.com/search?type=pullrequests&q=" + urllib.parse.quote(
        f"is:pr author:{USER} is:merged -user:{USER}"
    )
    return (
        "<H4>Open source</H4>\n"
        f"<p><b>{s(len(prs), 'merged PR')}</b> across <b>{s(projects, 'project')}</b> since {since}</p>\n"
        "<p>\n" + "\n".join(rows) + "\n</p>\n"
        f'<p><a href="{search}">See all merged PRs →</a></p>\n'
    )


def main():
    readme = README.read_text()
    head, rest = readme.split(START, 1)
    _, tail = rest.split(END, 1)
    block = build_block(fetch_merged_prs())
    README.write_text(f"{head}{START}\n{block}{END}{tail}")


if __name__ == "__main__":
    main()
