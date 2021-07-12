from django.contrib import admin
from .models import MaxQuantPipeline, FastaFile, MaxQuantExecutable, MaxQuantParameter,\
        RawFile, MaxQuantResult, RawToolsSetup


class RawFileAdmin(admin.ModelAdmin):
    model = RawFile

    exclude = ('md5sum', 'slug')

    list_display =('name', 'download', 'pipeline', 'use_downstream', 'flagged', 'path', 'created')

    sortable_by = ('created', 'pipeline', 'name', 'use_downstream', 'flagged')

    list_filter = ('pipeline', 'use_downstream', 'flagged')

    search_fields = ('orig_file', )

    group_by = ('pipeline')

    ordering = ('-created',)
    
    actions = ('allow_use_downstream', 'prevent_use_downstream', 'save_and_run')

    def regroup_by(self):
        return 'pipeline'

    def get_readonly_fields(self, request, obj=None):
        if obj:
            return ['path', 'pipeline', 'created', 'orig_file']
        else:
            return ['path', 'created']
    
    def prevent_use_downstream(modeladmin, request, queryset):
        queryset.update(use_downstream=False)

    def allow_use_downstream(modeladmin, request, queryset):
        queryset.update(use_downstream=True)

    def save_and_run(modeladmin, request, queryset):
        for raw_file in queryset:
            raw_file.save()
        


class MaxQuantPipelineAdmin(admin.ModelAdmin):

    ordering = ('name',)

    list_filter = ('project', 'created_by')

    list_display = ('name', 'project', 'created', 'created_by')

    sortable_by = ('name', 'created', 'pipeline')

    fieldsets = (
        (None,       {'fields': ('project', 'name', 'created', 'created_by') }),
        ('MaxQuant', {'fields': ('maxquant_executable', 'mqpar_file', 'download_mqpar', 'fasta_file', 'download_fasta') }),
        ('RawTools', {'fields': ('rawtools_args',) }),
        ('Info',     {'fields': ('slug', 'uuid', 'path', 'fasta_path', 'mqpar_path') })
    )

    def get_readonly_fields(self, request, obj=None):
        if obj:
            return ('created', 'created_by', 'slug', 'uuid', 'path', 
                    'fasta_path', 'mqpar_path', 'download_fasta', 
                    'download_mqpar', 'project')
        else:
            return ('created', 'created_by', 'slug', 'uuid', 'path', 
                    'fasta_path', 'mqpar_path', 'download_fasta', 
                    'download_mqpar')


class MaxQuantResultAdmin(admin.ModelAdmin):
    readonly_fields = ('raw_file', 'created', 'created_by', 
                       'path', 'link', 'run_dir', 'raw_fn', 'mqpar_fn', 
                       'fasta_fn', 'pipeline', 'parquet_path', 
                       'create_protein_quant', 'n_files_maxquant', 
                       'n_files_rawtools_metrics', 'n_files_rawtools_qc',
                       'maxquant_execution_time', 'project', 'maxquant_errors',
                       'rawtools_qc_errors', 'rawtools_metrics_errors',
                       'download_raw'
                       )

    search_fields = ('raw_file__orig_file',)


    list_display = ('name', 'project', 'pipeline', 'n_files_maxquant', 
                    'n_files_rawtools_metrics', 'n_files_rawtools_qc', 
                    'status_protein_quant_parquet', 'maxquant_execution_time', 'created')

    fieldsets = (
        (None,       {'fields': ('project', 'pipeline', 'created', 'raw_file', 'created_by', 'link', 'download_raw')}),
        ('Paths',    {'fields': ('raw_fn', 'mqpar_fn', 'fasta_fn', 'run_dir', 'path')}),
        ('Info',     {'fields': ('n_files_maxquant', 'maxquant_execution_time', 'n_files_rawtools_metrics', 'n_files_rawtools_qc', )}),
        ('Errors',   {'fields': ('maxquant_errors', 'rawtools_qc_errors', 'rawtools_metrics_errors')}),
    )


    ordering = ('-created',)

    list_filter = ('raw_file__pipeline__project', 'raw_file__pipeline')

    def download_raw(self, obj):
        return obj.raw_file.download

    def project(self, obj):
        return obj.raw_file.pipeline.project

    def regroup_by(self):
        return ('project', 'pipeline')

    def rerun_maxquant(modeladmin, request, queryset):
        for mq_run in queryset:
            mq_run.run_maxquant(rerun=True)

    def rerun_rawtools(modeladmin, request, queryset):
        for mq_run in queryset:
            mq_run.run_rawtools_metrics(rerun=True)
            mq_run.run_rawtools_qc(rerun=True)

    def rerun_rawtools_qc(modeladmin, request, queryset):
        for mq_run in queryset:
            mq_run.run_rawtools_qc(rerun=True)

    def rerun_rawtools_metrics(modeladmin, request, queryset):
        for mq_run in queryset:
            mq_run.run_rawtools_metrics(rerun=True)

    def start_maxquant(modeladmin, request, queryset):
        for mq_run in queryset:
            mq_run.run_maxquant(rerun=False)

    def start_rawtools(modeladmin, request, queryset):
        for mq_run in queryset:
            mq_run.run_rawtools_qc(rerun=False)
            mq_run.run_rawtools_metrics(rerun=False)

    def start_all(modeladmin, request, queryset):
        for mq_run in queryset:
            mq_run.run_maxquant(rerun=False)
            mq_run.run_rawtools_qc(rerun=False)
            mq_run.run_rawtools_metrics(rerun=False)

    actions = [start_all, start_maxquant, start_rawtools,
               rerun_maxquant, rerun_rawtools, 
               rerun_rawtools_qc, rerun_rawtools_metrics] 



class MaxQuantExecutableAdmin(admin.ModelAdmin):


    def get_readonly_fields(self, request, obj=None):
        if obj:
            return ('created', 'filename')
        else:
            return ('created',)


admin.site.register(MaxQuantPipeline, MaxQuantPipelineAdmin)
admin.site.register(MaxQuantExecutable, MaxQuantExecutableAdmin)
admin.site.register(RawFile, RawFileAdmin)
admin.site.register(MaxQuantResult, MaxQuantResultAdmin)
