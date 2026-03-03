import logging
import pandas as pd
from dash import dcc, html

from dash.dependencies import Input, Output
from dash.exceptions import PreventUpdate

import plotly.graph_objects as go
import plotly.express as px

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

PLOT_TYPE_OPTIONS = [
    {"label": "Line", "value": "line"},
    {"label": "Bar", "value": "bar"},
]

# Color palette for multiple metrics
METRIC_COLORS = px.colors.qualitative.Set2

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
                        html.Div("QC Metrics", className="pqc-field-label"),
                        dcc.Dropdown(
                            id="qc-metric",
                            multi=True,
                            options=metric_options,
                            value=["N_peptides"],
                            className="pqc-metric-dropdown",
                            clearable=False,
                            placeholder="Select metrics...",
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
                html.Div(
                    className="pqc-qc-plottype-wrap",
                    children=[
                        html.Div("Plot Type", className="pqc-field-label"),
                        dcc.Dropdown(
                            id="qc-plot-type",
                            options=PLOT_TYPE_OPTIONS,
                            value="line",
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
        Input("qc-plot-type", "value"),
    )
    def plot_qc_figure(data_in, metrics_in, x_in, plot_type_in):
        """Creates the QC trend plot figure with multiple metrics support."""
        data = data_in
        if data is None:
            raise PreventUpdate
        x = x_in or "RawFile"
        plot_type = plot_type_in or "line"

        # Handle both single metric (string) and multiple metrics (list)
        if metrics_in is None:
            selected_metrics = ["N_peptides"]
        elif isinstance(metrics_in, str):
            selected_metrics = [metrics_in]
        else:
            selected_metrics = list(metrics_in) if metrics_in else ["N_peptides"]

        df = pd.DataFrame(data)
        if df.empty:
            return (
                go.Figure(),
                T.gen_figure_config(filename="QC-plot", editable=False),
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

        # Filter to valid metrics that exist in the data
        valid_metrics = [m for m in selected_metrics if m in df.columns]
        if not valid_metrics:
            return (
                go.Figure(),
                T.gen_figure_config(filename="QC-trends", editable=False),
                {**GRAPH_STYLE, "display": "none"},
                {"display": "flex"},
            )

        x_axis_label = X_AXIS_LABELS.get(x, x)

        raw_labels = (
            df["RawFile"].astype(str)
            if "RawFile" in df.columns
            else df.index.astype(str)
        )
        acquired = df["DateAcquired"].astype(str).replace("NaT", "N/A")

        fig = go.Figure()

        # Create a trace for each selected metric
        for i, metric in enumerate(valid_metrics):
            y_series = pd.to_numeric(df[metric], errors="coerce").fillna(0)
            metric_label = METRIC_LABELS.get(metric, metric)
            color = METRIC_COLORS[i % len(METRIC_COLORS)]

            if plot_type == "bar":
                fig.add_trace(
                    go.Bar(
                        x=df[x],
                        y=y_series,
                        name=metric_label,
                        marker=dict(color=color, opacity=0.85),
                        hovertext=raw_labels + "<br>" + acquired,
                        hovertemplate=(
                            "<b>%{hovertext}</b><br>"
                            + f"{metric_label}: "
                            + "%{y:.2f}<extra></extra>"
                        ),
                    )
                )
            else:
                fig.add_trace(
                    go.Scatter(
                        x=df[x],
                        y=y_series,
                        name=metric_label,
                        mode="lines+markers",
                        line=dict(width=3, color=color, shape="linear"),
                        marker=dict(size=8, color=color, line=dict(width=1, color="#ffffff")),
                        hovertext=raw_labels + "<br>" + acquired,
                        text=None if x == "RawFile" else raw_labels,
                        hovertemplate=(
                            "<b>%{hovertext}</b><br>"
                            + f"{metric_label}: "
                            + "%{y:.2f}<extra></extra>"
                        ),
                    )
                )

        # Show legend when multiple metrics are selected
        show_legend = len(valid_metrics) > 1

        # Adjust height based on legend
        height = 500 if show_legend else 450

        fig.update_layout(
            hovermode="x unified" if plot_type == "bar" else "closest",
            hoverlabel_namelength=-1,
            height=height,
            showlegend=show_legend,
            legend=dict(
                orientation="h",
                yanchor="bottom",
                y=1.02,
                xanchor="left",
                x=0,
            ),
            margin=dict(l=32, r=20, b=60, t=50 if show_legend else 24, pad=0),
            font=C.figure_font,
            plot_bgcolor="#fbfdff",
            paper_bgcolor="#f7fbfe",
            yaxis={"automargin": True},
            xaxis={"automargin": True},
            barmode="group" if plot_type == "bar" else None,
        )

        fig.update_traces(opacity=0.95)

        logging.info(f"QC plot built for metrics {valid_metrics} with plot type {plot_type}")

        fig.update_xaxes(
            title_text=x_axis_label,
            showgrid=False,
            zeroline=False,
            showline=True,
            linecolor="#cddbe6",
        )

        # Y-axis label: combine metric names if multiple, or use single metric label
        if len(valid_metrics) == 1:
            y_label = METRIC_LABELS.get(valid_metrics[0], valid_metrics[0])
        else:
            y_label = "Value"

        fig.update_yaxes(
            title_text=y_label,
            showgrid=False,
            zeroline=False,
            showline=True,
            linecolor="#cddbe6",
            rangemode="tozero",
        )

        config = T.gen_figure_config(filename="QC-trends", editable=False)

        graph_style = {**GRAPH_STYLE, "display": "block"}

        return fig, config, graph_style, {"display": "none"}
