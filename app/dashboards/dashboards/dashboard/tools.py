import os
import sys
import json
import logging
import numbers
from pathlib import Path

# from xml.etree.ElementPath import _SelectorContext
import shap
import pandas as pd
import numpy as np
import dask.dataframe as dd

from dash import dash_table as dt
from dash.dash_table.Format import Format

import plotly.graph_objects as go
import plotly.figure_factory as ff

from matplotlib import pyplot as pl

from pandas.api.types import is_numeric_dtype
from django.db import models

from api.views import (
    _dataframe_json_payload,
    _is_admin,
    _pipelines_for_user,
    _projects_for_user,
    _results_for_pipeline_mutation,
    get_protein_groups_data,
    get_protein_quant_fn,
    remove,
)
from maxquant.models import RawFile as RawFileModel
from maxquant.serializers import PipelineSerializer
from maxquant.services.qc_data import get_qc_data as orm_get_qc_data
from project.serializers import ProjectsNamesSerializer


from pycaret.anomaly import (
    setup,
    create_model,
    get_config,
    predict_model,
)

URL = os.getenv("OMICS_URL", "http://localhost:8000")

logging.info(f"Dashboard API URL:{URL}", file=sys.stderr)


def list_to_dropdown_options(values):
    return [{"label": v, "value": v} for v in values]


def table_from_dataframe(df, id="table", row_deletable=True, row_selectable="multi"):
    return dt.DataTable(
        id=id,
        columns=[
            {"name": i, "id": i, "format": Format(precision=2)} for i in df.columns
        ],
        data=df.iloc[::-1].to_dict("records"),
        sort_action="native",
        sort_mode="single",
        row_selectable=row_selectable,
        row_deletable=row_deletable,
        selected_rows=[],
        filter_action="native",
        page_action="native",
        page_current=0,
        page_size=16,
        style_table={"overflowX": "scroll"},
        export_format="csv",
        export_headers="display",
        merge_duplicate_headers=True,
        style_cell={"font_size": "10px", "padding-left": "5em", "padding-right": "5em"},
    )


def get_projects(user=None):
    if user is None:
        return []
    try:
        queryset = _projects_for_user(user)
        _json = ProjectsNamesSerializer(queryset, many=True).data
    except Exception as e:
        logging.error(f"Projects request error: {e}")
        return []
    if not isinstance(_json, list):
        return []
    output = [{"label": i["name"], "value": i["slug"]} for i in _json]
    output.sort(key=lambda o: o["label"].lower())
    return output


def get_pipelines(project, user=None):
    if user is None:
        return []
    try:
        queryset = _pipelines_for_user(user).filter(project__slug=project)
        payload = PipelineSerializer(queryset, many=True).data
        return payload if isinstance(payload, list) else []
    except Exception as e:
        logging.error(f"Pipelines request error: {e}")
        return []


def get_pipeline_uploaders(project, pipeline, user=None):
    if user is None:
        return []
    try:
        pipeline_obj = _pipelines_for_user(user).filter(
            project__slug=project,
            slug=pipeline,
        ).first()
        if pipeline_obj is None:
            return []
        queryset = RawFileModel.objects.filter(pipeline=pipeline_obj).select_related("created_by")
        if not _is_admin(user):
            queryset = queryset.filter(created_by_id=user.id)
        rows = (
            queryset.values("created_by__email")
            .distinct()
            .order_by("created_by__email")
        )
        output = []
        for row in rows:
            email = (row.get("created_by__email") or "").strip()
            if not email:
                continue
            output.append({"label": email, "value": email})
        return output
    except Exception as e:
        logging.error(f"Pipeline uploaders request error: {e}")
        return []


