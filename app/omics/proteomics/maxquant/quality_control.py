# Quality control for MaxQuant output
import pandas as pd
import numpy as np
import logging

from pathlib import Path as P
from glob import glob
from os.path import dirname, isdir, isfile, join, abspath

summary_columns_v1 = [
    "MS",
    "MS/MS",
    "MS3",
    "MS/MS Submitted",
    "MS/MS Identified",
    "MS/MS Identified [%]",
    "Peptide Sequences Identified",
    "Av. Absolute Mass Deviation [mDa]",
    "Mass Standard Deviation [mDa]"
]

summary_columns_v2 = [
    "MS",
    "MS/MS",
    "MS3",
    "MS/MS submitted",
    "MS/MS identified",
    "MS/MS identified [%]",
    "Peptide sequences identified",
    "Av. absolute mass deviation [mDa]",
    "Mass standard deviation [mDa]"
]

expected_columns = [
    "N_protein_groups",
    "N_protein_true_hits",
    "N_protein_potential_contaminants",
    "N_protein_reverse_seq",
    "Protein_mean_seq_cov [%]",
    "TMT1_missing_values",
    "TMT2_missing_values",
    "TMT3_missing_values",
    "TMT4_missing_values",
    "TMT5_missing_values",
    "TMT6_missing_values",
    "TMT7_missing_values",
    "TMT8_missing_values",
    "TMT9_missing_values",
    "TMT10_missing_values",
    "TMT11_missing_values",
    "N_peptides",
    "N_peptides_potential_contaminants",
    "N_peptides_reverse",
    "Oxidations [%]",
    "N_missed_cleavages_total",
    "N_missed_cleavages_eq_0 [%]",
    "N_missed_cleavages_eq_1 [%]",
    "N_missed_cleavages_eq_2 [%]",
    "N_missed_cleavages_gt_3 [%]",
    "N_peptides_last_amino_acid_K [%]",
    "N_peptides_last_amino_acid_R [%]",
    "N_peptides_last_amino_acid_other [%]",
    "Mean_parent_int_frac",
    "Uncalibrated - Calibrated m/z [ppm] (ave)",
    "Uncalibrated - Calibrated m/z [ppm] (sd)",
    "Uncalibrated - Calibrated m/z [Da] (ave)",
    "Uncalibrated - Calibrated m/z [Da] (sd)",
    "Peak Width(ave)",
    "Peak Width (std)",
    "qc1_peptide_charges",
    "N_qc1_missing_values",
    "reporter_intensity_corrected_qc1_ave",
    "reporter_intensity_corrected_qc1_sd",
    "reporter_intensity_corrected_qc1_cv",
    "calibrated_retention_time_qc1",
    "retention_length_qc1",
    "N_of_scans_qc1",
    "qc2_peptide_charges",
    "N_qc2_missing_values",
    "reporter_intensity_corrected_qc2_ave",
    "reporter_intensity_corrected_qc2_sd",
    "reporter_intensity_corrected_qc2_cv",
    "calibrated_retention_time_qc2",
    "retention_length_qc2",
    "N_of_scans_qc2",
    "N_of_Protein_qc_pepts",
    "N_Protein_qc_missing_values",
    "reporter_intensity_corrected_Protein_qc_ave",
    "reporter_intensity_corrected_Protein_qc_sd",
    "reporter_intensity_corrected_Protein_qc_cv",
]


def collect_maxquant_qc_data(root_path, force_update=False, from_csvs=True):
    """
    Generate MaxQuant quality control in all
    sub-directories of `root_path` where summary.txt is found.
    """
    paths = [
        abspath(dirname(i)) for i in glob(f"{root_path}/**/summary.txt", recursive=True)
    ]
    if len(paths) == 0:
        return None
    if from_csvs:
        dfs = [maxquant_qc_csv(path, force_update=force_update) for path in paths]
    else:
        dfs = [maxquant_qc(path) for path in paths]
    return pd.concat(dfs, sort=False).reset_index(drop=True)


