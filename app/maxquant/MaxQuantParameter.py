
import os
import hashlib
import shutil
import zipfile

from pathlib import Path as P

from django.db import models
from django_currentuser.db.models import CurrentUserField
from django.template.defaultfilters import slugify
from django.dispatch import receiver
from django.utils import timezone
from django.conf import settings 
from django.utils.translation import ugettext_lazy as _

from uuid import uuid4


class MaxQuantParameter(models.Model):

    class Meta:
            verbose_name = _("MaxQuant Parameter")
            verbose_name_plural = _("MaxQuant Parameters")

    mqpar_id = models.AutoField(primary_key=True)

    mqpar_file = models.FileField(
                upload_to  = 'uploads', 
                storage    = settings.COMPUTE, 
                max_length = 3000)
        
    def __str__(self):
        if self.mqpar_path is None:
            return 'NO FILE'
        return self.mqpar_path.name

    @property
    def mqpar_path(self): 
        if self.pipeline is None:
            return None
        return self.pipeline.mqpar_path

    def move_mqpar_to_config(self):
        src_path = (self.mqpar_file.path)
        trg_path = (self.mqpar_path)
        if P(src_path).is_file():
            os.makedirs(trg_path.parent, exist_ok=True)
            shutil.move(src_path, trg_path)
        else:
            pass

    @property
    def href(self):
        return self.mqpar_path

    @property
    def download_mqpar(self):
        print(self.href)
        return mark_safe('<a href="{0}" download>Download mqpar.xml</a>'.format(self.href))

