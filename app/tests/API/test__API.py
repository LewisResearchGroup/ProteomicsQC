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

URL = "http://localhost:8000"



class ApiTestCase(TestCase):

    def setUp(self):
        if not hasattr(self, "pipeline"):
            print("Setup")
            self.project = Project.objects.create(
                name="project", description="A test project"
            )

            fn_mqpar = P("tests/data/TMT11.xml")
            fn_fasta = P("tests/data/minimal.fasta")

            contents_mqpar = fn_mqpar.read_bytes()
            contents_fasta = fn_fasta.read_bytes()

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
        url = f"{URL}/api/projects"
        actual = c.post(url).json()
        expected = [{'pk': 1, 'name': 'project', 'description': 'A test project', 'slug': 'project'}]
        assert actual == expected, actual
