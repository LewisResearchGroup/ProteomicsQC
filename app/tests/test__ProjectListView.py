from django.test import TestCase
from django.urls import reverse

from user.models import User
from project.models import Project


class ProjectListViewTestCase(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username="tester", email="tester@example.com", password="pass1234"
        )
        Project.objects.create(name="Project 1", description="First project")
        Project.objects.create(name="Project 2", description="Second project")

    def test_projects_render_on_list_page(self):
        self.client.force_login(self.user)
        url = reverse("project:list")
        response = self.client.get(url)

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Project 1")
        self.assertContains(response, "Project 2")
