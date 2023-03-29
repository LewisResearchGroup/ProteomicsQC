from django.shortcuts import render
from django.http import HttpResponse
from django.conf import settings as conf_settings


def home(request):
    context = {"home_title": conf_settings.HOME_TITLE}
    return render(request, "home.html", context)
