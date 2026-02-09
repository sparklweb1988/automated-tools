from django.urls import path
from django.contrib.sitemaps.views import sitemap
from .sitemaps import StaticViewSitemap  # Import your Sitemap class
from django.contrib.auth import views as auth_views
from . import views




sitemaps = {
    'static': StaticViewSitemap,
}



urlpatterns = [
    # path('', views.home, name='home'),  # Add this line to map the root URL
    path('', views.upload_file, name="upload"),  # Change from '' to '/upload/'
    path('remove-duplicates/', views.remove_duplicates, name="remove_duplicates"),
    path('download/', views.download_cleaned_file, name="download_cleaned"),
    path('upload_visualization/', views.upload_visualization, name="upload_visualization"),
    path('generate_chart/', views.generate_chart, name="generate_chart"),
    path('visualization/download-excel/', views.download_charts_excel, name="download_charts_excel"),
    path('download/pdf/', views.download_charts_pdf, name='download_charts_pdf'),





    # CONVERTER
    path('convert/', views.convert_document, name='convert_document'),
    path('convert/docx-to-pdf/', views.docx_to_pdf, name='docx_to_pdf'),
    path('convert/pdf-to-docx/', views.pdf_to_docx, name='pdf_to_docx'),




    # PAGES
    
    path('about/', views.about, name='about'),  # About Us Page
    path('terms/', views.terms, name='terms'),  # Terms of Use Page
    path('privacy/', views.privacy, name='privacy'),  # Privacy Policy Page
    path('contact/', views.contact, name='contact'),  # Contact Us Page
    # path('sitemap/', views.sitemap, name='sitemap'),  # Added sitemap page URL
    path('sitemap.xml', sitemap, {'sitemaps': sitemaps}, name='sitemap'),

]