def get_protein_groups(
    project, pipeline, protein_names=None, columns=None, data_range=None, raw_files=None, user=None
):
    if user is None:
        return {}
    if columns is None or protein_names is None:
        return {}
    try:
        fns = get_protein_quant_fn(
            project,
            pipeline,
            data_range=data_range,
            user=user,
            raw_files=raw_files,
        )
        if len(fns) == 0:
            return {}
        columns = list(columns)
        if "Reporter intensity corrected" in columns:
            df = pd.read_parquet(fns[0])
            intensity_columns = df.filter(regex="Reporter intensity corrected").columns.to_list()
            columns.remove("Reporter intensity corrected")
            columns = columns + intensity_columns
        df = get_protein_groups_data(fns, columns=columns, protein_names=protein_names)
        return _dataframe_json_payload(df)
    except Exception as e:
        logging.error(f"Protein groups request error: {e}")
        return {}


def get_protein_names(
    project,
    pipeline,
    remove_contaminants=True,
    remove_reversed_sequences=True,
    data_range=None,
    raw_files=None,
    user=None,
):
    if user is None:
        return {}
    try:
        fns = get_protein_quant_fn(
            project,
            pipeline,
            data_range=data_range,
            user=user,
            raw_files=raw_files,
        )
        if len(fns) == 0:
            return {}
        cols = ["Majority protein IDs", "Fasta headers", "Score", "Intensity"]
        ddf = dd.read_parquet(fns, engine="pyarrow")[cols]
        if remove_contaminants:
            ddf = remove(ddf, "contaminants")
        if remove_reversed_sequences:
            ddf = remove(ddf, "reversed_sequences")
        dff = (
            ddf.groupby(["Majority protein IDs", "Fasta headers"])
            .mean()
            .sort_values("Score")
            .reset_index()
            .rename(columns={"Majority protein IDs": "protein_names"})
        )
        res = dff.compute()
        response = {}
        for col in res.columns:
            response[col] = res[col].to_list()
        return response
    except Exception as e:
        logging.error(f"Protein names request error: {e}")
        return {}


def get_qc_data(project, pipeline, columns, data_range=None, user=None):
    if user is None:
        return {}
    try:
        df = orm_get_qc_data(project, pipeline, data_range, user=user)
        if df is None:
            df = pd.DataFrame()
        df = df.replace({np.nan: None})
        response = {}
        cols = df.columns if (not columns) else columns
        n_rows = len(df.index)
        for col in cols:
            if col in df.columns:
                response[col] = df[col].tolist()
            else:
                response[col] = [None] * n_rows
        return response
    except Exception as e:
        logging.error(f"QC data request error: {e}")
        return {}


def set_rawfile_action(project, pipeline, raw_files, action, user=None):
    if user is None:
        return {"status": "Missing user context."}
    try:
        pipeline_obj = _pipelines_for_user(user).filter(
            project__slug=project,
            slug=pipeline,
        ).first()
        if pipeline_obj is None:
            return {"status": "Missing permissions"}
        results = _results_for_pipeline_mutation(user, pipeline_obj)
        raw_file_set = {str(Path(i).name) for i in list(raw_files or [])}
        for result in results:
            if result.raw_file.name not in raw_file_set:
                continue
            if action == "flag":
                result.raw_file.flagged = True
                result.raw_file.save(update_fields=["flagged"])
            elif action == "unflag":
                result.raw_file.flagged = False
                result.raw_file.save(update_fields=["flagged"])
            elif action == "accept":
                result.raw_file.use_downstream = True
                result.raw_file.save(update_fields=["use_downstream"])
            elif action == "reject":
                result.raw_file.use_downstream = False
                result.raw_file.save(update_fields=["use_downstream"])
        return {"status": "success"}
    except Exception as e:
        logging.error(f"Raw file action error: {e}")
        return {"status": str(e)}


def gen_figure_config(
    filename="plot", format="svg", height=None, width=None, scale=None, editable=True
):
    config = {
        "toImageButtonOptions": {"format": format, "filename": filename},
        "height": height,
        "width": width,
        "scale": scale,
        "editable": editable,
    }
    return config


