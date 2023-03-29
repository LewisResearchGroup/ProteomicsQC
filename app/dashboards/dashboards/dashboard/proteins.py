import logging
import pandas as pd

from dash import html, dcc
from dash import dash_table
import dash_bootstrap_components as dbc

from dash.dependencies import Input, Output, State
from dash.exceptions import PreventUpdate

from plotly import express as px

from dash_tabulator import DashTabulator

try:
    from .tools import list_to_dropdown_options
    from . import tools as T
except:
    from tools import list_to_dropdown_options
    import tools as T


tabulator_options = {
    "groupBy": "Label",
    "selectable": True,
    "headerFilterLiveFilterDelay": 3000,
    "layout": "fitDataFill",
    "height": "500px",
}

downloadButtonType = {
    "css": "btn btn-primary",
    "text": "Export",
    "type": "csv",
    "filename": "data",
}

clearFilterButtonType = {"css": "btn btn-outline-dark", "text": "Clear Filters"}

proteins_table = html.Div(
    id="proteins-table-container",
    style={"minHeight": 100, "margin": "0%"},
    children=[
        DashTabulator(
            id="proteins-table",
            columns=T.gen_tabulator_columns(
                col_names=["protein_names", "Fasta headers", "Score", "Intensity"],
                col_width=300,
            ),
            options=tabulator_options,
            downloadButtonType=downloadButtonType,
            clearFilterButtonType=clearFilterButtonType,
        )
    ],
)


plot_columns = [
    # 'Peptide counts (all)',
    # 'Peptide counts (razor+unique)',
    # 'Peptide counts (unique)',
    # 'Number of proteins', 'Sequence coverage [%]',
    "Unique + razor sequence coverage [%]",
    "Unique sequence coverage [%]",
    "Score",
    "Reporter intensity corrected",
    "Reporter intensity corrected (normalized)",
]

layout = html.Div(
    [

        dcc.Dropdown(
            id="proteins-options",
            placeholder="Options",
            options=[
                {"value": "remove_contaminants", "label": "Remove contaminants"},
                {
                    "value": "remove_reversed_sequences",
                    "label": "Remove reversed sequences",
                },
            ],
            value=['remove_contaminants', 'remove_reversed_sequences'],
            multi=True,
            style={"margin-top": "50px", "margin-bottom": "50px"},
        ),

        html.Button("Update table", id="proteins-update"),

        dcc.Loading(proteins_table),
        dcc.Dropdown(
            id="protein-plot-column",
            multi=False,
            options=list_to_dropdown_options(plot_columns),
            placeholder="Select data columns",
            value="Reporter intensity corrected",
            style={
                "width": "100%",
                "max-width": "100%",
                "margin-top": "50px",
                "margin-bottom": "50px",
            },
        ),
        html.Button("Update figure", id="proteins-fig-update"),
        dcc.Loading(
            [
                html.Div(style={"min-width": 400}),
                dcc.Graph(
                    id="protein-figure",
                    config=T.gen_figure_config(filename="protein-groups"),
                ),
            ]
        ),
    ]
)


def callbacks(app):
    @app.callback(
        Output("proteins-table", "data"),
        Input("proteins-update", "n_clicks"),
        State("project", "value"),
        State("pipeline", "value"),
        State("qc-table", "data"),
        State("tabs", "value"),
        State("proteins-options", "value"),
    )
    def refresh_proteins_table(n_clicks, project, pipeline, data, tab, options):
        if (project is None) or (pipeline is None):
            raise PreventUpdate
        if tab != "proteins":
            raise PreventUpdate

        raw_files = list(pd.DataFrame(data).RawFile.values)

        df = pd.DataFrame(
            T.get_protein_names(
                project=project,
                pipeline=pipeline,
                remove_contaminants="remove_contaminants" in options,
                remove_reversed_sequences="remove_reversed_sequences" in options,
                raw_files=raw_files,
            )
        )
        return df.to_dict("records")

    @app.callback(
        Output("protein-figure", "figure"),
        Output("protein-figure", "config"),
        Input("proteins-fig-update", "n_clicks"),
        State("proteins-table", "data"),
        State("proteins-table", "multiRowsClicked"),
        State("protein-plot-column", "value"),
        State("project", "value"),
        State("pipeline", "value"),
        State("data-range", "value"),
        State("qc-table", "data"),
        State("qc-table", "derived_virtual_indices"),
    )
    def plot_protein_figure(
        n_clicks,
        data,
        ndxs,
        plot_column,
        project,
        pipeline,
        data_range,
        qc_data,
        derived_virtual_indices,
    ):
        """Create the protein groups figure."""
        if (project is None) or (pipeline is None):
            raise PreventUpdate
        if (ndxs is None) or (ndxs == []):
            raise PreventUpdate

        if plot_column == "Reporter intensity corrected (normalized)":
            plot_column = "Reporter intensity corrected"
            normalized = True
        else:
            normalized = False

        protein_names = list(pd.DataFrame(ndxs)["protein_names"])

        qc_data = pd.DataFrame(qc_data)

        if derived_virtual_indices is not None:
            qc_data = qc_data.reindex(derived_virtual_indices)

        raw_files = list(qc_data.RawFile.values)

        data = T.get_protein_groups(
            project,
            pipeline,
            protein_names=protein_names,
            columns=[plot_column],
            data_range=data_range,
            raw_files=raw_files,
        )

        df = pd.read_json(data)

        color = None

        if plot_column == "Reporter intensity corrected":
            id_vars = ["RawFile", "Majority protein IDs"]
            df = (
                df.set_index(id_vars)
                .filter(regex=plot_column)
                .reset_index()
                .melt(id_vars=id_vars, var_name="TMT Channel", value_name=plot_column)
            )

            df["TMT Channel"] = df["TMT Channel"].apply(
                lambda x: f"{int(x.split()[3]):02.0f}"
            )
            if normalized:
                df[plot_column] = (
                    df[plot_column]
                    / df.groupby(["RawFile", "Majority protein IDs"]).transform("sum")[
                        plot_column
                    ]
                )
            color = "TMT Channel"
            df = df.sort_values(["RawFile", "TMT Channel"])
        else:
            df = df.sort_values("RawFile")

        n_rows = len(df["Majority protein IDs"].drop_duplicates())

        height = 300 * n_rows + (100 * n_rows)

        if n_rows <= 1:
            facet_row_spacing = 0.04
        else:
            facet_row_spacing = min(0.04, (1 / (n_rows - 1)))

        fig = px.bar(
            data_frame=df,
            x="RawFile",
            y=plot_column,
            facet_col="Majority protein IDs",
            facet_col_wrap=1,
            color=color,
            color_discrete_sequence=px.colors.qualitative.Dark24,
            color_continuous_scale=px.colors.sequential.Rainbow,
            facet_row_spacing=facet_row_spacing,
            height=height,
            category_orders={"RawFile": raw_files},
        )

        fig.for_each_annotation(lambda a: a.update(text=a.text.split("=")[-1]))

        fig.update(layout_showlegend=True)
        fig.update_layout(hovermode="closest")
        fig.update_xaxes(matches="x")
        fig.update_xaxes(automargin=True)
        fig.update_yaxes(automargin=True)
        fig.update_yaxes(matches=None)

        if normalized:
            fig.update_layout(yaxis=dict(range=[0, 1]))

        config = T.gen_figure_config(filename="PQC-protein-quant")

        return fig, config
