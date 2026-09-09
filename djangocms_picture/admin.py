from django.contrib import admin

from .models import RenditionPreset


@admin.register(RenditionPreset)
class RenditionPresetAdmin(admin.ModelAdmin):
    list_display = ("name", "slug", "width", "height", "crop", "upscale")
    list_filter = ("crop", "upscale")
    prepopulated_fields = {"slug": ("name",)}
    search_fields = ("name", "slug")
