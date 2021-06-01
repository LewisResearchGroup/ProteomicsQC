
import os
import logging
from os.path import dirname, isdir, join, isfile, basename
from celery import shared_task

import shutil

from lrg_omics.proteomics import MaxquantRunner

from lrg_omics.proteomics.quality_control.rawtools import rawtools_metrics_cmd, rawtools_qc_cmd


@shared_task
def rawtools_metrics(raw, output_dir, arguments=None, rerun=False):
    cmd = rawtools_metrics_cmd(raw=raw, 
            output_dir=output_dir, rerun=rerun, arguments=arguments)
    if cmd is not None: os.system(cmd)

@shared_task    
def rawtools_qc(input_dir, output_dir, rerun=False):                
    cmd = rawtools_qc_cmd(input_dir=input_dir, output_dir=output_dir, rerun=rerun)
    if cmd is not None: os.system(cmd)

@shared_task
def run_maxquant(raw_file, params, rerun=False):
    mq = MaxquantRunner(verbose=True, **params)
    mq.run(raw_file, rerun=rerun)

    

