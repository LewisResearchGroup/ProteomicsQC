import os
import logging
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
                html.Div("Outlier fraction", className="pqc-field-label"),
                html.Div(
                    className="pqc-anomaly-slider-wrap",
                    children=[
                        dcc.Slider(
                            id="anomaly-fraction",
                            value=5,
                            min=1,
                            max=100,
                            step=1,
                            marks={i: {"label": f"{i}%"} for i in range(10, 110, 10)},
                            tooltip={"placement": "bottom", "always_visible": False},
                        )
                    ],
                ),
            ],
        ),
        html.Div(
            className="pqc-anomaly-plot-area",
            children=[
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

    def _short_label(value, max_len=26):
        text = str(value)
        if len(text) <= max_len:
            return text
        return f"{text[:max_len-1]}…"

    def _pretty_metric_name(name):
        text = str(name)
        text = text.replace("_", " ")
        text = text.replace(" [ppm] (ave)", " delta m/z (ppm)")
        text = text.replace("[%]", "(%)")
        text = text.replace("calibrated retention time qc1", "calibrated retention time qc1")
        text = text.replace("Uncalibrated - Calibrated m/z", "delta m/z")
        return text

    @app.callback(
        Output("shapley-values", "children"),
        Output("anomaly-progress-probe", "children"),
        Input("tabs", "value"),
        Input("project", "value"),
        Input("pipeline", "value"),
        Input("anomaly-fraction", "value"),
        Input("qc-scope-data", "data"),
        State("qc-table-columns", "value"),
    )
    def run_anomaly_detection(tab, project, pipeline, fraction_in, scope_data, columns, **kwargs):
        if tab != "anomaly":
            raise PreventUpdate
        if project is None or pipeline is None:
            raise PreventUpdate
        if not scope_data:
            raise PreventUpdate

        fraction = (fraction_in or 5) / 100.0
        algorithm = "iforest"

        columns = columns or []

        uid = kwargs["user"].uuid

        pqc = ProteomicsQC(
            host=os.getenv("OMICS_URL", "http://localhost:8000"),
            project_slug=project,
            pipeline_slug=pipeline,
            uid=uid,
        )

        qc_data = pqc.get_qc_data(data_range=None).set_index("RawFile")

        # Replace column fully None → True
        if qc_data["Use Downstream"].isna().all():
            qc_data["Use Downstream"] = True

        params = dict(n_estimators=1000, max_features=10)

        predictions, df_shap = T.detect_anomalies(
            qc_data, algorithm=algorithm, columns=columns, fraction=fraction, **params
        )

        # Update flags in backend
        currently_unflagged = list(qc_data[~qc_data.Flagged].reset_index().RawFile)
        currently_flagged   = list(qc_data[qc_data.Flagged].reset_index().RawFile)
        files_to_flag   = [i for i in predictions[predictions.Anomaly == 1].index if i in currently_unflagged]
        files_to_unflag = [i for i in predictions[predictions.Anomaly == 0].index if i in currently_flagged]

        pqc.rawfile(files_to_flag, "flag")
        pqc.rawfile(files_to_unflag, "unflag")

        payload = df_shap.to_json() if df_shap is not None else None
        return payload, f"updated-{project}-{pipeline}-{fraction_in}"


    @app.callback(
        Output("anomaly-figure", "figure"),
        Output("anomaly-figure", "config"),
        Output("anomaly-figure", "style"),
        Input("shapley-values", "children"),
        Input("qc-scope-data", "data"),
        Input("tabs", "value"),
    )
    def plot_shapley(shapley_values, qc_data, tab):
        if tab != "anomaly" or shapley_values is None:
            return {}, T.gen_figure_config(filename="Anomaly-Detection-Shapley-values", editable=False), {"display": "block", "width": "100%", "height": "100%", "margin": "0"}

        df_shap = pd.read_json(shapley_values)
        qc_data = pd.DataFrame(qc_data or [])
        if qc_data.empty:
            return {}, T.gen_figure_config(filename="Anomaly-Detection-Shapley-values", editable=False), {"display": "block", "width": "100%", "height": "100%", "margin": "0"}
        if "RawFile" not in qc_data.columns:
            return {}, T.gen_figure_config(filename="Anomaly-Detection-Shapley-values", editable=False), {"display": "block", "width": "100%", "height": "100%", "margin": "0"}

        fns = qc_data["RawFile"]
        df_shap = df_shap.loc[fns]

        # samples on rows, QC metrics on columns
        fns = qc_data["RawFile"].astype(str)
        df_shap = df_shap.reindex(fns).fillna(0)
        df_plot = df_shap.copy()
        df_plot.index = [_short_label(v, max_len=34) for v in df_plot.index]
        df_plot.columns = [_short_label(_pretty_metric_name(c), max_len=30) for c in df_plot.columns]

        # Fit inside workspace canvas while remaining readable.
        n_samples = max(1, df_shap.shape[0])
        dynamic_height = max(380, min(620, 210 + (n_samples * 42)))

        fig = T.px_heatmap(
            df_plot,
            layout_kws=dict(
                height=dynamic_height,
            ),
        )

        # Clean axes
        fig.update_xaxes(showgrid=False, zeroline=False)
        fig.update_yaxes(showgrid=False, zeroline=False,
                         side="left", ticklabelposition="outside")

        # Size & spacing
        fig.update_layout(
            width=None,
            margin=dict(l=24, r=20, t=12, b=26),
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

        fig.update_layout(font=C.figure_font)

        config = T.gen_figure_config(
            filename="Anomaly-Detection-Shapley-values",
            editable=False
        )
        config["displayModeBar"] = False

        return fig, config, {"display": "block", "width": "100%", "height": "100%", "margin": "0"}
