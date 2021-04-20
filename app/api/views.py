import pandas as pd
import numpy as np

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
from maxquant.serializers import MaxQuantPipelineSerializer
from project.models import Project
from project.serializers import ProjectsNamesSerializer


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

    for result in results:
        rts.append( result.rawtools_qc_data() )
        mqs.append( result.maxquant_qc_data() )

    rt = pd.concat(rts)
    mq = pd.concat(mqs)

    del rts, mqs

    if rt is not None: print('RawFile' in rt.columns)
    if mq is not None: print('RawFile' in mq.columns)

    rt['Index'] = rt['DateAcquired'].rank()

    print(rt)
    print(mq)

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
            
    df['DateAcquired'] = df['DateAcquired'].astype( np.int64 )
    assert df.columns.value_counts().max()==1, df.columns.value_counts()
    return df