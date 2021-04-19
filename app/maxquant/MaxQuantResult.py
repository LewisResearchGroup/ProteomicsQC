
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

from .tasks import rawtools_metrics, rawtools_qc, run_maxquant

DATALAKE_ROOT = settings.DATALAKE_ROOT
COMPUTE_ROOT = settings.COMPUTE_ROOT
COMPUTE = settings.COMPUTE



class MaxQuantResult(models.Model):

    raw_file = models.ForeignKey('RawFile', on_delete=models.CASCADE)
    
    @property
    def pipeline(self):
        return self.raw_file.pipeline

    def __str__(self):
        return self.name

    @property
    def name(self):
        return str( self.raw_file.name )

    @property
    def raw_fn(self):
        return self.raw_file.path
        
    @property
    def mqpar_fn(self):
        return self.pipeline.mqpar_path
    
    @property
    def fasta_fn(self):
        return self.pipeline.fasta_path
        
    @property
    def run_directory(self):
        return COMPUTE_ROOT / 'tmp'/ 'MaxQuant' / self.name

    @property
    def pipename(self):
        return self.pipeline.name
    
    @property
    def path(self):
        return self.raw_file.output_dir
   
    @property
    def maxquant_binary(self):
        return self.pipeline.maxquant_executable
    
    @property
    def output_directory_exists(self):
        return self.path.is_dir()
    
    @property
    def maxquantcmd(self):
        return 'maxquant'

    @property 
    def run_directory_exists(self):
        return self.run_directory.is_dir()

    @property
    def use_downstream(self):
        return self.raw_file.use_downstream

    def run(self, rerun=False):
        raw_file      = str( self.raw_fn )
        mqpar_file    = str( self.mqpar_fn ) 
        fasta_file    = str( self.fasta_fn )
        run_directory = str( self.run_directory )
        output_dir    = str( self.path )
        maxquantcmd   = self.maxquantcmd

        params = dict(
            maxquantcmd = maxquantcmd,
            mqpar_file = mqpar_file, 
            fasta_file = fasta_file, 
            run_dir = run_directory, 
            output_dir = output_dir,
        )
            
        run_maxquant.delay(raw_file, params)


@receiver(models.signals.post_save, sender=MaxQuantResult)
def run_maxquant_after_save(sender, instance, created, *args, **kwargs):
    instance.run()


@receiver(models.signals.post_delete, sender=MaxQuantResult)
def remove_maxquant_folders_after_delete(sender, instance, *args, **kwargs):
    if instance.output_directory_exists:
        shutil.rmtree(instance.path)
    if instance.run_directory_exists:
        shutil.rmtree(instance.path)
    