#!/usr/bin/env python3
"""
Contrôle PageSpeed — Monte-Cristo Patrimoine
Interroge l'API PageSpeed Insights (Google) sur les pages actives du site.

Scores retournés :
  performance   — vitesse de chargement (LCP, CLS, FID…)
  seo           — signaux SEO techniques (meta, robots, lisibilité)
  accessibility — accessibilité (contrastes, labels, rôles ARIA)

Niveaux :
  critique  — performance < 50 OU seo < 80
  important — performance < 70
  ok        — tout ≥ 70 performance, ≥ 80 seo

Note : ce script contrôle les URLs en PRODUCTION (monte-cristo.net).
       Lancer après un déploiement, pas avant.

Usage : python3 seo/scripts/check-pagespeed.py
        (depuis la racine du site)
"""

import json
import sys
import time
import urllib.request
import urllib.parse
import urllib.error
from pathlib import Path
from datetime import datetime

SCRIPT_DIR   = Path(__file__).parent
REPORTS_DIR  = SCRIPT_DIR.parent / "reports"
CONFIG_PATH  = SCRIPT_DIR.parent / "config" / "pages.json"
BASE_URL     = "https://monte-cristo.net"
API_ENDPOINT = "https://www.googleapis.com/pagespeedonline/v5/runPagespeed"

# Pages à contrôler : les actives uniquement, limitées aux plus importantes
MAX_PAGES = 6
STRATEGY  = "mobile"  # mobile est le signal de ranking Google

# ── Chargement config ─────────────────────────────────────────────────────────

def load_pages():
    if not CONFIG_PATH.exists():
        print(f"❌ {CONFIG_PATH} introuvable.")
        sys.exit(1)
    data = json.loads(CONFIG_PATH.read_text(encoding="utf-8"))
    pages = data.get("pages", [])
    # Garder uniquement les pages actives et indexables, par priorité décroissante
    active = [p for p in pages if p.get("status") == "active" and p.get("indexable")]
    active.sort(key=lambda p: p.get("priority") or 0, reverse=True)
    return active[:MAX_PAGES]

# ── Appel API ─────────────────────────────────────────────────────────────────

def fetch_scores(url, strategy="mobile"):
    params = urllib.parse.urlencode({
        "url": url,
        "strategy": strategy,
        "category": ["performance", "seo", "accessibility"],
    }, doseq=True)
    api_url = f"{API_ENDPOINT}?{params}"
    try:
        req = urllib.request.urlopen(api_url, timeout=30)
        data = json.loads(req.read().decode("utf-8"))
        cats = data.get("lighthouseResult", {}).get("categories", {})
        return {
            "performance":   round((cats.get("performance",   {}).get("score") or 0) * 100),
            "seo":           round((cats.get("seo",           {}).get("score") or 0) * 100),
            "accessibility": round((cats.get("accessibility", {}).get("score") or 0) * 100),
            "error": None,
        }
    except urllib.error.HTTPError as e:
        if e.code == 429:
            return {"error": "rate_limit"}
        return {"error": f"HTTP {e.code}"}
    except Exception as e:
        return {"error": str(e)[:80]}

# ── Classification ────────────────────────────────────────────────────────────

def classify(scores):
    if scores.get("error"):
        return "error"
    perf = scores["performance"]
    seo  = scores["seo"]
    if perf < 50 or seo < 80:
        return "critique"
    if perf < 70:
        return "important"
    return "ok"

EMOJI = {"critique": "🔴", "important": "🟠", "ok": "✅", "error": "⚪"}

# ── Rapport Markdown ──────────────────────────────────────────────────────────

