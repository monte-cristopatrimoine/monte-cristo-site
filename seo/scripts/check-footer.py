#!/usr/bin/env python3
"""
Contrôle du footer — Monte-Cristo Patrimoine
Vérifie que le footer de chaque page est conforme au footer de référence (index.html).

Éléments vérifiés :
  - Liens de navigation footer (Cabinet, Services)
  - Liens légaux (mentions légales, politique de confidentialité)
  - Contact (téléphone, email, LinkedIn)
  - Badge ORIAS
  - Texte légal (raison sociale, n° RCS)
  - Copyright

Niveaux :
  critique  — lien légal ou ORIAS manquant
  important — lien de navigation manquant
  mineur    — copyright ou texte de présentation manquant

Usage : python3 seo/scripts/check-footer.py
        (depuis la racine du site)
"""

import json
import re
import sys
from pathlib import Path
from datetime import datetime

SCRIPT_DIR  = Path(__file__).parent
SITE_ROOT   = SCRIPT_DIR.parent.parent
REPORTS_DIR = SCRIPT_DIR.parent / "reports"
CONFIG_PATH = SCRIPT_DIR.parent / "config" / "pages.json"

SKIP = {"mockup-contenu.html", "404.html"}  # footers intentionnellement simplifiés

# Éléments obligatoires du footer, avec leur niveau de criticité
FOOTER_CHECKS = [
    # (label, pattern_ou_substr, niveau)
    ("ORIAS badge",              "orias.fr",                           "critique"),
    ("Lien mentions légales",    'href="/mentions-legales"',           "critique"),
    ("Lien politique conf.",     'href="/politique-confidentialite"',  "critique"),
    ("Téléphone",                "tel:+33",                            "critique"),
    ("Email",                    "mailto:kevin@monte-cristo.net",      "critique"),
    ("Lien /le-cabinet",         'href="/le-cabinet"',                 "important"),
    ("Lien /particuliers",       'href="/particuliers"',               "important"),
    ("Lien /entreprises",        'href="/entreprises"',                "important"),
    ("Lien /blog",               'href="/blog"',                      "important"),
    ("Lien LinkedIn",            "linkedin.com/company/",             "important"),
    ("Texte légal (RCS)",        "RCS",                               "important"),
    ("Copyright",                "© 2026",                            "mineur"),
    ("Description cabinet",      "Cabinet de conseil en gestion",     "mineur"),
]

EMOJI = {"critique": "🔴", "important": "🟠", "mineur": "🟡", "ok": "✅"}

# ── Extraction du footer ──────────────────────────────────────────────────────

FOOTER_RE = re.compile(r"<footer[^>]*>(.*?)</footer>", re.S | re.I)

def extract_footer(html: str) -> str:
    m = FOOTER_RE.search(html)
    return m.group(0) if m else ""


# ── Analyse ───────────────────────────────────────────────────────────────────

def check_page_footer(footer_html: str) -> list[dict]:
    issues = []
    for label, pattern, level in FOOTER_CHECKS:
        if pattern not in footer_html:
            issues.append({"label": label, "pattern": pattern, "level": level})
    return issues


# ── Rapport Markdown ──────────────────────────────────────────────────────────

def build_report(results, generated_at):
    all_issues = [i for r in results for i in r["issues"]]
    critiques  = [i for i in all_issues if i["level"] == "critique"]
    importants = [i for i in all_issues if i["level"] == "important"]
    mineurs    = [i for i in all_issues if i["level"] == "mineur"]
    pages_ok   = [r for r in results if not r["issues"]]

    lines = []
    a = lines.append
    a("# Contrôle footer — Monte-Cristo Patrimoine")
    a(f"*Généré le {generated_at}*\n")

    a("## Résumé\n")
    a("| | |")
    a("|---|---|")
    a(f"| Pages contrôlées | **{len(results)}** |")
    a(f"| ✅ Pages conformes | **{len(pages_ok)}** |")
    a(f"| 🔴 Problèmes critiques | **{len(critiques)}** |")
    a(f"| 🟠 Problèmes importants | **{len(importants)}** |")
    a(f"| 🟡 Problèmes mineurs | **{len(mineurs)}** |")
    a("")

    if not all_issues:
        a("> ✅ Tous les footers sont conformes.\n")
    else:
        a(f"> ⚠️ **{len([r for r in results if r['issues']])} page(s) avec footer non conforme.**\n")

    pages_with_issues = [r for r in results if r["issues"]]
    if pages_with_issues:
        a("---\n## Détail par page\n")
        for r in pages_with_issues:
            a(f"### `{r['file']}`\n")
            if not r["footer_found"]:
                a("❌ **Aucun footer `<footer>` trouvé dans cette page.**\n")
                continue
            a("| Élément manquant | Niveau |")
            a("|------------------|--------|")
            for i in r["issues"]:
                emoji = EMOJI.get(i["level"], "—")
                a(f"| {i['label']} | {emoji} {i['level']} |")
            a("")

    a("---")
    a("*Rapport généré par `seo/scripts/check-footer.py`*")
    return "\n".join(lines)


# ── Point d'entrée ────────────────────────────────────────────────────────────

def main():
    if not CONFIG_PATH.exists():
        print(f"❌ {CONFIG_PATH} introuvable.")
        sys.exit(1)

    print("🦶 Contrôle footer — Monte-Cristo Patrimoine\n")

    data  = json.loads(CONFIG_PATH.read_text(encoding="utf-8"))
    pages = [p for p in data["pages"] if p.get("has_footer") and p["file"] not in SKIP]

    results = []
    for p in pages:
        path = SITE_ROOT / p["file"]
        if not path.exists():
            continue
        html         = path.read_text(encoding="utf-8", errors="ignore")
        footer_html  = extract_footer(html)
        footer_found = bool(footer_html)
        issues       = check_page_footer(footer_html) if footer_found else [
            {"label": "Footer <footer> absent", "pattern": "<footer>", "level": "critique"}
        ]
        results.append({
            "file":         p["file"],
            "url":          p["url"],
            "footer_found": footer_found,
            "issues":       issues,
        })

    all_issues = [i for r in results for i in r["issues"]]
    critiques  = [i for i in all_issues if i["level"] == "critique"]
    importants = [i for i in all_issues if i["level"] == "important"]
    mineurs    = [i for i in all_issues if i["level"] == "mineur"]

    print(f"📊 Résumé ({len(results)} pages) :")
    print(f"   🔴 Critiques  : {len(critiques)}")
    print(f"   🟠 Importants : {len(importants)}")
    print(f"   🟡 Mineurs    : {len(mineurs)}")

    for r in results:
        status = "✅" if not r["issues"] else ("🔴" if any(i["level"] == "critique" for i in r["issues"]) else "🟠")
        print(f"   {status}  {r['file']}")

    generated_at = datetime.now().strftime("%d/%m/%Y à %H:%M")
    REPORTS_DIR.mkdir(parents=True, exist_ok=True)

    summary = {
        "critique":    len(critiques),
        "important":   len(importants),
        "mineur":      len(mineurs),
        "amelioration": 0,
    }

    md_path   = REPORTS_DIR / "footer-report.md"
    json_path = REPORTS_DIR / "footer-report.json"

    md_path.write_text(build_report(results, generated_at), encoding="utf-8")
    json_path.write_text(json.dumps({
        "generated_at": generated_at,
        "summary":      summary,
        "pages":        results,
    }, ensure_ascii=False, indent=2), encoding="utf-8")

    print(f"\n📄 Rapports :")
    print(f"   {md_path}")
    print(f"   {json_path}")


if __name__ == "__main__":
    main()
