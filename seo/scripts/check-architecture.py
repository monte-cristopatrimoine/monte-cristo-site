#!/usr/bin/env python3
"""
Contrôle d'architecture — Monte-Cristo Patrimoine
Orchestre les contrôles de liens, URLs, pages orphelines et footer.
Produit un rapport d'architecture consolidé.

Scripts lancés :
  check-links.py   → liens internes cassés / pages futures
  check-urls.py    → cohérence URLs (canonical, sitemap, .html)
  check-orphans.py → pages sans lien entrant
  check-footer.py  → conformité du footer

Usage : python3 seo/scripts/check-architecture.py
        (depuis la racine du site)
"""

import json
import re
import subprocess
import sys
from pathlib import Path
from datetime import datetime

SCRIPT_DIR  = Path(__file__).parent
SITE_ROOT   = SCRIPT_DIR.parent.parent
REPORTS_DIR = SCRIPT_DIR.parent / "reports"

SCRIPTS = {
    "check-links":   SCRIPT_DIR / "check-links.py",
    "check-urls":    SCRIPT_DIR / "check-urls.py",
    "check-orphans": SCRIPT_DIR / "check-orphans.py",
    "check-footer":  SCRIPT_DIR / "check-footer.py",
}

REPORT_FILES = {
    "check-links":   REPORTS_DIR / "links-report.json",
    "check-orphans": REPORTS_DIR / "orphans-report.json",
    "check-footer":  REPORTS_DIR / "footer-report.json",
}

EMOJI = {"critique": "🔴", "important": "🟠", "mineur": "🟡", "ok": "✅"}

# ── Lancement des scripts ─────────────────────────────────────────────────────

def run_script(name, path):
    print(f"  ▶ {name}…", end=" ", flush=True)
    result = subprocess.run(
        [sys.executable, str(path)],
        cwd=str(SITE_ROOT),
        capture_output=True,
        text=True,
    )
    ok = result.returncode == 0
    print("OK" if ok else "ERREUR")
    if not ok:
        print(result.stderr[:200])
    return ok


# ── Lecture des rapports JSON ─────────────────────────────────────────────────

def read_summary(tool):
    path = REPORT_FILES.get(tool)
    if not path or not path.exists():
        return {"critique": 0, "important": 0, "mineur": 0}
    data = json.loads(path.read_text(encoding="utf-8"))
    s = data.get("summary", {})
    return {
        "critique":  s.get("critique", 0),
        "important": s.get("important", 0),
        "mineur":    s.get("mineur", 0) or s.get("amelioration", 0),
    }


def read_links_summary():
    path = REPORTS_DIR / "links-report.json"
    if not path.exists():
        return {"critique": 0, "important": 0, "mineur": 0}
    data = json.loads(path.read_text(encoding="utf-8"))
    s = data.get("summary", {})
    broken = s.get("broken", 0)
    future = s.get("future", 0)
    return {
        "critique":  broken,
        "important": future,
        "mineur":    0,
    }


def read_urls_summary():
    """check-urls produit un .md — on lit les chiffres depuis le tableau résumé."""
    path = REPORTS_DIR / "urls-report.md"
    if not path.exists():
        return {"critique": 0, "important": 0, "mineur": 0}
    content = path.read_text(encoding="utf-8")
    m_c = re.search(r"🔴 Critiques\s*\|\s*\*\*(\d+)\*\*", content)
    m_i = re.search(r"🟠 Importants\s*\|\s*\*\*(\d+)\*\*", content)
    return {
        "critique":  int(m_c.group(1)) if m_c else 0,
        "important": int(m_i.group(1)) if m_i else 0,
        "mineur":    0,
    }


# ── Rapport Markdown ──────────────────────────────────────────────────────────

