import os
import pandas as pd

from os.path import isdir, isfile, dirname, abspath, join
from glob import glob
from pathlib import Path as P

from ...common import relative_path, maybe_create_symlink, get_all_raws


def collect_rawtools_qc_data(root_path):
    """
    Finds all QcDataTable.csv file in subfolders of root_path
    and returns them as a concatenated dataframe.
    """
    paths = glob(f"{root_path}/**/QcDataTable.csv", recursive=True)
    dfs = [pd.read_csv(p) for p in paths]
    if len(dfs) == 0:
        return None
    df = pd.concat(dfs, sort=False)
    df.DateAcquired = pd.to_datetime(df.DateAcquired)
    df.sort_values("DateAcquired", inplace=True, ascending=False)
    df.index = range(len(df))
    return df


def update_rawtools_qc_data(raw_root, output_root=None, run=False, verbose=False):
    """
    Finds all files ending on .raw in subfolders of raw_root and runs
    the rawtools_cmds() on them. If run is False it returns a list of
    command-line commands that would be run.
    """
    commands = []
    if verbose:
        print("Updating rawtools QC data:")
    for raw_file in get_all_raws(raw_root):
        if verbose:
            print(f" {raw_file}")
        cmds = rawtools_cmds(
            raw_file,
            raw_root=raw_root,
            output_root=output_root,
            run=run,
            verbose=verbose,
        )
        commands.extend(cmds)
    if not run:
        return commands


def rawtools_cmds(
    raw, raw_root, output_root=None, force=False, run=False, verbose=False
):
    """
    Returns commands to run, if target folder is not already present.
    Otherwise, an empty list is returned.
    """
    if output_root is None:
        output_root = raw_root

    raw_relative = relative_path(raw, raw_root)
    raw_basename = os.path.basename(raw)
    output_raw = abspath(P(output_root) / P(raw_relative))
    output_dir = dirname(output_raw)

    if verbose:
        print("Generating raw tools commmands")
        print(" raw:", raw)
        print(" raw_root", raw_root)
        print(" raw_relative:", raw_relative)
        print(" raw_basename:", raw_basename)
        print(" output_dir:", output_dir)

    if (isdir(output_dir) and rawtools_output_files_exist(output_dir)) and not force:
        if verbose:
            print("Skipping:", output_dir)
        return []

    os.makedirs(output_dir, exist_ok=True)
    maybe_create_symlink(abspath(raw), output_dir / P(os.path.basename(raw)))
    commands = [
        rawtools_qc_cmd(output_dir, output_dir),
        rawtools_metrics_cmd(output_raw, output_dir),
    ]
    if verbose:
        for cmd in commands:
            print(f" CMD: {cmd}")
    if run:
        if verbose:
            print("Running: ", output_dir)
        for cmd in commands:
            if verbose:
                print("Command:", cmd)
            os.system(cmd)
    return commands


def rawtools_metrics_cmd(
    raw, output_dir, rerun=False, arguments="-p -q -x -u -l -m -r TMT11 -chro 12TB"
):
    """
    Generates command to run rawtools parse to generate
    the RawTools files:
        *_Matrix.txt
        *_Metrics.txt
        *_Ms2_TIC_chromatogram.txt
        *.mgf
    """
    raw = abspath(str(raw))
    output_dir = abspath(str(output_dir))
    raw_basename = os.path.basename(raw)
    os.makedirs(output_dir, exist_ok=True)
    if not isfile(join(output_dir, f"{raw_basename}_Matrix.txt")) or rerun:
        cmd = (
            f'cd "{output_dir}"; rawtools.sh -f "{raw}" -o "{output_dir}" '
            f"{arguments}  2>rawtools_metrics.err 1>rawtools_metrics.out"
        )
    else:
        cmd = None
    return cmd


def rawtools_qc_cmd(input_dir, output_dir, rerun=False):
    """
    Generates command to run rawtools quality control to
    generate the file QcDataTable.csv.
    """
    input_dir = abspath(str(input_dir))
    output_dir = abspath(str(output_dir))
    os.makedirs(output_dir, exist_ok=True)
    if not isfile(join(output_dir, "QcDataTable.csv")) or rerun:
        cmd = (
            f'cd "{output_dir}"; rawtools.sh -d "{input_dir}" '
            f'-qc "{output_dir}" 2>rawtools_qc.err 1>rawtools_qc.out'
        )
    else:
        cmd = None
    return cmd


def rawtools_output_files_exist(path):
    """
    Checks whether RawTools output exists for all .raw files
    in a directory.
    Returns
        True - if all outputfiles exist for all .raw files.
        False - if at least one RawTools output file is missing.
    """
    raw_files = glob(str(path) + "/*.raw")
    assert len(raw_files) > 0
    for raw_file in raw_files:
        mgf = raw_file + ".mgf"
        matrix = raw_file + "_Matrix.txt"
        metrics = raw_file + "_Metrics.txt"
        tic = raw_file + "_Ms2_TIC_chromatogram.txt"
        files = [mgf, matrix, metrics, tic]
        exist = [isfile(f) for f in files]
        if not all(exist):
            return False
    return True
