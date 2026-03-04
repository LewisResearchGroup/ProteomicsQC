import os
import hashlib
import shutil
import uuid
import re

from pathlib import Path as P

from django.db import models
from django_currentuser.db.models import CurrentUserField
from django.template.defaultfilters import slugify
from django.dispatch import receiver
from django.utils import timezone
from django.conf import settings
from django.utils.translation import gettext_lazy as _
from django.utils.html import mark_safe

from .Result import Result

from .validators import validate_file_is_rawfile


DATALAKE_ROOT = settings.DATALAKE_ROOT
DATALAKE = settings.DATALAKE
COMPUTE_ROOT = settings.COMPUTE_ROOT
COMPUTE = settings.COMPUTE


class RawFile(models.Model):
    # use the custom storage class fo the FileField

    created_by = CurrentUserField()

    created = models.DateField(default=timezone.now)

    pipeline = models.ForeignKey(
        "Pipeline", on_delete=models.CASCADE, null=False, default=1
    )

    md5sum = models.CharField(max_length=36, default=timezone.now, unique=False)

    valid_extensions = [".raw", ".RAW"]

    orig_file = models.FileField(
        upload_to="upload",
        storage=DATALAKE,
        max_length=1000,
        unique=False,
        validators=[validate_file_is_rawfile],
    )

    slug = models.SlugField(max_length=250, null=True, blank=True)

    flagged = models.BooleanField(default=False)

    use_downstream = models.BooleanField(default=None, null=True, blank=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["orig_file", "pipeline", "created_by"],
                condition=models.Q(created_by__isnull=False),
                name="rawfile_unique_owned_upload",
            ),
            models.UniqueConstraint(
                fields=["orig_file", "pipeline"],
                condition=models.Q(created_by__isnull=True),
                name="rawfile_unique_null_owner_upload",
            ),
        ]
        verbose_name = _("RawFile")
        verbose_name_plural = _("RawFiles")

    def save(self, *args, **kwargs):

        self.slug = slugify(self.name)

        if not self.pk:  # file is new
            md5 = hashlib.md5()
            for chunk in self.orig_file.chunks():
                md5.update(chunk)
            self.md5sum = md5.hexdigest()

        if not self.id:
            self.created = timezone.now()

        super(RawFile, self).save(*args, **kwargs)

    def __str__(self):
        return str(self.name)

    @property
    def name(self):
        return P(self.orig_file.name).name

    @property
    def logical_name(self):
        match = re.match(r"^[0-9a-f]{32}_(.+)$", self.name, re.IGNORECASE)
        if match:
            return match.group(1)
        return self.name

    @property
    def display_ref(self):
        if self.pk:
            return f"rf{self.pk}"
        return "rf?"

    @property
    def _legacy_path(self):
        return self.pipeline.input_path / P(self.name).with_suffix("").name / self.name

    @property
    def storage_scope(self):
        stem = slugify(P(self.name).with_suffix("").name) or "raw"
        uploader = self.created_by_id or 0
        if self.pk:
            return f"u{uploader}_rf{self.pk}_{stem}"
        if not hasattr(self, "_pending_storage_scope"):
            self._pending_storage_scope = f"u{uploader}_tmp{uuid.uuid4().hex[:12]}_{stem}"
        return self._pending_storage_scope

    @property
    def path(self):
        namespaced = self.pipeline.input_path / self.storage_scope / self.name
        legacy = self._legacy_path
        if getattr(self, "_force_namespaced_storage", False):
            return namespaced
        if namespaced.is_file():
            return namespaced
        if legacy.is_file():
            return legacy
        return namespaced

    @property
    def upload_path(self):
        return DATALAKE_ROOT / self.orig_file.name

    @property
    def filename(self):
        return self.path.with_suffix("")

    @property
    def rawtools_status(self):
        path = self.path.parent
        if (path / "QcDataTable.csv").is_file():
            return "Done"
        elif (path / "rawtools.txt").is_file():
            return "Running"
        return "New file"

    @property
    def href(self):
        return self.path

    @property
    def download(self):
        return mark_safe(f'<a href="{self.href}">Download</a>')

    def browse(self):
        return mark_safe(r'<a href="{}">Browse</a>'.format(self.href))

    browse.short_description = "Browse"

    def detail_view(self):
        return mark_safe(r'<a href="{}">Details</a>'.format(self.get_absolute_url))

    detail_view.short_description = "Details"

    def move_to_input_dir(self):
        src_path = self.upload_path
        trg_path = self.path
        os.makedirs(trg_path.parent, exist_ok=True)
        shutil.move(src_path, trg_path)
        # self.orig_file.path = trg_path

    @property
    def output_dir(self):
        namespaced = self.pipeline.output_path / self.storage_scope
        legacy = self.pipeline.output_path / self.name
        if getattr(self, "_force_namespaced_storage", False):
            return namespaced
        if self.pk and namespaced.is_dir():
            return namespaced
        if legacy.is_dir():
            return legacy
        return namespaced

    def make_output_dir(self):
        os.makedirs(self.output_dir, exist_ok=True)

    def submit(self):
        pass


@receiver(models.signals.post_save, sender=RawFile)
def move_rawfile_to_input_dir(sender, instance, created, *args, **kwargs):
    raw_file = instance
    if created:
        raw_file.move_to_input_dir()

    # create output directory
    raw_file.make_output_dir()

    # Create Results only if not present yet
    if getattr(raw_file, "_skip_auto_result", False):
        return
    if raw_file.pipeline.has_maxquant_config:
        if len(Result.objects.filter(raw_file=raw_file)) == 0:
            Result.objects.create(raw_file=raw_file, input_source="upload")


@receiver(models.signals.post_delete, sender=RawFile)
def delete_rawfile(sender, instance, *args, **kwargs):
    raw_file = instance
    if raw_file.path.is_file():
        os.remove(raw_file.path)
