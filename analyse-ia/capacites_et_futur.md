# Amah Agent — Capacités actuelles et évolutions futures
*Document de référence — 29/05/2026*

---

## PARTIE 1 — CE QUE L'AGENT PEUT FAIRE MAINTENANT

### 1.1 Gestion de fichiers et dossiers

Amah peut interagir directement avec le système de fichiers Windows.

**Ce qu'elle fait concrètement :**
- Lister le contenu de n'importe quel dossier (bureau, documents, téléchargements...)
- Classer automatiquement un dossier en créant des sous-dossiers par type (Images/, Vidéos/, Documents/, etc.)
- Chercher un fichier par nom ou extension dans tout un répertoire
- Déplacer ou renommer un fichier
- Créer un nouveau dossier
- Lire le contenu d'un fichier texte, CSV, JSON, Python...
- Donner des statistiques sur un dossier (taille totale, nombre de fichiers, types présents)

**Exemples de demandes :**
- "Organise mon bureau automatiquement"
- "Trouve tous les fichiers PDF dans mes téléchargements"
- "Lis le fichier rapport.txt sur mon bureau"
- "Quelle est la taille du dossier Projets ?"

---

### 1.2 Création de documents

Amah peut créer des documents Word, PDF et texte directement depuis la conversation.

**Ce qu'elle fait concrètement :**
- Créer un document Word (.docx) avec titre, contenu formaté et date
- Créer un fichier texte (.txt)
- Créer un document PDF avec mise en page propre
- Lire et extraire le contenu d'un document Word, PDF ou TXT existant

**Exemples de demandes :**
- "Crée un rapport Word sur notre réunion de ce matin"
- "Génère un PDF avec le résumé de ce projet"
- "Lis le contrat.pdf et dis-moi ce qu'il dit"
- "Crée un fichier texte avec ma liste de tâches"

---

### 1.3 Recherche sur internet

Amah peut chercher des informations en ligne et lire des pages web.

**Ce qu'elle fait concrètement :**
- Effectuer une recherche DuckDuckGo et retourner les résultats (titres, URLs, extraits)
- Ouvrir une URL et extraire tout le texte d'une page web
- Résumer une page web à la demande

**Exemples de demandes :**
- "Cherche les dernières actualités sur l'IA"
- "Quel est le prix de l'iPhone 16 ?"
- "Lis cet article et fais-m'en un résumé"
- "Cherche des informations sur Python 3.14"

---

### 1.4 Informations système Windows

Amah connaît l'état de ton PC en temps réel.

**Ce qu'elle fait concrètement :**
- Afficher l'utilisation de la RAM, du CPU, de l'espace disque
- Ouvrir un fichier ou un dossier avec le programme Windows par défaut
- Exécuter des commandes PowerShell sécurisées (les commandes dangereuses sont bloquées)

**Exemples de demandes :**
- "Combien de RAM il me reste ?"
- "Ouvre le dossier Projets"
- "Lance le fichier rapport.xlsx"
- "Quelle version de Windows j'ai ?"

---

### 1.5 Mémoire persistante

Amah se souvient entre les sessions — elle reprend la conversation là où elle s'est arrêtée.

**Ce qu'elle fait concrètement :**
- Recharger automatiquement les 20 derniers messages au démarrage (mémoire court terme)
- Mémoriser explicitement des informations importantes sur l'utilisateur (mémoire long terme)
- Rappeler les informations mémorisées à tout moment
- Supprimer une information mémorisée si elle est obsolète

**Catégories de mémoire :** préférence, tâche, info, projet, général

**Exemples de demandes :**
- "Mémorise que je préfère les PDF aux Word"
- "Retiens que mon client principal s'appelle Jean Dupont"
- "Qu'est-ce que tu sais de moi ?"
- "Oublie l'info sur Jean Dupont"

---

### 1.6 Email Gmail

Amah peut lire, envoyer et chercher des emails depuis le compte contact.amah.officiel@gmail.com.

**Ce qu'elle fait concrètement :**
- Lire les N derniers emails (expéditeur, sujet, date, extrait du contenu)
- Envoyer un email à n'importe quelle adresse
- Chercher des emails par expéditeur, sujet, mot-clé, état (lu/non lu...)

**Exemples de demandes :**
- "Lis mes 5 derniers emails"
- "Envoie un email à contact@client.com pour confirmer le rendez-vous de demain"
- "Cherche les emails de Google dans ma boîte"
- "Est-ce que j'ai des emails non lus de mon client ?"

---

### 1.7 Navigation web automatique

Amah peut contrôler Chrome de façon visible — l'utilisateur voit tout ce qu'elle fait.

**Ce qu'elle fait concrètement :**
- Ouvrir n'importe quelle URL dans Chrome
- Cliquer sur un élément de la page (bouton, lien, onglet...)
- Remplir un champ de formulaire (recherche, login, formulaire...)
- Capturer une capture d'écran du navigateur
- Lire et retourner tout le texte visible sur la page ouverte

**Exemples de demandes :**
- "Ouvre Gmail dans le navigateur"
- "Va sur le site météo et dis-moi le temps de demain à Paris"
- "Ouvre YouTube et cherche des tutoriels Python"
- "Prends une capture d'écran de ce que tu vois"

---

## PARTIE 2 — CE QU'ON PEUT LUI FAIRE FAIRE DANS LE FUTUR

### 2.1 Agenda Google Calendar ⭐ Priorité haute

