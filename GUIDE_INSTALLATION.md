# Guide d'installation — Amah Agent
*Version 1.4.1 — Juin 2026*

---

## Ce dont vous avez besoin

- Un PC Windows 10 ou Windows 11
- Une connexion internet
- Un microphone (optionnel, pour l'interface vocale)
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
> **Conseil :** Créez jusqu'à 3 comptes gratuits pour tripler votre quota quotidien.

---

## Étape 3 — Premier lancement

Double-cliquez sur `Amah Agent.exe`.

Un écran de configuration s'ouvre automatiquement :

```
┌────────────────────────────────────────────┐
│   THE AMAH — PREMIER LANCEMENT  v1.4.1    │
│   Configure tes accès pour démarrer       │
├────────────────────────────────────────────┤
│                                            │
│  Clé Groq n1 (obligatoire)                │
│  [______________________________________]  │
│                                            │
│  Clé Groq n2 (optionnel — +quota)         │
│  [______________________________________]  │
│                                            │
│  Clé Groq n3 (optionnel — +quota)         │
│  [______________________________________]  │
│                                            │
│  Clé de licence (obligatoire)             │
│  [______________________________________]  │
│                                            │
│  Adresse Gmail (optionnel)                │
│  [______________________________________]  │
│                                            │
│           [ Démarrer Amah ]               │
└────────────────────────────────────────────┘
```

1. **Collez votre clé Groq** dans le premier champ
2. **Entrez votre clé de licence** (fournie par contact.amah.officiel@gmail.com)
3. Les champs Gmail sont optionnels (voir Étape 4)
4. Cliquez **"Démarrer Amah"**

Amah démarre. La configuration est sauvegardée — vous n'aurez plus à la refaire.

---

## Étape 4 — Configurer les emails Gmail (optionnel)

### 4a — Activer la validation en 2 étapes
1. Allez sur **myaccount.google.com**
2. Sécurité → **Validation en 2 étapes** → Activez-la

### 4b — Créer un mot de passe d'application
1. Toujours dans Sécurité → **Mots de passe des applications**
2. Tapez `Amah` dans le champ et cliquez **Créer**
3. Copiez le code à 16 caractères affiché

### 4c — Activer IMAP dans Gmail
1. Ouvrez **Gmail** → ⚙️ Paramètres → **Voir tous les paramètres**
2. Onglet **"Transfert et POP/IMAP"**
3. Activez **"Activer IMAP"** → Enregistrer

---

## Utilisation quotidienne

Double-cliquez sur `Amah Agent.exe` pour lancer Amah.

### Exemples de commandes (texte)
- *"Lis mes 5 derniers emails"*
- *"Crée un document Word sur notre réunion"*
- *"Cherche les dernières nouvelles sur l'IA"*
- *"Règle le volume à 70%"*
- *"Lance une vidéo YouTube sur la guitare"*
- *"Cherche un vol Paris → New York pour le 15 juillet"*
- *"Qu'est-ce que tu vois sur mon écran ?"*

### Interface vocale
Cliquez sur le bouton **[◎]** dans la barre de saisie :
- Une fenêtre animée s'ouvre (style HUD)
- Parlez naturellement (8 secondes max)
- Amah transcrit, répond et parle à voix haute

---

## Problèmes fréquents

| Problème | Solution |
|----------|----------|
| Windows bloque le .exe | Clic droit → "Exécuter quand même" |
| "Clé Groq invalide" | Vérifiez que vous avez bien copié toute la clé |
| "Erreur Gmail" | Vérifiez que IMAP est activé dans Gmail |
| Micro non détecté | Vérifiez que votre micro est branché et activé dans Windows |
| Volume/luminosité ne change pas | Normal sur certains écrans externes (WMI non supporté) |
| L'écran de config réapparaît | Le fichier .env a été supprimé, reconfigurez |

---

## Support

Contact : **contact.amah.officiel@gmail.com**
