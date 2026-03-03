import logging
import pandas as pd
from dash import dcc, html

from dash.dependencies import Input, Output
from dash.exceptions import PreventUpdate

import plotly.graph_objects as go
import plotly.express as px
from plotly.subplots import make_subplots

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
        """Creates the QC trend plot figure with multiple metrics in separate facets."""
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

        n_metrics = len(valid_metrics)

        # Create subplots - one row per metric (faceted layout)
        subplot_titles = [METRIC_LABELS.get(m, m) for m in valid_metrics]
        fig = make_subplots(
            rows=n_metrics,
            cols=1,
            shared_xaxes=True,
            vertical_spacing=0.08 if n_metrics > 1 else 0,
            subplot_titles=subplot_titles if n_metrics > 1 else None,
        )

        # Create a trace for each metric in its own subplot
        for i, metric in enumerate(valid_metrics):
            row = i + 1
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
                        showlegend=False,
                    ),
                    row=row,
                    col=1,
                )
            else:
                fig.add_trace(
                    go.Scatter(
                        x=df[x],
                        y=y_series,
                        name=metric_label,
                        mode="lines+markers",
                        line=dict(width=2, color=color, shape="linear"),
                        marker=dict(size=6, color=color, line=dict(width=1, color="#ffffff")),
                        hovertext=raw_labels + "<br>" + acquired,
                        text=None if x == "RawFile" else raw_labels,
                        hovertemplate=(
                            "<b>%{hovertext}</b><br>"
                            + f"{metric_label}: "
                            + "%{y:.2f}<extra></extra>"
                        ),
                        showlegend=False,
                    ),
                    row=row,
                    col=1,
                )

            # Update y-axis for this subplot
            fig.update_yaxes(
                title_text=metric_label if n_metrics == 1 else None,
                showgrid=True,
                gridcolor="#e8f0f5",
                zeroline=False,
                showline=True,
                linecolor="#cddbe6",
                rangemode="tozero",
                automargin=True,
                row=row,
                col=1,
            )

        # Height scales with number of metrics
        height_per_metric = 200
        base_height = 150
        height = base_height + (n_metrics * height_per_metric)
        height = min(height, 1200)  # Cap at reasonable max

        fig.update_layout(
            hovermode="x unified",
            hoverlabel_namelength=-1,
            height=height,
            showlegend=False,
            margin=dict(l=80, r=20, b=120, t=40, pad=0),
            font=C.figure_font,
            plot_bgcolor="#fbfdff",
            paper_bgcolor="#f7fbfe",
        )

        fig.update_traces(opacity=0.95)

        logging.info(f"QC plot built for {n_metrics} metrics with plot type {plot_type}")

        # Update x-axis only on the bottom subplot
        fig.update_xaxes(
            title_text=x_axis_label,
            showgrid=False,
            zeroline=False,
            showline=True,
            linecolor="#cddbe6",
            tickangle=-45,
            row=n_metrics,
            col=1,
        )

        config = T.gen_figure_config(filename="QC-trends", editable=False)

        graph_style = {**GRAPH_STYLE, "display": "block"}

        return fig, config, graph_style, {"display": "none"}
