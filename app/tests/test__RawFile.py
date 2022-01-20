from django.test import TestCase
from project.models import Project
from maxquant.models import MaxQuantPipeline as Pipeline
from maxquant.models import MaxQuantResult as Result

from maxquant.models import RawFile

from pathlib import Path as P
from glob import glob

from django.core.files.uploadedfile import SimpleUploadedFile
from celery.contrib.testing.worker import start_worker

import time

from maxquant import tasks
from main.celery import app


class RawFileTestCase(TestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.celery_worker = start_worker(app)
        cls.celery_worker.__enter__()

    def setUp(self):
        if not hasattr(self, "pipeline"):
            print("Setup")
            self.project = Project.objects.create(
                name="project", description="A test project"
            )

            fn_mqpar = P("tests/data/D01/TMT11.xml")
            fn_fasta = P("tests/data/D01/minimal.fasta")

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

    def test__raw_file_exists(self):
        assert self.raw_file.path.is_file(), self.raw_file.path

    def test__rawfile_output_dir_created(self):
        path = self.raw_file.output_dir
        files = glob(f"{self.raw_file.pipeline.path}/**/*", recursive=True)
        files.sort()
        assert path.is_dir(), f"{path} NOT IN:\n\t" + "\n\t".join(files)

    def test__maxquant_results_created(self):
        result = Result.objects.get(raw_file=self.raw_file)
        assert result is not None, result
