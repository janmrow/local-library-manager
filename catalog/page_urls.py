"""Browse page routes (slice 5: catalogue + account pages)."""

from django.urls import path
from django.views.generic import TemplateView

urlpatterns = [
    path("", TemplateView.as_view(template_name="catalog/book_list.html"), name="catalogue-page"),
    path("konto/", TemplateView.as_view(template_name="catalog/konto.html"), name="account-page"),
]
