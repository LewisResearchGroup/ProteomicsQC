from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import SimpleTestCase, TestCase

from dashboards.dashboards.dashboard.tools import (
    _normalize_max_features,
    get_pipelines,
    get_projects,
)
from maxquant.models import Pipeline
from project.models import Project
from user.models import User


class DashboardToolsTestCase(SimpleTestCase):
    def test__normalize_max_features_caps_integer_values(self):
        assert _normalize_max_features(10, 4) == 4
        assert _normalize_max_features(0, 4) == 1

    def test__normalize_max_features_keeps_fractional_values(self):
        assert _normalize_max_features(0.5, 4) == 0.5
        assert _normalize_max_features("0.25", 4) == 0.25

    def test__normalize_max_features_supports_non_integer_numeric_input(self):
        assert _normalize_max_features(2.8, 4) == 2
        assert _normalize_max_features("3", 4) == 3

    def test__normalize_max_features_rejects_invalid_values(self):
        assert _normalize_max_features(None, 4) is None
        assert _normalize_max_features(True, 4) is None
        assert _normalize_max_features("abc", 4) is None


class DashboardToolsUserFilteringTestCase(TestCase):
    def setUp(self):
        self.owner = User.objects.create_user(
            email="owner@example.com",
            password="pass1234",
        )
        self.member = User.objects.create_user(
            email="member@example.com",
            password="pass1234",
        )
        self.outsider = User.objects.create_user(
            email="outsider@example.com",
            password="pass1234",
        )
        self.admin = User.objects.create_superuser(
            email="admin@example.com",
            password="pass1234",
        )

        self.owner_project = Project.objects.create(
            name="Owner Project",
            description="owned",
            created_by=self.owner,
        )
        self.member_project = Project.objects.create(
            name="Member Project",
            description="shared",
            created_by=self.outsider,
        )
        self.member_project.users.add(self.member)
        self.member_project.users.add(self.owner)

        self.private_project = Project.objects.create(
            name="Private Project",
            description="private",
            created_by=self.outsider,
        )

        fasta = SimpleUploadedFile("test.fasta", b">protein\nAAAA")
        mqpar = SimpleUploadedFile("test.xml", b"<mqpar></mqpar>")
        self.owner_pipeline = Pipeline.objects.create(
            name="owner-pipe",
            project=self.owner_project,
            created_by=self.owner,
            fasta_file=fasta,
            mqpar_file=mqpar,
        )
        self.member_pipeline = Pipeline.objects.create(
            name="member-pipe",
            project=self.member_project,
            created_by=self.outsider,
            fasta_file=SimpleUploadedFile("test2.fasta", b">protein\nBBBB"),
            mqpar_file=SimpleUploadedFile("test2.xml", b"<mqpar></mqpar>"),
        )
        self.private_pipeline = Pipeline.objects.create(
            name="private-pipe",
            project=self.private_project,
            created_by=self.outsider,
            fasta_file=SimpleUploadedFile("test3.fasta", b">protein\nCCCC"),
            mqpar_file=SimpleUploadedFile("test3.xml", b"<mqpar></mqpar>"),
        )

    def test_get_projects_filters_by_owner_or_membership(self):
        projects = get_projects(user=self.owner)
        values = {p["value"] for p in projects}
        assert self.owner_project.slug in values
        assert self.member_project.slug in values
        assert self.private_project.slug not in values

    def test_get_projects_for_admin_includes_all(self):
        projects = get_projects(user=self.admin)
        values = {p["value"] for p in projects}
        assert self.owner_project.slug in values
        assert self.member_project.slug in values
        assert self.private_project.slug in values

    def test_get_pipelines_filters_by_project_access(self):
        owner_visible = get_pipelines(self.owner_project.slug, user=self.owner)
        owner_names = {p["name"] for p in owner_visible}
        assert self.owner_pipeline.name in owner_names

        private_for_owner = get_pipelines(self.private_project.slug, user=self.owner)
        assert private_for_owner == []

        member_visible = get_pipelines(self.member_project.slug, user=self.member)
        member_names = {p["name"] for p in member_visible}
        assert self.member_pipeline.name in member_names
