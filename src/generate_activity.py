
import html
import json
import os
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

USERNAME = "Shrijit0105"
PROFILE_REPO = USERNAME
DASHBOARD_REPO = "GitHub-Activity-Centre"
OUTPUT = Path("assets/github-activity.svg")

API = "https://api.github.com"
TOKEN = os.environ.get("GH_TOKEN", "")

HEADERS = {
    "Accept": "application/vnd.github+json",
    "X-GitHub-Api-Version": "2022-11-28",
    "User-Agent": "GitHub-Activity-Centre",
}
if TOKEN:
    HEADERS["Authorization"] = f"Bearer {TOKEN}"


def api_get(url):
    request = urllib.request.Request(url, headers=HEADERS)
    with urllib.request.urlopen(request, timeout=25) as response:
        return json.loads(response.read().decode("utf-8"))


def fetch_repositories():
    repositories = []
    page = 1

    while True:
        url = (
            f"{API}/users/{USERNAME}/repos"
            f"?type=owner&sort=updated&per_page=100&page={page}"
        )
        batch = api_get(url)

        if not batch:
            break

        repositories.extend(
            repo for repo in batch
            if not repo.get("fork", False)
        )

        if len(batch) < 100:
            break

        page += 1

    return repositories


def fetch_recent_commits(repositories):
    commits = []

    ignored = {
        PROFILE_REPO.lower(),
        DASHBOARD_REPO.lower(),
    }

    for repo in repositories:
        if repo["name"].lower() in ignored:
            continue

        full_name = repo["full_name"]
        url = (
            f"{API}/repos/{full_name}/commits"
            f"?author={urllib.parse.quote(USERNAME)}&per_page=3"
        )

        try:
            results = api_get(url)

            for item in results:
                commit = item.get("commit", {})
                author = commit.get("author") or {}
                message = (commit.get("message") or "").splitlines()[0]

                commits.append({
                    "repo": repo["name"],
                    "message": message,
                    "sha": item.get("sha", "")[:7],
                    "url": item.get("html_url", ""),
                    "date": author.get("date", ""),
                })

        except (urllib.error.HTTPError, urllib.error.URLError, TimeoutError) as error:
            print(f"Skipping {full_name}: {error}")

    commits.sort(key=lambda item: item["date"], reverse=True)
    return commits[:5]


def shorten(value, limit):
    value = " ".join(str(value).split())
    if len(value) > limit:
        return value[:limit - 1] + "…"
    return value


def esc(value):
    return html.escape(str(value), quote=True)


