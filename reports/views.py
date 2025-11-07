from django.shortcuts import render
from django.http import JsonResponse
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer
from reportlab.lib.styles import getSampleStyleSheet,ParagraphStyle
from docx import Document
import google.generativeai as genai
import os
from django.conf import settings
import re
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import cm
from reportlab.pdfgen import canvas
import calendar
from datetime import datetime

# Configuration Gemini
genai.configure(api_key=os.getenv("GEMINI_API_KEY", "AIzaSyCBLgdFqqf0DVB5zhGcNTfPc8p8vN1CX2w"))

def clean_content(text):
    paragraphs = text.split("\n\n")
    if len(paragraphs) > 2:
        paragraphs = paragraphs[2:]  # garder à partir du 3ème paragraphe
    text = "\n\n".join(paragraphs) 
    text = re.sub(r"\n{3,}", "\n\n", text) 
    text = re.sub(r"[---]", "", text) 
    text = re.sub(r"[*#_]", "", text) 
    text = re.sub(r"[|]", "", text)
    text = re.sub(r"[::]", "", text)
    return text.strip()

def add_page_number(canvas, doc, logo_path='C:/Users/dell/myproject/media/reports/logo.jpeg'): 
    canvas.saveState() # Pied de page : numéro de page 
    page_num = f"Page {doc.page}" 
    canvas.setFont('Helvetica', 9) 
    canvas.drawRightString(A4[0] - 2*cm, 1.2*cm, page_num)
    if logo_path and os.path.exists(logo_path):
        canvas.drawImage(logo_path, 2*cm, A4[1] - 3*cm, width=3*cm, height=2*cm, preserveAspectRatio=True) 
    canvas.setFont('Helvetica-Bold', 14) 
    canvas.restoreState()

def get_temp_data():
    """Jeu de données temporaire (janvier-février 2025)"""
    sites = [{"id": 1, "nom": "Casablanca Plant", "societe": "Innovatech Solutions", "region": "Grand Casablanca"}]

    energie = [
        {"site_id": 1, "annee": 2025, "mois": "Janvier",  "type": "Électricité", "unite": "kWh", "valeur": 15800},
        {"site_id": 1, "annee": 2025, "mois": "Février", "type": "Électricité", "unite": "kWh", "valeur": 15000},
    ]

    eau = [
        {"site_id": 1, "annee": 2025, "mois": "Janvier", "famille_culture": "Tomate", "variete": "Cerise", "eau_m3": 3500},
        {"site_id": 1, "annee": 2025, "mois": "Février", "famille_culture": "Tomate", "variete": "Cerise", "eau_m3": 3400},
    ]

    dechets = [
        {"site_id": 1, "annee": 2025, "mois": "Janvier", "categorie_dechets": "Plastique", "unite": "kg", "valeur": 480},
        {"site_id": 1, "annee": 2025, "mois": "Février", "categorie_dechets": "Métal", "unite": "kg", "valeur": 320},
    ]

    social = [
        {"site_id": 1, "annee": 2025, "mois": "Janvier", "action": "Formation sécurité", "budget": 2500, "nb": 40},
        {"site_id": 1, "annee": 2025, "mois": "Février", "action": "Don de sang", "budget": 1800, "nb": 60},
    ]

    production = [
        {"site_id": 1, "annee": 2025, "mois": "Janvier", "famille_culture": "Tomate", "variete": "Cerise", "sup_ha": 12, "prod_kg": 26500},
        {"site_id": 1, "annee": 2025, "mois": "Février", "famille_culture": "Tomate", "variete": "Cerise", "sup_ha": 12, "prod_kg": 28000},
    ]

    return {"sites": sites, "energie": energie, "eau": eau, "dechets": dechets, "social": social, "production": production}


