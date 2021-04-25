import os
import sys
import pandas as pd
import numpy as np
import requests

import dash
import plotly
import dash_core_components as dcc
import dash_html_components as html
import dash_bootstrap_components as dbc
import plotly.express as px

import dash_table as dt
import dash_table

from dash.dependencies import Input, Output, State
from dash.exceptions import PreventUpdate
#from flask_caching import Cache
#from cache_memoize import cache_memoize

from lrg_omics.plotly import plotly_heatmap, plotly_bar, plotly_histogram, set_template
from plotly.subplots import make_subplots
import plotly.graph_objects as go

from scipy.cluster.hierarchy import linkage, dendrogram
from scipy.spatial.distance import pdist, squareform



set_template()


if __name__ == '__main__':
    app = dash.Dash(__name__)
    import proteins, quality_control, explorer
    from tools import table_from_dataframe, get_projects, get_pipelines,\
        get_protein_groups, get_qc_data, list_to_dropdown_options, get_protein_names
    
    import tools as T

    from config import qc_columns_always, data_range_options

    app.config.suppress_callback_exceptions = True
    #from style import graph_style
else:
    from django_plotly_dash import DjangoDash
    from . import proteins, quality_control, explorer
    from .tools import table_from_dataframe, get_projects, get_pipelines,\
        get_protein_groups, get_qc_data, list_to_dropdown_options, get_protein_names

    from . import tools as T

    from .config import qc_columns_always, data_range_options

    #from .style import graph_style
    app = DjangoDash('dashboard', 
                     add_bootstrap_links=True,
                     suppress_callback_exceptions=True, 
                     external_stylesheets=[] )

timeout = 360

protein_table_default_cols = []

layout = html.Div([
    dcc.Loading(dcc.Store(id='store')),
    html.H1('Dashboard'),
    dbc.Row([
      dbc.Col([
        html.Button('Load projects and pipelines', id='B_update', className='btn'),
        dcc.Dropdown(
            id='project',
            options=get_projects(),
            value='lsarp')]),
      dbc.Col([
        dcc.Dropdown(
            id='pipeline',
            options=[],
            value=None)
      ]),
      dbc.Col([
           html.Div(dcc.Dropdown(id='data-range', options=data_range_options, value='last-30'), style={'display': 'block'}),
      ])
    ], style={'width': 300, 'display': 'inline-block'}),

    dcc.Markdown('---'),
    
    dbc.Row([
      dbc.Col(html.Div([
              dcc.Tabs(id="tabs", value='quality_control', children=[
                      dcc.Tab(id='tab-qc', label='Quality Control', value='quality_control'),
                      dcc.Tab(id='tab-explorer', label='Explorer', value='explorer'),
                      dcc.Tab(label='Proteins', value='proteins'),
                  ]),
                dcc.Markdown('---'),
                html.Div(id='tabs-content'),
          ]))]),
          
    ], style={'max-width': '90%', 'display': 'block', 'margin': 'auto'}
)

app.layout = layout

@app.callback(
    Output('tabs-content', 'children'),
    [Input('tabs', 'value')])
def render_content(tab):
    if tab == 'proteins':
        return proteins.layout
    if tab == 'quality_control':
        return quality_control.layout
    if tab == 'explorer':
        return explorer.layout

@app.callback(
    Output('project', 'options'),
    [Input('B_update','n_clicks')])
def populate_projects(project):
    return get_projects()

@app.callback(
    Output('pipeline', 'options'),
    [Input('project','value')])
def populate_pipelines(project):
    return get_pipelines(project)


@app.callback(
Output('protein-table-div','children'),
[Input('project', 'value'),
 Input('pipeline', 'value'),
 Input('tabs', 'value')])
def refresh_protein_table(project, pipeline, tab):
    if (project is None) or (pipeline is None):
        raise PreventUpdate
    if (tab != 'proteins'):
        raise PreventUpdate
    data = get_protein_names(project=project, pipeline=pipeline)
    print(type(data))
    df = pd.DataFrame(data)
    print('Generated dataframe:', df)
    return table_from_dataframe(df, id='protein-table')


@app.callback(
Output('qc-table-div', 'children'),
[Input('qc-update-table', 'n_clicks')],
[State('tabs', 'value'),
 State('pipeline', 'value'),
 State('project', 'value'),
 State('qc-table-columns', 'value'),
 State('data-range', 'value')])
