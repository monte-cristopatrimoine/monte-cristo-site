#!/usr/bin/env python3
"""
Audit SEO — Monte-Cristo Patrimoine
Analyse toutes les pages HTML du site et génère deux rapports :
  - seo/reports/site-audit.json
  - seo/reports/site-audit.md

Usage : python3 seo/scripts/audit.py
        (depuis la racine du site)
"""

import os
import re
import json
import sys
from pathlib import Path
from datetime import datetime
import xml.etree.ElementTree as ET

# ── Configuration ────────────────────────────────────────────────────────────

SCRIPT_DIR  = Path(__file__).parent
SITE_ROOT   = SCRIPT_DIR.parent.parent          # seo/scripts/ → racine du site
REPORTS_DIR = SCRIPT_DIR.parent / "reports"
SITEMAP     = SITE_ROOT / "sitemap.xml"
BASE_URL    = "https://monte-cristo.net"

# Pages à classer comme "technique" (auditées mais hors indexation normale)
TECHNICAL_PAGES = {"404.html"}

# Pages à classer comme "travail" (auditées mais exclues de l'indexation)
WORK_PAGES = {"mockup-contenu.html"}

# Toutes les pages à traiter (technique + travail incluses, mais classées différemment)
EXCLUDE_FROM_AUDIT = set()  # rien n'est complètement exclu, tout est classé

# ── Helpers HTML ─────────────────────────────────────────────────────────────

def extract(pattern, html, group=1, flags=re.IGNORECASE | re.DOTALL):
    m = re.search(pattern, html, flags)
    return m.group(group).strip() if m else ""

def extract_all(pattern, html, flags=re.IGNORECASE | re.DOTALL):
    return re.findall(pattern, html, flags)

def decode_entities(text):
    replacements = {
        "&amp;": "&", "&lt;": "<", "&gt;": ">",
        "&quot;": '"', "&#39;": "'", "&nbsp;": " ",
        "&#8239;": " ", "&#160;": " ",
    }
    for k, v in replacements.items():
        text = text.replace(k, v)
    text = re.sub(r"&#(\d+);", lambda m: chr(int(m.group(1))), text)
    return text

def strip_tags(html):
    return re.sub(r"<[^>]+>", "", html).strip()

def page_url(filename):
    """Convertit un nom de fichier en URL estimée."""
    name = filename.replace(".html", "")
    if name == "index":
        return BASE_URL + "/"
    return f"{BASE_URL}/{name}"

# ── Lecture du sitemap ────────────────────────────────────────────────────────

def load_sitemap_urls():
    if not SITEMAP.exists():
        return set()
    try:
        tree = ET.parse(SITEMAP)
        ns = {"sm": "http://www.sitemaps.org/schemas/sitemap/0.9"}
        return {loc.text.rstrip("/") for loc in tree.findall(".//sm:loc", ns)}
    except Exception:
        return set()

# ── Analyse d'une page ───────────────────────────────────────────────────────

