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
from django.shortcuts import render, reverse

from uuid import uuid4


DATALAKE_ROOT = settings.DATALAKE_ROOT
COMPUTE_ROOT = settings.COMPUTE_ROOT
COMPUTE = settings.COMPUTE



class MaxQuantPipeline(models.Model):
    
    created_by = CurrentUserField()

    created = models.DateField(default=timezone.now)

    project = models.ForeignKey('project.Project', on_delete=models.PROTECT, null=True)

    name = models.CharField(max_length=100, unique=True, null=False)
    
    run_automatically = models.BooleanField(default=False)

    regular_expressions_filter = models.CharField(max_length=256, default='.*')

    maxquant_executable = models.FilePathField(path=str(COMPUTE_ROOT), 
        match=".*MaxQuantCmd.exe", recursive=True, null=True, blank=True)

    fasta_file = models.OneToOneField(
                    'FastaFile', 
                    on_delete=models.SET_DEFAULT, 
                    null=True, 
                    default='', 
                    parent_link=True)
    
    mqpar_file = models.OneToOneField(
                    'MaxQuantParameter', 
                    on_delete=models.SET_DEFAULT, 
                    null=True, 
                    default='', 
                    parent_link=True)
    
    slug = models.SlugField(max_length=256, unique=False, default=uuid4)

    uuid = models.CharField(max_length=36, default=uuid4)

    rawtools = models.OneToOneField('RawToolsSetup', on_delete=models.SET_NULL, null=True)

    def __str__(self):
        return self.name
    
    @property
    def tmp_dir(self):
         return f'{TMP_ROOT}/{self.project.slug}/{self.slug}'

    def save(self, *args, **kwargs):
        self.slug = slugify(self.name)
        return super().save(*args, **kwargs)

    def get_absolute_url(self):
        return reverse('pipeline-detail', kwargs={'pipeline': self.slug,
                                                  'project': self.project.slug}) 
    @property
    def path(self):
        return self.project.path / self._id

    @property
    def path_as_str(self):
        return str( self.path )

    @property
    def _id(self):
        return f'{self.project.id}MQ{self.pk}'

    @property
    def config_path(self):
        return self.path / 'config'

    @property
    def result_path(self):
        return self.path / 'result'

    @property
    def input_path(self):
        return self.path / 'inputs'

    @property
    def output_path(self):
        return self.path / 'output'

    @property
    def mqpar_path(self):
        return self.path / 'config' / 'mqpar.xml'

    @property
    def fasta_path(self):
        return self.path / 'config' / 'fasta.faa'

    @property
    def path_exists(self):
        return self.path.is_dir()

    @property
    def url(self):
        return reverse('maxquant:detail', kwargs={'project':  self.project.slug,
                                                  'pipeline': self.slug})

    @property
    def parquet_path(self):
        return self.path / 'parquet'



    #def args(self):
    #    return None

    #def pipeline_id(self):
    #    return None



@receiver(models.signals.post_save, sender=MaxQuantPipeline)
def create_maxquant_path(sender, instance, created, *args, **kwargs):
    mq_pipe = instance
    if created:
        os.makedirs( mq_pipe.path )
        os.makedirs( mq_pipe.config_path )
        os.makedirs( mq_pipe.result_path )
        os.makedirs( mq_pipe.input_path)
        os.makedirs( mq_pipe.output_path)


@receiver(models.signals.post_delete, sender=MaxQuantPipeline)
def delete_maxquant_path(sender, instance, *args, **kwargs):
    mq_pipe = instance
    if mq_pipe.path.is_dir():
        shutil.rmtree( mq_pipe.path )

