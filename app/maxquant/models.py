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

## Upload MaxQuant versions        
class MaxQuantExecutable(models.Model):
    filename = models.FileField(upload_to='software/MaxQuant',
                                storage = COMPUTE)
    
    created = models.DateField(default = timezone.now)
        
    def __str__(self):
        return os.path.basename(str(self.filename).replace('.zip', ''))
    
    @property
    def path(self): 
        fn = str(self.filename)
        return COMPUTE_ROOT / 'software' / 'MaxQuant' / P( fn ).name
    
    def save(self, *args, **kwargs):
        print('Save MQ bin')
        super(MaxQuantExecutable, self).save(*args, **kwargs)
        

@receiver(models.signals.post_save, sender=MaxQuantExecutable)
def unzip_maxquant(sender, instance, created, *args, **kwargs):
    'Unzip MaxQuant.zip'
    mq_bin = instance
    name = mq_bin.path
    tmp = mq_bin.path.with_suffix('')

    assert name.is_file(), name

    with zipfile.ZipFile(name, 'r') as zip_ref:
        print('Extracting zip archive:', name, tmp)
        zip_ref.extractall(tmp)

    os.remove(name)
    os.rename(tmp, name)


@receiver(models.signals.post_delete, sender=MaxQuantExecutable)
def remove_maxquant(sender, instance, *args, **kwargs):
    'Remove MaxQuant directory'
    mq_bin = instance
    path = mq_bin.path
    if path.is_dir():
        shutil.rmtree(mq_bin.path)


class MaxQuantPipeline(models.Model):
    
    created_by = CurrentUserField()

    project = models.ForeignKey('project.Project', on_delete=models.PROTECT, null=True)

    name = models.CharField(max_length=100, unique=True, null=False)
    
    run_automatically = models.BooleanField(default=False)

    regular_expressions_filter = models.CharField(max_length=256, default='.*')

    maxquant_executable = models.FilePathField(path=str(COMPUTE_ROOT), match=".*MaxQuantCmd.exe", recursive=True)

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

    #rawtools_config = models.ForeignKey(RawToolsConfig, on_delete=models.PROTECT, null=True)


    def __str__(self):
        return self.name
    
    @property
    def tmp_directory(self):
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
    def _id(self):
        return f'{self.project.id}MQ{self.pk}'


    @property
    def config_path(self):
        return self.path / 'config'

    @property
    def result_path(self):
        return self.path / 'result'

    @property
    def mqpar_path(self):
        return self.path / 'config' / 'mqpar.xml'

    @property
    def fasta_path(self):
        return self.path / 'config' / 'fasta.faa'

    @property
    def path_exists(self):
        return self.path.is_dir()


@receiver(models.signals.post_save, sender=MaxQuantPipeline)
def create_maxquant_path(sender, instance, created, *args, **kwargs):
    mq_pipe = instance
    if created:
        os.makedirs( mq_pipe.path )
        os.makedirs( mq_pipe.config_path )
        os.makedirs( mq_pipe.result_path )


@receiver(models.signals.post_delete, sender=MaxQuantPipeline)
def delete_maxquant_path(sender, instance, *args, **kwargs):
    mq_pipe = instance
    if mq_pipe.path.is_dir():
        shutil.rmtree( mq_pipe.path )


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
def create_project_path(sender, instance, created, *args, **kwargs):
    config_file = instance
    config_file.move_to_config()



class MaxQuantParameter(models.Model):

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

        super(MaxQuantParameter, self).save(*args, **kwargs) 
        
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


@receiver(models.signals.post_save, sender=MaxQuantParameter)
def create_project_path(sender, instance, created, *args, **kwargs):
    config_file = instance
    config_file.move_to_config()