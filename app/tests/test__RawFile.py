
from django.test import TestCase
from django.urls import reverse
from project.models import Project
from maxquant.models import Pipeline
from maxquant.models import Result

from maxquant.models import RawFile

from glob import glob

from django.core.files.uploadedfile import SimpleUploadedFile

from user.models import User


class RawFileTestCase(TestCase):
    def setUp(self):
        if not hasattr(self, "pipeline"):
            print("Setup RawFileTestCase")
            self.project = Project.objects.create(
                name="project", description="A test project"
            )

            contents_mqpar = b"<mqpar></mqpar>"
            contents_fasta = b">protein\nSEQUENCE"

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
            print("...done setup RawFileTestCase.")

    def test__raw_file_exists(self):
        assert self.raw_file.path.is_file(), self.raw_file.path

    def test__rawfile_output_dir_created(self):
        path = self.raw_file.output_dir
        files = glob(f"{self.raw_file.pipeline.path}/**/*", recursive=True)
        files.sort()
        print(files)
        assert path.is_dir(), f"{path} NOT FOUND\n\t" + "\n\t".join(files)

    def test__maxquant_results_created(self):
        result = Result.objects.get(raw_file=self.raw_file)
        assert result is not None, result


class SameRawFileCanBeUploadedToMultiplePipelines(TestCase):
    def setUp(self):
        self.project = Project.objects.create(
            name="project", description="A test project"
        )

        contents_mqpar = b"<mqpar></mqpar>"
        contents_fasta = b">protein\nSEQUENCE"

        self.pipeline_A = Pipeline.objects.create(
            name="pipeA",
            project=self.project,
            fasta_file=SimpleUploadedFile("my_fasta.fasta", contents_fasta),
            mqpar_file=SimpleUploadedFile("my_mqpar.xml", contents_mqpar),
            rawtools_args="-p -q -x -u -l -m -r TMT11 -chro 12TB",
        )

        self.pipeline_B = Pipeline.objects.create(
            name="pipeB",
            project=self.project,
            fasta_file=SimpleUploadedFile("my_fasta.fasta", contents_fasta),
            mqpar_file=SimpleUploadedFile("my_mqpar.xml", contents_mqpar),
            rawtools_args="-p -q -x -u -l -m -r TMT11 -chro 12TB",
        )

    def test__upload_same_raw_file_to_different_pipelines(self):

        self.raw_file = RawFile.objects.create(
            pipeline=self.pipeline_A, orig_file=SimpleUploadedFile("fake.raw", b"...")
        )

        self.raw_file = RawFile.objects.create(
            pipeline=self.pipeline_B, orig_file=SimpleUploadedFile("fake.raw", b"...")
        )


class ReuploadAfterResultDeletionRestoresResult(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            email="tester@example.com", password="pass1234"
        )
        self.project = Project.objects.create(
            name="project", description="A test project", created_by=self.user
        )

        contents_mqpar = b"<mqpar></mqpar>"
        contents_fasta = b">protein\nSEQUENCE"

        self.pipeline = Pipeline.objects.create(
            name="pipe",
            project=self.project,
            created_by=self.user,
            fasta_file=SimpleUploadedFile("my_fasta.fasta", contents_fasta),
            mqpar_file=SimpleUploadedFile("my_mqpar.xml", contents_mqpar),
            rawtools_args="-p -q -x -u -l -m -r TMT11 -chro 12TB",
        )

        self.raw_file = RawFile.objects.create(
            pipeline=self.pipeline, orig_file=SimpleUploadedFile("fake.raw", b"...")
        )
        self.result = Result.objects.get(raw_file=self.raw_file)

    def test_reupload_same_filename_recreates_missing_result(self):
        self.client.force_login(self.user)

        self.result.delete()
        self.assertFalse(Result.objects.filter(raw_file=self.raw_file).exists())

        response = self.client.post(
            reverse("maxquant:basic_upload"),
            data={
                "project": self.project.pk,
                "pipeline": self.pipeline.pk,
                "orig_file": SimpleUploadedFile("fake.raw", b"..."),
            },
        )

        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertTrue(payload["is_valid"])
        self.assertTrue(payload.get("already_exists"))
        self.assertTrue(payload.get("restored_result"))

        self.assertEqual(
            RawFile.objects.filter(pipeline=self.pipeline, orig_file="upload/fake.raw").count(),
            1,
        )
        self.assertTrue(Result.objects.filter(raw_file=self.raw_file).exists())
