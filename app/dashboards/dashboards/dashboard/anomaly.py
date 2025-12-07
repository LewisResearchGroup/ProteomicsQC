import os
import logging
import pandas as pd

from dash import html, dcc, no_update
import dash_bootstrap_components as dbc
from dash.dependencies import Input, Output, State
from dash.exceptions import PreventUpdate

from lrg_omics.proteomics import ProteomicsQC

try:
    from . import tools as T
    from . import config as C
except Exception as e:
    logging.warning(e)
    import tools as T
    import config as C


checklist_options = [
    {"label": "Hide rejected samples", "value": "hide_rejected"},
]

algorithm_options = [
    {"label": "Isolation Forest", "value": "iforest"},
    {"label": "Angle-base Outlier Detection", "value": "abod"},
    {"label": "Clustering-Based Local Outlier", "value": "cluster"},
    {"label": "Connectivity-Based Outlier Factor", "value": "cof"},
    {"label": "Histogram-based Outlier Detection", "value": "histogram"},
    {"label": "k-Nearest Neighbors Detector", "value": "knn"},
    {"label": "Local Outlier Factor", "value": "lof"},
    {"label": "One-class SVM detector", "value": "svm"},
    {"label": "Principal Component Analysis", "value": "pca"},
    {"label": "Minimum Covariance Determinant", "value": "mcd"},
    {"label": "Subspace Outlier Detection", "value": "sod"},
    {"label": "Stochastic Outlier Selection", "value": "sos"},
]

layout = html.Div(
    [
        html.H1("Anomaly detection"),

        html.Label("Select Algorithm"),
        dcc.Dropdown(
            id="anomaly-algorithm",
            options=algorithm_options,
            value="iforest"
        ),

        html.Label("Estimated outlier fraction"),
        dcc.Slider(
            id="anomaly-fraction",
            value=5,
            min=1,
            max=100,
            step=1,
            marks={i: {"label": f"{i}%"} for i in range(10, 110, 10)},
        ),

        dcc.Checklist(
            id="anomaly-checklist",
            options=checklist_options,
            value=["hide_rejected"],
            style=dict(padding="15px"),
        ),

        dbc.Button(
            "Predict Anomalies",
            id="anomaly-btn",
            className="btn",
            color="primary"
        ),

        # Spinner wrapper (entire graph)
        dcc.Loading(
            id="anomaly-loading",
            type="circle",
            children=[
                html.Div(
                    dcc.Graph(
                        id="anomaly-figure",
                        figure={},
                        style={
                            "display": "none",  # start hidden/empty
                            "width": "100%",
                            "maxWidth": "1200px",
                            "margin": "0 auto",
                        },
                    ),
                    style={
                        "display": "flex",
                        "justifyContent": "center",
                        "width": "100%",
                        "margin": "0 auto",
                    },
                )
            ]
        ),
    ]
)


def callbacks(app):

    @app.callback(
        Output("shapley-values", "children"),
        Input("anomaly-btn", "n_clicks"),
        State("anomaly-algorithm", "value"),
        State("project", "value"),
        State("pipeline", "value"),
        State("qc-table-columns", "value"),
        State("anomaly-fraction", "value"),
    )
    def run_anomaly_detection(
        n_clicks, algorithm, project, pipeline, columns, fraction, **kwargs
    ):
        if n_clicks is None:
            raise PreventUpdate

        fraction = fraction / 100.0

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

        if algorithm == "iforest":
            params = dict(n_estimators=1000, max_features=10)
        else:
            params = {}

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

        return df_shap.to_json() if df_shap is not None else None


    @app.callback(
        Output("anomaly-figure", "figure"),
        Output("anomaly-figure", "config"),
        Output("anomaly-figure", "style"),
        Input("shapley-values", "children"),
        Input("qc-table", "data"),
        Input("anomaly-checklist", "value"),
        Input("qc-table", "derived_virtual_indices"),
        Input("tabs", "value"),
        State("anomaly-btn", "n_clicks")
    )
    def plot_shapley(shapley_values, qc_data, options, ndxs, tab, n_clicks):

        # 1. Nothing clicked yet → keep hidden/empty
        if n_clicks is None:
            return {}, no_update, {"display": "none"}

        # 2. Button clicked but SHAP not computed yet → clear figure and hide
        if tab != "anomaly" or shapley_values is None:
            return {}, no_update, {"display": "none"}

        # 3. SHAP available → build the heatmap
        df_shap = pd.read_json(shapley_values)
        qc_data = pd.DataFrame(qc_data)

        if ndxs is None:
            ndxs = list(qc_data.index)
        else:
            qc_data = qc_data.iloc[ndxs]

        if "hide_rejected" in options:
            qc_data = qc_data[qc_data["Use Downstream"] != False]

        fns = qc_data["RawFile"]
        df_shap = df_shap.loc[fns]

        # Build heatmap
        fig = T.px_heatmap(
            df_shap.T,
            layout_kws=dict(
                title="Anomaly feature score (Shapley values)",
                height=1200,
            ),
        )

        # Clean axes
        fig.update_xaxes(showgrid=False, zeroline=False)
        fig.update_yaxes(showgrid=False, zeroline=False,
                         side="left", ticklabelposition="outside")

        # Size & spacing
        fig.update_layout(
            width=1200,
            margin=dict(l=40, r=40, t=80, b=20),
            xaxis=dict(domain=[0.05, 0.75]),
            coloraxis_colorbar=dict(
                x=0.80,
                thickness=20,
                len=0.9,
            ),
        )

        # X label rotation
        fig.update_xaxes(
            tickangle=90,
            ticklabelposition="outside",
            automargin=True
        )

        # SHAP diverging scale
        heatmap = [t for t in fig.data if t.type == "heatmap"][0]
        zmin = float(df_shap.values.min())
        zmax = float(df_shap.values.max())
        rng  = max(abs(zmin), abs(zmax))

        heatmap.zmin = -rng
        heatmap.zmax =  rng
        heatmap.zmid = 0
        heatmap.colorscale = "RdBu"

        heatmap.colorbar.title = "SHAP\n(- normal | + anomalous)"
        heatmap.colorbar.tickvals = [-rng, 0, rng]
        heatmap.colorbar.ticktext = ["More normal", "0", "More anomalous"]

        fig.update_layout(font=C.figure_font)

        config = T.gen_figure_config(
            filename="Anomaly-Detection-Shapley-values",
            editable=False
        )

        return fig, config, {"display": "block", "width": "100%", "maxWidth": "1200px", "margin": "0 auto"}
