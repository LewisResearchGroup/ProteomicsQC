from django.shortcuts import render, redirect
from django.contrib.auth import authenticate, login
from django.conf import settings
from .forms import UserCreationForm


def index(request):
    context = {'home_title': settings.HOME_TITLE}
    return render(request, 'index.html', context)


def registration(request):
    if request.method == 'POST':
        form = UserCreationForm(request.POST)
        if form.is_valid():
            form.save()
            email = form.cleaned_data['email']
            password = form.cleaned_data['password1']
            user = authenticate(email=email, password=password)   
            login(request, user)
            return redirect('home')
    else:
        form = UserCreationForm()
    context = {'form': form, 'home_title': settings.HOME_TITLE}
    return render(request, 'registration/register.html', context)
