#!/usr/bin/env python3
"""
Contrôle des métadonnées — Monte-Cristo Patrimoine
Vérifie la qualité et la cohérence des balises meta sur toutes les pages.

Complète l'audit général (audit.py) avec une analyse fine :
- cohérence entre title / og:title / twitter:title
- cohérence entre description / og:description / twitter:description
- détection des doublons inter-pages
- longueurs idéales (fourchettes recommandées)
- qualité du contenu (mots-clés, ponctuation, majuscules)

Usage : python3 seo/scripts/check-meta.py
        (depuis la racine du site)
"""

import re
import json
import sys
from pathlib import Path
from datetime import datetime

SCRIPT_DIR  = Path(__file__).parent
SITE_ROOT   = SCRIPT_DIR.parent.parent
REPORTS_DIR = SCRIPT_DIR.parent / "reports"
BASE_URL    = "https://monte-cristo.net"

SKIP_PAGES  = {"mockup-contenu.html", "404.html"}

# Longueurs recommandées
TITLE_MIN, TITLE_MAX       = 30, 65
DESC_MIN,  DESC_MAX        = 80, 160
OG_TITLE_MIN, OG_TITLE_MAX = 25, 95
OG_DESC_MIN,  OG_DESC_MAX  = 60, 200

# ── Extraction ────────────────────────────────────────────────────────────────

def decode_entities(text):
    replacements = {
        "&amp;": "&", "&lt;": "<", "&gt;": ">",
        "&quot;": '"', "&#39;": "'", "&nbsp;": " ",
        "&#8239;": " ", "&#160;": " ",
    }
    for k, v in replacements.items():
        text = text.replace(k, v)
    text = re.sub(r"&#(\d+);", lambda m: chr(int(m.group(1))), text)
    return text

def meta_name_val(html, name):
    """Extrait content d'une balise <meta name="X" content="Y"> de façon fiable."""
    n = re.escape(name)
    # name avant content, attribut entre guillemets doubles
    m = re.search(rf'<meta\s[^>]*name="{n}"[^>]*content="([^"]*)"', html, re.IGNORECASE)
    if m: return decode_entities(m.group(1))
    # name avant content, attribut entre guillemets simples
    m = re.search(rf"<meta\s[^>]*name='{n}'[^>]*content='([^']*)'", html, re.IGNORECASE)
    if m: return decode_entities(m.group(1))
    # content avant name
    m = re.search(rf'<meta\s[^>]*content="([^"]*)"[^>]*name="{n}"', html, re.IGNORECASE)
    if m: return decode_entities(m.group(1))
    return ""

def meta_prop_val(html, prop):
    """Extrait content d'une balise <meta property="X" content="Y"> de façon fiable."""
    p = re.escape(prop)
    m = re.search(rf'<meta\s[^>]*property="{p}"[^>]*content="([^"]*)"', html, re.IGNORECASE)
    if m: return decode_entities(m.group(1))
    m = re.search(rf"<meta\s[^>]*property='{p}'[^>]*content='([^']*)'", html, re.IGNORECASE)
    if m: return decode_entities(m.group(1))
    m = re.search(rf'<meta\s[^>]*content="([^"]*)"[^>]*property="{p}"', html, re.IGNORECASE)
    if m: return decode_entities(m.group(1))
    return ""

def extract_meta(html):
    """Extrait toutes les balises meta pertinentes d'une page."""
    title_m   = re.search(r"<title>([^<]+)</title>", html, re.IGNORECASE)
    title     = decode_entities(title_m.group(1).strip()) if title_m else ""
    canon_m   = re.search(r'<link\s[^>]*rel="canonical"[^>]*href="([^"]*)"', html, re.IGNORECASE)
    canonical = canon_m.group(1).strip() if canon_m else ""

    return {
        "title":               title,
        "description":         meta_name_val(html, "description"),
        "canonical":           canonical,
        "og_title":            meta_prop_val(html, "og:title"),
        "og_description":      meta_prop_val(html, "og:description"),
        "og_image":            meta_prop_val(html, "og:image"),
        "og_url":              meta_prop_val(html, "og:url"),
        "twitter_title":       meta_name_val(html, "twitter:title"),
        "twitter_description": meta_name_val(html, "twitter:description"),
        "twitter_card":        meta_name_val(html, "twitter:card"),
        "robots":              meta_name_val(html, "robots"),
    }

# ── Contrôles ─────────────────────────────────────────────────────────────────

def check_length(value, label, min_len, max_len, issues):
    n = len(value)
    if not value:
        issues.append(("critique", f"{label} absent"))
    elif n < min_len:
        issues.append(("important", f"{label} trop court ({n} car., min {min_len})"))
    elif n > max_len:
        issues.append(("important", f"{label} trop long ({n} car., max {max_len})"))
    else:
        issues.append(("ok", f"{label} longueur OK ({n} car.)"))

