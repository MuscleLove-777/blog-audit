#!/usr/bin/env python3
"""
FANZAアフィリエイトブログ群 自動監査スクリプト
全9サイトのSEO・リンク・CSS・記事品質を自動チェック
"""

import json
import os
import re
import time
from datetime import datetime, timezone, timedelta
from pathlib import Path

import requests

# 監査対象サイト
SITES = {
    "musclelove-blog": {
        "url": "https://musclelove-777.github.io/fitness-affiliate-blog/",
        "genre": "筋肉",
        "repo": "MuscleLove-777/fitness-affiliate-blog",
    },
    "ntr-navi": {
        "url": "https://musclelove-777.github.io/ntr-navi/",
        "genre": "NTR",
        "repo": "MuscleLove-777/ntr-navi",
    },
    "vr-eros": {
        "url": "https://musclelove-777.github.io/vr-eros/",
        "genre": "VR",
        "repo": "MuscleLove-777/vr-eros",
    },
    "entsuma": {
        "url": "https://musclelove-777.github.io/entsuma/",
        "genre": "熟女",
        "repo": "MuscleLove-777/entsuma",
    },
    "shiroto-squad": {
        "url": "https://musclelove-777.github.io/shiroto-squad/",
        "genre": "素人",
        "repo": "MuscleLove-777/shiroto-squad",
    },
    "oppai-paradise": {
        "url": "https://musclelove-777.github.io/oppai-paradise/",
        "genre": "巨乳",
        "repo": "MuscleLove-777/oppai-paradise",
    },
    "nijigen-realize": {
        "url": "https://musclelove-777.github.io/nijigen-realize/",
        "genre": "コスプレ",
        "repo": "MuscleLove-777/nijigen-realize",
    },
    "fetish-dendo": {
        "url": "https://musclelove-777.github.io/fetish-dendo/",
        "genre": "フェチ",
        "repo": "MuscleLove-777/fetish-dendo",
    },
    "eronavi": {
        "url": "https://musclelove-777.github.io/eronavi/",
        "genre": "総合",
        "repo": "MuscleLove-777/eronavi",
    },
}

JST = timezone(timedelta(hours=9))
SESSION = requests.Session()
SESSION.headers.update({"User-Agent": "BlogAuditBot/1.0"})


def check_http(url: str) -> dict:
    """HTTP応答チェック"""
    try:
        start = time.time()
        resp = SESSION.get(url, timeout=30)
        elapsed = round(time.time() - start, 2)
        return {
            "status_code": resp.status_code,
            "ok": resp.status_code == 200,
            "response_time_sec": elapsed,
            "html": resp.text if resp.status_code == 200 else "",
        }
    except Exception as e:
        return {"status_code": 0, "ok": False, "response_time_sec": 0, "html": "", "error": str(e)}


def check_css(html: str) -> dict:
    """CSSチェック: stylesheet読み込み & grid-layout"""
    has_stylesheet = bool(re.search(r'<link[^>]+rel=["\']stylesheet["\']', html, re.I))
    has_grid = "grid" in html.lower()
    return {"has_stylesheet": has_stylesheet, "has_grid_layout": has_grid, "ok": has_stylesheet}


def count_articles(html: str) -> dict:
    """記事数カウント"""
    articles = re.findall(r"<article", html, re.I)
    # articleタグがなければカード系divを探す
    if not articles:
        articles = re.findall(r'class="[^"]*card[^"]*"', html, re.I)
    count = len(articles)
    return {"count": count, "ok": count > 0}


def check_images(html: str) -> dict:
    """サンプル画像チェック(最大3枚)"""
    img_urls = re.findall(r'<img[^>]+src=["\']([^"\']+)["\']', html, re.I)
    # 相対URLやdata:は除外
    img_urls = [u for u in img_urls if u.startswith("http")][:3]
    results = []
    for url in img_urls:
        try:
            resp = SESSION.head(url, timeout=10, allow_redirects=True)
            results.append({"url": url, "status": resp.status_code, "ok": resp.status_code == 200})
        except Exception:
            results.append({"url": url, "status": 0, "ok": False})
    all_ok = all(r["ok"] for r in results) if results else False
    return {"images": results, "checked": len(results), "ok": all_ok}


def check_affiliate_links(html: str) -> dict:
    """アフィリエイトリンクチェック"""
    fanza_links = re.findall(r'href="[^"]*dmm\.co\.jp[^"]*"', html, re.I)
    fanza_links += re.findall(r'href="[^"]*fanza[^"]*"', html, re.I)
    fanza_links += re.findall(r'href="[^"]*al\.dmm\.co\.jp[^"]*"', html, re.I)
    count = len(fanza_links)
    return {"count": count, "ok": count > 0}


