from django import forms
from django.contrib.contenttypes.fields import GenericForeignKey
from django.contrib.contenttypes.models import ContentType
from django.db import models


class PictureWidget(forms.MultiWidget):
    def __init__(self):
        widgets = [
            forms.Select(attrs={},choices=[
                # TODO: provide a configuration settings instead of
                # accessing the db?
                # Also, check that the provided value exists
                (ct.id, ct.name) for ct in ContentType.objects.all()
            ]),
            forms.NumberInput(attrs={}),
        ]
        super().__init__(widgets)


class PictureFormField(forms.Field):
    widget = PictureWidget

    def __init__(self, *args, **kwargs):
        kwargs.pop('encoder', None)  # passed from models.JSONField
        kwargs.pop('decoder', None)
        super().__init__(*args, **kwargs)

    def prepare_value(self, value):
        data = []
        if value is None:
            return data

        ct = ContentType.objects.get_for_model(value)
        data.extend([ct.id, value.pk])
        return data

    def to_python(self, value):
        if not value:
            return value

        # NOTE: what if we save this in a hidden widget
        ct_id, fk = value

        ct = ContentType.objects.get_for_id(id=ct_id)
        obj = ct.get_object_for_this_type(id=fk)

        # This should help us deceive GFK.get_content_type
        # to get the necessary ct and fk
        class HelperObj:
            _state = ct._state
            pk = int(fk)
            _meta = ct.model_class()._meta

            def __repr__(this):
                return f"{this._meta.model_name}({fk})"

        return obj


class PictureField(GenericForeignKey, models.Field):
    def __init__(self, **kwargs):
        # call to models.JSONField
        super(GenericForeignKey, self).__init__(**kwargs)

        # call to GenericForeignKey
        super().__init__(**kwargs)
        self.editable = True

    def contribute_to_class(self, cls, name):
        ct = models.ForeignKey(ContentType,
                               editable=False,
                               on_delete=models.CASCADE)
        fk = models.PositiveIntegerField(editable=False)

        self.ct_field = f"{name}_ct"
        self.fk_field = f"{name}_fk"

        cls.add_to_class(self.ct_field, ct)
        cls.add_to_class(self.fk_field, fk)
        super().contribute_to_class(cls, name)

        # this is required by _post_clean hook used during
        # model validation in forms
        self.attname = self.name

    def formfield(self, **kwargs):
        kwargs.setdefault("form_class", PictureFormField)
        return super().formfield(**kwargs)

