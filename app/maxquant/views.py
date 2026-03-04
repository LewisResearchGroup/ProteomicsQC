from os.path import isfile
from pathlib import Path as P
import hashlib
from uuid import uuid4
import pandas as pd
import logging
import numpy as np
import re
try:
    import polars as pl
except Exception:  # pragma: no cover - fallback when dependency is unavailable
    pl = None

from io import BytesIO

from django.http import (
    HttpResponse,
    JsonResponse,
    Http404,
    HttpResponseForbidden,
)
from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib.auth.decorators import login_required
from django.views import generic, View
from django.views.decorators.http import require_POST
from django.db import transaction, IntegrityError
from django.shortcuts import render, get_object_or_404, redirect
from django.core.paginator import Paginator, EmptyPage, PageNotAnInteger
from django.core.cache import cache
from django.db.models import Q

from django.conf import settings

import plotly.graph_objects as go
from .forms import BasicUploadForm, SearchResult
from .models import RawFile, Result, Pipeline
from project.models import Project

from omics.common import today
from omics.proteomics.rawtools.plotly import histograms, lines_plot
from omics.plotly_tools import plotly_fig_to_div


# Create your views here.
def _projects_for_user(user):
    queryset = Project.objects.all()
    if user.is_staff or user.is_superuser:
        return queryset
    return queryset.filter(Q(created_by_id=user.id) | Q(users=user)).distinct()


def _pipelines_for_user(user):
    queryset = Pipeline.objects.select_related("project")
    if user.is_staff or user.is_superuser:
        return queryset
    return queryset.filter(
        Q(project__created_by_id=user.id) | Q(project__users=user)
    ).distinct()


def _results_for_user(user):
    queryset = Result.objects.select_related(
        "raw_file__pipeline__project",
        "raw_file__created_by",
    )
    if user.is_staff or user.is_superuser:
        return queryset
    return queryset.filter(raw_file__created_by_id=user.id).distinct()


def _demo_chromatogram_frame(multiplier=1, ms2=False):
    rows = []
    for minute in range(0, 91):
        if ms2:
            centers = (
                (22 + multiplier, 90000, 4500),
                (49 + multiplier, 180000, 5200),
                (72 + multiplier, 110000, 4000),
            )
        else:
            centers = (
                (18 + multiplier, 140000, 6000),
                (52 + multiplier, 240000, 7000),
                (74 + multiplier, 120000, 5000),
            )
        intensity = 0
        for center, height, slope in centers:
            intensity += max(0, height - abs(minute - center) * slope)
        rows.append({"Retention time": minute, "Intensity": intensity})
    return pd.DataFrame(rows).set_index("Retention time")