def check_musclelove_links(html: str) -> dict:
    """Patreon/X/Linktreeリンク確認"""
    patreon = bool(re.search(r'href="[^"]*patreon\.com[^"]*"', html, re.I))
    twitter = bool(re.search(r'href="[^"]*(?:twitter\.com|x\.com)[^"]*"', html, re.I))
    linktree = bool(re.search(r'href="[^"]*linktr\.ee[^"]*"', html, re.I))
    return {
        "patreon": patreon,
        "twitter": twitter,
        "linktree": linktree,
        "ok": patreon or twitter or linktree,
    }


def check_dark_theme(html: str) -> dict:
    """ダークテーマチェック"""
    has_dark = bool(re.search(r'data-theme=["\']dark["\']', html, re.I))
    # CSSでのダークテーマも検出
    has_dark_css = bool(re.search(r"background[^;]*#(?:0d1117|1a1a2e|121212|0a0a0a)", html, re.I))
    return {"data_theme_dark": has_dark, "dark_css": has_dark_css, "ok": has_dark or has_dark_css}


def check_responsive(html: str) -> dict:
    """レスポンシブチェック"""
    has_viewport = bool(re.search(r'<meta[^>]+name=["\']viewport["\']', html, re.I))
    return {"has_viewport": has_viewport, "ok": has_viewport}


def check_sitemap(base_url: str) -> dict:
    """サイトマップチェック"""
    url = base_url.rstrip("/") + "/sitemap.xml"
    try:
        resp = SESSION.get(url, timeout=10)
        exists = resp.status_code == 200
        return {"url": url, "exists": exists, "ok": exists}
    except Exception:
        return {"url": url, "exists": False, "ok": False}


def check_robots(base_url: str) -> dict:
    """robots.txtチェック"""
    url = base_url.rstrip("/") + "/robots.txt"
    try:
        resp = SESSION.get(url, timeout=10)
        exists = resp.status_code == 200
        return {"url": url, "exists": exists, "ok": exists}
    except Exception:
        return {"url": url, "exists": False, "ok": False}


def get_last_commit(repo: str) -> dict:
    """GitHub APIで最終コミット日時を取得"""
    url = f"https://api.github.com/repos/{repo}/commits?per_page=1"
    headers = {}
    token = os.environ.get("GITHUB_TOKEN") or os.environ.get("GH_TOKEN")
    if token:
        headers["Authorization"] = f"token {token}"
    try:
        resp = SESSION.get(url, timeout=10, headers=headers)
        if resp.status_code == 200:
            data = resp.json()
            if data:
                date_str = data[0]["commit"]["committer"]["date"]
                return {"last_commit": date_str, "ok": True}
        return {"last_commit": None, "ok": False, "status": resp.status_code}
    except Exception as e:
        return {"last_commit": None, "ok": False, "error": str(e)}


def audit_site(name: str, config: dict) -> dict:
    """1サイトの全チェック実行"""
    print(f"  監査中: {name} ({config['genre']}) ...")
    url = config["url"]
    repo = config["repo"]

    # HTTP応答チェック
    http_result = check_http(url)
    html = http_result.pop("html", "")

    result = {
        "name": name,
        "url": url,
        "genre": config["genre"],
        "repo": repo,
        "checks": {
            "http": http_result,
            "css": check_css(html) if html else {"has_stylesheet": False, "has_grid_layout": False, "ok": False},
            "articles": count_articles(html) if html else {"count": 0, "ok": False},
            "images": check_images(html) if html else {"images": [], "checked": 0, "ok": False},
            "affiliate_links": check_affiliate_links(html) if html else {"count": 0, "ok": False},
            "musclelove_links": check_musclelove_links(html) if html else {"patreon": False, "twitter": False, "linktree": False, "ok": False},
            "dark_theme": check_dark_theme(html) if html else {"data_theme_dark": False, "dark_css": False, "ok": False},
            "responsive": check_responsive(html) if html else {"has_viewport": False, "ok": False},
            "sitemap": check_sitemap(url),
            "robots_txt": check_robots(url),
            "last_commit": get_last_commit(repo),
        },
        "response_time_sec": http_result["response_time_sec"],
    }

    # 合計スコア計算
    checks = result["checks"]
    total = len(checks)
    passed = sum(1 for c in checks.values() if c.get("ok"))
    result["score"] = {"total": total, "passed": passed, "percentage": round(passed / total * 100)}
    result["status"] = "green" if passed >= 9 else ("yellow" if passed >= 6 else "red")

    return result


