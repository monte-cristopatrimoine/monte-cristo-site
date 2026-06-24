Lance le contrôle des métadonnées du site Monte-Cristo Patrimoine.

Étapes à suivre dans l'ordre :

1. Utilise le Bash tool pour lancer : `python3 seo/scripts/check-meta.py`
   depuis le répertoire : `/Users/MCGP/Library/CloudStorage/OneDrive-Bibliothèquespartagées-MCGP/Monte-Cristo Patrimoine - Documents/COMMUNICATION/Site Web/Claude/Site internet de travail`

2. Lis le fichier `seo/reports/meta-check.md` généré.

3. Résume les résultats :
   - Problèmes de longueur (title, description, og:title, og:description) avec les valeurs actuelles
   - Doublons détectés entre pages (même title ou description sur plusieurs pages)
   - Incohérences entre title / og:title / twitter:title
   - Balises absentes

4. Pour chaque problème, indique :
   - La page concernée
   - La valeur actuelle et sa longueur
   - La valeur cible recommandée (fourchette idéale)
   - Une suggestion concrète de correction

5. Si des doublons sont détectés, explique pourquoi c'est problématique pour le référencement et propose des variantes distinctes.

6. Propose les corrections sous forme de liste, mais ne modifie aucun fichier sans validation explicite.

Ne modifie aucun fichier HTML sans validation explicite de l'utilisateur.
