from django.http.response import HttpResponse
import pandas as pd
import numpy as np
import logging
import json 

### Dask setup
import dask.dataframe as dd
from dask.distributed import Client, LocalCluster

#cluster = LocalCluster(n_workers=4, threads_per_worker=2)
#client = Client()

#print(cluster)

from pathlib import Path as P

from django.shortcuts import render

from rest_framework import generics
from rest_framework.views import APIView
from rest_framework.parsers import MultiPartParser, FormParser
from rest_framework.response import Response
from rest_framework import status
from cache_memoize import cache_memoize

from django.http import JsonResponse
from django.conf import settings
timeout = 360

from maxquant.models import MaxQuantPipeline, MaxQuantResult
from maxquant.serializers import MaxQuantPipelineSerializer, RawFileSerializer
from project.models import Project
from project.serializers import ProjectsNamesSerializer
from user.models import User

from tqdm import tqdm

VERBOSE = settings.DEBUG

class ProjectNames(generics.ListAPIView):
    filter_fields = ['name', 'slug']
    def post(self, request, format=None):
            queryset = Project.objects.all()
            serializer = ProjectsNamesSerializer(queryset, many=True)
            data = serializer.data
            return JsonResponse(data, status=201, safe=False)


class MaxQuantPipelineNames(generics.ListAPIView):
    def post(self, request, format=None):

            data = request.data
            project = data['project']

            queryset = MaxQuantPipeline.objects.filter(project__slug=project)
            serializer = MaxQuantPipelineSerializer(queryset, many=True)
            data = serializer.data
            return JsonResponse(data, status=201, safe=False)


class QcDataAPI(generics.ListAPIView):
    def post(self, request):

        data = request.data
        project_slug = data['project']
        pipeline_slug = data['pipeline']
        data_range = data['data_range']

        df = get_qc_data(project_slug, pipeline_slug, data_range)

        response = {}

        if 'columns' not in data:
            cols = df.columns
        else:
            cols = data['columns']

        for col in cols:
            if col in df.columns:
                response[col] = list(df[col])
            else:
                response[col] = ''
    
        return JsonResponse(response)



class ProteinNamesAPI(generics.ListAPIView):
    def post(self, request):
        data = request.data
        
        project_slug = data['project']
        pipeline_slug = data['pipeline']
        data_range = data['data_range']

        add_con = data['add_con']
        add_rev = data['add_rev']

        print(project_slug, pipeline_slug, add_con, add_rev, data_range)

        fns = get_protein_quant_fn(project_slug, pipeline_slug, data_range=data_range)

        if len(fns) == 0: return JsonResponse({})
        cols = ['Majority protein IDs', 'Score', 'Intensity']
        ddf = dd.read_parquet(fns, engine="pyarrow")[cols]
        if not add_con: ddf = ddf[~ddf['Majority protein IDs'].str.contains('CON__')]
        if not add_rev: ddf = ddf[~ddf['Majority protein IDs'].str.contains('REV__')]
        dff = ddf.groupby(['Majority protein IDs']).mean().sort_values('Score')
        res = dff.compute()
        response = {}
        response['protein_names'] = list( res.index  )
        for col in res.columns:
            response[col] = res[col].to_list()
        return JsonResponse(response)



class ProteinGroupsAPI(generics.ListAPIView):
    def post(self, request):
        """Returns reporter corrected intensity columns for selected proteins"""
        
        data = request.data

        project_slug = data['project']
        pipeline_slug = data['pipeline']
        data_range = data['data_range']

        if 'columns' in data:
            columns = data['columns']
        else:
            columns = None

        if 'protein_names' in data:
            protein_names = data['protein_names']
        else:
            protein_names = None

        if columns is None or protein_names is None:
            return HttpResponse('alive')

        fns = get_protein_quant_fn(project_slug, pipeline_slug, data_range=data_range)

        if 'Reporter intensity corrected' in columns:
            df = pd.read_parquet(fns[0])
            intensity_columns = df.filter(regex='Reporter intensity corrected').columns.to_list()
            columns.remove('Reporter intensity corrected')
            columns = columns + intensity_columns

        df = get_protein_groups_data(fns, 
                columns=columns, 
                protein_names=protein_names)
        
        return JsonResponse(df.to_json(), safe=False)


