from django.contrib.contenttypes.fields import GenericForeignKey
from django.contrib.contenttypes.models import ContentType
from django import forms
from django.db import models


class PictureWidget(forms.MultiWidget):
    def __init__(self):
        widgets = [
            forms.Select(attrs={},choices=[
                (ct.id, ct.name) for ct in ContentType.objects.filter(id=45)
            ]),
            forms.NumberInput(attrs={}),
        ]
        super().__init__(widgets)

    def decompress(self, value):
        print("Decompress Value: ", value)
        if value:
            return [value.content_type.id, value.object_id]
        return [None, None]

    def value_from_datadict(self, data, file, name):
        value = super().value_from_datadict(data, file, name)
        value = ContentType.objects.filter(id=value[0]).first()
        return value


class PictureFormField(forms.Field):
    widget = PictureWidget

    def __init__(self, *args, **kwargs):
        kwargs.pop('encoder', None)
        kwargs.pop('decoder', None)
        super().__init__(*args, **kwargs)

    def prepare_value(self, value):
        print("picture form: ", value)
        # if we return list or tuple from here,
        # django skips decompress
        # value = (4, 3)
        return value

    # def to_python(self, value):
    #     # This is called inside `clean`
    #     # Note that `clean` is called inside `full_clean`'s `_clean_fields()`
    #     pass


class PictureField(GenericForeignKey, models.JSONField):
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

        self.ct_field = picture_ct = f"{name}_ct"
        self.fk_field = picture_fk = f"{name}_fk"
 
        cls.add_to_class(picture_ct, ct)
        cls.add_to_class(picture_fk, fk)
        super().contribute_to_class(cls, name)

        # this is required by _post_clean hook used during
        # model validation in forms
        self.attname = self.name

    def formfield(self, **kwargs):
        kwargs.setdefault("form_class", PictureFormField)
        return super().formfield(**kwargs)

