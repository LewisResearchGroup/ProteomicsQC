import pandas as pd

qc_columns_always = [
    "Index",
    "Date",
    "RawFile",
    "DateAcquired",
    "Use Downstream",
    "Flagged",
]

qc_columns_default = [
    "MS/MS Identified [%]",
    "N_peptides",
    "N_protein_groups",
    "Oxidations [%]",
    "N_missed_cleavages_eq_1 [%]",
    "NumEsiInstabilityFlags",
    "MeanMs2TriggerRate(/Ms1Scan)",
    "MedianMs2PeakFractionConsumingTop80PercentTotalIntensity",
    "MedianPeakWidthAt50%H(s)",
    "MedianAsymmetryAt50%H",
    "TimeBeforeFirstExceedanceOf10%MaxIntensity",
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
    "N_peptides_potential_contaminants",
    "Mean_parent_int_frac",
    "Uncalibrated - Calibrated m/z [ppm] (ave)",
    "Uncalibrated - Calibrated m/z [ppm] (sd)",
    "calibrated_retention_time_qc1",
    "calibrated_retention_time_qc2",
]

qc_columns_options = [
    "RawFile",
    "Index",
    "DateAcquired",
    "Instrument",
    "ExperimentMsOrder",
    "Ms1Analyzer",
    "Ms2Analyzer",
    "Ms3Analyzer",
    "TotalAnalysisTime(min)",
    "TotalScans",
    "NumMs1Scans",
    "NumMs2Scans",
    "NumMs3Scans",
    "Ms1ScanRate(/s)",
    "Ms2ScanRate(/s)",
    "Ms3ScanRate(/s)",
    "MeanDutyCycle(s)",
    "MeanMs2TriggerRate(/Ms1Scan)",
    "Ms1MedianSummedIntensity",
    "Ms2MedianSummedIntensity",
    "MedianPrecursorIntensity",
    # "MedianMs1IsolationInterence",  # no values generated
    "MedianMs2PeakFractionConsumingTop80PercentTotalIntensity",
    "NumEsiInstabilityFlags",
    # "MedianMassDrift(ppm)",  # no values generated
    # "IdentificationRate(IDs/Ms2Scan)",  # no values generated
    # "DigestionEfficiency",  # no values generated
    # "MissedCleavageRate(/PSM)",  # no values generated
    # "MedianPeptideScore",  # no values generated
    # "CutoffDecoyScore(0.05FDR)",  # no values generated
    # "NumberOfPSMs",  # no values generated
    # "NumberOfUniquePeptides",  # no values generated
    "MedianMs1FillTime(ms)",
    "MedianMs2FillTime(ms)",
    "MedianMs3FillTime(ms)",
    "MedianPeakWidthAt10%H(s)",
    "MedianPeakWidthAt50%H(s)",
    "MedianAsymmetryAt10%H",
    "MedianAsymmetryAt50%H",
    "MeanCyclesPerAveragePeak",
    "PeakCapacity",
    "TimeBeforeFirstExceedanceOf10%MaxIntensity",
    "TimeAfterLastExceedanceOf10%MaxIntensity",
    "FractionOfRunAbove10%MaxIntensity",
    # "PsmChargeRatio3to2",  # no values generated
    # "PsmChargeRatio4to2",  # no values generated
    # "SearchParameters",  # not used
    "RawFilePath",
    "Date",
    "Day",
    "Week",
    "Month",
    "Year",
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
    # "qc1_peptide_charges",
    # "N_qc1_missing_values",
    "reporter_intensity_corrected_qc1_ave",
    "reporter_intensity_corrected_qc1_sd",
    "reporter_intensity_corrected_qc1_cv",
    "calibrated_retention_time_qc1",
    "retention_length_qc1",
    "N_of_scans_qc1",
    # "qc2_peptide_charges",
    # "N_qc2_missing_values",
    "reporter_intensity_corrected_qc2_ave",
    "reporter_intensity_corrected_qc2_sd",
    "reporter_intensity_corrected_qc2_cv",
    "calibrated_retention_time_qc2",
    "retention_length_qc2",
    "N_of_scans_qc2",
    # "N_of_Protein_qc_pepts",
    # "N_Protein_qc_missing_values",
    "reporter_intensity_corrected_Protein_qc_ave",
    "reporter_intensity_corrected_Protein_qc_sd",
    "reporter_intensity_corrected_Protein_qc_cv",
    "Missed Cleavages [%]",
    "Flagged",
    "Use Downstream",
]

qc_columns_options = [c for c in qc_columns_options if c not in qc_columns_always]

assert pd.value_counts(qc_columns_options).max() == 1, pd.value_counts(
    qc_columns_options
)

# qc_columns_options.sort()

figure_config = {"toImageButtonOptions": {"width": None, "height": None}}

data_range_options = [
    {"label": "Last 3", "value": 3},
    {"label": "Last 30", "value": 30},
    {"label": "Last 100", "value": 100},
    {"label": "Last 300", "value": 300},
    {"label": "Last 1k", "value": 1000},
    {"label": "Last 3k", "value": 3000},
    {"label": "Last 10k", "value": 10000},
    {"label": "All", "value": None},
]


turquoise = "rgb(64,224,208)"
lightblue = "rgb(123,180,230)"
maroon = "rgb(128,0,0)"
midnight = "rgb(0,51,102)"
slategrey = "rgb(112,128,144)"
lightred = "rgb(255,230,230)"

colors = {
    "accepted": lightblue,
    "rejected": lightred,
    "unassigned": "white",
    "flagged": "maroon",
    "not_flagged": "black",
    "selected": "purple",
}

figure_font = dict(
    # family="Courier New, monospace",
    size=15,
    color="black",
)
