from rest_framework import serializers
from .models import Project

class ProjectsNamesSerializer(serializers.ModelSerializer):
    class Meta():
        model = Project
        fields = ('pk', 'name', 'description', 'slug')