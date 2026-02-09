import os
import uuid
import tempfile
from io import BytesIO

import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
import base64

from django.conf import settings
from django.contrib.auth.decorators import login_required
from django.http import (
    HttpResponse,
    FileResponse,
    HttpResponseBadRequest
)
from django.shortcuts import render, redirect
from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas
from reportlab.lib.utils import ImageReader

from io import BytesIO
from django.contrib.auth.models import User
from django.contrib.auth import authenticate, login
from django.contrib import messages
from django.utils import timezone
from django.contrib.auth import logout
import logging
from .models import Profile
from django.contrib.auth.decorators import login_required
from django.core.mail import send_mail

from docx import Document
from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas
from pdf2docx import Converter


# ---------------- UTILITIES ----------------
def clean_dataframe(df):
    df = df.dropna(axis=0, how="all")
    df = df.dropna(axis=1, how="all")

    df.columns = (
        df.columns.astype(str)
        .str.strip()
        .str.lower()
        .str.replace(" ", "_")
        .str.replace(r"[^0-9a-zA-Z_]", "", regex=True)
    )

    for col in df.select_dtypes(include=["object"]).columns:
        df[col] = df[col].astype(str).str.strip().str.replace(
            r"[^0-9a-zA-Z ]", "", regex=True
        )

    return df


def make_df_json_safe(df):
    for col in df.columns:
        if pd.api.types.is_datetime64_any_dtype(df[col]):
            df[col] = df[col].astype(str)
    return df


def find_duplicate_columns(df):
    duplicates = {}
    for col in df.columns:
        duplicates.setdefault(tuple(df[col].astype(str)), []).append(col)
    return {k: v for k, v in duplicates.items() if len(v) > 1}


# ---------------- DATA CLEANER ----------------
def upload_file(request):
    if request.method == "GET":
        return render(request, "upload.html")

    file = request.FILES.get("file")
    if not file:
        return render(request, "upload.html", {"error": "No file selected"})

    try:
        if file.name.endswith(".csv"):
            df = pd.read_csv(file)
        elif file.name.endswith((".xls", ".xlsx")):
            df = pd.read_excel(file)
        else:
            return render(request, "upload.html", {"error": "Unsupported file format"})
    except Exception as e:
        return render(request, "upload.html", {"error": str(e)})

    df = clean_dataframe(df)
    df = make_df_json_safe(df)

    duplicates = find_duplicate_columns(df)

    request.session["cleaned_df"] = df.to_dict(orient="list")

    # Prepare preview
    preview_rows = df.head(10).values.tolist()
    columns = df.columns.tolist()

    return render(request, "clean_duplicates.html", {
        "duplicates": duplicates,
        "preview_rows": preview_rows,
        "columns": columns,
        "allow_ignore_duplicates": True,
    })


# ---------------- STEP 2: REMOVE DUPLICATE COLUMNS ----------------
def remove_duplicates(request):
    if request.method != "POST":
        return redirect("upload")

    cleaned_df = request.session.get("cleaned_df")
    if not cleaned_df:
        return redirect("upload")

    df = pd.DataFrame(cleaned_df)

    if request.POST.get("ignore_duplicates"):
        pass
    else:
        remove_cols = request.POST.getlist("remove_columns")
        if remove_cols:
            df = df.drop(columns=remove_cols)

    request.session["cleaned_df"] = df.to_dict(orient="list")

    columns = df.columns.tolist()[:10]
    preview_rows = df[columns].head(10).values.tolist()

    return render(request, "download_cleaned.html", {
        "preview_rows": preview_rows,
        "columns": columns
    })


def download_cleaned_file(request):
    cleaned_df = request.session.get("cleaned_df")
    if not cleaned_df:
        return redirect("upload")

    df = pd.DataFrame(cleaned_df)
    df = df.fillna("NaN")
    df = df.replace(r'^\s*$', 'NaN', regex=True)

    csv_data = df.to_csv(index=False)
    response = HttpResponse(csv_data, content_type="text/csv")
    response["Content-Disposition"] = 'attachment; filename="cleaned_data.csv"'
    return response


def upload_visualization(request):
    if request.method == "GET":
        return render(request, "upload_visualization.html")

    file = request.FILES.get("file")
    if not file or not file.name.endswith(".csv"):
        return render(request, "upload_visualization.html", {"error": "Please upload a cleaned CSV file"})

    df = pd.read_csv(file)
    df = make_df_json_safe(df)

    request.session["viz_df"] = df.to_dict(orient="list")
    request.session["charts"] = []

    return render(request, "select_chart.html", {"columns": df.columns})


