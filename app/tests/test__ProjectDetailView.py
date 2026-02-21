from django.test import TestCase
from django.urls import reverse
from django.core.files.uploadedfile import SimpleUploadedFile

from user.models import User
from project.models import Project
from maxquant.models import Pipeline, RawFile

class ProjectDetailViewTestCase(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            email="tester@example.com", password="pass1234"
        )
        self.other_user = User.objects.create_user(
            email="other@example.com", password="pass5678"
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
        )
        
        self.raw_file = RawFile.objects.create(
            pipeline=self.pipeline, 
            orig_file=SimpleUploadedFile("fake.raw", b"..."),
            created_by=self.user
        )

    def test_project_detail_requires_login(self):
        url = reverse("project:detail", kwargs={"slug": self.project.slug})
        response = self.client.get(url)
        self.assertRedirects(response, f"/admin/login/?next={url}")

    def test_project_detail_access_for_owner(self):
        self.client.force_login(self.user)
        url = reverse("project:detail", kwargs={"slug": self.project.slug})
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        
        self.assertEqual(response.context["object"], self.project)
        # Verify passing correct pipelines downstream
        pipelines = response.context["maxquant_pipelines"]
        self.assertEqual(len(pipelines), 1)
        self.assertEqual(pipelines[0], self.pipeline)

    def test_project_detail_forbidden_for_non_member(self):
        self.client.force_login(self.other_user)
        url = reverse("project:detail", kwargs={"slug": self.project.slug})
        response = self.client.get(url)
        self.assertEqual(response.status_code, 403)
