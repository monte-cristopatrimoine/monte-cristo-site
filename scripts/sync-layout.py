#!/usr/bin/env python3
"""
sync-layout.py — Monte-Cristo Patrimoine
Synchronise le header et footer canoniques dans toutes les pages HTML du site.

Markers attendus dans chaque page cible :
  <!-- BEGIN GLOBAL HEADER --> ... <!-- END GLOBAL HEADER -->
  <!-- BEGIN GLOBAL FOOTER --> ... <!-- END GLOBAL FOOTER -->

Placeholders dans partials/header.html :
  {{ACTIVE_CABINET}}      → ' class="active"' sur /le-cabinet
  {{ACTIVE_PARTICULIERS}} → ' class="active"' sur /particuliers
  {{ACTIVE_ENTREPRISES}}  → ' class="active"' sur /entreprises
  {{ACTIVE_BLOG}}         → ' class="active"' sur /blog

Usage : python3 scripts/sync-layout.py
        (depuis la racine du site)
"""

import json
import sys
from pathlib import Path

SCRIPT_DIR   = Path(__file__).parent
SITE_ROOT    = SCRIPT_DIR.parent
PARTIALS_DIR = SITE_ROOT / "partials"
CONFIG_PATH  = SITE_ROOT / "seo" / "config" / "pages.json"

HEADER_BEGIN = "<!-- BEGIN GLOBAL HEADER -->"
HEADER_END   = "<!-- END GLOBAL HEADER -->"
FOOTER_BEGIN = "<!-- BEGIN GLOBAL FOOTER -->"
FOOTER_END   = "<!-- END GLOBAL FOOTER -->"

ACTIVE_CLASS = ' class="active"'

# Pages à exclure : footer non standard ou fichiers techniques
EXCLUDE = {"404.html", "mockup-contenu.html"}

# Active state par page — clé = nom de fichier, valeur = placeholder à activer
ACTIVE_MAP = {
    "le-cabinet.html":                              "ACTIVE_CABINET",
    "particuliers.html":                            "ACTIVE_PARTICULIERS",
    "entreprises.html":                             "ACTIVE_ENTREPRISES",
    "blog.html":                                    "ACTIVE_BLOG",
    "article-cgp-independant.html":                 "ACTIVE_BLOG",
    "article-frais-bancaires.html":                 "ACTIVE_BLOG",
    # Pages piliers et légales : aucun active
    "index.html":                                   None,
    "conseiller-gestion-patrimoine-independant.html": None,
    "honoraires-frais-caches.html":                 None,
    "simulateur-frais.html":                        None,
    "simulateurs.html":                             None,
    "mentions-legales.html":                        None,
    "politique-confidentialite.html":               None,
}

ALL_PLACEHOLDERS = [
    "{{ACTIVE_CABINET}}",
    "{{ACTIVE_PARTICULIERS}}",
    "{{ACTIVE_ENTREPRISES}}",
    "{{ACTIVE_BLOG}}",
]


def load_partial(name):
    path = PARTIALS_DIR / name
    if not path.exists():
        print(f"❌ Partial introuvable : {path}")
        sys.exit(1)
    return path.read_text(encoding="utf-8").rstrip("\n")


def resolve_header(header_template, filename):
    """Remplace les placeholders active selon la page courante."""
    active_key = ACTIVE_MAP.get(filename)
    active_placeholder = f"{{{{{active_key}}}}}" if active_key else None

    result = header_template
    for ph in ALL_PLACEHOLDERS:
        if ph == active_placeholder:
            result = result.replace(ph, ACTIVE_CLASS)
        else:
            result = result.replace(ph, "")
    return result


def replace_between(content, begin_marker, end_marker, replacement):
    begin_idx = content.find(begin_marker)
    end_idx   = content.find(end_marker)
    if begin_idx == -1 or end_idx == -1:
        return None, f"marqueurs '{begin_marker}' / '{end_marker}' introuvables"
    if end_idx <= begin_idx:
        return None, "marqueur END placé avant BEGIN"
    after_end = end_idx + len(end_marker)
    new_content = (
        content[:begin_idx]
        + begin_marker + "\n"
        + replacement + "\n"
        + end_marker
        + content[after_end:]
    )
    return new_content, None


def load_pages():
    if not CONFIG_PATH.exists():
        print(f"❌ pages.json introuvable : {CONFIG_PATH}")
        sys.exit(1)
    data = json.loads(CONFIG_PATH.read_text(encoding="utf-8"))
    return data.get("pages", [])


def main():
    print("🔄  sync-layout.py — Monte-Cristo Patrimoine\n")

    header_template = load_partial("header.html")
    footer_partial  = load_partial("footer.html")

    pages   = load_pages()
    targets = [p for p in pages if p.get("file") not in EXCLUDE]

    updated   = []
    no_change = []
    errors    = []

    for page in targets:
        filename = page.get("file", "")
        filepath = SITE_ROOT / filename

        if not filepath.exists():
            errors.append((filename, "fichier HTML introuvable sur le disque"))
            continue

        # Résolution du header avec active state correct pour cette page
        header_resolved = resolve_header(header_template, filename)

        # Vérification : aucun placeholder résiduel
        if "{{ACTIVE_" in header_resolved:
            errors.append((filename, "placeholder non résolu dans le header"))
            continue

        original = filepath.read_text(encoding="utf-8")
        content  = original

        # Remplacement header
        content, err = replace_between(content, HEADER_BEGIN, HEADER_END, header_resolved)
        if err:
            errors.append((filename, f"header — {err}"))
            continue

        # Remplacement footer
        content, err = replace_between(content, FOOTER_BEGIN, FOOTER_END, footer_partial)
        if err:
            errors.append((filename, f"footer — {err}"))
            continue

        if content == original:
            no_change.append(filename)
        else:
            filepath.write_text(content, encoding="utf-8")
            updated.append(filename)

    # ── Rapport terminal ─────────────────────────────────────────────────────
    print(f"Pages cibles   : {len(targets)}")
    print(f"Mises à jour   : {len(updated)}")
    print(f"Déjà à jour    : {len(no_change)}")
    print(f"Erreurs        : {len(errors)}")

    if updated:
        print("\n✅ Mises à jour :")
        for f in updated:
            active_key = ACTIVE_MAP.get(f)
            tag = f" [active: {active_key}]" if active_key else " [aucun active]"
            print(f"   {f}{tag}")

    if no_change:
        print("\n↩️  Déjà à jour (aucun changement) :")
        for f in no_change:
            active_key = ACTIVE_MAP.get(f)
            tag = f" [active: {active_key}]" if active_key else " [aucun active]"
            print(f"   {f}{tag}")

    if errors:
        print("\n❌ Erreurs :")
        for f, msg in errors:
            print(f"   {f} — {msg}")
        print()
        print("⚠️  Certaines pages n'ont pas les marqueurs attendus.")
        print("   Ajoutez les marqueurs manuellement avant de relancer le script :")
        print(f"   Header : {HEADER_BEGIN} ... {HEADER_END}")
        print(f"   Footer : {FOOTER_BEGIN} ... {FOOTER_END}")
        sys.exit(1)

    print("\n✅ Synchronisation terminée.")


if __name__ == "__main__":
    main()
