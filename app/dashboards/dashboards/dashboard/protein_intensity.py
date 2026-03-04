import logging

import numpy as np
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from dash import dcc, html
from dash.dependencies import Input, Output, State
from dash.exceptions import PreventUpdate

try:
    from . import config as C
    from . import tools as T
except Exception as e:
    logging.warning(e)
    import config as C
    import tools as T


X_AXIS_LABELS = {
    "Index": "Sample Index",
    "RawFile": "Sample",
    "DateAcquired": "Acquisition Date",
}
X_AXIS_OPTIONS = [{"label": v, "value": k} for k, v in X_AXIS_LABELS.items()]

GRAPH_STYLE = {"maxWidth": "100%"}


layout = html.Div(
    [
        html.Div(
            className="pqc-qc-plot-toolbar",
            children=[
                html.Div(
                    className="pqc-qc-metric-wrap",
                    children=[
                        html.Div("Protein IDs", className="pqc-field-label"),
                        dcc.Dropdown(
                            id="protein-intensity-proteins",
                            options=[],
                            value=[],
                            multi=True,
                            placeholder="Select one or more proteins",
                            className="pqc-scope-dropdown pqc-protein-intensity-dropdown",
                        ),
                    ],
                ),
                html.Div(
                    className="pqc-qc-xaxis-wrap",
                    children=[
                        html.Div("Single-protein x-axis", className="pqc-field-label"),
                        dcc.Dropdown(
                            id="protein-intensity-x",
                            options=X_AXIS_OPTIONS,
                            value="Index",
                            clearable=False,
                            className="pqc-scope-dropdown pqc-protein-intensity-dropdown",
                        ),
                    ],
                ),
            ],
        ),
        html.Div(
            "Select proteins to visualize intensity distributions.",
            id="protein-intensity-empty-state",
            className="pqc-empty-state",
        ),
        dcc.Loading(
            type="circle",
            children=[
                dcc.Graph(
                    id="protein-intensity-figure",
                    style={**GRAPH_STYLE, "display": "none"},
                ),
            ],
        ),
    ]
)


