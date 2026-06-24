#!/usr/bin/env python3
"""
Contrôle des liens — Monte-Cristo Patrimoine
Détecte les liens internes cassés ou pointant vers des pages futures inexistantes.

Catégories de liens :
  valid_internal   — lien interne vers une page active existante
  valid_anchor     — ancre #section (sur la page courante)
  valid_anchor_page — ancre sur une autre page existante (/page#section)
  valid_static     — lien vers fichier statique existant (image, pdf…)
  external         — lien http/https vers un autre domaine (non testé)
  mailto_tel       — lien mailto: ou tel:
  broken           — lien interne vers un fichier inexistant (avec .html ou autre)
  future           — lien interne vers une URL propre sans .html, page inexistante

Règles :
  - Les URLs publiques sont sans extension .html
  - Un lien /page est valide si pages.json contient une page active à cette URL
    OU si un fichier HTML correspondant existe à la racine
  - status "planned" dans pages.json ne rend pas la page valide pour un lien actif
  - Les ancres /page#section sont valides si /page existe (ancre non vérifiée)
  - Les liens externes ne sont pas testés par requête web

Usage : python3 seo/scripts/check-links.py
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
BASE_URL    = "https://monte-cristo.net"

# ── Chargement de pages.json ──────────────────────────────────────────────────

def load_config():
    if not CONFIG_PATH.exists():
        print(f"❌ {CONFIG_PATH} introuvable. Lancez bootstrap-pages.py d'abord.")
        sys.exit(1)
    data = json.loads(CONFIG_PATH.read_text(encoding="utf-8"))
    return data.get("pages", [])

def build_valid_urls(pages):
    """
    Retourne l'ensemble des URLs valides pour les liens internes.
    Une URL est valide uniquement si la page est active (status == "active").
    Les pages planned, work, legal, technical ne comptent pas.
    """
    valid = set()
    for p in pages:
        if p.get("status") == "active":
            url = p["url"].rstrip("/") or "/"
            valid.add(url)
    return valid

def build_url_to_file(pages):
    """Retourne un dict url → filename pour toutes les pages."""
    return {p["url"].rstrip("/") or "/": p["file"] for p in pages}

# ── Extraction des liens ──────────────────────────────────────────────────────

def extract_links(html):
    """Extrait tous les href des balises <a>."""
    return re.findall(r'<a\s[^>]*href=["\']([^"\']*)["\']', html, re.IGNORECASE)

# ── Classification d'un lien ──────────────────────────────────────────────────

def classify_link(href, source_file, valid_urls, url_to_file):
    href = href.strip()

    # Vide ou fragment pur
    if not href or href == "#" or href.startswith("javascript:"):
        return "ignored", None

    # mailto / tel
    if href.startswith("mailto:") or href.startswith("tel:"):
        return "mailto_tel", None

    # Lien externe
    if href.startswith("http://") or href.startswith("https://"):
        if not href.startswith(BASE_URL):
            return "external", None
        # Lien absolu vers notre domaine → traiter comme interne
        href = href[len(BASE_URL):]
        if not href:
            href = "/"

    # Ancre pure sur la même page
    if href.startswith("#"):
        return "valid_anchor", None

    # Normaliser le chemin
    path = href.split("?")[0].split("#")[0]  # enlever query et fragment
    anchor = href[len(path):]                 # conserver #fragment si présent
    path = path.rstrip("/") or "/"

    # Lien avec extension .html → probablement un bug de convention
    if path.endswith(".html"):
        clean = path[:-5]  # retirer .html
        exists_as_clean = clean in valid_urls or (SITE_ROOT / path.lstrip("/")).exists()
        if exists_as_clean:
            return "broken", f"Convention : utiliser `{clean}` sans `.html`"
        return "broken", f"Lien avec .html vers page inconnue"

    # Fichier statique (assets, fonts, images…)
    filepath = SITE_ROOT / path.lstrip("/")
    if filepath.suffix and filepath.suffix not in (".html", ""):
        if filepath.exists():
            return "valid_static", None
        return "broken", f"Fichier statique introuvable : {path}"

    # Lien interne sans extension → URL publique
    # Cas avec ancre : /le-cabinet#modele → vérifier /le-cabinet
    base_path = path

    # Vérifier si valide dans pages.json (status active)
    if base_path in valid_urls or base_path + "/" in valid_urls:
        if anchor:
            return "valid_anchor_page", None
        return "valid_internal", None

    # Vérifier si le fichier existe physiquement (page non déclarée dans pages.json)
    candidate = SITE_ROOT / (base_path.lstrip("/") + ".html")
    if candidate.exists():
        return "valid_internal", f"Page existante mais non déclarée dans pages.json : {base_path}"

    # Page inconnue → est-ce une page future ?
    # Heuristique : URL en kebab-case sans fichier = page future probable
    return "future", f"Page inexistante : {base_path}"

# ── Analyse d'une page ────────────────────────────────────────────────────────

def analyse_file(filepath, valid_urls, url_to_file):
    html = filepath.read_text(encoding="utf-8", errors="replace")
    hrefs = extract_links(html)
    results = []

    for href in hrefs:
        category, note = classify_link(href, filepath.name, valid_urls, url_to_file)
        if category == "ignored":
            continue
        results.append({
            "source":   filepath.name,
            "href":     href,
            "category": category,
            "note":     note,
        })

    return results

# ── Rapport ───────────────────────────────────────────────────────────────────

CATEGORY_LABEL = {
    "valid_internal":   ("✅", "Interne valide"),
    "valid_anchor":     ("✅", "Ancre (même page)"),
    "valid_anchor_page":("✅", "Ancre (autre page)"),
    "valid_static":     ("✅", "Fichier statique"),
    "external":         ("⚪", "Externe (non testé)"),
    "mailto_tel":       ("⚪", "mailto / tel"),
    "broken":           ("🔴", "Lien cassé"),
    "future":           ("🟠", "Page future inexistante"),
}

LEVEL = {
    "broken": "critique",
    "future": "important",
    "valid_internal": "ok",
    "valid_anchor": "ok",
    "valid_anchor_page": "ok",
    "valid_static": "ok",
    "external": "ok",
    "mailto_tel": "ok",
}

def build_markdown(all_links, generated_at):
    broken  = [l for l in all_links if l["category"] == "broken"]
    future  = [l for l in all_links if l["category"] == "future"]
    valid_i = [l for l in all_links if l["category"] in ("valid_internal", "valid_anchor_page", "valid_anchor", "valid_static")]
    ext     = [l for l in all_links if l["category"] == "external"]
    mailto  = [l for l in all_links if l["category"] == "mailto_tel"]

    lines = []
    a = lines.append
    a("# Contrôle des liens — Monte-Cristo Patrimoine")
    a(f"*Généré le {generated_at}*\n")

    a("## Résumé\n")
    a("| | |")
    a("|---|---|")
    a(f"| Total liens analysés | **{len(all_links)}** |")
    a(f"| Liens internes valides ✅ | **{len(valid_i)}** |")
    a(f"| Liens externes ⚪ | **{len(ext)}** |")
    a(f"| mailto / tel ⚪ | **{len(mailto)}** |")
    a(f"| Liens cassés 🔴 | **{len(broken)}** |")
    a(f"| Pages futures inexistantes 🟠 | **{len(future)}** |")
    a("")

    if not broken and not future:
        a("> ✅ Aucun lien cassé ni page future inexistante détectés.\n")
    else:
        a(f"> ⚠️ **{len(broken) + len(future)} problème(s) à traiter.**\n")

    if broken:
        a("---\n## 🔴 Liens cassés — à corriger\n")
        a("| Source | Lien | Note |")
        a("|--------|------|------|")
        for l in broken:
            note = l["note"] or ""
            a(f"| `{l['source']}` | `{l['href']}` | {note} |")
        a("")

    if future:
        a("---\n## 🟠 Pages futures inexistantes\n")
        a("Ces liens pointent vers des URLs qui n'existent pas encore.\n")
        a("À remplacer par un contenu existant ou à masquer jusqu'à publication de la page.\n")
        a("| Source | Lien | Note |")
        a("|--------|------|------|")
        for l in future:
            note = l["note"] or ""
            a(f"| `{l['source']}` | `{l['href']}` | {note} |")
        a("")

    a("---\n## Détail par page source\n")
    sources = sorted({l["source"] for l in all_links})
    for source in sources:
        page_links = [l for l in all_links if l["source"] == source]
        problems = [l for l in page_links if l["category"] in ("broken", "future")]
        badge = f" — {len(problems)} problème(s)" if problems else ""
        a(f"### `{source}`{badge}")
        a("| Lien | Catégorie | Note |")
        a("|------|-----------|------|")
        for l in sorted(page_links, key=lambda x: (LEVEL.get(x["category"], "z"), x["href"])):
            emoji, label = CATEGORY_LABEL.get(l["category"], ("?", l["category"]))
            note = l["note"] or ""
            a(f"| `{l['href']}` | {emoji} {label} | {note} |")
        a("")

    a("---")
    a("*Rapport généré par `seo/scripts/check-links.py`*")
    return "\n".join(lines)

# ── Point d'entrée ────────────────────────────────────────────────────────────

def main():
    print("🔗 Contrôle des liens — Monte-Cristo Patrimoine")
    print(f"   Racine : {SITE_ROOT}\n")

    pages    = load_config()
    valid_urls  = build_valid_urls(pages)
    url_to_file = build_url_to_file(pages)

    print(f"   Pages actives dans pages.json : {len(valid_urls)}")
    print(f"   URLs valides : {sorted(valid_urls)}\n")

    html_files = sorted(SITE_ROOT.glob("*.html"))
    all_links  = []

    for filepath in html_files:
        links = analyse_file(filepath, valid_urls, url_to_file)
        all_links.extend(links)
        broken_count = sum(1 for l in links if l["category"] == "broken")
        future_count = sum(1 for l in links if l["category"] == "future")
        if broken_count or future_count:
            print(f"   {filepath.name:<50} 🔴 {broken_count} cassé(s)  🟠 {future_count} futur(s)")
        else:
            print(f"   {filepath.name:<50} ✅")

    broken = [l for l in all_links if l["category"] == "broken"]
    future = [l for l in all_links if l["category"] == "future"]

    print(f"\n📊 Résumé :")
    print(f"   Total liens analysés         : {len(all_links)}")
    print(f"   🔴 Cassés                    : {len(broken)}")
    print(f"   🟠 Pages futures inexistantes : {len(future)}")
    print(f"   ✅ Valides                   : {len([l for l in all_links if l['category'] not in ('broken','future')])}")

    generated_at = datetime.now().strftime("%d/%m/%Y à %H:%M")
    REPORTS_DIR.mkdir(parents=True, exist_ok=True)

    # JSON
    json_path = REPORTS_DIR / "links-report.json"
    json_path.write_text(json.dumps({
        "generated_at": generated_at,
        "summary": {
            "total":   len(all_links),
            "broken":  len(broken),
            "future":  len(future),
        },
        "links": all_links,
    }, ensure_ascii=False, indent=2), encoding="utf-8")

    # Markdown
    md_path = REPORTS_DIR / "links-report.md"
    md_path.write_text(build_markdown(all_links, generated_at), encoding="utf-8")

    print(f"\n📄 Rapports :")
    print(f"   {json_path}")
    print(f"   {md_path}")

if __name__ == "__main__":
    main()
