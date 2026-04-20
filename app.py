import streamlit as st
import json
import os
from pathlib import Path

from scraper.adzuna_scraper import fetch_jobs, clean_jobs, filter_jobs, save_jobs
from agents.analyzer_agent import analyze_all_jobs
from agents.cv_agent import run_cv_agent
from agents.letter_agent import run_letter_agent

# --- Config page ---
st.set_page_config(
    page_title="Job Agent",
    page_icon="🎯",
    layout="wide"
)

# --- CSS custom ---
st.markdown("""
<style>
    .metric-card {
        background: #f8f9fa;
        border-radius: 12px;
        padding: 20px;
        border-left: 4px solid #4f46e5;
        margin-bottom: 12px;
    }
    .job-card {
        background: #ffffff;
        border-radius: 12px;
        padding: 20px;
        border: 1px solid #e5e7eb;
        margin-bottom: 16px;
    }
    .skill-badge {
        display: inline-block;
        background: #ede9fe;
        color: #5b21b6;
        border-radius: 20px;
        padding: 2px 12px;
        font-size: 13px;
        margin: 2px;
    }
    .approved  { border-left: 4px solid #10b981; }
    .rejected  { border-left: 4px solid #ef4444; }
    .pending   { border-left: 4px solid #f59e0b; }
    .section-title {
        font-size: 22px;
        font-weight: 600;
        margin-bottom: 20px;
        color: #111827;
    }
</style>
""", unsafe_allow_html=True)


# --- Session state init ---
# Streamlit recharge la page à chaque interaction
# session_state permet de garder les données entre les rechargements
if "jobs_analyzed" not in st.session_state:
    st.session_state.jobs_analyzed = []
if "decisions" not in st.session_state:
    st.session_state.decisions = {}  # { job_id: "approved" | "rejected" | "pending" }
if "generated" not in st.session_state:
    st.session_state.generated = {}  # { job_id: { cv: path, letter: path } }


# ─────────────────────────────────────────
# SIDEBAR — Contrôles principaux
# ─────────────────────────────────────────
with st.sidebar:
    st.image("https://img.icons8.com/fluency/96/goal.png", width=60)
    st.title("Job Agent 🎯")
    st.markdown("---")

    st.markdown("### 🔍 Recherche d'offres")

    keywords = st.text_input("Mots-clés", value="full stack developer python")

    source = st.radio(
        "Source",
        options=["Adzuna", "LinkedIn", "WTTJ"],
        horizontal=True
    )

    # Options spécifiques selon la source
    if source == "Adzuna":
        country = st.selectbox("Pays", options=["fr", "gb", "us", "de"], index=0)
        nb_results = st.slider("Nombre d'offres", 5, 50, 10, step=5)
        location = "France"
    else:
        location   = st.text_input("Localisation", value="Maroc")
        nb_results = st.slider("Nombre d'offres", 5, 20, 10, step=5)
        country    = "fr"

    my_keywords = st.multiselect(
        "Filtrer par compétences",
        options=["react", "node", "python", "spring", "fullstack", "full-stack", "ai", "llm", "angular", "docker"],
        default=["react", "node", "python", "fullstack", "ai", "llm"]
    )

    st.markdown("---")

    if st.button("🚀 Lancer le pipeline", use_container_width=True, type="primary"):
        # ── Scraping selon la source choisie ──
        with st.spinner(f"Scraping {source} en cours..."):
            if source == "Adzuna":
                from scraper.adzuna_scraper import fetch_jobs, clean_jobs, filter_jobs, save_jobs
                raw      = fetch_jobs(keywords, country=country, results_per_page=nb_results)
                clean    = clean_jobs(raw)
                filtered = filter_jobs(clean, my_keywords)
                save_jobs(filtered)

            elif source == "LinkedIn":
                from scraper.linkedin_scraper import scrape_linkedin, save_linkedin_jobs
                from scraper.adzuna_scraper import filter_jobs, save_jobs
                raw      = scrape_linkedin(keywords, location=location, max_jobs=nb_results)
                filtered = filter_jobs(raw, my_keywords)
                save_linkedin_jobs(filtered)

            elif source == "WTTJ":
                from scraper.wttj_scraper import scrape_wttj, save_wttj_jobs
                from scraper.adzuna_scraper import filter_jobs
                raw      = scrape_wttj(keywords, location=location, max_jobs=nb_results)
                filtered = filter_jobs(raw, my_keywords)
                save_wttj_jobs(filtered)

        st.success(f"✓ {len(filtered)} offres récupérées depuis {source}")

        # ── Analyse Groq ──
        with st.spinner("Analyse avec Groq..."):
            from agents.analyzer_agent import analyze_all_jobs
            analyzed = analyze_all_jobs()
            st.session_state.jobs_analyzed = analyzed
            for job in analyzed:
                jid = job["id"]
                if jid not in st.session_state.decisions:
                    st.session_state.decisions[jid] = "pending"

        st.success(f"✓ {len(analyzed)} offres analysées !")

    st.markdown("---")

    # Métriques globales
    if st.session_state.jobs_analyzed:
        total    = len(st.session_state.jobs_analyzed)
        approved = sum(1 for v in st.session_state.decisions.values() if v == "approved")
        rejected = sum(1 for v in st.session_state.decisions.values() if v == "rejected")
        pending  = total - approved - rejected

        st.markdown("### 📊 Résumé")
        col1, col2 = st.columns(2)
        with col1:
            st.metric("Total",      total)
            st.metric("✅ Approuvées", approved)
        with col2:
            st.metric("⏳ En attente", pending)
            st.metric("❌ Rejetées",   rejected)


