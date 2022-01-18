from tkinter.messagebox import YES
from django.test import TestCase
from project.models import Project
from maxquant.models import MaxQuantPipeline as Pipeline

from pathlib import Path as P



class PipelineTestCase(TestCase):
    def setUp(self):
        Project.objects.create(name='test-pipeline', description='a test project')
        project = Project.objects.get(name='test-pipeline')
        Pipeline.objects.create(name='test', project=project)
    
    def test__pipeline_creation(self):
        project = Project.objects.get(name='test-pipeline')
        pipeline = Pipeline.objects.get(name='test', project=project.pk)
        assert pipeline is not None, pipeline