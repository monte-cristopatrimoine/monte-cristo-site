#!/usr/bin/env python3
"""
Contrôle de cohérence des URLs — Monte-Cristo Patrimoine
Vérifie que les URLs publiques du site respectent la convention sans .html.

Contrôles :
  1. Fichier HTML présent sur le disque pour chaque page déclarée
  2. Canonical correcte sur les pages indexables
  3. Pages sitemap:true présentes dans sitemap.xml
  4. Pages sitemap:false absentes de sitemap.xml
  5. Liens internes avec .html dans les fichiers HTML

Niveaux :
  critique  — fichier manquant, canonical absente/incorrecte, page indexable absente du sitemap
  important — lien interne avec .html, page non indexable présente dans sitemap

Usage : python3 seo/scripts/check-urls.py
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
SITEMAP_PATH = SITE_ROOT / "sitemap.xml"
BASE_URL    = "https://monte-cristo.net"

# ── Chargement ────────────────────────────────────────────────────────────────

def load_pages():
    if not CONFIG_PATH.exists():
        print(f"❌ {CONFIG_PATH} introuvable.")
        sys.exit(1)
    return json.loads(CONFIG_PATH.read_text(encoding="utf-8")).get("pages", [])

def load_sitemap_urls():
    if not SITEMAP_PATH.exists():
        return set()
    xml = SITEMAP_PATH.read_text(encoding="utf-8")
    locs = re.findall(r'<loc>(.*?)</loc>', xml)
    return {loc.rstrip("/") for loc in locs}

# ── Contrôles ─────────────────────────────────────────────────────────────────

def check_canonical(html, expected_url):
    m = re.search(r'<link\s[^>]*rel=["\']canonical["\'][^>]*href=["\']([^"\']+)["\']', html, re.IGNORECASE)
    if not m:
        m = re.search(r'<link\s[^>]*href=["\']([^"\']+)["\'][^>]*rel=["\']canonical["\']', html, re.IGNORECASE)
    if not m:
        return None, "absente"
    canonical = m.group(1).rstrip("/")
    expected  = (BASE_URL + expected_url).rstrip("/")
    if canonical == expected:
        return canonical, "ok"
    return canonical, f"attendu {expected}, trouvé {canonical}"

def check_html_links(html, filename):
    hrefs = re.findall(r'<a\s[^>]*href=["\']([^"\']*)["\']', html, re.IGNORECASE)
    bad = []
    for href in hrefs:
        path = href.split("?")[0].split("#")[0]
        if path.endswith(".html") and not path.startswith("http"):
            bad.append(href)
    return bad

# ── Rapport Markdown ──────────────────────────────────────────────────────────

def build_report(issues, stats, generated_at):
    critiques  = [i for i in issues if i["level"] == "critique"]
    importants = [i for i in issues if i["level"] == "important"]

    lines = []
    a = lines.append
    a("# Contrôle URLs — Monte-Cristo Patrimoine")
    a(f"*Généré le {generated_at}*\n")

    a("## Résumé\n")
    a("| | |")
    a("|---|---|")
    a(f"| Pages vérifiées | **{stats['pages']}** |")
    a(f"| 🔴 Critiques | **{len(critiques)}** |")
    a(f"| 🟠 Importants | **{len(importants)}** |")
    a("")

    if not issues:
        a("> ✅ Aucune anomalie détectée.\n")
    else:
        a(f"> ⚠️ **{len(issues)} anomalie(s) à traiter.**\n")

    if critiques:
        a("---\n## 🔴 Critiques\n")
        a("| Page | Contrôle | Détail |")
        a("|------|----------|--------|")
        for i in critiques:
            a(f"| `{i['file']}` | {i['check']} | {i['detail']} |")
        a("")

    if importants:
        a("---\n## 🟠 Importants\n")
        a("| Page | Contrôle | Détail |")
        a("|------|----------|--------|")
        for i in importants:
            a(f"| `{i['file']}` | {i['check']} | {i['detail']} |")
        a("")

    a("---")
    a("*Rapport généré par `seo/scripts/check-urls.py`*")
    return "\n".join(lines)

# ── Point d'entrée ────────────────────────────────────────────────────────────

def main():
    print("🔗 Contrôle URLs — Monte-Cristo Patrimoine\n")

    pages        = load_pages()
    sitemap_urls = load_sitemap_urls()
    issues       = []

    for page in pages:
        filename = page["file"]
        filepath = SITE_ROOT / filename
        url      = page["url"].rstrip("/") or "/"
        full_url = (BASE_URL + url).rstrip("/")

        # 1. Fichier présent
        if not filepath.exists():
            issues.append({"level": "critique", "file": filename,
                           "check": "Fichier manquant", "detail": f"`{filename}` introuvable sur le disque"})
            continue

        html = filepath.read_text(encoding="utf-8", errors="replace")

        # 2. Canonical sur pages indexables
        if page.get("indexable"):
            canonical, status = check_canonical(html, url)
            if status != "ok":
                issues.append({"level": "critique", "file": filename,
                               "check": "Canonical", "detail": status})

        # 3. Pages sitemap:true présentes dans sitemap.xml
        if page.get("sitemap") and page.get("status") == "active":
            if full_url not in sitemap_urls:
                issues.append({"level": "critique", "file": filename,
                               "check": "Absente du sitemap", "detail": f"`{full_url}` non trouvée dans sitemap.xml"})

        # 4. Pages sitemap:false absentes de sitemap.xml
        if not page.get("sitemap"):
            if full_url in sitemap_urls:
                issues.append({"level": "important", "file": filename,
                               "check": "Présente dans sitemap", "detail": f"`{full_url}` trouvée dans sitemap.xml alors que sitemap: false"})

        # 5. Liens internes avec .html
        bad_links = check_html_links(html, filename)
        for href in bad_links:
            issues.append({"level": "important", "file": filename,
                           "check": "Lien avec .html", "detail": f"`{href}`"})

    stats = {"pages": len(pages)}
    critiques  = len([i for i in issues if i["level"] == "critique"])
    importants = len([i for i in issues if i["level"] == "important"])

    print(f"   Pages vérifiées : {stats['pages']}")
    print(f"   🔴 Critiques    : {critiques}")
    print(f"   🟠 Importants   : {importants}")

    if issues:
        print("\n   Anomalies :")
        for i in issues:
            emoji = "🔴" if i["level"] == "critique" else "🟠"
            print(f"   {emoji} [{i['check']}] {i['file']} — {i['detail']}")

    generated_at = datetime.now().strftime("%d/%m/%Y à %H:%M")
    REPORTS_DIR.mkdir(parents=True, exist_ok=True)
    md_path = REPORTS_DIR / "urls-report.md"
    md_path.write_text(build_report(issues, stats, generated_at), encoding="utf-8")
    print(f"\n📄 Rapport : {md_path}")

if __name__ == "__main__":
    main()
