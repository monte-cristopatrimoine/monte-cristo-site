#!/usr/bin/env python3
"""
Contrôle pré-commit — Monte-Cristo Patrimoine
Vérifie l'architecture du site avant chaque commit.
Lance uniquement les contrôles rapides (pas PageSpeed, pas GA4).

Exit code :
  0 — aucun problème critique ou important → OK pour committer
  1 — problème détecté → corriger avant de committer

Usage : python3 seo/scripts/pre-commit-check.py
        (depuis la racine du site)

Pour l'intégrer comme hook git :
  echo 'python3 seo/scripts/pre-commit-check.py' > .git/hooks/pre-commit
  chmod +x .git/hooks/pre-commit
"""

import json
import re
import subprocess
import sys
from pathlib import Path
from datetime import datetime

SCRIPT_DIR  = Path(__file__).parent
SITE_ROOT   = SCRIPT_DIR.parent.parent
REPORTS_DIR = SCRIPT_DIR.parent / "reports"

CHECKS = [
    ("check-links",   SCRIPT_DIR / "check-links.py"),
    ("check-urls",    SCRIPT_DIR / "check-urls.py"),
    ("check-orphans", SCRIPT_DIR / "check-orphans.py"),
    ("check-footer",  SCRIPT_DIR / "check-footer.py"),
]

# ── Lancement ─────────────────────────────────────────────────────────────────

def run(name, path):
    result = subprocess.run(
        [sys.executable, str(path)],
        cwd=str(SITE_ROOT),
        capture_output=True,
        text=True,
    )
    return result.returncode == 0


# ── Lecture des totaux ────────────────────────────────────────────────────────

def get_totals():
    totals = {"critique": 0, "important": 0}

    def add(path_key, c_key="critique", i_key="important"):
        path = REPORTS_DIR / path_key
        if not path.exists():
            return
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
            s    = data.get("summary", {})
            totals["critique"]  += s.get(c_key, 0)
            totals["important"] += s.get(i_key, 0)
        except Exception:
            pass

    add("links-report.json",   c_key="broken",    i_key="future")
    add("orphans-report.json")
    add("footer-report.json")

    # urls-report.md (pas de JSON) — on lit les chiffres après les emojis dans le résumé
    urls_path = REPORTS_DIR / "urls-report.md"
    if urls_path.exists():
        content = urls_path.read_text(encoding="utf-8")
        m = re.search(r"🔴 Critiques\s*\|\s*\*\*(\d+)\*\*", content)
        if m:
            totals["critique"] += int(m.group(1))
        m = re.search(r"🟠 Importants\s*\|\s*\*\*(\d+)\*\*", content)
        if m:
            totals["important"] += int(m.group(1))

    return totals


# ── Point d'entrée ────────────────────────────────────────────────────────────

def main():
    print(f"⚡ Contrôle pré-commit — Monte-Cristo Patrimoine")
    print(f"   {datetime.now().strftime('%d/%m/%Y à %H:%M')}\n")

    failed_scripts = []
    for name, path in CHECKS:
        print(f"  ▶ {name}…", end=" ", flush=True)
        ok = run(name, path)
        print("OK" if ok else "ERREUR (script)")
        if not ok:
            failed_scripts.append(name)

    print()
    totals = get_totals()
    c, i   = totals["critique"], totals["important"]

    print(f"📊 Résultat :")
    print(f"   🔴 Critiques  : {c}")
    print(f"   🟠 Importants : {i}")
    print()

    if failed_scripts:
        print(f"⚠️  Scripts en erreur : {', '.join(failed_scripts)}")
        print("   Consulter les messages ci-dessus pour le détail.")
        sys.exit(1)

    if c > 0 or i > 0:
        print("❌  COMMIT BLOQUÉ — corriger les problèmes avant de committer.")
        print("   Consulter seo/reports/ pour le détail.")
        sys.exit(1)

    print("✅  OK — le site peut être commité.")
    sys.exit(0)


if __name__ == "__main__":
    main()
