"""Browse page routes (slices 1-2: catalogue + account pages)."""

from django.urls import path
from django.views.generic import TemplateView

urlpatterns = [
    path("", TemplateView.as_view(template_name="catalog/book_list.html"), name="catalogue-page"),
    path("konto/", TemplateView.as_view(template_name="catalog/konto.html"), name="account-page"),
    path(
        "wypozyczenia/",
        TemplateView.as_view(template_name="catalog/wypozyczenia.html"),
        name="loans-page",
    ),
    path("panel/", TemplateView.as_view(template_name="catalog/panel.html"), name="staff-page"),
]
