#!/usr/bin/env python3
"""
check-header-css.py — Monte-Cristo Patrimoine
Vérifie que les règles CSS du header CTA sont correctes dans toutes les pages
qui embarquent un <style> inline.

Règles obligatoires :
  1. .nav-rdv masqué globalement (display:none)
  2. Seul .nav.open .nav-rdv peut réafficher le CTA mobile (display:flex/inline-flex)
  3. .header-inner > .btn (enfant direct) en mobile — pas .header-inner .btn (descendant)

Règle interdite :
  - Un sélecteur sans .nav.open qui met display:flex/inline-flex sur .nav-rdv
    → causerait un doublon CTA sur mobile menu fermé

Usage : python3 seo/scripts/check-header-css.py
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

SKIP = {"404.html", "mockup-contenu.html"}


def extract_style_blocks(html: str) -> str:
    return "\n".join(re.findall(r"<style[^>]*>(.*?)</style>", html, re.S | re.I))


def has_global_header_marker(html: str) -> bool:
    return "<!-- BEGIN GLOBAL HEADER -->" in html


def extract_css_rules(css: str) -> list[tuple[str, str]]:
    """
    Extrait (sélecteur, bloc) depuis le CSS, en gérant les blocs @media.
    Retourne une liste de tuples (selector, declarations).
    Les règles dans @media sont retournées avec le contexte @media préfixé.
    """
    rules = []
    # On retire les commentaires CSS
    css_clean = re.sub(r"/\*.*?\*/", "", css, flags=re.S)

    # Itération token par token avec un mini-parser de blocs
    i = 0
    n = len(css_clean)
    context_stack = []  # stack of @media contexts

    while i < n:
        # Cherche le prochain { ou }
        brace_open  = css_clean.find("{", i)
        brace_close = css_clean.find("}", i)

        if brace_open == -1 and brace_close == -1:
            break

        # Prochain token est-il { ou } ?
        if brace_open != -1 and (brace_close == -1 or brace_open < brace_close):
            # On a un {
            selector_raw = css_clean[i:brace_open].strip()
            i = brace_open + 1

            if selector_raw.startswith("@"):
                # Début d'un @media ou @keyframes — on empile
                context_stack.append(selector_raw)
            else:
                # Règle CSS normale : cherche le } correspondant
                end = css_clean.find("}", i)
                if end == -1:
                    break
                declarations = css_clean[i:end].strip()
                # Contexte : @media courant si présent
                ctx = context_stack[-1] if context_stack else ""
                rules.append((selector_raw, declarations, ctx))
                i = end + 1
        else:
            # On a un } → fermeture de @media
            if context_stack:
                context_stack.pop()
            i = brace_close + 1

    return rules


def check_page(path: Path) -> list[dict]:
    issues = []
    html = path.read_text(encoding="utf-8")

    if not has_global_header_marker(html):
        return []
    css = extract_style_blocks(html)
    if not css:
        return []

    name = path.name
    rules = extract_css_rules(css)

    # ── Règle 1 : .nav-rdv doit être masqué globalement ──────────────────────
    has_navrdv_hidden = any(
        "nav-rdv" in sel and "display" in decl and "none" in decl
        for sel, decl, _ in rules
    )
    if not has_navrdv_hidden:
        issues.append({
            "severity": "critique",
            "page": name,
            "rule": "nav-rdv masquage global manquant",
            "detail": "Aucune règle .nav-rdv { display:none } trouvée"
        })

    # ── Règle 2 : pas de réaffichage de .nav-rdv hors .nav.open ──────────────
    # On cherche les règles qui mettent display:flex/inline-flex sur un sélecteur
    # contenant nav-rdv — et on vérifie que le sélecteur contient aussi nav.open
    for sel, decl, ctx in rules:
        if "nav-rdv" not in sel:
            continue
        if not re.search(r"display\s*:\s*(inline-flex|flex)\b", decl):
            continue
        # Ce sélecteur rend .nav-rdv visible — doit être scopé à .nav.open
        is_scoped = "nav.open" in sel or ".open" in sel
        if not is_scoped:
            issues.append({
                "severity": "critique",
                "page": name,
                "rule": "nav-rdv réaffichage non scopé",
                "detail": (
                    f"Sélecteur '{sel.strip()}' rend .nav-rdv visible "
                    f"sans .nav.open → doublon CTA possible"
                )
            })

    # ── Règle 3 : .nav.open .nav-rdv doit exister dans un @media ─────────────
    has_media = any(ctx for _, _, ctx in rules)
    has_open_navrdv = any(
        "nav.open" in sel and "nav-rdv" in sel
        and re.search(r"display\s*:\s*(inline-flex|flex)\b", decl)
        for sel, decl, _ in rules
    )
    if has_media and not has_open_navrdv:
        issues.append({
            "severity": "important",
            "page": name,
            "rule": "nav-rdv réaffichage mobile manquant",
            "detail": (
                ".nav.open .nav-rdv { display:inline-flex } absent "
                "— le CTA mobile ne s'affiche pas quand le menu est ouvert"
            )
        })

    # ── Règle 4 : préférer .header-inner > .btn (enfant direct) ──────────────
    for sel, decl, ctx in rules:
        # Sélecteur descendant sans > entre header-inner et .btn
        if (re.search(r"\.header-inner\s+\.btn", sel)
                and not re.search(r"\.header-inner\s*>\s*\.btn", sel)
                and "display" in decl and "none" in decl):
            issues.append({
                "severity": "important",
                "page": name,
                "rule": "masquage CTA desktop — sélecteur trop large",
                "detail": (
                    f"'{sel.strip()}' : utiliser .header-inner > .btn "
                    f"(enfant direct) pour ne pas masquer les .btn dans la nav"
                )
            })

    return issues


def main():
    print("🔍  check-header-css.py — Monte-Cristo Patrimoine\n")

    all_issues: list[dict] = []
    pages_checked = 0

    candidates = sorted(
        p for p in SITE_ROOT.glob("*.html") if p.name not in SKIP
    )

    for path in candidates:
        html = path.read_text(encoding="utf-8")
        if not (has_global_header_marker(html) and extract_style_blocks(html)):
            continue
        pages_checked += 1
        issues = check_page(path)
        if issues:
            all_issues.extend(issues)
            for issue in issues:
                sev = issue["severity"]
                icon = "🔴" if sev == "critique" else "🟠"
                print(f"  {icon} [{sev.upper()}] {issue['page']} — {issue['rule']}")
                print(f"       {issue['detail']}")

    critiques  = sum(1 for i in all_issues if i["severity"] == "critique")
    importants = sum(1 for i in all_issues if i["severity"] == "important")

    print(f"\nPages contrôlées : {pages_checked}")
    print(f"Critiques  🔴 : {critiques}")
    print(f"Importants 🟠 : {importants}")

    summary = {
        "generated_at": datetime.now().isoformat(timespec="seconds"),
        "pages_checked": pages_checked,
        "summary": {"critique": critiques, "important": importants, "amelioration": 0},
        "issues": all_issues
    }
    REPORTS_DIR.mkdir(parents=True, exist_ok=True)
    report_path = REPORTS_DIR / "header-css-check.json"
    report_path.write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"\n📄 Rapport : {report_path}")

    if critiques > 0 or importants > 0:
        print("\n❌  Problèmes CSS header détectés — corriger avant déploiement.")
        sys.exit(1)
    else:
        print("\n✅  CSS header conforme sur toutes les pages.")


if __name__ == "__main__":
    main()