def gen_tabulator_columns(
    col_names=None,
    add_ms_file_col=False,
    add_color_col=False,
    add_peakopt_col=False,
    add_ms_file_active_col=False,
    col_width="12px",
    editor="input",
):

    if col_names is None:
        col_names = []
    else:
        col_names = list(col_names)

    columns = [
        {
            "formatter": "rowSelection",
            "titleFormatter": "rowSelection",
            "titleFormatterParams": {"rowRange": "active"},
            "hozAlign": "center",
            "headerSort": False,
            "width": "1px",
            "frozen": True,
        }
    ]

    for col in col_names:
        content = {
            "title": col,
            "field": col,
            "headerFilter": True,
            "width": col_width,
            "editor": editor,
        }

        columns.append(content)

    return columns


def log2p1(x):
    try:
        return np.log2(x + 1)
    except (TypeError, ValueError):
        return x


class ShapAnalysis:
    def __init__(self, model, df):
        # explainer = shap.TreeExplainer(model)
        explainer = shap.Explainer(model)

        shap_values = explainer(df)
        self._shap_values = shap_values
        self._instance_names = df.index.to_list()
        self._feature_names = df.columns.to_list()
        self.df_shap = pd.DataFrame(
            shap_values.values, columns=df.columns, index=df.index
        )

    def waterfall(self, i, **kwargs):
        shap_values = self._shap_values
        self._base_values = shap_values[i][0].base_values
        self._values = shap_values[i].values
        shap_object = shap.Explanation(
            base_values=self._base_values,
            values=self._values,
            feature_names=self._feature_names,
            # instance_names = self._instance_names,
            data=shap_values[i].data,
        )
        shap.plots.waterfall(shap_object, **kwargs)

    def summary(self, **kwargs):
        shap.summary_plot(self._shap_values, **kwargs)

    def bar(self, **kwargs):
        shap.plots.bar(self._shap_values, **kwargs)
        for ax in pl.gcf().axes:
            for ch in ax.get_children():
                try:
                    ch.set_color("0.3")
                except AttributeError:
                    break


def px_heatmap(df, colorscale="jet_r", layout_kws=None):
    fig = go.Figure(
        data=go.Heatmap(z=df.values, y=df.index, x=df.columns, colorscale=colorscale)
    )
    fig.update_layout(**layout_kws)
    fig.update_yaxes(automargin=True)
    fig.update_xaxes(automargin=True)
    return fig


