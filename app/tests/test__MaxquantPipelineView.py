from django.test import TestCase
from django.urls import reverse
from django.core.files.uploadedfile import SimpleUploadedFile

from user.models import User
from project.models import Project
from maxquant.models import Pipeline

class MaxquantPipelineViewTestCase(TestCase):
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
        )

    def test_pipeline_view_loads(self):
        self.client.force_login(self.user)
        url = reverse("maxquant:detail", kwargs={
            "project": self.project.slug,
            "pipeline": self.pipeline.slug
        })
        response = self.client.get(url)

        self.assertEqual(response.status_code, 200)
        self.assertIn("maxquant_runs", response.context)

    def test_pipeline_view_requires_login(self):
        """Verify pipeline view requires authentication."""
        url = reverse("maxquant:detail", kwargs={
            "project": self.project.slug,
            "pipeline": self.pipeline.slug
        })
        response = self.client.get(url)
        self.assertEqual(response.status_code, 302)
        self.assertIn("/admin/login/", response.url)

    def test_pipeline_view_unauthorized_user(self):
        """Verify users cannot view pipelines they don't have access to."""
        other_user = User.objects.create_user(
            email="other@example.com", password="pass1234"
        )
        self.client.force_login(other_user)
        url = reverse("maxquant:detail", kwargs={
            "project": self.project.slug,
            "pipeline": self.pipeline.slug
        })
        response = self.client.get(url)
        self.assertEqual(response.status_code, 404)
