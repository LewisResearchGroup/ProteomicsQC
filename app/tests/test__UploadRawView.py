from django.test import TestCase
from django.urls import reverse
from django.core.files.uploadedfile import SimpleUploadedFile
import json
from unittest.mock import patch

from user.models import User
from project.models import Project
from maxquant.models import Pipeline, RawFile, Result
from django.db import IntegrityError

class UploadRawViewTestCase(TestCase):
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

    def test_upload_raw_get_renders_template(self):
        self.client.force_login(self.user)
        url = reverse("maxquant:upload_raw", kwargs={"pk": self.pipeline.pk})
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)

    def test_upload_raw_post_success(self):
        self.client.force_login(self.user)
        self.assertEqual(RawFile.objects.count(), 0)
        self.assertEqual(Result.objects.count(), 0)

        url = reverse("maxquant:basic_upload")
        fake_file = SimpleUploadedFile("test_file.raw", b"dummy raw data")

        response = self.client.post(url, {
            "pipeline": self.pipeline.pk,
            "project": self.project.pk,
            "orig_file": fake_file
        })

        self.assertEqual(response.status_code, 200)
        data = json.loads(response.content)
        self.assertTrue(data.get("is_valid"))

        self.assertEqual(RawFile.objects.filter(pipeline=self.pipeline).count(), 1)
        # Should also create a result automatically
        self.assertEqual(Result.objects.count(), 1)

    def test_upload_raw_post_duplicate_fallback(self):
        self.client.force_login(self.user)
        # First upload
        fake_file_1 = SimpleUploadedFile("duplicate.raw", b"dummy raw data")
        url = reverse("maxquant:basic_upload")
        response1 = self.client.post(url, {
            "pipeline": self.pipeline.pk,
            "project": self.project.pk,
            "orig_file": fake_file_1
        })
        self.assertEqual(response1.status_code, 200)

        # Second upload with same name
        fake_file_2 = SimpleUploadedFile("duplicate.raw", b"dummy raw data")
        response2 = self.client.post(url, {
            "pipeline": self.pipeline.pk,
            "project": self.project.pk,
            "orig_file": fake_file_2
        })

        self.assertEqual(response2.status_code, 200)
        data = json.loads(response2.content)
        self.assertTrue(data.get("is_valid"))
        self.assertTrue(data.get("already_exists"))

        # Only 1 raw file should exist for that pipeline
        self.assertEqual(RawFile.objects.filter(pipeline=self.pipeline).count(), 1)

    def test_upload_raw_post_duplicate_detects_nonstandard_stored_path(self):
        self.client.force_login(self.user)
        existing_raw = RawFile.objects.create(
            pipeline=self.pipeline,
            created_by=self.user,
            orig_file=SimpleUploadedFile("duplicate_case.raw", b"dummy raw data"),
        )
        # Simulate a legacy/nonstandard DB path for the same basename.
        RawFile.objects.filter(pk=existing_raw.pk).update(
            orig_file="upload/legacy/duplicate_case.raw"
        )

        url = reverse("maxquant:basic_upload")
        response = self.client.post(
            url,
            {
                "pipeline": self.pipeline.pk,
                "project": self.project.pk,
                "orig_file": SimpleUploadedFile(
                    "duplicate_case.raw", b"dummy raw data"
                ),
            },
        )

        self.assertEqual(response.status_code, 200)
        data = json.loads(response.content)
        self.assertTrue(data.get("is_valid"))
        self.assertTrue(data.get("already_exists"))
        self.assertEqual(RawFile.objects.filter(pipeline=self.pipeline).count(), 1)

    @patch("maxquant.views.RawFile.objects.create")
    def test_upload_raw_post_non_duplicate_integrity_error_returns_500(
        self, mocked_create
    ):
        self.client.force_login(self.user)
        mocked_create.side_effect = IntegrityError("NOT NULL constraint failed")

        url = reverse("maxquant:basic_upload")
        response = self.client.post(
            url,
            {
                "pipeline": self.pipeline.pk,
                "project": self.project.pk,
                "orig_file": SimpleUploadedFile("broken.raw", b"dummy raw data"),
            },
        )

        self.assertEqual(response.status_code, 500)
        data = json.loads(response.content)
        self.assertFalse(data.get("is_valid"))
        self.assertIn("Could not save file", data.get("error", ""))
