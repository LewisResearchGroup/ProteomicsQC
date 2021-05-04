import os
import hashlib
import shutil
import zipfile

from pathlib import Path as P

from django.db import models, IntegrityError
from django_currentuser.db.models import CurrentUserField
from django.template.defaultfilters import slugify
from django.dispatch import receiver
from django.utils import timezone
from django.conf import settings
from django.shortcuts import render, reverse

from .MaxQuantResult import MaxQuantResult
from uuid import uuid4


DATALAKE_ROOT = settings.DATALAKE_ROOT
DATALAKE = settings.DATALAKE
COMPUTE_ROOT = settings.COMPUTE_ROOT
COMPUTE = settings.COMPUTE


class RawFile(models.Model):
    # use the custom storage class fo the FileField

    created_by = CurrentUserField()

    created = models.DateField(default=timezone.now)

    pipeline = models.ForeignKey('MaxQuantPipeline', on_delete=models.CASCADE, null=False, default=1)

    md5sum = models.CharField(max_length = 36, default = timezone.now, unique = False)

    orig_file = models.FileField(upload_to = 'upload', storage = DATALAKE, max_length = 1000, unique = False)

    slug = models.SlugField(max_length = 250, null=True, blank=True)

    flagged = models.BooleanField(default=False)

    use_downstream = models.BooleanField(default=True)


    class Meta:
        unique_together = ('orig_file', 'pipeline')   

    def save(self, *args, **kwargs):

        self.slug = slugify(self.name)

        if not self.pk:  # file is new
            md5 = hashlib.md5()
            for chunk in self.orig_file.chunks():
                md5.update(chunk)
            self.md5sum = md5.hexdigest()

        if not self.id:
            self.created = timezone.now()
        
        try:
            super(RawFile, self).save(*args, **kwargs) 
            
        except IntegrityError as e:
            print(e)
            pass
        
    def __str__(self):
        return str( self.name )
    
    @property
    def name(self):
        return P( self.orig_file.name ).name

    @property
    def path(self): 
        return self.pipeline.input_path /  P(self.name).with_suffix('').name / self.name

    @property
    def upload_path(self):
        return DATALAKE_ROOT / self.orig_file.name

    @property
    def filename(self):
        return self.path.with_suffix('')
    
    @property
    def rawtools_status(self):
        path = dirname(self.abs_path)
        if isfile('QcDataTable.csv'):
            return 'Done'
        elif isfile(join(path, 'rawtools.txt')):
            return 'Running'
        return 'New file'
    
    @property    
    def href(self):
        return os.path.dirname('/'+self.orig_file.name)
    
    def browse(self):
        return mark_safe(r'<a href="{}">Browse</a>'.format(self.href))

    browse.short_description = 'Browse'

    def detail_view(self):
        return mark_safe(r'<a href="{}">Details</a>'.format(self.get_absolute_url))
    detail_view.short_description = 'Details'

    def move_to_input_dir(self):
        src_path = (self.upload_path)
        trg_path = (self.path)
        os.makedirs(trg_path.parent, exist_ok=True)
        shutil.move(src_path, trg_path)
        #self.orig_file.path = trg_path
    
    @property
    def output_dir(self):
        return self.pipeline.output_path / self.name

    def submit(self):
        pass


@receiver(models.signals.post_save, sender=RawFile)
def move_rawfile_to_input_dir(sender, instance, created, *args, **kwargs):
    raw_file = instance
    if created:
        raw_file.move_to_input_dir()
        MaxQuantResult.objects.create(raw_file = raw_file )

@receiver(models.signals.post_delete, sender=RawFile)
def delete_rawfile(sender, instance, *args, **kwargs):
    raw_file = instance
    if raw_file.path.is_file():
        os.remove( raw_file.path )