def plotly_heatmap(
    df,
    normed_by_cols=False,
    transposed=False,
    clustered=False,
    add_dendrogram=False,
    name="",
    x_tick_colors=None,
    height=None,
    width=None,
    correlation=False,
    call_show=False,
    verbose=False,
):

    max_is_not_zero = df.max(axis=1) != 0
    non_zero_labels = max_is_not_zero[max_is_not_zero].index
    df = df.loc[non_zero_labels]

    plot_type = "Heatmap"
    colorscale = "Bluered"
    plot_attributes = []

    if normed_by_cols:
        df = df.divide(df.max()).fillna(0)
        plot_attributes.append("normalized")

    if transposed:
        df = df.T

    if correlation:
        plot_type = "Correlation"
        df = df.corr()
        colorscale = [
            [0.0, "rgb(165,0,38)"],
            [0.1111111111111111, "rgb(215,48,39)"],
            [0.2222222222222222, "rgb(244,109,67)"],
            [0.3333333333333333, "rgb(253,174,97)"],
            [0.4444444444444444, "rgb(254,224,144)"],
            [0.5555555555555556, "rgb(224,243,248)"],
            [0.6666666666666666, "rgb(171,217,233)"],
            [0.7777777777777778, "rgb(116,173,209)"],
            [0.8888888888888888, "rgb(69,117,180)"],
            [1.0, "rgb(49,54,149)"],
        ]
    else:
        plot_type = "Heatmap"

    if clustered:
        dendro_side = ff.create_dendrogram(
            df,
            orientation="right",
            labels=df.index.to_list(),
            color_threshold=0,
            colorscale=["black"] * 8,
        )
        dendro_leaves = dendro_side["layout"]["yaxis"]["ticktext"]
        df = df.loc[dendro_leaves, :]
        if correlation:
            df = df[df.index]

    x = df.columns
    if clustered:
        y = dendro_leaves
    else:
        y = df.index.to_list()
    z = df.values

    heatmap = go.Heatmap(x=x, y=y, z=z, colorscale=colorscale)

    if name == "":
        title = ""
    else:
        title = f'{plot_type} of {",".join(plot_attributes)} {name}'

    # Figure without side-dendrogram
    if (not add_dendrogram) or (not clustered):
        fig = go.Figure(heatmap)
        fig.update_layout(
            {"title_x": 0.5},
            title={"text": title},
            yaxis={"title": "", "tickmode": "array", "automargin": True},
        )

        fig.update_layout({"height": height, "width": width, "hovermode": "closest"})

    else:  # Figure with side-dendrogram
        fig = go.Figure()

        for i in range(len(dendro_side["data"])):
            dendro_side["data"][i]["xaxis"] = "x2"

        for data in dendro_side["data"]:
            fig.add_trace(data)

        y_labels = heatmap["y"]
        heatmap["y"] = dendro_side["layout"]["yaxis"]["tickvals"]

        fig.add_trace(heatmap)

        fig.update_layout(
            {
                "height": height,
                "width": width,
                "showlegend": False,
                "hovermode": "closest",
                "paper_bgcolor": "white",
                "plot_bgcolor": "white",
                "title_x": 0.5,
            },
            title={"text": title},
            # X-axis of main figure
            xaxis={
                "domain": [0.11, 1],
                "mirror": False,
                "showgrid": False,
                "showline": False,
                "zeroline": False,
                "showticklabels": True,
                "ticks": "",
            },
            # X-axis of side-dendrogram
            xaxis2={
                "domain": [0, 0.1],
                "mirror": False,
                "showgrid": True,
                "showline": False,
                "zeroline": False,
                "showticklabels": False,
                "ticks": "",
            },
            # Y-axis of main figure
            yaxis={
                "domain": [0, 1],
                "mirror": False,
                "showgrid": False,
                "showline": False,
                "zeroline": False,
                "showticklabels": False,
            },
        )

        fig["layout"]["yaxis"]["ticktext"] = np.asarray(y_labels)
        fig["layout"]["yaxis"]["tickvals"] = np.asarray(
            dendro_side["layout"]["yaxis"]["tickvals"]
        )

    fig.update_layout(
        # margin=dict( l=50, r=10, b=200, t=50, pad=0 ),
        autosize=True,
        hovermode="closest",
    )

    fig.update_yaxes(automargin=True)
    fig.update_xaxes(automargin=True)

    if call_show:
        fig.show(config={"displaylogo": False})
    else:
        return fig


def _normalize_max_features(max_features, n_features):
    """
    Normalize max_features for anomaly models.
    - int-like values are capped to [1, n_features]
    - float values in (0, 1] are kept as-is (fraction semantics)
    - float values > 1 are treated as absolute counts and capped
    - numeric strings are parsed to int/float using the same rules
    - invalid values return None so model defaults are used
    """
    if max_features is None:
        return None

    if n_features <= 0:
        return None

    if isinstance(max_features, (bool, np.bool_)):
        return None

    value = max_features
    if isinstance(value, str):
        stripped = value.strip()
        if not stripped:
            return None
        try:
            value = float(stripped) if "." in stripped else int(stripped)
        except ValueError:
            return None

    if isinstance(value, (int, np.integer)):
        return max(1, min(int(value), n_features))

    if isinstance(value, (float, np.floating)) or isinstance(value, numbers.Real):
        value = float(value)
        if value <= 0:
            return 1
        if value <= 1:
            return value
        return max(1, min(int(value), n_features))

    return None


