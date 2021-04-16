from django.urls import path, include
from .views import proteomics_dashboard_view

urlpatterns = [
    path('', proteomics_dashboard_view, name='primary_dashboard'),
    path('django_plotly_dash/', include('django_plotly_dash.urls')),    
]