def callbacks(app):
    @app.callback(
        Output("protein-intensity-proteins", "options"),
        Output("protein-intensity-proteins", "value"),
        Input("tabs", "value"),
        Input("project", "value"),
        Input("pipeline", "value"),
        Input("qc-scope-data", "data"),
        State("protein-intensity-proteins", "value"),
    )
    def update_protein_dropdown(tab, project, pipeline, scope_data, current_values, **kwargs):
        current_values = list(current_values or [])
        if tab != "protein_intensity":
            raise PreventUpdate
        if not project or not pipeline:
            return [], []

        scope_df = pd.DataFrame(scope_data or [])
        if scope_df.empty or ("RawFile" not in scope_df.columns):
            return [], []
        raw_files = scope_df["RawFile"].dropna().astype(str).tolist()
        if len(raw_files) == 0:
            return [], []

        user = kwargs.get("user")
        protein_data = T.get_protein_names(
            project=project,
            pipeline=pipeline,
            remove_contaminants=True,
            remove_reversed_sequences=True,
            raw_files=raw_files,
            user=user,
        )

        protein_df = pd.DataFrame(protein_data or {})
        if protein_df.empty or ("protein_names" not in protein_df.columns):
            return [], []

        protein_values = (
            protein_df["protein_names"]
            .dropna()
            .astype(str)
            .str.strip()
        )
        protein_values = sorted({p for p in protein_values if p != ""}, key=str.lower)
        options = [{"label": p, "value": p} for p in protein_values]
        value_set = {opt["value"] for opt in options}
        selected = [v for v in current_values if v in value_set]
        return options, selected

    @app.callback(
        Output("protein-intensity-figure", "figure"),
        Output("protein-intensity-figure", "config"),
        Output("protein-intensity-figure", "style"),
        Output("protein-intensity-empty-state", "children"),
        Output("protein-intensity-empty-state", "style"),
        Input("tabs", "value"),
        Input("protein-intensity-proteins", "value"),
        Input("protein-intensity-x", "value"),
        Input("project", "value"),
        Input("pipeline", "value"),
        Input("qc-scope-data", "data"),
    )
    def plot_protein_intensity(
        tab,
        proteins,
        x_axis,
        project,
        pipeline,
        scope_data,
        **kwargs,
    ):
        config = T.gen_figure_config(filename="PQC-protein-intensity", editable=False)
        hidden_style = {**GRAPH_STYLE, "display": "none"}
        shown_style = {**GRAPH_STYLE, "display": "block"}

        if tab != "protein_intensity":
            return go.Figure(), config, hidden_style, "Select proteins to visualize intensity distributions.", {"display": "none"}
        if not project or not pipeline:
            return go.Figure(), config, hidden_style, "Select a project and pipeline first.", {"display": "flex"}

        proteins = [str(p).strip() for p in (proteins or []) if str(p).strip()]
        proteins = list(dict.fromkeys(proteins))
        if len(proteins) == 0:
            return go.Figure(), config, hidden_style, "Select at least one protein.", {"display": "flex"}

        scope_df = pd.DataFrame(scope_data or [])
        if scope_df.empty or ("RawFile" not in scope_df.columns):
            return go.Figure(), config, hidden_style, "No scoped samples available for this view.", {"display": "flex"}

        scope_df["RawFile"] = scope_df["RawFile"].astype(str)
        scope_df = scope_df.drop_duplicates(subset=["RawFile"]).reset_index(drop=True)
        if "DateAcquired" in scope_df.columns:
            scope_df["DateAcquired"] = pd.to_datetime(scope_df["DateAcquired"], errors="coerce")
        else:
            scope_df["DateAcquired"] = pd.NaT

        if ("Index" in scope_df.columns) and pd.to_numeric(scope_df["Index"], errors="coerce").notna().any():
            scope_df["Index"] = pd.to_numeric(scope_df["Index"], errors="coerce")
            scope_df = scope_df.sort_values("Index", na_position="last").reset_index(drop=True)
            scope_df["Index"] = pd.RangeIndex(start=1, stop=len(scope_df) + 1)
        else:
            scope_df["Index"] = pd.RangeIndex(start=1, stop=len(scope_df) + 1)

        raw_files = scope_df["RawFile"].tolist()
        user = kwargs.get("user")
        payload = T.get_protein_groups(
            project=project,
            pipeline=pipeline,
            protein_names=proteins,
            columns=["Reporter intensity corrected"],
            data_range=None,
            raw_files=raw_files,
            user=user,
        )
        data_df = pd.DataFrame(payload) if payload else pd.DataFrame()
        if data_df.empty:
            return go.Figure(), config, hidden_style, "No protein intensity values found for the current selection.", {"display": "flex"}

        protein_col = "Majority protein IDs"
        if protein_col not in data_df.columns:
            return go.Figure(), config, hidden_style, "Protein IDs were not found in the intensity data.", {"display": "flex"}
        if "RawFile" not in data_df.columns:
            return go.Figure(), config, hidden_style, "Sample names were not found in the intensity data.", {"display": "flex"}

        intensity_cols = [
            col
            for col in data_df.columns
            if isinstance(col, str) and col.startswith("Reporter intensity corrected ")
        ]
        if len(intensity_cols) == 0:
            return go.Figure(), config, hidden_style, "No reporter intensity columns are available for these proteins.", {"display": "flex"}

        long_df = data_df[["RawFile", protein_col] + intensity_cols].melt(
            id_vars=["RawFile", protein_col],
            value_vars=intensity_cols,
            var_name="Channel",
            value_name="Intensity",
        )
        long_df["RawFile"] = long_df["RawFile"].astype(str)
        long_df["Intensity"] = pd.to_numeric(long_df["Intensity"], errors="coerce").fillna(0)
        long_df["Log2Intensity"] = np.log2(long_df["Intensity"] + 1.0)
        long_df["Channel"] = (
            long_df["Channel"]
            .astype(str)
            .str.replace("Reporter intensity corrected ", "", regex=False)
            .str.strip()
        )
        long_df["ChannelNo"] = pd.to_numeric(long_df["Channel"], errors="coerce")
        long_df = long_df[long_df["RawFile"].isin(raw_files)]
        if long_df.empty:
            return go.Figure(), config, hidden_style, "No intensity records match the selected samples.", {"display": "flex"}

        axis_df = scope_df[["RawFile", "Index", "DateAcquired"]].copy()
        axis_df["RawFileLabel"] = axis_df["RawFile"]
        long_df = long_df.merge(axis_df, on="RawFile", how="left")
        x_axis = x_axis if x_axis in X_AXIS_LABELS else "Index"

        if len(proteins) == 1:
            protein_name = proteins[0]
            single = long_df[long_df[protein_col] == protein_name].copy()
            if single.empty:
                return go.Figure(), config, hidden_style, "The selected protein has no intensity values in this scope.", {"display": "flex"}

            single = (
                single.groupby(
                    ["RawFile", "Channel", "ChannelNo", "Index", "DateAcquired", "RawFileLabel"],
                    as_index=False,
                )["Intensity"]
                .median()
            )
            single["Log2Intensity"] = np.log2(single["Intensity"] + 1.0)
            run_order = {raw: idx for idx, raw in enumerate(raw_files)}
            single["run_idx"] = single["RawFile"].map(run_order)
            single = single.sort_values(["run_idx", "ChannelNo"], na_position="last").reset_index(drop=True)
            if single.empty:
                return go.Figure(), config, hidden_style, "The selected protein has no intensity values in this scope.", {"display": "flex"}

            axis_mode = x_axis if x_axis in {"Index", "RawFile", "DateAcquired"} else "Index"

            def _sample_axis_label(row):
                if axis_mode == "RawFile":
                    return str(row.get("RawFileLabel", "Sample"))
                if axis_mode == "DateAcquired":
                    dt = pd.to_datetime(row.get("DateAcquired"), errors="coerce")
                    if pd.notna(dt):
                        return dt.strftime("%Y-%m-%d")
                return f"Sample {int(row.get('run_idx', 0)) + 1}"

            single["sample_label"] = single.apply(_sample_axis_label, axis=1)
            single["x_label"] = single.apply(
                lambda row: f"{row['RawFile']} / TMT{int(row['ChannelNo'])}"
                if pd.notna(row["ChannelNo"])
                else f"{row['RawFile']} / {row['Channel']}",
                axis=1,
            )
            single["x_pos"] = np.arange(1, len(single) + 1, dtype=int)
            sample_tick_df = (
                single.groupby(["run_idx", "sample_label"], as_index=False)["x_pos"]
                .mean()
                .sort_values("run_idx")
            )
            fig = go.Figure(
                data=[
                    go.Scatter(
                        x=single["x_pos"],
                        y=single["Log2Intensity"],
                        mode="lines+markers",
                        showlegend=False,
                        marker=dict(
                            size=8,
                            color="#2a809d",
                            line=dict(width=0.8, color="#ffffff"),
                        ),
                        line=dict(width=2, color="rgba(42, 128, 157, 0.55)"),
                        text=single["x_label"],
                        customdata=np.stack(
                            [
                                single["RawFile"].astype(str).values,
                                single["Channel"].astype(str).values,
                                single["Intensity"].astype(float).values,
                            ],
                            axis=1,
                        ),
                        hovertemplate=(
                            "<b>%{text}</b><br>"
                            "log2(1+intensity): %{y:.2f}<br>"
                            "Raw file: %{customdata[0]}<br>"
                            "Channel: %{customdata[1]}<br>"
                            "Intensity: %{customdata[2]:.2f}<extra></extra>"
                        ),
                    )
                ]
            )
        else:
            multi = long_df[long_df[protein_col].isin(proteins)].copy()
            if multi.empty:
                return go.Figure(), config, hidden_style, "No intensities were found for the selected proteins.", {"display": "flex"}

            fig = go.Figure()
            palette = px.colors.qualitative.Pastel
            for idx, protein_name in enumerate(proteins):
                protein_df = multi[multi[protein_col] == protein_name]
                if protein_df.empty:
                    continue
                fig.add_trace(
                    go.Violin(
                        x=np.repeat(protein_name, len(protein_df)),
                        y=protein_df["Log2Intensity"],
                        name=protein_name,
                        side="positive",
                        spanmode="manual",
                        span=[
                            0.0,
                            max(float(protein_df["Log2Intensity"].max()), 1e-6),
                        ],
                        box_visible=False,
                        meanline_visible=False,
                        points="all",
                        pointpos=-0.4,
                        jitter=0.24,
                        marker=dict(
                            size=6,
                            opacity=1,
                            color=palette[idx % len(palette)],
                        ),
                        line=dict(width=0),
                        fillcolor=palette[idx % len(palette)],
                        opacity=1,
                        customdata=np.stack(
                            [
                                protein_df["RawFile"].astype(str).values,
                                protein_df["Channel"].astype(str).values,
                                protein_df["Intensity"].astype(float).values,
                            ],
                            axis=1,
                        ),
                        hovertemplate=(
                            "<b>%{x}</b><br>"
                            "log2(1+intensity): %{y:.2f}<br>"
                            "Raw file: %{customdata[0]}<br>"
                            "Channel: %{customdata[1]}<br>"
                            "Intensity: %{customdata[2]:.2f}<extra></extra>"
                        ),
                    )
                )
        chart_height = 475 if len(proteins) == 1 else 450
        fig.update_layout(
            hovermode="closest",
            height=chart_height,
            margin=dict(l=32, r=20, b=50, t=20, pad=0),
            font=C.figure_font,
            plot_bgcolor="#fbfdff",
            paper_bgcolor="#f7fbfe",
            yaxis={"automargin": True},
            xaxis={"automargin": True},
            showlegend=False,
        )
        fig.update_xaxes(
            title_text=X_AXIS_LABELS.get(x_axis, "Sample") if len(proteins) == 1 else "Proteins",
            showgrid=False,
            zeroline=False,
            showline=True,
            linecolor="#cddbe6",
        )
        if len(proteins) == 1:
            fig.update_xaxes(
                tickmode="array",
                tickvals=sample_tick_df["x_pos"].tolist(),
                ticktext=sample_tick_df["sample_label"].tolist(),
                tickangle=-90,
                title_standoff=20,
            )
        else:
            y_max = pd.to_numeric(multi["Log2Intensity"], errors="coerce").max()
            y_max = 1.0 if pd.isna(y_max) else float(y_max)
            fig.update_yaxes(range=[-0.35, y_max + 0.8])
        fig.update_yaxes(
            title_text="Log2Intensity",
            showgrid=False,
            zeroline=False,
            showline=True,
            linecolor="#cddbe6",
            rangemode="tozero",
            title_standoff=16,
        )

        return fig, config, shown_style, "", {"display": "none"}
