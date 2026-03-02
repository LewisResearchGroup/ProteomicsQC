import os
from datetime import date
from glob import glob


def maybe_create_symlink(src, dst):
    if not os.path.isfile(dst):
        os.symlink(src, dst)


def today():
    return date.today().strftime("%y%m%d")


def maybe_make_dir_and_chdir(path):
    os.makedirs(path, exist_ok=True)
    os.chdir(path)


def get_all_raws(directory, recursive=True):
    """
    Searches a directory for *.raw files and returns a list
    with the paths to the files including the file name.
    """
    raws = glob(str(directory) + "/**/*.raw", recursive=recursive)
    return raws


def relative_path(path, root_path):
    return os.path.abspath(str(path)).replace(os.path.abspath(str(root_path)), "")[1:]