def audit_page(filepath, sitemap_urls):
    html = filepath.read_text(encoding="utf-8", errors="replace")
    filename = filepath.name

    # Catégorie de la page
    if filename in TECHNICAL_PAGES:
        category = "technique"
    elif filename in WORK_PAGES:
        category = "travail"
    else:
        category = "production"

    url = page_url(filename)

    # ── Métadonnées de base
    title       = decode_entities(extract(r"<title>([^<]+)</title>", html))
    # Utilise une regex qui respecte le délimiteur d'attribut (évite de s'arrêter sur les apostrophes)
    description = decode_entities(extract(r'<meta\s[^>]*name=["\']description["\'][^>]*content="([^"]*)"', html))
    if not description:
        description = decode_entities(extract(r"<meta\s[^>]*name=[\"']description[\"'][^>]*content='([^']*)'", html))
    if not description:
        description = decode_entities(extract(r'<meta\s[^>]*content="([^"]*)"[^>]*name=["\']description["\']', html))
    canonical   = extract(r'<link\s[^>]*rel=["\']canonical["\'][^>]*href=["\'](.*?)["\']', html)

    # ── Open Graph
    og_title    = decode_entities(extract(r'<meta\s[^>]*property=["\']og:title["\'][^>]*content=["\'](.*?)["\']', html))
    og_desc     = decode_entities(extract(r'<meta\s[^>]*property=["\']og:description["\'][^>]*content=["\'](.*?)["\']', html))
    og_image    = extract(r'<meta\s[^>]*property=["\']og:image["\'][^>]*content=["\'](.*?)["\']', html)

    # ── H1 / H2
    h1_tags  = extract_all(r"<h1[^>]*>(.*?)</h1>", html)
    h1_texts = [decode_entities(strip_tags(h)) for h in h1_tags]
    h2_tags  = extract_all(r"<h2[^>]*>(.*?)</h2>", html)
    h2_texts = [decode_entities(strip_tags(h)) for h in h2_tags]

    # ── Images sans alt
    all_imgs        = extract_all(r"<img\s[^>]*/?>", html)
    imgs_without_alt = [
        img for img in all_imgs
        if not re.search(r'\balt=["\'][^"\']+["\']', img, re.IGNORECASE)
    ]

    # ── Liens internes / externes
    all_hrefs      = extract_all(r'<a\s[^>]*href=["\'](.*?)["\']', html)
    internal_links = [h for h in all_hrefs if h.startswith("/") or BASE_URL in h]
    external_links = [h for h in all_hrefs if h.startswith("http") and BASE_URL not in h]

    # ── Schema.org / JSON-LD
    jsonld_blocks = extract_all(r'<script\s[^>]*type=["\']application/ld\+json["\'][^>]*>(.*?)</script>', html)
    has_schema    = len(jsonld_blocks) > 0

    # ── noindex
    has_noindex = bool(re.search(
        r'<meta\s[^>]*name=["\']robots["\'][^>]*content=["\'][^"\']*noindex',
        html, re.IGNORECASE
    ))

    # ── Présence dans le sitemap
    url_clean  = url.rstrip("/")
    in_sitemap = url_clean in sitemap_urls

    # ── Longueurs
    title_len = len(title)
    desc_len  = len(description)

    # ── Détection des problèmes
    issues = []

    def add(level, code, message):
        issues.append({"level": level, "code": code, "message": message})

    if category == "production":
        # Critiques
        if not title:
            add("critique", "TITLE_MISSING", "Balise <title> absente")
        elif title_len < 30:
            add("critique", "TITLE_TOO_SHORT", f"Titre trop court ({title_len} car.) — minimum recommandé : 30")
        elif title_len > 65:
            add("important", "TITLE_TOO_LONG", f"Titre trop long ({title_len} car.) — sera tronqué dans Google (max 65)")

        if not description:
            add("critique", "DESC_MISSING", "Meta description absente")
        elif desc_len < 80:
            add("important", "DESC_TOO_SHORT", f"Description trop courte ({desc_len} car.) — minimum recommandé : 80")
        elif desc_len > 160:
            add("amelioration", "DESC_TOO_LONG", f"Description trop longue ({desc_len} car.) — sera tronquée dans Google (max 160)")

        if not canonical:
            add("critique", "CANONICAL_MISSING", "Balise canonical absente")

        h1_count = len(h1_texts)
        if h1_count == 0:
            add("critique", "H1_MISSING", "Aucune balise H1 — manquant pour le référencement")
        elif h1_count > 1:
            add("important", "H1_MULTIPLE", f"{h1_count} balises H1 trouvées — une seule recommandée")

        if not in_sitemap and not has_noindex:
            add("important", "NOT_IN_SITEMAP", "Page absente du sitemap.xml")
        if in_sitemap and has_noindex:
            add("important", "NOINDEX_IN_SITEMAP", "Page avec noindex présente dans le sitemap — incohérence")

        # Importants
        if not og_title:
            add("important", "OG_TITLE_MISSING", "og:title absent — partage réseaux sociaux dégradé")
        if not og_desc:
            add("important", "OG_DESC_MISSING", "og:description absent — partage réseaux sociaux dégradé")
        if not og_image:
            add("amelioration", "OG_IMAGE_MISSING", "og:image absent")
        elif og_image == "https://monte-cristo.net/assets/og-image.png":
            add("amelioration", "OG_IMAGE_GENERIC", "og:image générique (même image sur toutes les pages)")

        if not has_schema:
            add("amelioration", "SCHEMA_MISSING", "Aucune donnée structurée JSON-LD / Schema.org")

        if not h2_texts:
            add("amelioration", "H2_MISSING", "Aucune balise H2 — structure du contenu à améliorer")

        if imgs_without_alt:
            add("amelioration", "IMGS_NO_ALT",
                f"{len(imgs_without_alt)} image(s) sans attribut alt — accessibilité et SEO images")

    elif category == "technique":
        if not title:
            add("mineur", "TITLE_MISSING", "Balise <title> absente (page technique)")
        if canonical:
            add("amelioration", "CANONICAL_ON_404", "Canonical présent sur une page 404 — à vérifier")

    elif category == "travail":
        if in_sitemap:
            add("critique", "WORK_PAGE_IN_SITEMAP", "Page de travail présente dans le sitemap — à retirer")
        has_noindex = bool(re.search(r'content=["\'][^"\']*noindex', html, re.IGNORECASE))
        if not has_noindex:
            add("important", "WORK_PAGE_NO_NOINDEX",
                "Page de travail sans balise noindex — risque d'indexation par Google")

    return {
        "file":            filename,
        "category":        category,
        "url":             url,
        "title":           title,
        "title_length":    title_len,
        "description":     description,
        "description_length": desc_len,
        "canonical":       canonical,
        "og_title":        og_title,
        "og_description":  og_desc,
        "og_image":        og_image,
        "h1_count":        len(h1_texts),
        "h1_texts":        h1_texts,
        "h2_count":        len(h2_texts),
        "h2_texts":        h2_texts[:5],          # max 5 pour le rapport
        "imgs_without_alt":   len(imgs_without_alt),
        "internal_links":  len(internal_links),
        "external_links":  len(external_links),
        "has_schema":      has_schema,
        "in_sitemap":      in_sitemap,
        "issues":          issues,
    }

