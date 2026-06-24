#!/usr/bin/env python3
"""
Bootstrap pages.json — Monte-Cristo Patrimoine
Génère seo/config/pages.json depuis les fichiers HTML existants.

Ce script est à usage unique (ou à relancer pour intégrer de nouvelles pages).
Il produit un fichier JSON à valider manuellement avant utilisation.

Usage : python3 seo/scripts/bootstrap-pages.py
        (depuis la racine du site)
"""

import re
import json
import sys
from pathlib import Path

SCRIPT_DIR = Path(__file__).parent
SITE_ROOT  = SCRIPT_DIR.parent.parent
CONFIG_DIR = SCRIPT_DIR.parent / "config"
BASE_URL   = "https://monte-cristo.net"

# ── Règles de classification par fichier ────────────────────────────────────
# Ces valeurs sont des suggestions — à valider et ajuster manuellement.

PAGE_RULES = {
    "index.html": {
        "type": "accueil", "priority": 1.0, "changefreq": "monthly",
        "cluster": None, "status": "active",
    },
    "le-cabinet.html": {
        "type": "institutionnelle", "priority": 0.9, "changefreq": "monthly",
        "cluster": "cabinet", "status": "active",
    },
    "particuliers.html": {
        "type": "service", "priority": 0.9, "changefreq": "monthly",
        "cluster": "services", "status": "active",
    },
    "entreprises.html": {
        "type": "service", "priority": 0.9, "changefreq": "monthly",
        "cluster": "services", "status": "active",
    },
    "blog.html": {
        "type": "blog", "priority": 0.8, "changefreq": "weekly",
        "cluster": None, "status": "active",
    },
    "conseiller-gestion-patrimoine-independant.html": {
        "type": "pilier", "priority": 0.8, "changefreq": "monthly",
        "cluster": "cgp-independant", "status": "active",
    },
    "article-cgp-independant.html": {
        "type": "article", "priority": 0.7, "changefreq": "monthly",
        "cluster": "cgp-independant", "status": "active",
    },
    "article-frais-bancaires.html": {
        "type": "article", "priority": 0.7, "changefreq": "monthly",
        "cluster": "frais", "status": "active",
    },
    "simulateur-frais.html": {
        "type": "outil", "priority": 0.6, "changefreq": "monthly",
        "cluster": "frais", "status": "active",
    },
    "mentions-legales.html": {
        "type": "legal", "priority": 0.2, "changefreq": "yearly",
        "cluster": None, "status": "legal",
    },
    "politique-confidentialite.html": {
        "type": "legal", "priority": 0.3, "changefreq": "yearly",
        "cluster": None, "status": "legal",
    },
    "404.html": {
        "type": "technique", "priority": None, "changefreq": None,
        "cluster": None, "status": "active",
    },
    "mockup-contenu.html": {
        "type": "travail", "priority": None, "changefreq": None,
        "cluster": None, "status": "work",
    },
}

# ── Helpers ──────────────────────────────────────────────────────────────────

def has_noindex(html):
    return bool(re.search(
        r'<meta\s[^>]*name=["\']robots["\'][^>]*content=["\'][^"\']*noindex',
        html, re.IGNORECASE
    ))

def has_footer(html):
    return bool(re.search(r'<footer[\s>]', html, re.IGNORECASE))

def file_to_url(filename):
    name = filename.replace(".html", "")
    return "/" if name == "index" else f"/{name}"

def extract_nav_links(html):
    """Extrait les href depuis les balises <nav>."""
    nav_blocks = re.findall(r'<nav[\s>].*?</nav>', html, re.IGNORECASE | re.DOTALL)
    hrefs = []
    for block in nav_blocks:
        hrefs += re.findall(r'href=["\']([^"\']+)["\']', block, re.IGNORECASE)
    return hrefs

def extract_footer_links(html):
    """Extrait les href depuis les balises <footer>."""
    footer_blocks = re.findall(r'<footer[\s>].*?</footer>', html, re.IGNORECASE | re.DOTALL)
    hrefs = []
    for block in footer_blocks:
        hrefs += re.findall(r'href=["\']([^"\']+)["\']', block, re.IGNORECASE)
    return hrefs

def normalise_href(href, base_url=BASE_URL):
    """Normalise un href vers un chemin absolu sans domaine."""
    href = href.strip()
    if href.startswith(base_url):
        href = href[len(base_url):]
    if not href.startswith("/"):
        return None   # ancre, externe, relatif complexe
    return href.rstrip("/") or "/"

# ── Analyse de l'index pour détecter nav/footer ──────────────────────────────

