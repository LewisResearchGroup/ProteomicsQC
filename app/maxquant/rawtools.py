from django.db import models
from django_currentuser.db.models import CurrentUserField


class RawToolsSetup(models.Model):

    rawtools_setup_id = models.AutoField(primary_key=True)

    rawtools_args = models.CharField(
        max_length=256, null=True, default="-p -q -x -u -l -m -r TMT11 -chro 12TB"
    )

    def __str__(self):
        return self.rawtools_args
