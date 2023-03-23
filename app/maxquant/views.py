from os.path import isfile
import pandas as pd
import logging

from io import BytesIO

from django.http import HttpResponse, JsonResponse, HttpResponseNotFound, Http404
from django.contrib.auth.mixins import LoginRequiredMixin
from django.views import generic, View
from django.db import transaction, IntegrityError
from django.shortcuts import render
from django.core.paginator import Paginator, EmptyPage, PageNotAnInteger

from django.conf import settings

from .forms import BasicUploadForm, SearchResult
from .models import RawFile, Result, Pipeline
from project.models import Project

from lrg_omics.common import today
from lrg_omics.proteomics.rawtools.plotly import histograms, lines_plot
from lrg_omics.plotly_tools import (
    set_template,
    plotly_heatmap,
    plotly_fig_to_div,
    plotly_dendrogram,
    plotly_bar,
    plotly_table,
    plotly_histogram,
)


# Create your views here.
def maxquant_pipeline_view(request, project, pipeline):

    # Pattern to store form data in session
    # to make pagination work with search form
    if not request.method == "POST":
        if "search-files" in request.session:
            request.POST = request.session["search-files"]
            request.method = "POST"
        else:
            form = SearchResult(request.POST)
            maxquant_runs =  Result.objects.filter(
                raw_file__pipeline__slug=pipeline
            )

    if request.method == "POST":
        request.session["search-files"] = request.POST
        form = SearchResult(request.POST)
        if form.is_valid():
            maxquant_runs = Result.objects.filter(
                raw_file__pipeline__slug=pipeline,
                raw_file__orig_file__iregex=form.cleaned_data["raw_file"],
            )

    page = request.GET.get("page", 1)
    paginator = Paginator(maxquant_runs, settings.PAGINATE)

    try:
        maxquant_runs = paginator.page(page)
    except PageNotAnInteger:
        maxquant_runs = paginator.page(1)
    except EmptyPage:
        maxquant_runs = paginator.page(paginator.num_pages)

    project = Project.objects.get(slug=project)
    pipeline = Pipeline.objects.get(project=project, slug=pipeline)
    context = dict(maxquant_runs=maxquant_runs, project=project, pipeline=pipeline)
    context["home_title"] = settings.HOME_TITLE
    context["form"] = form
    return render(request, "proteomics/pipeline_detail.html", context)


def pipeline_download_file(request, pk):

    pipeline_pk = pk

    maxquant_runs = Result.objects.filter(
        raw_file__pipeline__pk=pipeline_pk, raw_file__use_downstream=True
    )

    fn = request.GET.get("file")

    pipeline = Pipeline.objects.get(pk=pipeline_pk)
    project = pipeline.project
    project_name = project.name
    pipeline_name = pipeline.name

    stream = BytesIO()
    dfs = []

    for mq_run in maxquant_runs:
        df = mq_run.get_data_from_file(fn)
        if df is None:
            continue
        dfs.append(df)

    if dfs == []:
        raise Http404(f"No file named {fn} found on the server.")

    data = pd.concat(dfs).set_index("RawFile").reset_index()
    stream.write(data.to_csv(index=False).encode())
    stream.seek(0)

    response = HttpResponse(stream, content_type="text/csv")

    fn = f"{today()}_{project}_{pipeline}__{fn.replace('.txt', '')}.csv"
    response["Content-Disposition"] = 'attachment; filename="{}"'.format(fn)

    return response


