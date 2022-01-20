from django.test import TestCase
from project.models import Project
from maxquant.models import MaxQuantPipeline as Pipeline

from pathlib import Path as P
from django.core.files.uploadedfile import SimpleUploadedFile
from glob import glob


class PipelineTestCase(TestCase):
    def setUp(self):
        Project.objects.create(name="test-pipeline", description="a test project")
        project = Project.objects.get(name="test-pipeline")
        Pipeline.objects.create(name="test", project=project)

    def test__pipeline_creation(self):
        project = Project.objects.get(name="test-pipeline")
        pipeline = Pipeline.objects.get(name="test", project=project.pk)
        assert pipeline is not None, pipeline

    def test__pipeline_creation(self):
        project = Project.objects.get(name="test-pipeline")
        pipeline = Pipeline.objects.get(name="test", project=project.pk)
        assert pipeline is not None, pipeline


class PipelineTestCaseWithFiles(TestCase):
    def setUp(self):
        Project.objects.create(name="project", description="a test project")
        project = Project.objects.get(name="project")

        fn_mqpar = P("tests/data/D01/TMT11.xml")
        fn_fasta = P("tests/data/D01/minimal.fasta")

        contents_mqpar = fn_mqpar.read_bytes()
        contents_fasta = fn_fasta.read_bytes()

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
