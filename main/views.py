from django.shortcuts import render, redirect
from django.contrib.auth import authenticate, login, logout
from django.contrib import messages
from .forms import SignUpForm

# Create your views here.
def index(request):
    if request.user.is_authenticated:
        return render(request, "main/index.html")
    else:
        return redirect('login')

def login_user(request):
    if request.user.is_authenticated:
        messages.error(request, 'You are already logged in.')
        return redirect('index')
    if request.method == 'POST':
        username = request.POST['username']
        password = request.POST['password']
        user = authenticate(request, username=username, password=password)
        if user is not None:
            login(request, user)
            messages.success(request, 'Logged in successfully.')
            return redirect('index')
        else:
            messages.error(request, 'Invalid username or password. Please try again!')
            return render(request, "main/login.html", {'messages': messages})
    return render(request, "main/login.html", {'messages': messages})

def sign_up(request):
    form = SignUpForm()
    if request.method == 'POST':
        form = SignUpForm(request.POST or None)
        if form.is_valid():
            form.save()
            messages.success(request, 'Account created successfully.')
            return redirect('index')
        else:
            messages.error(request, 'Invalid username or password. Please try again!')
            return render(request, "main/signup.html", {'form': form})
    return render(request, "main/signup.html", {'form': form})

def logout_user(request):
    if request.user.is_authenticated:
        logout(request)
        messages.success(request, 'Logged out successfully.')
        return redirect('login')
    else:
        messages.error(request, 'You are not logged in. Please login to continue.')
        return redirect('login')