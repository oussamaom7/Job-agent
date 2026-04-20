"""Compatibility wrapper for the corrected scraper filename.

Allows running:
python3 scraper/indeed_scraper.py
"""

from indeed_scaper import scrape_indeed, save_indeed_jobs


if __name__ == "__main__":
    jobs = scrape_indeed(
        keywords="full stack",
        location="Maroc",
        max_jobs=20,
    )

    if jobs:
        save_indeed_jobs(jobs)

        print("\n--- Aperçu ---")
        for job in jobs[:3]:
            print(f"\n{job['title']} — {job['company']}")
            print(f"  Location : {job['location']}")
            print(f"  Desc     : {job['description'][:150]}...")
