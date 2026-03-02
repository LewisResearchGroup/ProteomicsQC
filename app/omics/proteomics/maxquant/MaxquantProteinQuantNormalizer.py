import pandas as pd
import numpy as np
import logging

from tqdm import tqdm
from pathlib import Path as P

from .MaxquantReader import MaxquantReader


class MaxquantProteinQuantNormalizer:
    def __init__(
        self,
        paths=None,
        map_to_tmt_channel=True,
        remove_contaminants=False,
        remove_reverse=False,
    ):
        """
        Path is a list of paths towards Maxquant results folders.
        They are expected to contain proteinGroups.txt file.
        The name of the folder is taken as RawName.

        It should be something like:

        .../SA001-A/proteinGroups.txt
        .../SA001-B/proteinGroups.txt

        Then the data in this file will be stored as RawFile=SA001-A, RawFile=SA001-B, etc.

        Usage example:

            mpqn = MaxquantProteinQuantNormalizer()
            mpqn.read(paths)
            df = mpqn.normalize(...)

        """

        self._reader = MaxquantReader(
            remove_contaminants=remove_contaminants, remove_reverse=remove_reverse
        )
        self.df_protein_groups = None
        if paths is not None:
            self._df_paths = paths_to_df(paths)
            self._read_protein_groups()
        self._map_to_tmt_channel = map_to_tmt_channel
        self._tmt_mapping = {
            f"Reporter intensity corrected {i}": f"{i:02.0f}" for i in range(1, 24)
        }

    def _read_protein_groups(self):
        data = []
        for path, rawfile in tqdm(self._df_paths[["Path", "RawFile"]].values):
            fn = P(path) / "proteinGroups.txt"
            if not fn.is_file():
                logging.warning(f"FileNotFound: {fn}")
                continue
            df = self._reader.read(P(path) / "proteinGroups.txt")
            df["RawFile"] = rawfile
            data.append(df)
        self.df_protein_groups = pd.concat(data).set_index("RawFile").reset_index()

    @staticmethod
    def normalize_func(df):
        df = df.replace(0, np.nan)
        df = df.apply(pd.to_numeric, errors="ignore")
        channels = df.columns.to_list()
        channels_except_first = channels[1:]
        # Didvide by column mean
        df = df / df.mean(skipna=True)
        # Fold change to reference channel (channel 1)
        df = df.divide(df["Reporter intensity corrected 1"].values, axis=0)
        # Log2(x) transformation
        df = df.applymap(np.log2)
        # Mean centering except first channel
        mean_values_by_row = df.loc[:, channels_except_first].mean(axis=1)
        df.loc[:, channels_except_first] = df.loc[:, channels_except_first].sub(
            mean_values_by_row, axis=0
        )
        return df.values

    def normalize(
        self,
        fmt="plex",
        protein_col="Majority protein IDs",
    ):
        """
        Applies normalization and returns normalized datafame in specific format.
        -----
         Args:
        - divide_by_column_mean: bool
            * divide intensities by column-wise mean
        - take_log: apply log1p transformation, devide_by_mean
            is applied before log-transformation if set to True.
        - normed:
            * None: Don't apply further normalization
            * diff_to_ref: Substract intensities of reference
            column (super-mix in channel 1).
            * fold_change: Divide by reference intensities.
        - drop_zero_q
        - melt: Return a melted DataFrame

        """

        df = self.df_protein_groups.set_index("RawFile").copy()

        intensity_cols = df.filter(
            regex="Reporter intensity corrected"
        ).columns.to_list()
        df = df[[protein_col] + intensity_cols]
        minimum_n_of_values = 3
        n_of_values = (df[intensity_cols] != 0).sum(axis=1)
        df = df[(df[intensity_cols] > 0).sum(axis=1) >= minimum_n_of_values]
        df = df[df["Reporter intensity corrected 1"] != 0]

        grps = df.groupby("RawFile")
        for raw_file in tqdm(df.index.unique()):
            df.loc[raw_file, intensity_cols] = self.normalize_func(
                df.loc[raw_file, intensity_cols]
            )

        max_occurence_of_raw_file = (
            df.reset_index().groupby(["RawFile", protein_col]).count().max().max()
        )
        if max_occurence_of_raw_file > 1:
            logging.warning(
                f"Found duplicated index (RawFile, {protein_col}) taking first"
            )
            df = (
                df.groupby(["RawFile", protein_col])
                .first()
                .reset_index(level=protein_col)
            )

        df = df.set_index(protein_col, append=True)
        df = df[intensity_cols[1:]]
        df = df.rename(columns=self._tmt_mapping)
        df.columns.name = "TMT_CHANNEL"

        if fmt == "plex":
            return df
        elif fmt == "sample":
            return df.unstack(protein_col).stack("TMT_CHANNEL")
        elif fmt == "long":
            return df.reset_index().melt(
                id_vars=["RawFile", protein_col],
                var_name="TMT_CHANNEL",
                value_name="PROTEIN_QUANT",
            )


def melt_protein_quant(df, id_vars=None, var_name="TMT"):
    if id_vars is None:
        id_vars = df.filter(regex="^(?!.*Reporter.*)").columns
    output = df.melt(id_vars=id_vars, var_name=var_name, value_name="ReporterIntensity")
    output["TMT"] = (
        output["TMT"].str.replace("Reporter intensity corrected ", "").astype(int)
    )
    return output


def log2p1(x):
    return np.log2(x + 1)


def paths_to_df(paths):
    df = pd.DataFrame({"Path": paths})
    df["Path"] = df.Path.apply(lambda x: P(x).resolve())
    df["RawFile"] = df.Path.apply(lambda x: P(x).name)
    return df