def generate_html_dashboard(results: dict, output_path: str):
    """HTMLダッシュボード生成(docs/index.html)"""
    timestamp = results["timestamp"]
    sites = results["sites"]

    cards_html = ""
    for site in sites:
        name = site["name"]
        genre = site["genre"]
        url = site["url"]
        score = site["score"]
        status = site["status"]
        checks = site["checks"]

        status_color = {"green": "#2ea043", "yellow": "#d29922", "red": "#f85149"}[status]
        status_emoji = {"green": "&#9989;", "yellow": "&#9888;&#65039;", "red": "&#10060;"}[status]

        check_rows = ""
        check_labels = {
            "http": "HTTP応答",
            "css": "CSS読み込み",
            "articles": "記事数",
            "images": "画像チェック",
            "affiliate_links": "アフィリリンク",
            "musclelove_links": "SNSリンク",
            "dark_theme": "ダークテーマ",
            "responsive": "レスポンシブ",
            "sitemap": "サイトマップ",
            "robots_txt": "robots.txt",
            "last_commit": "最終更新",
        }
        for key, label in check_labels.items():
            check = checks.get(key, {})
            ok = check.get("ok", False)
            icon = "&#9989;" if ok else "&#10060;"
            detail = ""
            if key == "articles":
                detail = f" ({check.get('count', 0)}件)"
            elif key == "http":
                detail = f" ({check.get('status_code', '?')})"
            elif key == "affiliate_links":
                detail = f" ({check.get('count', 0)}件)"
            elif key == "last_commit" and check.get("last_commit"):
                detail = f" ({check['last_commit'][:10]})"
            check_rows += f'<tr><td>{label}{detail}</td><td style="text-align:center">{icon}</td></tr>'

        cards_html += f"""
        <div class="site-card" style="border-left: 4px solid {status_color}">
            <div class="card-header">
                <span class="status-badge" style="background:{status_color}">{status_emoji} {score['passed']}/{score['total']}</span>
                <h3>{name}</h3>
                <span class="genre-tag">{genre}</span>
            </div>
            <a href="{url}" target="_blank" class="site-link">{url}</a>
            <div class="response-time">応答時間: {site.get('response_time_sec', '?')}秒</div>
            <table class="check-table">
                {check_rows}
            </table>
        </div>
        """

    # 全体サマリー
    total_sites = len(sites)
    green_count = sum(1 for s in sites if s["status"] == "green")
    yellow_count = sum(1 for s in sites if s["status"] == "yellow")
    red_count = sum(1 for s in sites if s["status"] == "red")

    html = f"""<!DOCTYPE html>
<html lang="ja" data-theme="dark">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>ブログ監査ダッシュボード</title>
    <style>
        * {{ margin: 0; padding: 0; box-sizing: border-box; }}
        body {{
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Helvetica, Arial, sans-serif;
            background: #0d1117;
            color: #e6edf3;
            padding: 20px;
            line-height: 1.6;
        }}
        .header {{
            text-align: center;
            padding: 30px 0;
            border-bottom: 1px solid #30363d;
            margin-bottom: 30px;
        }}
        .header h1 {{
            font-size: 2em;
            margin-bottom: 10px;
            background: linear-gradient(135deg, #58a6ff, #bc8cff);
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
        }}
        .header .timestamp {{
            color: #8b949e;
            font-size: 0.9em;
        }}
        .summary {{
            display: flex;
            justify-content: center;
            gap: 30px;
            margin-bottom: 30px;
            flex-wrap: wrap;
        }}
        .summary-item {{
            text-align: center;
            padding: 20px 30px;
            border-radius: 12px;
            background: #161b22;
            border: 1px solid #30363d;
            min-width: 120px;
        }}
        .summary-item .count {{
            font-size: 2.5em;
            font-weight: bold;
        }}
        .summary-item .label {{
            font-size: 0.85em;
            color: #8b949e;
            margin-top: 5px;
        }}
        .grid {{
            display: grid;
            grid-template-columns: repeat(auto-fill, minmax(360px, 1fr));
            gap: 20px;
            max-width: 1400px;
            margin: 0 auto;
        }}
        .site-card {{
            background: #161b22;
            border-radius: 8px;
            padding: 20px;
            border: 1px solid #30363d;
            transition: transform 0.2s;
        }}
        .site-card:hover {{
            transform: translateY(-2px);
        }}
        .card-header {{
            display: flex;
            align-items: center;
            gap: 10px;
            margin-bottom: 10px;
        }}
        .card-header h3 {{
            font-size: 1.1em;
            flex-grow: 1;
        }}
        .status-badge {{
            padding: 3px 10px;
            border-radius: 20px;
            font-size: 0.8em;
            color: #fff;
            white-space: nowrap;
        }}
        .genre-tag {{
            background: #30363d;
            padding: 2px 8px;
            border-radius: 4px;
            font-size: 0.75em;
            color: #8b949e;
        }}
        .site-link {{
            color: #58a6ff;
            font-size: 0.8em;
            text-decoration: none;
            display: block;
            margin-bottom: 5px;
            word-break: break-all;
        }}
        .site-link:hover {{ text-decoration: underline; }}
        .response-time {{
            color: #8b949e;
            font-size: 0.8em;
            margin-bottom: 10px;
        }}
        .check-table {{
            width: 100%;
            font-size: 0.85em;
            border-collapse: collapse;
        }}
        .check-table tr {{ border-bottom: 1px solid #21262d; }}
        .check-table td {{ padding: 4px 8px; }}
        .footer {{
            text-align: center;
            margin-top: 40px;
            padding: 20px;
            color: #8b949e;
            font-size: 0.85em;
            border-top: 1px solid #30363d;
        }}
        .footer code {{
            background: #161b22;
            padding: 2px 6px;
            border-radius: 4px;
            font-size: 0.9em;
        }}
        .loading {{
            text-align: center;
            padding: 60px;
            color: #8b949e;
        }}
        @media (max-width: 768px) {{
            .grid {{ grid-template-columns: 1fr; }}
            .summary {{ gap: 15px; }}
            .summary-item {{ min-width: 80px; padding: 15px; }}
            body {{ padding: 10px; }}
        }}
    </style>
</head>
<body>
    <div class="header">
        <h1>ブログ監査ダッシュボード</h1>
        <div class="timestamp" id="timestamp">最終チェック: {timestamp}</div>
    </div>

    <div class="summary">
        <div class="summary-item">
            <div class="count" style="color:#e6edf3">{total_sites}</div>
            <div class="label">総サイト数</div>
        </div>
        <div class="summary-item">
            <div class="count" style="color:#2ea043">{green_count}</div>
            <div class="label">正常</div>
        </div>
        <div class="summary-item">
            <div class="count" style="color:#d29922">{yellow_count}</div>
            <div class="label">警告</div>
        </div>
        <div class="summary-item">
            <div class="count" style="color:#f85149">{red_count}</div>
            <div class="label">エラー</div>
        </div>
    </div>

    <div class="grid" id="sites-grid">
        {cards_html}
    </div>

    <div class="footer">
        <p>パワポレポート生成: <code>python3 scripts/generate_report.py</code></p>
        <p>手動監査実行: <code>python3 scripts/audit.py</code></p>
        <p>毎日 JST 10:00 に自動監査が実行されます</p>
    </div>

    <script>
        // latest.jsonから動的更新（GitHub Pages用）
        fetch('latest.json')
            .then(r => r.json())
            .then(data => {{
                document.getElementById('timestamp').textContent = '最終チェック: ' + data.timestamp;
            }})
            .catch(() => {{}});
    </script>
</body>
</html>"""

    Path(output_path).parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, "w", encoding="utf-8") as f:
        f.write(html)
    print(f"  HTML出力: {output_path}")


