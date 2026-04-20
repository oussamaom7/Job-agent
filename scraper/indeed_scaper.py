import json
import os
import time
import random
from urllib.parse import urlparse, parse_qs
from playwright.sync_api import sync_playwright


DEFAULT_USER_AGENTS = [
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
]


def parse_proxy_list(proxies: list | None = None) -> list:
    """
    Retourne la liste des proxies a utiliser.
    Priorite: argument proxies, puis variable d'env INDEED_PROXIES (CSV).
    """

    if proxies:
        return [p for p in proxies if p]

    env_value = os.getenv("INDEED_PROXIES", "").strip()
    if not env_value:
        return []

    return [p.strip() for p in env_value.split(",") if p.strip()]


def is_indeed_blocked(page) -> bool:
    """Detecte les pages anti-bot/captcha Indeed."""

    return (
        page.locator("text=Requête bloquée").count() > 0
        or page.locator("text=Vérifiez que vous êtes un humain").count() > 0
        or page.locator("text=Please verify you are a human").count() > 0
        or "captcha" in page.url.lower()
    )


def human_delay(min_sec=1.5, max_sec=3.5):
    """
    Attend un délai aléatoire pour simuler un comportement humain.
    Sans ça, Indeed détecte le bot et bloque.
    """
    time.sleep(random.uniform(min_sec, max_sec))


def scrape_indeed(
    keywords : str,
    location : str = "France",
    max_jobs : int = 10,
    max_attempts: int = 4,
    base_backoff_sec: float = 3.0,
    proxies: list | None = None,
    user_agents: list | None = None,
    headless: bool = False,
) -> list:
    jobs = []
    proxy_pool = parse_proxy_list(proxies)
    ua_pool = user_agents if user_agents else DEFAULT_USER_AGENTS
    url = f"https://fr.indeed.com/jobs?q={keywords.replace(' ', '+')}&l={location.replace(' ', '+')}"

    with sync_playwright() as p:
        for attempt in range(1, max_attempts + 1):
            attempt_jobs = []
            blocked_count = 0

            ua = ua_pool[(attempt - 1) % len(ua_pool)]
            proxy_server = proxy_pool[(attempt - 1) % len(proxy_pool)] if proxy_pool else None

            print(f"\n=== Tentative {attempt}/{max_attempts} ===")
            print(f"User-Agent: {ua[:70]}...")
            if proxy_server:
                print(f"Proxy: {proxy_server}")
            else:
                print("Proxy: aucun")

            browser_kwargs = {"headless": headless}
            if proxy_server:
                browser_kwargs["proxy"] = {"server": proxy_server}

            browser = p.chromium.launch(**browser_kwargs)
            context = browser.new_context(
                user_agent=ua,
                viewport={"width": 1280, "height": 800},
                locale="fr-FR",
            )
            page = context.new_page()

            try:
                print(f"Navigation vers : {url}\n")
                page.goto(url, wait_until="domcontentloaded", timeout=30000)
                human_delay(2, 4)

                try:
                    cookie_btn = page.locator("button#onetrust-accept-btn-handler")
                    if cookie_btn.is_visible(timeout=3000):
                        cookie_btn.click()
                        print("✓ Cookies acceptés")
                        human_delay()
                except:
                    pass

                if is_indeed_blocked(page):
                    raise RuntimeError("Page de résultats bloquée par anti-bot Indeed")

                job_links = []
                cards = page.locator("a.jcs-JobTitle").all()
                print(f"{len(cards)} offres trouvées\n")

                for card in cards[:max_jobs]:
                    try:
                        href = card.get_attribute("href")
                        data_jk = card.get_attribute("data-jk")

                        if href and href.startswith("/"):
                            job_url = f"https://fr.indeed.com{href}"
                        elif href:
                            job_url = href
                        elif data_jk:
                            job_url = f"https://fr.indeed.com/viewjob?jk={data_jk}"
                        else:
                            continue

                        if not data_jk:
                            parsed = urlparse(job_url)
                            data_jk = parse_qs(parsed.query).get("jk", [None])[0]

                        job_links.append({"jk": data_jk, "url": job_url})
                    except:
                        continue

                print(f"{len(job_links)} liens collectés\n")

                for i, link in enumerate(job_links):
                    try:
                        page.goto(link["url"], wait_until="domcontentloaded", timeout=30000)
                        human_delay(2, 3)

                        if is_indeed_blocked(page):
                            blocked_count += 1
                            print(f"  ⚠ Blocage Indeed détecté sur offre {i+1} ({blocked_count} fois)")
                            if blocked_count >= 3:
                                raise RuntimeError("Trop de pages d'offres bloquées")
                            continue

                        try:
                            title = page.locator("h1.jobsearch-JobInfoHeader-title").inner_text(timeout=4000).strip()
                            title = title.replace(" - job post", "").strip()
                        except:
                            try:
                                title = page.locator("h1").first.inner_text(timeout=3000).strip()
                            except:
                                title = "Titre inconnu"

                        try:
                            company = page.locator("[data-company-name='true']").inner_text(timeout=3000).strip()
                        except:
                            try:
                                company = page.locator(".jobsearch-InlineCompanyRating-companyHeader a").inner_text(timeout=2000).strip()
                            except:
                                try:
                                    company = page.locator("[data-testid='inlineHeader-companyName']").inner_text(timeout=2000).strip()
                                except:
                                    company = "Inconnue"

                        try:
                            location_text = page.locator("[data-testid='job-location']").inner_text(timeout=3000).strip()
                        except:
                            try:
                                location_text = page.locator("#jobLocationText").inner_text(timeout=2000).strip()
                            except:
                                location_text = location

                        try:
                            description = page.locator("#jobDescriptionText").inner_text(timeout=5000).strip()
                        except:
                            description = "Description non disponible"

                        job = {
                            "id"         : f"indeed_{link['jk'] or i}",
                            "title"      : title,
                            "company"    : company,
                            "location"   : location_text,
                            "description": description,
                            "salary_min" : None,
                            "salary_max" : None,
                            "salary_raw" : None,
                            "posted_at"  : "",
                            "url"        : link["url"],
                            "source"     : "indeed",
                        }

                        attempt_jobs.append(job)
                        print(f"  ✓ [{i+1}] {title} — {company} | {location_text}")
                        human_delay(1.5, 3)
                    except Exception as e:
                        print(f"  ⚠ Erreur offre {i+1} : {e}")
                        continue

                if attempt_jobs:
                    jobs = attempt_jobs
                    print(f"Tentative {attempt} réussie avec {len(attempt_jobs)} offres.")
                    break

                raise RuntimeError("Aucune offre exploitable sur cette tentative")

            except Exception as e:
                print(f"⚠ Tentative {attempt} échouée: {e}")
                if attempt < max_attempts:
                    backoff = base_backoff_sec * (2 ** (attempt - 1))
                    jitter = random.uniform(0.0, 1.5)
                    wait_time = backoff + jitter
                    print(f"Nouvelle tentative dans {wait_time:.1f}s...")
                    time.sleep(wait_time)
            finally:
                browser.close()

    print(f"\n{len(jobs)} offres scrapées depuis Indeed")
    return jobs


