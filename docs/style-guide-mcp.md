# Style Guide — Monte-Cristo Patrimoine

Version 1.0 · 2026-06-26

---

## Stack CSS

| Fichier | Rôle | Charger dans `<head>` |
|---|---|---|
| `/colors_and_type.css` | Tokens CSS (`:root`), @font-face Creato Display, typographie de base (body, h1-h4, .eyebrow, .lead…) | 1er |
| `/assets/css/mcp-design-system.css` | Composants réutilisables (header, nav, boutons, hero system, trust strip, footer) | 2e |
| `<style>` inline | CSS spécifique à la page | 3e |

Ordre obligatoire : `colors_and_type.css` → `mcp-design-system.css` → inline.

---

## Tokens couleur

| Token | Valeur | Usage |
|---|---|---|
| `--mcp-green` | `#346848` | Vert principal (marque) |
| `--mcp-green-700` | `#244F36` | Vert foncé (hover, accents) |
| `--mcp-green-deep` | `#1B6A45` | Vert profond (liens hover) |
| `--mcp-green-100` | `#DDE7DF` | Vert très clair (icônes bg) |
| `--mcp-orange` | `#E67E22` | Orange accent (CTA principal) |
| `--mcp-orange-700` | `#B66518` | Orange foncé (hover CTA) |
| `--mcp-beige` | `#FDFAF3` | Fond principal |
| `--mcp-beige-200` | `#F4EFE0` | Fond élevé (cartes) |
| `--mcp-beige-300` | `#E8E1CC` | Bordures |
| `--mcp-ink` | `#16110A` | Texte principal |
| `--mcp-ink-500` | `#6B6359` | Texte secondaire (corps, légendes) |

---

## Boutons

```html
<!-- Principal -->
<a href="…" class="btn btn-primary">Découvrir</a>

<!-- Accent (CTA rendez-vous) -->
<a href="…" class="btn btn-accent">Prendre rendez-vous</a>

<!-- Secondaire (contour) -->
<a href="…" class="btn btn-secondary">En savoir plus</a>

<!-- Sur fond vert -->
<a href="…" class="btn btn-on-green">Voir les articles</a>
```

---

## Composants section

```html
<!-- Container standard -->
<div class="container"> … </div>

<!-- En-tête de section (2 colonnes) -->
<div class="mcp-section-head">
  <div>
    <div class="eyebrow">Libellé catégorie</div>
    <h2>Titre de section</h2>
  </div>
  <p>Accroche complémentaire, max 480px.</p>
</div>
```

---

## Hero System

### Règle fondamentale — `hero-demeure.webp`

> **`/assets/hero-demeure.webp` est exclusif à `.mcp-hero-signature` (home uniquement).**
> Ne jamais utiliser cette image comme fond sur une page intérieure.
> Ne jamais ajouter `background-image: url('/assets/hero-demeure.webp')` hors de `.mcp-hero-signature`.

### Tableau des types de hero par page

| Type | Classe | Pages | Image autorisée |
|---|---|---|---|
| Signature | `.mcp-hero-signature` | Home (`/`) uniquement | `hero-demeure.webp` (exclusif) |
| Intérieur – portrait | `.mcp-hero-interior.mcp-hero-interior--portrait` | `/le-cabinet` | Portrait équipe (jamais demeure) |
| Intérieur – service | `.mcp-hero-interior.mcp-hero-interior--service` | `/particuliers`, `/entreprises` | Aucune image lourde |
| Intérieur – minimal | `.mcp-hero-interior.mcp-hero-interior--minimal` | Pages utilitaires | Aucune |
| Éditorial | `.mcp-hero-editorial` | `/blog`, articles | Image éditoriale (jamais demeure) |
| SEO | `.mcp-hero-seo` | `/conseiller-gestion-patrimoine-independant`, `/honoraires-frais-caches` | Fond clair, texte en avant |

### Usage HTML