# ── Rapport Markdown ──────────────────────────────────────────────────────────

def level_emoji(level):
    return {"critique": "🔴", "important": "🟠", "amelioration": "🟡", "mineur": "⚪"}.get(level, "")

def build_markdown(pages, generated_at):
    prod  = [p for p in pages if p["category"] == "production"]
    tech  = [p for p in pages if p["category"] == "technique"]
    work  = [p for p in pages if p["category"] == "travail"]

    all_issues = [(p["file"], i) for p in pages for i in p["issues"]]
    by_level   = lambda lvl: [(f, i) for f, i in all_issues if i["level"] == lvl]

    critiques    = by_level("critique")
    importants   = by_level("important")
    ameliorations = by_level("amelioration")
    mineurs      = by_level("mineur")

    score_map = {"critique": 0, "important": 1, "amelioration": 2, "mineur": 3}
    pages_ok  = [p for p in prod if not p["issues"]]

    lines = []
    a = lines.append

    a(f"# Rapport SEO — Monte-Cristo Patrimoine")
    a(f"*Généré le {generated_at}*\n")

    # ── Résumé global
    a("## Résumé global\n")
    a(f"| | |")
    a(f"|---|---|")
    a(f"| Pages de production analysées | **{len(prod)}** |")
    a(f"| Pages techniques | **{len(tech)}** |")
    a(f"| Pages de travail | **{len(work)}** |")
    a(f"| Problèmes critiques 🔴 | **{len(critiques)}** |")
    a(f"| Problèmes importants 🟠 | **{len(importants)}** |")
    a(f"| Améliorations utiles 🟡 | **{len(ameliorations)}** |")
    a(f"| Mineurs ⚪ | **{len(mineurs)}** |")
    a(f"| Pages sans problème | **{len(pages_ok)}** |")
    a("")

    if not critiques and not importants:
        a("> ✅ Aucun problème critique ou important détecté.\n")
    else:
        total = len(critiques) + len(importants)
        a(f"> ⚠️ **{total} problème(s) à corriger en priorité** (critiques + importants).\n")

    # ── Problèmes critiques
    a("---\n## 🔴 Problèmes critiques\n")
    if critiques:
        for fname, issue in critiques:
            a(f"- **{fname}** — {issue['message']}")
    else:
        a("Aucun problème critique.")
    a("")

    # ── Problèmes importants
    a("---\n## 🟠 Problèmes importants\n")
    if importants:
        for fname, issue in importants:
            a(f"- **{fname}** — {issue['message']}")
    else:
        a("Aucun problème important.")
    a("")

    # ── Améliorations
    a("---\n## 🟡 Améliorations utiles\n")
    if ameliorations:
        for fname, issue in ameliorations:
            a(f"- **{fname}** — {issue['message']}")
    else:
        a("Aucune amélioration suggérée.")
    a("")

    # ── Liste page par page
    a("---\n## Liste page par page\n")
    for p in sorted(pages, key=lambda x: ({"production":0,"technique":1,"travail":2}[x["category"]], x["file"])):
        badge = {"production": "", "technique": " *(technique)*", "travail": " *(travail — hors prod)*"}[p["category"]]
        a(f"### `{p['file']}`{badge}")
        a(f"- **URL** : {p['url']}")
        a(f"- **Title** : {p['title'] or '*(manquant)*'} *(longueur : {p['title_length']})*")
        a(f"- **Description** : {p['description'][:80] + '…' if len(p['description']) > 80 else p['description'] or '*(manquante)*'} *(longueur : {p['description_length']})*")
        a(f"- **Canonical** : {p['canonical'] or '*(manquant)*'}")
        a(f"- **H1** ({p['h1_count']}) : {', '.join(p['h1_texts']) or '*(aucun)*'}")
        a(f"- **H2** ({p['h2_count']}) : {', '.join(p['h2_texts'][:3]) or '*(aucun)*'}")
        a(f"- **Schema.org** : {'Oui' if p['has_schema'] else 'Non'}")
        a(f"- **Dans sitemap** : {'✅ Oui' if p['in_sitemap'] else '❌ Non'}")
        a(f"- **Images sans alt** : {p['imgs_without_alt']}")
        a(f"- **Liens** : {p['internal_links']} internes, {p['external_links']} externes")
        if p["issues"]:
            a(f"- **Problèmes :**")
            for issue in sorted(p["issues"], key=lambda i: score_map[i["level"]]):
                a(f"  - {level_emoji(issue['level'])} {issue['message']}")
        else:
            a("- ✅ Aucun problème détecté")
        a("")

    # ── Recommandations d'ordre d'exécution
    a("---\n## Recommandations — ordre d'exécution\n")

    reco_items = []

    # Construire des recommandations groupées par type de problème
    missing_h1 = [p["file"] for p in prod if p["h1_count"] == 0]
    missing_desc = [p["file"] for p in prod if not p["description"]]
    missing_canonical = [p["file"] for p in prod if not p["canonical"]]
    missing_title = [p["file"] for p in prod if not p["title"]]
    not_in_sitemap = [p["file"] for p in prod if not p["in_sitemap"]]
    work_no_noindex = [p["file"] for p in work]
    no_schema = [p["file"] for p in prod if not p["has_schema"]]
    no_h2 = [p["file"] for p in prod if p["h2_count"] == 0]
    imgs_no_alt = [p["file"] for p in prod if p["imgs_without_alt"] > 0]

    step = 1
    if missing_title:
        a(f"**{step}. Ajouter les balises `<title>` manquantes** 🔴")
        for f in missing_title: a(f"   - `{f}`")
        a(""); step += 1
    if missing_desc:
        a(f"**{step}. Ajouter les meta descriptions manquantes** 🔴")
        for f in missing_desc: a(f"   - `{f}`")
        a(""); step += 1
    if missing_canonical:
        a(f"**{step}. Ajouter les balises canonical manquantes** 🔴")
        for f in missing_canonical: a(f"   - `{f}`")
        a(""); step += 1
    if missing_h1:
        a(f"**{step}. Ajouter un H1 sur chaque page** 🔴")
        for f in missing_h1: a(f"   - `{f}`")
        a(""); step += 1
    if not_in_sitemap:
        a(f"**{step}. Ajouter les pages manquantes au sitemap.xml** 🟠")
        for f in not_in_sitemap: a(f"   - `{f}`")
        a(""); step += 1
    if work_no_noindex:
        a(f"**{step}. Ajouter `<meta name='robots' content='noindex'>` sur les pages de travail** 🟠")
        for f in work_no_noindex: a(f"   - `{f}`")
        a(""); step += 1
    if no_schema:
        a(f"**{step}. Ajouter des données structurées JSON-LD** 🟡")
        for f in no_schema: a(f"   - `{f}`")
        a(""); step += 1
    if no_h2:
        a(f"**{step}. Structurer le contenu avec des balises H2** 🟡")
        for f in no_h2: a(f"   - `{f}`")
        a(""); step += 1
    if imgs_no_alt:
        a(f"**{step}. Ajouter des attributs `alt` aux images** 🟡")
        for f in imgs_no_alt: a(f"   - `{f}`")
        a(""); step += 1

    a("---")
    a("*Rapport généré automatiquement par `seo/scripts/audit.py`*")

    return "\n".join(lines)

