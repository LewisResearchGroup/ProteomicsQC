from django.http.response import HttpResponse
import json
import pandas as pd
import numpy as np
import logging
import re

import dask.dataframe as dd

# from dask.distributed import Client, LocalCluster

from pathlib import Path as P

from rest_framework import generics
from rest_framework.views import APIView
from rest_framework.parsers import MultiPartParser, FormParser
from rest_framework.response import Response
from rest_framework import status
from rest_framework.permissions import IsAuthenticated

from django.http import JsonResponse
from django.conf import settings
from django.http import HttpResponseForbidden
from django.db import models
from django.core.exceptions import PermissionDenied

timeout = 360

from maxquant.models import Pipeline, Result, RawFile as RawFileModel
from maxquant.serializers import PipelineSerializer, RawFileSerializer
from project.models import Project
from project.serializers import ProjectsNamesSerializer
from user.models import User


VERBOSE = settings.DEBUG


def _dataframe_json_payload(df):
    return json.loads(df.to_json())


def _is_admin(user):
    return bool(user and (user.is_staff or user.is_superuser))


def _get_request_user(request):
    if getattr(request, "user", None) and request.user.is_authenticated:
        return request.user
    return None


def _projects_for_user(user):
    queryset = Project.objects.all()
    if _is_admin(user):
        return queryset
    return queryset.filter(
        models.Q(created_by_id=user.id) | models.Q(users=user)
    ).distinct()


def _pipelines_for_user(user):
    queryset = Pipeline.objects.select_related("project")
    if _is_admin(user):
        return queryset
    return queryset.filter(
        models.Q(project__created_by_id=user.id) | models.Q(project__users=user)
    ).distinct()


def _results_for_user(user):
    queryset = Result.objects.select_related(
        "raw_file__pipeline__project",
        "raw_file__created_by",
    )
    if _is_admin(user):
        return queryset
    return queryset.filter(raw_file__created_by_id=user.id).distinct()


def _results_for_pipeline_mutation(user, pipeline):
    queryset = Result.objects.select_related(
        "raw_file__pipeline__project",
        "raw_file__created_by",
    ).filter(raw_file__pipeline=pipeline)
    if _is_admin(user):
        return queryset.distinct()
    return queryset.filter(raw_file__created_by_id=user.id).distinct()


class ProjectNames(generics.ListAPIView):
    filter_fields = ["name", "slug"]
    permission_classes = [IsAuthenticated]

    def post(self, request, format=None):
        user = _get_request_user(request)
        if user is None:
            return HttpResponseForbidden("Missing user context.")
        queryset = _projects_for_user(user)
        serializer = ProjectsNamesSerializer(queryset, many=True)
        data = serializer.data
        return JsonResponse(data, status=200, safe=False)


class PipelineNames(generics.ListAPIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, format=None):
        user = _get_request_user(request)
        if user is None:
            return HttpResponseForbidden("Missing user context.")
        data = request.data
        project = data["project"]

        queryset = _pipelines_for_user(user).filter(project__slug=project)
        serializer = PipelineSerializer(queryset, many=True)
        data = serializer.data
        return JsonResponse(data, status=200, safe=False)


class PipelineUploaders(generics.ListAPIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, format=None):
        user = _get_request_user(request)
        if user is None:
            return HttpResponseForbidden("Missing user context.")

        project_slug = request.data.get("project")
        pipeline_slug = request.data.get("pipeline")
        if not project_slug or not pipeline_slug:
            return JsonResponse([], safe=False, status=200)

        pipeline = _pipelines_for_user(user).filter(
            project__slug=project_slug,
            slug=pipeline_slug,
        ).first()
        if pipeline is None:
            return JsonResponse([], safe=False, status=200)

        queryset = RawFileModel.objects.filter(pipeline=pipeline).select_related("created_by")
        if not _is_admin(user):
            queryset = queryset.filter(created_by_id=user.id)

        rows = (
            queryset
            .values("created_by__email")
            .distinct()
            .order_by("created_by__email")
        )
        output = []
        for row in rows:
            email = (row.get("created_by__email") or "").strip()
            if not email:
                continue
            output.append({"label": email, "value": email})
        return JsonResponse(output, safe=False, status=200)


