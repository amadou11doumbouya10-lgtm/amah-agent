"""
Génère le document de pitch pour la maison d'entrepreneuriat
"""
from fpdf import FPDF
from datetime import datetime
import os

GOLD   = (200, 169, 110)
DARK   = (26,  26,  23)
WHITE  = (255, 255, 255)
GREY   = (100, 100, 100)
LIGHT  = (245, 240, 230)
GREEN  = (39,  174, 96)


ARIAL    = "C:/Windows/Fonts/arial.ttf"
ARIAL_B  = "C:/Windows/Fonts/arialbd.ttf"
ARIAL_I  = "C:/Windows/Fonts/ariali.ttf"
ARIAL_BI = "C:/Windows/Fonts/arialbi.ttf"


class PitchPDF(FPDF):

    def __init__(self):
        super().__init__()
        self.add_font("Arial",    "",  ARIAL)
        self.add_font("Arial",    "B", ARIAL_B)
        self.add_font("Arial",    "I", ARIAL_I)
        self.add_font("Arial",    "BI",ARIAL_BI)

    def header(self):
        pass

    def footer(self):
        self.set_y(-14)
        self.set_font("Arial", "I", 8)
        self.set_text_color(*GREY)
        self.cell(0, 10, "Amah Agent  |  contact.amah.officiel@gmail.com  |  Confidentiel", align="C")

    def titre_page(self, titre, sous_titre=""):
        # Fond sombre
        self.set_fill_color(*DARK)
        self.rect(0, 0, 210, 297, "F")

        # Bande dorée en haut
        self.set_fill_color(*GOLD)
        self.rect(0, 0, 210, 4, "F")

        # Espace vertical
        self.set_y(60)

        # Titre principal
        self.set_font("Arial", "B", 36)
        self.set_text_color(*GOLD)
        self.cell(0, 14, "THE AMAH", align="C", new_x="LMARGIN", new_y="NEXT")

        self.set_font("Arial", "", 18)
        self.set_text_color(*WHITE)
        self.cell(0, 10, "Agent IA Local pour Windows", align="C", new_x="LMARGIN", new_y="NEXT")

        self.ln(10)
        self.set_fill_color(*GOLD)
        self.rect(60, self.get_y(), 90, 0.8, "F")
        self.ln(12)

        self.set_font("Arial", "B", 16)
        self.set_text_color(*GOLD)
        self.cell(0, 8, titre, align="C", new_x="LMARGIN", new_y="NEXT")

        if sous_titre:
            self.ln(4)
            self.set_font("Arial", "", 12)
            self.set_text_color(180, 180, 170)
            self.cell(0, 7, sous_titre, align="C", new_x="LMARGIN", new_y="NEXT")

        self.ln(30)
        self.set_font("Arial", "", 11)
        self.set_text_color(*GOLD)
        self.cell(0, 7, "contact.amah.officiel@gmail.com", align="C", new_x="LMARGIN", new_y="NEXT")

        self.set_font("Arial", "I", 9)
        self.set_text_color(*GREY)
        self.cell(0, 7, datetime.now().strftime("Présenté le %d/%m/%Y"), align="C")

    def section(self, titre, couleur=None):
        self.ln(6)
        if couleur:
            self.set_fill_color(*couleur)
            self.set_text_color(*WHITE)
            self.set_font("Arial", "B", 13)
            self.cell(0, 9, f"  {titre}", fill=True, new_x="LMARGIN", new_y="NEXT")
        else:
            self.set_fill_color(*GOLD)
            self.rect(15, self.get_y(), 3, 7, "F")
            self.set_x(22)
            self.set_font("Arial", "B", 13)
            self.set_text_color(*DARK)
            self.cell(0, 7, titre, new_x="LMARGIN", new_y="NEXT")
        self.ln(3)

    def corps(self, texte, indent=15):
        self.set_font("Arial", "", 11)
        self.set_text_color(50, 50, 50)
        self.set_x(indent)
        self.multi_cell(0, 6, texte)
        self.ln(2)

    def bullet(self, items, indent=20):
        self.set_font("Arial", "", 11)
        self.set_text_color(50, 50, 50)
        for item in items:
            self.set_x(indent)
            self.cell(6, 6, "•")
            self.multi_cell(0, 6, item)

    def encadre(self, titre, contenu, couleur=(245, 240, 230)):
        self.set_fill_color(*couleur)
        self.set_draw_color(*GOLD)
        y_start = self.get_y()
        self.rect(15, y_start, 180, 4 + len(contenu.split('\n')) * 7 + 10, "DF")
        self.set_xy(20, y_start + 3)
        self.set_font("Arial", "B", 11)
        self.set_text_color(*DARK)
        self.cell(0, 6, titre, new_x="LMARGIN", new_y="NEXT")
        self.set_x(20)
        self.set_font("Arial", "", 10)
        self.set_text_color(60, 60, 60)
        self.multi_cell(170, 6, contenu)
        self.ln(4)

    def tableau_2col(self, data, header1="", header2=""):
        col = 90
        if header1:
            self.set_fill_color(*DARK)
            self.set_text_color(*WHITE)
            self.set_font("Arial", "B", 10)
            self.set_x(15)
            self.cell(col, 7, f"  {header1}", fill=True, border=1)
            self.cell(col, 7, f"  {header2}", fill=True, border=1, new_x="LMARGIN", new_y="NEXT")

        alt = False
        for row in data:
            self.set_fill_color(245, 240, 230) if alt else self.set_fill_color(*WHITE)
            self.set_text_color(40, 40, 40)
            self.set_font("Arial", "", 10)
            self.set_x(15)
            self.cell(col, 6, f"  {row[0]}", fill=True, border=1)
            self.cell(col, 6, f"  {row[1]}", fill=True, border=1, new_x="LMARGIN", new_y="NEXT")
            alt = not alt
        self.ln(4)