def build_report(run_results, summaries, verdict, generated_at):
    lines = []
    a = lines.append

    a("# Rapport d'architecture — Monte-Cristo Patrimoine")
    a(f"*Généré le {generated_at}*\n")

    if verdict == "ok":
        a("## ✅ ARCHITECTURE SAINE\n")
        a("> Aucun problème de liens, URLs, orphelines ou footer détecté.\n")
    elif verdict == "warn":
        a("## 🟡 ARCHITECTURE CORRECTE — points mineurs\n")
        a("> Des améliorations mineures sont disponibles mais non bloquantes.\n")
    else:
        a("## ❌ PROBLÈMES D'ARCHITECTURE DÉTECTÉS\n")
        a("> Des pages sont cassées, orphelines ou ont un footer non conforme.\n")

    a("---\n## Résultats par contrôle\n")
    a("| Contrôle | Critiques 🔴 | Importants 🟠 | Mineurs 🟡 | Statut |")
    a("|----------|:-----------:|:------------:|:----------:|--------|")

    labels = {
        "check-links":   "Liens internes",
        "check-urls":    "Cohérence URLs",
        "check-orphans": "Pages orphelines",
        "check-footer":  "Footer",
    }

    for tool, label in labels.items():
        s      = summaries.get(tool, {})
        c, i, m = s.get("critique", 0), s.get("important", 0), s.get("mineur", 0)
        ok     = run_results.get(tool, False)
        status = "✅" if ok and c == 0 and i == 0 else ("🟡" if ok and c == 0 and i == 0 and m > 0 else ("🟠" if c == 0 else "🔴"))
        a(f"| {label} | {c} | {i} | {m} | {status} |")

    total_c = sum(s.get("critique", 0)  for s in summaries.values())
    total_i = sum(s.get("important", 0) for s in summaries.values())
    total_m = sum(s.get("mineur", 0)    for s in summaries.values())
    a(f"\n**Total :** 🔴 {total_c} critique(s) — 🟠 {total_i} important(s) — 🟡 {total_m} mineur(s)\n")

    a("---\n## Rapports détaillés\n")
    a("- `seo/reports/links-report.md` — liens internes")
    a("- `seo/reports/urls-report.md` — cohérence URLs")
    a("- `seo/reports/orphans-report.md` — pages orphelines")
    a("- `seo/reports/footer-report.md` — footer")
    a("")
    a("---")
    a("*Rapport généré par `seo/scripts/check-architecture.py`*")
    return "\n".join(lines)


# ── Point d'entrée ────────────────────────────────────────────────────────────

def main():
    generated_at = datetime.now().strftime("%d/%m/%Y à %H:%M")
    print(f"🏗️  Contrôle d'architecture — Monte-Cristo Patrimoine")
    print(f"   {generated_at}\n")
    print("Contrôles :")

    run_results = {}
    for name, path in SCRIPTS.items():
        run_results[name] = run_script(name, path)

    print()

    summaries = {
        "check-links":   read_links_summary(),
        "check-urls":    read_urls_summary(),
        "check-orphans": read_summary("check-orphans"),
        "check-footer":  read_summary("check-footer"),
    }

    total_c = sum(s.get("critique", 0)  for s in summaries.values())
    total_i = sum(s.get("important", 0) for s in summaries.values())
    total_m = sum(s.get("mineur", 0)    for s in summaries.values())

    if total_c > 0 or total_i > 0:
        verdict = "error"
    elif total_m > 0:
        verdict = "warn"
    else:
        verdict = "ok"

    print(f"📊 Résultats consolidés :")
    print(f"   🔴 Critiques  : {total_c}")
    print(f"   🟠 Importants : {total_i}")
    print(f"   🟡 Mineurs    : {total_m}")
    print()

    if verdict == "ok":
        print("✅  Architecture saine.")
    elif verdict == "warn":
        print("🟡  Architecture correcte — quelques points mineurs.")
    else:
        print("❌  Problèmes détectés — consulter les rapports détaillés.")

    REPORTS_DIR.mkdir(parents=True, exist_ok=True)
    report_path = REPORTS_DIR / "architecture-report.md"
    report_path.write_text(
        build_report(run_results, summaries, verdict, generated_at),
        encoding="utf-8",
    )

    json_path = REPORTS_DIR / "architecture-report.json"
    json_path.write_text(json.dumps({
        "generated_at": generated_at,
        "verdict":      verdict,
        "summary": {
            "critique":  total_c,
            "important": total_i,
            "mineur":    total_m,
        },
        "tools": summaries,
    }, ensure_ascii=False, indent=2), encoding="utf-8")

    print(f"\n📄 Rapport : {report_path}")


if __name__ == "__main__":
    main()
