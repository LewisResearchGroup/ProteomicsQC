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
from django.utils.translation import ugettext_lazy as _

from uuid import uuid4

from .rawtools import RawToolsSetup
from .MaxQuantParameter import MaxQuantParameter
from .FastaFile import FastaFile


DATALAKE_ROOT = settings.DATALAKE_ROOT
COMPUTE_ROOT = settings.COMPUTE_ROOT
COMPUTE = settings.COMPUTE


class MaxQuantPipeline(MaxQuantParameter, FastaFile, RawToolsSetup):
    class Meta:
        verbose_name = _("MaxQuant Pipeline")
        verbose_name_plural = _("MaxQuant Pipelines")

    maxquant_pipepline_id = models.AutoField(primary_key=True)

    created_by = CurrentUserField()

    created = models.DateField(default=timezone.now)

    project = models.ForeignKey("project.Project", on_delete=models.PROTECT, null=True)

    name = models.CharField(max_length=500, unique=True, null=False)

    run_automatically = models.BooleanField(default=False)

    regular_expressions_filter = models.CharField(max_length=256, default=".*")

    maxquant_executable = models.FilePathField(
        path=str(COMPUTE_ROOT),
        match=".*MaxQuantCmd.exe",
        recursive=True,
        null=True,
        blank=True,
        max_length=2000,
        help_text="If this field is empty the default MaxQuant version (1.6.10.43) will be used. "
        "To try a different version go to MaxQuant Executables. If this is changed, "
        "all MaxQuant jobs in this pipeline should be rerun.",
    )

    slug = models.SlugField(max_length=500, unique=False, default=uuid4)

    uuid = models.CharField(
        max_length=36,
        default=uuid4,
        help_text="UID to use the pipeline with the Python API (in the lrg-omics package)",
    )

    description = models.TextField(max_length=1000, default="")

    def __str__(self):
        return self.name

    @property
    def tmp_dir(self):
        return f"{TMP_ROOT}/{self.project.slug}/{self.slug}"

    def save(self, *args, **kwargs):
        self.slug = slugify(self.name)
        return super().save(*args, **kwargs)

    def get_absolute_url(self):
        return reverse(
            "pipeline-detail",
            kwargs={"pipeline": self.slug, "project": self.project.slug},
        )

    @property
    def path(self):
        return self.project.path / self._id

    @property
    def path_as_str(self):
        return str(self.path)

    @property
    def _id(self):
        return f"{self.project.id}MQ{self.pk}"

    @property
    def config_path(self):
        return self.path / "config"

    @property
    def result_path(self):
        return self.path / "result"

    @property
    def input_path(self):
        return self.path / "inputs"

    @property
    def output_path(self):
        return self.path / "output"

    @property
    def mqpar_path(self):
        return self.path / "config" / "mqpar.xml"

    @property
    def fasta_path(self):
        return self.path / "config" / "fasta.faa"

    @property
    def path_exists(self):
        return self.path.is_dir()

    @property
    def url(self):
        return reverse(
            "maxquant:detail",
            kwargs={"project": self.project.slug, "pipeline": self.slug},
        )

    @property
    def parquet_path(self):
        return self.path / "parquet"


@receiver(models.signals.post_save, sender=MaxQuantPipeline)
def create_maxquant_path(sender, instance, created, *args, **kwargs):
    mq_pipe = instance

    if created:
        os.makedirs(mq_pipe.path)
        os.makedirs(mq_pipe.config_path)
        os.makedirs(mq_pipe.result_path)
        os.makedirs(mq_pipe.input_path)
        os.makedirs(mq_pipe.output_path)

    mq_pipe.move_fasta_to_config()
    mq_pipe.move_mqpar_to_config()


@receiver(models.signals.post_delete, sender=MaxQuantPipeline)
def delete_maxquant_path(sender, instance, *args, **kwargs):
    mq_pipe = instance
    if mq_pipe.path.is_dir():
        shutil.rmtree(mq_pipe.path)
