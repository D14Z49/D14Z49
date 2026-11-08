#!/usr/bin/env python3
"""Gera os cartões de estatísticas do README do perfil (stats.svg e linguagens.svg).

Substitui o github-readme-stats.vercel.app, que foi pausado. Roda uma vez por dia no servidor com um token
somente leitura. Os cartões mostram só totais: nenhum nome de repositório privado sai daqui.

Uso: GITHUB_TOKEN_FILE=/root/.config/github-leitura.token python3 tools/cartoes.py [pasta_de_saida]
"""
import json
import os
import re
import sys
import urllib.request
from datetime import datetime, timedelta, timezone
from html import escape

USER = "D14Z49"
API = "https://api.github.com"
BG, BORDER, TITLE, TEXT, MUTED, ACCENT = "#0d1117", "#1f6feb", "#00d4ff", "#c9d1d9", "#8b949e", "#1f6feb"
LANG_COLORS = {
    "Python": "#3572A5", "TypeScript": "#3178c6", "JavaScript": "#f1e05a", "PHP": "#4F5D95", "Go": "#00ADD8",
    "HTML": "#e34c26", "CSS": "#663399", "Blade": "#f7523f", "Shell": "#89e051", "Kotlin": "#A97BFF",
    "Java": "#b07219", "Vue": "#41b883", "Dockerfile": "#384d54", "C++": "#f34b7d", "C": "#555555",
}
SKIP_LANGS = {"HTML", "CSS", "Blade", "Dockerfile", "Mako", "Jinja", "Makefile", "Procfile"}  # markup, not languages


def _token() -> str:
    path = os.environ.get("GITHUB_TOKEN_FILE", "/root/.config/github-leitura.token")
    with open(path) as f:
        return f.read().strip()


def _get(url: str, token: str):
    req = urllib.request.Request(url if url.startswith("http") else API + url,
                                 headers={"Authorization": f"Bearer {token}", "Accept": "application/vnd.github+json",
                                          "User-Agent": "perfil-cartoes"})
    with urllib.request.urlopen(req, timeout=30) as r:
        return json.load(r), r.headers.get("Link", "")


def _count(url: str, token: str) -> int:
    """Number of items in a paginated list, read from the Link header with per_page=1."""
    try:
        data, link = _get(url + ("&" if "?" in url else "?") + "per_page=1", token)
    except urllib.error.HTTPError as e:
        if e.code == 409:  # empty repository
            return 0
        raise
    m = re.search(r'[?&]page=(\d+)>; rel="last"', link)
    return int(m.group(1)) if m else len(data)


def collect(token: str) -> dict:
    repos, page = [], 1
    while True:
        batch, _ = _get(f"/user/repos?affiliation=owner&per_page=100&page={page}", token)
        repos += batch
        if len(batch) < 100:
            break
        page += 1
    own = [r for r in repos if not r["fork"] and r["owner"]["login"] == USER]
    since = (datetime.now(timezone.utc) - timedelta(days=365)).strftime("%Y-%m-%dT%H:%M:%SZ")
    commits, langs = 0, {}
    for r in own:
        commits += _count(f"/repos/{r['full_name']}/commits?since={since}", token)
        data, _ = _get(f"/repos/{r['full_name']}/languages", token)
        for lang, size in data.items():
            if lang not in SKIP_LANGS:
                langs[lang] = langs.get(lang, 0) + size
    user, _ = _get(f"/users/{USER}", token)
    return {
        "repos": len(own),
        "private": sum(1 for r in own if r["private"]),
        "commits": commits,
        "active_repos": sum(1 for r in own if r["pushed_at"] >= since),
        "since_year": user["created_at"][:4],
        "langs": sorted(langs.items(), key=lambda kv: -kv[1]),
    }


def _frame(width: int, height: int, title: str, body: str) -> str:
    return f'''<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="0 0 {width} {height}" role="img" aria-label="{escape(title)}">
<style>
.t{{font:600 18px 'Segoe UI',Ubuntu,'Helvetica Neue',sans-serif;fill:{TITLE}}}
.l{{font:400 14px 'Segoe UI',Ubuntu,'Helvetica Neue',sans-serif;fill:{TEXT}}}
.v{{font:700 14px 'Segoe UI',Ubuntu,'Helvetica Neue',sans-serif;fill:{TEXT}}}
.m{{font:400 11px 'Segoe UI',Ubuntu,'Helvetica Neue',sans-serif;fill:{MUTED}}}
</style>
<rect x="0.5" y="0.5" rx="6" width="{width - 1}" height="{height - 1}" fill="{BG}" stroke="{BORDER}" stroke-opacity="0.35"/>
<text x="24" y="36" class="t">{escape(title)}</text>
{body}
</svg>
'''


def stats_svg(s: dict, updated: str) -> str:
    rows = [("Repositórios", f"{s['repos']}  ({s['private']} privados)"),
            ("Commits nos últimos 12 meses", f"{s['commits']:,}".replace(",", ".")),
            ("Projetos ativos no último ano", str(s["active_repos"])),
            ("No GitHub desde", s["since_year"])]
    body = ""
    for i, (label, value) in enumerate(rows):
        y = 74 + i * 28
        body += (f'<circle cx="30" cy="{y - 5}" r="4" fill="{ACCENT}"/>'
                 f'<text x="44" y="{y}" class="l">{escape(label)}</text>'
                 f'<text x="471" y="{y}" class="v" text-anchor="end">{escape(value)}</text>\n')
    body += f'<text x="471" y="183" class="m" text-anchor="end">atualizado em {updated}</text>'
    return _frame(495, 195, "Atividade no GitHub", body)


def langs_svg(s: dict, updated: str) -> str:
    top = s["langs"][:6]
    total = sum(v for _, v in top) or 1
    width, bar_w, body, x = 300, 252, "", 24.0
    body += f'<clipPath id="c"><rect x="24" y="52" width="{bar_w}" height="8" rx="4"/></clipPath><g clip-path="url(#c)">'
    for lang, size in top:
        w = bar_w * size / total
        body += f'<rect x="{x:.2f}" y="52" width="{w + 0.5:.2f}" height="8" fill="{LANG_COLORS.get(lang, MUTED)}"/>'
        x += w
    body += "</g>\n"
    for i, (lang, size) in enumerate(top):
        col, row = i % 2, i // 2
        cx, cy = 24 + col * 132, 88 + row * 26
        pct = f"{100 * size / total:.1f}".replace(".", ",")
        body += (f'<circle cx="{cx + 5}" cy="{cy - 4}" r="5" fill="{LANG_COLORS.get(lang, MUTED)}"/>'
                 f'<text x="{cx + 16}" y="{cy}" class="l">{escape(lang)} <tspan class="m">{pct}%</tspan></text>\n')
    body += f'<text x="{width - 24}" y="183" class="m" text-anchor="end">atualizado em {updated}</text>'
    return _frame(width, 195, "Linguagens mais usadas", body)


def main():
    out = sys.argv[1] if len(sys.argv) > 1 else os.path.join(os.path.dirname(__file__), "..", "cartoes")
    os.makedirs(out, exist_ok=True)
    s = collect(_token())
    updated = datetime.now(timezone(timedelta(hours=-3))).strftime("%d/%m/%Y")
    for name, svg in (("stats.svg", stats_svg(s, updated)), ("linguagens.svg", langs_svg(s, updated))):
        with open(os.path.join(out, name), "w") as f:
            f.write(svg)
    print(json.dumps({k: v for k, v in s.items() if k != "langs"} | {"langs": s["langs"][:6]}, ensure_ascii=False))


if __name__ == "__main__":
    main()