@login_required
def maxquant_pipeline_view(request, project, pipeline):
    is_admin_session = request.user.is_staff or request.user.is_superuser
    selected_uploader_filter = request.GET.get("uploader", "").strip()
    selected_uploader_id = None
    if is_admin_session and selected_uploader_filter:
        try:
            selected_uploader_id = int(selected_uploader_filter)
        except ValueError:
            selected_uploader_filter = ""

    # Pattern to store form data in session
    # to make pagination work with search form
    def _runs_queryset(raw_file_regex=""):
        queryset = _results_for_user(request.user).filter(
            raw_file__pipeline__slug=pipeline,
            raw_file__pipeline__project__slug=project,
        )
        if raw_file_regex:
            queryset = queryset.filter(
                raw_file__orig_file__iregex=raw_file_regex,
            )
        if selected_uploader_id is not None:
            queryset = queryset.filter(raw_file__created_by_id=selected_uploader_id)
        return queryset.order_by("-created")

    maxquant_runs = _runs_queryset()

    if not request.method == "POST":
        if "search-files" in request.session:
            request.POST = request.session["search-files"]
            request.method = "POST"
        else:
            form = SearchResult(request.POST)

    if request.method == "POST":
        request.session["search-files"] = request.POST
        form = SearchResult(request.POST)
        if form.is_valid():
            maxquant_runs = _runs_queryset(
                raw_file_regex=form.cleaned_data["raw_file"]
            )

    page = request.GET.get("page", 1)
    paginator = Paginator(maxquant_runs, settings.PAGINATE)

    try:
        maxquant_runs = paginator.page(page)
    except PageNotAnInteger:
        maxquant_runs = paginator.page(1)
    except EmptyPage:
        maxquant_runs = paginator.page(paginator.num_pages)

    project = get_object_or_404(_projects_for_user(request.user), slug=project)
    pipeline = get_object_or_404(
        _pipelines_for_user(request.user), project=project, slug=pipeline
    )
    missing_raw_files = RawFile.objects.filter(
        pipeline=pipeline, result__isnull=True
    ).select_related("created_by").order_by("-created")
    if not is_admin_session:
        missing_raw_files = missing_raw_files.filter(created_by_id=request.user.id)
    elif selected_uploader_id is not None:
        missing_raw_files = missing_raw_files.filter(created_by_id=selected_uploader_id)

    # Adaptive queue-status strictness:
    # for small pages we allow stricter queue inspection; for larger workloads
    # we avoid expensive broker inspect calls in request/response path.
    visible_run_count = len(maxquant_runs.object_list)
    active_run_count = _results_for_user(request.user).filter(
        raw_file__pipeline__slug=pipeline.slug,
        raw_file__pipeline__project__slug=project.slug,
    ).filter(
        Q(maxquant_task_submitted_at__isnull=False)
        | Q(rawtools_metrics_task_submitted_at__isnull=False)
        | Q(rawtools_qc_task_submitted_at__isnull=False)
    ).count()
    max_visible_runs_for_inspect = int(
        getattr(settings, "RESULT_STATUS_INSPECT_MAX_VISIBLE_RUNS", 25)
    )
    max_active_runs_for_inspect = int(
        getattr(settings, "RESULT_STATUS_INSPECT_MAX_ACTIVE_RUNS", 12)
    )
    queue_check_mode = (
        "on"
        if (
            visible_run_count <= max_visible_runs_for_inspect
            and active_run_count <= max_active_runs_for_inspect
        )
        else "off"
    )
    for maxquant_run in maxquant_runs.object_list:
        maxquant_run._visible_run_count = visible_run_count
        maxquant_run._active_run_count = active_run_count
        maxquant_run._queue_check_mode = queue_check_mode

    context = dict(
        maxquant_runs=maxquant_runs, project=project, pipeline=pipeline
    )
    uploader_filters = []
    if is_admin_session:
        uploader_rows = (
            RawFile.objects.filter(pipeline=pipeline)
            .select_related("created_by")
            .values("created_by_id", "created_by__email")
            .distinct()
            .order_by("created_by__email")
        )
        uploader_filters = [
            {
                "id": row["created_by_id"],
                "label": row["created_by__email"] or "Unknown user",
            }
            for row in uploader_rows
            if row["created_by_id"] is not None
        ]
    context["home_title"] = settings.HOME_TITLE
    context["form"] = form
    context["is_admin_session"] = is_admin_session
    context["uploader_filters"] = uploader_filters
    context["selected_uploader_filter"] = selected_uploader_id
    context["missing_raw_files_count"] = missing_raw_files.count()
    context["missing_raw_files"] = missing_raw_files
    query_params = request.GET.copy()
    query_params.pop("page", None)
    context["pipeline_querystring"] = query_params.urlencode()
    return render(request, "proteomics/pipeline_detail.html", context)


