from django.shortcuts import render
from .plotly_dash import plotly_app

# Create your views here.

def dashboard(request):

    return render(request,'dashboard.html',{})