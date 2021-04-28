import os
import sys
import json
import requests
import pandas as pd
import dash_table as dt
from dash_table.Format import Format

URL = os.getenv('OMICS_URL', 'http://localhost:8000')
print(f'Dashboard API URL:{URL}', file=sys.stderr)


def list_to_dropdown_options(values):
    return [{'label': v, 'value': v} for v in values]


def table_from_dataframe(df, id='table', row_deletable=True, row_selectable='multi'):
    return dt.DataTable(
        id=id,
        columns=[{"name": i, "id": i, 'format': Format(precision=2)} for i in df.columns],
        data=df.iloc[::-1].to_dict('records'),
        sort_action="native",
        sort_mode="single",
        row_selectable=row_selectable,
        row_deletable=row_deletable,
        selected_rows=[],
        filter_action='native',
        page_action="native",
        page_current=0,
        page_size=16,
        style_table={'overflowX': 'scroll'},
        export_format='csv',
        export_headers='display',
        merge_duplicate_headers=True,
        style_cell={
            'font_size': '10px', 
            'padding-left': '5em', 
            'padding-right': '5em'}      
        )


def get_projects():
    url = f'{URL}/api/projects'
    print(f'URL: {url}', file=sys.stderr)
    try:
        json = requests.get(url).json()
    except:
        return []
    output = [ {'label': i['name'], 'value': i['slug']} for i in json]
    return output


def get_pipelines(project):
    url = f'{URL}/api/mq/pipelines?project={project}'
    print(f'URL:{url}', file=sys.stderr)
    json = requests.get(url).json()
    if len(json) == 0:
        return []
    else:
        output = [ {'label': i['name'], 'value': i['slug']} for i in json]
        return output


def get_protein_groups(project, pipeline, protein_names=None, 
        columns=None, data_range=None):
    url = f'{URL}/api/mq/protein-groups'
    headers = {'Content-type': 'application/json'}
    data =  json.dumps( dict(project=project, pipeline=pipeline, 
                             protein_names=protein_names,
                             columns=columns, data_range=data_range) )
    return requests.get(url, data=data, headers=headers).json()


def get_protein_names(project, pipeline):
    url = f'{URL}/api/mq/protein-names'
    headers = {'Content-type': 'application/json'}
    data =  json.dumps( dict(project=project, pipeline=pipeline) )
    obj = requests.post(url, data=data, headers=headers).json()
    return obj


def get_qc_data(project, pipeline, columns, data_range):
    url = f'{URL}/api/qc/data'
    print(f'URL: {url}', file=sys.stderr)
    headers = {'Content-type': 'application/json'}
    data =  json.dumps( dict(project=project, pipeline=pipeline, 
                             columns=columns, data_range=data_range) ) 
    return requests.get(url, data=data, headers=headers).json()


def gen_figure_config(filename='plot', format='svg', 
        height=None, width=None, scale=None, editable=True):
    config = {
        'toImageButtonOptions': {
            'format': format,
            'filename': filename
            },
        'height': height,
        'width': width,
        'scale': scale,
        'editable': editable
        }
    return config