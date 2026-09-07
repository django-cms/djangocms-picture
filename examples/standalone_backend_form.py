"""Use the reusable backend picker on a normal Django model and form."""

from typing import Any

from django import forms
from django.db import models
from django.http import HttpRequest

from djangocms_picture.fields import BackendImageField, BackendSelection


class Hero(models.Model):
    title = models.CharField(max_length=200)
    image_selection = models.JSONField(blank=True, null=True)

    class Meta:
        # The examples package is not a Django application. Models copied into
        # an installed application do not need this explicit label.
        app_label = "djangocms_picture_examples"


class HeroForm(forms.ModelForm):
    image: BackendImageField = BackendImageField(required=False)

    class Meta:
        model = Hero
        fields = ("title", "image")

    def __init__(
        self,
        *args: Any,
        request: HttpRequest | None = None,
        **kwargs: Any,
    ) -> None:
        super().__init__(*args, **kwargs)
        self.fields["image"] = BackendImageField(request=request, required=False)
        if not self.is_bound and self.instance.image_selection:
            self.initial["image"] = BackendSelection.deserialize(
                self.instance.image_selection,
                request=request,
            )

    def save(self, commit: bool = True) -> Hero:
        hero = super().save(commit=False)
        selection = self.cleaned_data["image"]
        hero.image_selection = selection.serialize() if selection else None
        if commit:
            hero.save()
        return hero