def build_report(results, generated_at):
    critiques  = [r for r in results if r["level"] == "critique"]
    importants = [r for r in results if r["level"] == "important"]

    lines = []
    a = lines.append
    a("# Contrôle PageSpeed — Monte-Cristo Patrimoine")
    a(f"*Généré le {generated_at} — stratégie : {STRATEGY}*\n")

    a("## Résumé\n")
    a("| | |")
    a("|---|---|")
    a(f"| Pages contrôlées | **{len(results)}** |")
    a(f"| 🔴 Critiques (perf < 50 ou SEO < 80) | **{len(critiques)}** |")
    a(f"| 🟠 Importants (perf < 70) | **{len(importants)}** |")
    a(f"| ✅ OK | **{len([r for r in results if r['level'] == 'ok'])}** |")
    a("")

    if not critiques and not importants:
        a("> ✅ Tous les scores sont dans les limites acceptables.\n")
    else:
        a(f"> ⚠️ **{len(critiques) + len(importants)} page(s) à optimiser.**\n")

    a("---\n## Scores par page\n")
    a("| Page | Performance | SEO | Accessibilité | Statut |")
    a("|------|:-----------:|:---:|:-------------:|--------|")
    for r in results:
        if r.get("error"):
            a(f"| `{r['url']}` | — | — | — | ⚪ Erreur : {r['error']} |")
        else:
            s = r["scores"]
            emoji = EMOJI[r["level"]]
            a(f"| `{r['url']}` | {s['performance']} | {s['seo']} | {s['accessibility']} | {emoji} |")
    a("")

    a("---\n## Repères\n")
    a("| Score | Performance | SEO |")
    a("|-------|-------------|-----|")
    a("| ✅ OK | ≥ 70 | ≥ 80 |")
    a("| 🟠 À améliorer | 50–69 | — |")
    a("| 🔴 Critique | < 50 | < 80 |")
    a("")
    a("*Les scores PageSpeed varient légèrement d'une exécution à l'autre.*")
    a("*Mobile est le signal utilisé par Google pour le ranking.*")
    a("")
    a("---")
    a("*Rapport généré par `seo/scripts/check-pagespeed.py`*")
    return "\n".join(lines)

# ── Point d'entrée ────────────────────────────────────────────────────────────

def main():
    print(f"⚡ Contrôle PageSpeed — Monte-Cristo Patrimoine")
    print(f"   Stratégie : {STRATEGY} (signal Google)\n")

    pages   = load_pages()
    results = []

    for i, page in enumerate(pages):
        url = BASE_URL + page["url"]
        print(f"   {url:<65}", end=" ", flush=True)

        if i > 0:
            time.sleep(1.5)  # respecter le rate limit de l'API sans clé

        scores = fetch_scores(url, STRATEGY)

        if scores.get("error") == "rate_limit":
            print("⚪ rate limit — attente 10s")
            time.sleep(10)
            scores = fetch_scores(url, STRATEGY)

        level = classify(scores)
        results.append({"url": page["url"], "scores": scores, "level": level, "error": scores.get("error")})

        if scores.get("error"):
            print(f"⚪ erreur : {scores['error']}")
        else:
            print(f"{EMOJI[level]}  perf:{scores['performance']}  seo:{scores['seo']}  a11y:{scores['accessibility']}")

    critiques  = len([r for r in results if r["level"] == "critique"])
    importants = len([r for r in results if r["level"] == "important"])

    print(f"\n📊 Résumé :")
    print(f"   🔴 Critiques  : {critiques}")
    print(f"   🟠 Importants : {importants}")
    print(f"   ✅ OK         : {len([r for r in results if r['level'] == 'ok'])}")

    generated_at = datetime.now().strftime("%d/%m/%Y à %H:%M")
    REPORTS_DIR.mkdir(parents=True, exist_ok=True)

    json_path = REPORTS_DIR / "pagespeed-report.json"
    json_path.write_text(json.dumps({
        "generated_at": generated_at,
        "strategy": STRATEGY,
        "summary": {"critique": critiques, "important": importants},
        "results": results,
    }, ensure_ascii=False, indent=2), encoding="utf-8")

    md_path = REPORTS_DIR / "pagespeed-report.md"
    md_path.write_text(build_report(results, generated_at), encoding="utf-8")

    print(f"\n📄 Rapports :")
    print(f"   {json_path}")
    print(f"   {md_path}")

if __name__ == "__main__":
    main()
