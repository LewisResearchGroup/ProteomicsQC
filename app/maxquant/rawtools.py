from django.db import models
from django_currentuser.db.models import CurrentUserField
from django.utils import timezone


class RawToolsSetup(models.Model):

    created_by = CurrentUserField()
    
    created = models.DateField(default=timezone.now)

    name = models.CharField(max_length=100, null=True, default='RawTools')

    args = models.CharField(max_length=256, null=True, default='-p -q -x -u -l -m -r TMT11 -chro 12TB')
    
    pipeline = models.OneToOneField('MaxQuantPipeline', on_delete=models.CASCADE, null=True, parent_link=True)

    def __str__(self):
        return self.name
