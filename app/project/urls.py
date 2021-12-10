from django.urls import path, re_path, include

from . import views

urlpatterns = [
    path("l/", views.ListView.as_view(), name="list"),
    path("d/<slug>", views.DetailView.as_view(), name="detail"),
]
