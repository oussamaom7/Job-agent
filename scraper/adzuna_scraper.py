import requests
import os
from dotenv import load_dotenv
import json

load_dotenv()  # charge les variables depuis .env

APP_ID  = os.getenv("ADZUNA_APP_ID")
APP_KEY = os.getenv("ADZUNA_APP_KEY")

def fetch_jobs(keywords: str, country: str = "fr", results_per_page: int = 10) -> list:
    """
    Appelle l'API Adzuna et retourne une liste d'offres brutes.
    
    keywords        : ce que tu cherches, ex: "software engineer python"
    country         : code pays — "fr" pour France, "ma" n'existe pas, donc "fr" ou "gb"
    results_per_page: nombre d'offres à récupérer
    """
    
    url = f"https://api.adzuna.com/v1/api/jobs/{country}/search/1"
    
    # Paramètres envoyés à l'API
    params = {
        "app_id"          : APP_ID,
        "app_key"         : APP_KEY,
        "results_per_page": results_per_page,
        "what"            : keywords,  # mots-clés du poste
        "content-type"    : "application/json"
    }
    
    response = requests.get(url, params=params)
    
    # On vérifie que la requête a réussi
    if response.status_code != 200:
        print(f"Erreur API : {response.status_code}")
        print(response.text)
        return []
    
    data = response.json()
    
    # Les offres sont dans la clé "results"
    jobs = data.get("results", [])
    print(f"{len(jobs)} offres récupérées pour '{keywords}'")
    
    return jobs

def clean_job(raw_job: dict) -> dict:
    """
    Prend une offre brute d'Adzuna et retourne un dict propre et structuré.
    
    On garde uniquement les champs utiles pour l'agent d'analyse.
    """
    
    return {
        "id"         : raw_job.get("id", ""),
        "title"      : raw_job.get("title", ""),
        "company"    : raw_job.get("company", {}).get("display_name", "Inconnue"),
        "location"   : raw_job.get("location", {}).get("display_name", ""),
        "description": raw_job.get("description", ""),
        "salary_min" : raw_job.get("salary_min", None),   # None si pas renseigné
        "salary_max" : raw_job.get("salary_max", None),
        "posted_at"  : raw_job.get("created", ""),
        "url"        : raw_job.get("redirect_url", ""),
    }


def clean_jobs(raw_jobs: list) -> list:
    """
    Applique clean_job() sur toute la liste.
    """
    return [clean_job(job) for job in raw_jobs]


def save_jobs(jobs: list, filepath: str = "data/jobs.json") -> None:
    """
    Sauvegarde la liste d'offres dans un fichier JSON.
    
    filepath : chemin du fichier de sortie
    """
    
    # On s'assure que le dossier data/ existe
    os.makedirs(os.path.dirname(filepath), exist_ok=True)
    
    with open(filepath, "w", encoding="utf-8") as f:
        json.dump(jobs, f, ensure_ascii=False, indent=2)
    #                        ↑                   ↑
    #           garde les accents français     formatage lisible
    
    print(f"{len(jobs)} offres sauvegardées dans {filepath}")


def load_jobs(filepath: str = "data/jobs.json") -> list:
    """
    Charge les offres depuis le fichier JSON.
    Retourne une liste vide si le fichier n'existe pas encore.
    """
    
    if not os.path.exists(filepath):
        print("Aucun fichier trouvé, retourne une liste vide.")
        return []
    
    with open(filepath, "r", encoding="utf-8") as f:
        jobs = json.load(f)
    
    print(f"{len(jobs)} offres chargées depuis {filepath}")
    return jobs

def filter_jobs(jobs: list, keywords: list) -> list:
    """
    Filtre les offres qui contiennent au moins un mot-clé
    dans le titre ou la description.
    
    keywords : liste de mots à chercher, ex: ["react", "node", "python"]
    
    Exemple :
        filter_jobs(jobs, ["react", "node"])
        → garde uniquement les offres qui mentionnent react ou node
    """
    
    matched = []
    
    for job in jobs:
        # On met tout en minuscules pour comparer sans souci de casse
        title       = job.get("title", "").lower()
        description = job.get("description", "").lower()
        
        # On cherche si AU MOINS UN mot-clé est présent
        for keyword in keywords:
            if keyword.lower() in title or keyword.lower() in description:
                matched.append(job)
                break  # ← inutile de continuer si déjà matché
    
    print(f"{len(matched)} offres matchées sur {len(jobs)} total")
    return matched

if __name__ == "__main__":
    raw_jobs = fetch_jobs("full stack developer python", country="fr")
    clean    = clean_jobs(raw_jobs)
    
    # Étape 4 : on filtre selon ton profil
    my_keywords = ["react", "node", "python", "spring", "fullstack", "full-stack"]
    filtered    = filter_jobs(clean, my_keywords)
    
    # On sauvegarde uniquement les offres filtrées
    save_jobs(filtered)
    
    # Aperçu des titres matchés
    print("\n--- Offres retenues ---")
    for job in filtered:
        print(f"  · {job['title']} — {job['company']}")