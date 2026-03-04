import os
import logging
import json
import hashlib
import pandas as pd

from dash import html, dcc
from dash.dependencies import Input, Output, State
from dash.exceptions import PreventUpdate

from omics.proteomics import ProteomicsQC

try:
    from . import tools as T
    from . import config as C
except Exception as e:
    logging.warning(e)
    import tools as T
    import config as C


layout = html.Div(
    [
        html.Div(
            className="pqc-anomaly-controls",
            children=[
                html.Div(
                    className="pqc-anomaly-controls-row",
                    children=[
                        html.Div(
                            className="pqc-anomaly-head",
                            children=[
                                html.Div("Anomaly Settings", className="pqc-panel-kicker"),
                                html.Div(
                                    "Tune sensitivity and display options for outlier screening.",
                                    className="pqc-anomaly-subtitle",
                                ),
                            ],
                        ),
                        html.Div(
                            className="pqc-anomaly-slider-panel pqc-anomaly-slider-panel-inline",
                            children=[
                                html.Div(
                                    className="pqc-anomaly-label-row",
                                    children=[
                                        html.Div("Outlier fraction", className="pqc-field-label"),
                                    ],
                                ),
                                html.Div(
                                    className="pqc-anomaly-slider-wrap",
                                    children=[
                                        dcc.Slider(
                                            id="anomaly-fraction",
                                            value=5,
                                            min=1,
                                            max=100,
                                            step=1,
                                            marks={i: {"label": f"{i}%"} for i in [1] + list(range(5, 105, 5))},
                                            tooltip={"placement": "bottom", "always_visible": False},
                                        )
                                    ],
                                ),
                            ],
                        ),
                        html.Div(
                            className="pqc-anomaly-extra-controls",
                            children=[
                                html.Div(
                                    className="pqc-anomaly-control-block",
                                    children=[
                                        html.Div("Row order", className="pqc-field-label"),
                                        dcc.Dropdown(
                                            id="anomaly-row-order",
                                            className="pqc-anomaly-dropdown",
                                            clearable=False,
                                            searchable=False,
                                            options=[
                                                {"label": "Input order", "value": "input"},
                                                {"label": "Anomalous first", "value": "anomalous_first"},
                                            ],
                                            value="input",
                                        ),
                                    ],
                                ),
                                html.Div(
                                    className="pqc-anomaly-control-block",
                                    children=[
                                        html.Div("Metrics shown", className="pqc-field-label"),
                                        dcc.Dropdown(
                                            id="anomaly-metric-count",
                                            className="pqc-anomaly-dropdown",
                                            clearable=False,
                                            searchable=False,
                                            options=[
                                                {"label": "10", "value": 10},
                                                {"label": "15", "value": 15},
                                                {"label": "20", "value": 20},
                                                {"label": "25", "value": 25},
                                                {"label": "30", "value": 30},
                                                {"label": "All", "value": "all"},
                                            ],
                                            value=20,
                                        ),
                                    ],
                                ),
                            ],
                        ),
                    ],
                ),
                html.Div("5%", id="anomaly-fraction-value", className="pqc-hidden-trigger"),
            ],
        ),
        html.Div(
            className="pqc-anomaly-plot-area",
            children=[
                html.Div(
                    "No anomaly plot data available for this scope.",
                    id="anomaly-empty-state",
                    className="pqc-empty-state",
                    style={"display": "none"},
                ),
                dcc.Loading(
                    id="anomaly-loading",
                    type="circle",
                    style={"height": "100%"},
                    children=html.Div(
                        className="pqc-anomaly-loading-scope",
                        children=[
                            html.Div(id="anomaly-progress-probe", className="pqc-hidden-trigger"),
                            dcc.Graph(
                                id="anomaly-figure",
                                figure={},
                                style={
                                    "display": "block",
                                    "width": "100%",
                                    "height": "100%",
                                },
                            ),
                        ],
                    ),
                )
            ],
        ),
    ]
)


