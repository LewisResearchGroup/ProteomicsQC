
from django.shortcuts import render
from django.http import HttpResponse
from django.contrib.auth.decorators import login_required
from django.conf import settings as conf_settings

@login_required
def home(request):
    context = {'home_title': conf_settings.HOME_TITLE}
    return render(request, 'home.html', context)