# ─────────────────────────────────────────
# MAIN — Tabs
# ─────────────────────────────────────────
if not st.session_state.jobs_analyzed:
    # État vide — page d'accueil
    st.markdown("## Bienvenue sur Job Agent 🎯")
    st.markdown("Lance une recherche depuis la **sidebar** pour commencer.")

    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.markdown("""<div class="metric-card">
            <h3>1️⃣ Scraping</h3>
            <p>Récupère les offres depuis Adzuna</p>
        </div>""", unsafe_allow_html=True)
    with col2:
        st.markdown("""<div class="metric-card">
            <h3>2️⃣ Analyse</h3>
            <p>Groq extrait skills et missions</p>
        </div>""", unsafe_allow_html=True)
    with col3:
        st.markdown("""<div class="metric-card">
            <h3>3️⃣ Génération</h3>
            <p>CV + lettre personnalisés</p>
        </div>""", unsafe_allow_html=True)
    with col4:
        st.markdown("""<div class="metric-card">
            <h3>4️⃣ Review</h3>
            <p>Approuve ou rejette chaque candidature</p>
        </div>""", unsafe_allow_html=True)

else:
    # Tabs principaux
    tab1, tab2, tab3 = st.tabs(["📋 Offres & Analyse", "📄 CV & Lettres", "✅ Review & Envoi"])

    # ─────────────────────────────────────────
    # TAB 1 — Offres & Analyse
    # ─────────────────────────────────────────
    with tab1:
        st.markdown('<p class="section-title">Offres trouvées</p>', unsafe_allow_html=True)

        for job in st.session_state.jobs_analyzed:
            jid      = job["id"]
            analysis = job.get("analysis", {})
            decision = st.session_state.decisions.get(jid, "pending")

            # Couleur de la card selon la décision
            border_class = {"approved": "approved", "rejected": "rejected", "pending": "pending"}[decision]

            with st.expander(f"**{job['title']}** — {job['company']}  |  {job['location']}", expanded=False):
                col1, col2 = st.columns([2, 1])

                with col1:
                    st.markdown("**📝 Description**")
                    st.write(job["description"][:500] + "..." if len(job["description"]) > 500 else job["description"])

                    if analysis.get("key_missions"):
                        st.markdown("**🎯 Missions clés**")
                        for m in analysis["key_missions"]:
                            st.markdown(f"- {m}")

                with col2:
                    st.markdown("**🛠 Skills requis**")
                    skills_html = " ".join(
                        f'<span class="skill-badge">{s}</span>'
                        for s in analysis.get("required_skills", [])
                    )
                    st.markdown(skills_html, unsafe_allow_html=True)

                    st.markdown("<br>", unsafe_allow_html=True)

                    col_a, col_b = st.columns(2)
                    with col_a:
                        st.metric("Séniorité", analysis.get("seniority", "—").capitalize())
                    with col_b:
                        st.metric("Ton", analysis.get("company_tone", "—").capitalize())

                    if job.get("salary_min"):
                        st.metric("Salaire", f"{int(job['salary_min'])}–{int(job['salary_max'])}€")

                    st.markdown(f"[🔗 Voir l'offre]({job.get('url', '#')})")

    # ─────────────────────────────────────────
    # TAB 2 — CV & Lettres
    # ─────────────────────────────────────────
    with tab2:
        st.markdown('<p class="section-title">Génération des documents</p>', unsafe_allow_html=True)

        for job in st.session_state.jobs_analyzed:
            jid = job["id"]

            col1, col2, col3 = st.columns([3, 1, 1])

            with col1:
                st.markdown(f"**{job['title']}** — {job['company']}")

            with col2:
                # Bouton générer
                if st.button("⚡ Générer", key=f"gen_{jid}"):
                    with st.spinner(f"Génération pour {job['company']}..."):
                        cv_path     = run_cv_agent(job)
                        letter_path = run_letter_agent(job)
                        st.session_state.generated[jid] = {
                            "cv"    : cv_path,
                            "letter": letter_path
                        }
                    st.success("✓ Générés !")

            with col3:
                # Boutons de téléchargement si déjà générés
                if jid in st.session_state.generated:
                    files = st.session_state.generated[jid]

                    cv_path = files["cv"]
                    if os.path.exists(cv_path):
                        with open(cv_path, "rb") as f:
                            st.download_button(
                                "📥 CV",
                                data=f,
                                file_name=Path(cv_path).name,
                                mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
                                key=f"dl_cv_{jid}"
                            )

                    letter_path = files["letter"]
                    if os.path.exists(letter_path):
                        with open(letter_path, "rb") as f:
                            st.download_button(
                                "📥 Lettre",
                                data=f,
                                file_name=Path(letter_path).name,
                                mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
                                key=f"dl_letter_{jid}"
                            )

            st.markdown("---")

    # ─────────────────────────────────────────
    # TAB 3 — Review & Envoi
    # ─────────────────────────────────────────
    with tab3:
        st.markdown('<p class="section-title">Review des candidatures</p>', unsafe_allow_html=True)

        for job in st.session_state.jobs_analyzed:
            jid      = job["id"]
            decision = st.session_state.decisions.get(jid, "pending")
            generated = jid in st.session_state.generated

            # Icône selon statut
            icon = {"approved": "✅", "rejected": "❌", "pending": "⏳"}[decision]

            with st.container():
                col1, col2, col3, col4 = st.columns([3, 1, 1, 1])

                with col1:
                    st.markdown(f"{icon} **{job['title']}** — {job['company']}")
                    if not generated:
                        st.caption("⚠ Documents non générés — va dans l'onglet CV & Lettres")

                with col2:
                    if st.button("✅ Approuver", key=f"approve_{jid}", disabled=not generated):
                        st.session_state.decisions[jid] = "approved"
                        st.rerun()

                with col3:
                    if st.button("❌ Rejeter", key=f"reject_{jid}"):
                        st.session_state.decisions[jid] = "rejected"
                        st.rerun()

                with col4:
                    if st.button("🔄 Reset", key=f"reset_{jid}"):
                        st.session_state.decisions[jid] = "pending"
                        st.rerun()

                st.markdown("---")

        # Bouton envoi final
        approved_jobs = [
            j for j in st.session_state.jobs_analyzed
            if st.session_state.decisions.get(j["id"]) == "approved"
        ]

        if approved_jobs:
            st.markdown(f"### {len(approved_jobs)} candidature(s) prête(s) à envoyer")

            if st.button("📨 Envoyer toutes les candidatures approuvées", type="primary", use_container_width=True):
                st.info("→ Gmail API — prochaine étape à intégrer !")