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
from uuid import uuid4


DATALAKE_ROOT = settings.DATALAKE_ROOT
COMPUTE_ROOT = settings.COMPUTE_ROOT
COMPUTE = settings.COMPUTE




class FastaFile(models.Model):

    created_by = CurrentUserField()

    pipeline = models.OneToOneField(
                        'MaxQuantPipeline', 
                        on_delete=models.CASCADE, 
                        null=True, 
                        parent_link=False)

    filename = models.FileField(
                upload_to  = 'uploads', 
                storage    = settings.COMPUTE, 
                max_length = 3000)
    
    md5sum = models.CharField(
                max_length = 36, 
                default    = 'Not calculated', 
                unique     = False)
    
    created = models.DateField(default=timezone.now)
    
    description = models.TextField(max_length = 500, default = 'No description')

    def save(self, *args, **kwargs):
        if not self.pk:  # file is new
            md5 = hashlib.md5()
            for chunk in self.filename.chunks():
                md5.update(chunk)
            self.md5sum = md5.hexdigest()
        if not self.id:
            self.created = timezone.now()

        super(FastaFile, self).save(*args, **kwargs) 
        
    def __str__(self):
        return self.name
    
    @property
    def name(self):
        return self.filename.name

    @property
    def path(self): 
        return self.pipeline.fasta_path

    @property
    def project_id(self):
        return None

    def move_to_config(self):
        src_path = (self.filename.path)
        trg_path = (self.path)
        os.makedirs(trg_path.parent, exist_ok=True)
        shutil.move(src_path, trg_path)


@receiver(models.signals.post_save, sender=FastaFile)
def move_fasta_to_config(sender, instance, created, *args, **kwargs):
    config_file = instance
    config_file.move_to_config()


