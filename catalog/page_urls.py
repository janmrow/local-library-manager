"""Browse page routes (slice 1: public catalogue at /)."""

from django.urls import path
from django.views.generic import TemplateView

urlpatterns = [
    path("", TemplateView.as_view(template_name="catalog/book_list.html"), name="catalogue-page"),
]
