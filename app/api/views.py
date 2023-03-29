from django.http.response import HttpResponse
import pandas as pd
import numpy as np
import logging

import dask.dataframe as dd

# from dask.distributed import Client, LocalCluster

from pathlib import Path as P

from rest_framework import generics
from rest_framework.views import APIView
from rest_framework.parsers import MultiPartParser, FormParser
from rest_framework.response import Response
from rest_framework import status

from django.http import JsonResponse
from django.conf import settings

timeout = 360

from maxquant.models import Pipeline, Result
from maxquant.serializers import PipelineSerializer, RawFileSerializer
from project.models import Project
from project.serializers import ProjectsNamesSerializer
from user.models import User

from tqdm import tqdm

VERBOSE = settings.DEBUG


class ProjectNames(generics.ListAPIView):
    filter_fields = ["name", "slug"]

    def post(self, request, format=None):
        queryset = Project.objects.all()
        serializer = ProjectsNamesSerializer(queryset, many=True)
        data = serializer.data
        return JsonResponse(data, status=201, safe=False)


class PipelineNames(generics.ListAPIView):
    def post(self, request, format=None):

        data = request.data
        project = data["project"]

        queryset = Pipeline.objects.filter(project__slug=project)
        serializer = PipelineSerializer(queryset, many=True)
        data = serializer.data
        return JsonResponse(data, status=201, safe=False)


class QcDataAPI(generics.ListAPIView):
    def post(self, request):

        data = request.data
        project_slug = data["project"]
        pipeline_slug = data["pipeline"]
        data_range = data["data_range"]

        df = get_qc_data(project_slug, pipeline_slug, data_range)

        response = {}

        if "columns" not in data:
            cols = df.columns
        else:
            cols = data["columns"]

        for col in cols:
            if col in df.columns:
                response[col] = list(df[col])
            else:
                response[col] = ""

        return JsonResponse(response)


class ProteinNamesAPI(generics.ListAPIView):
    def post(self, request):
        data = request.data

        logging.warning(f"ProteinNamesAPI: {data}")

        (
            project_slug,
            pipeline_slug,
            data_range,
            raw_files,
            remove_contaminants,
            remove_reversed_sequences,
        ) = (
            data["project"],
            data["pipeline"],
            data["data_range"],
            data["raw_files"],
            data["remove_contaminants"],
            data["remove_reversed_sequences"],
        )

        fns = get_protein_quant_fn(project_slug, pipeline_slug, data_range=data_range)

        if raw_files is not None:
            fns = [fn for fn in fns if P(fn).stem in raw_files]

        if len(fns) == 0:
            return JsonResponse({})

        cols = ["Majority protein IDs", "Fasta headers", "Score", "Intensity"]
        ddf = dd.read_parquet(fns, engine="pyarrow")[cols]
        if remove_contaminants:
            ddf = remove(ddf, "contaminants")
        if remove_reversed_sequences:
            ddf = remove(ddf, "reversed_sequences")
        dff = (
            ddf.groupby(["Majority protein IDs", "Fasta headers"])
            .mean()
            .sort_values("Score")
            .reset_index()
            .rename(columns={"Majority protein IDs": "protein_names"})
        )

        res = dff.compute()

        response = {}
        for col in res.columns:
            response[col] = res[col].to_list()

        return JsonResponse(response)


def remove(df, what="contaminants"):
    if what == "contaminants":
        pattern = "CON__"
    elif what == "reversed_sequences":
        pattern = "REV__"
    else:
        logging.error(f"No pattern defined for {what}")
    df_reduced = df[~df["Majority protein IDs"].str.contains(pattern)]
    return df_reduced


