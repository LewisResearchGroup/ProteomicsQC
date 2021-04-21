from os.path import isfile
import pandas as pd
import logging

from io import BytesIO

from django.http import HttpResponse, JsonResponse, HttpResponseNotFound, Http404
from django.contrib.auth.mixins import LoginRequiredMixin
from django.views import generic, View
from django.db import transaction, IntegrityError
from django.shortcuts import render

from django.conf import settings

from .forms import BasicUploadForm
from .models import RawFile, MaxQuantResult, MaxQuantPipeline
from project.models import Project

from lrg_omics.tools import today
from lrg_omics.proteomics.vis.plotly.rawtools import histograms, lines_plot
from lrg_omics.plotly import set_template, plotly_heatmap, plotly_fig_to_div, plotly_dendrogram, plotly_bar,\
    plotly_table, plotly_histogram

# Create your views here.
def maxquant_pipeline_view(request, project, pipeline):
    maxquant_runs = MaxQuantResult.objects.filter(raw_file__pipeline__slug=pipeline)
    project = Project.objects.get(slug=project)
    pipeline = MaxQuantPipeline.objects.get(project=project, slug=pipeline)
    context = dict(maxquant_runs=maxquant_runs, project=project, pipeline=pipeline)
    context['home_title'] = settings.HOME_TITLE
    return render(request, 'proteomics/pipeline_detail.html', context)


def pipeline_download_file(request, project, pipeline):

    maxquant_runs = MaxQuantResult.objects.filter(raw_file__pipeline__slug=pipeline)

    file = request.GET.get('file')
    project_name = Project.objects.get(slug=project).name
    pipeline_name = MaxQuantPipeline.objects.get(project__slug=project, slug=pipeline).name
    print(f'Get {file} from {project_name}/{pipeline_name}')

    stream = BytesIO()
    dfs = []

    for mq_run in maxquant_runs:
        if mq_run.use_downstream:
            print('Write', mq_run.name)
            df = mq_run.get_data_from_file(file)
            if df is None:
                continue
            dfs.append(df)

    if dfs == []:
        raise Http404(f'No file named {file} found on the server.')
    data = pd.concat(dfs).set_index('RawFile').reset_index()    
    stream.write(data.to_csv(index=False).encode())
    stream.seek(0)

    response = HttpResponse(stream, content_type='text/csv')
    fn = f"{today()}_{project}_{pipeline}__{file.replace('.txt', '')}.csv"
    response['Content-Disposition'] = 'attachment; filename="{}"'.format(fn)
    return response



class MaxQuantResultDetailView(LoginRequiredMixin, generic.DetailView):
    model = MaxQuantResult 
    template_name = 'proteomics/maxquant_detail.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        mq_run = context['object']
        path = mq_run.output_dir_maxquant

        context['name'] = context['object'].name
        context['project'] = mq_run.raw_file.pipeline.project
        context['pipeline'] = mq_run.raw_file.pipeline
        context['raw_file'] = mq_run.raw_file

        figures = []
        fn = f'{path}/evidence.txt'
        if isfile(fn):
            msms = pd.read_csv(fn, sep='\t').set_index('Retention time').sort_index()
            cols = ['Length', 'Oxidation (M)', 'Missed cleavages', 'MS/MS m/z', 
                    'Charge', 'm/z', 'Mass']
            for col in cols:
                fig = lines_plot(msms, cols=[col], title=f'Evidence: {col}')
                figures.append( plotly_fig_to_div(fig) )

        fn = f'{path}/msmsScans.txt'
        if isfile(fn):
            msms = pd.read_csv(fn, sep='\t').set_index('Retention time')
            cols = ['Total ion current', 'm/z', 'Base peak intensity']
            for col in cols:
                fig = lines_plot(msms, cols=[col], title=f'MSMS: {col}')
                figures.append( plotly_fig_to_div(fig) ) 

        fn = f'{path}/peptides.txt'
        if isfile(fn):
            peptides = pd.read_csv(fn, sep='\t')
            cols = ['Length', 'Mass']
            for col in cols:
                fig = lines_plot(peptides, cols=[col], title=f'Peptide: {col}')
                figures.append( plotly_fig_to_div(fig) ) 

        fn = f'{path}/proteinGroups.txt'
        if isfile(fn):
            proteins = pd.read_csv(fn, sep='\t')
            cols = ['Mol. weight [kDa]', 'Unique sequence coverage [%]']
            for col in cols:
                fig = lines_plot(proteins, cols=[col], title=f'Protein: {col}')
                figures.append( plotly_fig_to_div(fig) )

        context['figures'] = figures
        context['home_title'] = settings.HOME_TITLE
        return context


def maxquant_download(request, pk):
    mq_run = MaxQuantResult.objects.get(pk=pk)
    response = HttpResponse(mq_run.download, content_type='application/zip')
    fn = f"{mq_run.name}.zip"
    response['Content-Disposition'] = 'attachment; filename="{}"'.format(fn)
    return response

   
class UploadRaw(LoginRequiredMixin, View):

    def get(self, request, pk=None):
        pipeline = MaxQuantPipeline.objects.get(pk=pk)
        project = pipeline.project
        context = {'project': project, 'home_title': settings.HOME_TITLE, 'pipeline': pipeline}
        return render(request, 'proteomics/upload.html', context)
 
    def post(self, request):
        form = BasicUploadForm(self.request.POST, self.request.FILES)
        logging.warning('RAW upload')

        project_id  = request.POST.get('project')
        pipeline_id = request.POST.get('pipeline')

        logging.warning(f'Upload to: {project_id} / {pipeline_id}')

        pipeline = MaxQuantPipeline.objects.get(pk=pipeline_id)
        project  = pipeline.project 

        logging.warning(f'Upload to: {project.name} / {pipeline.name}')
        
        if form.is_valid():
            _file = form.cleaned_data['orig_file']
            _file = RawFile.objects.create(orig_file=_file, pipeline=pipeline)

            if str( _file.name ).lower().endswith('.raw'): 
                _file.save()
            data = {'is_valid': True, 'name': str( _file.name ), 'url': str( _file.path ) }
        else:
            data = {'is_valid': False}
        return JsonResponse(data)