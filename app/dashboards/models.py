from django.db import models
from .dashboards.dashboard.index import app as dashboard


class StatelessProteomicsDashboardApp(models.Model):
    """
    A stateless Dash app.

    An instance of this model represents a dash app without any specific state
    """

    app_name = models.CharField(max_length=100, blank=False, null=False, unique=True)
    slug = models.SlugField(max_length=110, unique=True, blank=True)

    def as_dash_app(self):
        return dashboard()
