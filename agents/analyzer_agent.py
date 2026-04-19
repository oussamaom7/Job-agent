import os
import json
from groq import Groq
from dotenv import load_dotenv

load_dotenv()

client = Groq(api_key=os.getenv("GROQ_API_KEY"))


def build_prompt(job: dict) -> str:
    """
    Construit le prompt envoye a Groq pour analyser une offre.

    On lui donne le titre, la boite et la description,
    et on lui demande de repondre UNIQUEMENT en JSON.
    """

    return f"""
Tu es un expert en recrutement tech. Analyse cette offre d'emploi et retourne UNIQUEMENT un objet JSON valide, sans texte avant ou apres.

Offre :
- Titre      : {job['title']}
- Entreprise : {job['company']}
- Description: {job['description']}

Retourne exactement ce format JSON :
{{
  "required_skills"    : ["skill1", "skill2"],
  "nice_to_have_skills": ["skill1", "skill2"],
  "seniority"          : "junior | mid | senior",
  "company_tone"       : "startup | corporate | scale-up",
  "key_missions"       : ["mission1", "mission2"],
  "match_keywords"     : ["mot1", "mot2"]
}}

Regles :
- required_skills    : competences explicitement demandees
- nice_to_have_skills: competences mentionnees mais optionnelles
- seniority          : deduis-le depuis le texte (annees d'exp, niveau)
- company_tone       : deduis-le depuis le style d'ecriture et le contexte
- key_missions       : les 3 missions principales du poste
- match_keywords     : mots-cles importants a reutiliser dans un CV
"""


def analyze_job(job: dict) -> dict:
    """
    Envoie une offre a Groq et retourne l'analyse structuree.
    Ajoute l'analyse directement dans le dict du job.
    """

    print(f"Analyse en cours : {job['title']} - {job['company']}")

    response = client.chat.completions.create(
        model="llama-3.3-70b-versatile",
        messages=[
            {
                "role": "user",
                "content": build_prompt(job),
            }
        ],
        temperature=0.2,
    )

    raw_text = response.choices[0].message.content

    try:
        analysis = json.loads(raw_text)
    except json.JSONDecodeError:
        print("  [WARN] JSON invalide recu, offre ignoree")
        print(f"  Recu : {raw_text[:100]}...")
        analysis = {}

    job["analysis"] = analysis
    return job


def analyze_all_jobs(
    input_file: str = "data/jobs.json",
    output_file: str = "data/jobs_analyzed.json",
) -> list:
    """
    Charge toutes les offres, les analyse une par une, sauvegarde le resultat.
    """

    with open(input_file, "r", encoding="utf-8") as f:
        jobs = json.load(f)

    print(f"{len(jobs)} offres a analyser\n")

    analyzed = []

    for job in jobs:
        result = analyze_job(job)
        analyzed.append(result)
        print("  [OK] Analyse terminee\n")

    with open(output_file, "w", encoding="utf-8") as f:
        json.dump(analyzed, f, ensure_ascii=False, indent=2)

    print(f"\n{len(analyzed)} offres analysees -> {output_file}")
    return analyzed


if __name__ == "__main__":
    analyzed_jobs = analyze_all_jobs()

    if analyzed_jobs:
        first = analyzed_jobs[0]
        print("\n--- Analyse de la première offre ---")
        print(f"Poste     : {first['title']}")
        print(f"Séniorité : {first['analysis'].get('seniority')}")
        print(f"Ton       : {first['analysis'].get('company_tone')}")
        print(f"Skills    : {first['analysis'].get('required_skills')}")
        print(f"Keywords  : {first['analysis'].get('match_keywords')}")
