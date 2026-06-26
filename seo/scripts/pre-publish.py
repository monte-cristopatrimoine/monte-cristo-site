#!/usr/bin/env python3
"""
Checklist pré-publication — Monte-Cristo Patrimoine
Lance tous les outils SEO et produit un verdict global.

Usage : python3 seo/scripts/pre-publish.py
        (depuis la racine du site)

Statuts possibles :
  ✅ PUBLIABLE           — aucun problème critique ou important
  ⚠️  PUBLIABLE (corrections mineures) — uniquement des améliorations
  ❌ À CORRIGER          — au moins 1 critique ou important
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
    "audit":            SCRIPT_DIR / "audit.py",
    "check-meta":       SCRIPT_DIR / "check-meta.py",
    "generate-sitemap": SCRIPT_DIR / "generate-sitemap.py",
    "check-robots":     SCRIPT_DIR / "check-robots.py",
    "check-header-css": SCRIPT_DIR / "check-header-css.py",
}

REPORT_FILES = {
    "audit":            REPORTS_DIR / "site-audit.json",
    "check-meta":       REPORTS_DIR / "meta-check.json",
    "check-robots":     REPORTS_DIR / "robots-check.md",
    "check-header-css": REPORTS_DIR / "header-css-check.json",
}

# ── Lancement des scripts ─────────────────────────────────────────────────────

def run_script(name, path):
    print(f"  ▶ {name}…", end=" ", flush=True)
    result = subprocess.run(
        [sys.executable, str(path)],
        cwd=str(SITE_ROOT),
        capture_output=True,
        text=True
    )
    if result.returncode == 0:
        print("OK")
    else:
        print("ERREUR")
        print(result.stderr[:300])
    return result.returncode == 0, result.stdout, result.stderr

# ── Lecture des rapports JSON ─────────────────────────────────────────────────

def read_audit_summary():
    path = REPORT_FILES["audit"]
    if not path.exists():
        return None
    data = json.loads(path.read_text(encoding="utf-8"))
    return data.get("summary", {})

def read_meta_summary():
    path = REPORT_FILES["check-meta"]
    if not path.exists():
        return None
    data = json.loads(path.read_text(encoding="utf-8"))
    return data.get("summary", {})

def read_json_summary(tool):
    """Lecture générique d'un rapport JSON avec clé 'summary'."""
    path = REPORT_FILES.get(tool)
    if not path or not path.exists():
        return None
    data = json.loads(path.read_text(encoding="utf-8"))
    return data.get("summary", {})

def read_robots_summary():
    """Extrait les compteurs depuis robots-check.md (pas de JSON pour ce rapport)."""
    path = REPORT_FILES["check-robots"]
    if not path.exists():
        return None
    content = path.read_text(encoding="utf-8")
    def extract_count(label):
        m = re.search(rf"\| [^|]*{re.escape(label)}[^|]* \| \*\*(\d+)\*\* \|", content)
        return int(m.group(1)) if m else 0
    return {
        "critique":    extract_count("critiques"),
        "important":   extract_count("importants"),
        "amelioration":extract_count("Améliorations"),
    }

# ── Rapport Markdown ──────────────────────────────────────────────────────────