def refresh_qc_table(n_clicks, tab, pipeline, project, optional_columns, data_range):
    if (project is None) or (pipeline is None):
        raise PreventUpdate    
    if (tab != 'quality_control'):
        raise PreventUpdate
    columns = qc_columns_always+optional_columns
    data = get_qc_data(project=project, pipeline=pipeline, columns=columns, data_range=data_range)
    df = pd.DataFrame( data )
    if 'DateAcquired' in df.columns:
        df['DateAcquired'] = pd.to_datetime( df['DateAcquired'] )
        df = df.replace('not detected', np.NaN)[qc_columns_always+optional_columns]
    return table_from_dataframe(df, id='qc-table')


@app.callback(
[Output('protein-figure','figure'),
 Output('protein-figure','config')],
[Input('protein-table', 'data'),
 Input('protein-table', 'selected_rows'),
 Input('protein-plot-column', 'value')],
[State('project', 'value'),
 State('pipeline', 'value')])
def plot_protein_figure(data, ndxs, plot_column, project, pipeline):
    '''Create the protein groups figure.'''
    if (project is None) or (pipeline is None):
        raise PreventUpdate
    if (ndxs is None) or (ndxs == []):
        raise PreventUpdate

    if plot_column == 'Reporter intensity corrected (normalized)':
        plot_column = 'Reporter intensity corrected'
        normalized = True
    else:
        normalized = False

    df = pd.DataFrame(data)
    protein_names = list( df.iloc[ndxs, 0] )

    data = get_protein_groups(project, pipeline, protein_names=protein_names, 
            columns=[plot_column])

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

    fig = px.bar(data_frame=df, x='RawFile', y=plot_column, facet_col='Majority protein IDs', facet_col_wrap=1, 
                 color=color, color_discrete_sequence=px.colors.qualitative.Dark24,
                 color_continuous_scale=px.colors.sequential.Rainbow)

    n_rows = len(df['Majority protein IDs'].drop_duplicates())

    height = 300*(1+n_rows)

    fig.update_layout(
            height=height,        
            margin=dict( l=50, r=10, b=200, t=50, pad=0 ),
            hovermode='closest')

    fig.for_each_annotation(lambda a: a.update(text=a.text.split("=")[-1]))
    fig.update(layout_showlegend=True)
    fig.update_xaxes(matches='x')

    if normalized: fig.update_layout(yaxis=dict(range=[0,1]))

    config = T.gen_figure_config(filename='protein-quant', format='svg')

    return fig, config


inputs = [Input('refresh-plots', 'n_clicks')]
states = [State('qc-table', 'derived_virtual_selected_rows'),
          State('qc-table', 'derived_virtual_indices'),
          State('x','value'),
          State('qc-table', 'data'),
          State('qc-table-columns', 'value')]

plot_map = [
    {'title': 'PSMs [%]',
     'plots': [
        {'y': 'MS/MS Identified [%]', 
         'label': 'n_psm'}]
    },
    {'title': 'Peptides / Protein Groups',
     'plots': [
        {'y': 'N_peptides',
         'label': 'n_peptides'},
        {'y': 'N_protein_groups',
         'label': 'n_proteins'}]
    },
    {'title': 'Oxidations [%]',
     'plots': [{
        'y': 'Oxidations [%]',
        'label': 'Oxidations [%]'}]
    },
    {'title': 'Missed Cleavages [%]',
     'plots': [
        {'y': 'N_missed_cleavages_eq_1 [%]',
         'label': 'Missed Cleavages [%]'},]
    },
    {'title': 'Median fill times (ms)',
     'plots': [
        {'y': 'MedianMs1FillTime(ms)',
         'label': 'Median MS1 Fill Time'},
        {'y': 'MedianMs2FillTime(ms)',
         'label': 'Median MS2 Fill Time'}]
    },
    {'title': 'Total MS Scans',
     'plots': [
        {'y': 'NumMs1Scans',
         'label': '# MS1 scans'},
        {'y': 'NumMs2Scans',
         'label': '# MS2 scans'}, 
        {'y': 'NumMs3Scans',
         'label': '# MS3 scans'} ]
    },
    {'title': 'ESI Instability Flags',
     'plots': [
        {'y': 'NumEsiInstabilityFlags',
         'label': 'ESI Instability'}]
    }
]


