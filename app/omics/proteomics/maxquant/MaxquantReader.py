import pandas as pd
import logging
from pathlib import Path as P


MAXQUANT_STANDARDS = {
    "proteinGroups.txt": {
        "usecols": [
            0,
            1,
            2,
            3,
            4,
            5,
            6,
            7,
            8,
            9,
            13,
            14,
            15,
            16,
            17,
            18,
            19,
            20,
            21,
            22,
            23,
            24,
            25,
            26,
            27,
            28,
            29,
            30,
            31,
            55,
            57,
            58,
            59,
            60,
            61,
            62,
            63,
            64,
            65,
            66,
            67,
            68,
            69,
        ],
        "column_names": [
            "Protein IDs",
            "Majority protein IDs",
            "Peptide counts all",
            "Peptide counts (razor+unique)",
            "Peptide counts (unique)",
            "Fasta headers",
            "Number of proteins",
            "Peptides",
            "Razor + unique peptides",
            "Unique peptides",
            "Sequence coverage [%]",
            "Unique + razor sequence coverage [%]",
            "Unique sequence coverage [%]",
            "Mol. weight [kDa]",
            "Sequence length",
            "Sequence lengths",
            "Q-value",
            "Score",
            "Reporter intensity corrected 1",
            "Reporter intensity corrected 2",
            "Reporter intensity corrected 3",
            "Reporter intensity corrected 4",
            "Reporter intensity corrected 5",
            "Reporter intensity corrected 6",
            "Reporter intensity corrected 7",
            "Reporter intensity corrected 8",
            "Reporter intensity corrected 9",
            "Reporter intensity corrected 10",
            "Reporter intensity corrected 11",
            "Intensity",
            "MS/MS count",
            "Only identified by site",
            "Reverse",
            "Potential contaminant",
            "id",
            "Peptide IDs",
            "Peptide is razor",
            "Mod. peptide IDs",
            "Evidence IDs",
            "MS/MS IDs",
            "Best MS/MS",
            "Oxidation (M) site IDs",
            "Oxidation (M) site positions",
        ],
    }
}


class MaxquantReader:
    def __init__(self, standardize=True, remove_contaminants=True, remove_reverse=True):
        self.standards = MAXQUANT_STANDARDS
        self.standardize = standardize
        self.remove_con = remove_contaminants
        self.remove_rev = remove_reverse

    def read(self, fn):
        assert P(fn).is_file(), fn
        name = P(fn).name

        try:
            df = pd.read_csv(fn, sep="\t", low_memory=False, na_filter=None)
        except Exception as e:
            logging.warning(f"MaxQuantReader: {e}")
            return None

        if name == "proteinGroups.txt":
            return self.process_protein_groups(df)

        return df

    def process_protein_groups(
        self,
        df,
    ):

        standard_cols = [
            "Majority protein IDs",
            "Fasta headers",
            "Number of proteins",
            "Peptides",
            "Razor + unique peptides",
            "Unique peptides",
            "Sequence coverage [%]",
            "Unique + razor sequence coverage [%]",
            "Unique sequence coverage [%]",
            "Mol. weight [kDa]",
            "Sequence length",
            "Sequence lengths",
            "Q-value",
            "Score",
            "Intensity",
            "MS/MS count",
            "Only identified by site",
            "Reverse",
            "Potential contaminant",
            "id",
            "Peptide IDs",
            "Peptide is razor",
            "Mod. peptide IDs",
            "Evidence IDs",
            "MS/MS IDs",
            "Best MS/MS",
            "Oxidation (M) site IDs",
            "Oxidation (M) site positions",
        ]

        quant_cols = df.filter(regex="Reporter intensity corrected").columns.to_list()

        df = df[standard_cols + quant_cols].rename(
            columns={c: " ".join(i for i in c.split(" ")[:4]) for c in quant_cols}
        )

        if self.remove_con:
            df = df[df["Potential contaminant"] != "+"]
        if self.remove_rev:
            df = df[~df["Majority protein IDs"].str.contains("REV_")]

        return df