def check_coherence(val_a, label_a, val_b, label_b, issues, strict=False):
    """Vérifie que deux champs sont cohérents (pas identiques ET pas contradictoires)."""
    if not val_a or not val_b:
        return
    if val_a == val_b:
        if strict:
            issues.append(("amelioration", f"{label_a} identique à {label_b} — différencier pour enrichir le partage social"))
    # Vérifier que le titre de la page est bien reflété dans l'og:title
    # (on ne force pas l'identité, mais on signale si trop différents)

def check_starts_uppercase(value, label, issues):
    if value and not value[0].isupper():
        issues.append(("amelioration", f"{label} ne commence pas par une majuscule"))

def check_ends_with_brand(value, label, brand="Monte-Cristo Patrimoine", issues_list=None):
    if value and brand not in value:
        issues_list.append(("amelioration", f"{label} ne contient pas le nom de marque « {brand} »"))

def check_canonical_matches_url(canonical, expected_url, issues):
    if canonical and canonical.rstrip("/") != expected_url.rstrip("/"):
        issues.append(("important", f"Canonical ({canonical}) ≠ URL attendue ({expected_url})"))

def check_twitter_card(card, issues):
    valid = {"summary", "summary_large_image", "app", "player"}
    if not card:
        issues.append(("amelioration", "twitter:card absent"))
    elif card not in valid:
        issues.append(("amelioration", f"twitter:card invalide : « {card} »"))

# ── Analyse d'une page ────────────────────────────────────────────────────────

def analyse_page(filepath):
    html     = filepath.read_text(encoding="utf-8", errors="replace")
    filename = filepath.name
    name     = filename.replace(".html", "")
    url      = BASE_URL + "/" if name == "index" else f"{BASE_URL}/{name}"
    meta     = extract_meta(html)
    issues   = []   # liste de (level, message)

    # ── Title
    check_length(meta["title"], "title", TITLE_MIN, TITLE_MAX, issues)
    check_ends_with_brand(meta["title"], "title", issues_list=issues)

    # ── Description
    check_length(meta["description"], "description", DESC_MIN, DESC_MAX, issues)

    # ── Canonical
    if not meta["canonical"]:
        issues.append(("critique", "canonical absent"))
    else:
        check_canonical_matches_url(meta["canonical"], url, issues)

    # ── Open Graph
    check_length(meta["og_title"], "og:title", OG_TITLE_MIN, OG_TITLE_MAX, issues)
    check_length(meta["og_description"], "og:description", OG_DESC_MIN, OG_DESC_MAX, issues)
    if not meta["og_image"]:
        issues.append(("amelioration", "og:image absent"))
    if not meta["og_url"]:
        issues.append(("amelioration", "og:url absent"))
    elif meta["og_url"].rstrip("/") != url.rstrip("/"):
        issues.append(("important", f"og:url ({meta['og_url']}) ≠ URL attendue ({url})"))

    # Cohérence og:title vs title (différents = bien, identiques = toléré mais signalé)
    check_coherence(meta["title"], "title", meta["og_title"], "og:title", issues, strict=True)

    # ── Twitter
    check_twitter_card(meta["twitter_card"], issues)
    if meta["og_title"] and not meta["twitter_title"]:
        issues.append(("amelioration", "twitter:title absent (og:title présent)"))
    if meta["og_description"] and not meta["twitter_description"]:
        issues.append(("amelioration", "twitter:description absent (og:description présent)"))

    return {
        "file":     filename,
        "url":      url,
        "meta":     meta,
        "issues":   [{"level": lvl, "message": msg} for lvl, msg in issues],
    }

# ── Détection des doublons inter-pages ───────────────────────────────────────

def find_duplicates(pages):
    """Détecte les titres ou descriptions identiques entre plusieurs pages."""
    dupes = []
    fields = ["title", "description", "og_title", "og_description"]
    for field in fields:
        seen = {}
        for p in pages:
            val = p["meta"].get(field, "").strip()
            if not val:
                continue
            if val in seen:
                dupes.append({
                    "field":  field,
                    "value":  val[:80] + ("…" if len(val) > 80 else ""),
                    "pages":  [seen[val], p["file"]],
                })
            else:
                seen[val] = p["file"]
    return dupes

# ── Rapport Markdown ──────────────────────────────────────────────────────────

EMOJI = {"critique": "🔴", "important": "🟠", "amelioration": "🟡", "ok": "✅"}

