import os
import logging
from os.path import isdir, join, isfile, basename
from celery import shared_task

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


@shared_task(bind=True, max_retries=None)
def rawtools_metrics(self, raw, output_dir, arguments=None, rerun=False):
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
        logging.info(f"[rawtools_metrics] {cmd}")
        print(f"[rawtools_metrics] {cmd}")
        os.system(cmd)


@shared_task(bind=True, max_retries=None)
def rawtools_qc(self, input_dir, output_dir, rerun=False):
    _defer_if_busy(
        task=self,
        kind="rawtools_qc",
        min_free_mem_gb=_safe_float("MIN_FREE_MEM_GB_RAWTOOLS", 2),
        max_load_per_cpu=_safe_float("MAX_LOAD_PER_CPU_RAWTOOLS", 0.95),
    )
    cmd = rawtools_qc_cmd(input_dir=input_dir, output_dir=output_dir, rerun=rerun)
    if cmd is not None:
        logging.info(f"[rawtools_qc] {cmd}")
        print(f"[rawtools_qc] {cmd}")
        os.system(cmd)


@shared_task(bind=True, max_retries=None)
def run_maxquant(self, raw_file, params, rerun=False):
    _defer_if_busy(
        task=self,
        kind="run_maxquant",
        min_free_mem_gb=_safe_float("MIN_FREE_MEM_GB_MAXQUANT", 8),
        max_load_per_cpu=_safe_float("MAX_LOAD_PER_CPU_MAXQUANT", 0.85),
    )
    mq = MaxquantRunner(verbose=True, **params)
    logging.info(f"[run_maxquant] raw_file={raw_file} params={params} rerun={rerun}")
    print(f"[run_maxquant] raw_file={raw_file} params={params} rerun={rerun}")
    mq.run(raw_file, rerun=rerun)