def generate_report(request):
    if request.method == "POST":
        report_type = request.POST.get("report_type")
        referentiel = request.POST.get("referentiel")
        filters = request.POST.get("filters")
        start_str = request.POST.get("start")
        end_str = request.POST.get("end")

        try:
            start_date = datetime.strptime(start_str, "%Y-%m")
            end_year, end_month = map(int, end_str.split('-'))
            last_day = calendar.monthrange(end_year, end_month)[1]
            end_date = datetime(end_year, end_month, last_day)
        except Exception as e:
            return JsonResponse({"error": f"Format de date invalide: {str(e)}"}, status=400)

        try:
            data = get_temp_data()

            # --- Création du résumé pour le prompt ---
            summary_lines = ["Synthèse des données (janvier-février 2025) :"]
            for site in data["sites"]:
                sid = site["id"]
                sname = site["nom"]

                e_jan = sum(e["valeur"] for e in data["energie"] if e["site_id"]==sid and e["mois"]=="Janvier")
                e_fev = sum(e["valeur"] for e in data["energie"] if e["site_id"]==sid and e["mois"]=="Février")
                w_jan = sum(w["eau_m3"] for w in data["eau"] if w["site_id"]==sid and w["mois"]=="Janvier")
                w_fev = sum(w["eau_m3"] for w in data["eau"] if w["site_id"]==sid and w["mois"]=="Février")
                d_jan = sum(d["valeur"] for d in data["dechets"] if d["site_id"]==sid and d["mois"]=="Janvier")
                d_fev = sum(d["valeur"] for d in data["dechets"] if d["site_id"]==sid and d["mois"]=="Février")
                p_jan = sum(p["prod_kg"] for p in data["production"] if p["site_id"]==sid and p["mois"]=="Janvier")
                p_fev = sum(p["prod_kg"] for p in data["production"] if p["site_id"]==sid and p["mois"]=="Février")

                summary_lines.append(f"- {sname} : énergie (kWh) — Jan: {e_jan}, Fév: {e_fev}")
                summary_lines.append(f"  Production (kg) — Jan: {p_jan}, Fév: {p_fev}")
                summary_lines.append(f"  Eau (m³) — Jan: {w_jan}, Fév: {w_fev}")
                summary_lines.append(f"  Déchets (kg) — Jan: {d_jan}, Fév: {d_fev}")

            data_summary = "\n".join(summary_lines)

            # --- Génération avec Gemini ---
            model = genai.GenerativeModel("gemini-2.5-pro")
            if report_type == "extra-financier":
                prompt = f"""
                Tu es un rédacteur expert RSE. Rédige un rapport extra-financier conforme au référentiel {referentiel} 
                pour la période {start_date.strftime('%B %Y')} à {end_date.strftime('%B %Y')}. 
                Inclut les titres suivants :
                       - Résumé exécutif (100-150 mots) 
                       - Méthodologie (sources de données) 
                       - Section Environnement (KPIs, analyse) 
                       - Section Social (KPIs, actions) 
                       - Gouvernance 
                       - Alignement avec les Objectifs de Développement Durable (ODD)
                       - Recommandations
                Format : sections avec titres.
                Données : {data_summary}
                """
            else:
                prompt = f"""
                Rédige un rapport RSE pour les indicateurs {filters}, entre {start_date.strftime('%B %Y')} et {end_date.strftime('%B %Y')}.
                Données : {data_summary}
                """

            response = model.generate_content(prompt)
            content = clean_content(response.text.strip())
            if not content:
                content = "Pas de contenu généré par Gemini."

        except Exception as e:
            return JsonResponse({"error": f"Erreur Gemini : {str(e)}"}, status=500)

        # --- Répertoire de sortie ---
        output_dir = os.path.join(settings.MEDIA_ROOT, "reports")
        os.makedirs(output_dir, exist_ok=True)
        base_name = f"{report_type}_{start_str}_{end_str}".replace(" ", "_")

        # --- Styles PDF ---
        styles = getSampleStyleSheet()
        title_style = ParagraphStyle(name="Title", fontSize=16, leading=18, spaceBefore=12, spaceAfter=12, textColor="#1F4E79", bold=True)
        normal_style = styles["Normal"]

        # --- Création PDF ---
        pdf_path = os.path.join(output_dir, f"{base_name}.pdf")
        doc = SimpleDocTemplate(pdf_path, pagesize=A4, rightMargin=2*cm, leftMargin=2*cm, topMargin=3*cm, bottomMargin=2*cm)
        elements = []
        title_keywords = ['résumé exécutif', 'méthodologie', 'section social', 'section environnement','gouvernance', 'alignement avec les objectifs de développement durable (odd)', 'recommandations']

        for sec in content.split("\n\n"):
            sec = sec.strip()
            if not sec:
                continue
            if any(sec.lower().startswith(k) for k in title_keywords):
                elements.append(Paragraph(sec, title_style))
            else:
                elements.append(Paragraph(sec, normal_style))
            elements.append(Spacer(1, 12))

        doc.build(elements, onFirstPage=lambda c,d: add_page_number(c,d),
                  onLaterPages=lambda c,d: add_page_number(c,d))


        # --- Création Word ---
        word_path = os.path.join(output_dir, f"{base_name}.docx")
        document = Document()
        for line in content.split("\n\n"):
            line_strip = line.strip()
            if not line_strip:
                continue
            if any(line_strip.lower().startswith(k) for k in title_keywords):
                document.add_heading(line_strip, level=2)
            else:
                document.add_paragraph(line_strip, style="Normal")
        document.save(word_path)
        # --- Création TXT ---
        txt_path = os.path.join(output_dir, f"{base_name}.txt")
        with open(txt_path, "w", encoding="utf-8") as f:
            f.write(content)

        # --- URLs ---
        pdf_url = f"{settings.MEDIA_URL}reports/{base_name}.pdf"
        word_url = f"{settings.MEDIA_URL}reports/{base_name}.docx"
        txt_url = f"{settings.MEDIA_URL}reports/{base_name}.txt"

        return JsonResponse({
            "pdf_url": pdf_url,
            "word_url": word_url,
            "txt_url": txt_url
        })

    return render(request, "reports/generate_report.html")