def main():
    pdf = PitchPDF()
    pdf.set_auto_page_break(auto=True, margin=18)
    pdf.set_margins(15, 15, 15)

    # ── PAGE 1 — TITRE ──────────────────────────────────────────────────────
    pdf.add_page()
    pdf.titre_page(
        "Dossier de Présentation Entrepreneuriat",
        "Un assistant IA qui agit vraiment sur votre PC"
    )

    # ── PAGE 2 — PROBLÈME & SOLUTION ────────────────────────────────────────
    pdf.add_page()

    pdf.section("1. Le Problème", couleur=DARK)
    pdf.corps(
        "Les assistants IA actuels (ChatGPT, Copilot, Gemini) sont des chatbots. "
        "Ils répondent à des questions, mais ils ne peuvent pas :"
    )
    pdf.bullet([
        "Organiser vos fichiers ou créer un document sur votre PC",
        "Lire et envoyer vos emails directement",
        "Naviguer sur internet de façon autonome",
        "Se souvenir de vos préférences entre les sessions",
        "Fonctionner sans connexion internet permanente",
    ])
    pdf.ln(2)
    pdf.encadre(
        "Résultat",
        "Un cadre ou un entrepreneur passe en moyenne 2h30 par jour sur des tâches\n"
        "répétitives : classer des fichiers, rédiger des emails, chercher des informations.\n"
        "C'est du temps perdu qui pourrait être automatisé.",
        couleur=(255, 245, 230)
    )

    pdf.section("2. La Solution — Amah Agent")
    pdf.corps(
        "Amah Agent est un assistant IA installé directement sur le PC Windows. "
        "Il n'envoie rien dans le cloud — tout reste local. "
        "Il parle français et agit concrètement sur le système."
    )
    pdf.bullet([
        "\"Organise mon bureau\" → Amah classe tous les fichiers par type en 3 secondes",
        "\"Lis mes 5 derniers emails\" → Amah ouvre Gmail et lit le contenu",
        "\"Crée un rapport Word sur notre réunion\" → le document est généré automatiquement",
        "\"Rappelle-moi dans 1 heure d'appeler le client\" → notification Windows programmée",
        "\"Quelle est la météo à Paris demain ?\" → réponse immédiate avec prévisions",
    ])

    # ── PAGE 3 — PRODUIT ────────────────────────────────────────────────────
    pdf.add_page()

    pdf.section("3. Le Produit", couleur=DARK)
    pdf.corps("Amah Agent dispose de 65 outils opérationnels répartis en 15 catégories :")
    pdf.ln(2)

    pdf.tableau_2col([
        ("Fichiers & Dossiers",    "Organiser, chercher, déplacer, classer"),
        ("Documents",             "Créer Word, PDF, TXT — lire et résumer"),
        ("Email Gmail",           "Lire, envoyer, chercher (SMTP/IMAP)"),
        ("Navigation Web",        "Piloter Chrome, remplir formulaires"),
        ("Excel",                 "Lire, créer, modifier des tableurs"),
        ("Voix",                  "Synthèse vocale + reconnaissance micro"),
        ("Mémoire",               "Se souvient entre les sessions (SQLite)"),
        ("Météo & Traduction",    "100+ langues, prévisions temps réel"),
        ("Notifications & Rappels","Alertes Windows, tâches planifiées"),
        ("Système & Réseau",      "Infos PC, processus, IP, archives ZIP"),
    ], "Catégorie", "Ce qu'Amah fait")

    pdf.section("Caractéristiques techniques")
    pdf.bullet([
        "Intelligence : Groq API — modèle Llama 3.3-70B (gratuit, 14 400 req/jour)",
        "Interface : Python tkinter — thème or/sombre sur mesure",
        "Distribution : fichier .exe standalone (114 Mo) — aucune installation Python requise",
        "Mémoire : base SQLite locale — données confidentielles, jamais dans le cloud",
        "Licence : système offline lié au hardware de chaque machine",
    ])

    # ── PAGE 4 — MARCHÉ & MODÈLE ────────────────────────────────────────────
    pdf.add_page()

    pdf.section("4. Marché Cible", couleur=DARK)
    pdf.tableau_2col([
        ("Freelances & Indépendants",  "Gain de temps sur tâches admin — 5-10h/semaine récupérées"),
        ("TPE & PME (1-20 salariés)",  "Pas de service informatique — besoin d'automatisation simple"),
        ("Professions libérales",      "Médecins, avocats, comptables — confidentialité des données"),
        ("Étudiants & Chercheurs",     "Gestion documents, recherches, organisation"),
    ], "Segment", "Valeur perçue")

    pdf.encadre(
        "Taille du marché",
        "En France : 3,2 millions d'indépendants + 2,5 millions de TPE\n"
        "Si 1% adopte une solution à 199€ → marché adressable : 11,4 millions €",
        couleur=(230, 245, 235)
    )

    pdf.section("5. Modèle Commercial")
    pdf.tableau_2col([
        ("Licence unique (one-shot)",  "199€ par poste — simple, pas d'abonnement"),
        ("Abonnement mensuel",         "29€/mois — accès aux mises à jour + nouveaux outils"),
        ("Prestation sur mesure",      "500-2000€ — personnalisation pour un métier spécifique"),
        ("Revendeurs partenaires",     "Commission 30-40% — démultiplier les ventes"),
    ], "Modèle", "Tarif")

    pdf.ln(2)
    pdf.encadre(
        "Projection à 12 mois",
        "20 ventes à 199€ = 3 980€ (seuil de rentabilité du développement)\n"
        "50 ventes à 199€ = 9 950€\n"
        "100 clients en abonnement 29€/mois = 2 900€ récurrents/mois = 34 800€/an",
        couleur=(255, 245, 230)
    )

    # ── PAGE 5 — AVANTAGES & VISION ─────────────────────────────────────────
    pdf.add_page()

    pdf.section("6. Avantages Concurrentiels", couleur=DARK)
    pdf.tableau_2col([
        ("Microsoft Copilot",    "25€/mois — limité à Office, données dans le cloud"),
        ("ChatGPT Plus",         "20€/mois — répond, n'agit pas, données cloud"),
        ("Zapier + GPT",         "50-100€/mois — automatisation web, pas local"),
        ("AMAH AGENT ✓",         "199€ unique — agit vraiment, local, privé, 65 outils"),
    ], "Concurrent", "Positionnement")

    pdf.section("Différenciateurs clés")
    pdf.bullet([
        "Local & privé : les données ne quittent jamais le PC du client",
        "Agit concrètement : effectue des actions réelles, pas seulement du texte",
        "Distributable en .exe : le client n'installe rien, double-clic et ça marche",
        "65 outils intégrés : couverture complète des besoins quotidiens",
        "Licence hardware : protégé contre la copie et le partage illégal",
    ])

    pdf.section("7. Vision & Roadmap")
    pdf.bullet([
        "Version 1.0 (actuel) : 65 outils, .exe distributable, système de licence",
        "Version 1.1 : Google Calendar, mode mains libres (voix complète)",
        "Version 1.2 : Connexion Telegram, tableau de bord journalier automatique",
        "Version 2.0 : Mode multi-utilisateurs pour entreprises (5-20 postes)",
        "Long terme : plateforme de personnalisation par métier (cabinet médical, cabinet d'avocat...)",
    ])

    # ── PAGE 6 — DEMANDE & CONTACT ───────────────────────────────────────────
    pdf.add_page()

    pdf.section("8. Ce que nous recherchons", couleur=DARK)
    pdf.corps(
        "En présentant Amah Agent à la Maison de l'Entrepreneuriat, nous cherchons :"
    )
    pdf.bullet([
        "Un accompagnement pour structurer la stratégie commerciale et le go-to-market",
        "Un accès au réseau d'entrepreneurs et d'investisseurs de l'université",
        "Un mentorat sur les aspects juridiques (propriété intellectuelle, licence logicielle)",
        "Des ressources pour financer le développement des prochaines versions",
        "Un espace pour tester le produit avec des clients pilotes (freelances, TPE locales)",
    ])

    pdf.ln(4)
    pdf.section("9. Résumé Exécutif")
    pdf.encadre(
        "En une phrase",
        "Amah Agent est l'assistant IA qui agit vraiment — il organise vos fichiers, lit vos emails,\n"
        "navigue sur internet et automatise votre quotidien, directement sur votre PC Windows,\n"
        "sans abonnement cloud, sans risque pour vos données.",
        couleur=(245, 240, 230)
    )

    pdf.tableau_2col([
        ("Produit",          "Application Windows standalone (65 outils)"),
        ("Technologie",      "Python 3.13 + Groq AI + PyInstaller"),
        ("État",             "Version 1.0 — prête à distribuer"),
        ("Prix",             "199€ licence unique / 29€ abonnement mensuel"),
        ("Distribution",     ".exe standalone — livré clé en main"),
        ("Contact",          "contact.amah.officiel@gmail.com"),
    ], "Indicateur", "Valeur")

    # Contact final
    pdf.ln(6)
    pdf.set_fill_color(*DARK)
    pdf.rect(15, pdf.get_y(), 180, 35, "F")
    pdf.set_fill_color(*GOLD)
    pdf.rect(15, pdf.get_y(), 4, 35, "F")

    pdf.set_xy(25, pdf.get_y() + 8)
    pdf.set_font("Arial", "B", 13)
    pdf.set_text_color(*GOLD)
    pdf.cell(0, 7, "Nous contacter", new_x="LMARGIN", new_y="NEXT")
    pdf.set_x(25)
    pdf.set_font("Arial", "", 11)
    pdf.set_text_color(*WHITE)
    pdf.cell(0, 6, "contact.amah.officiel@gmail.com", new_x="LMARGIN", new_y="NEXT")
    pdf.set_x(25)
    pdf.set_font("Arial", "I", 10)
    pdf.set_text_color(180, 170, 140)
    pdf.cell(0, 6, "github.com/amadou11doumbouya10-lgtm/amah-agent")

    # Sauvegarde
    path = r"C:\Users\Smarte technologui\Desktop\Amah_Agent_Pitch_Entrepreneuriat.pdf"
    pdf.output(path)
    print(f"Document cree : {path}")
    os.startfile(path)


if __name__ == "__main__":
    main()



