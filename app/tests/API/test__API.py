from django.test import TestCase
from datetime import date
from unittest.mock import patch
from pathlib import Path as P
import pandas as pd
from project.models import Project
from maxquant.models import Pipeline

from maxquant.models import RawFile


from django.core.files.uploadedfile import SimpleUploadedFile


from django.test import Client
from user.models import User
from api.views import get_protein_quant_fn

URL = "http://localhost:8000"


class ApiTestCase(TestCase):
    def setUp(self):
        if not hasattr(self, "pipeline"):
            print("Setup")
            self.user = User.objects.create_user(
                email="api-user@example.com",
                password="testpass123",
            )
            self.member_user = User.objects.create_user(
                email="member@example.com",
                password="testpass123",
            )
            self.project = Project.objects.create(
                name="project", description="A test project", created_by=self.user
            )
            self.project.users.add(self.user)
            self.project.users.add(self.member_user)

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
                pipeline=self.pipeline,
                orig_file=SimpleUploadedFile("fake.raw", b"..."),
                created_by=self.user,
            )

    def test__projects(self):
        c = Client()
        c.force_login(self.user)
        url = f"{URL}/api/projects"
        actual = c.post(
            url,
            data={"uid": self.user.uuid},
            content_type="application/json",
        ).json()
        expected = [
            {
                "pk": self.project.pk,
                "name": "project",
                "description": "A test project",
                "slug": "project",
            }
        ]
        assert actual == expected, actual

    def test__projects_unauthenticated(self):
        """Verify that unauthenticated requests are rejected."""
        c = Client()
        url = f"{URL}/api/projects"
        response = c.post(url)
        assert response.status_code == 403, f"Expected 403, got {response.status_code}"

    def test__projects_reject_uid_impersonation_without_auth(self):
        c = Client()
        url = f"{URL}/api/projects"
        response = c.post(
            url,
            data={"uid": str(self.user.uuid)},
            content_type="application/json",
        )
        assert response.status_code == 403, f"Expected 403, got {response.status_code}"

    def test__pipelines(self):
        """Test pipeline list endpoint."""
        c = Client()
        c.force_login(self.user)
        url = f"{URL}/api/pipelines"
        response = c.post(url, {"project": "project"}, content_type="application/json")
        assert response.status_code == 200, f"Expected 200, got {response.status_code}"
        data = response.json()
        assert len(data) == 1
        assert data[0]["name"] == "pipe"

    def test__pipelines_unauthenticated(self):
        """Verify unauthenticated pipeline requests are rejected."""
        c = Client()
        url = f"{URL}/api/pipelines"
        response = c.post(url, {"project": "project"}, content_type="application/json")
        assert response.status_code == 403, f"Expected 403, got {response.status_code}"

    def test__pipelines_reject_uid_impersonation_without_auth(self):
        c = Client()
        url = f"{URL}/api/pipelines"
        response = c.post(
            url,
            {"project": "project", "uid": str(self.user.uuid)},
            content_type="application/json",
        )
        assert response.status_code == 403, f"Expected 403, got {response.status_code}"

    def test__create_flag_requires_auth(self):
        """Verify flag creation requires authentication."""
        c = Client()
        url = f"{URL}/api/flag/create"
        response = c.post(url, {
            "project": "project",
            "pipeline": "pipe",
            "raw_files": ["fake.raw"],
        })
        assert response.status_code == 403, f"Expected 403, got {response.status_code}"

    def test__create_flag_requires_project_membership(self):
        """Verify users can only flag files in their projects."""
        other_user = User.objects.create_user(
            email="other@example.com",
            password="testpass123",
        )
        c = Client()
        c.force_login(other_user)
        url = f"{URL}/api/flag/create"
        response = c.post(url, {
            "project": "project",
            "pipeline": "pipe",
            "raw_files": ["fake.raw"],
        })
        assert response.status_code == 403, f"Expected 403, got {response.status_code}"

    def test__delete_flag_requires_auth(self):
        """Verify flag deletion requires authentication."""
        c = Client()
        url = f"{URL}/api/flag/delete"
        response = c.post(url, {
            "project": "project",
            "pipeline": "pipe",
            "raw_files": ["fake.raw"],
        })
        assert response.status_code == 403, f"Expected 403, got {response.status_code}"

    def test__project_member_cannot_create_flag_for_other_users_raw_file(self):
        c = Client()
        c.force_login(self.member_user)
        url = f"{URL}/api/flag/create"
        response = c.post(url, {
            "project": "project",
            "pipeline": "pipe",
            "raw_files": ["fake.raw"],
        })

        assert response.status_code == 200, f"Expected 200, got {response.status_code}"
        self.raw_file.refresh_from_db()
        assert self.raw_file.flagged is False

    def test__project_member_cannot_delete_flag_for_other_users_raw_file(self):
        self.raw_file.flagged = True
        self.raw_file.save(update_fields=["flagged"])

        c = Client()
        c.force_login(self.member_user)
        url = f"{URL}/api/flag/delete"
        response = c.post(url, {
            "project": "project",
            "pipeline": "pipe",
            "raw_files": ["fake.raw"],
        })

        assert response.status_code == 200, f"Expected 200, got {response.status_code}"
        self.raw_file.refresh_from_db()
        assert self.raw_file.flagged is True
    def test__rawfile_requires_auth(self):
        """Verify rawfile endpoint requires authentication."""
        c = Client()
        url = f"{URL}/api/rawfile"
        response = c.post(url, {
            "project": "project",
            "pipeline": "pipe",
            "action": "flag",
            "raw_files": ["fake.raw"],
        })
        assert response.status_code == 403, f"Expected 403, got {response.status_code}"

    def test__qc_data_requires_pipeline_access(self):
        other_user = User.objects.create_user(
            email="qc-other@example.com",
            password="testpass123",
        )
        c = Client()
        c.force_login(other_user)
        url = f"{URL}/api/qc-data"
        response = c.post(url, {
            "project": "project",
            "pipeline": "pipe",
            "data_range": 0,
        }, content_type="application/json")

        assert response.status_code == 403, f"Expected 403, got {response.status_code}"

    def test__qc_data_includes_tmt_peptide_and_protein_group_counts(self):
        result = self.raw_file.result
        maxquant_dir = result.output_dir_maxquant
        maxquant_dir.mkdir(parents=True, exist_ok=True)

        evidence = (
            "Sequence\tReporter intensity corrected 1\tReporter intensity corrected 2\n"
            "PEP_A\t100\t0\n"
            "PEP_B\t0\t10\n"
            "PEP_B\t5\t0\n"
        )
        (maxquant_dir / "evidence.txt").write_text(evidence)

        protein_groups = (
            "Majority protein IDs\tReporter intensity corrected 1\tReporter intensity corrected 2\n"
            "P1\t10\t0\n"
            "P2\t0\t20\n"
            "P2\t1\t0\n"
        )
        (maxquant_dir / "proteinGroups.txt").write_text(protein_groups)

        raw_name = P(self.raw_file.logical_name).with_suffix("").name
        rt_df = pd.DataFrame(
            {
                "RawFile": [raw_name],
                "DateAcquired": [pd.Timestamp("2024-01-01")],
                "Index": [1],
            }
        )
        mq_df = pd.DataFrame({"RawFile": [raw_name], "N_peptides": [123]})

        c = Client()
        c.force_login(self.user)
        url = f"{URL}/api/qc-data"
        with patch("maxquant.Result.Result.rawtools_qc_data", return_value=rt_df), patch(
            "maxquant.Result.Result.maxquant_qc_data", return_value=mq_df
        ):
            response = c.post(
                url,
                {
                    "project": "project",
                    "pipeline": "pipe",
                    "data_range": 100,
                    "columns": [
                        "RawFile",
                        "TMT1_peptide_count",
                        "TMT2_peptide_count",
                        "TMT1_protein_group_count",
                        "TMT2_protein_group_count",
                    ],
                },
                content_type="application/json",
            )

        assert response.status_code == 200, f"Expected 200, got {response.status_code}"
        payload = response.json()
        assert payload["TMT1_peptide_count"] == [2], payload
        assert payload["TMT2_peptide_count"] == [1], payload
        assert payload["TMT1_protein_group_count"] == [2], payload
        assert payload["TMT2_protein_group_count"] == [1], payload

    @patch("api.views.get_protein_quant_fn", return_value=[])
    def test__protein_groups_empty_result_returns_json_object(self, _mock_get_fns):
        c = Client()
        c.force_login(self.user)
        url = f"{URL}/api/protein-groups"
        response = c.post(url, {
            "project": "project",
            "pipeline": "pipe",
            "data_range": 0,
            "raw_files": [],
            "columns": ["Score"],
            "protein_names": ["P1"],
        })

        assert response.status_code == 200, f"Expected 200, got {response.status_code}"
        assert response.json() == {}, response.content

    def test__get_protein_quant_fn_data_range_limits_results(self):
        RawFile.objects.create(
            pipeline=self.pipeline,
            orig_file=SimpleUploadedFile("fake-1.raw", b"..."),
            created_by=self.user,
            created=date(2024, 1, 1),
        )
        RawFile.objects.create(
            pipeline=self.pipeline,
            orig_file=SimpleUploadedFile("fake-2.raw", b"..."),
            created_by=self.user,
            created=date(2024, 1, 2),
        )
        RawFile.objects.create(
            pipeline=self.pipeline,
            orig_file=SimpleUploadedFile("fake-3.raw", b"..."),
            created_by=self.user,
            created=date(2024, 1, 3),
        )

        with patch(
            "maxquant.Result.Result.create_protein_quant",
            side_effect=lambda: "protein_quant.parquet",
        ):
            fns = get_protein_quant_fn(
                self.project.slug,
                self.pipeline.slug,
                data_range=2,
                user=self.user,
            )

        assert len(fns) == 2, fns

    def test__get_protein_quant_fn_data_range_limits_filtered_raw_files(self):
        RawFile.objects.create(
            pipeline=self.pipeline,
            orig_file=SimpleUploadedFile("fake-1.raw", b"..."),
            created_by=self.user,
            created=date(2024, 1, 1),
        )
        RawFile.objects.create(
            pipeline=self.pipeline,
            orig_file=SimpleUploadedFile("fake-2.raw", b"..."),
            created_by=self.user,
            created=date(2024, 1, 2),
        )
        RawFile.objects.create(
            pipeline=self.pipeline,
            orig_file=SimpleUploadedFile("fake-3.raw", b"..."),
            created_by=self.user,
            created=date(2024, 1, 3),
        )

        with patch(
            "maxquant.Result.Result.create_protein_quant",
            autospec=True,
            side_effect=lambda result: result.raw_file.logical_name,
        ):
            fns = get_protein_quant_fn(
                self.project.slug,
                self.pipeline.slug,
                data_range=2,
                raw_files=["fake-1.raw", "fake-2.raw", "fake-3.raw"],
                user=self.user,
            )

        assert fns == ["fake-2.raw", "fake-3.raw"], fns
