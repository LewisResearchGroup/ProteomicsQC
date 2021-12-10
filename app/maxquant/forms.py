from django import forms

from .models import RawFile, BasicUpload


class BasicUploadForm(forms.ModelForm):
    class Meta:
        model = RawFile
        fields = ("orig_file",)