class ProteinGroupsAPI(generics.ListAPIView):
    def post(self, request):
        """Returns reporter corrected intensity columns for selected proteins"""

        data = request.data

        project_slug = data["project"]
        pipeline_slug = data["pipeline"]
        data_range = data["data_range"]
        raw_files = data["raw_files"]

        if "columns" in data:
            columns = data["columns"]
        else:
            columns = None

        if "protein_names" in data:
            protein_names = data["protein_names"]
        else:
            protein_names = None

        if columns is None or protein_names is None:
            return HttpResponse("alive")

        fns = get_protein_quant_fn(project_slug, pipeline_slug, data_range=data_range)
        if raw_files is not None:
            fns = [fn for fn in fns if P(fn).stem in raw_files]

        if "Reporter intensity corrected" in columns:
            df = pd.read_parquet(fns[0])
            intensity_columns = df.filter(
                regex="Reporter intensity corrected"
            ).columns.to_list()
            columns.remove("Reporter intensity corrected")
            columns = columns + intensity_columns

        df = get_protein_groups_data(fns, columns=columns, protein_names=protein_names)

        return JsonResponse(df.to_json(), safe=False)


class RawFileUploadAPI(APIView):
    parser_classes = (MultiPartParser, FormParser)

    def post(self, request, *args, **kwargs):

        pipeline = get_pipeline(request)
        user = get_user(request)
        orig_file = request.data["orig_file"]

        file_serializer = RawFileSerializer(
            data={
                "orig_file": orig_file,
                "pipeline": pipeline.pk,
                "created_by": user.pk,
            }
        )

        if file_serializer.is_valid():
            file_serializer.save()
            return Response(file_serializer.data, status=status.HTTP_201_CREATED)
        else:
            return Response(file_serializer.errors, status=status.HTTP_400_BAD_REQUEST)


def get_user(request):
    uuid = request.data["uid"]
    return get_instance_from_uuid(User, uuid)


def get_pipeline(request):
    uuid = request.data["pid"]
    return get_instance_from_uuid(Pipeline, uuid)


def get_instance_from_uuid(model, uuid):
    return model.objects.get(uuid=uuid)


def get_protein_quant_fn(
    project_slug,
    pipeline_slug,
    data_range,
    only_use_downstream=False,
    raw_files=None,
):
    pipeline = Pipeline.objects.get(project__slug=project_slug, slug=pipeline_slug)
    results = Result.objects.filter(raw_file__pipeline=pipeline)

    if only_use_downstream:
        results = results.filter(raw_file__use_downstream=True)

    if data_range is not None:
        n_results = len(results)
        if data_range is None:
            data_range = len(results) + 1

        if (n_results > data_range) and (n_results > 0):
            results = results.order_by("raw_file__created")[n_results - data_range :]

    fns = []
    for res in tqdm(results):
        fn = res.create_protein_quant()
        if fn is None:
            continue
        fns.append(fn)

    return fns


def get_protein_groups_data(
    fns,
    columns,
    protein_names,
    protein_col="Majority protein IDs",
):
    ddf = dd.read_parquet(fns, engine="pyarrow")
    ddf = ddf[ddf[protein_col].isin(protein_names)]
    ddf = ddf[["RawFile", protein_col] + columns]
    df = ddf.compute().reset_index(drop=True)
    df["RawFile"] = df["RawFile"].apply(lambda x: P(x).stem)
    return df