def main():
    print("=" * 60)
    print("  ブログ監査システム 開始")
    print(f"  実行日時: {datetime.now(JST).strftime('%Y-%m-%d %H:%M:%S JST')}")
    print("=" * 60)

    results = {
        "timestamp": datetime.now(JST).strftime("%Y-%m-%d %H:%M:%S JST"),
        "sites": [],
    }

    for name, config in SITES.items():
        site_result = audit_site(name, config)
        results["sites"].append(site_result)

    # サマリー表示
    print("\n" + "=" * 60)
    print("  監査結果サマリー")
    print("=" * 60)
    for site in results["sites"]:
        status_mark = {"green": "OK", "yellow": "WARN", "red": "NG"}[site["status"]]
        print(f"  [{status_mark:4s}] {site['name']:20s} {site['score']['passed']}/{site['score']['total']} ({site['genre']})")

    # JSON出力
    base_dir = Path(__file__).resolve().parent.parent
    results_dir = base_dir / "results"
    results_dir.mkdir(parents=True, exist_ok=True)
    json_path = results_dir / "latest.json"
    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(results, f, ensure_ascii=False, indent=2)
    print(f"\n  JSON出力: {json_path}")

    # docs/latest.json にもコピー
    docs_dir = base_dir / "docs"
    docs_dir.mkdir(parents=True, exist_ok=True)
    docs_json_path = docs_dir / "latest.json"
    with open(docs_json_path, "w", encoding="utf-8") as f:
        json.dump(results, f, ensure_ascii=False, indent=2)
    print(f"  docs/latest.json にコピー完了")

    # HTMLダッシュボード生成
    html_path = docs_dir / "index.html"
    generate_html_dashboard(results, str(html_path))

    print("\n  監査完了!")
    return results


if __name__ == "__main__":
    main()