def maxquant_qc_csv(
    txt_path,
    out_fn="maxquant_quality_control.csv",
    force_update=False,
):
    abs_path = join(txt_path, out_fn)
    if isfile(abs_path) and not force_update:
        df = pd.read_csv(abs_path)
    else:
        df = maxquant_qc(txt_path)
        if df is None:
            logging.warning(f"maxquant_qc_csv(): No data generated from {txt_path}")
            return None
        if out_fn is not None:
            df.to_csv(abs_path, index=False)
    df = df.reindex(columns=expected_columns)
    return df


def maxquant_qc(txt_path, protein=None, pept_list=None):
    """
    Runs all MaxQuant quality control functions
    and returns a concatenated pandas.Series()
    object including meta data.
    Args:
        txt_path: path with MaxQuant txt output.
        protein: list with protein name (only the first one will be processed). If None then protein = ['BSA']
        pept_list: list with peptides names (only the first six will be processed). If None then
        pept_list = ["HVLTSIGEK", "LTILEELR", "ATEEQLK", "AEFVEVTK", "QTALVELLK", "TVMENFVAFVDK"]
    """
    txt_path = P(abspath(txt_path))
    meta_json = txt_path / P("meta.json")
    assert isdir(txt_path), f"Path does not exists: {txt_path}"
    dfs = []
    if isfile(meta_json):
        meta = pd.read_json(meta_json, typ="series")
        dfs.append(meta)
    for df in [
        maxquant_qc_summary(txt_path),
        maxquant_qc_protein_groups(txt_path, protein),
        maxquant_qc_peptides(txt_path),
        maxquant_qc_msmScans(txt_path),
        maxquant_qc_evidence(txt_path, pept_list),
    ]:
        dfs.append(df)
    if len(dfs) == 0:
        return None
    df = pd.concat(dfs, sort=False).to_frame().T
    df["RUNDIR"] = str(txt_path)

    if "MS/MS Submitted" in df.columns:
        df = df.reindex(columns=["Date"] + summary_columns_v1 + expected_columns)
    elif "MS/MS submitted" in df.columns:
        df = df.reindex(columns=["Date"] + summary_columns_v2 + expected_columns)
    return df.infer_objects()


def maxquant_qc_summary(txt_path):
    filename = "summary.txt"

    df_summary = pd.read_csv(txt_path / P(filename), sep="\t", nrows=1).T[0]

    if "MS/MS Submitted" in df_summary.index:
        return df_summary[summary_columns_v1]
    elif "MS/MS submitted" in df_summary.index:
        return df_summary[summary_columns_v2]

