from django import forms

from .models import RawFile


class BasicUploadForm(forms.ModelForm):
    class Meta:
        model = RawFile
        fields = ("orig_file",)


class SearchResult(forms.Form):
    raw_file = forms.CharField(
        label="File name contains", max_length=100, required=False
    )
