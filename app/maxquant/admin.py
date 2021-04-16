from django.contrib import admin
from .models import MaxQuantPipeline, FastaFile, MaxQuantExecutable


class FastaFileAdmin(admin.StackedInline):
    model = FastaFile
    readonly_fields = ('md5sum', 'created', 'name', 'path', 'created_by')
    list_display = ('name', 'pipeline', 'created', 'description', 'path')
    #list_filter = ['project']

class MaxQuantPipelineAdmin(admin.ModelAdmin):
    readonly_fields = ('path', 'path_exists', 'slug', 'fasta_path', 'mqpar_path', 'created_by')
    list_display = ('pk', 'name', 'project', 'run_automatically', 'regular_expressions_filter', 'path', 'path_exists')
                    #'fasta_file', 'maxquant_param', 'maxquant_executable',)
    list_filter = ['project']
    inlines = [FastaFileAdmin]

admin.site.register(MaxQuantPipeline, MaxQuantPipelineAdmin)
admin.site.register(MaxQuantExecutable)
