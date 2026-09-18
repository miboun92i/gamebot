# GameBot Telegram

Bot de mini-jeux et d'activité pour groupes Telegram.

## V1
- Mini-jeu automatique toutes les 2 heures
- Anagrammes, calcul mental et mots à recopier
- XP d'activité avec anti-farm simple
- Objectifs quotidiens
- /profil, /missions, /classement
- Classements jour / semaine / mois / général
- PostgreSQL, compatible Railway

## Installation
1. Créer le bot via BotFather et récupérer BOT_TOKEN.
2. Désactiver Privacy Mode dans BotFather pour que le bot voie les messages du groupe.
3. Ajouter PostgreSQL sur Railway.
4. Définir BOT_TOKEN et DATABASE_URL.
5. Déployer ce repo.

Les tables sont créées automatiquement au démarrage.
