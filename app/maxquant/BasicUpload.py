from django.db import models
from django.conf import settings

class BasicUpload(models.Model):
    title = models.CharField(max_length=255, blank=True)
    orig_file = models.FileField(upload_to = 'upload/', storage = settings.DATALAKE)
    uploaded_at = models.DateTimeField(auto_now_add=True)
