# Déploiement Monte-Cristo Patrimoine — Procédure

Ce dossier contient le **site complet, prêt à uploader sur OVH**. Tout est auto-suffisant.

## Contenu du dossier

```
deploy/
├── .htaccess                      ← redirections SEO + URLs propres + HTTPS
├── index.html                     ← page d'accueil
├── le-cabinet.html
├── particuliers.html
├── entreprises.html
├── blog.html
├── article-cgp-independant.html
├── mentions-legales.html
├── colors_and_type.css
├── fonts/                         ← 14 fichiers Creato Display
│   └── *.otf + fonts.css
└── assets/
    ├── logo-beige.png
    ├── logo-vert.png
    ├── partners/                  ← 12 logos partenaires
    └── team/                      ← 2 photos fondateurs
```

## Étapes de bascule

### 1. Sauvegarder WordPress (5 min)

Dans votre **Espace Client OVH** :
- **Hébergement** → votre hébergement → **FTP-SSH**
- Faites une sauvegarde / snapshot complet du dossier `www/` (ou `public_html/`)
- Faites un dump SQL de la base de données WordPress (au cas où)

### 2. Préparer le dossier pour la signature email (5 min)

Vos signatures Outlook existantes pointent vers 2 images stockées dans `wp-content/uploads/2025/08/` :
- `Capture-decran-2025-08-27-a-11.58.09.png` (le logo MCP)
- `Prendre-rendez-vous.png` (le bouton "Prendre rendez-vous")

Pour ne pas casser ces images dans les emails déjà envoyés :

1. Créez le dossier `wp-content/uploads/2025/08/` à la racine de votre nouveau site
2. Uploadez les 2 fichiers PNG dedans (ils existent encore sur votre WordPress actuel)

### 3. Bascule du site (15 min)

Via FTP OVH :

1. **Renommez** le dossier `www/` actuel en `wordpress-backup/` (au cas où il faudrait revenir en arrière)
2. **Créez un nouveau dossier vide** nommé `www/`
3. **Uploadez** tout le contenu de ce dossier `deploy/` dans le nouveau `www/`

⚠️ **Important** : activez l'affichage des fichiers cachés dans votre client FTP — sinon le fichier `.htaccess` (qui commence par un point) ne sera pas uploadé. Sur FileZilla : *Serveur → Forcer l'affichage des fichiers cachés*.

### 4. Vérifier (10 min)

Testez ces URLs depuis votre navigateur (en mode privé, pour éviter le cache) :

- `https://monte-cristo.net` → la nouvelle page d'accueil ✓
- `https://monte-cristo.net/le-cabinet` → page Le cabinet ✓
- `https://monte-cristo.net/about/` → doit **rediriger** vers `/le-cabinet` ✓
- `https://monte-cristo.net/optimisation-fiscale/` → doit **rediriger** vers `/particuliers` ✓
- `https://monte-cristo.net/blog/` → page Blog ✓

### 5. Google Search Console (le lendemain)

- Connectez-vous à [search.google.com/search-console](https://search.google.com/search-console)
- Sélectionnez votre propriété `monte-cristo.net`
- Surveillez l'onglet **Couverture** pendant 2-3 semaines pour détecter d'éventuelles 404
- Si des 404 apparaissent, dites-les moi : on rajoute des redirections dans `.htaccess`

## Ce qui est protégé / pas touché

- ✅ **Emails @monte-cristo.net** : on ne touche pas à la zone DNS ni aux enregistrements MX. Vos emails continuent de fonctionner.
- ✅ **Signatures email existantes** : si vous avez fait l'étape 2, les images des emails déjà envoyés s'affichent toujours.
- ✅ **Base de données WordPress** : reste en place sur OVH (peut être supprimée plus tard si vous êtes sûr de ne plus revenir à WP).
- ✅ **15 anciennes URLs SEO** redirigées en 301 — Google transfère le poids SEO automatiquement.

## En cas de problème

Pour revenir à WordPress :
1. Renommez `www/` (nouveau site) en `static-backup/`
2. Renommez `wordpress-backup/` en `www/`
3. Tout revient comme avant.
