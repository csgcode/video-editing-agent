from django.contrib import admin

from .models import Asset, Draft, DraftVersion, ExportArtifact, Job, Overlay, Project, VideoContext

admin.site.register(Project)
admin.site.register(Asset)
admin.site.register(VideoContext)
admin.site.register(Draft)
admin.site.register(DraftVersion)
admin.site.register(Overlay)
admin.site.register(ExportArtifact)
admin.site.register(Job)
