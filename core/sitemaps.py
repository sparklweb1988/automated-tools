# sitemaps.py

from django.contrib.sitemaps import Sitemap
from django.urls import reverse

class StaticViewSitemap(Sitemap):
    def items(self):
        # List the names of views you want to include in the sitemap
        return ['upload', 'about', 'terms', 'privacy', 'contact']
    
    def location(self, item):
        # Generate the URLs for each of the view names
        return reverse(item)
    
    def lastmod(self, obj):
        # Optionally add a "last modified" date, for example:
        # You can modify this to return the last modification date for each page
        return None

    def priority(self, obj):
        # Optionally set a priority for the URL (from 0.0 to 1.0)
        return 0.5
    
    def changefreq(self, obj):
        # Optionally specify how often the page is likely to change
        return 'monthly'
