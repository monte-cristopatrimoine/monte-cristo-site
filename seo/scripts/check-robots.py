#!/usr/bin/env python3
"""
Contrôle robots.txt — Monte-Cristo Patrimoine
Analyse le fichier robots.txt et vérifie sa cohérence avec le site statique.

Contrôles effectués :
- Existence du fichier
- Présence et validité de la directive Sitemap
- Cohérence avec sitemap.xml (même URL)
- Règles inutiles ou héritées d'un autre CMS (WordPress, etc.)
- Règles qui bloquent accidentellement des pages importantes
- Syntaxe de base (User-agent, Allow, Disallow)

Le script propose une version propre du fichier mais NE LA APPLIQUE PAS.
L'utilisateur doit valider avant toute modification.

Usage : python3 seo/scripts/check-robots.py
        (depuis la racine du site)
"""

import re
import sys
from pathlib import Path
from datetime import datetime

SCRIPT_DIR  = Path(__file__).parent
SITE_ROOT   = SCRIPT_DIR.parent.parent
REPORTS_DIR = SCRIPT_DIR.parent / "reports"
ROBOTS_PATH = SITE_ROOT / "robots.txt"
SITEMAP_PATH = SITE_ROOT / "sitemap.xml"
BASE_URL    = "https://monte-cristo.net"

# Règles connues comme inutiles sur un site statique
USELESS_RULES = {
    "/wp-admin/":    "Dossier WordPress — inutile sur un site statique",
    "/wp-login.php": "Page de connexion WordPress — inutile sur un site statique",
    "/wp-content/":  "Dossier WordPress — inutile sur un site statique",
    "/wp-includes/": "Dossier WordPress — inutile sur un site statique",
    "/wp-json/":     "API WordPress — inutile sur un site statique",
    "/xmlrpc.php":   "API XML-RPC WordPress — inutile sur un site statique",
    "/cgi-bin/":     "Dossier CGI — probablement inutile sur ce site",
}

# Pages importantes qui ne doivent pas être bloquées
IMPORTANT_PATHS = [
    "/", "/le-cabinet", "/particuliers", "/entreprises",
    "/blog", "/article-cgp-independant", "/article-frais-bancaires",
    "/simulateur-frais",
]

# ── Parsing ───────────────────────────────────────────────────────────────────

def parse_robots(content):
    """Parse robots.txt en blocs User-agent / règles."""
    blocks   = []
    sitemap_directives = []
    current_agents = []
    current_rules  = []

    for raw_line in content.splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#"):
            continue
        if ":" not in line:
            continue
        key, _, value = line.partition(":")
        key   = key.strip().lower()
        value = value.strip()

        if key == "user-agent":
            if current_rules:
                blocks.append({"agents": current_agents, "rules": current_rules})
                current_agents = []
                current_rules  = []
            current_agents.append(value)
        elif key in ("allow", "disallow"):
            current_rules.append({"type": key, "path": value})
        elif key == "sitemap":
            sitemap_directives.append(value)

    if current_agents or current_rules:
        blocks.append({"agents": current_agents, "rules": current_rules})

    return blocks, sitemap_directives

def load_sitemap_url():
    """Lit l'URL attendue du sitemap depuis sitemap.xml."""
    if not SITEMAP_PATH.exists():
        return None
    return f"{BASE_URL}/sitemap.xml"

# ── Contrôles ─────────────────────────────────────────────────────────────────

def run_checks(content, blocks, sitemap_directives, expected_sitemap_url):
    issues = []

    def add(level, code, message):
        issues.append({"level": level, "code": code, "message": message})

    # 1. Présence du fichier (déjà garantie si on est ici)
    # 2. Directive Sitemap
    if not sitemap_directives:
        add("critique", "SITEMAP_MISSING", "Aucune directive `Sitemap:` — Google ne trouvera pas le sitemap automatiquement")
    else:
        for url in sitemap_directives:
            if url != expected_sitemap_url:
                add("important", "SITEMAP_URL_MISMATCH",
                    f"URL du sitemap incorrecte : `{url}` — attendu : `{expected_sitemap_url}`")
            else:
                add("ok", "SITEMAP_OK", f"Sitemap correctement déclaré : {url}")

    # 3. Analyse des blocs de règles
    for block in blocks:
        agents = block["agents"]
        rules  = block["rules"]
        is_global = "*" in agents

        for rule in rules:
            path = rule["path"]
            rtype = rule["type"]

            # Règles inutiles héritées de WordPress
            if path in USELESS_RULES:
                add("important", "USELESS_RULE",
                    f"`{rtype.capitalize()}: {path}` — {USELESS_RULES[path]}")

            # Règle qui bloquerait une page importante
            # Logique : Disallow: /x bloque les URLs qui commencent par /x
            if rtype == "disallow" and path and path != "/":
                for important in IMPORTANT_PATHS:
                    # Une page importante est bloquée si son chemin commence par le chemin interdit
                    if important.startswith(path.rstrip("/")):
                        add("critique", "BLOCKS_IMPORTANT_PAGE",
                            f"`Disallow: {path}` bloquerait `{important}`")

            # Disallow vide = tout est autorisé (OK mais à signaler si ambigu)
            if rtype == "disallow" and path == "":
                add("ok", "DISALLOW_EMPTY", "Disallow vide (tout autorisé) — syntaxe correcte")

    # 4. Cohérence générale
    has_global_allow = any(
        r["type"] == "allow" and r["path"] in ("/", "")
        for b in blocks for r in b["rules"]
        if "*" in b["agents"]
    )
    has_global_agent = any("*" in b["agents"] for b in blocks)

    if not has_global_agent:
        add("amelioration", "NO_GLOBAL_AGENT",
            "Aucun bloc `User-agent: *` — ajouter un bloc global pour couvrir tous les robots")
    elif not has_global_allow:
        add("amelioration", "NO_EXPLICIT_ALLOW",
            "Pas de `Allow: /` explicite — recommandé pour clarifier que tout est autorisé")

    return issues

