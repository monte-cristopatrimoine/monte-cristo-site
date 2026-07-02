#!/usr/bin/env python3
"""
Contrôle des pages orphelines — Monte-Cristo Patrimoine
Détecte les pages actives qui ne sont liées par aucune autre page
et ne figurent ni dans la navigation principale ni dans le footer.

Une page orpheline est invisible pour Google : les liens entrants
sont le seul moyen pour les robots de la découvrir et de lui transférer
de l'autorité.

Niveaux :
  critique  — page pilier ou service non liée (cocon SEO cassé)
  important — article ou outil non lié
  ok        — toutes les pages actives sont accessibles

Usage : python3 seo/scripts/check-orphans.py
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

SKIP_TYPES   = {"technique", "travail"}
SKIP_STATUSES = {"work"}
SKIP_URLS    = {"/", "/404"}

# ── Chargement ────────────────────────────────────────────────────────────────

def load_pages():
    data = json.loads(CONFIG_PATH.read_text(encoding="utf-8"))
    return data["pages"]


def load_html_files(pages):
    """Retourne {url: html_content} pour toutes les pages ayant un fichier."""
    result = {}
    for p in pages:
        path = SITE_ROOT / p["file"]
        if path.exists():
            result[p["url"]] = path.read_text(encoding="utf-8", errors="ignore")
    return result


# ── Extraction des liens ──────────────────────────────────────────────────────

HREF_RE = re.compile(r'href=["\']([^"\']+)["\']', re.I)

def extract_internal_links(html: str) -> set:
    """Extrait toutes les URLs internes absolues (sans .html) depuis le HTML."""
    links = set()
    for href in HREF_RE.findall(html):
        href = href.strip()
        # Ignore: externe, mailto, tel, ancre pure, vide
        if not href or href.startswith(("http", "mailto:", "tel:", "#", "//")):
            continue
        # Normalise : retire ancre, retire .html
        href = href.split("#")[0].rstrip("/") or "/"
        href = re.sub(r"\.html$", "", href)
        links.add(href)
    return links


# ── Analyse ───────────────────────────────────────────────────────────────────

def classify_level(page: dict) -> str:
    t = page.get("type", "")
    if t in ("pilier", "service", "institutionnelle"):
        return "critique"
    return "important"


def check_orphans(pages, html_map):
    # Construire l'ensemble de toutes les URLs ciblées par des liens dans tout le site
    all_linked = set()
    for url, html in html_map.items():
        links = extract_internal_links(html)
        for link in links:
            if link != url:  # un lien vers soi-même ne compte pas
                all_linked.add(link)

    # Pages potentiellement orphelines : actives, ni dans nav ni dans footer
    issues = []
    for p in pages:
        if p.get("status") in SKIP_STATUSES:
            continue
        if p.get("type") in SKIP_TYPES:
            continue
        if p["url"] in SKIP_URLS:
            continue
        if p.get("in_main_nav") or p.get("in_footer_nav"):
            continue  # accessible via navigation globale

        url = p["url"]
        linked_by = [u for u, html in html_map.items()
                     if url in extract_internal_links(html) and u != url]

        if not linked_by:
            level = classify_level(p)
            issues.append({
                "url":    url,
                "file":   p["file"],
                "type":   p.get("type", "—"),
                "level":  level,
                "status": p.get("status", "—"),
            })

    return issues


# ── Rapport Markdown ──────────────────────────────────────────────────────────

def build_report(issues, total_checked, generated_at):
    critiques  = [i for i in issues if i["level"] == "critique"]
    importants = [i for i in issues if i["level"] == "important"]

    lines = []
    a = lines.append
    a("# Contrôle des pages orphelines — Monte-Cristo Patrimoine")
    a(f"*Généré le {generated_at}*\n")

    a("## Résumé\n")
    a("| | |")
    a("|---|---|")
    a(f"| Pages analysées | **{total_checked}** |")
    a(f"| 🔴 Orphelines critiques (pilier/service sans lien entrant) | **{len(critiques)}** |")
    a(f"| 🟠 Orphelines importantes (article/outil sans lien entrant) | **{len(importants)}** |")
    a("")

    if not issues:
        a("> ✅ Aucune page orpheline détectée.\n")
    else:
        a(f"> ⚠️ **{len(issues)} page(s) orpheline(s)** — non liées depuis aucune autre page "
          "(et absentes de la navigation globale).\n")
        a("---\n## Détail\n")
        a("| Page | Type | Niveau |")
        a("|------|------|--------|")
        for i in sorted(issues, key=lambda x: x["level"]):
            emoji = "🔴" if i["level"] == "critique" else "🟠"
            a(f"| `{i['url']}` | {i['type']} | {emoji} {i['level']} |")
        a("")
        a("### Comment corriger\n")
        a("Ajouter au moins un lien entrant depuis une autre page active :")
        a("- Page pilier du même cocon")
        a("- Page blog ou hub de catégorie")
        a("- Footer (si la page a une valeur de navigation permanente)")

    a("\n---")
    a("*Rapport généré par `seo/scripts/check-orphans.py`*")
    return "\n".join(lines)


# ── Point d'entrée ────────────────────────────────────────────────────────────

def main():
    if not CONFIG_PATH.exists():
        print(f"❌ {CONFIG_PATH} introuvable.")
        sys.exit(1)

    print("🔗 Contrôle des pages orphelines — Monte-Cristo Patrimoine\n")

    pages    = load_pages()
    html_map = load_html_files(pages)

    # Pages à contrôler (actives, non travail, non skip)
    checked = [
        p for p in pages
        if p.get("status") not in SKIP_STATUSES
        and p.get("type") not in SKIP_TYPES
        and p["url"] not in SKIP_URLS
        and not p.get("in_main_nav")
        and not p.get("in_footer_nav")
    ]

    print(f"   Pages potentiellement orphelines à vérifier : {len(checked)}")
    issues = check_orphans(pages, html_map)

    critiques  = [i for i in issues if i["level"] == "critique"]
    importants = [i for i in issues if i["level"] == "important"]

    print(f"\n📊 Résumé :")
    print(f"   🔴 Critiques  : {len(critiques)}")
    print(f"   🟠 Importants : {len(importants)}")

    if issues:
        for i in issues:
            emoji = "🔴" if i["level"] == "critique" else "🟠"
            print(f"   {emoji}  {i['url']}  ({i['type']})")
    else:
        print("   ✅ Aucune page orpheline.")

    generated_at = datetime.now().strftime("%d/%m/%Y à %H:%M")
    REPORTS_DIR.mkdir(parents=True, exist_ok=True)

    md_path   = REPORTS_DIR / "orphans-report.md"
    json_path = REPORTS_DIR / "orphans-report.json"

    md_path.write_text(build_report(issues, len(checked), generated_at), encoding="utf-8")
    json_path.write_text(json.dumps({
        "generated_at": generated_at,
        "summary": {
            "checked":   len(checked),
            "critique":  len(critiques),
            "important": len(importants),
        },
        "issues": issues,
    }, ensure_ascii=False, indent=2), encoding="utf-8")

    print(f"\n📄 Rapports :")
    print(f"   {md_path}")
    print(f"   {json_path}")


if __name__ == "__main__":
    main()
