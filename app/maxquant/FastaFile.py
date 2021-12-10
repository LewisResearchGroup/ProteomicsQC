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
from django.utils.html import mark_safe

from uuid import uuid4


DATALAKE_ROOT = settings.DATALAKE_ROOT
COMPUTE_ROOT = settings.COMPUTE_ROOT
COMPUTE = settings.COMPUTE


class FastaFile(models.Model):

    fasta_file_id = models.AutoField(primary_key=True)

    fasta_file = models.FileField(
        upload_to="uploads",
        storage=settings.COMPUTE,
        max_length=1000,
        help_text="Fasta file to use with MaxQuant. If this is changed all MaxQuant jobs in this pipeline should be rerun. Note: The link above does not work.",
    )

    def __str__(self):
        return self.fasta_name

    @property
    def fasta_name(self):
        return self.fasta_file.name

    @property
    def fasta_path(self):
        return self.pipeline.fasta_path

    def move_fasta_to_config(self):
        src_path = self.fasta_file.path
        trg_path = self.fasta_path
        if P(src_path).is_file():
            os.makedirs(trg_path.parent, exist_ok=True)
            shutil.move(src_path, trg_path)
        else:
            pass

    @property
    def fasta_href(self):
        return self.fasta_path

    @property
    def download_fasta(self):
        return mark_safe(
            '<a href="{0}" download>Download Fasta</a>'.format(self.fasta_href)
        )
