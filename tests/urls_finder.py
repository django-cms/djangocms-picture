from django.contrib import admin
from django.urls import include, path

urlpatterns = [
    path("finder/", include("finder.browser.urls")),
    path("admin/", admin.site.urls),
    path("", include("cms.urls")),
]