def callbacks(app):
    min_samples_for_anomaly = 3

    def _short_label(value, max_len=26):
        text = str(value)
        if len(text) <= max_len:
            return text
        return f"{text[:max_len-1]}…"

    def _short_label_keep_ends(value, max_len=30, tail_len=8):
        text = str(value)
        if len(text) <= max_len:
            return text
        head_len = max(8, max_len - tail_len - 1)
        return f"{text[:head_len]}…{text[-tail_len:]}"

    def _pretty_metric_name(name):
        text = str(name)
        text = text.replace("_", " ")
        text = text.replace(" [ppm] (ave)", " delta m/z (ppm)")
        text = text.replace("[%]", "(%)")
        text = text.replace("calibrated retention time qc1", "calibrated retention time qc1")
        text = text.replace("Uncalibrated - Calibrated m/z", "delta m/z")
        return text

    @app.callback(
        Output("anomaly-fraction-value", "children"),
        Input("anomaly-fraction", "value"),
    )
    def render_fraction_value(value):
        return f"{int(value or 0)}%"

    @app.callback(
        Output("shapley-values", "children"),
        Output("anomaly-progress-probe", "children"),
        Output("anomaly-cache-key", "children"),
        Input("tabs", "value"),
        Input("project", "value"),
        Input("pipeline", "value"),
        Input("anomaly-fraction", "value"),
        Input("qc-scope-data", "data"),
        State("qc-table-columns", "value"),
        State("anomaly-cache-key", "children"),
        State("shapley-values", "children"),
    )
    def run_anomaly_detection(
        tab,
        project,
        pipeline,
        fraction_in,
        scope_data,
        columns,
        cached_key,
        cached_payload,
        **kwargs,
    ):
        if tab != "anomaly":
            raise PreventUpdate
        if project is None or pipeline is None:
            raise PreventUpdate
        if not scope_data:
            raise PreventUpdate

        fraction = (fraction_in or 5) / 100.0
        algorithm = "iforest"
        columns = columns or []
        # Cache against the current scope payload itself, not just the selected
        # project/pipeline parameters, so a changed sample set forces recompute.
        scope_sig = hashlib.md5(json.dumps(scope_data, sort_keys=True, default=str).encode("utf-8")).hexdigest()
        cache_key = json.dumps(
            {
                "project": project,
                "pipeline": pipeline,
                "fraction": int(fraction_in or 5),
                "columns": sorted(columns),
                "scope_sig": scope_sig,
                "algorithm": algorithm,
            },
            sort_keys=True,
        )
        if cached_key == cache_key and cached_payload:
            raise PreventUpdate

        user = kwargs.get("user")
        uid = getattr(user, "uuid", None)
        if uid is None:
            raise PreventUpdate

        # Use already loaded QC scope data from dashboard state to avoid
        # secondary API calls that may fail auth-context checks.
        qc_data = pd.DataFrame(scope_data or [])
        if qc_data.empty or "RawFile" not in qc_data.columns:
            return None, f"empty-{project}-{pipeline}-{fraction_in}", cache_key
        sample_count = qc_data["RawFile"].dropna().astype(str).nunique()
        if sample_count < min_samples_for_anomaly:
            return None, f"insufficient-{project}-{pipeline}-{sample_count}", cache_key
        qc_data = qc_data.set_index("RawFile")

        # Replace column fully None → True
        if "Use Downstream" not in qc_data.columns:
            qc_data["Use Downstream"] = True
        if qc_data["Use Downstream"].isna().all():
            qc_data["Use Downstream"] = True
        if "Flagged" not in qc_data.columns:
            qc_data["Flagged"] = False

        params = dict(n_estimators=1000, max_features=10)

        try:
            predictions, df_shap = T.detect_anomalies(
                qc_data, algorithm=algorithm, columns=columns, fraction=fraction, **params
            )
        except Exception as exc:
            logging.warning(f"Anomaly detection skipped for {project}/{pipeline}: {exc}")
            return None, f"empty-{project}-{pipeline}-{fraction_in}", cache_key

        # Update flags in backend
        currently_unflagged = list(qc_data[~qc_data.Flagged].reset_index().RawFile)
        currently_flagged   = list(qc_data[qc_data.Flagged].reset_index().RawFile)
        files_to_flag   = [i for i in predictions[predictions.Anomaly == 1].index if i in currently_unflagged]
        files_to_unflag = [i for i in predictions[predictions.Anomaly == 0].index if i in currently_flagged]

        T.set_rawfile_action(project, pipeline, files_to_flag, "flag", user=user)
        T.set_rawfile_action(project, pipeline, files_to_unflag, "unflag", user=user)

        payload = (
            df_shap.to_json(orient="split")
            if df_shap is not None
            else None
        )
        return payload, f"updated-{project}-{pipeline}-{fraction_in}", cache_key


    @app.callback(
        Output("anomaly-figure", "figure"),
        Output("anomaly-figure", "config"),
        Output("anomaly-figure", "style"),
        Output("anomaly-empty-state", "children"),
        Output("anomaly-empty-state", "style"),
        Input("shapley-values", "children"),
        Input("qc-scope-data", "data"),
        Input("tabs", "value"),
        Input("anomaly-row-order", "value"),
        Input("anomaly-metric-count", "value"),
    )
    def plot_shapley(shapley_values, qc_data, tab, row_order, metric_count):
        config = T.gen_figure_config(
            filename="Anomaly-Detection-Shapley-values",
            editable=False,
        )
        config["displayModeBar"] = False
        hidden_graph_style = {
            "display": "none",
            "width": "100%",
            "height": "100%",
            "margin": "0",
        }
        visible_graph_style = {
            "display": "block",
            "width": "100%",
            "height": "100%",
            "margin": "0",
        }
        default_empty_message = "No anomaly plot data available for this scope."

        if tab != "anomaly":
            return {}, config, hidden_graph_style, default_empty_message, {"display": "none"}

        qc_data = pd.DataFrame(qc_data or [])
        if qc_data.empty:
            return {}, config, hidden_graph_style, default_empty_message, {"display": "flex"}
        if "RawFile" not in qc_data.columns:
            return {}, config, hidden_graph_style, default_empty_message, {"display": "flex"}
        sample_count = qc_data["RawFile"].dropna().astype(str).nunique()
        if sample_count < min_samples_for_anomaly:
            return (
                {},
                config,
                hidden_graph_style,
                f"Anomaly detection requires at least {min_samples_for_anomaly} samples. Current selection has {sample_count}.",
                {"display": "flex"},
            )
        if shapley_values is None:
            return {}, config, hidden_graph_style, default_empty_message, {"display": "flex"}

        try:
            df_shap = pd.read_json(shapley_values, orient="split")
        except ValueError:
            # Backward compatibility with cached payloads serialized
            # using pandas default orient.
            df_shap = pd.read_json(shapley_values)

        # samples on rows, QC metrics on columns
        fns = qc_data["RawFile"].astype(str)
        df_shap = df_shap.reindex(fns).fillna(0)

        if row_order == "anomalous_first":
            sample_rank = df_shap.abs().mean(axis=1).sort_values(ascending=False).index
            df_shap = df_shap.reindex(sample_rank)

        if metric_count != "all":
            max_metrics = int(metric_count or 20)
            metric_rank = df_shap.abs().mean(axis=0).sort_values(ascending=False).index
            df_shap = df_shap.loc[:, metric_rank[:max_metrics]]

        df_plot = df_shap.copy()
        df_plot.index = [_short_label_keep_ends(v, max_len=30, tail_len=8) for v in df_plot.index]
        df_plot.columns = [_short_label(_pretty_metric_name(c), max_len=30) for c in df_plot.columns]

        # Keep a stable panel size across cohorts to avoid page-height jumps.
        fixed_height = 460

        fig = T.px_heatmap(
            df_plot,
            layout_kws=dict(
                height=fixed_height,
            ),
        )

        # Clean axes
        fig.update_xaxes(showgrid=False, zeroline=False)
        fig.update_yaxes(showgrid=False, zeroline=False,
                         side="left", ticklabelposition="outside")

        # Size & spacing
        fig.update_layout(
            width=None,
            margin=dict(l=14, r=20, t=6, b=24),
            coloraxis_colorbar=dict(
                x=1.02,
                y=0.48,
                yanchor="middle",
                thickness=14,
                len=0.76,
            ),
            plot_bgcolor="#f7fbfe",
            paper_bgcolor="#f7fbfe",
        )

        # X label rotation
        fig.update_xaxes(
            tickangle=0,
            ticklabelposition="outside",
            automargin=True,
            title_text="QC metrics",
            title_standoff=12,
            showticklabels=False,
            ticks="",
        )
        fig.update_yaxes(title_text="Samples", title_standoff=36)

        # SHAP diverging scale
        heatmap = [t for t in fig.data if t.type == "heatmap"][0]
        zmin = float(df_plot.values.min())
        zmax = float(df_plot.values.max())
        rng  = max(abs(zmin), abs(zmax))

        heatmap.zmin = -rng
        heatmap.zmax =  rng
        heatmap.zmid = 0
        heatmap.colorscale = "RdBu"

        heatmap.colorbar.title = dict(
            text="SHAP (- normal | + anomalous)",
            side="right",
        )
        heatmap.colorbar.tickvals = [-rng, 0, rng]
        heatmap.colorbar.ticktext = ["More normal", "0", "More anomalous"]
        heatmap.colorbar.tickfont = dict(size=9)
        heatmap.colorbar.title.font = dict(size=11)

        base_font = dict(C.figure_font) if isinstance(C.figure_font, dict) else {}
        fig.update_layout(font={**base_font, "size": 11})
        fig.update_xaxes(title_font=dict(size=12))
        fig.update_yaxes(title_font=dict(size=12), tickfont=dict(size=9))

        return fig, config, visible_graph_style, default_empty_message, {"display": "none"}
