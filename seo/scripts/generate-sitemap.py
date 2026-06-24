#!/usr/bin/env python3
"""
Générateur de sitemap — Monte-Cristo Patrimoine
Génère sitemap.xml à la racine du site depuis seo/config/pages.json.

Règles d'inclusion (depuis pages.json) :
- indexable: true
- sitemap: true
- status: "active"

Les priorités, changefreq et URLs sont lues depuis pages.json.
Le <lastmod> est calculé depuis la date de modification réelle du fichier.

Usage : python3 seo/scripts/generate-sitemap.py
        (depuis la racine du site)
"""

import json
import sys
from pathlib import Path
from datetime import datetime, timezone

SCRIPT_DIR  = Path(__file__).parent
SITE_ROOT   = SCRIPT_DIR.parent.parent
REPORTS_DIR = SCRIPT_DIR.parent / "reports"
CONFIG_PATH = SCRIPT_DIR.parent / "config" / "pages.json"
BASE_URL    = "https://monte-cristo.net"

# ── Lecture de la configuration ───────────────────────────────────────────────

def load_pages():
    if not CONFIG_PATH.exists():
        print(f"❌ Fichier de configuration introuvable : {CONFIG_PATH}")
        print("   Lancez d'abord : python3 seo/scripts/bootstrap-pages.py")
        sys.exit(1)
    data = json.loads(CONFIG_PATH.read_text(encoding="utf-8"))
    return data.get("pages", [])

def should_include(page):
    return (
        page.get("indexable") is True
        and page.get("sitemap") is True
        and page.get("status") == "active"
    )

def exclude_reason(page):
    if page.get("status") == "legal":
        return f"Page légale (status: legal)"
    if page.get("status") == "work":
        return "Page de travail (status: work)"
    if page.get("status") == "technical":
        return "Page technique (status: technical)"
    if not page.get("indexable"):
        return "Non indexable (indexable: false)"
    if not page.get("sitemap"):
        return "Exclue du sitemap (sitemap: false)"
    return "Exclue"

# ── lastmod depuis le fichier ─────────────────────────────────────────────────

def file_lastmod(filepath):
    mtime = filepath.stat().st_mtime
    return datetime.fromtimestamp(mtime, tz=timezone.utc).strftime("%Y-%m-%d")

# ── Génération du XML ─────────────────────────────────────────────────────────

def build_sitemap_xml(entries):
    lines = ['<?xml version="1.0" encoding="UTF-8"?>']
    lines.append('<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">')
    for e in entries:
        lines.append("")
        lines.append("  <url>")
        lines.append(f"    <loc>{BASE_URL}{e['url']}</loc>")
        lines.append(f"    <lastmod>{e['lastmod']}</lastmod>")
        lines.append(f"    <changefreq>{e['changefreq']}</changefreq>")
        lines.append(f"    <priority>{e['priority']}</priority>")
        lines.append("  </url>")
    lines.append("")
    lines.append("</urlset>")
    return "\n".join(lines)

# ── Rapport Markdown ──────────────────────────────────────────────────────────

def build_report(entries, excluded, generated_at):
    lines = []
    a = lines.append
    a("# Rapport sitemap — Monte-Cristo Patrimoine")
    a(f"*Généré le {generated_at} — source : `seo/config/pages.json`*\n")
    a(f"## URLs incluses ({len(entries)})\n")
    a("| URL | Priorité | Fréquence | Dernière modif. |")
    a("|-----|----------|-----------|-----------------|")
    for e in entries:
        a(f"| {BASE_URL}{e['url']} | {e['priority']} | {e['changefreq']} | {e['lastmod']} |")
    a("")
    a(f"## Pages exclues ({len(excluded)})\n")
    if excluded:
        a("| Fichier | Raison |")
        a("|---------|--------|")
        for name, reason in excluded:
            a(f"| `{name}` | {reason} |")
    else:
        a("Aucune exclusion.")
    a("")
    a("---")
    a("*Rapport généré par `seo/scripts/generate-sitemap.py`*")
    return "\n".join(lines)

# ── Point d'entrée ────────────────────────────────────────────────────────────

def main():
    print("🗺️  Générateur de sitemap — Monte-Cristo Patrimoine")
    print(f"   Configuration : {CONFIG_PATH}\n")

    pages = load_pages()

    entries  = []
    excluded = []

    for page in pages:
        filename = page.get("file", "")
        filepath = SITE_ROOT / filename

        if should_include(page):
            if not filepath.exists():
                print(f"   ⚠️  Fichier déclaré dans pages.json mais introuvable : {filename}")
                excluded.append((filename, "Fichier HTML introuvable sur le disque"))
                continue

            entries.append({
                "file":       filename,
                "url":        page["url"],
                "priority":   page["priority"],
                "changefreq": page["changefreq"],
                "lastmod":    file_lastmod(filepath),
            })
        else:
            excluded.append((filename, exclude_reason(page)))

    if not entries:
        print("❌ Aucune page à inclure dans le sitemap.")
        sys.exit(1)

    # Écrire sitemap.xml
    sitemap_path = SITE_ROOT / "sitemap.xml"
    sitemap_xml  = build_sitemap_xml(entries)
    sitemap_path.write_text(sitemap_xml + "\n", encoding="utf-8")

    # Écrire rapport
    generated_at = datetime.now().strftime("%d/%m/%Y à %H:%M")
    REPORTS_DIR.mkdir(parents=True, exist_ok=True)
    report_path  = REPORTS_DIR / "sitemap-report.md"
    report_path.write_text(build_report(entries, excluded, generated_at), encoding="utf-8")

    # Affichage terminal
    print(f"{'URL':<60} {'Priorité':>8}  Lastmod")
    print("-" * 80)
    for e in entries:
        print(f"{BASE_URL + e['url']:<60} {e['priority']:>8}  {e['lastmod']}")

    if excluded:
        print(f"\nExclus ({len(excluded)}) :")
        for name, reason in excluded:
            print(f"   ⛔ {name:<50} {reason}")

    print(f"\n✅ sitemap.xml généré : {len(entries)} URL(s)")
    print(f"📄 Rapport            : {report_path}")

if __name__ == "__main__":
    main()