def generate_chart(request):
    if request.method != "POST":
        return redirect("upload_visualization")

    viz_df = request.session.get("viz_df")
    if not viz_df:
        return redirect("upload_visualization")

    df = pd.DataFrame(viz_df)

    x = request.POST.get("x_column")
    y = request.POST.get("y_column")
    chart_type = request.POST.get("chart_type")

    plt.figure(figsize=(20, 10))

    if chart_type == "bar":
        sns.barplot(x=x, y=y, data=df)
    elif chart_type == "line":
        sns.lineplot(x=x, y=y, data=df)
    elif chart_type == "scatter":
        sns.scatterplot(x=x, y=y, data=df)
    elif chart_type == "pie":
        df.groupby(x)[y].sum().plot(kind="pie", autopct="%1.1f%%")

    buf = BytesIO()
    plt.tight_layout()
    plt.savefig(buf, format="png")
    plt.close()

    img_base64 = base64.b64encode(buf.getvalue()).decode()

    charts = request.session.get("charts", [])
    charts.append(img_base64)
    request.session["charts"] = charts

    return render(request, "select_chart.html", {
        "columns": df.columns,
        "plots": charts
    })


def download_charts_excel(request):
    charts = request.session.get("charts")
    if not charts:
        return HttpResponse("No charts to export", status=400)

    output = BytesIO()

    with pd.ExcelWriter(output, engine="xlsxwriter") as writer:
        workbook = writer.book
        worksheet = workbook.add_worksheet("Charts")
        row = 0
        for chart in charts:
            image_data = base64.b64decode(chart)
            worksheet.insert_image(row, 0, "chart.png", {"image_data": BytesIO(image_data)})
            row += 20

    output.seek(0)

    response = HttpResponse(
        output,
        content_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )
    response["Content-Disposition"] = 'attachment; filename="visualizations.xlsx"'
    return response


def download_charts_pdf(request):
    charts = request.session.get("charts")
    if not charts:
        return HttpResponse("No charts to export", status=400)

    buffer = BytesIO()
    pdf = canvas.Canvas(buffer, pagesize=A4)

    page_width, page_height = A4
    margin = 40
    y_position = page_height - margin

    for chart in charts:
        image_data = base64.b64decode(chart)
        image = ImageReader(BytesIO(image_data))

        img_width = page_width - (2 * margin)
        img_height = img_width * 0.6

        if y_position - img_height < margin:
            pdf.showPage()
            y_position = page_height - margin

        pdf.drawImage(
            image,
            margin,
            y_position - img_height,
            width=img_width,
            height=img_height,
            preserveAspectRatio=True
        )

        y_position -= img_height + 20

    pdf.save()
    buffer.seek(0)

    response = HttpResponse(buffer, content_type="application/pdf")
    response["Content-Disposition"] = 'attachment; filename="visualizations.pdf"'
    return response


# ---------------- DOCUMENT CONVERTER (NO FILE SAVING) ----------------
def convert_docx_to_pdf_bytes(docx_bytes):
    doc = Document(BytesIO(docx_bytes))
    buffer = BytesIO()

    c = canvas.Canvas(buffer, pagesize=letter)
    width, height = letter
    y = height - 50

    for para in doc.paragraphs:
        c.drawString(50, y, para.text)
        y -= 15
        if y < 50:
            c.showPage()
            y = height - 50

    c.save()
    buffer.seek(0)
    return buffer


def convert_pdf_to_docx_bytes(pdf_bytes):
    with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as temp_pdf:
        temp_pdf.write(pdf_bytes)
        temp_pdf_path = temp_pdf.name

    temp_docx_path = temp_pdf_path.replace(".pdf", ".docx")
    cv = Converter(temp_pdf_path)
    cv.convert(temp_docx_path)
    cv.close()

    with open(temp_docx_path, "rb") as f:
        docx_bytes = f.read()

    os.remove(temp_pdf_path)
    os.remove(temp_docx_path)

    return BytesIO(docx_bytes)


def convert_document(request):
    return render(request, "converter.html")


def docx_to_pdf(request):
    if request.method != "POST":
        return HttpResponseBadRequest("POST request required")

    file = request.FILES.get("file")
    if not file or os.path.splitext(file.name)[1].lower() != ".docx":
        return HttpResponseBadRequest("Invalid DOCX file")

    output_name = os.path.splitext(file.name)[0] + ".pdf"
    pdf_bytes = convert_docx_to_pdf_bytes(file.read())

    return FileResponse(pdf_bytes, as_attachment=True, filename=output_name)


def pdf_to_docx(request):
    if request.method != "POST":
        return HttpResponseBadRequest("POST request required")

    file = request.FILES.get("file")
    if not file or os.path.splitext(file.name)[1].lower() != ".pdf":
        return HttpResponseBadRequest("Invalid PDF file")

    output_name = os.path.splitext(file.name)[0] + ".docx"
    docx_bytes = convert_pdf_to_docx_bytes(file.read())

    return FileResponse(docx_bytes, as_attachment=True, filename=output_name)


# PAGES
def about(request):
    return render(request, 'about.html')


def terms(request):
    return render(request, 'terms.html')


def privacy(request):
    return render(request, 'privacy.html')


def contact(request):
    return render(request, 'contact.html')


from django.contrib.sitemaps import Sitemap
from django.urls import reverse

class StaticViewSitemap(Sitemap):
    def items(self):
        return ['home', 'about', 'terms', 'privacy', 'contact']

    def location(self, item):
        return reverse(item)
