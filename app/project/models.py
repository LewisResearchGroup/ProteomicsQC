# /pipelines/projects/models.py

import os
import shutil

from pathlib import Path as P

from django.db import models
from django.template.defaultfilters import slugify
from django.dispatch import receiver
from django.conf import settings
from django.urls import reverse, reverse_lazy

from django_currentuser.db.models import CurrentUserField

from user.models import User

DATALAKE_ROOT = settings.DATALAKE_ROOT


class Project(models.Model):

    project_id = models.AutoField(primary_key=True)
    name = models.CharField(max_length=256, unique=True, blank=False)
    created = models.DateTimeField(auto_now_add=True)
    description = models.TextField(max_length=10000, default="")
    slug = models.SlugField(max_length=256, unique=True)
    created_by = CurrentUserField(related_name="creator")
    users = models.ManyToManyField(User, related_name="users", blank=True)

    def __str__(self):
        return self.name

    def save(self, *args, **kwargs):
        self.slug = slugify(self.name)
        return super().save(*args, **kwargs)

    @property
    def url(self):
        return reverse_lazy("project:detail", kwargs={"slug": self.slug})

    @property
    def id(self):
        return f"P{self.pk}"

    @property
    def path(self):
        path = DATALAKE_ROOT / "P" / self.id
        return path

    @property
    def path_exists(self):
        return self.path.is_dir()


@receiver(models.signals.post_save, sender=Project)
def create_project_path(sender, instance, created, *args, **kwargs):
    project = instance
    if created:
        os.makedirs(project.path)


@receiver(models.signals.post_delete, sender=Project)
def delete_project_path(sender, instance, *args, **kwargs):
    project = instance
    if project.path.is_dir():
        shutil.rmtree(project.path)
