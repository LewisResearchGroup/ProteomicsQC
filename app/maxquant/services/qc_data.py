import logging
import re
from pathlib import Path as P

import numpy as np
import pandas as pd
from django.core.exceptions import PermissionDenied
from django.db import models

from maxquant.models import Pipeline, Result


def _is_admin(user):
    return bool(user and (user.is_staff or user.is_superuser))


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
        c
        for c in available
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
        c
        for c in available
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


def get_qc_data(project_slug, pipeline_slug, data_range=None, user=None):
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
        raw_fn = P(result.raw_file.name).with_suffix("").name
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

    if metadata is not None and not metadata.empty and "RunKey" in df.columns:
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

    if tmt_peptide_df is not None and not tmt_peptide_df.empty and "RunKey" in df.columns:
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

