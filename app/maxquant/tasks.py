
import os
import logging
from os.path import dirname, isdir, join, isfile, basename
from celery import shared_task

import shutil

from lrg_omics.proteomics.pipelines.maxquant import run_maxquant as run_mq
from lrg_omics.proteomics.MaxQuantRunner import MaxQuantRunner

from lrg_omics.proteomics.quality_control.rawtools import rawtools_metrics_cmd, rawtools_qc_cmd

## Do NOT call print() inside a celery task!!!

@shared_task
def rawtools_metrics(raw, output_dir, rerun=False, arguments=None):
    cmd = rawtools_metrics_cmd(raw=raw, 
            output_dir=output_dir, rerun=rerun, arguments=arguments)
    print('RawTools Metrics command:', cmd)
    if cmd is not None: os.system(cmd)

@shared_task    
def rawtools_qc(input_dir, output_dir, rerun=False):                
    cmd = rawtools_qc_cmd(input_dir=input_dir, output_dir=output_dir, rerun=rerun)
    print('RawTools QC command:', cmd)
    if cmd is not None: os.system(cmd)

@shared_task
def run_maxquant(raw_file, params):
    mq = MaxQuantRunner(verbose=True, **params)
    mq.run(raw_file, rerun=True)
    