def detect_anomalies(
    qc_data,
    algorithm=None,
    columns=None,
    max_features=None,
    fraction=None,
    percentage=None,
    **model_kws,
):

    if columns is None:
        columns = []

    # only use columns that exist and are numeric
    available_cols = [c for c in columns if c in qc_data.columns]
    selected_cols = [c for c in available_cols if is_numeric_dtype(qc_data[c])]
    if not selected_cols:
        fallback_cols = [
            c
            for c in qc_data.select_dtypes(include=[np.number]).columns
            if c not in {"Index"}
        ]
        selected_cols = [c for c in fallback_cols if is_numeric_dtype(qc_data[c])]
    if not selected_cols:
        raise ValueError("No numeric columns available for anomaly detection")
    selected_cols.reverse()
    normalized_max_features = _normalize_max_features(max_features, len(selected_cols))
    if normalized_max_features is not None:
        model_kws["max_features"] = normalized_max_features
    if "contamination" not in model_kws:
        contamination = fraction if fraction is not None else percentage
        if contamination is not None:
            model_kws["contamination"] = float(contamination)
    log_cols = [
        "Ms1MedianSummedIntensity",
        "Ms2MedianSummedIntensity",
        "MedianPrecursorIntensity",
    ]
    for c in log_cols:
        if c in qc_data.columns:
            qc_data[c] = qc_data[c].apply(log2p1)

    df_train = qc_data[qc_data["Use Downstream"].fillna(False)][selected_cols].fillna(0)
    df_all = qc_data[selected_cols].fillna(0)

    # Keep anomaly setup from consuming all CPUs by default.
    env_n_jobs = os.getenv("PQC_ANOMALY_N_JOBS")
    if env_n_jobs is not None:
        try:
            n_jobs = max(1, int(env_n_jobs))
        except ValueError:
            n_jobs = 2
            logging.warning(
                "Invalid PQC_ANOMALY_N_JOBS=%r. Falling back to %s.", env_n_jobs, n_jobs
            )
    else:
        cpu_count = os.cpu_count() or 2
        n_jobs = min(4, max(1, cpu_count // 2))

    _ = setup(
        df_train,
        verbose=False,
        html=False,
        n_jobs=n_jobs,
        numeric_features=selected_cols,
    )

    logging.info(f"Create anomaly model: {algorithm}")
    model = create_model(algorithm, **model_kws)
    pipeline = get_config("pipeline")
    data = pipeline.transform(df_all)
    # pycaret changes column names
    # change it to original names
    data.columns = selected_cols
    if algorithm == "iforest":
        sa = ShapAnalysis(model, data)
        shapley_values = sa.df_shap.reindex(selected_cols, axis=1)
    else:
        shapley_values = None
    prediction = predict_model(model, df_all)[["Anomaly", "Anomaly_Score"]]
    return prediction, shapley_values


def get_marker_color(use_downstream, flagged, selected):
    colors = {
        ("unknown", False, False): "grey",
        ("unknown", True, False): "grey",
        ("unknown", False, True): "black",
        ("unknown", True, True): "black",
        (True, False, False): "blue",
        (False, False, False): "deepskyblue",
        (True, True, False): "red",
        (False, True, False): "pink",
        (True, False, True): "magenta",
        (False, False, True): "magenta",
        (True, True, True): "cyan",
        (False, True, True): "cyan",
    }
    key = (
        use_downstream if isinstance(use_downstream, bool) else "unknown",
        flagged,
        selected,
    )
    color = colors[key]
    return color


def get_marker_line_color(use_downstream, flagged, selected):
    colors = {
        ("unknown", False, False): "lightblue",
        ("unknown", True, False): "red",
        ("unknown", False, True): "black",
        ("unknown", True, True): "black",
        (True, False, False): "deepskyblue",
        (False, False, False): "lightblue",
        (True, True, False): "red",
        (False, True, False): "pink",
        (True, False, True): "magenta",
        (False, False, True): "magenta",
        (True, True, True): "cyan",
        (False, True, True): "cyan",
    }
    color = colors[
        (
            use_downstream if isinstance(use_downstream, bool) else "unknown",
            flagged,
            selected,
        )
    ]
    return color