# ── Point d'entrée ────────────────────────────────────────────────────────────

def main():
    print(f"🔍 Audit SEO — Monte-Cristo Patrimoine")
    print(f"   Racine du site : {SITE_ROOT}")
    print()

    if not SITE_ROOT.exists():
        print(f"❌ Dossier introuvable : {SITE_ROOT}")
        sys.exit(1)

    sitemap_urls = load_sitemap_urls()
    print(f"   Sitemap chargé : {len(sitemap_urls)} URL(s) trouvée(s)")

    html_files = sorted(SITE_ROOT.glob("*.html"))
    if not html_files:
        print("❌ Aucun fichier .html trouvé à la racine.")
        sys.exit(1)

    print(f"   Pages trouvées : {len(html_files)}\n")

    pages = []
    for f in html_files:
        result = audit_page(f, sitemap_urls)
        pages.append(result)
        issues = result["issues"]
        critiques = sum(1 for i in issues if i["level"] == "critique")
        badge = f"  🔴 {critiques} critique(s)" if critiques else "  ✅"
        print(f"   {f.name:<40} {badge}")

    print()

    # JSON
    generated_at = datetime.now().strftime("%d/%m/%Y à %H:%M")
    output = {
        "generated_at": generated_at,
        "site": BASE_URL,
        "total_pages": len(pages),
        "pages": pages,
        "summary": {
            "critique":    sum(1 for p in pages for i in p["issues"] if i["level"] == "critique"),
            "important":   sum(1 for p in pages for i in p["issues"] if i["level"] == "important"),
            "amelioration":sum(1 for p in pages for i in p["issues"] if i["level"] == "amelioration"),
            "mineur":      sum(1 for p in pages for i in p["issues"] if i["level"] == "mineur"),
        }
    }

    REPORTS_DIR.mkdir(parents=True, exist_ok=True)
    json_path = REPORTS_DIR / "site-audit.json"
    md_path   = REPORTS_DIR / "site-audit.md"

    json_path.write_text(json.dumps(output, ensure_ascii=False, indent=2), encoding="utf-8")
    md_path.write_text(build_markdown(pages, generated_at), encoding="utf-8")

    s = output["summary"]
    print(f"📊 Résumé :")
    print(f"   🔴 Critiques    : {s['critique']}")
    print(f"   🟠 Importants   : {s['important']}")
    print(f"   🟡 Améliorations: {s['amelioration']}")
    print(f"   ⚪ Mineurs      : {s['mineur']}")
    print()
    print(f"📄 Rapports générés :")
    print(f"   {json_path}")
    print(f"   {md_path}")

if __name__ == "__main__":
    main()
