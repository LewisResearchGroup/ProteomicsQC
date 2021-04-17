from django.contrib import admin
from .models import MaxQuantPipeline, FastaFile, MaxQuantExecutable, MaxQuantParameter,\
        RawFile, MaxQuantResult



class FastaFileAdmin(admin.StackedInline):
    model = FastaFile
    readonly_fields = ('md5sum', 'created', 'name', 'path', 'created_by')
    list_display = ('name', 'pipeline', 'created', 'description', 'path')

class MaxQuantParameterAdmin(admin.StackedInline):
    model = MaxQuantParameter

class RawFileAdmin(admin.ModelAdmin):
    model = RawFile
    exclude = ('md5sum', 'slug', 'created', 'created_by')
    list_display =('name', 'path', 'pipeline')
    read_only_fields = ('path',)

class MaxQuantPipelineAdmin(admin.ModelAdmin):
    readonly_fields = ('path', 'path_exists', 'slug', 'fasta_path', 'mqpar_path', 'created_by')
    list_display = ('pk', 'name', 'project', 'run_automatically', 'regular_expressions_filter', 'path', 'path_exists')
    list_filter = ['project']
    inlines = [FastaFileAdmin, MaxQuantParameterAdmin]


class MaxQuantResultAdmin(admin.ModelAdmin):
    readonly_fields = ('path', 'run_directory', 'raw_fn', 'pipeline')


admin.site.register(MaxQuantPipeline, MaxQuantPipelineAdmin)
admin.site.register(MaxQuantExecutable)
admin.site.register(RawFile, RawFileAdmin)
admin.site.register(MaxQuantResult, MaxQuantResultAdmin)