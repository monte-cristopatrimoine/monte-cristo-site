#!/usr/bin/env python3
"""
Générateur de sitemap — Monte-Cristo Patrimoine
Génère sitemap.xml à la racine du site à partir des fichiers HTML.

Règles d'inclusion :
- Seuls les fichiers .html à la racine sont analysés
- Exclut les pages avec <meta name="robots" content="noindex...">
- Exclut 404.html (page d'erreur technique)
- Exclut mockup-contenu.html (page de travail)
- Inclut mentions-legales.html et politique-confidentialite.html
- <lastmod> calculé depuis la date de modification du fichier

Usage : python3 seo/scripts/generate-sitemap.py
        (depuis la racine du site)
"""

import re
import sys
from pathlib import Path
from datetime import datetime, timezone

SCRIPT_DIR  = Path(__file__).parent
SITE_ROOT   = SCRIPT_DIR.parent.parent
REPORTS_DIR = SCRIPT_DIR.parent / "reports"
BASE_URL    = "https://monte-cristo.net"

# Exclusions fixes — jamais dans le sitemap
ALWAYS_EXCLUDE = {"404.html", "mockup-contenu.html"}

# Priorités par page (défaut 0.5 si non listé)
PRIORITIES = {
    "index.html":                  ("1.0", "monthly"),
    "le-cabinet.html":             ("0.9", "monthly"),
    "particuliers.html":           ("0.9", "monthly"),
    "entreprises.html":            ("0.9", "monthly"),
    "blog.html":                   ("0.8", "weekly"),
    "article-cgp-independant.html":("0.7", "monthly"),
    "article-frais-bancaires.html":("0.7", "monthly"),
    "simulateur-frais.html":       ("0.6", "monthly"),
    "politique-confidentialite.html": ("0.3", "yearly"),
    "mentions-legales.html":       ("0.2", "yearly"),
}

def has_noindex(html):
    """Retourne True si la page contient une directive noindex."""
    return bool(re.search(
        r'<meta\s[^>]*name=["\']robots["\'][^>]*content=["\'][^"\']*noindex',
        html, re.IGNORECASE
    ))

def file_to_url(filename):
    name = filename.replace(".html", "")
    return BASE_URL + "/" if name == "index" else f"{BASE_URL}/{name}"

def file_lastmod(filepath):
    """Date de dernière modification du fichier au format W3C (YYYY-MM-DD)."""
    mtime = filepath.stat().st_mtime
    return datetime.fromtimestamp(mtime, tz=timezone.utc).strftime("%Y-%m-%d")

def build_sitemap_xml(entries):
    lines = ['<?xml version="1.0" encoding="UTF-8"?>']
    lines.append('<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">')
    for e in entries:
        lines.append("")
        lines.append("  <url>")
        lines.append(f"    <loc>{e['url']}</loc>")
        lines.append(f"    <lastmod>{e['lastmod']}</lastmod>")
        lines.append(f"    <changefreq>{e['changefreq']}</changefreq>")
        lines.append(f"    <priority>{e['priority']}</priority>")
        lines.append("  </url>")
    lines.append("")
    lines.append("</urlset>")
    return "\n".join(lines)

def build_report(entries, excluded, generated_at):
    lines = []
    a = lines.append
    a(f"# Rapport sitemap — Monte-Cristo Patrimoine")
    a(f"*Généré le {generated_at}*\n")
    a(f"## URLs incluses ({len(entries)})\n")
    a("| URL | Priorité | Fréquence | Dernière modif. |")
    a("|-----|----------|-----------|-----------------|")
    for e in entries:
        a(f"| {e['url']} | {e['priority']} | {e['changefreq']} | {e['lastmod']} |")
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

def main():
    print("🗺️  Générateur de sitemap — Monte-Cristo Patrimoine")
    print(f"   Racine : {SITE_ROOT}\n")

    html_files = sorted(SITE_ROOT.glob("*.html"))
    if not html_files:
        print("❌ Aucun fichier .html trouvé.")
        sys.exit(1)

    entries  = []
    excluded = []

    # Ordre d'apparition dans le sitemap : selon PRIORITIES, puis alphabétique
    priority_order = list(PRIORITIES.keys())

    def sort_key(f):
        try:
            return priority_order.index(f.name)
        except ValueError:
            return len(priority_order)

    for filepath in sorted(html_files, key=sort_key):
        filename = filepath.name

        if filename in ALWAYS_EXCLUDE:
            excluded.append((filename, "Page exclue (technique ou travail)"))
            continue

        html = filepath.read_text(encoding="utf-8", errors="replace")

        if has_noindex(html):
            excluded.append((filename, "Balise `noindex` détectée"))
            continue

        priority, changefreq = PRIORITIES.get(filename, ("0.5", "monthly"))
        url     = file_to_url(filename)
        lastmod = file_lastmod(filepath)

        entries.append({
            "file":       filename,
            "url":        url,
            "priority":   priority,
            "changefreq": changefreq,
            "lastmod":    lastmod,
        })

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
    print(f"{'URL':<55} {'Priorité':>8}  Lastmod")
    print("-" * 75)
    for e in entries:
        print(f"{e['url']:<55} {e['priority']:>8}  {e['lastmod']}")

    if excluded:
        print(f"\nExclus :")
        for name, reason in excluded:
            print(f"   ⛔ {name} — {reason}")

    print(f"\n✅ sitemap.xml généré : {len(entries)} URL(s)")
    print(f"📄 Rapport : {report_path}")

if __name__ == "__main__":
    main()