class ResultDetailView(LoginRequiredMixin, generic.DetailView):
    model = Result
    template_name = "proteomics/maxquant_detail.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        mq_run = context["object"]
        path = mq_run.output_dir_maxquant
        path_rt = mq_run.output_dir_rawtools

        context["name"] = context["object"].name
        context["project"] = mq_run.raw_file.pipeline.project
        context["pipeline"] = mq_run.raw_file.pipeline
        raw_fn = mq_run.raw_file
        context["raw_file"] = raw_fn

        figures = []

        fn = f"{path_rt}/{raw_fn}_Ms_TIC_chromatogram.txt"
        if isfile(fn):
            df = (
                pd.read_csv(fn, sep="\t")
                .rename(columns={"RetentionTime": "Retention time"})
                .set_index("Retention time")
            )
            fig = lines_plot(df, cols=["Intensity"], title=f"Ms TIC chromatogram")
            figures.append(plotly_fig_to_div(fig))
            fig = histograms(df, cols=["Intensity"], title=f"Ms TIC histogram")
            figures.append(plotly_fig_to_div(fig))

        fn = f"{path_rt}/{raw_fn}_Ms2_TIC_chromatogram.txt"
        if isfile(fn):
            df = (
                pd.read_csv(fn, sep="\t")
                .rename(columns={"RetentionTime": "Retention time"})
                .set_index("Retention time")
            )
            fig = lines_plot(df, cols=["Intensity"], title=f"Ms2 TIC chromatogram")
            figures.append(plotly_fig_to_div(fig))
            fig = histograms(df, cols=["Intensity"], title=f"Ms2 TIC histogram")
            figures.append(plotly_fig_to_div(fig))

        fn = f"{path}/evidence.txt"
        if isfile(fn):
            msms = pd.read_csv(fn, sep="\t").set_index("Retention time").sort_index()
            cols = [
                "Length",
                #'Oxidation (M)', 'Missed cleavages', 'MS/MS m/z',
                "Charge",
                "m/z",
                "Mass",
            ]
            for col in cols:
                fig = lines_plot(msms, cols=[col], title=f"Evidence: {col}")
                figures.append(plotly_fig_to_div(fig))
                fig = histograms(msms, cols=[col], title=f"Evidence: {col} (histogram)")
                figures.append(plotly_fig_to_div(fig))

        fn = f"{path}/msmsScans.txt"
        if isfile(fn):
            msms = pd.read_csv(fn, sep="\t").set_index("Retention time")
            cols = [
                #'Total ion current',
                #'m/z', 'Base peak intensity'
            ]
            for col in cols:
                fig = lines_plot(msms, cols=[col], title=f"MSMS: {col}")
                figures.append(plotly_fig_to_div(fig))

        fn = f"{path}/peptides.txt"
        if isfile(fn):
            peptides = pd.read_csv(fn, sep="\t")
            cols = ["Length", "Mass"]
            for col in cols:
                # fig = lines_plot(peptides, cols=[col], title=f'Peptide: {col}')
                # figures.append( plotly_fig_to_div(fig) )
                fig = histograms(
                    peptides, cols=[col], title=f"Peptide: {col} (histogram)"
                )
                figures.append(plotly_fig_to_div(fig))

        fn = f"{path}/proteinGroups.txt"
        if isfile(fn):
            proteins = pd.read_csv(fn, sep="\t")
            cols = ["Mol. weight [kDa]", "Unique sequence coverage [%]"]
            for col in cols:
                # fig = lines_plot(proteins, cols=[col], title=f'Protein: {col}')
                # figures.append( plotly_fig_to_div(fig) )
                fig = histograms(
                    proteins, cols=[col], title=f"Protein: {col} (histogram)"
                )
                figures.append(plotly_fig_to_div(fig))

        context["figures"] = figures
        context["home_title"] = settings.HOME_TITLE
        return context


def maxquant_download(request, pk):
    mq_run = Result.objects.get(pk=pk)
    response = HttpResponse(mq_run.download, content_type="application/zip")
    fn = f"{mq_run.name}.zip"
    response["Content-Disposition"] = 'attachment; filename="{}"'.format(fn)
    return response


class UploadRaw(LoginRequiredMixin, View):
    def get(self, request, pk=None):
        pipeline = Pipeline.objects.get(pk=pk)
        project = pipeline.project
        context = {
            "project": project,
            "home_title": settings.HOME_TITLE,
            "pipeline": pipeline,
        }
        return render(request, "proteomics/upload.html", context)

    def post(self, request):
        form = BasicUploadForm(self.request.POST, self.request.FILES)
        logging.warning("RAW upload")

        project_id = request.POST.get("project")
        pipeline_id = request.POST.get("pipeline")

        logging.warning(f"Upload to: {project_id} / {pipeline_id}")

        pipeline = Pipeline.objects.get(pk=pipeline_id)
        project = pipeline.project

        logging.warning(f"Upload to: {project.name} / {pipeline.name}")

        if form.is_valid():
            _file = form.cleaned_data["orig_file"]
            _file = RawFile.objects.create(orig_file=_file, pipeline=pipeline)

            if str(_file.name).lower().endswith(".raw"):
                _file.save()
            data = {"is_valid": True, "name": str(_file.name), "url": str(_file.path)}
        else:
            data = {"is_valid": False}
        return JsonResponse(data)
