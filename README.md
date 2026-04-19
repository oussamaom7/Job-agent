# Job Agent

Pipeline Python pour automatiser une candidature tech:
- Scraping d'offres (Adzuna)
- Filtrage selon mots-cles
- Analyse des offres avec Groq
- Generation de CV cible (DOCX)
- Generation de lettre de motivation ciblee (DOCX)

## Structure

- main.py: point d'entree principal
- scraper/adzuna_scraper.py: scraping, nettoyage, filtrage, sauvegarde jobs
- agents/analyzer_agent.py: analyse semantique des offres avec Groq
- agents/cv_agent.py: generation d'un CV adapte a chaque offre
- agents/letter_agent.py: generation d'une lettre adaptee a chaque offre
- data/cv_master.json: profil CV source
- data/jobs.json: offres filtrees
- data/jobs_analyzed.json: offres enrichies avec analyse
- output/: documents generes

## Prerequis

- Python 3.10+
- Compte et cle API Adzuna
- Cle API Groq

## Installation

1. Creer et activer un environnement virtuel:

```bash
python3 -m venv .venv
source .venv/bin/activate
```

2. Installer les dependances:

```bash
pip install -r requirements.txt
pip install python-docx
```

Note: python-docx est requis par les agents CV et lettre.

## Configuration

Creer un fichier .env a la racine:

```env
ADZUNA_APP_ID=...
ADZUNA_APP_KEY=...
GROQ_API_KEY=...
```

Le fichier .env est ignore par Git via .gitignore.

## Execution

Lancer le pipeline complet:

```bash
python3 main.py
```

Le pipeline effectue:
1. Recuperation et filtrage des offres
2. Analyse AI des offres
3. Generation CV + lettre pour chaque offre
4. Validation manuelle finale (oui/non)

## Execution par etape

Scraper seulement:

```bash
python3 scraper/adzuna_scraper.py
```

Analyser les offres deja scrapees:

```bash
python3 agents/analyzer_agent.py
```

Generer un CV de test sur la premiere offre analysee:

```bash
python3 agents/cv_agent.py
```

Generer une lettre de test sur la premiere offre analysee:

```bash
python3 agents/letter_agent.py
```

## Sorties generees

- data/jobs.json
- data/jobs_analyzed.json
- output/CV_Oussama_<Company>.docx
- output/LM_Oussama_<Company>.docx

## Troubleshooting

1. ModuleNotFoundError sur un agent
- Verifier que vous lancez depuis la racine du projet.
- Utiliser les chemins existants sous agents/.

2. Erreur d'architecture pydantic_core sur macOS
- Reinstaller les paquets:

```bash
python3 -m pip install --upgrade --force-reinstall pydantic-core pydantic groq
```

3. Locale francaise indisponible (fr_FR.UTF-8)
- Selon votre systeme, installer/activer la locale FR.
- Ou adapter agents/letter_agent.py pour un fallback de locale.

## Notes

- Les appels API Groq et Adzuna consomment des quotas.
- Le dossier output peut contenir des fichiers lourds: nettoyez-le avant commit si besoin.
