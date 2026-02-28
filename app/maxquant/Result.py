import os
import re
import shutil
import zipfile
import subprocess
import pandas as pd
import logging
import datetime
import shlex
import time

from functools import lru_cache, cached_property

from io import BytesIO
from pathlib import Path as P
from glob import glob

from django.db import models
from django_currentuser.db.models import CurrentUserField
from django.dispatch import receiver
from django.utils import timezone
from django.conf import settings
from django.shortcuts import reverse
from django.utils.translation import gettext_lazy as _
from django.utils.html import mark_safe
from celery import current_app

from lrg_omics.proteomics.tools import load_rawtools_data_from, load_maxquant_data_from
from lrg_omics.proteomics.maxquant.MaxquantReader import MaxquantReader

from .tasks import rawtools_metrics, rawtools_qc, run_maxquant

DATALAKE_ROOT = settings.DATALAKE_ROOT
COMPUTE_ROOT = settings.COMPUTE_ROOT
COMPUTE = settings.COMPUTE


def get_time_of_file_modification(fn):
    fn = P(fn)
    mtime = datetime.datetime.fromtimestamp(fn.stat().st_mtime)
    return mtime.utcnow()


class Result(models.Model):
    class Meta:
        verbose_name = _("Result")
        verbose_name_plural = _("Results")

    created_by = CurrentUserField()

    created = models.DateTimeField(default=timezone.now)

    raw_file = models.OneToOneField("RawFile", on_delete=models.CASCADE)
    input_source = models.CharField(max_length=32, default="upload")
    maxquant_task_id = models.CharField(max_length=255, null=True, blank=True)
    rawtools_metrics_task_id = models.CharField(max_length=255, null=True, blank=True)
    rawtools_qc_task_id = models.CharField(max_length=255, null=True, blank=True)
    maxquant_task_submitted_at = models.DateTimeField(null=True, blank=True)
    rawtools_metrics_task_submitted_at = models.DateTimeField(null=True, blank=True)
    rawtools_qc_task_submitted_at = models.DateTimeField(null=True, blank=True)
    cancel_requested_at = models.DateTimeField(null=True, blank=True)

    @property
    def pipeline(self):
        return self.raw_file.pipeline

    def __str__(self):
        return str(self.name)

    @property
    def name(self):
        return str(self.raw_file.name)

    @property
    def raw_fn(self):
        return self.raw_file.path

    @property
    def basename(self):
        return self.raw_fn.with_suffix("").name

    @property
    def mqpar_fn(self):
        return self.pipeline.mqpar_path

    @property
    def fasta_fn(self):
        return self.pipeline.fasta_path

    @property
    def run_dir(self):
        return COMPUTE_ROOT / "tmp" / "MaxQuant" / self.name

    @property
    def pipename(self):
        return self.pipeline.name

    @property
    def path(self):
        return self.raw_file.output_dir

    @property
    def output_dir(self):
        return self.raw_file.output_dir

    @property
    def output_dir_maxquant(self):
        return self.path / "maxquant"

    @property
    def output_dir_rawtools(self):
        return self.path / "rawtools"

    @property
    def output_dir_rawtools_qc(self):
        return self.path / "rawtools_qc"

    @property
    def maxquant_binary(self):
        return self.pipeline.maxquant_executable

    @property
    def output_dir_exists(self):
        return self.path.is_dir()

    @property
    def maxquantcmd(self):
        dotnet_cmd = os.getenv("DOTNET_CMD", "dotnet")
        if (
            self.raw_file.pipeline.maxquant_executable is None
            or self.raw_file.pipeline.maxquant_executable == ""
        ):
            return "maxquant"
        exe = self.raw_file.pipeline.maxquant_executable
        exe_str = str(exe)
        exe_quoted = shlex.quote(exe_str)
        runtime = os.getenv("MAXQUANT_RUNTIME", "").lower()

        def version_tuple(path):
            match = re.search(r"(\d+)\.(\d+)\.(\d+)\.(\d+)", path)
            if not match:
                return None
            return tuple(int(part) for part in match.groups())

        def use_dotnet(path):
            if runtime in {"mono", "dotnet"}:
                return runtime == "dotnet"
            version = version_tuple(path)
            # MaxQuant >= 2.6.* ships for .NET; older versions keep using mono
            if version and version >= (2, 6, 0, 0):
                return True
            return False

        lower = exe_str.lower()
        if lower.endswith(".dll"):
            return f"{dotnet_cmd} {exe_quoted}"

        if lower.endswith(".exe"):
            if use_dotnet(exe_str):
                dll_candidate = str(P(exe_str).with_suffix(".dll"))
                target = dll_candidate if os.path.isfile(dll_candidate) else exe_str
                return f"{dotnet_cmd} {shlex.quote(target)}"
            return f"mono {exe_quoted}"
        return exe_quoted

    @property
    def run_dir_exists(self):
        return self.run_dir.is_dir()

    @property
    def use_downstream(self):
        return self.raw_file.use_downstream

    def maxquant_parameters(self):
        mqpar_file = str(self.mqpar_fn)
        fasta_file = str(self.fasta_fn)
        run_dir = str(self.run_dir)
        output_dir = str(self.output_dir_maxquant)
        maxquantcmd = str(self.maxquantcmd)

        params = dict(
            maxquantcmd=maxquantcmd,
            mqpar_file=mqpar_file,
            fasta_file=fasta_file,
            run_dir=run_dir,
            output_dir=output_dir,
            add_uuid_to_rundir=True,
            cleanup=True,
        )
        return params

    def run_maxquant(self, rerun=False):
        if self.pipeline.has_maxquant_config:
            if not rerun and self.n_files_maxquant > 0:
                return
            raw_file = str(self.raw_fn)
            params = self.maxquant_parameters()
            async_result = run_maxquant.delay(
                raw_file, params, rerun=rerun, result_id=self.pk
            )
            self.maxquant_task_id = async_result.id
            self.maxquant_task_submitted_at = timezone.now()
            self.cancel_requested_at = None
            self.save(
                update_fields=[
                    "maxquant_task_id",
                    "maxquant_task_submitted_at",
                    "cancel_requested_at",
                ]
            )
            logging.info("Submitted MaxQuant.")

    @property
    def maxquant_execution_time(self):
        fn = self.output_dir_maxquant / "time.txt"
        if fn.is_file():
            with open(fn) as file:
                time = file.read()
            return time
        else:
            return None

    def run_rawtools_qc(self, rerun=False):
        inp_dir, out_dir = str(self.raw_file.path.parent), str(
            self.output_dir_rawtools_qc
        )
        if rerun or (self.n_files_rawtools_qc == 0):
            async_result = rawtools_qc.delay(
                inp_dir, out_dir, rerun=rerun, result_id=self.pk
            )
            self.rawtools_qc_task_id = async_result.id
            self.rawtools_qc_task_submitted_at = timezone.now()
            self.cancel_requested_at = None
            self.save(
                update_fields=[
                    "rawtools_qc_task_id",
                    "rawtools_qc_task_submitted_at",
                    "cancel_requested_at",
                ]
            )
            logging.info("Submitted RawTools QC.")

    def run_rawtools_metrics(self, rerun=False):
        raw_fn, out_dir, args = (
            str(self.raw_file.path),
            str(self.output_dir_rawtools),
            self.pipeline.rawtools_args,
        )
        if rerun or (self.n_files_rawtools_metrics == 0):
            async_result = rawtools_metrics.delay(
                raw_fn, out_dir, args, rerun=rerun, result_id=self.pk
            )
            self.rawtools_metrics_task_id = async_result.id
            self.rawtools_metrics_task_submitted_at = timezone.now()
            self.cancel_requested_at = None
            self.save(
                update_fields=[
                    "rawtools_metrics_task_id",
                    "rawtools_metrics_task_submitted_at",
                    "cancel_requested_at",
                ]
            )
            logging.info("Submitted RawTools metrics.")

    def run(self):
        logging.info("Run Jobs")
        self.run_maxquant()
        self.run_rawtools_metrics()
        self.run_rawtools_qc()

    def get_data_from_file(self, fn="proteinGroups.txt"):
        abs_fn = self.output_dir_maxquant / fn
        if abs_fn.is_file():
            df = MaxquantReader(remove_contaminants=False, remove_reverse=False).read(
                abs_fn
            )
            if df is None:
                return None
            df["RawFile"] = str(self.raw_file.name)
            df["Project"] = str(self.raw_file.pipeline.project.name)
            df["Pipeline"] = str(self.raw_file.pipeline.name)
            df["UseDownstream"] = str(self.raw_file.use_downstream)
            df["Flagged"] = str(self.raw_file.flagged)
            df = df.set_index(
                ["Project", "Pipeline", "RawFile", "UseDownstream", "Flagged"]
            ).reset_index()
            return df
        else:
            return None

    @property
    def url(self):
        return reverse("maxquant:mq_detail", kwargs={"pk": self.pk})

    @property
    def download(self):
        stream = BytesIO()
        path = self.output_dir
        files = glob(f"{path}/**/*.*", recursive=True)
        with zipfile.ZipFile(stream, "w") as temp_zip_file:
            for fn in files:
                temp_zip_file.write(fn, arcname=P(fn).name)
        return stream.getvalue()

    def maxquant_qc_data(self):
        try:
            df = load_maxquant_data_from(self.path, unpack=False)
        except Exception as e:
            logging.warning(f"{e}: load_maxquant_data_from({self.path})")
        if df is None:
            df = pd.DataFrame()
        df["RawFile"] = self.raw_fn.with_suffix("").name
        return df.set_index("RawFile").reset_index()

    def rawtools_qc_data(self):
        df = load_rawtools_data_from(self.path)
        if df is None:
            df = pd.DataFrame()
        df["RawFile"] = self.raw_fn.with_suffix("").name
        return df.set_index("RawFile").reset_index()

    @property
    def parquet_path(self):
        return self.pipeline.parquet_path

    def create_protein_quant(self):
        fn_txt = "proteinGroups.txt"
        abs_fn_txt = self.output_dir_maxquant / fn_txt
        abs_fn_par = self.protein_quant_fn
        if not abs_fn_par.is_file():
            if not abs_fn_par.parent.is_dir():
                os.makedirs(abs_fn_par.parent)
            df = self.get_data_from_file("proteinGroups.txt")
            # Remove duplicated columns
            # sometimes MaxQuant generates
            # files with repeated column names
            if df is None:
                return None
            df = df.loc[:, ~df.columns.duplicated()]
            try:
                df.to_parquet(abs_fn_par)
            except Exception as e:
                logging.error(f"Could not create parquet file for {abs_fn_txt}:\n {e}")
                return None
        return abs_fn_par

    @property
    def protein_quant_fn(self):
        basename = self.basename
        par_path = (self.parquet_path / "protein_groups" / basename).with_suffix(
            ".parquet"
        )
        return par_path

    @property
    def n_files_maxquant(self):
        return len(glob(f'{self.output_dir_maxquant/"*.*"}'))

    @property
    def n_files_rawtools_metrics(self):
        return len(glob(f'{self.output_dir_rawtools/"*.*"}'))

    @property
    def n_files_rawtools_qc(self):
        return len(glob(f'{self.output_dir_rawtools_qc/"*.*"}'))

    @staticmethod
    def _has_error_text(fn):
        if not fn.is_file():
            return False
        try:
            return fn.stat().st_size > 0
        except OSError:
            return False

    @staticmethod
    def _dir_has_files(path):
        return path.is_dir() and any(path.iterdir())

    @staticmethod
    def _task_state(task_id):
        if not task_id:
            return None
        try:
            return current_app.AsyncResult(task_id).state
        except Exception:
            return None

    @staticmethod
    def _is_task_running(task_state):
        return task_state in {"STARTED"}

    @staticmethod
    def _is_task_queued(task_state):
        return task_state in {"PENDING", "RECEIVED", "RETRY"}

    @staticmethod
    def _is_task_failed(task_state):
        return task_state in {"FAILURE"}

    @staticmethod
    def _is_task_canceled(task_state):
        return task_state in {"REVOKED"}

    @staticmethod
    def _is_task_succeeded(task_state):
        return task_state in {"SUCCESS"}

    @staticmethod
    @lru_cache(maxsize=2)
    def _known_enqueued_task_ids(cache_bucket):
        # cache_bucket is an integer time window to keep inspect calls cheap
        # while avoiding stale queue snapshots.
        del cache_bucket
        try:
            inspect_timeout = float(
                getattr(settings, "RESULT_STATUS_INSPECT_TIMEOUT_SECONDS", 10.0)
            )
            inspector = current_app.control.inspect(timeout=inspect_timeout)
            if inspector is None:
                return set()
            snapshots = [
                inspector.active() or {},
                inspector.reserved() or {},
                inspector.scheduled() or {},
            ]
        except Exception:
            return set()

        task_ids = set()
        for snapshot in snapshots:
            for worker_tasks in snapshot.values():
                for task in worker_tasks or []:
                    task_id = task.get("id")
                    if task_id:
                        task_ids.add(task_id)
                    request_data = task.get("request") or {}
                    request_id = request_data.get("id")
                    if request_id:
                        task_ids.add(request_id)
        return task_ids

    def _is_task_observed_in_queue(self, task_id):
        if not task_id:
            return False
        if not self._queue_inspect_allowed():
            return False
        # 3-second windows keep UI responsive without hammering inspect.
        bucket = int(time.time() / 3)
        return task_id in self._known_enqueued_task_ids(bucket)

    def _queue_inspect_allowed(self):
        mode = getattr(self, "_queue_check_mode", "adaptive")
        if mode == "off":
            return False
        if mode == "on":
            return True
        max_visible_runs = int(
            getattr(settings, "RESULT_STATUS_INSPECT_MAX_VISIBLE_RUNS", 25)
        )
        max_active_runs = int(
            getattr(settings, "RESULT_STATUS_INSPECT_MAX_ACTIVE_RUNS", 12)
        )
        visible_run_count = getattr(self, "_visible_run_count", None)
        active_run_count = getattr(self, "_active_run_count", None)
        if visible_run_count is not None and visible_run_count > max_visible_runs:
            return False
        if active_run_count is not None and active_run_count > max_active_runs:
            return False
        return True

    @staticmethod
    def _path_recently_modified(path, lookback_seconds=180):
        path = P(path)
        if not path.exists():
            return False
        now_ts = time.time()
        try:
            if path.is_file():
                return (now_ts - path.stat().st_mtime) <= lookback_seconds
            for entry in path.iterdir():
                try:
                    if (now_ts - entry.stat().st_mtime) <= lookback_seconds:
                        return True
                except OSError:
                    continue
        except OSError:
            return False
        return False

    @staticmethod
    def _is_fresh_output_file(fn, submitted_at):
        if not fn.is_file():
            return False
        if submitted_at is None:
            return True
        skew_seconds = int(
            getattr(settings, "RESULT_STATUS_DONE_MTIME_SKEW_SECONDS", 300)
        )
        try:
            return fn.stat().st_mtime >= (submitted_at.timestamp() - skew_seconds)
        except OSError:
            return False

    def _has_fresh_error_text(self, err_fn, submitted_at):
        if not self._is_fresh_output_file(err_fn, submitted_at):
            return False
        return self._has_error_text(err_fn)

    @staticmethod
    def _file_contains_text(fn, needle, chunk_size=65536):
        if not fn.is_file():
            return False
        try:
            with open(fn, "r", encoding="utf-8", errors="ignore") as handle:
                tail = ""
                while True:
                    chunk = handle.read(chunk_size)
                    if not chunk:
                        return False
                    haystack = tail + chunk
                    if needle in haystack:
                        return True
                    tail = haystack[-(len(needle) - 1):] if len(needle) > 1 else ""
        except OSError:
            return False

    def _has_fresh_success_text(self, fn, submitted_at, needle):
        if not self._is_fresh_output_file(fn, submitted_at):
            return False
        return self._file_contains_text(fn, needle)

    def _has_fresh_error_markers(self, fn, submitted_at, markers):
        if not self._is_fresh_output_file(fn, submitted_at):
            return False
        for marker in markers:
            if self._file_contains_text(fn, marker):
                return True
        return False

    @classmethod
    def _started_but_stale(
        cls, task_state, activity_paths, lookback_seconds=600
    ):
        if not cls._is_task_running(task_state):
            return False
        return not any(
            cls._path_recently_modified(path, lookback_seconds=lookback_seconds)
            for path in activity_paths
            if path is not None
        )

    def _stage_is_queued(self, task_id, task_state, submitted_at):
        del submitted_at
        if task_state in {"RECEIVED", "RETRY"}:
            return True
        if task_state == "PENDING":
            # Keep PENDING as queued to avoid "missing" churn that can trigger
            # duplicate re-submissions during normal broker backlogs.
            return True
        if task_state != "STARTED":
            return False
        # STARTED jobs are active if they are visible on a worker snapshot.
        return self._is_task_observed_in_queue(task_id)

    def _pending_stalled(self, task_id, submitted_at):
        if not task_id or submitted_at is None:
            return False
        task_state = self._task_state(task_id)
        if task_state != "PENDING":
            return False
        warning_after = int(
            getattr(settings, "RESULT_STATUS_PENDING_STALLED_WARNING_SECONDS", 7200)
        )
        age_seconds = (timezone.now() - submitted_at).total_seconds()
        # Fast path: most pending tasks are recent; avoid expensive inspect()
        # calls on every page render.
        if age_seconds <= warning_after:
            return False
        # If inspect sees it, it is not stalled from UX perspective.
        if self._is_task_observed_in_queue(task_id):
            return False
        return True

    @property
    def rawtools_metrics_expected_files(self):
        raw_name = self.raw_file.name
        return [
            self.output_dir_rawtools / f"{raw_name}_Ms_TIC_chromatogram.txt",
            self.output_dir_rawtools / f"{raw_name}_Ms2_TIC_chromatogram.txt",
        ]

    @property
    def rawtools_qc_expected_files(self):
        # Older and newer RawTools QC layouts have used different output locations.
        return [
            self.output_dir_rawtools_qc / "QcDataTable.csv",
            self.raw_file.path.parent / "QcDataTable.csv",
        ]

    @property
    def maxquant_run_root(self):
        return COMPUTE_ROOT / "tmp" / "MaxQuant"

    @cached_property
    def maxquant_run_dir_candidates(self):
        # MaxquantRunner uses add_uuid_to_rundir=True, yielding directories like:
        # <compute>/tmp/MaxQuant/<uuid>-<raw_basename>
        raw_base = self.basename
        run_root = self.maxquant_run_root
        if not run_root.is_dir():
            return []
        candidates = []
        candidates.extend(run_root.glob(f"*-{raw_base}"))
        # keep backward-compatibility if add_uuid_to_rundir is disabled
        candidates.extend(
            [
                run_root / raw_base,
                run_root / self.name,
            ]
        )
        # return only existing unique directories
        uniq = []
        seen = set()
        for path in candidates:
            if path in seen:
                continue
            seen.add(path)
            if path.is_dir():
                uniq.append(path)
        return uniq

    @cached_property
    def maxquant_status(self):
        err_fn = self.output_dir_maxquant / "maxquant.err"
        out_fn = self.output_dir_maxquant / "maxquant.out"
        done_fn = self.output_dir_maxquant / "time.txt"
        fatal_error_markers = ("Unhandled Exception", "System.Exception")
        started_stale_seconds = int(
            getattr(settings, "RESULT_STATUS_MAXQUANT_STALE_SECONDS", 21600)
        )
        fallback_activity_seconds = int(
            getattr(settings, "RESULT_STATUS_ACTIVITY_FALLBACK_SECONDS", 300)
        )
        cancel_activity_seconds = int(
            getattr(settings, "RESULT_STATUS_CANCEL_ACTIVITY_SECONDS", 180)
        )
        run_dir_candidates = None

        def get_run_dir_candidates():
            nonlocal run_dir_candidates
            if run_dir_candidates is None:
                run_dir_candidates = self.maxquant_run_dir_candidates
            return run_dir_candidates
        if self._has_fresh_error_markers(
            err_fn, self.maxquant_task_submitted_at, fatal_error_markers
        ):
            return "failed"
        if self._has_fresh_success_text(
            out_fn, self.maxquant_task_submitted_at, "Finish writing tables"
        ):
            return "done"
        task_state = self._task_state(self.maxquant_task_id)
        if self.cancel_requested_at is not None:
            # A cancel request can race with process teardown. Keep reporting
            # running while there is clear task/filesystem activity.
            if self._is_task_running(task_state):
                return "running"
            if any(
                self._path_recently_modified(
                    path, lookback_seconds=cancel_activity_seconds
                )
                for path in [*get_run_dir_candidates(), self.output_dir_maxquant]
            ):
                return "running"
            return "canceled"
        if self._is_task_canceled(task_state):
            return "canceled"
        if self._is_task_running(task_state):
            maxquant_activity_paths = [
                *get_run_dir_candidates(),
                self.output_dir_maxquant,
            ]
            if self._started_but_stale(
                task_state,
                maxquant_activity_paths,
                lookback_seconds=started_stale_seconds,
            ):
                if self._is_task_observed_in_queue(self.maxquant_task_id):
                    return "running"
                return "missing"
            return "running"
        if self._stage_is_queued(
            self.maxquant_task_id, task_state, self.maxquant_task_submitted_at
        ):
            return "queued"
        if self._is_task_failed(task_state):
            return "failed"
        if self._is_task_succeeded(task_state):
            if self._has_fresh_error_text(err_fn, self.maxquant_task_submitted_at):
                return "failed"
            if self._is_fresh_output_file(done_fn, self.maxquant_task_submitted_at):
                return "done"
            # Task backend says success but required marker/output is missing.
            return "failed"
        if self._has_fresh_error_text(err_fn, self.maxquant_task_submitted_at):
            return "failed"
        if self._is_fresh_output_file(done_fn, self.maxquant_task_submitted_at):
            return "done"
        # Celery inspect can miss transient task states. If the MaxQuant run dir
        # or output folder shows fresh filesystem activity, treat it as running.
        if any(
            self._path_recently_modified(
                path, lookback_seconds=fallback_activity_seconds
            )
            for path in get_run_dir_candidates()
        ):
            return "running"
        if self._path_recently_modified(
            self.output_dir_maxquant, lookback_seconds=fallback_activity_seconds
        ):
            return "running"
        return "missing"

    @cached_property
    def rawtools_metrics_status(self):
        err_fn = self.output_dir_rawtools / "rawtools_metrics.err"
        done_fns = self.rawtools_metrics_expected_files
        started_stale_seconds = int(
            getattr(settings, "RESULT_STATUS_RAWTOOLS_STALE_SECONDS", 3600)
        )
        fallback_activity_seconds = int(
            getattr(settings, "RESULT_STATUS_ACTIVITY_FALLBACK_SECONDS", 300)
        )
        cancel_activity_seconds = int(
            getattr(settings, "RESULT_STATUS_CANCEL_ACTIVITY_SECONDS", 180)
        )
        rawtools_metrics_activity_paths = [self.output_dir_rawtools]
        task_state = self._task_state(self.rawtools_metrics_task_id)
        if self._has_fresh_error_text(
            err_fn, self.rawtools_metrics_task_submitted_at
        ):
            return "failed"
        # Done should win over cancel when output markers are present.
        # This avoids reporting a completed stage as canceled when a cancel
        # request raced with the final file writes.
        if all(
            self._is_fresh_output_file(fn, self.rawtools_metrics_task_submitted_at)
            for fn in done_fns
        ):
            return "done"
        # If all outputs exist and no process is running, treat as done.
        if all(fn.is_file() for fn in done_fns) and not self._is_task_running(
            task_state
        ):
            return "done"
        if self.cancel_requested_at is not None:
            if self._is_task_running(task_state):
                return "running"
            if self._path_recently_modified(
                self.output_dir_rawtools,
                lookback_seconds=cancel_activity_seconds,
            ):
                return "running"
            return "canceled"
        if self._is_task_canceled(task_state):
            return "canceled"
        if self._is_task_running(task_state):
            if self._started_but_stale(
                task_state,
                rawtools_metrics_activity_paths,
                lookback_seconds=started_stale_seconds,
            ):
                if self._is_task_observed_in_queue(self.rawtools_metrics_task_id):
                    return "running"
                return "missing"
            return "running"
        if self._stage_is_queued(
            self.rawtools_metrics_task_id,
            task_state,
            self.rawtools_metrics_task_submitted_at,
        ):
            return "queued"
        if self._is_task_failed(task_state):
            return "failed"
        if self._is_task_succeeded(task_state):
            # Task says SUCCESS but we didn't return "done" from output-file check
            # above → outputs missing or not fresh; report incomplete, not failed.
            return "missing"
        if self._path_recently_modified(
            self.output_dir_rawtools, lookback_seconds=fallback_activity_seconds
        ):
            return "running"
        return "missing"

    @cached_property
    def rawtools_qc_status(self):
        err_fn = self.output_dir_rawtools_qc / "rawtools_qc.err"
        done_fns = self.rawtools_qc_expected_files
        started_stale_seconds = int(
            getattr(settings, "RESULT_STATUS_RAWTOOLS_STALE_SECONDS", 3600)
        )
        fallback_activity_seconds = int(
            getattr(settings, "RESULT_STATUS_ACTIVITY_FALLBACK_SECONDS", 300)
        )
        cancel_activity_seconds = int(
            getattr(settings, "RESULT_STATUS_CANCEL_ACTIVITY_SECONDS", 180)
        )
        rawtools_qc_activity_paths = [self.output_dir_rawtools_qc]
        task_state = self._task_state(self.rawtools_qc_task_id)
        if self._has_fresh_error_text(err_fn, self.rawtools_qc_task_submitted_at):
            return "failed"
        # Done should win over cancel when output markers are present.
        # This avoids reporting a completed stage as canceled when a cancel
        # request raced with the final file writes.
        if any(
            self._is_fresh_output_file(fn, self.rawtools_qc_task_submitted_at)
            for fn in done_fns
        ):
            return "done"
        # If output exists and no process is running, treat as done (e.g. run
        # finished but task is stale PENDING or freshness failed due to requeue).
        if any(fn.is_file() for fn in done_fns) and not self._is_task_running(
            task_state
        ):
            return "done"
        if self.cancel_requested_at is not None:
            if self._is_task_running(task_state):
                return "running"
            if self._path_recently_modified(
                self.output_dir_rawtools_qc,
                lookback_seconds=cancel_activity_seconds,
            ):
                return "running"
            return "canceled"
        if self._is_task_canceled(task_state):
            return "canceled"
        if self._is_task_running(task_state):
            if self._started_but_stale(
                task_state,
                rawtools_qc_activity_paths,
                lookback_seconds=started_stale_seconds,
            ):
                if self._is_task_observed_in_queue(self.rawtools_qc_task_id):
                    return "running"
                return "missing"
            return "running"
        if self._stage_is_queued(
            self.rawtools_qc_task_id, task_state, self.rawtools_qc_task_submitted_at
        ):
            return "queued"
        if self._is_task_failed(task_state):
            return "failed"
        if self._is_task_succeeded(task_state):
            # Task says SUCCESS but we didn't return "done" from output-file check
            # above → outputs missing or not fresh; report incomplete, not failed.
            return "missing"
        if self._path_recently_modified(
            self.output_dir_rawtools_qc, lookback_seconds=fallback_activity_seconds
        ):
            return "running"
        return "missing"

    @cached_property
    def stage_statuses(self):
        return {
            "maxquant": self.maxquant_status,
            "rawtools_metrics": self.rawtools_metrics_status,
            "rawtools_qc": self.rawtools_qc_status,
        }

    @cached_property
    def overall_status(self):
        statuses = self.stage_statuses.values()
        # Active stages win precedence so UI/control flow cannot claim terminal
        # failure while any backend worker is still running/queued.
        if any(status == "running" for status in statuses):
            return "running"
        # Failed takes precedence over queued: if any stage failed, the run has
        # failed even if a downstream stage is still queued.
        if "failed" in statuses:
            return "failed"
        if any(status == "queued" for status in statuses):
            return "queued"
        if "canceled" in statuses:
            return "canceled"
        if all(status == "done" for status in statuses):
            return "done"
        # No active stages remain, but outputs are incomplete.
        # This includes combinations like {done, missing, missing}.
        return "missing"

    @cached_property
    def is_processing(self):
        return self.has_active_stage

    @cached_property
    def has_active_stage(self):
        # Don't treat run as active when it has already failed or been canceled;
        # avoids showing "Queued" and auto-refresh when e.g. only a stuck
        # downstream task is PENDING and no process is actually running.
        if self.overall_status in {"failed", "canceled"}:
            return False
        return any(
            status in {"queued", "running"} for status in self.stage_statuses.values()
        )

    @cached_property
    def processing_message(self):
        if any(
            (
                self._pending_stalled(
                    self.maxquant_task_id, self.maxquant_task_submitted_at
                ),
                self._pending_stalled(
                    self.rawtools_metrics_task_id,
                    self.rawtools_metrics_task_submitted_at,
                ),
                self._pending_stalled(
                    self.rawtools_qc_task_id, self.rawtools_qc_task_submitted_at
                ),
            )
        ):
            return "Some tasks have remained queued for a long time. Verify worker/broker health and then cancel/requeue if needed."
        if self.has_active_stage and any(
            s in {"failed", "canceled"} for s in self.stage_statuses.values()
        ):
            return "Some stages failed or were canceled while others are still running. Review per-stage details below."
        if self.overall_status == "failed":
            return "One or more jobs failed. Review per-stage error details below."
        if self.overall_status == "canceled":
            return "Jobs were canceled before completion."
        if self.overall_status == "done":
            return "All processing stages completed."

        completed = sum(1 for s in self.stage_statuses.values() if s == "done")
        total = len(self.stage_statuses)
        if completed == 0:
            return "Jobs are queued. Results will appear as each stage finishes."
        return f"Processing in progress ({completed}/{total} stages completed)."

    @staticmethod
    def _read_text_excerpt(fn, max_chars=16000):
        if not fn.is_file():
            return ""
        try:
            with open(fn, "r", encoding="utf-8", errors="ignore") as file:
                content = file.read(max_chars + 1)
        except OSError:
            return ""
        if len(content) > max_chars:
            content = content[:max_chars] + "\n... (truncated)"
        return content

    @staticmethod
    def _compact_lines(text, max_lines=24):
        lines = [line.rstrip() for line in text.splitlines() if line.strip()]
        if not lines:
            return ""
        compact = lines[:max_lines]
        suffix = "\n... (truncated)" if len(lines) > max_lines else ""
        return "\n".join(compact) + suffix

    @classmethod
    def _extract_maxquant_error_excerpt(cls, text):
        lines = [line.rstrip() for line in text.splitlines() if line.strip()]
        if not lines:
            return ""
        markers = ("Unhandled Exception", "System.Exception")
        for idx, line in enumerate(lines):
            if any(marker in line for marker in markers):
                start = max(0, idx - 1)
                end = min(len(lines), idx + 16)
                excerpt = "\n".join(lines[start:end])
                if end < len(lines):
                    excerpt += "\n... (truncated)"
                return excerpt
        return cls._compact_lines(text, max_lines=24)

    @cached_property
    def stage_error_details(self):
        details = []
        stage_specs = [
            (
                "maxquant",
                "MaxQuant",
                self.output_dir / "maxquant" / "maxquant.err",
            ),
            (
                "rawtools_metrics",
                "RawTools metrics",
                self.output_dir / "rawtools" / "rawtools_metrics.err",
            ),
            (
                "rawtools_qc",
                "RawTools QC",
                self.output_dir / "rawtools_qc" / "rawtools_qc.err",
            ),
        ]

        for stage_key, label, err_fn in stage_specs:
            if self.stage_statuses.get(stage_key) != "failed":
                continue
            raw_text = self._read_text_excerpt(err_fn)
            if stage_key == "maxquant":
                excerpt = self._extract_maxquant_error_excerpt(raw_text)
            else:
                excerpt = self._compact_lines(raw_text, max_lines=20)
            if not excerpt:
                excerpt = "No error details were captured in the stage error log."
            details.append({"stage": stage_key, "label": label, "message": excerpt})
        return details

    @property
    def status_protein_quant_parquet(self):
        fn = self.protein_quant_fn
        if not fn.is_file():
            return "File not found"
        try:
            pd.read_parquet(fn)
            return "OK"
        except Exception:
            return "Not readable."

    @property
    def maxquant_errors(self):
        fn = self.output_dir / "maxquant" / "maxquant.err"
        if not fn.is_file():
            return "No file"
        else:
            with open(fn, "r") as file:
                lines = file.read()
            return lines

    @property
    def rawtools_qc_errors(self):
        fn = self.output_dir / "rawtools_qc" / "rawtools_qc.err"
        if not fn.is_file():
            return "No file"
        else:
            with open(fn, "r") as file:
                lines = file.read()
            return lines

    @property
    def rawtools_metrics_errors(self):
        fn = self.output_dir / "rawtools" / "rawtools_metrics.err"
        if not fn.is_file():
            return "No file"
        else:
            with open(fn, "r") as file:
                lines = file.read()
            return lines

    @property
    def href(self):
        return self.output_dir

    @property
    def link(self):
        return mark_safe(f"<a href='{self.href}'>Browse</a>")

    @property
    def task_ids(self):
        return [
            self.maxquant_task_id,
            self.rawtools_metrics_task_id,
            self.rawtools_qc_task_id,
        ]

    def cancel_active_jobs(self):
        revoked = 0
        for task_id in self.task_ids:
            if not task_id:
                continue
            try:
                current_app.control.revoke(task_id, terminate=True, signal="SIGTERM")
                revoked += 1
            except Exception as exc:
                logging.warning(
                    "Could not revoke task %s for result %s: %s",
                    task_id,
                    self.pk,
                    exc,
                )

        killed = self._kill_local_processes_for_run()
        if killed > 0:
            logging.info(
                "Killed %s local process(es) for result %s (%s).",
                killed,
                self.pk,
                self.basename,
            )

        self.cancel_requested_at = timezone.now()
        self.save(update_fields=["cancel_requested_at"])
        # Invalidate status caches so reused instances recompute with cancel state.
        for key in (
            "maxquant_status",
            "rawtools_metrics_status",
            "rawtools_qc_status",
            "stage_statuses",
            "overall_status",
            "has_active_stage",
            "is_processing",
            "processing_message",
        ):
            self.__dict__.pop(key, None)
        return revoked

    def _kill_local_processes_for_run(self):
        # Celery revoke(terminate=True) can leave child mono/sh processes alive.
        # As a fallback, terminate processes whose command line references this run.
        raw_name = self.raw_file.name
        raw_stem = P(raw_name).stem
        patterns = [
            self.basename,
            raw_name,
            raw_stem,
            str(self.raw_fn),
            str(self.raw_fn.parent),
            str(self.output_dir_maxquant),
            str(self.output_dir_rawtools),
            str(self.output_dir_rawtools_qc),
        ]
        killed = 0
        matched_pids = set()

        def _pids_for_pattern(pattern):
            if not pattern:
                return []
            try:
                proc = subprocess.run(
                    ["pgrep", "-f", pattern],
                    capture_output=True,
                    text=True,
                    check=False,
                )
            except FileNotFoundError:
                return []
            if proc.returncode not in (0, 1):
                return []
            pids = []
            for line in (proc.stdout or "").splitlines():
                line = line.strip()
                if not line:
                    continue
                try:
                    pid = int(line)
                except ValueError:
                    continue
                if pid != os.getpid():
                    pids.append(pid)
            return pids

        for pattern in patterns:
            if not pattern:
                continue
            for pid in _pids_for_pattern(pattern):
                matched_pids.add(pid)
            for signal in ("TERM", "KILL"):
                try:
                    proc = subprocess.run(
                        ["pkill", f"-{signal}", "-f", pattern],
                        capture_output=True,
                        text=True,
                        check=False,
                    )
                except FileNotFoundError:
                    logging.warning("pkill command not found; skipping process cleanup.")
                    return killed
                # pkill return code:
                # 0 => matched and signaled, 1 => no processes matched, >1 => error.
                if proc.returncode == 0:
                    killed += 1
                elif proc.returncode > 1:
                    logging.warning(
                        "pkill -%s -f %s failed (rc=%s): %s",
                        signal,
                        pattern,
                        proc.returncode,
                        (proc.stderr or "").strip(),
                    )

        # Explicit PID fallback in case pkill misses descendants.
        for sig in (signal.SIGTERM, signal.SIGKILL):
            for pid in sorted(matched_pids):
                try:
                    os.kill(pid, sig)
                    killed += 1
                except ProcessLookupError:
                    continue
                except PermissionError:
                    continue
                except OSError:
                    continue
        return killed


@receiver(models.signals.post_save, sender=Result)
def run_maxquant_after_save(sender, instance, created, *args, **kwargs):
    if created:
        instance.run()
        # Default new processed samples to be usable downstream; users can unmark later.
        if instance.raw_file.use_downstream is not True:
            instance.raw_file.use_downstream = True
            instance.raw_file.save(update_fields=["use_downstream"])


@receiver(models.signals.post_delete, sender=Result)
def remove_maxquant_folders_after_delete(sender, instance, *args, **kwargs):
    result = instance
    if result.output_dir_exists:
        shutil.rmtree(result.path)
    if result.run_dir_exists:
        shutil.rmtree(result.run_dir)
    if result.protein_quant_fn.is_file():
        os.remove(result.protein_quant_fn)
