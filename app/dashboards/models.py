from django.db import models
from .dashboards.proteomics_dashboard import app as proteomics_dashboard


class StatelessProteomicsDashboardApp(models.Model):
    """
    A stateless Dash app.

    An instance of this model represents a dash app without any specific state
    """

    app_name = models.CharField(max_length=100, blank=False, null=False, unique=True)
    slug = models.SlugField(max_length=110, unique=True, blank=True)

    def as_dash_app(self):
        return proteomics_dashboard()


class DashApp(models.Model):
    """
    An instance of this model represents a Dash application and its internal state
    """

    stateless_app = models.ForeignKey(
        StatelessProteomicsDashboardApp,
        on_delete=models.PROTECT,
        unique=False,
        null=False,
        blank=False,
    )
    instance_name = models.CharField(
        max_length=100, unique=True, blank=True, null=False
    )
    slug = models.SlugField(max_length=110, unique=True, blank=True)
    base_state = models.TextField(null=False, default="{}")
    creation = models.DateTimeField(auto_now_add=True)
    update = models.DateTimeField(auto_now=True)
    save_on_change = models.BooleanField(null=False, default=False)

    def current_state(self):
        """
        Return the current internal state of the model instance
        """
        pass

    def update_current_state(self, wid, key, value):
        """
        Update the current internal state, ignorning non-tracked objects
        """
        pass

    def populate_values(self):
        """
        Add values from the underlying dash layout configuration
        """
        pass
