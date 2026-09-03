from django.urls import include, path

urlpatterns = [
    path("finder/", include("finder.browser.urls")),
    path("", include("cms.urls")),
]
