import json
import os
import time
import random
from playwright.sync_api import sync_playwright


def human_delay(min_sec=1.5, max_sec=3.5):
    time.sleep(random.uniform(min_sec, max_sec))


def scrape_linkedin(
    keywords : str,
    location : str = "Maroc",
    max_jobs : int = 10
) -> list:
    """
    Scrape les offres LinkedIn Jobs sans login.
    LinkedIn permet de voir les offres publiques sans compte.
    """

    jobs = []

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=False)

        context = browser.new_context(
            user_agent=(
                "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/120.0.0.0 Safari/537.36"
            ),
            viewport={"width": 1440, "height": 900},
            locale="fr-FR"
        )

        page = context.new_page()

        # URL LinkedIn Jobs public — pas besoin de compte
        url = (
            f"https://www.linkedin.com/jobs/search/"
            f"?keywords={keywords.replace(' ', '%20')}"
            f"&location={location.replace(' ', '%20')}"
            f"&f_TPR=r604800"  # offres des 7 derniers jours
        )

        print(f"Navigation vers LinkedIn Jobs...")
        page.goto(url, wait_until="domcontentloaded")
        human_delay(3, 5)

        # Ferme le popup login — plusieurs tentatives car LinkedIn change souvent
        human_delay(2, 3)

        closed = False

        # Tentative 1 — bouton X classique
        for selector in [
            "button.modal__dismiss",
            "button[aria-label='Dismiss']",
            "button[aria-label='Fermer']",
            "svg[aria-label='Fermer']",
            ".modal__dismiss",
        ]:
            try:
                btn = page.locator(selector)
                if btn.is_visible(timeout=1500):
                    btn.click()
                    print(f"✓ Popup fermé via {selector}")
                    closed = True
                    human_delay()
                    break
            except:
                continue

        # Tentative 2 — touche Escape
        if not closed:
            page.keyboard.press("Escape")
            human_delay(1, 2)
            print("✓ Popup fermé via Escape")

        # Tentative 3 — clic en dehors du modal
        try:
            overlay = page.locator("div.modal__overlay")
            if overlay.is_visible(timeout=2000):
                # Clic dans le coin supérieur gauche — hors du modal
                page.mouse.click(10, 10)
                human_delay(1, 2)
                print("✓ Popup fermé via clic extérieur")
        except:
            pass

        # Scroll pour charger plus d'offres (lazy loading)
        print("Chargement des offres...")
        for _ in range(3):
            page.keyboard.press("End")
            human_delay(1, 2)

        # ─────────────────────────────────────────
        # ÉTAPE 1 — Collecte infos de base depuis les cards
        # sans cliquer — titre et company sont déjà dans le DOM
        # ─────────────────────────────────────────
        cards_data = []
        cards = page.locator("ul.jobs-search__results-list li").all()

        for card in cards[:max_jobs]:
            try:
                # Titre depuis la card directement
                try:
                    title = card.locator("h3.base-search-card__title").inner_text(timeout=2000).strip()
                except:
                    title = card.locator("h3").inner_text(timeout=2000).strip()

                # Entreprise depuis la card
                try:
                    company = card.locator("h4.base-search-card__subtitle").inner_text(timeout=2000).strip()
                except:
                    company = "Inconnue"

                # Localisation depuis la card
                try:
                    location_text = card.locator("span.job-search-card__location").inner_text(timeout=2000).strip()
                except:
                    location_text = location

                # URL depuis le lien de la card
                try:
                    job_url = card.locator("a.base-card__full-link").get_attribute("href", timeout=2000)
                    job_url = job_url.split("?")[0] if job_url else ""
                    job_id  = job_url.split("-")[-1] if job_url else f"li_{len(cards_data)}"
                except:
                    job_url = ""
                    job_id  = f"li_{len(cards_data)}"

                cards_data.append({
                    "id"      : f"linkedin_{job_id}",
                    "title"   : title,
                    "company" : company,
                    "location": location_text,
                    "url"     : job_url,
                    "card"    : card  # on garde la référence pour cliquer après
                })

            except Exception as e:
                continue

        print(f"{len(cards_data)} cards parsées\n")

        # Supprime tous les modals via JS une fois pour toutes
        page.evaluate("""
            document.querySelectorAll('.modal__overlay, .modal__container')
            .forEach(el => el.remove())
        """)
        print("✓ Modals supprimés via JS")
        human_delay(1, 2)

        # ─────────────────────────────────────────
        # ÉTAPE 2 — Navigation directe par URL
        # On évite complètement le problème du modal
        # ─────────────────────────────────────────
        for i, data in enumerate(cards_data):
            try:
                if not data["url"]:
                    print(f"  ⚠ Pas d'URL pour card {i+1}, skipped")
                    continue

                # Navigation directe vers la page de l'offre
                page.goto(data["url"], wait_until="domcontentloaded")
                human_delay(2, 3)

                # Supprime les modals sur la page de l'offre
                page.evaluate("""
                    document.querySelectorAll('.modal__overlay, .modal__container, [data-test-modal]')
                    .forEach(el => el.remove())
                """)

                # Voir plus
                try:
                    see_more = page.locator("button.show-more-less-html__button--more")
                    if see_more.is_visible(timeout=2000):
                        see_more.click()
                        human_delay(0.5, 1)
                except:
                    pass

                # Description
                try:
                    description = page.locator("div.show-more-less-html__markup").inner_text(timeout=4000).strip()
                except:
                    try:
                        description = page.locator(".description__text").inner_text(timeout=3000).strip()
                    except:
                        description = "Description non disponible"

                job = {
                    "id"         : data["id"],
                    "title"      : data["title"],
                    "company"    : data["company"],
                    "location"   : data["location"],
                    "description": description,
                    "salary_min" : None,
                    "salary_max" : None,
                    "salary_raw" : None,
                    "posted_at"  : "",
                    "url"        : data["url"],
                    "source"     : "linkedin"
                }

                jobs.append(job)
                print(f"  ✓ [{i+1}] {data['title']} — {data['company']}")
                human_delay(2, 3)

            except Exception as e:
                print(f"  ⚠ Erreur card {i+1} : {e}")
                continue

        browser.close()

    print(f"\n{len(jobs)} offres scrapées depuis LinkedIn")
    return jobs


def save_linkedin_jobs(jobs: list, filepath: str = "data/jobs.json") -> None:
    """
    Fusionne avec les offres existantes et sauvegarde.
    Évite les doublons par titre + company.
    """

    os.makedirs(os.path.dirname(filepath), exist_ok=True)

    existing = []
    if os.path.exists(filepath):
        with open(filepath, "r", encoding="utf-8") as f:
            existing = json.load(f)

    existing_keys = {(j["title"], j["company"]) for j in existing}
    new_jobs = [j for j in jobs if (j["title"], j["company"]) not in existing_keys]
    merged   = existing + new_jobs

    with open(filepath, "w", encoding="utf-8") as f:
        json.dump(merged, f, ensure_ascii=False, indent=2)

    print(f"✓ {len(new_jobs)} nouvelles offres ajoutées → {filepath} ({len(merged)} total)")


if __name__ == "__main__":
    jobs = scrape_linkedin(
        keywords = "full stack developer",
        location = "Maroc",
        max_jobs = 10
    )

    if jobs:
        save_linkedin_jobs(jobs)

        print("\n--- Aperçu ---")
        for job in jobs[:3]:
            print(f"\n{job['title']} — {job['company']}")
            print(f"  Location    : {job['location']}")
            print(f"  Description : {job['description'][:200]}...")