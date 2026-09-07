"""Use backend-aware image storage and its picker outside a CMS plugin."""

from typing import Any

from django import forms
from django.conf import settings
from django.contrib.contenttypes.fields import GenericForeignKey
from django.contrib.contenttypes.models import ContentType
from django.core.exceptions import ValidationError
from django.db import models
from django.http import HttpRequest

from djangocms_picture.backends import (
    BaseImageAsset,
    PictureBackendError,
    PictureSourceDescriptor,
    StoredPictureSource,
    get_backend,
)
from djangocms_picture.fields import BackendImageField, BackendSelection


class Hero(models.Model):
    """Example consumer with its own names for the source backing fields."""

    title = models.CharField(max_length=200)
    image_backend = models.CharField(
        max_length=32,
        default=getattr(settings, "DJANGOCMS_PICTURE_DEFAULT_BACKEND", "filer"),
    )
    image_content_type = models.ForeignKey(
        ContentType,
        blank=True,
        null=True,
        on_delete=models.PROTECT,
        related_name="+",
    )
    image_object_id = models.CharField(blank=True, null=True, max_length=255)
    image_object = GenericForeignKey(
        "image_content_type",
        "image_object_id",
        for_concrete_model=False,
    )
    image_config = models.JSONField(blank=True, default=dict)
    image_source = PictureSourceDescriptor(
        backend_field="image_backend",
        content_type_field="image_content_type",
        object_id_field="image_object_id",
        config_field="image_config",
        object_field="image_object",
    )

    class Meta:
        # The examples package is not a Django application. Models copied into
        # an installed application do not need this explicit label.
        app_label = "djangocms_picture_examples"
        constraints = [
            models.CheckConstraint(
                condition=(
                    models.Q(image_content_type__isnull=True, image_object_id__isnull=True)
                    | models.Q(image_content_type__isnull=False, image_object_id__isnull=False)
                ),
                name="example_hero_image_object_pair",
            ),
        ]

    @property
    def image_asset(self) -> BaseImageAsset | None:
        """Return the selected image through the portable rendering API."""

        return get_backend(self.image_backend).get_asset(self)

    def clean(self) -> None:
        """Apply the selected backend's cross-column integrity checks."""

        super().clean()
        try:
            get_backend(self.image_backend).validate_storage(self)
        except PictureBackendError as error:
            raise ValidationError({"image_source": str(error)}) from error


class HeroForm(forms.ModelForm):
    """Render every configured picker as one logical model form field."""

    image_source: BackendImageField = BackendImageField(required=False)

    class Meta:
        model = Hero
        fields = ("title", "image_source")

    def __init__(
        self,
        *args: Any,
        request: HttpRequest | None = None,
        **kwargs: Any,
    ) -> None:
        super().__init__(*args, **kwargs)
        source_field = BackendImageField(request=request, required=False)
        self.fields["image_source"] = source_field
        if not self.is_bound:
            backend = source_field.backends_by_alias.get(self.instance.image_backend)
            backend = backend or source_field.backends[0]
            self.initial["image_source"] = source_field.selection_from_instance(
                self.instance,
                backend,
            )

    def save(self, commit: bool = True) -> Hero:
        hero = super().save(commit=False)
        selection = self.cleaned_data["image_source"]
        if isinstance(selection, BackendSelection):
            source_field: BackendImageField = self.fields["image_source"]
            source_field.apply_selection(hero, selection)
        else:
            hero.image_source = StoredPictureSource(backend=hero.image_backend)
        if commit:
            hero.save()
        return hero
