import os
import base64
import json
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.base import MIMEBase
from email import encoders
from pathlib import Path

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build

# Permissions qu'on demande à Gmail
# On demande uniquement l'envoi — pas la lecture des emails
SCOPES = ["https://www.googleapis.com/auth/gmail.send"]


def get_client_secrets_path() -> str:
    """Retourne le chemin du fichier OAuth client secrets disponible."""

    candidates = ["credentials.json", "credential.json"]

    for path in candidates:
        if os.path.exists(path):
            return path

    raise FileNotFoundError(
        "Aucun fichier OAuth trouve. Ajoute 'credentials.json' ou 'credential.json' a la racine du projet."
    )


def get_gmail_service():
    """
    Authentifie l'utilisateur et retourne le service Gmail.
    
    Première fois : ouvre le navigateur pour l'autorisation Google
    Fois suivantes : utilise le token.json sauvegardé automatiquement
    """
    
    creds = None
    
    # Si on a déjà un token sauvegardé, on le charge
    if os.path.exists("token.json"):
        creds = Credentials.from_authorized_user_file("token.json", SCOPES)
    
    # Si pas de token valide → on lance le flow d'authentification
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            # Token expiré → on le rafraîchit automatiquement
            creds.refresh(Request())
        else:
            # Première fois → ouvre le navigateur
            client_secrets_path = get_client_secrets_path()
            flow = InstalledAppFlow.from_client_secrets_file(client_secrets_path, SCOPES)
            # Port fixe pour aligner l'URI de redirection autorisee cote Google Cloud.
            creds = flow.run_local_server(port=8080)
        
        # On sauvegarde le token pour les prochaines fois
        with open("token.json", "w") as f:
            f.write(creds.to_json())
    
    service = build("gmail", "v1", credentials=creds)
    print("✓ Gmail connecté")
    return service


def build_email(
    to      : str,
    subject : str,
    body    : str,
    cv_path : str,
    letter_path: str,
    sender  : str
) -> dict:
    """
    Construit l'email avec le CV et la lettre en pièces jointes.
    Retourne le message encodé prêt pour l'API Gmail.
    
    MIMEMultipart : format email qui supporte texte + pièces jointes
    """
    
    # Conteneur principal de l'email
    message = MIMEMultipart()
    message["to"]      = to
    message["from"]    = sender
    message["subject"] = subject
    
    # Corps du mail en texte plain
    message.attach(MIMEText(body, "plain"))
    
    # Fonction helper pour attacher un fichier
    def attach_file(filepath: str):
        filename = Path(filepath).name
        
        with open(filepath, "rb") as f:
            part = MIMEBase("application", "octet-stream")
            part.set_payload(f.read())
        
        # Encode en base64 pour le transport email
        encoders.encode_base64(part)
        part.add_header(
            "Content-Disposition",
            f"attachment; filename={filename}"
        )
        message.attach(part)
        print(f"  ✓ Pièce jointe : {filename}")
    
    # On attache les deux fichiers
    attach_file(cv_path)
    attach_file(letter_path)
    
    # Gmail API attend le message encodé en base64
    raw = base64.urlsafe_b64encode(message.as_bytes()).decode()
    return {"raw": raw}


def send_application(
    job        : dict,
    cv_path    : str,
    letter_path: str,
    sender_email: str,
    recruiter_email: str = None
) -> bool:
    """
    Envoie la candidature complète pour un job donné.
    
    Si recruiter_email est None → on s'envoie à soi-même pour tester
    Retourne True si envoi réussi, False sinon.
    """
    
    service = get_gmail_service()
    
    # Destinataire : recruteur si connu, sinon on s'envoie à soi-même
    to = recruiter_email if recruiter_email else sender_email
    
    subject = f"Candidature — {job['title']} | {job['title'].split()[0]} Engineer"
    
    # Corps du mail sobre et professionnel
    body = f"""Madame, Monsieur,

Veuillez trouver ci-joint mon CV et ma lettre de motivation pour le poste de {job['title']}.

Je reste disponible pour tout entretien à votre convenance.

Cordialement,
Oussama Maache
+212767389825
om7.oussama@gmail.com
linkedin.com/in/oussama-maache
"""
    
    print(f"\nPréparation de l'email pour {job['company']}...")
    
    email_message = build_email(
        to          = to,
        subject     = subject,
        body        = body,
        cv_path     = cv_path,
        letter_path = letter_path,
        sender      = sender_email
    )
    
    try:
        service.users().messages().send(
            userId="me",
            body=email_message
        ).execute()
        
        print(f"✓ Email envoyé à {to}")
        return True
    
    except Exception as e:
        print(f"✗ Erreur envoi : {e}")
        return False


def send_all_approved(approved_jobs: list, generated: dict, sender_email: str) -> list:
    """
    Envoie toutes les candidatures approuvées.
    Retourne la liste des résultats.
    
    approved_jobs : liste des jobs avec decision == "approved"
    generated     : dict { job_id: { cv: path, letter: path } }
    """
    
    results = []
    
    for job in approved_jobs:
        jid   = job["id"]
        files = generated.get(jid, {})
        
        if not files:
            print(f"⚠ Pas de documents générés pour {job['company']} — skipped")
            continue
        
        success = send_application(
            job             = job,
            cv_path         = files["cv"],
            letter_path     = files["letter"],
            sender_email    = sender_email,
        )
        
        results.append({
            "company": job["company"],
            "title"  : job["title"],
            "success": success
        })
    
    return results


# Test direct
if __name__ == "__main__":
    # Charge la première offre analysée
    import json
    with open("data/jobs_analyzed.json", "r") as f:
        jobs = json.load(f)
    
    job = jobs[0]
    
    # Simule des fichiers générés
    test_files = {
        job["id"]: {
            "cv"    : f"output/CV_Oussama_{job['company'].replace(' ', '_')}.docx",
            "letter": f"output/LM_Oussama_{job['company'].replace(' ', '_')}.docx"
        }
    }
    
    results = send_all_approved(
        approved_jobs = [job],
        generated     = test_files,
        sender_email  = "om7.oussama@gmail.com"
    )
    
    print("\n--- Résultats ---")
    for r in results:
        status = "✓" if r["success"] else "✗"
        print(f"{status} {r['company']} — {r['title']}")