```html
<!-- Home uniquement -->
<section class="mcp-hero-signature">
  <div class="container hero-grid">
    …
  </div>
</section>

<!-- Page intérieure (ex. le-cabinet) -->
<section class="mcp-hero-interior mcp-hero-interior--portrait">
  <div class="container">
    <div class="mcp-hero-inner">
      <div>…texte…</div>
      <div>…photo équipe…</div>
    </div>
  </div>
</section>

<!-- Article de blog -->
<section class="mcp-hero-editorial">
  <div class="container">
    <div class="eyebrow">Catégorie</div>
    <h1>Titre de l'article</h1>
  </div>
</section>

<!-- Page SEO (texte-first) -->
<section class="mcp-hero-seo">
  <div class="container">
    <div class="eyebrow">Catégorie</div>
    <h1>Titre optimisé</h1>
    <p class="lead">…</p>
  </div>
</section>
```

---

## Trust strip (partenaires)

```html
<div class="trust">
  <div class="trust-inner">
    <div class="trust-label">Partenaires</div>
    <div class="trust-logos">
      <div class="cell"><img src="/assets/partners/nom.webp" alt="Nom partenaire"/></div>
      …
    </div>
  </div>
</div>
```

---

## CTA Rendez-vous — règle header

Le header contient deux éléments CTA :
- `.nav-rdv` → bouton dans `<nav>` (mobile uniquement, menu ouvert)
- `.btn.btn-accent` direct dans `.header-inner` → bouton desktop

**Règles CSS obligatoires dans chaque page** (gardées inline pour le guard `check-header-css.py`) :

```css
/* Masquage global du CTA mobile */
.nav-rdv,
.nav .nav-rdv { display: none !important; }

/* Mobile : masquer le CTA desktop, afficher le CTA mobile quand menu ouvert */
@media (max-width: 760px) {
  .header-inner > .btn { display: none !important; }
  .nav.open .nav-rdv { display: inline-flex !important; }
}
```

**Résultat attendu :**
- Desktop (> 760px) : un seul bouton visible (`.header-inner > .btn`)
- Mobile menu fermé : aucun CTA visible
- Mobile menu ouvert : un seul CTA visible (`.nav-rdv` dans `.nav.open`)

---

## Formulations éditoriales

### Approuvées

- « Cabinet indépendant »
- « Honoraires transparents »
- « Architecture ouverte »
- « Moins de 5 % des CGP en France »
- « Premier échange de 45 minutes, sans engagement »
- « En présentiel ou à distance partout en France »
- « Nous ne dépendons pas de la gamme d'un seul établissement »

### Interdites (réglementaire / compliance)

- `sans commission` — interdit
- `zéro commission` — interdit
- `zéro frais` — interdit
- `100 % indépendant` — interdit
- `aucun conflit d'intérêts` — interdit
- `meilleurs produits` — interdit
- `garanti` — interdit
- `fictif`, `illustratif`, `placeholder`, `simulation`, `à remplacer` — interdit en contenu visible

---

## Images équipe

| Fichier | Usage autorisé |
|---|---|
| `/assets/team/kevin-portrait-v2.webp` | Section cabinet (home), page le-cabinet, byline articles |
| `/assets/team/luc-portrait-v2.webp` | Section cabinet (home), page le-cabinet |
| `/assets/hero-demeure.webp` | **Home uniquement** — `.mcp-hero-signature` |

---

## Préfixe des composants

Tout nouveau composant réutilisable doit être préfixé `mcp-` :

- `.mcp-section-head` ✓
- `.mcp-hero-signature` ✓
- `.mcp-hero-interior` ✓
- `.mcp-hero-editorial` ✓
- `.mcp-hero-seo` ✓

Les classes non préfixées existantes (`.header`, `.nav`, `.btn`, `.footer-inner`…) sont maintenues pour compatibilité avec les partials et les 12 autres pages non encore migrées.
