import pandas as pd
from unittest.mock import patch
from django.test import TestCase
from django.urls import reverse
from django.core.files.uploadedfile import SimpleUploadedFile

from user.models import User
from project.models import Project
from maxquant.models import Pipeline, RawFile, Result

class ResultDetailViewTestCase(TestCase):
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
        
        self.raw_file = RawFile.objects.create(
            pipeline=self.pipeline, 
            orig_file=SimpleUploadedFile("fake.raw", b"..."),
            created_by=self.user
        )
        self.result, _ = Result.objects.get_or_create(raw_file=self.raw_file)

    @patch("maxquant.views.isfile", return_value=True)
    @patch("maxquant.views.pd.read_csv")
    def test_result_detail_view(self, mock_read_csv, mock_isfile):
        # Mock the dataframe returned by read_csv
        mock_df = pd.DataFrame({"Intensity": [1, 2, 3], "Retention time": [0.1, 0.2, 0.3]})
        mock_read_csv.return_value = mock_df

        self.client.force_login(self.user)
        url = reverse("maxquant:mq_detail", kwargs={"pk": self.result.pk})
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, 200)
        self.assertIn("figures", response.context)
        self.assertIn("summary_stats", response.context)
