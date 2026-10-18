# Guide d'installation — Amah Agent
*Version 1.5.2 — Octobre 2026*

---

## Ce dont vous avez besoin

- Un PC Windows 10 ou Windows 11
- Une connexion internet
- Environ 450 Mo d'espace disque (plus ~170 Mo pour le navigateur)
- Un microphone (optionnel, pour l'interface vocale)
- 5 minutes

---

## Étape 1 — Installer Amah Agent

1. Téléchargez le fichier `Amah-Agent-v1.5.2.zip` fourni par votre prestataire.
2. Faites un clic droit dessus → **Extraire tout…**, puis choisissez un dossier,
   par exemple `C:\` :

```
C:\Amah Agent\
    ├── Amah Agent.exe          ← le programme à lancer
    ├── _internal\              ← fichiers du programme (ne pas toucher)
    ├── installer_navigateur.bat
    └── GUIDE_INSTALLATION.md
```

> Gardez le dossier **entier** : `Amah Agent.exe` ne fonctionne pas seul, il a
> besoin du dossier `_internal` à côté de lui. Pour le lancer depuis le bureau,
> faites un clic droit sur `Amah Agent.exe` → **Envoyer vers** → **Bureau
> (créer un raccourci)**.
>
> Ne le placez pas dans un dossier système (Program Files, Windows, etc.).

### Installer le navigateur (une seule fois)

Les outils web d'Amah (ouvrir un site, remplir un formulaire…) utilisent leur
propre navigateur. Double-cliquez sur `installer_navigateur.bat` dans le
dossier et attendez la fin du téléchargement (~170 Mo). Sans cette étape, Amah
fonctionne, mais sans les outils de navigation.

---

## Étape 2 — Obtenir votre clé Groq (gratuit)

Amah utilise Groq pour son intelligence artificielle. C'est entièrement gratuit.

1. Allez sur **console.groq.com**
2. Créez un compte gratuit (ou connectez-vous)
3. Cliquez sur **"API Keys"** dans le menu gauche
4. Cliquez sur **"Create API Key"**
5. Donnez-lui un nom (ex: `Amah`) et copiez la clé générée

> La clé ressemble à : `gsk_xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx`  
> **Conseil :** une clé gratuite permet environ 40 demandes avec outils par jour.
> Créez jusqu'à 3 comptes Groq gratuits et renseignez les 3 clés pour tripler
> ce quota : Amah passe automatiquement à la clé suivante quand l'une est épuisée.

---

## Étape 3 — Premier lancement

Double-cliquez sur `Amah Agent.exe` dans le dossier `Amah Agent`.

Un écran de configuration s'ouvre automatiquement :

```
┌────────────────────────────────────────────┐
│   THE AMAH — PREMIER LANCEMENT  v1.5.2    │
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

Double-cliquez sur `Amah Agent.exe` (ou son raccourci sur le bureau) pour lancer Amah.

Quand Amah va faire une action importante (supprimer ou déplacer un fichier,
exécuter une commande, envoyer un email, couper le wifi…), une fenêtre vous
demande votre accord. Rien n'est fait tant que vous n'avez pas cliqué **Oui**.

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
| Windows bloque le .exe | Cliquez sur "Informations complémentaires" → "Exécuter quand même" |
| "Amah Agent.exe" ne démarre pas ou signale un fichier manquant | Le .exe a été sorti de son dossier : relancez-le depuis le dossier `Amah Agent` (avec `_internal` à côté) |
| "Quota journalier Groq épuisé" | Les clés Groq gratuites ont atteint leur limite du jour : réessayez plus tard ou ajoutez une 2e/3e clé |
| "Clé Groq invalide" | Vérifiez que vous avez bien copié toute la clé |
| "Erreur Gmail" | Vérifiez que IMAP est activé dans Gmail |
| Micro non détecté | Vérifiez que votre micro est branché et activé dans Windows |
| Volume/luminosité ne change pas | Normal sur certains écrans externes (WMI non supporté) |
| L'écran de config réapparaît | Le fichier .env a été supprimé, reconfigurez |

---

## Support

Contact : **contact.amah.officiel@gmail.com**