def maxquant_qc_protein_groups(txt_path, protein=None):
    filename = "proteinGroups.txt"
    df = pd.read_csv(txt_path / P(filename), sep="\t")
    n_contaminants = df["Potential contaminant"].eq("+").sum()
    n_reverse = df["Reverse"].fillna("-").eq("+").sum()
    n_true_hits = len(df) - (n_contaminants + n_reverse)
    mean_sequence_coverage = df[
        (df["Potential contaminant"].isnull()) & (df["Reverse"].isnull())
        ]["Sequence coverage [%]"].mean(skipna=True)

    df1 = df[
        (df["Potential contaminant"] != "+")
        & (df.Reverse != "+")
        & (df["Majority protein IDs"] != "QC1|Peptide1")
        & (df["Majority protein IDs"] != "QC2|Peptide2")
        & (df["Only identified by site"] != "+")
        ]

    m_v = (
        df1.filter(regex="Reporter intensity corrected")
        .replace(np.nan, 0)
        .isin([0])
        .sum()
        .to_list()
    )

    result = {
        "N_protein_groups": len(df),
        "N_protein_true_hits": n_true_hits,
        "N_protein_potential_contaminants": n_contaminants,
        "N_protein_reverse_seq": n_reverse,
        "Protein_mean_seq_cov [%]": mean_sequence_coverage,
    }

    if len(m_v) != 0:
        l_1 = [
            "TMT1_missing_values",
            "TMT2_missing_values",
            "TMT3_missing_values",
            "TMT4_missing_values",
            "TMT5_missing_values",
            "TMT6_missing_values",
            "TMT7_missing_values",
            "TMT8_missing_values",
            "TMT9_missing_values",
            "TMT10_missing_values",
            "TMT11_missing_values",
        ]
        l_2 = m_v + (11 - len(m_v)) * ["not detected"]
        dic_m_v = dict(zip(l_1, l_2))
        result.update(dic_m_v)

    if protein is None:
        protein = [
            "QC3_BSA"
        ]  # name must be unique, otherwise generates a df with more than one row and ends up in error

    df_qc3 = df[df["Protein IDs"].str.contains(protein[0], na=False, case=True)]

    if not df_qc3[df_qc3.Intensity == df_qc3.Intensity.max()].empty:
        df_qc3 = df_qc3[df_qc3.Intensity == df_qc3.Intensity.max()]

    if not df_qc3.empty:

        ave = float(df_qc3.filter(regex="Reporter intensity corrected").mean(axis=1))
        std = float(df_qc3.filter(regex="Reporter intensity corrected").std(axis=1, ddof=0))

        if ave != 0:
            cv = std / ave * 100
        else:
            cv = None

        dict_info_qc3 = {
            "Protein_qc": protein[0],
            "N_of_Protein_qc_pepts": ";".join(
                [str(x) for x in df_qc3["Peptide counts (all)"].to_list()]
            ),
            "N_Protein_qc_missing_values": ";".join(
                [
                    str(x)
                    for x in df_qc3.filter(regex="Reporter intensity corrected")
                .replace(np.nan, 0)
                .isin([0])
                .sum()
                .to_list()
                ]
            ),
            "reporter_intensity_corrected_Protein_qc_ave": ave,
            "reporter_intensity_corrected_Protein_qc_sd": std,
            "reporter_intensity_corrected_Protein_qc_cv": cv,
        }

        result.update(dict_info_qc3)

    else:
        dict_info_qc3 = {
            "Protein_qc": "not detected",
            "N_of_Protein_qc_pepts": "not detected",
            "N_Protein_qc_missing_values": "not detected",
            "reporter_intensity_corrected_Protein_qc_ave": "not detected",
            "reporter_intensity_corrected_Protein_qc_sd": "not detected",
            "reporter_intensity_corrected_Protein_qc_cv": "not detected",
        }
        result.update(dict_info_qc3)

    return pd.Series(result)


def maxquant_qc_peptides(txt_path):
    filename = "peptides.txt"
    df = pd.read_csv(txt_path / P(filename), sep="\t")
    max_missed_cleavages = 3
    last_amino_acids = ["K", "R"]
    n_peptides = len(df)
    n_contaminants = df["Potential contaminant"].eq("+").sum()
    n_reverse = df["Reverse"].fillna("-").eq("+").sum()
    ox_pep_seq = len(df) - df["Oxidation (M) site IDs"].isnull().sum()
    ox_pep_seq_percent = ox_pep_seq / n_peptides * 100
    result = {
        "N_peptides": n_peptides,
        "N_peptides_potential_contaminants": n_contaminants,
        "N_peptides_reverse": n_reverse,
        "Oxidations [%]": ox_pep_seq_percent,
        "N_missed_cleavages_total": (df["Missed cleavages"] != 0).sum(),
    }
    for n in range(max_missed_cleavages):
        result[f"N_missed_cleavages_eq_{n} [%]"] = (
            (df["Missed cleavages"] == n).sum() / n_peptides * 100
        )
    result[f"N_missed_cleavages_gt_{max_missed_cleavages} [%]"] = (
        (df["Missed cleavages"] > max_missed_cleavages).sum() / n_peptides * 100
    )
    for amino in last_amino_acids:
        result[f"N_peptides_last_amino_acid_{amino} [%]"] = (
            df["Last amino acid"].eq(amino).sum() / n_peptides * 100
        )
    result["N_peptides_last_amino_acid_other [%]"] = (
        (~df["Last amino acid"].isin(last_amino_acids)).sum() / n_peptides * 100
    )
    return pd.Series(result).round(2)


def maxquant_qc_msmScans(txt_path, t0=None, tf=None):
    filename = "msmsScans.txt"
    df = pd.read_csv(txt_path / P(filename), sep="\t")
    if t0 is None:
        t0 = df["Retention time"].min()
    if tf is None:
        tf = df["Retention time"].max()
    mean_parent_int_frac = df["Parent intensity fraction"].mean(skipna=True)
    results = {"Mean_parent_int_frac": mean_parent_int_frac}
    return pd.Series(results).round(2)


