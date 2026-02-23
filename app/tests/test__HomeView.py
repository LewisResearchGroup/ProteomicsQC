from datetime import timedelta

from django.test import TestCase
from django.urls import reverse
from django.core.files.uploadedfile import SimpleUploadedFile
from django.utils import timezone

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
        self.assertIn("login_form", response.context)

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

    def test_home_post_logs_in_anonymous_user(self):
        url = reverse("home")
        response = self.client.post(
            url,
            data={"username": self.user.email, "password": "pass1234", "next": "/"},
        )
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.url, "/")
        self.assertTrue("_auth_user_id" in self.client.session)

    def test_login_url_redirects_to_home_inline_login(self):
        response = self.client.get(reverse("login"), {"next": "/dashboard/"})
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.url, "/?next=%2Fdashboard%2F")

    def test_quick_steps_use_last_activity_for_project_and_pipeline(self):
        self.client.force_login(self.user)

        project_recent_created = Project.objects.create(
            name="Project 2", description="Second project", created_by=self.user
        )
        old_project = self.project

        contents_mqpar = b"<mqpar></mqpar>"
        contents_fasta = b">protein\nSEQUENCE"
        old_pipeline = self.pipeline
        new_pipeline = Pipeline.objects.create(
            name="pipe2",
            project=project_recent_created,
            created_by=self.user,
            fasta_file=SimpleUploadedFile("my_fasta_2.fasta", contents_fasta),
            mqpar_file=SimpleUploadedFile("my_mqpar_2.xml", contents_mqpar),
            rawtools_args="-p -q -x",
        )

        RawFile.objects.create(
            pipeline=new_pipeline,
            orig_file=SimpleUploadedFile("newer_created.raw", b"..."),
            created_by=self.user,
        )

        old_project.created = timezone.now() - timedelta(days=10)
        old_project.save(update_fields=["created"])
        old_pipeline.created = old_project.created.date()
        old_pipeline.save(update_fields=["created"])

        old_result = old_pipeline.rawfile_set.first().result
        old_result.created = timezone.now() + timedelta(minutes=5)
        old_result.save(update_fields=["created"])

        url = reverse("home")
        response = self.client.get(url)
        quick_steps = response.context["quick_steps"]

        self.assertEqual(quick_steps[1]["note"], f"Continue in {old_project.name}.")
        self.assertEqual(
            quick_steps[2]["note"],
            f"Open {old_pipeline.project.name} / {old_pipeline.name} upload queue.",
        )

    def test_active_runs_counts_all_visible_runs_not_only_recent_three(self):
        self.client.force_login(self.user)
        now = timezone.now()

        self.result.maxquant_task_id = "task-0"
        self.result.maxquant_task_submitted_at = now
        self.result.save(update_fields=["maxquant_task_id", "maxquant_task_submitted_at"])

        for idx in range(1, 7):
            raw_file = RawFile.objects.create(
                pipeline=self.pipeline,
                orig_file=SimpleUploadedFile(f"fake-{idx}.raw", b"..."),
                created_by=self.user,
            )
            result, _ = Result.objects.get_or_create(raw_file=raw_file)
            result.maxquant_task_id = f"task-{idx}"
            result.maxquant_task_submitted_at = now
            result.save(update_fields=["maxquant_task_id", "maxquant_task_submitted_at"])

        response = self.client.get(reverse("home"))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context["active_runs"], 7)
        self.assertEqual(len(response.context["recent_runs"]), 3)