class RawFileUploadAPI(APIView):
  parser_classes = (MultiPartParser, FormParser)
  def post(self, request, *args, **kwargs):

    pipeline = get_pipeline(request)
    user = get_user(request)
    orig_file = request.data['orig_file']
    
    file_serializer = RawFileSerializer(data={'orig_file': orig_file, 'pipeline': pipeline.pk, 'created_by': user.pk})

    if file_serializer.is_valid():
      file_serializer.save()
      return Response(file_serializer.data, status=status.HTTP_201_CREATED)
    else:
      return Response(file_serializer.errors, status=status.HTTP_400_BAD_REQUEST)


def get_user(request):
    uuid = request.data['user']
    return get_instance_from_uuid(User, uuid)
    

def get_pipeline(request):
    uuid = request.data['pipeline']
    return get_instance_from_uuid(MaxQuantPipeline, uuid)
        

def get_instance_from_uuid(model, uuid):
    return model.objects.get(uuid=uuid)


def get_protein_quant_fn(project_slug, pipeline_slug, data_range):
    pipeline = MaxQuantPipeline.objects.get( project__slug=project_slug, slug=pipeline_slug )
    results = MaxQuantResult.objects.filter( raw_file__pipeline = pipeline, 
                                             raw_file__use_downstream=True)
    if data_range is not None:
        results = results.order_by('raw_file__created')[len(results)-data_range:]

    fns = []
    for res in tqdm( results ) :
        fn = res.create_protein_quant()
        if fn is None: continue
        fns.append( fn )

    print(fn)

    return fns


def get_protein_groups_data(fns, columns, protein_names, protein_col='Majority protein IDs'):
    ddf = dd.read_parquet(fns, engine="pyarrow")
    ddf = ddf[ddf[protein_col].isin(protein_names)] 
    ddf = ddf[['RawFile', protein_col]+columns]
    return ddf.compute().reset_index(drop=True)


def get_qc_data(project_slug, pipeline_slug, data_range=None):

    pipeline = MaxQuantPipeline.objects.get( slug=pipeline_slug )

    path = pipeline.path

    results = MaxQuantResult.objects.filter( raw_file__pipeline = pipeline )

    if data_range is not None:
        results = results.order_by('raw_file__created')[len(results)-data_range:]

    mqs = []
    rts = []

    flagged = pd.DataFrame()
    use_downstream = pd.DataFrame()
    for result in tqdm(results):
        raw_fn = P(result.raw_file.name).with_suffix('').name
        raw_is_flagged = result.raw_file.flagged
        raw_use_downstream = result.raw_file.use_downstream     
        flagged.loc[raw_fn, 'Flagged'] = raw_is_flagged
        use_downstream.loc[raw_fn, 'Use Downstream'] = raw_use_downstream
        try:
            rts.append( result.rawtools_qc_data() )
        except Exception as e:
            logging.warning(e)
        try:
            mqs.append( result.maxquant_qc_data() )
        except Exception as e:
            logging.warning(e)

    rt = pd.concat(rts)
    mq = pd.concat(mqs)

    del rts, mqs

    rt['Index'] = rt['DateAcquired'].rank()

    if (rt is None) and (mq is not None):
        return mq
    elif (rt is not None) and (mq is None):
        return rt
    elif (rt is None) and (mq is None):
        return None

    if 'Index' in mq.columns:
        mq = mq.drop('Index', axis=1)

    df = pd.merge(rt, mq, on='RawFile', how='outer')\
            .sort_values('Index', ascending=True)

    df = pd.merge(df, flagged, left_on='RawFile', right_index=True)
    df = pd.merge(df, use_downstream, left_on='RawFile', right_index=True)

    df['DateAcquired'] = df['DateAcquired'].astype( np.int64, errors='ignore' )

    assert df.columns.value_counts().max()==1, df.columns.value_counts()
    return df

