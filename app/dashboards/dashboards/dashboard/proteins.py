import pandas as pd
import numpy as np

import dash_core_components as dcc
import dash_html_components as html 
import dash_bootstrap_components as dbc 

from dash.dependencies import Input, Output, State
from dash.exceptions import PreventUpdate

import dash_table as dt

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

downloadButtonType = {"css": "btn btn-primary", "text":"Export", "type":"csv", "filename":"data"}

clearFilterButtonType = {"css": "btn btn-outline-dark", "text":"Clear Filters"}

proteins_table = html.Div(id='proteins-table-container', 
    style={'minHeight':  100, 'margin': '0%'},
    children=[
        DashTabulator(id='proteins-table',
            columns=T.gen_tabulator_columns(col_names=['protein_names', 'Fasta headers', 'Score', 'Intensity'], col_width=300), 
            options=tabulator_options,
            downloadButtonType=downloadButtonType,
            clearFilterButtonType=clearFilterButtonType
        )
])



plot_columns = [
    # 'Peptide counts (all)',
    # 'Peptide counts (razor+unique)', 
    # 'Peptide counts (unique)',
    # 'Number of proteins', 'Sequence coverage [%]',   
       'Unique + razor sequence coverage [%]', 'Unique sequence coverage [%]',
       'Score', 'Reporter intensity corrected', 
       'Reporter intensity corrected (normalized)']

layout = html.Div([

    dcc.Dropdown(id='proteins-options', multi=True, value=[], placeholder='Table options...',
                 style={'margin-top': '50px', 'margin-bottom': '50px'},
                 options=[{'value': 'add-con', 'label': 'Include contaminants'},
                          {'value': 'add-rev', 'label': 'Include reversed sequences'}]),

    html.Button('Update table', id='proteins-update'), 
    dcc.Loading( proteins_table ),

    dcc.Dropdown(id='protein-plot-column', multi=False, options=list_to_dropdown_options(plot_columns), 
                placeholder='Select data columns', value='Reporter intensity corrected', 
                style={'width': '100%', 'max-width': '100%', 'margin-top': '50px', 'margin-bottom': '50px'}),

    html.Button('Update figure', id='proteins-fig-update'), 

    dcc.Loading([ 
        html.Div(style={'min-width': 400}),
        dcc.Graph(id="protein-figure", config=T.gen_figure_config(filename='protein-groups')),
    ]),

])

def callbacks(app):

    @app.callback(
        Output('proteins-table','data'),
        Input('proteins-update', 'n_clicks'),
        State('project', 'value'),
        State('pipeline', 'value'),
        State('tabs', 'value'),
        State('proteins-options', 'value'))
    def refresh_proteins_table(n_clicks, project, pipeline, tab, options):
        if (project is None) or (pipeline is None):
            raise PreventUpdate
        if (tab != 'proteins'):
            raise PreventUpdate

        df = pd.DataFrame( T.get_protein_names(
                                project=project, 
                                pipeline=pipeline, 
                                add_con='add-con' in options,
                                add_rev='add-rev' in options)
            ) 
        return df.to_dict('records')


    @app.callback(
        Output('protein-figure','figure'),
        Output('protein-figure','config'),
        Input('proteins-fig-update', 'n_clicks'),
        State('proteins-table', 'data'),
        State('proteins-table', 'multiRowsClicked'),
        State('protein-plot-column', 'value'),
        State('project', 'value'),
        State('pipeline', 'value'),
        State('data-range', 'value')
        )
    def plot_protein_figure(n_clicks, data, ndxs, plot_column, project, pipeline, data_range):
        '''Create the protein groups figure.'''
        if (project is None) or (pipeline is None): raise PreventUpdate
        if (ndxs is None) or (ndxs == []): raise PreventUpdate

        if plot_column == 'Reporter intensity corrected (normalized)':
            plot_column = 'Reporter intensity corrected'
            normalized = True
        else:
            normalized = False

        protein_names = list( pd.DataFrame(ndxs)['protein_names'] )

        data = T.get_protein_groups(project, pipeline, 
            protein_names=protein_names, 
            columns=[plot_column],
            data_range=data_range)

        df = pd.read_json( data )

        color = None

        if plot_column == 'Reporter intensity corrected':
            id_vars = ['RawFile', 'Majority protein IDs']
            df = df.set_index(id_vars).filter(regex=plot_column)\
                   .reset_index().melt(id_vars=id_vars, var_name='TMT Channel', value_name=plot_column)

            df['TMT Channel'] = df['TMT Channel'].apply(lambda x: f'{int(x.split()[3]):02.0f}')
            if normalized: df[plot_column] =  df[plot_column] / df.groupby(['RawFile', 'Majority protein IDs']).transform('sum')[plot_column]
            color = 'TMT Channel'
            df = df.sort_values(['RawFile', 'TMT Channel'])
        else:
            df = df.sort_values('RawFile')

        n_rows = len(df['Majority protein IDs'].drop_duplicates())

        height = 300 * n_rows + (100 * n_rows^2)

        if n_rows <= 1:
            facet_row_spacing = 0.04
        else:
            facet_row_spacing = min(0.04, (1 / (n_rows - 1)) )
        
        print(df.columns.to_list())

        df.sort_values('RawFile', inplace=True)

        fig = px.bar(data_frame=df, x='RawFile', y=plot_column, facet_col='Majority protein IDs', facet_col_wrap=1, 
                     color=color, color_discrete_sequence=px.colors.qualitative.Dark24,
                     color_continuous_scale=px.colors.sequential.Rainbow,
                     facet_row_spacing=facet_row_spacing, height=height)



        fig.for_each_annotation(lambda a: a.update(text=a.text.split("=")[-1]))

        fig.update_layout(hovermode='closest')
        fig.update(layout_showlegend=True)
        fig.update_xaxes(matches='x')
        fig.update_xaxes(automargin=True)
        fig.update_yaxes(automargin=True)

        if normalized: fig.update_layout(yaxis=dict(range=[0,1]))

        config = T.gen_figure_config(filename='protein-quant', format='svg')

        return fig, config