def analyse_reference_page(site_root):
    """
    Utilise index.html comme page de référence pour détecter
    les liens présents en nav principale et en footer.
    """
    ref_path = site_root / "index.html"
    if not ref_path.exists():
        return set(), set()
    html = ref_path.read_text(encoding="utf-8", errors="replace")
    nav_links    = {normalise_href(h) for h in extract_nav_links(html) if normalise_href(h)}
    footer_links = {normalise_href(h) for h in extract_footer_links(html) if normalise_href(h)}
    # Retirer les ancres internes pures
    nav_links    = {l for l in nav_links    if not l.startswith("/#")}
    footer_links = {l for l in footer_links if not l.startswith("/#")}
    return nav_links, footer_links

# ── Construction de l'entrée pour une page ───────────────────────────────────

def build_entry(filepath, rules, nav_links, footer_links):
    filename = filepath.name
    html     = filepath.read_text(encoding="utf-8", errors="replace")
    r        = rules.get(filename, {})

    page_type   = r.get("type", "inconnue")
    noindex     = has_noindex(html)
    indexable   = not noindex and page_type not in ("technique", "travail")
    in_sitemap  = indexable and page_type != "legal"

    # Pour les pages légales déjà exclues via noindex : respecter le noindex
    if page_type == "legal" and noindex:
        in_sitemap = False

    url = file_to_url(filename)

    # Détection nav / footer depuis les liens de la page de référence
    # On cherche si l'URL de la page apparaît dans les liens de nav/footer d'index
    url_variants = {url, url + "/", url.rstrip("/") or "/"}
    in_main_nav   = bool(url_variants & nav_links)
    in_footer_nav = bool(url_variants & footer_links)

    # Cas particulier : ancres de nav (ex: /le-cabinet#modele)
    for link in nav_links:
        if link.startswith(url + "#") or link == url:
            in_main_nav = True
    for link in footer_links:
        if link.startswith(url + "#") or link == url:
            in_footer_nav = True

    return {
        "file":         filename,
        "url":          url,
        "type":         page_type,
        "indexable":    indexable,
        "sitemap":      in_sitemap,
        "priority":     r.get("priority"),
        "changefreq":   r.get("changefreq"),
        "cluster":      r.get("cluster"),
        "has_footer":   has_footer(html),
        "in_main_nav":  in_main_nav,
        "in_footer_nav":in_footer_nav,
        "status":       r.get("status", "active"),
    }

# ── Ordre d'affichage ─────────────────────────────────────────────────────────

ORDER = [
    "index.html", "le-cabinet.html", "particuliers.html", "entreprises.html",
    "blog.html", "conseiller-gestion-patrimoine-independant.html",
    "article-cgp-independant.html", "article-frais-bancaires.html",
    "simulateur-frais.html", "mentions-legales.html",
    "politique-confidentialite.html", "404.html", "mockup-contenu.html",
]

def sort_key(f):
    try:
        return ORDER.index(f.name)
    except ValueError:
        return len(ORDER)

# ── Point d'entrée ────────────────────────────────────────────────────────────

def main():
    print("⚙️  Bootstrap pages.json — Monte-Cristo Patrimoine")
    print(f"   Racine : {SITE_ROOT}\n")

    html_files = sorted(SITE_ROOT.glob("*.html"), key=sort_key)
    if not html_files:
        print("❌ Aucun fichier .html trouvé.")
        sys.exit(1)

    nav_links, footer_links = analyse_reference_page(SITE_ROOT)
    print(f"   Nav principale détectée  : {sorted(nav_links)}")
    print(f"   Liens footer détectés    : {sorted(footer_links)}\n")

    pages = []
    for filepath in html_files:
        entry = build_entry(filepath, PAGE_RULES, nav_links, footer_links)
        pages.append(entry)
        idx = "✅ indexable" if entry["indexable"] else "⛔ non-indexable"
        nav = "nav" if entry["in_main_nav"] else "   "
        ftr = "footer" if entry["in_footer_nav"] else "      "
        print(f"   {entry['file']:<50} {idx}  {nav}  {ftr}")

    output = {
        "_comment": "Source de vérité SEO — à valider manuellement avant utilisation. Généré par bootstrap-pages.py.",
        "base_url": BASE_URL,
        "pages": pages,
    }

    CONFIG_DIR.mkdir(parents=True, exist_ok=True)
    out_path = CONFIG_DIR / "pages.json"
    out_path.write_text(json.dumps(output, ensure_ascii=False, indent=2), encoding="utf-8")

    print(f"\n✅ {len(pages)} pages analysées")
    print(f"📄 Fichier généré : {out_path}")
    print(f"\n⚠️  Ce fichier est une suggestion — vérifiez et ajustez avant de l'utiliser.")

if __name__ == "__main__":
    main()
