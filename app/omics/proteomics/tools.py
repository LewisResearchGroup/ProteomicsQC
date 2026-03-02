import os
import logging

from .rawtools.quality_control import collect_rawtools_qc_data
from .maxquant.quality_control import collect_maxquant_qc_data


def load_rawtools_data_from(path="/var/www/html/proteomics/files/raw"):
    df = collect_rawtools_qc_data(path)
    if df is None:
        return None
    df.index = df.iloc[::-1].index
    df.reset_index(inplace=True)
    df["RawFilePath"] = df["RawFile"].apply(os.path.dirname)
    df["RawFile"] = df["RawFile"].apply(os.path.basename)
    df.rename(columns={"index": "Index"}, inplace=True)
    df["Date"] = df.DateAcquired.dt.date.astype(str)
    df["Day"] = df.DateAcquired.dt.dayofyear.map("{:03d}".format)
    df["Week"] = df.DateAcquired.dt.isocalendar().week.map("{:02d}".format)
    df["Month"] = df.DateAcquired.dt.month.map("{:02d}".format)
    df["Year"] = df.DateAcquired.dt.year.astype(str)
    df["Month"] = df["Year"] + "-" + df["Month"]
    df["Week"] = df["Year"] + "-" + df["Week"]
    df["Day"] = df["Year"] + "-" + df["Day"]
    return df


formated_rawtools_data_from = load_rawtools_data_from

SEPARATED_VALUE_COLS_MAXQUANT = [
 'qc1_peptide_charges',
 'N_qc1_missing_values',
 'qc2_peptide_charges',
 'N_qc2_missing_values',
 'N_of_Protein_qc_pepts',
 'N_Protein_qc_missing_values'
]

def load_maxquant_data_from(path="/var/www/html/proteomics/files/", unpack=False):
    if not os.path.isdir(path):
        logging.warning(f"FileNotFound: {path}")
        return None
    df = collect_maxquant_qc_data(path)
    if df is None:
        logging.debug(f"Got no MaxQuant QC data from: {path}")
        return None
    df.index = df.iloc[::-1].index
    df.reset_index(inplace=True)
    df.rename(columns={"index": "Index"}, inplace=True)
    df["Missed Cleavages [%]"] = 100 - df["N_missed_cleavages_eq_0 [%]"]

    for col in ["MAXQUANTBIN", "proteomics_tools version", "RUNDIR", "Date"]:
        try:
            del df[col]
        except:
            pass
    for col in ["FastaFile", "RawFile", "MaxQuantPar"]:
        try:
            df[col] = df[col].apply(os.path.basename)
        except:
            pass
    if unpack:
      df = unpack_separated_values(df, SEPARATED_VALUE_COLS_MAXQUANT)
    return df

def split_and_replace(df, column, sep=',', suffix='_'):
    split_columns = df[column].str.split(sep, expand=True)
    split_columns.columns = [f'{column}{suffix}{i+1}' for i in split_columns.columns]
    return df.drop(column, axis=1).join(split_columns)

def unpack_separated_values(df, columns):
    for col in columns:
        df = split_and_replace(df, col, sep=';')
    return df
