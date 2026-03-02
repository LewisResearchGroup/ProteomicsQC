import pandas as pd
import os

from omics.proteomics.maxquant.quality_control import (
    maxquant_qc,
    maxquant_qc_summary,
    maxquant_qc_protein_groups,
    maxquant_qc_peptides,
    maxquant_qc_msmScans,
    maxquant_qc_evidence,
)

PATH = os.path.join("tests", "omics", "data", "maxquant", "tmt11", "example-0")


class TestMaxquantQualityControl:
    def test__maxquant_qc_summary(self):
        out = maxquant_qc_summary(PATH)

        assert isinstance(out, pd.Series), f"It is a {type(out)} not a Series"

        expected_cols = [
            "MS",
            "MS/MS",
            "MS3",
            "MS/MS Submitted",
            "MS/MS Identified",
            "MS/MS Identified [%]",
            "Peptide Sequences Identified",
            "Av. Absolute Mass Deviation [mDa]",
            "Mass Standard Deviation [mDa]",
        ]

        assert len(expected_cols) - len(out.index) == 0, (
            f"New columns {out.index[len(expected_cols):]} in output "
            f"file. Adjust expected_cols variable accordingly"
        )

        assert len(list(set(expected_cols) - set(out.index))) == 0, list(
            set(expected_cols) - set(out.index)
        )

        assert (
            ~out.isnull().values.any()
        ), f"NaN value at {out.index[out.isna().any()].tolist()}"

    def test__maxquant_qc_protein_groups(self):
        out = maxquant_qc_protein_groups(PATH, protein=None)

        assert isinstance(out, pd.Series), f"It is a {type(out)} not a Series"

        actual_ndx = out.index.to_list()

        expected_ndx = [
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
            "Protein_qc",
            "N_of_Protein_qc_pepts",
            "N_Protein_qc_missing_values",
            "reporter_intensity_corrected_Protein_qc_ave",
            "reporter_intensity_corrected_Protein_qc_sd",
            "reporter_intensity_corrected_Protein_qc_cv",
        ]

        assert len(expected_ndx) - len(actual_ndx) == 0, (
            f"New columns {actual_ndx[len(expected_ndx):]} in output "
            f"file. Adjust expected_cols variable accordingly"
        )

        assert len(list(set(expected_ndx) - set(actual_ndx))) == 0, list(
            set(expected_ndx) - set(actual_ndx)
        )

        assert (
            ~out.isnull().values.any()
        ), f"NaN value at {actual_ndx[out.isna().any()].tolist()}"

    def test__maxquant_qc_peptides(self):
        out = maxquant_qc_peptides(PATH)

        assert isinstance(out, pd.Series), f"It is a {type(out)} not a Series"

        expected_cols = [
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
        ]

        assert len(expected_cols) - len(out.index) == 0, (
            f"New columns {out.index[len(expected_cols):]} in output "
            f"file. Adjust expected_cols variable accordingly"
        )

        assert len(list(set(expected_cols) - set(out.index))) == 0, list(
            set(expected_cols) - set(out.index)
        )

        assert (
            ~out.isnull().values.any()
        ), f"NaN value at {out.index[out.isna().any()].tolist()}"

    def test__maxquant_qc_msmScans(self):
        out = maxquant_qc_msmScans(PATH)

        assert isinstance(out, pd.Series), f"It is a {type(out)} not a Series"

        expected_cols = ["Mean_parent_int_frac"]

        assert len(expected_cols) - len(out.index) == 0, (
            f"New columns {out.index[len(expected_cols):]} in output "
            f"file. Adjust expected_cols variable accordingly"
        )

        assert len(list(set(expected_cols) - set(out.index))) == 0, list(
            set(expected_cols) - set(out.index)
        )

        assert (
            ~out.isnull().values.any()
        ), f"NaN value at {out.index[out.isna().any()].tolist()}"

    def test__maxquant_qc_evidence(self):
        out = maxquant_qc_evidence(PATH, pept_list=None)

        assert isinstance(out, pd.Series), f"It is a {type(out)} not a Series"

        actual_ndx = out.index.to_list()

        expected_ndx = [
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
            "qc3_peptide_charges",
            "N_qc3_missing_values",
            "reporter_intensity_corrected_qc3_ave",
            "reporter_intensity_corrected_qc3_sd",
            "reporter_intensity_corrected_qc3_cv",
            "calibrated_retention_time_qc3",
            "retention_length_qc3",
            "N_of_scans_qc3",
            "qc4_peptide_charges",
            "N_qc4_missing_values",
            "reporter_intensity_corrected_qc4_ave",
            "reporter_intensity_corrected_qc4_sd",
            "reporter_intensity_corrected_qc4_cv",
            "calibrated_retention_time_qc4",
            "retention_length_qc4",
            "N_of_scans_qc4",
            "qc5_peptide_charges",
            "N_qc5_missing_values",
            "reporter_intensity_corrected_qc5_ave",
            "reporter_intensity_corrected_qc5_sd",
            "reporter_intensity_corrected_qc5_cv",
            "calibrated_retention_time_qc5",
            "retention_length_qc5",
            "N_of_scans_qc5",
            "qc6_peptide_charges",
            "N_qc6_missing_values",
            "reporter_intensity_corrected_qc6_ave",
            "reporter_intensity_corrected_qc6_sd",
            "reporter_intensity_corrected_qc6_cv",
            "calibrated_retention_time_qc6",
            "retention_length_qc6",
            "N_of_scans_qc6",
        ]

        assert len(expected_ndx) - len(actual_ndx) == 0, (
            f"New columns {actual_ndx[len(expected_ndx):]} in output "
            f"file. Adjust expected_cols variable accordingly"
        )

        assert len(list(set(expected_ndx) - set(actual_ndx))) == 0, list(
            set(expected_ndx) - set(actual_ndx)
        )

        assert (
            ~out.isnull().values.any()
        ), f"NaN value at {out[out.isna()].index.to_list()}"

    def test__maxquant_qc_columns(self):
        result = maxquant_qc(PATH, protein=None, pept_list=None)
        actual_cols = result.columns

        expected_cols = [
            "Date",
            "MS",
            "MS/MS",
            "MS3",
            "MS/MS Submitted",
            "MS/MS Identified",
            "MS/MS Identified [%]",
            "Peptide Sequences Identified",
            "Av. Absolute Mass Deviation [mDa]",
            "Mass Standard Deviation [mDa]",
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

        assert all(actual_cols == expected_cols), actual_cols
