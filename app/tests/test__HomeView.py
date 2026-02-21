from django.test import TestCase
from django.urls import reverse
from django.core.files.uploadedfile import SimpleUploadedFile

from user.models import User
from project.models import Project
from maxquant.models import Pipeline, RawFile, Result

class HomeViewTestCase(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            email="tester@example.com", password="pass1234"
        )
        self.project = Project.objects.create(
            name="Project 1", description="First project", created_by=self.user
        )
        
        contents_mqpar = b"<mqpar></mqpar>"
        contents_fasta = b">protein\nSEQUENCE"
        
        self.pipeline = Pipeline.objects.create(
            name="pipe1",
            project=self.project,
            created_by=self.user,
            fasta_file=SimpleUploadedFile("my_fasta.fasta", contents_fasta),
            mqpar_file=SimpleUploadedFile("my_mqpar.xml", contents_mqpar),
            rawtools_args="-p -q -x",
        )
        
        self.raw_file = RawFile.objects.create(
            pipeline=self.pipeline, 
            orig_file=SimpleUploadedFile("fake.raw", b"..."),
            created_by=self.user
        )
        self.result, _ = Result.objects.get_or_create(raw_file=self.raw_file)

    def test_home_renders_for_anonymous_user(self):
        url = reverse("home")
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)

    def test_home_renders_for_authenticated_user(self):
        self.client.force_login(self.user)
        url = reverse("home")
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context["project_count"], 1)
        self.assertEqual(response.context["pipeline_count"], 1)
        self.assertIn("quick_steps", response.context)
        
        # Verify quick steps are populated
        quick_steps = response.context["quick_steps"]
        self.assertEqual(len(quick_steps), 4)
        self.assertEqual(quick_steps[0]["title"], "Open projects")
