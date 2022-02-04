from rest_framework import serializers
from .models import RawFile, Result, Pipeline


class RawFileSerializer(serializers.ModelSerializer):
    class Meta:
        model = RawFile
        fields = ("orig_file", "pipeline", "created_by")


class PipelineSerializer(serializers.ModelSerializer):
    class Meta:
        model = Pipeline
        fields = ("slug", "name", "path_as_str")
        name = serializers.SerializerMethodField()

        def get_name(self, instance):
            return instance.name


class MaxQuantPathSerializer(serializers.ModelSerializer):
    class Meta:
        model = Result
        fields = "path"
        depth = 1

    path = serializers.SerializerMethodField()

    def get_path(self, instance):
        return instance.abs_path
