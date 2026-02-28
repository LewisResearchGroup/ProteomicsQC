from django.test import TestCase
from project.models import Project
from maxquant.models import Pipeline

from maxquant.models import RawFile

from pathlib import Path as P

from django.core.files.uploadedfile import SimpleUploadedFile
from celery.contrib.testing.worker import start_worker

from maxquant import tasks
from main.celery import app

from django.test import Client
from user.models import User

URL = "http://localhost:8000"


class ApiTestCase(TestCase):
    def setUp(self):
        if not hasattr(self, "pipeline"):
            print("Setup")
            self.user = User.objects.create_user(
                email="testuser@example.com",
                password="testpass123",
            )

            self.project = Project.objects.create(
                name="project", description="A test project"
            )
            self.project.users.add(self.user)

            contents_mqpar = b"<mqpar></mqpar>"
            contents_fasta = b">protein\nSEQUENCE"

            self.pipeline = Pipeline.objects.create(
                name="pipe",
                project=self.project,
                fasta_file=SimpleUploadedFile("my_fasta.fasta", contents_fasta),
                mqpar_file=SimpleUploadedFile("my_mqpar.xml", contents_mqpar),
                rawtools_args="-p -q -x -u -l -m -r TMT11 -chro 12TB",
            )

            self.raw_file = RawFile.objects.create(
                pipeline=self.pipeline, orig_file=SimpleUploadedFile("fake.raw", b"...")
            )

    def test__projects(self):
        c = Client()
        c.force_login(self.user)
        url = f"{URL}/api/projects"
        actual = c.post(url).json()
        expected = [
            {
                "pk": 1,
                "name": "project",
                "description": "A test project",
                "slug": "project",
            }
        ]
        assert actual == expected, actual

    def test__projects_unauthenticated(self):
        """Verify that unauthenticated requests are rejected."""
        c = Client()
        url = f"{URL}/api/projects"
        response = c.post(url)
        assert response.status_code == 403, f"Expected 403, got {response.status_code}"
