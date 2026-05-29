# Guide d'installation — Amah Agent
*Version 1.0 — Mai 2026*

---

## Ce dont vous avez besoin

- Un PC Windows 10 ou Windows 11
- Une connexion internet
- 5 minutes

---

## Étape 1 — Télécharger Amah Agent

Téléchargez le fichier `Amah Agent.exe` fourni par votre prestataire.
Placez-le dans un dossier de votre choix, par exemple :

```
C:\Amah Agent\
    └── Amah Agent.exe
```

> Ne le placez pas dans un dossier système (Program Files, Windows, etc.)

---

## Étape 2 — Obtenir votre clé Groq (gratuit)

Amah utilise Groq pour son intelligence artificielle. C'est entièrement gratuit.

1. Allez sur **console.groq.com**
2. Créez un compte gratuit (ou connectez-vous)
3. Cliquez sur **"API Keys"** dans le menu gauche
4. Cliquez sur **"Create API Key"**
5. Donnez-lui un nom (ex: `Amah`) et copiez la clé générée

> La clé ressemble à : `gsk_xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx`
> Conservez-la, vous en aurez besoin à l'étape suivante.

---

## Étape 3 — Premier lancement

Double-cliquez sur `Amah Agent.exe`.

Un écran de configuration s'ouvre automatiquement :

```
┌─────────────────────────────────────────┐
│   THE AMAH — PREMIER LANCEMENT         │
│   Configure tes accès pour démarrer    │
├─────────────────────────────────────────┤
│                                         │
│  Clé API Groq (obligatoire)             │
│  [___________________________________]  │
│                                         │
│  Adresse Gmail (optionnel)              │
│  [___________________________________]  │
│                                         │
│  Mot de passe Gmail (optionnel)         │
│  [___________________________________]  │
│                                         │
│           [ Démarrer Amah ]             │
└─────────────────────────────────────────┘
```

1. **Collez votre clé Groq** dans le premier champ
2. Les champs Gmail sont optionnels (voir Étape 4 si vous voulez les emails)
3. Cliquez **"Démarrer Amah"**

Amah démarre. La configuration est sauvegardée — vous n'aurez plus à la refaire.

---

## Étape 4 — Configurer les emails Gmail (optionnel)

Si vous souhaitez qu'Amah puisse lire et envoyer des emails depuis votre Gmail :

### 4a — Activer la validation en 2 étapes
1. Allez sur **myaccount.google.com**
2. Sécurité → **Validation en 2 étapes** → Activez-la

### 4b — Créer un mot de passe d'application
1. Toujours dans Sécurité → **Mots de passe des applications**
   *(ou allez directement sur myaccount.google.com/apppasswords)*
2. Tapez `Amah` dans le champ et cliquez **Créer**
3. Copiez le code à 16 caractères affiché

### 4c — Activer IMAP dans Gmail
1. Ouvrez **Gmail** → ⚙️ Paramètres → **Voir tous les paramètres**
2. Onglet **"Transfert et POP/IMAP"**
3. Activez **"Activer IMAP"** → Enregistrer

### 4d — Renseigner dans Amah
Au premier lancement (Étape 3), remplissez :
- **Adresse Gmail** : votre.adresse@gmail.com
- **Mot de passe d'application** : le code à 16 caractères

---

## Utilisation quotidienne

Double-cliquez sur `Amah Agent.exe` pour lancer Amah.

Exemples de commandes :
- *"Lis mes 5 derniers emails"*
- *"Crée un document Word avec le résumé de notre réunion"*
- *"Cherche les dernières nouvelles sur l'IA"*
- *"Montre-moi les fichiers de mon bureau"*
- *"Quelle est la taille de mon disque dur ?"*

---

## Problèmes fréquents

| Problème | Solution |
|----------|----------|
| Windows bloque le .exe | Clic droit → "Exécuter quand même" |
| "Clé Groq invalide" | Vérifiez que vous avez bien copié toute la clé |
| "Erreur Gmail" | Vérifiez que IMAP est activé dans Gmail |
| L'écran de config réapparaît | Le fichier .env a été supprimé, reconfigurez |

---

## Support

Contact : **contact.amah.officiel@gmail.com**
