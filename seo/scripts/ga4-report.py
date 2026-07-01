#!/usr/bin/env python3
"""
Rapport GA4 — Monte-Cristo Patrimoine
Interroge l'API GA4 Data directement via un compte de service.

Credentials : ~/.config/monte-cristo/ga4-credentials.json
Propriété   : 538539081 (G-2QZE9BL80W)

Usage : python3 seo/scripts/ga4-report.py
        (depuis la racine du site)

Rapports produits :
  seo/reports/ga4-report.md   — rapport décisionnel (Markdown)
  seo/reports/ga4-report.json — données brutes (JSON)
"""

import base64
import json
import os
import subprocess
import sys
import tempfile
import time
import urllib.request
import urllib.parse
import urllib.error
from datetime import datetime, timedelta
from pathlib import Path

PROPERTY_ID = "538539081"
CREDS_PATH  = Path.home() / ".config/monte-cristo/ga4-credentials.json"
SCRIPT_DIR  = Path(__file__).parent
REPORTS_DIR = SCRIPT_DIR.parent / "reports"
API_BASE    = f"https://analyticsdata.googleapis.com/v1beta/properties/{PROPERTY_ID}"

# ── Auth — JWT signé RS256 via openssl ────────────────────────────────────────

def load_credentials():
    if not CREDS_PATH.exists():
        print(f"❌  Credentials introuvables : {CREDS_PATH}")
        sys.exit(1)
    return json.loads(CREDS_PATH.read_text(encoding="utf-8"))


def _b64(data: str) -> str:
    return base64.urlsafe_b64encode(data.encode()).rstrip(b"=").decode()


def _b64_bytes(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).rstrip(b"=").decode()


def make_jwt(creds: dict) -> str:
    header  = _b64(json.dumps({"alg": "RS256", "typ": "JWT"}))
    now     = int(time.time())
    payload = _b64(json.dumps({
        "iss":   creds["client_email"],
        "scope": "https://www.googleapis.com/auth/analytics.readonly",
        "aud":   "https://oauth2.googleapis.com/token",
        "iat":   now,
        "exp":   now + 3600,
    }))
    signing_input = f"{header}.{payload}"

    with tempfile.NamedTemporaryFile(mode="w", suffix=".pem", delete=False) as f:
        f.write(creds["private_key"])
        key_path = f.name

    try:
        result = subprocess.run(
            ["openssl", "dgst", "-sha256", "-sign", key_path],
            input=signing_input.encode(),
            capture_output=True,
        )
        if result.returncode != 0:
            raise RuntimeError(f"openssl: {result.stderr.decode().strip()}")
        signature = _b64_bytes(result.stdout)
    finally:
        os.unlink(key_path)

    return f"{signing_input}.{signature}"


def get_access_token(creds: dict) -> str:
    jwt  = make_jwt(creds)
    body = urllib.parse.urlencode({
        "grant_type": "urn:ietf:params:oauth:grant-type:jwt-bearer",
        "assertion":  jwt,
    }).encode()
    req = urllib.request.Request(
        "https://oauth2.googleapis.com/token",
        data=body,
        headers={"Content-Type": "application/x-www-form-urlencoded"},
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=15) as resp:
        return json.loads(resp.read())["access_token"]


# ── Requête GA4 Data API ──────────────────────────────────────────────────────

