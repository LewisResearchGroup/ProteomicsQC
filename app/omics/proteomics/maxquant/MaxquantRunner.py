import os
import shutil
from os.path import isfile, basename, join, abspath, isdir
from uuid import uuid1

from pathlib import Path as P
import logging

from ...common import maybe_create_symlink
from .MqparParser import MqparParser


class MaxquantRunner:
    def __init__(
        self,
        fasta_file,
        mqpar_file,
        maxquantcmd="maxquant",
        run_dir=None,
        out_dir=None,
        add_raw_name_to_outdir=False,
        add_uuid_to_rundir=False,
        sbatch_cmds=None,
        cleanup=False,
        verbose=False,
        output_dir=None,
        runtime='10:00:00',
    ):
        """
        Runs MaxQuant jobs using a mqpar.txt template,
        a fasta file, and a .RAW file as input. It
        performes the calculations in the run-directory and
        then moves the results to the output directory.
        It also creates a batch submission file for
        the slurm queing system.

        ARGS
        ----

        fasta_file: str|pathlib.Path, absolute path to a fasta file
        mqpar_file: str|pathlib.Path, absolute path to a mqpar.xml template file
        maxquantcmd: str, command to run maxquant
            - Example: '/usr/bin/mono ~/software/MaxQuant/bin/MaxQuantCmd.exe'
        run_dir: str|pathlib.Path, path to the run-directory
        out_dir: str|pathlib.Path, path to the output-diretory
        add_raw_name_to_outdir: bool, default=False
            * True: store files in a subdirectory of output-directory: <output-dir>/<name-of-raw-file>/
            * False: store files in output directory without sub-directory: <output-dir>/
        add_uuid_to_rundir: bool, default=False
        sbatch_cmds: additional commands to add to the sbatch.file
            - Example: 'conda activate myenv\\nMYENV=test'
        cleanup: bool, default=False
            * True: removes the files in the run directory when run finishes
            * False: keep the run files, e.g. for debugging
        time: str, default='5:00:00'
        """

        if output_dir is not None:
            logging.warning('"output_dir" is deprecated use "out_dir" instead.')
            if out_dir is None:
                out_dir = output_dir

        self._fasta = abspath(fasta_file)
        self._mqpar = abspath(mqpar_file)
        self._mqcmd = maxquantcmd
        self._run_dir = P(run_dir) if isinstance(run_dir, str) else run_dir
        self._tgt_dir = P(out_dir) if isinstance(out_dir, str) else out_dir
        self._add_raw_name_to_outdir = add_raw_name_to_outdir
        self._add_uuid_to_rundir = add_uuid_to_rundir
        self._runtime = runtime

        if sbatch_cmds is None:
            sbatch_cmds = ""

        self._sbatch_cmds = [i.strip() for i in sbatch_cmds.split(";")]
        self._cleanup = cleanup
        self._verbose = verbose

        self.last_run_dir = None
        self.last_out_dir = None

        assert isfile(self._fasta), self._fasta
        assert isfile(self._mqpar), self._mqpar

    def run(
        self,
        raw_file,
        cold_run=False,
        rerun=False,
        submit=False,
        run=True,
        with_time=True,
        runtime=None,
    ):
        """
        Executes MaxQuant run or only prepares output and run directories.
        ARGS
        ----
        raw_file: str|pathlib.Path, path to a proteomics.raw file
        cold_run: bool, default=False
            * True: do not execute, only return the commands
            * False:
        rerun: bool, default=False
            * True: execute even if output-dir is already present, and replace results
            * False: ommit run, if output-dir exists
        submit: bool, default=False
            * True: submit batch-file to slurm queing system
            * False: do not submit batch-file
        with_time: bool, default=True
            * True: time the MaxQuant run using /usr/bin/time
            * False: do not time MaxQuant execution
        """
        raw_file = abspath(raw_file)
        if raw_file.lower().endswith(".raw"):
            raw_label = basename(raw_file[:-4])
        else:
            raw_label = basename(raw_file)
        if self._run_dir is None:
            run_dir = abspath(join(os.getcwd(), "run"))
        else:
            run_dir = abspath(self._run_dir)
        if self._tgt_dir is None:
            tgt_dir = abspath(join(os.getcwd(), "out"))
        else:
            tgt_dir = abspath(self._tgt_dir)
        if self._add_raw_name_to_outdir:
            tgt_dir = join(tgt_dir, raw_label)
        if runtime is None:
            runtime = self._runtime

        run_id = f"{raw_label}"

        if self._add_uuid_to_rundir:
            run_id = str(uuid1())[:8] + f"-{run_label}"
            run_dir = join(run_dir, run_id)

        self.last_run_dir = run_dir
        self.last_out_dir = tgt_dir

        if isdir(run_dir):
            if not rerun:
                logging.warning(f"Run directory exists ({run_dir}).")
                return None
            else:
                shutil.rmtree(run_dir)

        if isdir(tgt_dir):
            if not rerun:
                logging.warning(
                    f"Output directory exists ({tgt_dir}) omitting raw file: {raw_file}."
                )
                return None
            else:
                shutil.rmtree(tgt_dir)

        run_raw_ref = P(run_dir) / P(raw_file).name
        run_mqpar = P(run_dir) / P(self._mqpar).name
        run_sbatch = P(run_dir) / "run.sbatch"

        if with_time:
            time_cmd = f'/usr/bin/time -o {run_dir}/time.txt -f "%E" '
        else:
            time_cmd = "touch time.txt;"

        # these are just the commands
        # directories will be created later
        cmds = [
            f"cd {run_dir}",
            "sleep 10",
            f"{time_cmd} {self._mqcmd} {run_mqpar} 1>maxquant.out 2>maxquant.err",
            f"if [ ! -d {run_dir}/combined ]; then mkdir {run_dir}/combined ; fi",
            f"if [ ! -d {run_dir}/combined/txt ]; then mkdir {run_dir}/combined/txt ; fi",
            f"cp time.txt maxquant.err maxquant.out {run_mqpar} {run_dir}/combined/txt/",
            f"mv {run_dir}/combined/txt/* {tgt_dir}",
            f"rm -rf {run_dir}/combined",
            f"rm -rf {run_dir}/{raw_label}",
            f"ls -artlh {tgt_dir}"
        ]

        if self._cleanup:
            cmds.append(f"rm -r {run_dir}")

        if not cold_run:
            os.makedirs(run_dir, exist_ok=True)
            os.makedirs(tgt_dir, exist_ok=True)
            # maybe_create_symlink(raw_file, run_raw_ref)
            shutil.copy2(raw_file, run_raw_ref) # prevent errors with symlinks in newer MaxQuant versions

        if self._verbose or cold_run:
            print(f"Create run directory: {run_dir}")
            print(f"Create target directory: {tgt_dir}")
            print(f"Create link: {raw_file} {run_raw_ref}")
            print("Commands:")
            for cmd in cmds:
                print('\t'+cmd)

        create_mqpar(
            self._mqpar,
            run_raw_ref,
            self._fasta,
            raw_label,
            fn=run_mqpar,
            cold_run=cold_run,
        )

        gen_sbatch_file(
            self._sbatch_cmds + cmds,
            jobname=run_id,
            fn=run_sbatch,
            cold_run=cold_run,
            submit=submit,
            maxquantcmd=self._mqcmd,
            rundir=run_dir,
            runtime=runtime
        )

        cmds = "; ".join(cmds)

        if run and not submit:
            print(f"Running run_id={run_id} in {run_dir}")
            os.system(cmds)

        return cmds