class QcDataAPI(generics.ListAPIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        user = _get_request_user(request)
        if user is None:
            return HttpResponseForbidden("Missing user context.")

        data = request.data
        project_slug = data["project"]
        pipeline_slug = data["pipeline"]
        data_range = data["data_range"]

        try:
            df = get_qc_data(project_slug, pipeline_slug, data_range, user=user)
        except PermissionDenied:
            return HttpResponseForbidden("Missing permissions for requested pipeline.")
        if df is None:
            df = pd.DataFrame()

        # Ensure JSON-serializable values
        df = df.replace({np.nan: None})

        response = {}

        if ("columns" not in data) or (not data.get("columns")):
            cols = df.columns
        else:
            cols = data["columns"]

        n_rows = len(df.index)
        for col in cols:
            if col in df.columns:
                response[col] = df[col].tolist()
            else:
                response[col] = [None] * n_rows

        return JsonResponse(response)


class ProteinNamesAPI(generics.ListAPIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        user = _get_request_user(request)
        if user is None:
            return HttpResponseForbidden("Missing user context.")
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

        fns = get_protein_quant_fn(
            project_slug, pipeline_slug, data_range=data_range, user=user
        )

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
    permission_classes = [IsAuthenticated]

    def post(self, request):
        """Returns reporter corrected intensity columns for selected proteins"""
        user = _get_request_user(request)
        if user is None:
            return HttpResponseForbidden("Missing user context.")

        data = request.data

        project_slug = data["project"]
        pipeline_slug = data["pipeline"]
        data_range = data["data_range"]
        raw_files = data.get("raw_files")

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

        fns = get_protein_quant_fn(
            project_slug, pipeline_slug, data_range=data_range, user=user
        )
        if len(fns) == 0:
            return JsonResponse(_dataframe_json_payload(pd.DataFrame()))
        if raw_files is not None:
            fns = [fn for fn in fns if P(fn).stem in raw_files]
            if len(fns) == 0:
                return JsonResponse(_dataframe_json_payload(pd.DataFrame()))

        if "Reporter intensity corrected" in columns:
            df = pd.read_parquet(fns[0])
            intensity_columns = df.filter(
                regex="Reporter intensity corrected"
            ).columns.to_list()
            columns.remove("Reporter intensity corrected")
            columns = columns + intensity_columns

        df = get_protein_groups_data(fns, columns=columns, protein_names=protein_names)

        return JsonResponse(_dataframe_json_payload(df))


class RawFileUploadAPI(APIView):
    parser_classes = (MultiPartParser, FormParser)
    permission_classes = [IsAuthenticated]

    def post(self, request, *args, **kwargs):

        pipeline = get_pipeline(request)
        user = request.user
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


def get_pipeline(request):
    uuid = request.data["pid"]
    return get_instance_from_uuid(Pipeline, uuid)


def get_instance_from_uuid(model, uuid):
    return model.objects.get(uuid=uuid)


def get_protein_quant_fn(
    project_slug,
    pipeline_slug,
    data_range,
    user,
    only_use_downstream=False,
    raw_files=None,
):
    def _normalize_raw_name(value):
        if value is None:
            return None
        text = str(value).strip()
        if not text:
            return None
        lowered = text.lower()
        if lowered in {"none", "nan"}:
            return None
        return P(text).stem.lower()

    pipeline = _pipelines_for_user(user).filter(
        project__slug=project_slug, slug=pipeline_slug
    ).first()
    if pipeline is None:
        return []
    results = _results_for_user(user).filter(raw_file__pipeline=pipeline)

    if raw_files is not None:
        requested_raws = {
            normalized
            for normalized in (_normalize_raw_name(raw) for raw in raw_files)
            if normalized
        }
        if requested_raws:
            results = [
                res
                for res in results
                if _normalize_raw_name(res.raw_file.logical_name) in requested_raws
            ]
        else:
            results = []

    if only_use_downstream:
        if isinstance(results, list):
            results = [res for res in results if res.raw_file.use_downstream]
        else:
            results = results.filter(raw_file__use_downstream=True)

    if data_range is not None:
        n_results = len(results)

        if (n_results > data_range) and (n_results > 0):
            if isinstance(results, list):
                results = sorted(results, key=lambda res: res.raw_file.created)[
                    n_results - data_range :
                ]
            else:
                results = results.order_by("raw_file__created")[n_results - data_range :]

    fns = []
    for res in results:
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
    def _normalize_display_rawfile(value):
        if value is None:
            return None
        stem = P(str(value)).stem
        return re.sub(r"^[0-9a-f]{32}_", "", stem, flags=re.IGNORECASE)

    ddf = dd.read_parquet(fns, engine="pyarrow")
    ddf = ddf[ddf[protein_col].isin(protein_names)]
    ddf = ddf[["RawFile", protein_col] + columns]
    df = ddf.compute().reset_index(drop=True)
    df["RawFile"] = df["RawFile"].apply(_normalize_display_rawfile)
    return df

def get_qc_data(project_slug, pipeline_slug, data_range=None, user=None):
    def _extract_tmt_peptide_counts(result_obj):
        """Count detected peptides per TMT channel from evidence.txt for a run."""
        fn = result_obj.output_dir_maxquant / "evidence.txt"
        if not fn.is_file():
            return {}
        try:
            header = pd.read_csv(fn, sep="\t", nrows=0)
        except Exception:
            return {}

        available = list(header.columns)
        reporter_cols = [
            c for c in available
            if isinstance(c, str) and c.startswith("Reporter intensity corrected ")
        ]
        if len(reporter_cols) == 0:
            return {}

        usecols = list(reporter_cols)
        has_sequence = "Sequence" in available
        if has_sequence:
            usecols.append("Sequence")
        try:
            evidence = pd.read_csv(fn, sep="\t", usecols=usecols, low_memory=False)
        except Exception:
            return {}
        if evidence.empty:
            return {}

        channel_to_cols = {}
        for col in reporter_cols:
            match = re.search(r"\b(\d+)\b", str(col))
            if match is None:
                continue
            channel_no = int(match.group(1))
            channel_to_cols.setdefault(channel_no, []).append(col)

        out = {}
        for channel_no in sorted(channel_to_cols):
            cols = channel_to_cols[channel_no]
            channel_values = evidence[cols].apply(pd.to_numeric, errors="coerce")
            # Prefer max across duplicate channel columns (e.g. experiment suffixes).
            detected = channel_values.max(axis=1, skipna=True).fillna(0) > 0
            if has_sequence:
                seq = evidence.loc[detected, "Sequence"].dropna().astype(str).str.strip()
                seq = seq[seq != ""]
                count = int(seq.nunique())
            else:
                count = int(detected.sum())
            out[f"TMT{channel_no}_peptide_count"] = count

        return out

    def _extract_tmt_protein_group_counts(result_obj):
        """Count detected protein groups per TMT channel from proteinGroups.txt for a run."""
        fn = result_obj.output_dir_maxquant / "proteinGroups.txt"
        if not fn.is_file():
            return {}
        try:
            header = pd.read_csv(fn, sep="\t", nrows=0)
        except Exception:
            return {}

        available = list(header.columns)
        reporter_cols = [
            c for c in available
            if isinstance(c, str) and c.startswith("Reporter intensity corrected ")
        ]
        if len(reporter_cols) == 0:
            return {}

        id_col = None
        for candidate in ["Majority protein IDs", "Protein IDs"]:
            if candidate in available:
                id_col = candidate
                break

        usecols = list(reporter_cols)
        if id_col is not None:
            usecols.append(id_col)
        try:
            proteins = pd.read_csv(fn, sep="\t", usecols=usecols, low_memory=False)
        except Exception:
            return {}
        if proteins.empty:
            return {}

        channel_to_cols = {}
        for col in reporter_cols:
            match = re.search(r"\b(\d+)\b", str(col))
            if match is None:
                continue
            channel_no = int(match.group(1))
            channel_to_cols.setdefault(channel_no, []).append(col)

        out = {}
        for channel_no in sorted(channel_to_cols):
            cols = channel_to_cols[channel_no]
            channel_values = proteins[cols].apply(pd.to_numeric, errors="coerce")
            detected = channel_values.max(axis=1, skipna=True).fillna(0) > 0
            if id_col is not None:
                ids = proteins.loc[detected, id_col].dropna().astype(str).str.strip()
                ids = ids[ids != ""]
                count = int(ids.nunique())
            else:
                count = int(detected.sum())
            out[f"TMT{channel_no}_protein_group_count"] = count

        return out

    def _normalize_index_column(frame):
        if frame is None or frame.empty:
            return frame
        if "Index" in frame.columns:
            frame = frame.sort_values("Index", na_position="last").reset_index(drop=True)
            frame["Index"] = np.arange(1, len(frame) + 1, dtype=int)
        return frame

    def _normalize_rawfile_name(value):
        if value is None:
            return None
        text = str(value).strip()
        if not text:
            return None
        lowered = text.lower()
        if lowered in {"none", "nan"}:
            return None
        return P(text).stem.lower()

    pipeline = _pipelines_for_user(user).filter(
        project__slug=project_slug, slug=pipeline_slug
    ).first()
    if pipeline is None:
        raise PermissionDenied("Missing permissions for requested pipeline.")
    results = _results_for_user(user).filter(raw_file__pipeline=pipeline)
    n_results = len(results)

    if isinstance(data_range, int) and (n_results > data_range) and (n_results > 0):
        results = results.order_by("raw_file__created")[len(results) - data_range :]

    mqs = []
    rts = []

    metadata_rows = []
    tmt_peptide_rows = []
    for result in results:
        raw_fn = P(result.raw_file.logical_name).with_suffix("").name
        raw_is_flagged = result.raw_file.flagged
        raw_use_downstream = result.raw_file.use_downstream
        raw_file_id = result.raw_file_id
        raw_uploader = (
            getattr(getattr(result.raw_file, "created_by", None), "email", None)
            or f"user-{result.raw_file.created_by_id}"
        )
        metadata_rows.append(
            {
                "RunKey": f"rf{raw_file_id}",
                "RawFile": raw_fn,
                "Flagged": raw_is_flagged,
                "Use Downstream": raw_use_downstream,
                "Uploader": raw_uploader,
            }
        )
        tmt_peptide_rows.append(
            {
                "RunKey": f"rf{raw_file_id}",
                **_extract_tmt_peptide_counts(result),
                **_extract_tmt_protein_group_counts(result),
            }
        )
        try:
            rt_df = result.rawtools_qc_data()
            if rt_df is not None and not rt_df.empty:
                rt_df = rt_df.copy()
                rt_df["RunKey"] = f"rf{raw_file_id}"
                rts.append(rt_df)
        except Exception as e:
            logging.warning(f"{e}: {result.raw_file.name} rawtools_qc_data")
        try:
            mq_df = result.maxquant_qc_data()
            if mq_df is not None and not mq_df.empty:
                mq_df = mq_df.copy()
                mq_df["RunKey"] = f"rf{raw_file_id}"
                mqs.append(mq_df)
        except Exception as e:
            logging.warning(f"{e}: {result.raw_file.name} maxquant_qc_data")

    rt = pd.concat(rts) if len(rts) > 0 else None
    mq = pd.concat(mqs) if len(mqs) > 0 else None

    del rts, mqs

    if rt is not None:
        try:
            rt["Index"] = rt["DateAcquired"].rank()
        except KeyError as e:
            logging.error(f"{e}: {rt}")

    metadata = pd.DataFrame(metadata_rows)
    tmt_peptide_df = pd.DataFrame(tmt_peptide_rows)

    if (rt is None) and (mq is not None):
        df = mq
    elif (rt is not None) and (mq is None):
        df = rt
    elif (rt is None) and (mq is None):
        return None
    else:
        if "Index" in mq.columns:
            mq = mq.drop("Index", axis=1)
        merge_keys = ["RunKey"]
        if "RawFile" in rt.columns and "RawFile" in mq.columns:
            merge_keys.append("RawFile")
        df = pd.merge(rt, mq, on=merge_keys, how="outer")

    # Fallback: if RunKey was dropped upstream but shape matches one-row-per-run,
    # restore it from metadata so uploader enrichment remains possible.
    if (
        "RunKey" not in df.columns
        and metadata is not None
        and not metadata.empty
        and len(df.index) == len(metadata.index)
    ):
        df = df.reset_index(drop=True)
        df["RunKey"] = metadata["RunKey"].to_list()

    if (
        metadata is not None
        and not metadata.empty
        and "RunKey" in df.columns
    ):
        # Join on the unique run key to avoid dropping uploader info when
        # RawFile labels differ slightly between upstream sources.
        df = pd.merge(
            df,
            metadata,
            on=["RunKey"],
            how="left",
            suffixes=("", "_meta"),
        )
        if "RawFile" not in df.columns and "RawFile_meta" in df.columns:
            df["RawFile"] = df["RawFile_meta"]
        elif "RawFile_meta" in df.columns:
            df["RawFile"] = df["RawFile_meta"].where(
                df["RawFile_meta"].notna() & (df["RawFile_meta"].astype(str).str.strip() != ""),
                df["RawFile"],
            )
        if "RawFile_meta" in df.columns:
            df = df.drop(columns=["RawFile_meta"])

    if (
        tmt_peptide_df is not None
        and not tmt_peptide_df.empty
        and "RunKey" in df.columns
    ):
        df = pd.merge(
            df,
            tmt_peptide_df,
            on=["RunKey"],
            how="left",
        )

    # Final fallback: fill uploader directly from RunKey mapping when merge
    # produced missing values.
    if metadata is not None and not metadata.empty and "RunKey" in df.columns:
        uploader_map = metadata.set_index("RunKey")["Uploader"]
        mapped = df["RunKey"].map(uploader_map)
        if "Uploader" not in df.columns:
            df["Uploader"] = mapped
        else:
            df["Uploader"] = df["Uploader"].where(
                df["Uploader"].notna() & (df["Uploader"].astype(str).str.strip() != ""),
                mapped,
            )

    # Additional fallback: populate uploader by normalized raw-file name when
    # RunKey cannot be used (or is partially missing) after upstream merges.
    if metadata is not None and not metadata.empty and "RawFile" in df.columns:
        metadata_with_raw = metadata.copy()
        metadata_with_raw["_raw_name_norm"] = metadata_with_raw["RawFile"].map(
            _normalize_rawfile_name
        )
        metadata_with_raw = metadata_with_raw.dropna(subset=["_raw_name_norm"])
        metadata_with_raw = metadata_with_raw.drop_duplicates(
            subset=["_raw_name_norm"], keep="last"
        )
        if not metadata_with_raw.empty:
            uploader_by_raw = metadata_with_raw.set_index("_raw_name_norm")["Uploader"]
            mapped_by_raw = df["RawFile"].map(_normalize_rawfile_name).map(uploader_by_raw)
            if "Uploader" not in df.columns:
                df["Uploader"] = mapped_by_raw
            else:
                df["Uploader"] = df["Uploader"].where(
                    df["Uploader"].notna() & (df["Uploader"].astype(str).str.strip() != ""),
                    mapped_by_raw,
                )

    if "Index" in df.columns:
        df = df.sort_values("Index", ascending=True, na_position="last")
    df = _normalize_index_column(df)

    if "DateAcquired" in df.columns:
        df["DateAcquired"] = df["DateAcquired"].view(np.int64)

    assert df.columns.value_counts().max() == 1, df.columns.value_counts()

    return df


class CreateFlag(generics.ListAPIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        """Add flags to raw files."""

        data = request.data

        user = request.user

        project_slug = data["project"]
        pipeline_slug = data["pipeline"]
        raw_files = request.POST.getlist("raw_files")

        project = _projects_for_user(user).filter(slug=project_slug).first()
        if project is None or not (
            _is_admin(user) or user in project.users.all() or project.created_by_id == user.id
        ):
            logging.warning(
                f"User {user.email} does not belong to project {project_slug}"
            )
            return JsonResponse({"status": "Missing permissions"}, status=403)

        pipeline = _pipelines_for_user(user).filter(
            project__slug=project_slug, slug=pipeline_slug
        ).first()
        if pipeline is None:
            return JsonResponse({"status": "Missing permissions"}, status=403)
        results = _results_for_pipeline_mutation(user, pipeline)
        for result in results:
            if result.raw_file.name in raw_files:
                logging.warning(f"Flag {result.raw_file.name} in {pipeline.name}")
                result.raw_file.flagged = True
                result.raw_file.save()

        return JsonResponse({})


class DeleteFlag(generics.ListAPIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        """Remove flags from raw files."""
        data = request.data

        user = request.user

        project_slug = data["project"]
        pipeline_slug = data["pipeline"]
        raw_files = request.POST.getlist("raw_files")

        project = _projects_for_user(user).filter(slug=project_slug).first()
        if project is None or not (
            _is_admin(user) or user in project.users.all() or project.created_by_id == user.id
        ):
            logging.warning(
                f"User {user.email} does not belong to project {project_slug}"
            )
            return JsonResponse({"status": "Missing permissions"}, status=403)

        pipeline = _pipelines_for_user(user).filter(
            project__slug=project_slug, slug=pipeline_slug
        ).first()
        if pipeline is None:
            return JsonResponse({"status": "Missing permissions"}, status=403)
        results = _results_for_pipeline_mutation(user, pipeline)
        for result in results:
            if result.raw_file.name in raw_files:
                logging.warning(f"Un-flag {result.raw_file.name} in {pipeline.name}")
                result.raw_file.flagged = False
                result.raw_file.save()

        return JsonResponse({})


class RawFile(generics.ListAPIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        """Add flags to raw files."""

        data = request.data

        user = request.user

        project_slug = data["project"]
        pipeline_slug = data["pipeline"]
        action = data["action"]

        project = _projects_for_user(user).filter(slug=project_slug).first()
        if project is None or not (
            _is_admin(user) or user in project.users.all() or project.created_by_id == user.id
        ):
            logging.warning(
                f"User {user.email} does not belong to project {project_slug}"
            )
            return JsonResponse({"status": "Missing permissions"}, status=403)

        raw_files = request.POST.getlist("raw_files")

        pipeline = _pipelines_for_user(user).filter(
            project__slug=project_slug, slug=pipeline_slug
        ).first()
        if pipeline is None:
            return JsonResponse({"status": "Missing permissions"}, status=403)
        results = _results_for_user(user).filter(raw_file__pipeline=pipeline)
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
