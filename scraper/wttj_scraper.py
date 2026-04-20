import json
import os
import time
import random
from playwright.sync_api import sync_playwright


def human_delay(min_sec=1.5, max_sec=3.5):
    time.sleep(random.uniform(min_sec, max_sec))


def scrape_wttj(
    keywords : str,
    location : str = "Maroc",
    max_jobs : int = 10
) -> list:
    """
    Scrape les offres Welcome to the Jungle.
    WTTJ est public, pas de login requis, pas de captcha agressif.
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

        # URL de recherche WTTJ
        url = (
            f"https://www.welcometothejungle.com/fr/jobs"
            f"?query={keywords.replace(' ', '%20')}"
            f"&location={location.replace(' ', '%20')}"
        )

        print(f"Navigation vers WTTJ...")
        page.goto(url, wait_until="domcontentloaded")
        human_delay(3, 5)

        # Accepte les cookies si présent
        try:
            cookie_btn = page.locator("button[data-testid='cookie-accept-all']")
            if cookie_btn.is_visible(timeout=3000):
                cookie_btn.click()
                print("✓ Cookies acceptés")
                human_delay()
        except:
            pass

        # Scroll pour charger les offres
        print("Chargement des offres...")
        for _ in range(3):
            page.keyboard.press("End")
            human_delay(1, 2)

        # ─────────────────────────────────────────
        # ÉTAPE 1 — Collecte les liens des offres
        # ─────────────────────────────────────────
        job_links = []
        cards = page.locator("li[data-testid='search-results-list-item-wrapper']").all()
        
        # Fallback si le sélecteur principal ne marche pas
        if not cards:
            cards = page.locator("article").all()

        print(f"{len(cards)} offres trouvées\n")

        for card in cards[:max_jobs]:
            try:
                # Récupère le lien de l'offre
                link = card.locator("a").first.get_attribute("href", timeout=2000)
                if link and "/jobs/" in link:
                    full_url = f"https://www.welcometothejungle.com{link}" if link.startswith("/") else link
                    job_links.append(full_url)
            except:
                continue

        print(f"{len(job_links)} liens collectés\n")

        # ─────────────────────────────────────────
        # ÉTAPE 2 — Visite chaque offre
        # ─────────────────────────────────────────
        for i, job_url in enumerate(job_links):
            try:
                page.goto(job_url, wait_until="domcontentloaded")
                human_delay(2, 3)

                # Accepte cookies si réapparu
                try:
                    cookie_btn = page.locator("button[data-testid='cookie-accept-all']")
                    if cookie_btn.is_visible(timeout=2000):
                        cookie_btn.click()
                        human_delay(0.5, 1)
                except:
                    pass

                # Titre + company depuis le bloc metadata
                try:
                    metadata = page.locator("[data-testid='job-metadata-block']").inner_text(timeout=4000).strip()
                    # Le bloc contient "COMPANY\nTitre du poste"
                    lines  = [l.strip() for l in metadata.split("\n") if l.strip()]
                    company = lines[0] if len(lines) > 0 else "Inconnue"
                    title   = lines[1] if len(lines) > 1 else "Titre inconnu"
                except:
                    # Fallback — titre depuis la balise <title> de la page
                    page_title = page.title()
                    # Format : "Titre - Welcome to the Jungle - CDI à Paris"
                    parts   = page_title.split(" - ")
                    title   = parts[0].strip() if parts else "Titre inconnu"
                    company = "Inconnue"

                # Localisation propre — extrait juste la ville/pays
                try:
                    meta_text = page.locator("[data-testid='job-metadata-block']").inner_text(timeout=3000)
                    loc_line  = ""
                    for line in meta_text.split("\n"):
                        line = line.strip()
                        if any(x in line.lower() for x in ["paris", "lyon", "maroc", "casablanca", "remote", "télétravail", "france"]):
                            loc_line = line
                            break
                    location_text = loc_line if loc_line else location
                except:
                    location_text = location

                # Contrat depuis l'URL ou metadata
                try:
                    contract = "CDI" if "cdi" in job_url.lower() else ""
                except:
                    contract = ""

                # Clique "Voir plus" pour description complète
                try:
                    voir_plus = page.locator("[data-testid='view-more-btn']")
                    if voir_plus.is_visible(timeout=2000):
                        voir_plus.click()
                        human_delay(0.5, 1)
                except:
                    pass

                # Description
                try:
                    desc_parts = []

                    # Section description principale
                    desc = page.locator("[data-testid='job-section-description']").inner_text(timeout=4000).strip()
                    desc_parts.append(desc)

                    # Section profil recherché
                    try:
                        profil = page.locator("[data-testid='job-section-experience']").inner_text(timeout=2000).strip()
                        desc_parts.append(profil)
                    except:
                        pass

                    # Nettoie la description — supprime le header "Descriptif du poste"
                    description = "\n\n".join(desc_parts)
                    description = description.replace("Descriptif du poste\n", "").strip()
                    description = description.replace("Profil recherché\n", "\nProfil recherché:\n").strip()

                except:
                    description = "Description non disponible"

                # ID unique depuis l'URL
                job_id = job_url.rstrip("/").split("/")[-1].split("?")[0]

                job = {
                    "id"         : f"wttj_{job_id}",
                    "title"      : title,
                    "company"    : company,
                    "location"   : location_text,
                    "contract"   : contract,
                    "description": description,
                    "salary_min" : None,
                    "salary_max" : None,
                    "salary_raw" : None,
                    "posted_at"  : "",
                    "url"        : job_url,
                    "source"     : "wttj"
                }

                jobs.append(job)
                print(f"  ✓ [{i+1}] {title} — {company} | {location_text[:40]}")
                human_delay(2, 3)

            except Exception as e:
                print(f"  ⚠ Erreur offre {i+1} : {e}")
                continue

        browser.close()

    print(f"\n{len(jobs)} offres scrapées depuis WTTJ")
    return jobs


def save_wttj_jobs(jobs: list, filepath: str = "data/jobs.json") -> None:
    """
    Fusionne avec les offres existantes, évite les doublons.
    """

    os.makedirs(os.path.dirname(filepath), exist_ok=True)

    existing = []
    if os.path.exists(filepath):
        with open(filepath, "r", encoding="utf-8") as f:
            existing = json.load(f)

    existing_keys = {(j["title"], j["company"]) for j in existing}
    new_jobs      = [j for j in jobs if (j["title"], j["company"]) not in existing_keys]
    merged        = existing + new_jobs

    with open(filepath, "w", encoding="utf-8") as f:
        json.dump(merged, f, ensure_ascii=False, indent=2)

    print(f"✓ {len(new_jobs)} nouvelles offres ajoutées → {filepath} ({len(merged)} total)")


if __name__ == "__main__":
    jobs = scrape_wttj(
        keywords = "full stack developer",
        location = "Maroc",
        max_jobs = 10
    )

    if jobs:
        save_wttj_jobs(jobs)

        print("\n--- Aperçu ---")
        for job in jobs[:3]:
            print(f"\n{job['title']} — {job['company']}")
            print(f"  Location : {job['location']}")
            print(f"  Contrat  : {job['contract']}")
            print(f"  Desc     : {job['description'][:200]}...")