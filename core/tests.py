from __future__ import annotations

from django.test import TestCase

from projects.models import Project


class CoreUiTests(TestCase):
    def test_home_page_loads(self):
        response = self.client.get("/app")
        assert response.status_code == 200

    def test_create_project_from_home(self):
        response = self.client.post(
            "/app",
            {
                "name": "UI Project",
                "prompt": "Make an ad",
                "template_id": "hook_benefit_cta_v1",
                "primary_color": "#00A86B",
            },
        )
        assert response.status_code == 302
        assert Project.objects.filter(name="UI Project").exists()

    def test_workspace_shows_agent_decisions_panel(self):
        project = Project.objects.create(name="Panel Project")
        response = self.client.get(f"/app/projects/{project.id}")
        assert response.status_code == 200
        assert "Agent Decisions" in response.content.decode()