def build_report(results, totals, verdict, generated_at):
    lines = []
    a = lines.append

    a("# Rapport pré-publication — Monte-Cristo Patrimoine")
    a(f"*Généré le {generated_at}*\n")

    # Verdict en tête
    if verdict == "ok":
        a("## ✅ PUBLIABLE\n")
        a("> Aucun problème critique ou important détecté. Le site peut être déployé.\n")
    elif verdict == "warn":
        a("## ⚠️ PUBLIABLE — corrections mineures recommandées\n")
        a("> Pas de blocage. Des améliorations sont disponibles mais non urgentes.\n")
    else:
        a("## ❌ À CORRIGER AVANT PUBLICATION\n")
        a("> Des problèmes critiques ou importants ont été détectés. Corrigez-les avant de déployer.\n")

    # Tableau des résultats par outil
    a("---\n## Résultats par outil\n")
    a("| Outil | Critiques 🔴 | Importants 🟠 | Améliorations 🟡 | Statut |")
    a("|-------|:-----------:|:------------:|:----------------:|--------|")
    for tool, summary in totals.items():
        c = summary.get("critique", 0)
        i = summary.get("important", 0)
        am = summary.get("amelioration", 0)
        ok = results[tool]
        status = "✅" if ok and c == 0 and i == 0 else ("⚠️" if ok and c == 0 else "❌")
        a(f"| `{tool}` | {c} | {i} | {am} | {status} |")
    a("")

    # Total consolidé
    total_c  = sum(s.get("critique", 0)     for s in totals.values())
    total_i  = sum(s.get("important", 0)    for s in totals.values())
    total_am = sum(s.get("amelioration", 0) for s in totals.values())
    a(f"**Total consolidé :** 🔴 {total_c} critique(s) — 🟠 {total_i} important(s) — 🟡 {total_am} amélioration(s)\n")

    # Checklist de publication
    a("---\n## Checklist avant publication\n")
    checks = [
        ("robots.txt propre (sans règles inutiles)",          totals.get("check-robots", {}).get("important", 0) == 0),
        ("sitemap.xml à jour",                                results.get("generate-sitemap", False)),
        ("Titres et descriptions dans les limites",           totals.get("audit", {}).get("critique", 0) == 0),
        ("Métadonnées cohérentes (og:, twitter:)",            totals.get("check-meta", {}).get("critique", 0) == 0),
        ("Aucune page critique sans H1",                      totals.get("audit", {}).get("critique", 0) == 0),
        ("Aucun doublon de métadonnées",                      totals.get("check-meta", {}).get("duplicates", 0) == 0 if "duplicates" in totals.get("check-meta", {}) else True),
    ]
    for label, passed in checks:
        icon = "✅" if passed else "❌"
        a(f"- {icon} {label}")
    a("")

    a("---")
    a("*Rapport généré par `seo/scripts/pre-publish.py`*")
    a(f"*Scripts exécutés : audit.py · check-meta.py · generate-sitemap.py · check-robots.py*")
    return "\n".join(lines)

# ── Point d'entrée ────────────────────────────────────────────────────────────

def main():
    generated_at = datetime.now().strftime("%d/%m/%Y à %H:%M")
    print(f"🚀 Checklist pré-publication — Monte-Cristo Patrimoine")
    print(f"   {generated_at}\n")
    print("Lancement des contrôles :")

    results = {}
    for name, path in SCRIPTS.items():
        ok, stdout, stderr = run_script(name, path)
        results[name] = ok

    print()

    # Lecture des résumés
    audit_sum      = read_audit_summary()   or {"critique": 0, "important": 0, "amelioration": 0}
    meta_sum       = read_meta_summary()    or {"critique": 0, "important": 0, "amelioration": 0}
    robots_sum     = read_robots_summary()  or {"critique": 0, "important": 0, "amelioration": 0}
    header_css_sum = read_json_summary("check-header-css") or {"critique": 0, "important": 0, "amelioration": 0}
    # generate-sitemap n'a pas de JSON — on le considère ok si le script a réussi
    sitemap_sum = {"critique": 0 if results.get("generate-sitemap") else 1, "important": 0, "amelioration": 0}

    totals = {
        "audit":            audit_sum,
        "check-meta":       meta_sum,
        "generate-sitemap": sitemap_sum,
        "check-robots":     robots_sum,
        "check-header-css": header_css_sum,
    }

    total_c  = sum(s.get("critique", 0)  for s in totals.values())
    total_i  = sum(s.get("important", 0) for s in totals.values())
    total_am = sum(s.get("amelioration", 0) for s in totals.values())

    # Verdict
    if total_c > 0 or total_i > 0:
        verdict = "error"
    elif total_am > 0:
        verdict = "warn"
    else:
        verdict = "ok"

    # Affichage terminal
    print(f"📊 Résultats consolidés :")
    print(f"   🔴 Critiques    : {total_c}")
    print(f"   🟠 Importants   : {total_i}")
    print(f"   🟡 Améliorations: {total_am}")
    print()

    if verdict == "ok":
        print("✅  PUBLIABLE — aucun problème bloquant.")
    elif verdict == "warn":
        print("⚠️   PUBLIABLE — des améliorations sont disponibles mais non urgentes.")
    else:
        print("❌  À CORRIGER AVANT PUBLICATION — voir le rapport pour les détails.")

    # Rapport
    REPORTS_DIR.mkdir(parents=True, exist_ok=True)
    report_path = REPORTS_DIR / "pre-publish-report.md"
    report_path.write_text(
        build_report(results, totals, verdict, generated_at),
        encoding="utf-8"
    )
    print(f"\n📄 Rapport complet : {report_path}")

if __name__ == "__main__":
    main()
