import pandas as pd

import requests
import json
import logging

from tqdm import tqdm
from pathlib import Path as P


class ProteomicsQC:
    """
    Python API to interact with the Proteomics-QC pipeline server (PQC).

    Parameters
    ----------
    host :  str, default='http://localhost:8000'
    pid : str, default=None
    uid : str, default=None
    project_slug : str, default=None
    pipeline_slug : str, default=None

    Methods
    -------
    get_projects() - Returns a dataframe with information about all
        available projects on server.
    get_pipelines(project_slug) - Returns list of pipelines in
        project space
    get_qc_data(data_range=30) - Downloads the Quality Control data
        for the last <data_range> files in the currently selected
        pipeline.
    upload_raw(fns=[list-of-local-path-to-raw-file]) - Upload raw files
        to currently selected pipeline.
    download_maxquant_data() - ...
    flag(fns=[list-of-local-path-to-raw-file]) - Set flags for files
        in list in currently selected pipeline.
    unflag(fns=[list-of-local-path-to-raw-file]) - Unset flags for files
        in currently selected pipeline.

    Example
    -------
    pqc = ProteomicsQC(
            host='https://proteomics.resistancedb.org',
            uid='your-user-uuid',         # Optional, required for upload of RAW files
            uid='your-pipeline-uuid'      # Optional, required for upload of RAW files
            project_slug='project-slug'
            pipeline_slug='pipeline-slug'
    )

    pqc.get_projects()

    pqc.get_pipelines(project='lsarp')

    pqc.get_qc_data(data_range=100)

    pqc.upload_raw(fns=[list-of-filenames])  # Requires uid and pid set

    pqc.flag(fns=[list-of-filenames])

    pqc.unflag(fns=[list-of-filenames])

    """

    def __init__(
        self,
        host="https://localhost:8000",
        pid=None,
        uid=None,
        verbose=False,
        project_slug=None,
        pipeline_slug=None,
    ):

        self._host = host
        self._pipeline_uuid = pid
        self._user_uuid = uid
        self._verbose = verbose
        self._projects = None
        self._project_slug = project_slug
        self._pipeline_slug = pipeline_slug
        self._qc_data = None

    def get_projects(self):
        url = f"{self._host}/api/projects"
        r = requests.post(url).json()
        self.projects = pd.DataFrame(r)
        return self.projects

    def get_pipelines(self, project_slug):
        url = f"{self._host}/api/pipelines"
        headers = {"Content-type": "application/json"}
        data = json.dumps(dict(project=project_slug))
        r = requests.post(url, data=data, headers=headers).json()
        return pd.DataFrame(r)

    def get_qc_data(
        self, project_slug=None, pipeline_slug=None, columns=None, data_range=30
    ):
        url = f"{self._host}/api/qc-data"
        headers = {"Content-type": "application/json"}

        if self._verbose:
            print(url)
        if project_slug is None:
            project_slug = self._project_slug
        if pipeline_slug is None:
            pipeline_slug = self._pipeline_slug

        data_dict = dict(
            project=project_slug, pipeline=pipeline_slug, data_range=data_range
        )
        if columns is not None:
            data_dict["columns"] = columns

        data = json.dumps(data_dict)
        r = requests.post(url, data=data, headers=headers).json()
        df = pd.DataFrame(r)
        df["DateAcquired"] = pd.to_datetime(df["DateAcquired"])
        return df

    def upload_raw(self, fns):
        if isinstance(fns, str):
            fns = [fns]
        url = f"{self._host}/api/upload/raw"
        pid = self._pipeline_uuid
        uid = self._user_uuid

        if (pid is None) or (uid is None):
            logging.error(
                "Please, initiate D3PO with user_uuid "
                "and pipeline_uuid to submit RAW files."
            )

        for fn in tqdm(fns):
            with open(fn, "rb") as file:
                files = {"orig_file": file}
                data = {"pid": pid, "uid": uid}
                if self._verbose:
                    print(f"Uploading {fn}...", end="")
                r = requests.post(url, files=files, data=data)
                status_code = r.status_code
                if self._verbose:
                    if status_code == 201:
                        print(" success")
                    else:
                        print(f" failed ([{status_code}])")

    def download_maxquant_data(self, project_slug, pipeline_slug, filename):
        url = f"{self._host}/api/download"

    def flag(self, fns):
        self.change_flags(fns, "create")

    def unflag(self, fns):
        self.change_flags(fns, "delete")

    def change_flags(self, fns, how):
        if isinstance(fns, str):
            fns = [fns]
        fns = [P(fn).with_suffix(".raw").name for fn in fns]
        project_slug = self._project_slug
        pipeline_slug = self._pipeline_slug
        url = f"{self._host}/api/flag/{how}"
        data = {
            "project": project_slug,
            "pipeline": pipeline_slug,
            "uid": self._user_uuid,
            "raw_files": fns,
        }
        response = requests.post(url, data=data)

    def rawfile(self, fns, action):
        if isinstance(fns, str):
            fns = [fns]
        fns = [P(fn).with_suffix(".raw").name for fn in fns]
        project_slug = self._project_slug
        pipeline_slug = self._pipeline_slug
        url = f"{self._host}/api/rawfile"
        data = {
            "project": project_slug,
            "pipeline": pipeline_slug,
            "uid": self._user_uuid,
            "raw_files": fns,
            "action": action,
        }
        response = requests.post(url, data=data)
        return response.json()