def generate_svg(repositories, commits):
    public_repos = len(repositories)
    stars = sum(repo.get("stargazers_count", 0) for repo in repositories)
    forks = sum(repo.get("forks_count", 0) for repo in repositories)

    updated = datetime.now(timezone.utc).strftime("%d %b %Y · %H:%M UTC")

    width = 1000
    row_height = 66
    commit_start = 300
    height = commit_start + max(len(commits), 1) * row_height + 65

    parts = [
        f'<svg xmlns="http://www.w3.org/2000/svg" '
        f'width="{width}" height="{height}" viewBox="0 0 {width} {height}">',
        """
        <defs>
          <linearGradient id="bg" x1="0" y1="0" x2="1" y2="1">
            <stop offset="0%" stop-color="#0b1020"/>
            <stop offset="100%" stop-color="#111827"/>
          </linearGradient>
          <linearGradient id="line" x1="0" y1="0" x2="1" y2="0">
            <stop offset="0%" stop-color="#ef4444"/>
            <stop offset="100%" stop-color="#38bdf8"/>
          </linearGradient>
        </defs>
        <rect width="1000" height="100%" rx="18" fill="url(#bg)"/>
        <rect x="1" y="1" width="998" height="100%" rx="17"
              fill="none" stroke="#293449"/>
        <rect x="0" y="0" width="1000" height="5" rx="2"
              fill="url(#line)"/>
        """,
        f'<text x="34" y="48" fill="#f8fafc" font-size="25" '
        f'font-family="monospace" font-weight="700">'
        f'ACTIVITY COMMAND CENTRE</text>',
        f'<text x="35" y="75" fill="#94a3b8" font-size="12" '
        f'font-family="monospace">USER // {USERNAME.upper()} '
        f'· PUBLIC REPOSITORY TELEMETRY</text>',
        f'<text x="965" y="48" text-anchor="end" fill="#4ade80" '
        f'font-size="12" font-family="monospace">● SYSTEM ONLINE</text>',
        f'<text x="965" y="75" text-anchor="end" fill="#64748b" '
        f'font-size="11" font-family="monospace">{esc(updated)}</text>',
    ]

    metrics = [
        ("PUBLIC REPOSITORIES", public_repos, "#38bdf8"),
        ("STARS EARNED", stars, "#f87171"),
        ("FORKS", forks, "#a78bfa"),
    ]

    for index, (label, value, accent) in enumerate(metrics):
        x = 34 + index * 315
        parts.extend([
            f'<rect x="{x}" y="105" width="294" height="105" rx="10" '
            f'fill="#0f172a" stroke="#273449"/>',
            f'<rect x="{x}" y="105" width="4" height="105" rx="2" '
            f'fill="{accent}"/>',
            f'<text x="{x + 20}" y="137" fill="#94a3b8" font-size="12" '
            f'font-family="monospace">{esc(label)}</text>',
            f'<text x="{x + 20}" y="181" fill="#f8fafc" font-size="34" '
            f'font-family="monospace" font-weight="700">{value:,}</text>',
        ])

    parts.extend([
        '<text x="34" y="250" fill="#e2e8f0" font-size="16" '
        'font-family="monospace" font-weight="700">'
        '▸ RECENT COMMIT ACTIVITY</text>',
        '<line x1="34" y1="266" x2="966" y2="266" stroke="#334155"/>',
    ])

    if not commits:
        parts.append(
            '<text x="38" y="310" fill="#94a3b8" font-size="14" '
            'font-family="monospace">'
            'No recent authored commits found in tracked repositories.</text>'
        )
    else:
        for index, commit in enumerate(commits):
            y = commit_start + index * row_height
            parts.extend([
                f'<circle cx="42" cy="{y + 7}" r="4" fill="#38bdf8"/>',
                f'<text x="58" y="{y + 4}" fill="#7dd3fc" '
                f'font-size="12" font-family="monospace">'
                f'{esc(shorten(commit["repo"], 34))}</text>',
                f'<text x="58" y="{y + 25}" fill="#e2e8f0" '
                f'font-size="13" font-family="monospace">'
                f'{esc(shorten(commit["message"], 88))}</text>',
                f'<text x="58" y="{y + 44}" fill="#64748b" '
                f'font-size="10" font-family="monospace">'
                f'COMMIT {esc(commit["sha"])} · '
                f'{esc(commit["date"][:10] or "DATE N/A")}</text>',
            ])

            if commit["url"]:
                parts.append(
                    f'<a href="{esc(commit["url"])}" '
                    f'target="_blank"><rect x="25" y="{y - 12}" '
                    f'width="940" height="57" fill="transparent"/></a>'
                )

            parts.append(
                f'<line x1="34" y1="{y + 53}" x2="966" '
                f'y2="{y + 53}" stroke="#1e293b"/>'
            )

    footer_y = height - 25
    parts.extend([
        f'<text x="34" y="{footer_y}" fill="#64748b" '
        f'font-size="10" font-family="monospace">'
        'GENERATED BY GITHUB ACTIONS · SVG TELEMETRY</text>',
        f'<text x="966" y="{footer_y}" text-anchor="end" '
        f'fill="#64748b" font-size="10" font-family="monospace">'
        'END OF TRANSMISSION</text>',
        '</svg>',
    ])

    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT.write_text("\n".join(parts), encoding="utf-8")
    print(f"Generated {OUTPUT} ({public_repos} repositories, "
          f"{len(commits)} recent commits)")


def main():
    repositories = fetch_repositories()
    commits = fetch_recent_commits(repositories)
    generate_svg(repositories, commits)


if __name__ == "__main__":
    main()
