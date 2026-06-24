Lance la checklist complète pré-publication du site Monte-Cristo Patrimoine.

Cette commande exécute tous les outils SEO en séquence et donne un verdict final.

Étapes à suivre dans l'ordre :

1. Utilise le Bash tool pour lancer : `python3 seo/scripts/pre-publish.py`
   depuis le répertoire : `/Users/MCGP/Library/CloudStorage/OneDrive-Bibliothèquespartagées-MCGP/Monte-Cristo Patrimoine - Documents/COMMUNICATION/Site Web/Claude/Site internet de travail`

   Ce script lance automatiquement : audit.py · check-meta.py · generate-sitemap.py · check-robots.py

2. Lis le fichier `seo/reports/pre-publish-report.md` généré.

3. Affiche le verdict en premier, clairement :
   - ✅ PUBLIABLE — aucun problème bloquant
   - ⚠️ PUBLIABLE avec corrections mineures recommandées
   - ❌ À CORRIGER AVANT PUBLICATION

4. Présente le tableau consolidé (critiques / importants / améliorations par outil).

5. Si le verdict est ❌ :
   - Liste les problèmes bloquants page par page
   - Propose les corrections dans l'ordre de priorité
   - Ne modifie rien sans validation explicite

6. Si le verdict est ⚠️ :
   - Confirme que le site est déployable
   - Liste les améliorations disponibles pour plus tard
   - Demande si l'utilisateur veut les traiter maintenant ou déployer

7. Si le verdict est ✅ :
   - Confirme que tout est en ordre
   - Rappelle la commande git push pour déployer si le site est sur GitHub Pages ou similaire

Ne modifie aucun fichier HTML, sitemap, robots.txt ou script Python sans validation explicite.
