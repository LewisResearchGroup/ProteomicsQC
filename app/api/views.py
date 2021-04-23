import pandas as pd
import numpy as np
import dask.dataframe as dd

from django.shortcuts import render

from rest_framework import generics
from rest_framework.views import APIView
from rest_framework.parsers import MultiPartParser, FormParser
from rest_framework.response import Response
from rest_framework import status
from cache_memoize import cache_memoize

from django.http import JsonResponse

timeout = 360

from maxquant.models import MaxQuantPipeline, MaxQuantResult
from maxquant.serializers import MaxQuantPipelineSerializer, RawFileSerializer
from project.models import Project
from project.serializers import ProjectsNamesSerializer

from tqdm import tqdm

class ProjectNames(generics.ListAPIView):
    filter_fields = ['name', 'slug']
    def get(self, request, format=None):
            queryset = Project.objects.all()
            serializer = ProjectsNamesSerializer(queryset, many=True)
            data = serializer.data
            return JsonResponse(data, status=201, safe=False)


class MaxQuantPipelineNames(generics.ListAPIView):
    def get(self, request, format=None):
            get_data = request.query_params
            project = get_data['project']
            queryset = MaxQuantPipeline.objects.filter(project__slug=project)
            serializer = MaxQuantPipelineSerializer(queryset, many=True)
            data = serializer.data
            return JsonResponse(data, status=201, safe=False)


class QcDataAPI(generics.ListAPIView):
    def get(self, request):
        print('QcDataAPI()')
        data = request.data
        project_slug = data['project']
        pipeline_slug = data['pipeline']
        df = get_qc_data(project_slug, pipeline_slug)
        response = {}
        for col in data['columns']:
            if col in df.columns:
                response[col] = list(df[col])
            else:
                response[col] = ''
        return JsonResponse(response)


def get_qc_data(project_slug, pipeline_slug):

    pipeline = MaxQuantPipeline.objects.get( slug=pipeline_slug )
    path = pipeline.path

    results = MaxQuantResult.objects.filter( raw_file__pipeline = pipeline)

    mqs = []
    rts = []

    for result in tqdm(results):
        rts.append( result.rawtools_qc_data() )
        mqs.append( result.maxquant_qc_data() )

    rt = pd.concat(rts)
    mq = pd.concat(mqs)

    del rts, mqs

    if rt is not None: print('RawFile' in rt.columns)
    if mq is not None: print('RawFile' in mq.columns)

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
            
    df['DateAcquired'] = df['DateAcquired'].astype( np.int64, errors='ignore' )

    assert df.columns.value_counts().max()==1, df.columns.value_counts()
    return df



class ProteinNamesAPI(generics.ListAPIView):
    def post(self, request):
        data = request.data
        project_slug = data['project']
        pipeline_slug = data['pipeline']
        fns = get_protein_quant_fn(project_slug, pipeline_slug)
        if len(fns) == 0: return JsonResponse({})
        cols = ['Majority protein IDs', 'Score', 'Intensity']
        ddf = dd.read_parquet(fns, engine="pyarrow")[cols]
        res = ddf.groupby(['Majority protein IDs']).mean().sort_values('Score').compute()
        response = {}
        response['protein_names'] = list( res.index  )
        for col in res.columns:
            response[col] = res[col].to_list()
        return JsonResponse(response)



class ProteinGroupsAPI(generics.ListAPIView):
    def get(self, request):
        """Returns reporter corrected intensity columns for selected proteins"""
        data = request.data

        if 'columns' in data:
            columns = data['columns']

        project_slug = data['project']
        pipeline_slug = data['pipeline']
        protein_names = data['protein_names']

        if columns is None or protein_names is None:
            return JsonResponse({})

        fns = get_protein_quant_fn(project_slug, pipeline_slug)

        if 'Reporter intensity corrected' in columns:
            df = pd.read_parquet(fns[0])
            intensity_columns = df.filter(regex='Reporter intensity corrected').columns.to_list()
            columns.remove('Reporter intensity corrected')
            columns = columns + intensity_columns

        df = get_protein_groups_data(fns, 
                columns=columns, 
                protein_names=protein_names)
        
        print(pd.value_counts(df.columns))
        return JsonResponse(df.to_json(), safe=False)



def get_protein_quant_fn(project_slug, pipeline_slug):
    pipeline = MaxQuantPipeline.objects.get( project__slug=project_slug, slug=pipeline_slug )
    results = MaxQuantResult.objects.filter( raw_file__pipeline = pipeline, 
                                             raw_file__use_downstream=True)
    fns = []
    for res in tqdm( results ) :
        fn = res.create_protein_quant()
        if fn is None: continue
        fns.append( fn )
    return fns


def get_protein_groups_data(fns, columns, protein_names, protein_col='Majority protein IDs'):
    print('Get protein groups')
    ddf = dd.read_parquet(fns, engine="pyarrow")
    ddf = ddf[ddf[protein_col].isin(protein_names)]
    ddf = ddf[['RawFile', protein_col]+columns]
    return ddf.compute().reset_index(drop=True)


class RawFileUploadAPI(APIView):
  parser_classes = (MultiPartParser, FormParser)
  def post(self, request, *args, **kwargs):
    file_serializer = RawFileSerializer(data=request.data)
    if file_serializer.is_valid():
      file_serializer.save()
      return Response(file_serializer.data, status=status.HTTP_201_CREATED)
    else:
      return Response(file_serializer.errors, status=status.HTTP_400_BAD_REQUEST)
