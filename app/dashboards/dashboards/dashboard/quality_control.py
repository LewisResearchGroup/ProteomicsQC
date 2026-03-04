import logging
import re
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
    "__tmt_peptides_per_sample__": "Peptides per TMT Sample",
    "__tmt_protein_groups_per_sample__": "Protein Groups per TMT Sample",
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
        "__tmt_peptides_per_sample__",
        "N_protein_groups",
        "__tmt_protein_groups_per_sample__",
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
            type="circle",
            children=[
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
        if x == "Index" and "Index" in df.columns:
            df = df.sort_values("Index", na_position="last").reset_index(drop=True)
            df["Index"] = pd.RangeIndex(start=1, stop=len(df) + 1)

        if selected_metric not in df.columns:
            synthetic_metric_cols = {
                "__tmt_peptides_per_sample__": (
                    r"^TMT\d+_peptide_count$",
                    "Peptide Count",
                ),
                "__tmt_protein_groups_per_sample__": (
                    r"^TMT\d+_protein_group_count$",
                    "Protein Group Count",
                ),
            }
            if selected_metric in synthetic_metric_cols:
                tmt_pattern, y_axis_title = synthetic_metric_cols[selected_metric]
                tmt_cols = sorted(
                    [c for c in df.columns if re.match(tmt_pattern, str(c))],
                    key=lambda c: int(re.search(r"\d+", str(c)).group(0)),
                )
                if len(tmt_cols) == 0:
                    return (
                        go.Figure(),
                        T.gen_figure_config(filename="QC-trends", editable=False),
                        {**GRAPH_STYLE, "display": "none"},
                        {"display": "flex"},
                    )

                if "Index" in df.columns:
                    df = df.sort_values("Index", na_position="last").reset_index(drop=True)
                else:
                    df = df.reset_index(drop=True)
                if "RawFile" not in df.columns:
                    df["RawFile"] = [f"Run {i+1}" for i in range(len(df))]

                axis_mode = x if x in {"Index", "RawFile", "DateAcquired"} else "Index"

                def _sample_axis_label(row, run_idx):
                    if axis_mode == "RawFile":
                        return str(row.get("RawFile", f"Sample {run_idx + 1}"))
                    if axis_mode == "DateAcquired":
                        dt_value = row.get("DateAcquired")
                        dt = pd.to_datetime(dt_value, errors="coerce")
                        if pd.notna(dt):
                            return dt.strftime("%Y-%m-%d")
                    return f"Sample {run_idx + 1}"

                expanded_rows = []
                for run_idx, row in df.iterrows():
                    run_label = str(row.get("RawFile", f"Run {run_idx + 1}"))
                    sample_label = _sample_axis_label(row, run_idx)
                    for col in tmt_cols:
                        channel_no = int("".join(ch for ch in str(col) if ch.isdigit()))
                        value = pd.to_numeric(
                            pd.Series([row.get(col)]), errors="coerce"
                        ).iloc[0]
                        value = 0.0 if pd.isna(value) else float(value)
                        expanded_rows.append(
                            {
                                "x_label": f"{run_label} / TMT{channel_no}",
                                "x_label_short": f"R{run_idx + 1}-T{channel_no}",
                                "sample_label": sample_label,
                                "run_label": run_label,
                                "channel_no": channel_no,
                                "value": value,
                                "run_idx": int(run_idx),
                            }
                        )
                long_df = pd.DataFrame(expanded_rows)
                if long_df.empty:
                    return (
                        go.Figure(),
                        T.gen_figure_config(filename="QC-trends", editable=False),
                        {**GRAPH_STYLE, "display": "none"},
                        {"display": "flex"},
                    )

                metric_label = METRIC_LABELS.get(selected_metric, selected_metric)
                long_df["x_pos"] = range(1, len(long_df) + 1)
                sample_tick_df = (
                    long_df.groupby(["run_idx", "sample_label"], as_index=False)["x_pos"]
                    .mean()
                    .sort_values("run_idx")
                )
                tickvals = sample_tick_df["x_pos"].tolist()
                ticktext = sample_tick_df["sample_label"].tolist()

                fig = go.Figure(
                    data=[
                        go.Scatter(
                            x=long_df["x_pos"],
                            y=long_df["value"],
                            mode="lines+markers",
                            showlegend=False,
                            marker=dict(
                                size=6,
                                color="#2a809d",
                                line=dict(width=0.8, color="#ffffff"),
                            ),
                            line=dict(width=1.6, color="rgba(42, 128, 157, 0.55)"),
                            text=long_df["x_label"],
                            customdata=long_df["run_idx"],
                            hovertemplate=(
                                "<b>%{text}</b><br>"
                                + f"{metric_label}: "
                                + "%{y:.0f}<extra></extra>"
                            ),
                        )
                    ]
                )
                fig.update_layout(
                    hovermode="closest",
                    hoverlabel_namelength=-1,
                    height=475,
                    showlegend=False,
                    margin=dict(l=32, r=20, b=60, t=24, pad=0),
                    font=C.figure_font,
                    plot_bgcolor="#fbfdff",
                    paper_bgcolor="#f7fbfe",
                    yaxis={"automargin": True},
                    xaxis={"automargin": True},
                )
                fig.update_xaxes(
                    title_text=X_AXIS_LABELS.get(axis_mode, "Sample"),
                    tickmode="array",
                    tickvals=tickvals,
                    ticktext=ticktext,
                    showgrid=False,
                    zeroline=False,
                    showline=True,
                    linecolor="#cddbe6",
                    tickangle=-90,
                    title_standoff=20,
                )
                fig.update_yaxes(
                    title_text=y_axis_title,
                    showgrid=False,
                    zeroline=False,
                    showline=True,
                    linecolor="#cddbe6",
                    rangemode="tozero",
                    title_standoff=16,
                )
                config = T.gen_figure_config(filename="QC-trends", editable=False)
                graph_style = {**GRAPH_STYLE, "display": "block"}
                return fig, config, graph_style, {"display": "none"}

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
                    customdata=df.index.to_list(),
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
            height=475,
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
        if x == "Index":
            fig.update_xaxes(dtick=1, tickformat="d")
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
