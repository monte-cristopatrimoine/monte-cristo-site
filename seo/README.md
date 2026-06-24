# Outils SEO — Monte-Cristo Patrimoine

Outils d'audit et de contrôle SEO pour le site statique monte-cristo.net.
Aucune dépendance externe — Python 3 uniquement (préinstallé sur Mac).

---

## Structure

```
seo/
├── scripts/
│   └── audit.py         ← script d'audit SEO complet
└── reports/
    ├── site-audit.json  ← rapport machine (données brutes)
    └── site-audit.md    ← rapport lisible (humain)
```

---

## Utilisation

Depuis la racine du site (dossier "Site internet de travail") :

```bash
python3 seo/scripts/audit.py
```

Le script analyse toutes les pages HTML, croise avec le sitemap.xml,
et génère les deux rapports dans `seo/reports/`.

---

## Ce que l'audit vérifie

Pour chaque page de production :

| Élément | Niveaux possibles |
|---------|-------------------|
| Balise `<title>` | Critique si absente, Important si trop longue |
| Meta description | Critique si absente |
| Balise canonical | Critique si absente |
| Balise H1 | Critique si absente, Important si plusieurs |
| Présence dans sitemap | Important si absente |
| og:title / og:description | Important si absents |
| Schema.org / JSON-LD | Amélioration |
| Balises H2 | Amélioration |
| Images sans `alt` | Amélioration |

Pages techniques (`404.html`) et pages de travail (`mockup-contenu.html`)
sont auditées séparément avec des règles adaptées.

---

## Niveaux de priorité

- 🔴 **Critique** — à corriger immédiatement (impact direct sur l'indexation)
- 🟠 **Important** — à corriger prochainement (impact significatif)
- 🟡 **Amélioration** — utile mais non urgent
- ⚪ **Mineur** — cosmétique ou très faible impact

---

## Outils à venir

- `seo/scripts/check-meta.py` — contrôle fin des métadonnées
- `seo/scripts/generate-sitemap.py` — génération automatique du sitemap
- `seo/scripts/check-robots.py` — contrôle du robots.txt
- `seo/scripts/pre-publish.py` — checklist avant déploiement
