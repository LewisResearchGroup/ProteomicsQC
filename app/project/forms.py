from django import forms


class SearchProject(forms.Form):
    regex = forms.CharField(
        label="Project name contains", max_length=100, required=False
    )


class SearchPipeline(forms.Form):
    regex = forms.CharField(
        label="Pipeline name contains", max_length=100, required=False
    )
