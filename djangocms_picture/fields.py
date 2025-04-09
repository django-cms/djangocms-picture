from django.contrib.contenttypes.fields import GenericForeignKey
from django.contrib.contenttypes.models import ContentType
from django import forms
from django.db import models


class PictureWidget(forms.MultiWidget):
    def __init__(self, attrs=None):
        widgets = [
            forms.Select(attrs=attrs,choices=[
                (ct.id, ct.name) for ct in ContentType.objects.all()
            ]),
            forms.NumberInput(attrs=attrs),
        ]
        super().__init__(widgets, attrs)

    def decompress(self, value):
        if value:
            return [value.content_type.id, value.object_id]
        return [None, None]


class PictureFormField(forms.Field):
    widget = PictureWidget

    def __init__(self, *args, **kwargs):
        print(args)
        print(kwargs)
        super().__init__(*args, **kwargs)


class PictureField(GenericForeignKey, models.Field):
    def __init__(self, ct_field="content_type", fk_field="object_id", config="config", **kwargs):

        # call to models.Field
        super(GenericForeignKey, self).__init__(**kwargs)

        # call to GenericForeignKey
        super().__init__(ct_field, fk_field, **kwargs)

        print(self.concrete, self.ct_field, self.fk_field)
        sys.exit()

        # self.editable = True
        # self.config = config
        # self.blank = False

#     def formfield(self, **kwargs):
#         kwargs.setdefault("form_class", PictureFormField)
#         return super().formfield(**kwargs)

# class PictureField(models.Field):
#     def __init__(self, config='config', *args, **kwargs):
#         super().__init__(*args, **kwargs)
#         self.config = config

    def formfield(self, **kwargs):
        kwargs.setdefault("form_class", PictureFormField)
        return super().formfield(**kwargs)

    def contribute_to_class(self, cls, name):

        # print("from here: ", cls, name)
        super().contribute_to_class(cls, name)
        # print("then here")
        
        ct = models.ForeignKey(ContentType,
                               on_delete=models.CASCADE)
        fk = models.PositiveIntegerField()

        picture_ct = f"{name}_ct"
        picture_fk = f"{name}_fk"

        cls.add_to_class(picture_ct, ct)
        cls.add_to_class(picture_fk, fk)

        gk = GenericForeignKey(picture_ct, picture_fk)
        gk.editable = True

        # gk.name = name
        # gk.model = cls
        # gk.form_class = PictureFormField
        # setattr(cls, name, gk)

        # cls.add_to_class(f"{name}", gk)

    def get_prep_value(self, value):
        print(value)

    def from_db_value(self, value):
        print("DB: ", value)




