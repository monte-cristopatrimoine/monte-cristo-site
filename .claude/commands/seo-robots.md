Vérifie le fichier robots.txt du site Monte-Cristo Patrimoine.

Étapes à suivre dans l'ordre :

1. Utilise le Bash tool pour lancer : `python3 seo/scripts/check-robots.py`
   depuis le répertoire : `/Users/MCGP/Library/CloudStorage/OneDrive-Bibliothèquespartagées-MCGP/Monte-Cristo Patrimoine - Documents/COMMUNICATION/Site Web/Claude/Site internet de travail`

2. Lis le fichier `seo/reports/robots-check.md` généré.

3. Résume les résultats en termes simples :
   - Le fichier robots.txt existe-t-il ?
   - Le sitemap est-il correctement déclaré ?
   - Des règles inutiles ou dangereuses sont-elles présentes ?
   - Des pages importantes sont-elles accidentellement bloquées ?

4. Si le rapport propose une version propre du robots.txt :
   - Affiche côte à côte la version actuelle et la version proposée
   - Explique chaque différence en termes simples
   - Demande validation avant toute modification

5. Ne modifie jamais robots.txt sans validation explicite de l'utilisateur.