#@lru_cache(maxsize=32)
@app.callback(
    Output('qc-figure', 'figure'),
    Output('qc-figure', 'config'),
    inputs,
    states)
def plot_qc_figure(refresh, selected, ndxs, x, data, optional_columns):
    '''Creates the bar-plot figure'''
    if (data is None) or (ndxs is None) or (len(ndxs) == 0):
        raise PreventUpdate
    
    if x is None:
        x = 'RawFile'

    titles = [el['title'] for el in plot_map]
    
    df = pd.DataFrame(data)

    assert pd.value_counts(df.columns).max() == 1, pd.value_counts(df.columns)
    df['DateAcquired'] = pd.to_datetime(df['DateAcquired'])

    if ndxs is not None: df = df.reindex(ndxs)
    
    numeric_columns = df[optional_columns].head(1)._get_numeric_data().columns

    fig = make_subplots(cols=1, rows=len(numeric_columns), 
                        subplot_titles=numeric_columns,
                        shared_xaxes=True,
                        vertical_spacing=0.05,
                        print_grid=True)

    for i, col in enumerate(numeric_columns):
        trace = go.Bar(x=df[x], y=df[col], name=col,
                       text=None if x == 'RawFile' else df['RawFile']
                       )
        fig.add_trace(trace, row=1+i, col=1)        

    fig.update_layout(hovermode='closest')

    fig.update_layout(
        height=200+250*(i+1),
        showlegend=False,
        margin=dict(
            l=50,
            r=10,
            b=200,
            t=50,
            pad=0
        ),
    )    
    
    fig.update_traces(marker_color='rgb(158,202,225)', 
                      marker_line_color='rgb(8,48,107)',
                      marker_line_width=1.5, opacity=0.6)

    fig.update_xaxes(matches='x')

    if x == 'RawFile':
        fig.update_layout(
            xaxis5 = dict(
                tickmode = 'array',
                tickvals = tuple(range(len(df))),
                ticktext = tuple(df[x])
            )
        )
 
    config = T.gen_figure_config(filename='QC-barplot')
    
    return fig, config


# EXPLORER Callbacks
@app.callback(
[Output('explorer-figure', 'figure'),
 Output('explorer-figure', 'config')],
[Input('explorer-x', 'value'),
 Input('explorer-y', 'value'),
 Input('explorer-color', 'value'),
 Input('explorer-size', 'value'),
 Input('explorer-facet-row', 'value'),
 Input('explorer-facet-col', 'value')],
[State('project', 'value'),
 State('pipeline', 'value'),
 State('data-range', 'value')]
)
def explorer_plot(x, y, color, size, facet_row, facet_col, project, pipeline, data_range):
    if (project is None) or (pipeline is None):
        raise PreventUpdate

    print(x, y, project, pipeline, data_range, file=sys.stderr)

    columns = [x, y, color, size, facet_row, facet_col, 'RawFile', 'Index', 'DateAcquired']

    if y is None:
        raise PreventUpdate

    if None in columns:
        columns.remove(None)
    
    columns = [c for c in columns if (c is not None)]

    data = get_qc_data(project=project, pipeline=pipeline, columns=columns, data_range=data_range)
    df = pd.DataFrame( data )
    df['DateAcquired'] = pd.to_datetime( df['DateAcquired'] )

    if facet_row is not None:
        n_rows = len(df[facet_row].value_counts())
    else:
        n_rows = 2

    facet_col_wrap = 3
    if facet_col is not None:
        n_cols = len(df[facet_col].value_counts())
        n_rows = min(2, int(n_cols / facet_col_wrap)+2)

    if size is not None:
        # Plotly crashes if size column has NaNs
        df[size] = df[size].fillna(0)

    fig = px.scatter(data_frame=df, x=x, y=y, color=color, size=size, facet_row=facet_row, 
                     facet_col=facet_col, hover_data=['Index', 'RawFile'], facet_col_wrap=facet_col_wrap)

    fig.update_layout(
            autosize=True,
            height=300*n_rows+200,
            showlegend=False,
            margin=dict(
                l=50,
                r=10,
                b=200,
                t=50,
                pad=0
            ))

    config = T.gen_figure_config(filename='QC-scatter')

    return fig, config


if __name__ == '__main__':
    app.run_server(debug = True)