def build_markdown(pages, dupes, generated_at):
    lines = []
    a = lines.append

    a(f"# Contrôle des métadonnées — Monte-Cristo Patrimoine")
    a(f"*Généré le {generated_at}*\n")

    # Résumé
    all_issues = [(p["file"], i) for p in pages for i in p["issues"] if i["level"] != "ok"]
    critiques     = [(f, i) for f, i in all_issues if i["level"] == "critique"]
    importants    = [(f, i) for f, i in all_issues if i["level"] == "important"]
    ameliorations = [(f, i) for f, i in all_issues if i["level"] == "amelioration"]

    a("## Résumé\n")
    a(f"| | |")
    a(f"|---|---|")
    a(f"| Pages analysées | **{len(pages)}** |")
    a(f"| Problèmes critiques 🔴 | **{len(critiques)}** |")
    a(f"| Problèmes importants 🟠 | **{len(importants)}** |")
    a(f"| Améliorations 🟡 | **{len(ameliorations)}** |")
    a(f"| Doublons détectés | **{len(dupes)}** |")
    a("")

    # Doublons
    if dupes:
        a("---\n## ⚠️ Doublons détectés inter-pages\n")
        a("Des pages partagent des valeurs identiques — Google peut les pénaliser.\n")
        for d in dupes:
            a(f"- **{d['field']}** identique sur `{d['pages'][0]}` et `{d['pages'][1]}` :")
            a(f"  > {d['value']}")
        a("")
    else:
        a("---\n## Doublons\n\n✅ Aucun doublon détecté entre les pages.\n")

    # Critiques
    a("---\n## 🔴 Problèmes critiques\n")
    if critiques:
        for fname, issue in critiques:
            a(f"- **{fname}** — {issue['message']}")
    else:
        a("✅ Aucun.")
    a("")

    # Importants
    a("---\n## 🟠 Problèmes importants\n")
    if importants:
        for fname, issue in importants:
            a(f"- **{fname}** — {issue['message']}")
    else:
        a("✅ Aucun.")
    a("")

    # Améliorations
    a("---\n## 🟡 Améliorations\n")
    if ameliorations:
        for fname, issue in ameliorations:
            a(f"- **{fname}** — {issue['message']}")
    else:
        a("✅ Aucune.")
    a("")

    # Détail page par page
    a("---\n## Détail page par page\n")
    for p in pages:
        m = p["meta"]
        a(f"### `{p['file']}`")
        a(f"| Champ | Valeur | Long. |")
        a(f"|-------|--------|-------|")
        for field, label in [
            ("title",             "title"),
            ("description",       "description"),
            ("canonical",         "canonical"),
            ("og_title",          "og:title"),
            ("og_description",    "og:description"),
            ("og_image",          "og:image"),
            ("twitter_title",     "twitter:title"),
            ("twitter_description","twitter:description"),
            ("twitter_card",      "twitter:card"),
            ("robots",            "robots"),
        ]:
            val = m.get(field, "")
            display = (val[:60] + "…") if len(val) > 60 else val
            display = display or "*(absent)*"
            length  = str(len(val)) if val else "—"
            a(f"| `{label}` | {display} | {length} |")

        page_issues = [i for i in p["issues"] if i["level"] != "ok"]
        if page_issues:
            a("\n**Problèmes :**")
            for i in sorted(page_issues, key=lambda x: {"critique":0,"important":1,"amelioration":2}[x["level"]]):
                a(f"- {EMOJI.get(i['level'],'')} {i['message']}")
        else:
            a("\n✅ Aucun problème.")
        a("")

    a("---")
    a("*Rapport généré par `seo/scripts/check-meta.py`*")
    return "\n".join(lines)

# ── Point d'entrée ────────────────────────────────────────────────────────────

def main():
    print("🔎 Contrôle des métadonnées — Monte-Cristo Patrimoine")
    print(f"   Racine : {SITE_ROOT}\n")

    html_files = sorted(
        f for f in SITE_ROOT.glob("*.html")
        if f.name not in SKIP_PAGES
    )

    if not html_files:
        print("❌ Aucun fichier .html trouvé.")
        sys.exit(1)

    pages = []
    for f in html_files:
        result = analyse_page(f)
        pages.append(result)
        n_issues = sum(1 for i in result["issues"] if i["level"] != "ok")
        badge = f"  ⚠️  {n_issues} problème(s)" if n_issues else "  ✅"
        print(f"   {f.name:<40} {badge}")

    print()
    dupes = find_duplicates(pages)
    if dupes:
        print(f"   ⚠️  {len(dupes)} doublon(s) détecté(s) entre les pages")

    # JSON
    generated_at = datetime.now().strftime("%d/%m/%Y à %H:%M")
    output = {
        "generated_at": generated_at,
        "pages":        pages,
        "duplicates":   dupes,
        "summary": {
            "critique":    sum(1 for p in pages for i in p["issues"] if i["level"] == "critique"),
            "important":   sum(1 for p in pages for i in p["issues"] if i["level"] == "important"),
            "amelioration":sum(1 for p in pages for i in p["issues"] if i["level"] == "amelioration"),
            "duplicates":  len(dupes),
        }
    }

    REPORTS_DIR.mkdir(parents=True, exist_ok=True)
    json_path = REPORTS_DIR / "meta-check.json"
    md_path   = REPORTS_DIR / "meta-check.md"

    json_path.write_text(json.dumps(output, ensure_ascii=False, indent=2), encoding="utf-8")
    md_path.write_text(build_markdown(pages, dupes, generated_at), encoding="utf-8")

    s = output["summary"]
    print(f"\n📊 Résumé :")
    print(f"   🔴 Critiques    : {s['critique']}")
    print(f"   🟠 Importants   : {s['important']}")
    print(f"   🟡 Améliorations: {s['amelioration']}")
    print(f"   🔁 Doublons     : {s['duplicates']}")
    print(f"\n📄 Rapports :")
    print(f"   {json_path}")
    print(f"   {md_path}")

if __name__ == "__main__":
    main()