def ga4_report(token: str, body: dict):
    req = urllib.request.Request(
        f"{API_BASE}:runReport",
        data=json.dumps(body).encode(),
        headers={
            "Authorization": f"Bearer {token}",
            "Content-Type":  "application/json",
        },
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            return json.loads(resp.read())
    except urllib.error.HTTPError as e:
        print(f"HTTP {e.code}: {e.read().decode()[:200]}")
        return None


def date_range(days: int = 30) -> dict:
    end   = datetime.now().date()
    start = end - timedelta(days=days - 1)
    return {"startDate": str(start), "endDate": str(end)}


def parse_rows(result):
    if not result or "rows" not in result:
        return []
    dim_hdrs = [h["name"] for h in result.get("dimensionHeaders", [])]
    met_hdrs = [h["name"] for h in result.get("metricHeaders",   [])]
    rows = []
    for row in result["rows"]:
        r = {}
        for i, d in enumerate(row.get("dimensionValues", [])):
            r[dim_hdrs[i]] = d["value"]
        for i, m in enumerate(row.get("metricValues", [])):
            r[met_hdrs[i]] = m["value"]
        rows.append(r)
    return rows


# ── Formatage Markdown ────────────────────────────────────────────────────────

def fmt_table(headers: list, rows: list, keys: list, max_rows: int = 15) -> str:
    if not rows:
        return "*Aucune donnée disponible.*"
    sep   = "|" + "|".join(["---"] * len(headers)) + "|"
    lines = ["| " + " | ".join(headers) + " |", sep]
    for row in rows[:max_rows]:
        cells = [str(row.get(k, "—")) for k in keys]
        lines.append("| " + " | ".join(cells) + " |")
    return "\n".join(lines)


def fmt_pct(value) -> str:
    return f"{round(float(value) * 100, 1)} %"


def fmt_duration(seconds) -> str:
    total = int(float(seconds))
    m, s  = divmod(total, 60)
    return f"{m}m {s:02d}s"


# ── Sections du rapport ───────────────────────────────────────────────────────

def section_overview(token: str, dr: dict):
    r = ga4_report(token, {
        "dateRanges": [dr],
        "metrics": [
            {"name": "sessions"},
            {"name": "totalUsers"},
            {"name": "newUsers"},
            {"name": "screenPageViews"},
            {"name": "bounceRate"},
            {"name": "averageSessionDuration"},
        ],
    })
    rows = parse_rows(r)
    if not rows:
        return "Vue d'ensemble", "*Aucune donnée.*", {}
    row  = rows[0]
    data = {
        "sessions":               row.get("sessions", "0"),
        "totalUsers":             row.get("totalUsers", "0"),
        "newUsers":               row.get("newUsers", "0"),
        "screenPageViews":        row.get("screenPageViews", "0"),
        "bounceRate":             fmt_pct(row.get("bounceRate", 0)),
        "averageSessionDuration": fmt_duration(row.get("averageSessionDuration", 0)),
    }
    content = (
        "| Indicateur | Valeur |\n|---|---|\n"
        f"| Sessions | **{data['sessions']}** |\n"
        f"| Utilisateurs | **{data['totalUsers']}** |\n"
        f"| Nouveaux utilisateurs | **{data['newUsers']}** |\n"
        f"| Pages vues | **{data['screenPageViews']}** |\n"
        f"| Taux de rebond | **{data['bounceRate']}** |\n"
        f"| Durée moyenne de session | **{data['averageSessionDuration']}** |"
    )
    return "Vue d'ensemble", content, data


def section_top_pages(token: str, dr: dict):
    r = ga4_report(token, {
        "dateRanges": [dr],
        "dimensions": [{"name": "pagePath"}],
        "metrics":    [
            {"name": "sessions"},
            {"name": "screenPageViews"},
            {"name": "bounceRate"},
            {"name": "averageSessionDuration"},
        ],
        "orderBys": [{"metric": {"metricName": "sessions"}, "desc": True}],
        "limit": 15,
    })
    rows = parse_rows(r)
    for row in rows:
        row["bounceRate"]             = fmt_pct(row.get("bounceRate", 0))
        row["averageSessionDuration"] = fmt_duration(row.get("averageSessionDuration", 0))
    content = fmt_table(
        ["Page", "Sessions", "Vues", "Rebond", "Durée"],
        rows,
        ["pagePath", "sessions", "screenPageViews", "bounceRate", "averageSessionDuration"],
    )
    return "Top pages", content, rows


def section_acquisition(token: str, dr: dict):
    r = ga4_report(token, {
        "dateRanges": [dr],
        "dimensions": [{"name": "sessionDefaultChannelGroup"}],
        "metrics":    [
            {"name": "sessions"},
            {"name": "totalUsers"},
            {"name": "bounceRate"},
        ],
        "orderBys": [{"metric": {"metricName": "sessions"}, "desc": True}],
    })
    rows = parse_rows(r)
    for row in rows:
        row["bounceRate"] = fmt_pct(row.get("bounceRate", 0))
    content = fmt_table(
        ["Canal", "Sessions", "Utilisateurs", "Rebond"],
        rows,
        ["sessionDefaultChannelGroup", "sessions", "totalUsers", "bounceRate"],
    )
    return "Canaux d'acquisition", content, rows


def section_conversions(token: str, dr: dict):
    r = ga4_report(token, {
        "dateRanges": [dr],
        "dimensions": [{"name": "eventName"}],
        "metrics":    [{"name": "eventCount"}, {"name": "totalUsers"}],
        "dimensionFilter": {
            "filter": {
                "fieldName": "eventName",
                "inListFilter": {
                    "values": [
                        "booking_open",
                        "cta_click",
                        "contact_click",
                        "session_start",
                        "first_visit",
                    ]
                },
            }
        },
        "orderBys": [{"metric": {"metricName": "eventCount"}, "desc": True}],
    })
    rows = parse_rows(r)
    if not rows:
        content = (
            "*Aucun événement de conversion enregistré pour la période.*\n\n"
            "> `booking_open`, `cta_click`, `contact_click` seront visibles "
            "après déploiement de `tracking.js`."
        )
    else:
        content = fmt_table(
            ["Événement", "Déclenchements", "Utilisateurs"],
            rows,
            ["eventName", "eventCount", "totalUsers"],
        )
    return "Événements de conversion", content, rows


def section_devices(token: str, dr: dict):
    r = ga4_report(token, {
        "dateRanges": [dr],
        "dimensions": [{"name": "deviceCategory"}],
        "metrics":    [
            {"name": "sessions"},
            {"name": "totalUsers"},
            {"name": "bounceRate"},
        ],
        "orderBys": [{"metric": {"metricName": "sessions"}, "desc": True}],
    })
    rows = parse_rows(r)
    for row in rows:
        row["bounceRate"] = fmt_pct(row.get("bounceRate", 0))
    content = fmt_table(
        ["Appareil", "Sessions", "Utilisateurs", "Rebond"],
        rows,
        ["deviceCategory", "sessions", "totalUsers", "bounceRate"],
    )
    note = (
        "\n\n> Mobile = signal de ranking Google. "
        "Un rebond mobile élevé justifie d'optimiser en priorité l'expérience mobile."
    )
    return "Répartition par appareil", content + note, rows


# ── Rapport Markdown complet ──────────────────────────────────────────────────

def build_report(sections_data: list, generated_at: str) -> str:
    lines = []
    a = lines.append
    a("# Rapport GA4 — Monte-Cristo Patrimoine")
    a(f"*Généré le {generated_at} — 30 derniers jours — Propriété {PROPERTY_ID}*\n")
    a("> Ce rapport est destiné à la prise de décision : quelles pages optimiser,")
    a("> d'où vient le trafic, quelles actions mènent à un rendez-vous.\n")
    for title, content, _ in sections_data:
        a(f"## {title}\n")
        a(content)
        a("")
    a("---")
    a("*Rapport généré par `seo/scripts/ga4-report.py`*")
    return "\n".join(lines)


# ── Point d'entrée ────────────────────────────────────────────────────────────

SECTIONS = [
    ("Vue d'ensemble",           section_overview),
    ("Top pages",                section_top_pages),
    ("Canaux d'acquisition",     section_acquisition),
    ("Événements de conversion", section_conversions),
    ("Répartition par appareil", section_devices),
]


def main():
    print("📊 Rapport GA4 — Monte-Cristo Patrimoine\n")

    creds = load_credentials()
    print("   🔑 Authentification…", end=" ", flush=True)
    try:
        token = get_access_token(creds)
        print("OK")
    except Exception as e:
        print(f"ERREUR\n   {e}")
        sys.exit(1)

    dr           = date_range(30)
    sections_data = []

    for label, fn in SECTIONS:
        print(f"   ▶ {label}…", end=" ", flush=True)
        try:
            title, content, raw = fn(token, dr)
            sections_data.append((title, content, raw))
            print("OK")
        except Exception as e:
            sections_data.append((label, f"*Erreur : {e}*", {}))
            print(f"ERREUR — {e}")

    generated_at = datetime.now().strftime("%d/%m/%Y à %H:%M")
    REPORTS_DIR.mkdir(parents=True, exist_ok=True)

    md_path   = REPORTS_DIR / "ga4-report.md"
    json_path = REPORTS_DIR / "ga4-report.json"

    md_path.write_text(build_report(sections_data, generated_at), encoding="utf-8")
    json_path.write_text(json.dumps({
        "generated_at": generated_at,
        "property_id":  PROPERTY_ID,
        "period_days":  30,
        "sections":     {t: r for t, _, r in sections_data},
    }, ensure_ascii=False, indent=2), encoding="utf-8")

    print(f"\n📄 Rapports :")
    print(f"   {md_path}")
    print(f"   {json_path}")


if __name__ == "__main__":
    main()
