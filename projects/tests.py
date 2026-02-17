from __future__ import annotations


from django.test import TestCase

from projects.models import Draft, Overlay, Project


class HealthTest(TestCase):
    def test_health(self):
        response = self.client.get("/health")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["status"], "ok")


class ProjectFlowTest(TestCase):
    def test_create_project(self):
        payload = {
            "name": "Test Project",
            "prompt": "Make a high-converting ad",
            "template_id": "hook_benefit_cta_v1",
            "primary_color": "#00A86B",
        }
        response = self.client.post("/api/v1/projects", payload, content_type="application/json")
        self.assertEqual(response.status_code, 201)
        self.assertEqual(Project.objects.count(), 1)


class OverlayValidationTest(TestCase):
    def test_invalid_overlay_timing_rejected(self):
        project = Project.objects.create(name="p")
        draft = Draft.objects.create(project=project)
        overlay = Overlay(draft=draft, overlay_type="headline", start_sec=5, end_sec=3)
        with self.assertRaises(Exception):
            overlay.full_clean()
