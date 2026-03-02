import logging
import pandas as pd
from dash import dcc, html

from dash.dependencies import Input, Output
from dash.exceptions import PreventUpdate

import plotly.graph_objects as go

try:
    from . import tools as T
    from . import config as C
except Exception as e:
    logging.warning(e)
    import tools as T
    import config as C

# Keep the graph responsive without forcing a tall container up front
GRAPH_STYLE = {"maxWidth": "100%"}

METRIC_LABELS = {
    "N_peptides": "Peptides Identified",
    "N_protein_groups": "Protein Groups Identified",
    "MS/MS Identified [%]": "MS/MS Identified (%)",
    "Oxidations [%]": "Oxidations (%)",
    "N_missed_cleavages_eq_1 [%]": "Missed Cleavages Eq1 (%)",
    "Uncalibrated - Calibrated m/z [ppm] (ave)": "Delta m/z (ppm, avg)",
    "calibrated_retention_time_qc1": "Calibrated RT QC1",
    "calibrated_retention_time_qc2": "Calibrated RT QC2",
}

X_AXIS_LABELS = {
    "Index": "Sample Index",
    "RawFile": "Sample",
    "DateAcquired": "Acquisition Date",
}

x_options = [dict(label=X_AXIS_LABELS[x], value=x) for x in X_AXIS_LABELS]

metric_options = [
    {"label": METRIC_LABELS[k], "value": k}
    for k in [
        "N_peptides",
        "N_protein_groups",
        "MS/MS Identified [%]",
        "Oxidations [%]",
        "N_missed_cleavages_eq_1 [%]",
        "Uncalibrated - Calibrated m/z [ppm] (ave)",
        "calibrated_retention_time_qc1",
        "calibrated_retention_time_qc2",
    ]
]

BUTTON_STYLE = {
    "padding": "8px 14px",
    "borderRadius": "8px",
    "fontWeight": 600,
    "fontSize": "14px",
}

layout = html.Div(
    [
        html.Div(
            className="pqc-qc-plot-toolbar",
            children=[
                html.Div(
                    className="pqc-qc-metric-wrap",
                    children=[
                        html.Div("QC Metric", className="pqc-field-label"),
                        dcc.Dropdown(
                            id="qc-metric",
                            multi=False,
                            options=metric_options,
                            value="N_peptides",
                            className="pqc-metric-dropdown",
                            clearable=False,
                        ),
                    ],
                ),
                html.Div(
                    className="pqc-qc-xaxis-wrap",
                    children=[
                        html.Div("X-Axis", className="pqc-field-label"),
                        dcc.Dropdown(
                            id="x",
                            options=x_options,
                            value="Index",
                            className="pqc-metric-dropdown",
                            clearable=False,
                        ),
                    ],
                ),
            ],
        ),
        html.Div(
            "No QC plot data available for this scope.",
            id="qc-empty-state",
            className="pqc-empty-state",
        ),
        dcc.Loading(
            [
                html.Div(
                    [
                        dcc.Graph(
                            id="qc-figure",
                            style={**GRAPH_STYLE, "display": "none"},
                        ),
                    ],
                    style={"textAlign": "center"},
                )
            ]
        ),
    ]
)


def callbacks(app):
    @app.callback(
        Output("qc-figure", "figure"),
        Output("qc-figure", "config"),
        Output("qc-figure", "style"),
        Output("qc-empty-state", "style"),
        Input("qc-scope-data", "data"),
        Input("qc-metric", "value"),
        Input("x", "value"),
    )
    def plot_qc_figure(data_in, metric_in, x_in):
        """Creates the QC trend plot figure."""
        data = data_in
        if data is None:
            raise PreventUpdate
        x = x_in or "RawFile"
        selected_metric = metric_in or "N_peptides"

        df = pd.DataFrame(data)
        if df.empty:
            return (
                go.Figure(),
                T.gen_figure_config(filename="QC-barplot", editable=False),
                {**GRAPH_STYLE, "display": "none"},
                {"display": "flex"},
            )

        assert pd.value_counts(df.columns).max() == 1, pd.value_counts(df.columns)

        if "DateAcquired" in df.columns:
            df["DateAcquired"] = pd.to_datetime(df["DateAcquired"], errors="coerce")
        else:
            df["DateAcquired"] = pd.NaT

        if x not in df.columns:
            x = "Index" if "Index" in df.columns else "RawFile"

        if selected_metric not in df.columns:
            return (
                go.Figure(),
                T.gen_figure_config(filename="QC-trends", editable=False),
                {**GRAPH_STYLE, "display": "none"},
                {"display": "flex"},
            )
        # Keep all samples visible by imputing missing points as zero.
        y_series = pd.to_numeric(df[selected_metric], errors="coerce").fillna(0)
        metric_label = METRIC_LABELS.get(selected_metric, selected_metric)
        x_axis_label = X_AXIS_LABELS.get(x, x)

        raw_labels = (
            df["RawFile"].astype(str)
            if "RawFile" in df.columns
            else df.index.astype(str)
        )
        acquired = df["DateAcquired"].astype(str).replace("NaT", "N/A")
        fig = go.Figure(
            data=[
                go.Scatter(
                    x=df[x],
                    y=y_series,
                    name=metric_label,
                    mode="lines+markers",
                    line=dict(width=3, color="#1f6f8b", shape="linear"),
                    marker=dict(size=8, color="#1f6f8b", line=dict(width=1, color="#ffffff")),
                    hovertext=raw_labels + "<br>" + acquired,
                    text=None if x == "RawFile" else raw_labels,
                    hovertemplate=(
                        "<b>%{hovertext}</b><br>"
                        + f"{metric_label}: "
                        + "%{y:.2f}<extra></extra>"
                    ),
                )
            ]
        )

        fig.update_layout(
            hovermode="closest",
            hoverlabel_namelength=-1,
            height=450,
            showlegend=False,
            margin=dict(l=32, r=20, b=60, t=24, pad=0),
            font=C.figure_font,
            plot_bgcolor="#fbfdff",
            paper_bgcolor="#f7fbfe",
            yaxis={"automargin": True},
            xaxis={"automargin": True},
        )

        fig.update_traces(marker_line_width=1, opacity=0.95)

        logging.info(f"QC plot built for metric {selected_metric} with height {fig.layout.height}")

        fig.update_xaxes(
            title_text=x_axis_label,
            showgrid=False,
            zeroline=False,
            showline=True,
            linecolor="#cddbe6",
        )
        fig.update_yaxes(
            title_text=metric_label,
            showgrid=False,
            zeroline=False,
            showline=True,
            linecolor="#cddbe6",
            rangemode="tozero",
        )

        config = T.gen_figure_config(filename="QC-trends", editable=False)

        graph_style = {**GRAPH_STYLE, "display": "block"}

        return fig, config, graph_style, {"display": "none"}
