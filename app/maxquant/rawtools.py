from django.db import models
from django_currentuser.db.models import CurrentUserField
from django.utils import timezone


class RawToolsSetup(models.Model):

    created_by = CurrentUserField()
    
    created = models.DateField(default=timezone.now)

    args = models.CharField(max_length=256, null=True, default='-p -q -x -u -l -m -r TMT11 -chro 12TB')
    
    pipeline = models.ForeignKey('MaxQuantPipeline', on_delete=models.SET_NULL, null=True)

    name = models.CharField(max_length=100, null=True, default='RawTools')

    def __str__(self):
        return self.name