# ── Version propre proposée ───────────────────────────────────────────────────

PROPOSED_ROBOTS = f"""User-agent: *
Allow: /

Sitemap: {BASE_URL}/sitemap.xml
"""

# ── Rapport ───────────────────────────────────────────────────────────────────

EMOJI = {"critique": "🔴", "important": "🟠", "amelioration": "🟡", "ok": "✅"}

def build_report(content, issues, sitemap_directives, has_useless, generated_at):
    lines = []
    a = lines.append

    critiques     = [i for i in issues if i["level"] == "critique"]
    importants    = [i for i in issues if i["level"] == "important"]
    ameliorations = [i for i in issues if i["level"] == "amelioration"]
    oks           = [i for i in issues if i["level"] == "ok"]

    a("# Contrôle robots.txt — Monte-Cristo Patrimoine")
    a(f"*Généré le {generated_at}*\n")

    a("## Résumé\n")
    a(f"| | |")
    a(f"|---|---|")
    a(f"| Problèmes critiques 🔴 | **{len(critiques)}** |")
    a(f"| Problèmes importants 🟠 | **{len(importants)}** |")
    a(f"| Améliorations 🟡 | **{len(ameliorations)}** |")
    a(f"| Contrôles OK ✅ | **{len(oks)}** |")
    a("")

    a("## Contenu actuel de `robots.txt`\n")
    a("```")
    a(content.strip())
    a("```\n")

    if critiques:
        a("---\n## 🔴 Problèmes critiques\n")
        for i in critiques:
            a(f"- {i['message']}")
        a("")

    if importants:
        a("---\n## 🟠 Problèmes importants\n")
        for i in importants:
            a(f"- {i['message']}")
        a("")

    if ameliorations:
        a("---\n## 🟡 Améliorations\n")
        for i in ameliorations:
            a(f"- {i['message']}")
        a("")

    if oks:
        a("---\n## ✅ Contrôles OK\n")
        for i in oks:
            a(f"- {i['message']}")
        a("")

    if has_useless:
        a("---\n## Version propre proposée\n")
        a("> ⚠️ **Le fichier actuel contient des règles inutiles** héritées d'un autre CMS.")
        a("> La version ci-dessous est plus propre et adaptée à un site statique.")
        a("> **Pour appliquer : valider avec l'équipe, puis remplacer `robots.txt`.**\n")
        a("```")
        a(PROPOSED_ROBOTS.strip())
        a("```\n")
        a("Différences avec la version actuelle :")
        a("- Suppression des règles WordPress (`/wp-admin/`, `/wp-login.php`, `/wp-content/`, `/wp-includes/`)")
        a("- Conservation de `User-agent: *`, `Allow: /` et `Sitemap:`")
        a("")

    a("---")
    a("*Rapport généré par `seo/scripts/check-robots.py`*")
    return "\n".join(lines)

# ── Point d'entrée ────────────────────────────────────────────────────────────

def main():
    print("🤖 Contrôle robots.txt — Monte-Cristo Patrimoine")
    print(f"   Racine : {SITE_ROOT}\n")

    # Existence
    if not ROBOTS_PATH.exists():
        print("❌ robots.txt introuvable à la racine du site.")
        print("   Créez un fichier robots.txt avec au minimum :")
        print(f"   User-agent: *")
        print(f"   Allow: /")
        print(f"   Sitemap: {BASE_URL}/sitemap.xml")
        sys.exit(1)

    content = ROBOTS_PATH.read_text(encoding="utf-8")
    print(f"   Fichier trouvé : {ROBOTS_PATH}")
    print(f"   Taille : {len(content)} caractères, {len(content.splitlines())} lignes\n")

    blocks, sitemap_directives = parse_robots(content)
    expected_sitemap_url = load_sitemap_url()
    issues = run_checks(content, blocks, sitemap_directives, expected_sitemap_url)

    has_useless = any(i["code"] == "USELESS_RULE" for i in issues)

    # Affichage terminal
    for i in issues:
        if i["level"] == "ok":
            continue
        print(f"   {EMOJI[i['level']]} [{i['level'].upper()}] {i['message']}")

    critiques  = sum(1 for i in issues if i["level"] == "critique")
    importants = sum(1 for i in issues if i["level"] == "important")
    amelios    = sum(1 for i in issues if i["level"] == "amelioration")
    oks_count  = sum(1 for i in issues if i["level"] == "ok")

    print(f"\n📊 Résumé :")
    print(f"   🔴 Critiques    : {critiques}")
    print(f"   🟠 Importants   : {importants}")
    print(f"   🟡 Améliorations: {amelios}")
    print(f"   ✅ OK           : {oks_count}")

    if has_useless:
        print(f"\n⚠️  Version propre proposée dans le rapport (à valider avant application).")

    # Rapport
    generated_at = datetime.now().strftime("%d/%m/%Y à %H:%M")
    REPORTS_DIR.mkdir(parents=True, exist_ok=True)
    report_path = REPORTS_DIR / "robots-check.md"
    report_path.write_text(
        build_report(content, issues, sitemap_directives, has_useless, generated_at),
        encoding="utf-8"
    )
    print(f"\n📄 Rapport : {report_path}")

if __name__ == "__main__":
    main()
