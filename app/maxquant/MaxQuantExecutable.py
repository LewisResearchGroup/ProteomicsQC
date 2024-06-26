import os
import hashlib
import shutil
import zipfile
import logging

from pathlib import Path as P

from django.db import models
from django.template.defaultfilters import slugify
from django.dispatch import receiver
from django.utils import timezone
from django.conf import settings
from django.utils.translation import gettext_lazy as _

DATALAKE_ROOT = settings.DATALAKE_ROOT
COMPUTE_ROOT = settings.COMPUTE_ROOT
COMPUTE = settings.COMPUTE


class MaxQuantExecutable(models.Model):
    class Meta:
        verbose_name = _("MaxQuant Version")
        verbose_name_plural = _("MaxQuant Versions")

    filename = models.FileField(
        upload_to="software/MaxQuant",
        storage=COMPUTE,
        max_length=1000,
        unique=True,
        help_text="Upload a zipped MaxQuant file (e.g. MaxQuant_1.6.10.43.zip)",
    )

    created = models.DateField(default=timezone.now)

    description = models.TextField(max_length=10000, default="")

    def __str__(self):
        return os.path.basename(str(self.filename).replace(".zip", ""))

    @property
    def path(self):
        fn = str(self.filename)
        return COMPUTE_ROOT / "software" / "MaxQuant" / P(fn).name

    def save(self, *args, **kwargs):
        logging.info("Save MQ bin")
        super(MaxQuantExecutable, self).save(*args, **kwargs)


@receiver(models.signals.post_save, sender=MaxQuantExecutable)
def unzip_maxquant(sender, instance, created, *args, **kwargs):
    "Unzip MaxQuant.zip"
    mq_bin = instance
    name = mq_bin.path
    tmp = mq_bin.path.with_suffix("")

    # If path is a file then unzip it.
    # Skip when it is a directory.
    if name.is_file():
        with zipfile.ZipFile(name, "r") as zip_ref:
            logging.info("Extracting zip archive:", name, tmp)
            zip_ref.extractall(tmp)
        os.remove(name)
        os.rename(tmp, name)


@receiver(models.signals.post_delete, sender=MaxQuantExecutable)
def remove_maxquant(sender, instance, *args, **kwargs):
    mq_bin = instance
    path = mq_bin.path
    if path.is_dir():
        shutil.rmtree(mq_bin.path)