def get_qc_data(project_slug, pipeline_slug, data_range=None):
    pipeline = Pipeline.objects.get(slug=pipeline_slug)
    results = Result.objects.filter(raw_file__pipeline=pipeline)
    n_results = len(results)

    if isinstance(data_range, int) and (n_results > data_range) and (n_results > 0):
        results = results.order_by("raw_file__created")[len(results) - data_range :]

    mqs = []
    rts = []

    flagged = pd.DataFrame()
    use_downstream = pd.DataFrame()
    for result in tqdm(results):
        raw_fn = P(result.raw_file.name).with_suffix("").name
        raw_is_flagged = result.raw_file.flagged
        raw_use_downstream = result.raw_file.use_downstream
        flagged.loc[raw_fn, "Flagged"] = raw_is_flagged
        use_downstream.loc[raw_fn, "Use Downstream"] = raw_use_downstream
        try:
            rts.append(result.rawtools_qc_data())
        except Exception as e:
            logging.warning(f"{e}: {result.raw_file.name} rawtools_qc_data")
        try:
            mqs.append(result.maxquant_qc_data())
        except Exception as e:
            logging.warning(f"{e}: {result.raw_file.name} maxquant_qc_data")

    rt = pd.concat(rts)
    mq = pd.concat(mqs)

    del rts, mqs

    try:
        rt["Index"] = rt["DateAcquired"].rank()
    except KeyError as e:
        logging.error(f"{e}: {rt}")

    if (rt is None) and (mq is not None):
        return mq
    elif (rt is not None) and (mq is None):
        return rt
    elif (rt is None) and (mq is None):
        return None

    if "Index" in mq.columns:
        mq = mq.drop("Index", axis=1)

    df = pd.merge(rt, mq, on="RawFile", how="outer").sort_values(
        "Index", ascending=True
    )

    df = pd.merge(df, flagged, left_on="RawFile", right_index=True)
    df = pd.merge(df, use_downstream, left_on="RawFile", right_index=True)

    df["DateAcquired"] = df["DateAcquired"].view(np.int64)

    assert df.columns.value_counts().max() == 1, df.columns.value_counts()

    return df


class CreateFlag(generics.ListAPIView):
    def post(self, request):
        """Add flags to raw files."""

        data = request.data

        user = get_user(request)

        project_slug = data["project"]
        pipeline_slug = data["pipeline"]
        raw_files = request.POST.getlist("raw_files")

        project = Project.objects.get(slug=project_slug)
        if not user in project.users.all():
            logging.warning(
                f"User {user.email} does not belong to project {project.name}"
            )
            return JsonResponse({})

        pipeline = Pipeline.objects.get(project__slug=project_slug, slug=pipeline_slug)
        results = Result.objects.filter(raw_file__pipeline=pipeline)
        for result in results:
            if result.raw_file.name in raw_files:
                logging.warning(f"Flag {result.raw_file.name} in {pipeline.name}")
                result.raw_file.flagged = True
                result.raw_file.save()

        return JsonResponse({})


class DeleteFlag(generics.ListAPIView):
    def post(self, request):
        """Remove flags from raw files."""
        data = request.data

        user = get_user(request)

        project_slug = data["project"]
        pipeline_slug = data["pipeline"]
        raw_files = request.POST.getlist("raw_files")

        project = Project.objects.get(slug=project_slug)
        if not user in project.users.all():
            logging.warning(
                f"User {user.email} does not belong to project {project.name}"
            )
            return JsonResponse({})

        pipeline = Pipeline.objects.get(project__slug=project_slug, slug=pipeline_slug)
        results = Result.objects.filter(raw_file__pipeline=pipeline)
        for result in results:
            if result.raw_file.name in raw_files:
                logging.warning(f"Un-flag {result.raw_file.name} in {pipeline.name}")
                result.raw_file.flagged = False
                result.raw_file.save()

        return JsonResponse({})


class RawFile(generics.ListAPIView):
    def post(self, request):
        """Add flags to raw files."""

        data = request.data

        user = get_user(request)

        project_slug = data["project"]
        pipeline_slug = data["pipeline"]
        action = data["action"]

        project = Project.objects.get(slug=project_slug)
        if not user in project.users.all():
            logging.warning(
                f"User {user.email} does not belong to project {project.name}"
            )
            return JsonResponse({"status": "Missing permissions"})

        raw_files = request.POST.getlist("raw_files")

        pipeline = Pipeline.objects.get(project__slug=project_slug, slug=pipeline_slug)

        results = Result.objects.filter(raw_file__pipeline=pipeline)
        for result in results:
            if result.raw_file.name in raw_files:
                logging.warning(f"{result.raw_file.name}: {action}")
                if action == "flag":
                    result.raw_file.flagged = True
                elif action == "unflag":
                    result.raw_file.flagged = False
                elif action == "accept":
                    result.raw_file.use_downstream = True
                elif action == "reject":
                    result.raw_file.use_downstream = False
                result.raw_file.save()

        return JsonResponse({"status": "success"})