def save_indeed_jobs(jobs: list, filepath: str = "data/jobs.json") -> None:
    """
    Fusionne les offres Indeed avec les offres existantes et sauvegarde.
    """

    os.makedirs(os.path.dirname(filepath), exist_ok=True)

    # Charge les offres existantes si le fichier existe
    existing = []
    if os.path.exists(filepath):
        with open(filepath, "r", encoding="utf-8") as f:
            existing = json.load(f)

    # Évite les doublons par titre + company
    existing_keys = {(j["title"], j["company"]) for j in existing}
    new_jobs = [j for j in jobs if (j["title"], j["company"]) not in existing_keys]

    merged = existing + new_jobs

    with open(filepath, "w", encoding="utf-8") as f:
        json.dump(merged, f, ensure_ascii=False, indent=2)

    print(f"✓ {len(new_jobs)} nouvelles offres ajoutées → {filepath} ({len(merged)} total)")


if __name__ == "__main__":
    jobs = scrape_indeed(
        keywords = "full stack",
        location = "Maroc",
        max_jobs = 20
    )

    if jobs:
        save_indeed_jobs(jobs)

        print("\n--- Aperçu ---")
        for job in jobs[:3]:
            print(f"\n{job['title']} — {job['company']}")
            print(f"  Location : {job['location']}")
            print(f"  Desc     : {job['description'][:150]}...")