**Ce que ça permettrait :**
- Voir les événements du calendrier (aujourd'hui, cette semaine...)
- Créer un nouveau rendez-vous directement depuis la conversation
- Modifier ou supprimer un événement existant
- Recevoir des rappels

**Exemples futurs :**
- "Qu'est-ce que j'ai de prévu demain ?"
- "Crée un rendez-vous vendredi à 14h avec Jean Dupont"
- "Décale mon rendez-vous de 30 minutes"

**Complexité :** Moyenne — nécessite Google Calendar API (OAuth2 ou Service Account)

---

### 2.2 Synthèse vocale — Amah parle ⭐ Priorité haute

**Ce que ça permettrait :**
- Amah lit ses réponses à voix haute via les haut-parleurs
- Mode "mains libres" — pas besoin de regarder l'écran
- Choix de la voix (française, ton, vitesse)

**Exemples futurs :**
- Amah annonce "Ton email a été envoyé" à voix haute
- Mode vocal pour les personnes qui ne peuvent pas taper

**Complexité :** Faible — bibliothèque `pyttsx3` ou `edge-tts` (gratuit, voix Microsoft)

---

### 2.3 Reconnaissance vocale — Parler à Amah

**Ce que ça permettrait :**
- Dicter ses demandes au lieu de taper
- Mode entièrement vocal
- Activation par mot-clé ("Amah, ...")

**Complexité :** Moyenne — bibliothèque `speech_recognition` + microphone
**Alternative rapide :** `whisper` d'OpenAI (très précis, gratuit en local)

---

### 2.4 Notifications Windows

**Ce que ça permettrait :**
- Amah envoie des notifications Windows (coin bas droite) pour des alertes
- Rappels automatiques (rendez-vous, tâches...)
- Alertes sur les emails importants

**Complexité :** Faible — bibliothèque `plyer` ou `win10toast`

---

### 2.5 Outil WhatsApp / Telegram

**Ce que ça permettrait :**
- Envoyer et recevoir des messages WhatsApp ou Telegram
- Répondre automatiquement à certains messages
- Alertes par message quand une tâche est terminée

**Complexité :** Moyenne (Telegram API gratuite) / Élevée (WhatsApp Business API payante)

---

### 2.6 Automatisation de tâches planifiées

**Ce que ça permettrait :**
- Programmer des tâches récurrentes ("chaque lundi matin, lis mes emails et fais un résumé")
- Rappels automatiques ("dans 2 heures, rappelle-moi d'appeler Jean")
- Nettoyage automatique de dossiers à intervalles réguliers

**Complexité :** Moyenne — utiliser le Planificateur de tâches Windows ou une boucle interne

---

### 2.7 Connexion à des bases de données

**Ce que ça permettrait :**
- Lire et écrire dans des bases de données MySQL, PostgreSQL, Excel...
- Générer des rapports automatiques depuis une base de données
- Analyser des données et faire des résumés

**Complexité :** Moyenne — bibliothèques `pymysql`, `psycopg2`, `openpyxl`

---

### 2.8 Intégration avec des logiciels métier

**Ce que ça permettrait :**
- Se connecter à des ERP, CRM, outils comptables via API
- Créer des devis, factures, bons de commande automatiquement
- Synchroniser avec Notion, Trello, Airtable...

**Complexité :** Variable selon le logiciel — la plupart ont des APIs REST

---

### 2.9 Génération d'images (IA)

**Ce que ça permettrait :**
- Créer des images, logos, illustrations depuis une description
- Utiliser Stable Diffusion en local ou DALL-E via API

**Complexité :** Élevée (local) / Faible (API payante OpenAI/Replicate)

---

### 2.10 Mode multi-utilisateurs

**Ce que ça permettrait :**
- Chaque utilisateur a son propre profil, ses préférences, sa mémoire
- Idéal pour les entreprises avec plusieurs employés
- Contrôle des accès par utilisateur

**Complexité :** Élevée — refonte de la base SQLite et du système d'authentification

---

### 2.11 Mise à jour automatique du .exe

**Ce que ça permettrait :**
- Amah vérifie si une nouvelle version est disponible au démarrage
- Télécharge et installe la mise à jour automatiquement
- Les clients ont toujours la dernière version sans intervention

**Complexité :** Moyenne — serveur de versions + téléchargement du nouveau .exe

---

### 2.12 Tableau de bord d'activité

**Ce que ça permettrait :**
- Une page d'accueil avec : emails du jour, calendrier, tâches en cours, météo...
- Résumé quotidien automatique envoyé chaque matin
- Vue d'ensemble de l'activité de l'agent

**Complexité :** Moyenne — extension de gui.py avec un onglet "Dashboard"

---

## RÉSUMÉ DES PRIORITÉS

| # | Évolution | Impact | Complexité | Recommandation |
|---|-----------|--------|------------|----------------|
| 1 | Synthèse vocale | ⭐⭐⭐ | Faible | À faire en priorité |
| 2 | Notifications Windows | ⭐⭐⭐ | Faible | À faire rapidement |
| 3 | Agenda Google Calendar | ⭐⭐⭐ | Moyenne | Très utile pour les pros |
| 4 | Automatisation planifiée | ⭐⭐⭐ | Moyenne | Fort potentiel commercial |
| 5 | Reconnaissance vocale | ⭐⭐ | Moyenne | Confort d'utilisation |
| 6 | WhatsApp / Telegram | ⭐⭐⭐ | Moyenne/Élevée | Très demandé |
| 7 | Base de données | ⭐⭐ | Moyenne | Niche entreprise |
| 8 | Mise à jour auto | ⭐⭐ | Moyenne | Important pour le commercial |
| 9 | Multi-utilisateurs | ⭐⭐ | Élevée | Version entreprise |
| 10 | Génération d'images | ⭐ | Élevée | Optionnel |