@login_required
def pipeline_download_file(request, pk):

    pipeline_pk = pk

    maxquant_runs = _results_for_user(request.user).filter(
        raw_file__pipeline__pk=pipeline_pk, raw_file__use_downstream=True
    )

    fn = request.GET.get("file")

    pipeline = get_object_or_404(
        _pipelines_for_user(request.user), pk=pipeline_pk
    )
    project = pipeline.project

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

    def get_queryset(self):
        return _results_for_user(self.request.user)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        mq_run = context["object"]
        # Detail rendering should not block on broker inspect calls.
        mq_run._queue_check_mode = "off"
        path = mq_run.output_dir_maxquant
        path_rt = mq_run.output_dir_rawtools

        context["name"] = context["object"].name
        context["project"] = mq_run.raw_file.pipeline.project
        context["pipeline"] = mq_run.raw_file.pipeline
        raw_fn = mq_run.raw_file
        context["raw_file"] = raw_fn

        # Cache rendered summary/figures per run and source-file freshness.
        source_files = [
            f"{path_rt}/{raw_fn}_Ms_TIC_chromatogram.txt",
            f"{path_rt}/{raw_fn}_Ms2_TIC_chromatogram.txt",
            f"{path}/summary.txt",
            f"{path}/evidence.txt",
            f"{path}/peptides.txt",
            f"{path}/proteinGroups.txt",
        ]
        freshness_parts = []
        for fn in source_files:
            if isfile(fn):
                try:
                    freshness_parts.append(f"{fn}:{int(P(fn).stat().st_mtime)}")
                except OSError:
                    freshness_parts.append(f"{fn}:0")
            else:
                freshness_parts.append(f"{fn}:missing")
        freshness_token = hashlib.sha1(
            "|".join(freshness_parts).encode("utf-8")
        ).hexdigest()
        cache_key = (
            f"mq-detail-v3:{mq_run.pk}:{mq_run.input_source}:{freshness_token}"
        )
        cached = cache.get(cache_key)
        if cached:
            context["figures"] = cached["figures"]
            context["figure_sections"] = cached["figure_sections"]
            context["summary_stats"] = cached["summary_stats"]
            context["home_title"] = settings.HOME_TITLE
            return context

        figures = []
        summary_stats = []
        figure_sections = []
        plot_help_by_title = {
            "MS TIC chromatogram": "Total ion current over retention time "
            "for MS1 scans.",
            "MS2 TIC chromatogram": "Total ion current over retention time "
            "for MS2 scans.",
            "Missed cleavages": "Number of missed enzymatic cleavages "
            "in identified peptides.",
            "Charge states": "Charge state distribution of identified "
            "precursor ions.",
            "Uncalibrated - Calibrated m/z [ppm]": (
                "Difference between uncalibrated and recalibrated precursor "
                "m/z in ppm; indicates mass drift corrected by MaxQuant."
            ),
            "Retention time calibration": (
                "Difference between uncalibrated and recalibrated retention "
                "time in minutes; indicates retention-time drift corrected "
                "by MaxQuant."
            ),
            "Peptide length distribution": "Length distribution of identified "
            "peptide sequences.",
            "Channel intensity distribution (peptides)": (
                "Distribution of channel reporter intensities from peptides "
                "(log2-transformed as log(1+intensity))."
            ),
            "Channel intensity distribution (protein groups)": (
                "Distribution of channel reporter intensities from protein "
                "groups (log2-transformed as log(1+intensity))."
            ),
            "Number of Peptides identified per Protein": (
                "Distribution of peptide counts per protein group. "
                "Values above 25 are grouped into the top bin."
            ),
            "Andromeda Scores": "Distribution of protein-group "
            "Andromeda scores.",
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
            "Number of Peptides identified per Protein": "Identification "
            "Quality",
            "Uncalibrated - Calibrated m/z [ppm]": "Calibration",
            "Retention time calibration": "Calibration",
            "Channel intensity distribution (peptides)": "Quantification",
            "Channel intensity distribution (protein groups)": (
                "Quantification"
            ),
        }

        def add_figure(fig, help_text=None):
            title_text = ""
            if hasattr(fig, "layout") and hasattr(fig.layout, "title"):
                title_text = fig.layout.title.text or ""

            # Normalize figure heights server-side to avoid excessive
            # whitespace and inconsistent client-side resizing behavior.
            raw_height = getattr(fig.layout, "height", None)
            try:
                height = int(raw_height) if raw_height is not None else None
            except (TypeError, ValueError):
                height = None

            if height is None:
                fig.update_layout(height=420, autosize=True)
            elif height > 560:
                fig.update_layout(height=520, autosize=True)
            elif height < 140:
                # Keep compact spark/bar strips as configured.
                pass
            else:
                fig.update_layout(autosize=True)

            resolved_help = (
                help_text
                if help_text is not None
                else plot_help_by_title.get(title_text)
            )
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
                col
                for col in df.columns
                if col.startswith("Reporter intensity corrected ")
            ]
            reporter_cols = [
                col
                for col in df.columns
                if col.startswith("Reporter intensity ")
            ]
            intensity_channel_cols = [
                col
                for col in df.columns
                if col.startswith("Intensity ") and col != "Intensity"
            ]
            channel_cols = (
                reporter_corrected_cols
                or reporter_cols
                or intensity_channel_cols
            )
            # Some exports include both generic and experiment-scoped
            # channel columns (e.g. "Reporter intensity corrected 1" and
            # "... 1 <experiment>"). Keep one column per numeric channel
            # and prefer experiment-scoped names.
            if channel_cols:
                channel_by_number = {}
                for col in channel_cols:
                    match = re.search(r"\b(\d+)\b", col)
                    if match is None:
                        continue
                    number = int(match.group(1))
                    current = channel_by_number.get(number)
                    if current is None:
                        channel_by_number[number] = col
                        continue
                    current_has_suffix = bool(
                        re.search(rf"\b{number}\b\s+\S+", current)
                    )
                    new_has_suffix = bool(
                        re.search(rf"\b{number}\b\s+\S+", col)
                    )
                    if new_has_suffix and not current_has_suffix:
                        channel_by_number[number] = col
                if channel_by_number:
                    channel_cols = [
                        channel_by_number[n] for n in sorted(channel_by_number)
                    ]
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
                intensity_long["Channel"],
                categories=channel_order,
                ordered=True,
            )
            intensity_long = intensity_long.sort_values("Channel")
            base_labels = [short_channel_name(col) for col in channel_order]
            label_counts = {}
            unique_labels = []
            for label in base_labels:
                label_counts[label] = label_counts.get(label, 0) + 1
                if label_counts[label] == 1:
                    unique_labels.append(label)
                else:
                    unique_labels.append(f"{label} ({label_counts[label]})")
            intensity_long["log2(Intensity)"] = np.log1p(
                intensity_long["Intensity"]
            )

            fig = go.Figure()
            fig.add_trace(
                go.Box(
                    x=intensity_long["Channel"],
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
                categoryarray=channel_order,
                tickmode="array",
                tickvals=channel_order,
                ticktext=unique_labels,
            )
            fig.update_yaxes(automargin=True, rangemode="tozero")
            add_figure(fig)

        def summary_value(summary_df, *candidates):
            """Return first matching summary value using tolerant
            column matching."""
            if summary_df.empty:
                return None
            for candidate in candidates:
                if candidate in summary_df.columns:
                    return summary_df.loc[0, candidate]
            normalized = {
                str(col).strip().casefold(): col for col in summary_df.columns
            }
            for candidate in candidates:
                key = str(candidate).strip().casefold()
                if key in normalized:
                    return summary_df.loc[0, normalized[key]]
            return None

        def read_tsv_selected(fn, exact_cols=None, prefix_cols=None):
            exact_cols = exact_cols or []
            prefix_cols = prefix_cols or []
            available_cols = []
            if pl is not None:
                try:
                    available_cols = list(
                        pl.read_csv(fn, separator="\t", n_rows=0).columns
                    )
                except Exception:
                    available_cols = []
            if not available_cols:
                try:
                    header = pd.read_csv(fn, sep="\t", nrows=0)
                    available_cols = list(header.columns)
                except Exception:
                    return pd.DataFrame()
            selected = [col for col in exact_cols if col in available_cols]
            if prefix_cols:
                selected.extend(
                    [
                        col
                        for col in available_cols
                        if any(col.startswith(prefix) for prefix in prefix_cols)
                    ]
                )
            # Preserve order and uniqueness
            selected = list(dict.fromkeys(selected))
            if not selected:
                return pd.DataFrame()
            if pl is not None:
                try:
                    pl_df = (
                        pl.scan_csv(
                            fn, separator="\t", has_header=True
                        )
                        .select([pl.col(col) for col in selected])
                        .collect(streaming=True)
                    )
                    return pl_df.to_pandas()
                except Exception:
                    pass
            try:
                return pd.read_csv(
                    fn,
                    sep="\t",
                    usecols=selected,
                    low_memory=False,
                )
            except Exception:
                return pd.DataFrame()

        fn = f"{path_rt}/{raw_fn}_Ms_TIC_chromatogram.txt"
        df_ms = pd.DataFrame()
        if isfile(fn):
            df_ms = read_tsv_selected(
                fn, exact_cols=["RetentionTime", "Intensity"]
            )
            if "RetentionTime" in df_ms.columns:
                df_ms = (
                    df_ms.rename(columns={"RetentionTime": "Retention time"})
                    .set_index("Retention time")
                )
        if df_ms.empty and mq_run.input_source == "demo":
            df_ms = _demo_chromatogram_frame(multiplier=(mq_run.raw_file.pk or 1))
        if not df_ms.empty:
            summary_stats.append({"label": "MS scans", "value": len(df_ms)})
            fig = lines_plot(
                df_ms, cols=["Intensity"], title="MS TIC chromatogram"
            )
            add_figure(fig)

        fn = f"{path_rt}/{raw_fn}_Ms2_TIC_chromatogram.txt"
        df_ms2 = pd.DataFrame()
        if isfile(fn):
            df_ms2 = read_tsv_selected(
                fn, exact_cols=["RetentionTime", "Intensity"]
            )
            if "RetentionTime" in df_ms2.columns:
                df_ms2 = (
                    df_ms2.rename(columns={"RetentionTime": "Retention time"})
                    .set_index("Retention time")
                )
        if df_ms2.empty and mq_run.input_source == "demo":
            df_ms2 = _demo_chromatogram_frame(
                multiplier=(mq_run.raw_file.pk or 1) + 3,
                ms2=True,
            )
        if not df_ms2.empty:
            fig = lines_plot(
                df_ms2, cols=["Intensity"], title="MS2 TIC chromatogram"
            )
            add_figure(fig)

        fn = f"{path}/summary.txt"
        if isfile(fn):
            summary = pd.read_csv(fn, sep="\t")
            msms_submitted = summary_value(
                summary, "MS/MS submitted", "MS/MS Submitted"
            )
            msms_identified = summary_value(
                summary, "MS/MS identified", "MS/MS Identified"
            )
            msms_identified_pct = summary_value(
                summary,
                "MS/MS identified [%]",
                "MS/MS Identified [%]",
                "MS/MS identified [%] ",
            )

            if msms_submitted is not None:
                summary_stats.append(
                    {"label": "MS/MS scans", "value": msms_submitted}
                )
            if msms_identified is not None:
                summary_stats.append(
                    {"label": "MS/MS identified", "value": msms_identified}
                )
            if msms_identified_pct is not None:
                summary_stats.append(
                    {
                        "label": "MS/MS identified [%]",
                        "value": msms_identified_pct,
                    }
                )

        fn = f"{path}/evidence.txt"
        if isfile(fn):
            msms = read_tsv_selected(
                fn,
                exact_cols=[
                    "Retention time",
                    "Missed cleavages",
                    "Uncalibrated - Calibrated m/z [ppm]",
                    "Charge",
                ],
            )
            if "Retention time" in msms.columns:
                msms = msms.set_index("Retention time").sort_index()

            if "Missed cleavages" in msms.columns:
                missed = (
                    msms["Missed cleavages"]
                    .fillna(0)
                    .astype(int)
                    .clip(lower=0)
                )
                buckets = [0, 1, 2]
                counts = []
                labels = []
                # Palette aligned with the rose color used in the other
                # distribution plots
                colors = ["#B58E8E", "#A87F7F", "#C6A3A3", "#D8BFBF"]
                for val in buckets:
                    labels.append(str(val))
                    counts.append(int((missed == val).sum()))
                labels.append("3+")
                counts.append(int((missed >= 3).sum()))

                fig = go.Figure()
                for idx, (label, count) in enumerate(zip(labels, counts)):
                    bar_value = (
                        count if count > 0 else 0.0001
                    )  # keep legend entry visible
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
                fig.update_yaxes(
                    showticklabels=False, showgrid=False, zeroline=False
                )
                fig.update_xaxes(visible=False, showgrid=False, zeroline=False)
                fig.update_traces(
                    marker_line_width=0, selector=dict(type="bar")
                )
                add_figure(fig)

            mz_delta_col = "Uncalibrated - Calibrated m/z [ppm]"
            if mz_delta_col in msms.columns:
                mz_delta = pd.to_numeric(
                    msms[mz_delta_col], errors="coerce"
                ).dropna()
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
            #     rt_cal = pd.to_numeric(
            #         msms[rt_cal_col], errors="coerce"
            #     ).dropna()
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
                charge = (
                    pd.to_numeric(msms["Charge"], errors="coerce")
                    .fillna(0)
                    .astype(int)
                    .clip(lower=0)
                )
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
                    bar_value = (
                        count if count > 0 else 0.0001
                    )  # keep legend entry visible
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
                fig.update_yaxes(
                    showticklabels=False, showgrid=False, zeroline=False
                )
                fig.update_xaxes(visible=False, showgrid=False, zeroline=False)
                fig.update_traces(
                    marker_line_width=0, selector=dict(type="bar")
                )
                add_figure(fig)

        # fn = f"{path}/msmsScans.txt"
        # if isfile(fn):
        #     msms = pd.read_csv(fn, sep="\t").set_index("Retention time")
        #     summary_stats.append(
        #         {"label": "MS/MS scans (msmsScans)", "value": len(msms)}
        #     )
        #     cols = [
        #           'Total ion current',
        #           'm/z', 'Base peak intensity'
        #     ]
        #     for col in cols:
        #         fig = lines_plot(msms, cols=[col], title=f"MSMS: {col}")
        #         figures.append(plotly_fig_to_div(fig))

        fn = f"{path}/peptides.txt"
        if isfile(fn):
            peptides = read_tsv_selected(
                fn,
                exact_cols=["Length"],
                prefix_cols=[
                    "Reporter intensity corrected ",
                    "Reporter intensity ",
                    "Intensity ",
                ],
            )

            if "Length" in peptides.columns:
                peptide_lengths = pd.to_numeric(
                    peptides["Length"], errors="coerce"
                ).dropna()
                if not peptide_lengths.empty:
                    peptides_binned = pd.DataFrame({"Length": peptide_lengths})
                    fig = histograms(
                        peptides_binned,
                        cols=["Length"],
                        title="Peptide length distribution",
                        xbins={
                            "start": 0.5,
                            "end": float(peptide_lengths.max()) + 0.5,
                            "size": 1,
                        },
                    )
                    add_figure(fig)

            add_channel_intensity_boxplot(
                peptides, "Channel intensity distribution (peptides)"
            )

        fn = f"{path}/proteinGroups.txt"
        if isfile(fn):
            proteins = read_tsv_selected(
                fn,
                exact_cols=["Peptides", "Score"],
                prefix_cols=[
                    "Reporter intensity corrected ",
                    "Reporter intensity ",
                    "Intensity ",
                ],
            )
            summary_stats.append({"label": "Protein groups", "value": len(proteins)})

            add_channel_intensity_boxplot(
                proteins, "Channel intensity distribution (protein groups)"
            )

            if "Peptides" in proteins.columns:
                peptides_capped = proteins["Peptides"].fillna(0).clip(upper=25)
                proteins_binned = proteins.copy()
                proteins_binned["Peptides (<=25, 25+)"] = peptides_capped

                fig = histograms(
                    proteins_binned,
                    cols=["Peptides (<=25, 25+)"],
                    title="Number of Peptides identified per Protein",
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
        cache.set(
            cache_key,
            {
                "figures": figures,
                "figure_sections": figure_sections,
                "summary_stats": summary_stats,
            },
            timeout=600,
        )
        return context


@login_required
def maxquant_download(request, pk):
    mq_run = get_object_or_404(_results_for_user(request.user), pk=pk)
    response = HttpResponse(mq_run.download, content_type="application/zip")
    fn = f"{mq_run.name}.zip"
    response["Content-Disposition"] = 'attachment; filename="{}"'.format(fn)
    return response


class UploadRaw(LoginRequiredMixin, View):
    def get(self, request, pk=None):
        pipeline = get_object_or_404(_pipelines_for_user(request.user), pk=pk)
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

        pipeline = get_object_or_404(
            _pipelines_for_user(request.user), pk=pipeline_id
        )
        project = pipeline.project

        logging.warning(f"Upload to: {project.name} / {pipeline.name}")

        if form.is_valid():
            uploaded_file = form.cleaned_data["orig_file"]

            def _logical_raw_name(value):
                basename = P(str(value)).name.lower()
                match = re.match(r"^[0-9a-f]{32}_(.+)$", basename)
                if match:
                    return match.group(1)
                return basename

            uploaded_basename = _logical_raw_name(uploaded_file.name)

            # If a prior run with the same basename exists for this uploader and
            # pipeline but its Result was deleted, restore that Result instead of
            # creating a duplicate RawFile row.
            missing_result_raw = None
            for candidate in (
                RawFile.objects.filter(
                    pipeline=pipeline,
                    result__isnull=True,
                )
                .only("id", "orig_file", "created_by")
                .order_by("-id")
            ):
                candidate_owner_id = getattr(candidate, "created_by_id", None)
                owner_matches = candidate_owner_id == request.user.id
                if not owner_matches:
                    continue
                if _logical_raw_name(candidate.orig_file.name) == uploaded_basename:
                    missing_result_raw = candidate
                    break

            if missing_result_raw is not None:
                result, _ = Result.objects.get_or_create(
                    raw_file=missing_result_raw,
                    defaults={
                        "created_by": request.user,
                        "input_source": "upload",
                    },
                )
                data = {
                    "is_valid": True,
                    "name": str(missing_result_raw.logical_name),
                    "url": str(missing_result_raw.path),
                    "result_url": result.url,
                    "result_pk": result.pk,
                    "already_exists": True,
                    "restored_result": True,
                }
                return JsonResponse(data)

            # Always create a fresh run, even for same file names.
            # Keep unique file names in storage to avoid uniqueness collisions.
            uploaded_file.name = f"{uuid4().hex}_{P(uploaded_file.name).name}"

            try:
                with transaction.atomic():
                    raw_file = RawFile(
                        orig_file=uploaded_file,
                        pipeline=pipeline,
                        created_by=request.user,
                    )
                    # Ensure new uploads never fall back into legacy name-based paths.
                    raw_file._force_namespaced_storage = True
                    raw_file.save()
            except IntegrityError as exc:
                data = {
                    "is_valid": False,
                    "error": f"Could not save file: {exc}",
                }
                return JsonResponse(data, status=500)

            result, _ = Result.objects.get_or_create(
                raw_file=raw_file,
                defaults={
                    "created_by": request.user,
                    "input_source": "upload",
                },
            )
            data = {
                "is_valid": True,
                "name": str(raw_file.logical_name),
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
        return HttpResponseForbidden(
            "You cannot cancel jobs started by another user."
        )
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
def queue_existing_run(request, pk):
    result = get_object_or_404(_results_for_user(request.user), pk=pk)
    can_queue = (
        request.user.is_superuser
        or request.user.is_staff
        or result.raw_file.created_by_id == request.user.id
    )
    if not can_queue:
        return HttpResponseForbidden(
            "You cannot queue jobs for files uploaded by another user."
        )
    if result.input_source == "demo":
        return JsonResponse(
            {
                "is_valid": False,
                "error": "Demo runs are seeded examples and cannot be requeued.",
                "status": result.overall_status,
                "run": result.name,
            },
            status=409,
        )
    if result.has_active_stage:
        return JsonResponse(
            {
                "is_valid": False,
                "error": "Run is already queued or running.",
                "status": result.overall_status,
                "run": result.name,
            },
            status=409,
        )

    # Force a full rerun by recreating stage outputs.
    result.run_maxquant(rerun=True)
    result.run_rawtools_metrics(rerun=True)
    result.run_rawtools_qc(rerun=True)
    return JsonResponse(
        {
            "is_valid": True,
            "status": result.overall_status,
            "run": result.name,
        }
    )


@login_required
@require_POST
def cancel_pipeline_jobs(request, pk):
    pipeline = get_object_or_404(_pipelines_for_user(request.user), pk=pk)
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


@login_required
@require_POST
def delete_raw_file(request, pk):
    raw_file = get_object_or_404(
        RawFile.objects.select_related("pipeline__project").filter(
            pipeline__in=_pipelines_for_user(request.user)
        ),
        pk=pk,
    )
    can_delete = (
        request.user.is_superuser
        or request.user.is_staff
        or raw_file.created_by_id == request.user.id
    )
    if not can_delete:
        return HttpResponseForbidden(
            "You cannot delete files uploaded by another user."
        )

    result = Result.objects.filter(raw_file=raw_file).first()
    revoked = 0
    if result is not None and result.has_active_stage:
        revoked = result.cancel_active_jobs()

    filename = raw_file.name
    raw_file.delete()

    return JsonResponse(
        {
            "is_valid": True,
            "deleted": filename,
            "revoked_tasks": revoked,
        }
    )


@login_required
@require_POST
def queue_missing_raw_run(request, pk):
    raw_file = get_object_or_404(
        RawFile.objects.select_related("pipeline__project").filter(
            pipeline__in=_pipelines_for_user(request.user)
        ),
        pk=pk,
    )
    result, created = Result.objects.get_or_create(
        raw_file=raw_file, defaults={"input_source": "upload"}
    )
    return JsonResponse(
        {
            "is_valid": True,
            "created": created,
            "run": raw_file.name,
            "result_pk": result.pk,
            "result_url": result.url,
        }
    )


@login_required
@require_POST
def queue_missing_pipeline_runs(request, pk):
    pipeline = get_object_or_404(_pipelines_for_user(request.user), pk=pk)
    missing_raw_files = list(
        RawFile.objects.filter(pipeline=pipeline, result__isnull=True)
    )
    created_results = 0

    with transaction.atomic():
        for raw_file in missing_raw_files:
            _, created = Result.objects.get_or_create(
                raw_file=raw_file, defaults={"input_source": "upload"}
            )
            if created:
                created_results += 1

    if created_results == 0:
        messages.info(
            request,
            "No missing runs were found. This pipeline already has result entries for all .raw files.",
        )
    else:
        messages.success(
            request,
            f"Queued {created_results} missing run(s) for pipeline {pipeline.name}.",
        )

    return redirect(
        "maxquant:detail",
        project=pipeline.project.slug,
        pipeline=pipeline.slug,
    )
