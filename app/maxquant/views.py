from os.path import isfile
from pathlib import Path as P
import pandas as pd
import logging
import numpy as np
import re

from io import BytesIO

from django.http import (
    HttpResponse,
    JsonResponse,
    HttpResponseNotFound,
    Http404,
    HttpResponseForbidden,
)
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib.auth.decorators import login_required
from django.views import generic, View
from django.views.decorators.http import require_POST
from django.db import transaction, IntegrityError
from django.shortcuts import render, get_object_or_404
from django.core.paginator import Paginator, EmptyPage, PageNotAnInteger

from django.conf import settings

import plotly.graph_objects as go
from .forms import BasicUploadForm, SearchResult
from .models import RawFile, Result, Pipeline
from project.models import Project

from lrg_omics.common import today
from lrg_omics.proteomics.rawtools.plotly import histograms, lines_plot
from lrg_omics.plotly_tools import (
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
            maxquant_runs = Result.objects.filter(raw_file__pipeline__slug=pipeline)

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
        summary_stats = []
        figure_sections = []
        plot_help_by_title = {
            "MS TIC chromatogram": "Total ion current over retention time for MS1 scans.",
            "MS2 TIC chromatogram": "Total ion current over retention time for MS2 scans.",
            "Missed cleavages": "Number of missed enzymatic cleavages in identified peptides.",
            "Charge states": "Charge state distribution of identified precursor ions.",
            "Uncalibrated - Calibrated m/z [ppm]": (
                "Difference between uncalibrated and recalibrated precursor m/z in ppm; "
                "indicates mass drift corrected by MaxQuant."
            ),
            "Retention time calibration": (
                "Difference between uncalibrated and recalibrated retention time in minutes; "
                "indicates retention-time drift corrected by MaxQuant."
            ),
            "Peptide length distribution": "Length distribution of identified peptide sequences.",
            "Channel intensity distribution (peptides)": (
                "Distribution of channel reporter intensities from peptides "
                "(log2-transformed as log(1+intensity))."
            ),
            "Channel intensity distribution (protein groups)": (
                "Distribution of channel reporter intensities from protein groups "
                "(log2-transformed as log(1+intensity))."
            ),
            "Number of Peptides identified per Protein": (
                "Distribution of peptide counts per protein group. Values above 25 are grouped into the top bin."
            ),
            "Andromeda Scores": "Distribution of protein-group Andromeda scores.",
        }

        section_order = [
            "Chromatography",
            "Identification Quality",
            "Calibration",
            "Quantification",
            "Other",
        ]
        section_labels = {
            "Chromatography": "Chromatography",
            "Identification Quality": "Identification quality",
            "Calibration": "Mass and retention-time calibration",
            "Quantification": "Quantification and channel intensity",
            "Other": "Other metrics",
        }
        section_by_title = {
            "MS TIC chromatogram": "Chromatography",
            "MS2 TIC chromatogram": "Chromatography",
            "Missed cleavages": "Identification Quality",
            "Charge states": "Identification Quality",
            "Peptide length distribution": "Identification Quality",
            "Andromeda Scores": "Identification Quality",
            "Number of Peptides identified per Protein": "Identification Quality",
            "Uncalibrated - Calibrated m/z [ppm]": "Calibration",
            "Retention time calibration": "Calibration",
            "Channel intensity distribution (peptides)": "Quantification",
            "Channel intensity distribution (protein groups)": "Quantification",
        }

        def add_figure(fig, help_text=None):
            title_text = ""
            if hasattr(fig, "layout") and hasattr(fig.layout, "title"):
                title_text = fig.layout.title.text or ""
            resolved_help = help_text if help_text is not None else plot_help_by_title.get(title_text)
            section = section_by_title.get(title_text, "Other")
            figures.append(
                {
                    "html": plotly_fig_to_div(fig),
                    "help": resolved_help,
                    "title": title_text,
                    "section": section,
                }
            )

        def channel_sort_key(col_name):
            base = col_name
            if col_name.startswith("Reporter intensity corrected "):
                base = col_name.replace("Reporter intensity corrected ", "")
            elif col_name.startswith("Reporter intensity "):
                base = col_name.replace("Reporter intensity ", "")
            elif col_name.startswith("Intensity "):
                base = col_name.replace("Intensity ", "")
            match = re.search(r"\b(\d+)\b", base)
            if match:
                return (0, int(match.group(1)), base)
            return (1, 10**9, base)

        def short_channel_name(col_name):
            if col_name.startswith("Reporter intensity corrected "):
                base = col_name.replace("Reporter intensity corrected ", "")
            elif col_name.startswith("Reporter intensity "):
                base = col_name.replace("Reporter intensity ", "")
            elif col_name.startswith("Intensity "):
                base = col_name.replace("Intensity ", "")
            else:
                base = col_name
            match = re.match(r"^(\d+)\b", base)
            if match:
                return f"Ch {int(match.group(1)):02d}"
            return base

        def add_channel_intensity_boxplot(df, title):
            reporter_corrected_cols = [
                col for col in df.columns if col.startswith("Reporter intensity corrected ")
            ]
            reporter_cols = [col for col in df.columns if col.startswith("Reporter intensity ")]
            intensity_channel_cols = [col for col in df.columns if col.startswith("Intensity ") and col != "Intensity"]
            channel_cols = reporter_corrected_cols or reporter_cols or intensity_channel_cols
            if not channel_cols:
                return

            intensity_long = (
                df[channel_cols]
                .apply(pd.to_numeric, errors="coerce")
                .melt(var_name="Channel", value_name="Intensity")
                .dropna()
            )
            intensity_long = intensity_long[intensity_long["Intensity"] > 0]
            if intensity_long.empty:
                return

            channel_order = sorted(channel_cols, key=channel_sort_key)
            intensity_long["Channel"] = pd.Categorical(
                intensity_long["Channel"], categories=channel_order, ordered=True
            )
            intensity_long = intensity_long.sort_values("Channel")
            intensity_long["Channel label"] = intensity_long["Channel"].apply(short_channel_name)
            channel_label_order = [short_channel_name(col) for col in channel_order]
            intensity_long["Channel label"] = pd.Categorical(
                intensity_long["Channel label"],
                categories=channel_label_order,
                ordered=True,
            )
            intensity_long["log2(Intensity)"] = np.log1p(intensity_long["Intensity"])

            fig = go.Figure()
            fig.add_trace(
                go.Box(
                    x=intensity_long["Channel label"],
                    y=intensity_long["log2(Intensity)"],
                    boxpoints="outliers",
                    jitter=0.3,
                    pointpos=0,
                    marker=dict(size=3, opacity=0, color="#B58E8E"),
                    line=dict(width=1, color="#B58E8E"),
                    fillcolor="rgba(181, 142, 142, 0.65)",
                )
            )
            fig.update_layout(
                title=title,
                xaxis_title="Channel",
                yaxis_title="log2(Intensity)",
                showlegend=False,
                height=420,
                margin=dict(l=60, r=20, t=50, b=80),
            )
            fig.update_xaxes(
                tickangle=0,
                automargin=True,
                categoryorder="array",
                categoryarray=channel_label_order,
            )
            fig.update_yaxes(automargin=True, rangemode="tozero")
            add_figure(fig)

        fn = f"{path_rt}/{raw_fn}_Ms_TIC_chromatogram.txt"
        if isfile(fn):
            df_ms = (
                pd.read_csv(fn, sep="\t")
                .rename(columns={"RetentionTime": "Retention time"})
                .set_index("Retention time")
            )
            summary_stats.append({"label": "MS scans", "value": len(df_ms)})
            fig = lines_plot(df_ms, cols=["Intensity"], title="MS TIC chromatogram")
            add_figure(fig)

        fn = f"{path_rt}/{raw_fn}_Ms2_TIC_chromatogram.txt"
        if isfile(fn):
            df_ms2 = (
                pd.read_csv(fn, sep="\t")
                .rename(columns={"RetentionTime": "Retention time"})
                .set_index("Retention time")
            )

            fig = lines_plot(df_ms2, cols=["Intensity"], title="MS2 TIC chromatogram")
            add_figure(fig)

        fn = f"{path}/summary.txt"
        if isfile(fn):
            summary = pd.read_csv(fn, sep="\t")
            summary_stats.append({"label": "MS/MS scans", "value": summary.loc[0, "MS/MS submitted"]})
            summary_stats.append({"label": "MS/MS identified", "value": summary.loc[0, "MS/MS identified"]})
            summary_stats.append({"label": "MS/MS identified [%]", "value": summary.loc[0, "MS/MS identified [%]"]})

        fn = f"{path}/evidence.txt"
        if isfile(fn):
            msms = pd.read_csv(fn, sep="\t").set_index("Retention time").sort_index()
            
            if "Missed cleavages" in msms.columns:
                missed = msms["Missed cleavages"].fillna(0).astype(int).clip(lower=0)
                buckets = [0, 1, 2]
                counts = []
                labels = []
                # Palette aligned with the rose color used in the other distribution plots
                colors = ["#B58E8E", "#A87F7F", "#C6A3A3", "#D8BFBF"]
                for val in buckets:
                    labels.append(str(val))
                    counts.append(int((missed == val).sum()))
                labels.append("3+")
                counts.append(int((missed >= 3).sum()))

                fig = go.Figure()
                for idx, (label, count) in enumerate(zip(labels, counts)):
                    bar_value = count if count > 0 else 0.0001  # keep legend entry visible
                    fig.add_trace(
                        go.Bar(
                            x=[bar_value],
                            y=["Missed cleavages"],
                            name=label,
                            showlegend=True,
                            orientation="h",
                            marker_color=colors[idx % len(colors)],
                            text=[count],
                            textposition="inside",
                        )
                    )
                fig.update_layout(
                    barmode="stack",
                    showlegend=True,
                    legend_traceorder="normal",
                    title="Missed cleavages",
                    margin=dict(l=0, r=0, t=24, b=0),
                    height=120,
                )
                fig.update_yaxes(showticklabels=False, showgrid=False, zeroline=False)
                fig.update_xaxes(visible=False, showgrid=False, zeroline=False)
                fig.update_traces(marker_line_width=0, selector=dict(type="bar"))
                add_figure(fig)

            mz_delta_col = "Uncalibrated - Calibrated m/z [ppm]"
            if mz_delta_col in msms.columns:
                mz_delta = pd.to_numeric(msms[mz_delta_col], errors="coerce").dropna()
                if not mz_delta.empty:
                    mz_delta_df = pd.DataFrame({mz_delta_col: mz_delta})
                    fig = histograms(
                        mz_delta_df,
                        cols=[mz_delta_col],
                        title="Uncalibrated - Calibrated m/z [ppm]",
                        nbinsx=80,
                    )
                    add_figure(fig)

            # rt_cal_col = "Retention time calibration"
            # if rt_cal_col in msms.columns:
            #     rt_cal = pd.to_numeric(msms[rt_cal_col], errors="coerce").dropna()
            #     if not rt_cal.empty:
            #         rt_cal_df = pd.DataFrame({rt_cal_col: rt_cal})
            #         fig = histograms(
            #             rt_cal_df,
            #             cols=[rt_cal_col],
            #             title="Retention time calibration",
            #             nbinsx=80,
            #         )
            #         add_figure(fig)

            if "Charge" in msms.columns:
                charge = pd.to_numeric(msms["Charge"], errors="coerce").fillna(0).astype(int).clip(lower=0)
                buckets = [1, 2, 3]
                counts = []
                labels = []
                colors = ["#B58E8E", "#A87F7F", "#C6A3A3", "#D8BFBF"]
                for val in buckets:
                    labels.append(str(val))
                    counts.append(int((charge == val).sum()))
                labels.append("4+")
                counts.append(int((charge >= 4).sum()))

                fig = go.Figure()
                for idx, (label, count) in enumerate(zip(labels, counts)):
                    bar_value = count if count > 0 else 0.0001  # keep legend entry visible
                    fig.add_trace(
                        go.Bar(
                            x=[bar_value],
                            y=["Charge states"],
                            name=label,
                            showlegend=True,
                            orientation="h",
                            marker_color=colors[idx % len(colors)],
                            text=[count],
                            textposition="inside",
                        )
                    )
                fig.update_layout(
                    barmode="stack",
                    showlegend=True,
                    legend_traceorder="normal",
                    title="Charge states",
                    margin=dict(l=0, r=0, t=24, b=0),
                    height=120,
                )
                fig.update_yaxes(showticklabels=False, showgrid=False, zeroline=False)
                fig.update_xaxes(visible=False, showgrid=False, zeroline=False)
                fig.update_traces(marker_line_width=0, selector=dict(type="bar"))
                add_figure(fig)

        # fn = f"{path}/msmsScans.txt"
        # if isfile(fn):
        #     msms = pd.read_csv(fn, sep="\t").set_index("Retention time")
        #     summary_stats.append({"label": "MS/MS scans (msmsScans)", "value": len(msms)})
        #     cols = [
        #           'Total ion current',
        #           'm/z', 'Base peak intensity'
        #     ]
        #     for col in cols:
        #         fig = lines_plot(msms, cols=[col], title=f"MSMS: {col}")
        #         figures.append(plotly_fig_to_div(fig))

        fn = f"{path}/peptides.txt"
        if isfile(fn):
            peptides = pd.read_csv(fn, sep="\t")

            if "Length" in peptides.columns:
                peptide_lengths = pd.to_numeric(peptides["Length"], errors="coerce").dropna()
                if not peptide_lengths.empty:
                    peptides_binned = pd.DataFrame({"Length": peptide_lengths})
                    fig = histograms(
                        peptides_binned,
                        cols=["Length"],
                        title="Peptide length distribution",
                        xbins={"start": 0.5, "end": float(peptide_lengths.max()) + 0.5, "size": 1},
                    )
                    add_figure(fig)

            add_channel_intensity_boxplot(peptides, "Channel intensity distribution (peptides)")

        fn = f"{path}/proteinGroups.txt"
        if isfile(fn):
            proteins = pd.read_csv(fn, sep="\t")
            summary_stats.append({"label": "Protein groups", "value": len(proteins)})

            add_channel_intensity_boxplot(proteins, "Channel intensity distribution (protein groups)")

            if "Peptides" in proteins.columns:
                peptides_capped = proteins["Peptides"].fillna(0).clip(upper=25)
                proteins_binned = proteins.copy()
                proteins_binned[f"Peptides (<=25, 25+)"] = peptides_capped

                fig = histograms(
                    proteins_binned,
                    cols=[f"Peptides (<=25, 25+)"],
                    title=f"Number of Peptides identified per Protein",
                    xbins={"start": 0.5, "end": 25.5, "size": 1},
                )
                add_figure(fig)
                

            if "Score" in proteins.columns:
                fig = histograms(
                    proteins,
                    cols=["Score"],
                    title="Andromeda Scores",
                    nbinsx=50,
                )
                add_figure(fig)

        grouped = {section: [] for section in section_order}
        for figure in figures:
            grouped.setdefault(figure["section"], []).append(figure)

        for section in section_order:
            items = grouped.get(section, [])
            if items:
                figure_sections.append(
                    {
                        "key": section,
                        "title": section_labels.get(section, section),
                        "figures": items,
                    }
                )

        context["figures"] = figures
        context["figure_sections"] = figure_sections
        context["summary_stats"] = summary_stats
        context["home_title"] = settings.HOME_TITLE
        return context


def maxquant_download(request, pk):
    mq_run = Result.objects.get(pk=pk)
    response = HttpResponse(mq_run.download, content_type="application/zip")
    fn = f"{mq_run.name}.zip"
    response["Content-Disposition"] = 'attachment; filename="{}"'.format(fn)
    return response


class UploadRaw(LoginRequiredMixin, View):
    def _resolve_existing_raw_file(self, pipeline, uploaded_name):
        # Raw files are stored as upload/<filename> in the FileField.
        candidate = f"upload/{P(uploaded_name).name}"
        return RawFile.objects.filter(pipeline=pipeline, orig_file=candidate).first()

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
            uploaded_file = form.cleaned_data["orig_file"]
            existing = self._resolve_existing_raw_file(pipeline, uploaded_file.name)

            if existing is not None:
                result, created = Result.objects.get_or_create(raw_file=existing)
                data = {
                    "is_valid": True,
                    "name": str(existing.name),
                    "url": str(existing.path),
                    "already_exists": True,
                    "restored_result": created,
                    "result_url": result.url,
                    "result_pk": result.pk,
                }
                return JsonResponse(data)

            try:
                with transaction.atomic():
                    raw_file = RawFile.objects.create(
                        orig_file=uploaded_file,
                        pipeline=pipeline,
                    )
            except IntegrityError:
                # Handle rare races where the same file is uploaded concurrently.
                existing = self._resolve_existing_raw_file(pipeline, uploaded_file.name)
                if existing is None:
                    data = {
                        "is_valid": False,
                        "error": "Could not save file because of a duplicate entry.",
                    }
                    return JsonResponse(data, status=409)
                result, created = Result.objects.get_or_create(raw_file=existing)
                data = {
                    "is_valid": True,
                    "name": str(existing.name),
                    "url": str(existing.path),
                    "already_exists": True,
                    "restored_result": created,
                    "result_url": result.url,
                    "result_pk": result.pk,
                }
                return JsonResponse(data)

            result, _ = Result.objects.get_or_create(raw_file=raw_file)
            data = {
                "is_valid": True,
                "name": str(raw_file.name),
                "url": str(raw_file.path),
                "result_url": result.url,
                "result_pk": result.pk,
                "already_exists": False,
                "restored_result": False,
            }
        else:
            data = {"is_valid": False}
        return JsonResponse(data)


@login_required
@require_POST
def cancel_run_jobs(request, pk):
    result = get_object_or_404(Result, pk=pk)
    can_cancel = (
        request.user.is_superuser
        or request.user.is_staff
        or result.raw_file.created_by_id == request.user.id
    )
    if not can_cancel:
        return HttpResponseForbidden("You cannot cancel jobs started by another user.")
    revoked = result.cancel_active_jobs()
    return JsonResponse(
        {
            "is_valid": True,
            "revoked_tasks": revoked,
            "status": result.overall_status,
            "run": result.name,
        }
    )


@login_required
@require_POST
def cancel_pipeline_jobs(request, pk):
    pipeline = get_object_or_404(Pipeline, pk=pk)
    runs_canceled = 0
    tasks_revoked = 0

    queryset = Result.objects.filter(raw_file__pipeline=pipeline)
    if not (request.user.is_superuser or request.user.is_staff):
        queryset = queryset.filter(raw_file__created_by_id=request.user.id)

    for result in queryset:
        if result.has_active_stage:
            tasks_revoked += result.cancel_active_jobs()
            runs_canceled += 1

    return JsonResponse(
        {
            "is_valid": True,
            "runs_canceled": runs_canceled,
            "revoked_tasks": tasks_revoked,
        }
    )
