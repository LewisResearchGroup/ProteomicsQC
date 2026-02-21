from django.test import TestCase
from project.models import Project
from maxquant.models import Pipeline

from pathlib import Path as P
from django.core.files.uploadedfile import SimpleUploadedFile


class PipelineTestCase(TestCase):
    def setUp(self):
        Project.objects.create(name="test-pipeline", description="a test project")
        project = Project.objects.get(name="test-pipeline")
        Pipeline.objects.create(name="test", project=project)

    def test__pipeline_creation(self):
        project = Project.objects.get(name="test-pipeline")
        pipeline = Pipeline.objects.get(name="test", project=project.pk)
        assert pipeline is not None, pipeline


class PipelineTestCaseWithFiles(TestCase):
    def setUp(self):
        Project.objects.create(name="project", description="a test project")
        project = Project.objects.get(name="project")

        contents_mqpar = b"<mqpar></mqpar>"
        contents_fasta = b">protein\nSEQUENCE"

        self.pipeline = Pipeline.objects.create(
            name="pipe",
            project=project,
            fasta_file=SimpleUploadedFile("my_fasta.fasta", contents_fasta),
            mqpar_file=SimpleUploadedFile("my_mqpar.xml", contents_mqpar),
        )

    def test__pipeline_mqpar_file_exists(self):
        assert self.pipeline.mqpar_path.is_file()

    def test__pipeline_fasta_file_exists(self):
        assert self.pipeline.fasta_path.is_file()

    def test__pipeline_has_maxquant_config(self):
        assert self.pipeline.has_maxquant_config
