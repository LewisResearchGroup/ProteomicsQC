import os
import hashlib
import shutil
import zipfile
import pandas as pd
import logging
import datetime

from functools import lru_cache

from io import BytesIO
from pathlib import Path as P
from glob import glob

from django.db import models
from django_currentuser.db.models import CurrentUserField
from django.dispatch import receiver
from django.utils import timezone
from django.conf import settings
from django.shortcuts import reverse
from django.utils.translation import ugettext_lazy as _
from django.utils.html import mark_safe

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
        if (
            self.raw_file.pipeline.maxquant_executable is None
            or self.raw_file.pipeline.maxquant_executable == ""
        ):
            return "maxquant"
        else:
            return f"mono {self.raw_file.pipeline.maxquant_executable}"

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
            raw_file = str(self.raw_fn)
            params = self.maxquant_parameters()
            run_maxquant.delay(raw_file, params, rerun=rerun)
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
        if rerun and os.path.isdir(out_dir):
            shutil.rmtree(out_dir)
        if rerun or (self.n_files_rawtools_qc == 0):
            rawtools_qc.delay(inp_dir, out_dir)
            logging.info("Submitted RawTools QC.")

    def run_rawtools_metrics(self, rerun=False):
        raw_fn, out_dir, args = (
            str(self.raw_file.path),
            str(self.output_dir_rawtools),
            self.pipeline.rawtools_args,
        )
        if rerun and os.path.isdir(out_dir):
            shutil.rmtree(out_dir)
        if rerun or (self.n_files_rawtools_metrics == 0):
            rawtools_metrics.delay(raw_fn, out_dir, args)
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

    @property
    def status_protein_quant_parquet(self):
        fn = self.protein_quant_fn
        if not fn.is_file():
            return "File not found"
        try:
            pd.read_parquet(fn)
            return "OK"
        except:
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


@receiver(models.signals.post_save, sender=Result)
def run_maxquant_after_save(sender, instance, created, *args, **kwargs):
    if created:
        instance.run()


@receiver(models.signals.post_delete, sender=Result)
def remove_maxquant_folders_after_delete(sender, instance, *args, **kwargs):
    result = instance
    if result.output_dir_exists:
        shutil.rmtree(result.path)
    if result.run_dir_exists:
        shutil.rmtree(result.run_dir)
    if result.protein_quant_fn.is_file():
        os.remove(result.protein_quant_fn)
