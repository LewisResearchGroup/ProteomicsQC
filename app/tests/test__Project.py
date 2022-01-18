from tkinter.messagebox import YES
from django.test import TestCase
from project.models import Project
from pathlib import Path as P

class ProjectTestCase(TestCase):
    def setUp(self):
        Project.objects.create(name='test', description='a test project')
    
    def test_project_created(self):
        project = Project.objects.get(name='test')
        url = project.url
        slug = project.slug
        assert url == f'/P/d/{slug}', url

    def test_path_is_pathlib_object(self):
        project = Project.objects.get(name='test')
        path = project.path
        assert isinstance(path, P), type(path)

    def test_path_exists(self):
        project = Project.objects.get(name='test')
        path = project.path
        assert path.is_dir()


    