def maxquant_qc_evidence(txt_path, pept_list=None):
    filename = "evidence.txt"
    df = pd.read_csv(txt_path / P(filename), sep="\t")

    result = {
        "Uncalibrated - Calibrated m/z [ppm] (ave)": df[
            "Uncalibrated - Calibrated m/z [ppm]"
        ].mean(skipna=True),
        "Uncalibrated - Calibrated m/z [ppm] (sd)": df[
            "Uncalibrated - Calibrated m/z [ppm]"
        ].std(ddof=0, skipna=True),
        "Uncalibrated - Calibrated m/z [Da] (ave)": df[
            "Uncalibrated - Calibrated m/z [Da]"
        ].mean(skipna=True),
        "Uncalibrated - Calibrated m/z [Da] (sd)": df[
            "Uncalibrated - Calibrated m/z [Da]"
        ].std(ddof=0, skipna=True),
        "Peak Width(ave)": df["Retention length"].mean(skipna=True),
        "Peak Width (std)": df["Retention length"].std(ddof=0, skipna=True),
    }

    if pept_list is None:
        pept_list = [
            "HVLTSIGEK",
            "LTILEELR",
            "ATEEQLK",
            "AEFVEVTK",
            "QTALVELLK",
            "TVMENFVAFVDK",
        ]
    elif len(pept_list) < 6:
        pept_list = pept_list + (6 - len(pept_list)) * ["dummy_peptide"]
    elif len(pept_list) > 6:
        pept_list = pept_list[:6]

    for i in pept_list:
        print(i)
        df_pept = df[df.Sequence == i]
        if not df_pept.empty:
            charges = ";".join([str(x) for x in df_pept["Charge"].to_list()])

            if not df_pept[df_pept.Intensity == df_pept.Intensity.max()].empty:
                df_pept = df_pept[df_pept.Intensity == df_pept.Intensity.max()]

            ave = float(df_pept.filter(regex="Reporter intensity corrected").mean(axis=1))
            std = float(df_pept.filter(regex="Reporter intensity corrected").std(axis=1, ddof=0))

            if ave != 0:
                cv = std / ave * 100
            else:
                cv = 'not calculated'

            dict_info_qc = {
                f"qc{pept_list.index(i) + 1}_peptide": i,
                f"qc{pept_list.index(i) + 1}_peptide_charges": charges,
                f"N_qc{pept_list.index(i) + 1}_missing_values": ";".join(
                    [
                        str(x)
                        for x in df_pept.filter(regex="Reporter intensity corrected")
                    .replace(np.nan, 0)
                    .isin([0])
                    .sum()
                    .to_list()
                    ]
                ),
                f"reporter_intensity_corrected_qc{pept_list.index(i) + 1}_ave": ave,
                f"reporter_intensity_corrected_qc{pept_list.index(i) + 1}_sd": std,
                f"reporter_intensity_corrected_qc{pept_list.index(i) + 1}_cv": cv,
                f"calibrated_retention_time_qc{pept_list.index(i) + 1}": float(
                    df_pept["Calibrated retention time"]
                ),
                f"retention_length_qc{pept_list.index(i) + 1}": float(
                    df_pept["Retention length"]
                ),
                f"N_of_scans_qc{pept_list.index(i) + 1}": float(
                    df_pept["Number of scans"]
                ),
            }

            result.update(dict_info_qc)
        else:
            dict_info_qc = {
                f"qc{pept_list.index(i) + 1}_peptide_charges": 'not detected',
                f"N_qc{pept_list.index(i) + 1}_missing_values": 'not detected',
                f"reporter_intensity_corrected_qc{pept_list.index(i) + 1}_ave": 'not detected',
                f"reporter_intensity_corrected_qc{pept_list.index(i) + 1}_sd": 'not detected',
                f"reporter_intensity_corrected_qc{pept_list.index(i) + 1}_cv": 'not detected',
                f"calibrated_retention_time_qc{pept_list.index(i) + 1}": 'not detected',
                f"retention_length_qc{pept_list.index(i) + 1}": 'not detected',
                f"N_of_scans_qc{pept_list.index(i) + 1}": 'not detected',
            }
            result.update(dict_info_qc)

    return pd.Series(result)
