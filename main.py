import json
from scraper.adzuna_scraper import fetch_jobs, clean_jobs, filter_jobs, save_jobs
from agents.analyzer_agent import analyze_all_jobs
from agents.cv_agent import run_cv_agent
from agents.letter_agent import run_letter_agent


def run_pipeline(keywords: str, country: str = "fr"):
    """
    Pipeline complet :
    1. Scrape les offres
    2. Nettoie et filtre
    3. Analyse avec Groq
    4. Pour chaque offre → génère CV + lettre
    5. Human review avant envoi
    """

    print("=" * 50)
    print("ÉTAPE 1 — Scraping des offres")
    print("=" * 50)
    raw_jobs  = fetch_jobs(keywords, country=country)
    clean     = clean_jobs(raw_jobs)

    my_keywords = ["react", "node", "python", "spring", "fullstack", "full-stack", "ai", "llm"]
    filtered  = filter_jobs(clean, my_keywords)
    save_jobs(filtered)

    print("\n" + "=" * 50)
    print("ÉTAPE 2 — Analyse des offres avec Groq")
    print("=" * 50)
    analyzed_jobs = analyze_all_jobs()

    print("\n" + "=" * 50)
    print("ÉTAPE 3 — Génération CV + Lettre par offre")
    print("=" * 50)

    results = []

    for job in analyzed_jobs:
        print(f"\n{'─' * 40}")
        print(f"Offre : {job['title']} — {job['company']}")
        print(f"{'─' * 40}")

        # Génération CV
        cv_path     = run_cv_agent(job)

        # Génération lettre
        letter_path = run_letter_agent(job)

        results.append({
            "job"        : f"{job['title']} — {job['company']}",
            "cv"         : cv_path,
            "letter"     : letter_path,
            "url"        : job.get("url", ""),
        })

    print("\n" + "=" * 50)
    print("ÉTAPE 4 — Human Review")
    print("=" * 50)
    print(f"\n{len(results)} candidatures générées :\n")

    for i, r in enumerate(results):
        print(f"[{i+1}] {r['job']}")
        print(f"    CV     : {r['cv']}")
        print(f"    Lettre : {r['letter']}")
        print(f"    URL    : {r['url']}\n")

    # Validation humaine avant envoi
    print("Veux-tu envoyer ces candidatures ? (oui/non) : ", end="")
    confirm = input().strip().lower()

    if confirm == "oui":
        print("\n→ Envoi en cours... (Gmail API — prochaine étape)")
    else:
        print("\n→ Candidatures sauvegardées dans output/ — envoi annulé.")

    return results


if __name__ == "__main__":
    run_pipeline("full stack developer python", country="fr")