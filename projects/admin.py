from django.contrib import admin

from .models import Asset, Draft, ExportArtifact, Job, Overlay, Project

admin.site.register(Project)
admin.site.register(Asset)
admin.site.register(Draft)
admin.site.register(Overlay)
admin.site.register(ExportArtifact)
admin.site.register(Job)
