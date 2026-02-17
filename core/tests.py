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
