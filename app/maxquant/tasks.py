import os
import logging
import signal
import subprocess
import time
from os.path import isdir, join, isfile, basename
from celery import shared_task
from django.apps import apps

from lrg_omics.proteomics.maxquant import MaxquantRunner

from lrg_omics.proteomics.rawtools.quality_control import (
    rawtools_metrics_cmd,
    rawtools_qc_cmd,
)


def _safe_float(env_name, default):
    try:
        return float(os.getenv(env_name, default))
    except (TypeError, ValueError):
        return float(default)


def _safe_int(env_name, default):
    try:
        return int(os.getenv(env_name, default))
    except (TypeError, ValueError):
        return int(default)


def _available_memory_gb():
    # Linux containers expose MemAvailable in /proc/meminfo.
    try:
        with open("/proc/meminfo", "r", encoding="utf-8") as handle:
            for line in handle:
                if line.startswith("MemAvailable:"):
                    kb = float(line.split()[1])
                    return kb / 1024.0 / 1024.0
    except Exception:
        return None
    return None


def _normalized_load():
    try:
        load_1m = os.getloadavg()[0]
    except OSError:
        return None
    n_cpu = os.cpu_count() or 1
    return load_1m / float(n_cpu)


def _resources_available(min_free_mem_gb, max_load_per_cpu):
    available_gb = _available_memory_gb()
    norm_load = _normalized_load()

    mem_ok = True if available_gb is None else (available_gb >= min_free_mem_gb)
    load_ok = True if norm_load is None else (norm_load <= max_load_per_cpu)
    return mem_ok and load_ok, available_gb, norm_load


def _defer_if_busy(task, kind, min_free_mem_gb, max_load_per_cpu):
    ok, avail_gb, norm_load = _resources_available(
        min_free_mem_gb=min_free_mem_gb,
        max_load_per_cpu=max_load_per_cpu,
    )
    if ok:
        return

    retry_seconds = _safe_int("RESOURCE_RETRY_SECONDS", 60)
    logging.info(
        "[%s] Deferring for %ss (min_mem=%.1fGB, avail_mem=%sGB, max_load=%.2f, load=%s)",
        kind,
        retry_seconds,
        min_free_mem_gb,
        "?" if avail_gb is None else f"{avail_gb:.2f}",
        max_load_per_cpu,
        "?" if norm_load is None else f"{norm_load:.2f}",
    )
    raise task.retry(countdown=retry_seconds)


def _is_canceled_result(result_id):
    if not result_id:
        return False
    Result = apps.get_model("maxquant", "Result")
    return Result.objects.filter(pk=result_id, cancel_requested_at__isnull=False).exists()


def _terminate_process_group(proc, grace_seconds=5):
    if proc is None:
        return
    try:
        os.killpg(proc.pid, signal.SIGTERM)
    except ProcessLookupError:
        return
    except Exception as exc:
        logging.warning("Failed to SIGTERM process group for pid=%s: %s", proc.pid, exc)
        return

    deadline = time.monotonic() + max(0, grace_seconds)
    while time.monotonic() < deadline:
        if proc.poll() is not None:
            return
        time.sleep(0.2)

    try:
        os.killpg(proc.pid, signal.SIGKILL)
    except ProcessLookupError:
        return
    except Exception as exc:
        logging.warning("Failed to SIGKILL process group for pid=%s: %s", proc.pid, exc)


def _run_cancelable_shell_command(cmd, kind, result_id=None):
    poll_seconds = max(0.2, _safe_float("CANCEL_POLL_SECONDS", 2.0))
    kill_grace_seconds = _safe_int("CANCEL_KILL_GRACE_SECONDS", 5)
    try:
        proc = subprocess.Popen(
            cmd,
            shell=True,
            executable="/bin/bash",
            preexec_fn=os.setsid,
        )
    except Exception as exc:
        logging.exception("[%s] Failed to start command: %s", kind, exc)
        return 1

    logging.info("[%s] started pid=%s", kind, proc.pid)
    while True:
        rc = proc.poll()
        if rc is not None:
            logging.info("[%s] finished pid=%s rc=%s", kind, proc.pid, rc)
            return rc

        if _is_canceled_result(result_id):
            logging.info(
                "[%s] cancel requested during execution; terminating pid=%s",
                kind,
                proc.pid,
            )
            _terminate_process_group(proc, grace_seconds=kill_grace_seconds)
            return -1

        time.sleep(poll_seconds)


@shared_task(bind=True, max_retries=None)
def rawtools_metrics(
    self, raw, output_dir, arguments=None, rerun=False, result_id=None
):
    if _is_canceled_result(result_id):
        logging.info("[rawtools_metrics] canceled before start (result_id=%s)", result_id)
        return
    _defer_if_busy(
        task=self,
        kind="rawtools_metrics",
        min_free_mem_gb=_safe_float("MIN_FREE_MEM_GB_RAWTOOLS", 2),
        max_load_per_cpu=_safe_float("MAX_LOAD_PER_CPU_RAWTOOLS", 0.95),
    )
    cmd = rawtools_metrics_cmd(
        raw=raw, output_dir=output_dir, rerun=rerun, arguments=arguments
    )
    if cmd is not None:
        if _is_canceled_result(result_id):
            logging.info(
                "[rawtools_metrics] canceled before execution (result_id=%s)",
                result_id,
            )
            return
        logging.info(f"[rawtools_metrics] {cmd}")
        print(f"[rawtools_metrics] {cmd}")
        _run_cancelable_shell_command(
            cmd, kind="rawtools_metrics", result_id=result_id
        )


@shared_task(bind=True, max_retries=None)
def rawtools_qc(self, input_dir, output_dir, rerun=False, result_id=None):
    if _is_canceled_result(result_id):
        logging.info("[rawtools_qc] canceled before start (result_id=%s)", result_id)
        return
    _defer_if_busy(
        task=self,
        kind="rawtools_qc",
        min_free_mem_gb=_safe_float("MIN_FREE_MEM_GB_RAWTOOLS", 2),
        max_load_per_cpu=_safe_float("MAX_LOAD_PER_CPU_RAWTOOLS", 0.95),
    )
    cmd = rawtools_qc_cmd(input_dir=input_dir, output_dir=output_dir, rerun=rerun)
    if cmd is not None:
        if _is_canceled_result(result_id):
            logging.info(
                "[rawtools_qc] canceled before execution (result_id=%s)", result_id
            )
            return
        logging.info(f"[rawtools_qc] {cmd}")
        print(f"[rawtools_qc] {cmd}")
        _run_cancelable_shell_command(cmd, kind="rawtools_qc", result_id=result_id)


@shared_task(bind=True, max_retries=None)
def run_maxquant(self, raw_file, params, rerun=False, result_id=None):
    if _is_canceled_result(result_id):
        logging.info("[run_maxquant] canceled before start (result_id=%s)", result_id)
        return
    _defer_if_busy(
        task=self,
        kind="run_maxquant",
        min_free_mem_gb=_safe_float("MIN_FREE_MEM_GB_MAXQUANT", 8),
        max_load_per_cpu=_safe_float("MAX_LOAD_PER_CPU_MAXQUANT", 0.85),
    )
    if _is_canceled_result(result_id):
        logging.info(
            "[run_maxquant] canceled before execution (result_id=%s)", result_id
        )
        return
    mq = MaxquantRunner(verbose=True, **params)
    logging.info(f"[run_maxquant] raw_file={raw_file} params={params} rerun={rerun}")
    print(f"[run_maxquant] raw_file={raw_file} params={params} rerun={rerun}")
    mq.run(raw_file, rerun=rerun)