def gen_sbatch_file(
    commands,
    jobname,
    submit=False,
    fn="run.sbatch",
    cold_run=False,
    maxquantcmd="maxqant",
    rundir=None,
    runtime="10:00:00"
):
    cmds_txt = "\n\n".join(commands)
    txt = f"""#!/bin/bash
#SBATCH --time={runtime}
#SBATCH --ntasks-per-node=1
#SBATCH --nodes=1
#SBATCH --mem=5000
#SBATCH -J {jobname}
#SBATCH -e {rundir}/slurm.err
#SBATCH -o {rundir}/slurm.out

which mono
mono --version

which {maxquantcmd}
{maxquantcmd} --version 2>&1

{cmds_txt}
"""
    if not cold_run:
        with open(fn, "w") as file:
            file.write(txt)
        if submit:
            os.system(f"sbatch {fn}")
    else:
        print(txt)


def create_mqpar(mqpar_temp, raw, fasta, label, fn="mqpar.xml", cold_run=False):

    mqpar = MqparParser()
    string = (
        mqpar.read(mqpar_temp)
        .as_template()
        ._content.replace("__RAW__", str(raw))
        .replace("__FASTA__", str(fasta))
        .replace("__LABEL__", str(label))
    )
    if not cold_run:
        with open(fn, "w") as file:
            file.write(string)
    else:
        print(f"Create {fn}:\n", string)
