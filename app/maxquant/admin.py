from django.contrib import admin
from .models import MaxQuantPipeline, FastaFile, MaxQuantExecutable, MaxQuantParameter,\
        RawFile, MaxQuantResult, RawToolsSetup



class FastaFileAdmin(admin.StackedInline):
    model = FastaFile
    readonly_fields = ('md5sum', 'created', 'name', 'path', 'created_by')
    list_display = ('name', 'pipeline', 'created', 'description', 'path')


class MaxQuantParameterAdmin(admin.StackedInline):
    model = MaxQuantParameter
    readonly_fields = ('md5sum', 'created', 'path', 'created_by')


class RawToolsSetupInline(admin.StackedInline):
    model = RawToolsSetup
    exclude = ('created', 'created_by')
    readonly_fields = ('created', 'created_by')


class RawFileAdmin(admin.ModelAdmin):
    model = RawFile
    exclude = ('md5sum', 'slug', 'created', 'created_by')
    list_display =('name', 'path', 'pipeline')
    read_only_fields = ('path',)
    def regroup_by(self):
        return 'pipeline'


class MaxQuantPipelineAdmin(admin.ModelAdmin):
    readonly_fields = ('path', 'path_exists', 'slug', 'fasta_path', 'mqpar_path', 'created_by', 'parquet_path', 'uuid')
    list_display = ('pk', 'name', 'project', 'run_automatically', 'regular_expressions_filter', 'path', 'path_exists')
    list_filter = ['project']
    #exclude = ('rawtools',)
    inlines = [MaxQuantParameterAdmin, FastaFileAdmin]

    def queryset(self, request):
        qs = super(MaxQuantPipelineAdmin, self).queryset(request)
        qs = qs.exclude(relatedNameForYourProduct__isnone=True)
        return qs


class MaxQuantResultAdmin(admin.ModelAdmin):
    readonly_fields = ('path', 'run_directory', 'raw_fn', 'mqpar_fn', 
                       'fasta_fn', 'pipeline', 'parquet_path', 
                       'create_protein_quant', 'n_files_maxquant', 
                       'n_files_rawtools_metics', 'n_files_rawtools_qc')

    list_display = ('name', 'pipeline', 'n_files_maxquant', 
        'n_files_rawtools_metics', 'n_files_rawtools_qc')

    #def regroup_by(self):
    #    return 'pipeline'

    def update_maxquant(modeladmin, request, queryset):
        for mq_run in queryset:
            mq_run.run_maxquant(rerun=True)

    def update_rawtools(modeladmin, request, queryset):
        for mq_run in queryset:
            mq_run.run_rawtools_metrics(rerun=True)
            mq_run.run_rawtools_qc(rerun=True)

    def update_rawtools_qc(modeladmin, request, queryset):
        for mq_run in queryset:
            mq_run.run_rawtools_qc(rerun=True)

    def update_rawtools_metrics(modeladmin, request, queryset):
        for mq_run in queryset:
            mq_run.run_rawtools_metrics(rerun=True)

    def run_maxquant(modeladmin, request, queryset):
        for mq_run in queryset:
            mq_run.run_maxquant(rerun=False)

    actions = [run_maxquant, update_maxquant, update_rawtools, 
               update_rawtools_qc, update_rawtools_metrics] 


class RawToolsSetupAdmin(admin.ModelAdmin):
    list_fields = ('name', 'args')


admin.site.register(MaxQuantPipeline, MaxQuantPipelineAdmin)
admin.site.register(MaxQuantExecutable)
admin.site.register(RawFile, RawFileAdmin)
admin.site.register(MaxQuantResult, MaxQuantResultAdmin)
admin.site.register(RawToolsSetup, RawToolsSetupAdmin)