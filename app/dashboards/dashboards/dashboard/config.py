import pandas as pd

qc_columns_always = ['Index', 'Date', 'RawFile',  'DateAcquired', 'Flagged']

qc_columns_default = [ 
 'MS/MS Identified [%]', 'N_peptides', 'N_protein_groups', 
 'Oxidations [%]', 'N_missed_cleavages_eq_1 [%]', 'MedianMs1FillTime(ms)', 
 'MedianMs2FillTime(ms)', 'NumMs1Scans', 'NumMs2Scans', 
 'NumEsiInstabilityFlags']

qc_columns_options = ['Index', 'DateAcquired', 'RawFile', 'Instrument', 
 'ExperimentMsOrder', 'TotalAnalysisTime(min)', 'TotalScans', 'NumMs1Scans',
 'NumMs2Scans', 'NumMs3Scans', 'Ms1ScanRate(/s)', 'Ms2ScanRate(/s)', 
 'Ms3ScanRate(/s)', 'MeanDutyCycle(s)', 'MeanMs2TriggerRate(/Ms1Scan)', 
 'Ms1MedianSummedIntensity', 'Ms2MedianSummedIntensity', 'MedianPrecursorIntensity', 
 'MedianMs1IsolationInterence', 'MedianMs2PeakFractionConsumingTop80PercentTotalIntensity', 
 'NumEsiInstabilityFlags', 'MedianMs1FillTime(ms)', 'MedianMs2FillTime(ms)', 
 'MedianMs3FillTime(ms)', 'MedianPeakWidthAt10%H(s)', 'MedianPeakWidthAt50%H(s)', 
 'MedianAsymmetryAt10%H', 'MedianAsymmetryAt50%H', 'MeanCyclesPerAveragePeak', 
 'PeakCapacity', 'TimeBeforeFirstExceedanceOf10%MaxIntensity', 
 'TimeAfterLastExceedanceOf10%MaxIntensity', 'FractionOfRunAbove10%MaxIntensity', 
 'RawFilePath', 'Day', 'Week', 'Month', 'Year', 'LRG_omics version', 
 'Pipeline', 'FastaFile', 'MaxQuantPar', 'MS/MS Submitted', 
 'MS/MS Identified', 'MS/MS Identified [%]', 'Peptide Sequences Identified',
 'Av. Absolute Mass Deviation [mDa]', 'Mass Standard Deviation [mDa]', 
 'N_protein_groups', 'N_protein_true_hits', 'N_missing_values', 
 'N_protein_potential_contaminants', 'N_protein_reverse_seq', 
 'Protein_mean_seq_cov [%]', 'N_peptides', 'N_peptides_potential_contaminants', 
 'N_peptides_reverse', 'Oxidations [%]', 'N_missed_cleavages_total', 
 'N_missed_cleavages_eq_0 [%]', 'N_missed_cleavages_eq_1 [%]', 
 'N_missed_cleavages_eq_2 [%]', 'N_missed_cleavages_gt_3 [%]',
 'N_peptides_last_amino_acid_K [%]', 'N_peptides_last_amino_acid_R [%]',
 'N_peptides_last_amino_acid_other [%]', 'Mean_parent_int_frac', 
 'Uncalibrated - Calibrated m/z [ppm] (ave)', 'Uncalibrated - Calibrated m/z [ppm] (sd)', 
 'Uncalibrated - Calibrated m/z [Da] (ave)', 'Uncalibrated - Calibrated m/z [Da] (sd)', 
 'Peak Width(ave)', 'Peak Width (std)', 'qc1_peptide_charge', 'N_qc1_missing_values', 
 'reporter_intensity_corrected_qc1_ave', 'reporter_intensity_corrected_qc1_sd', 
 'reporter_intensity_corrected_qc1_cv', 'calibrated_retention time_qc1', 
 'retention_length_qc1', 'N_of_scans_qc1', 'qc2_peptide_charge', 'N_qc2_missing_values', 
 'reporter_intensity_corrected_qc2_ave', 'reporter_intensity_corrected_qc2_sd', 
 'reporter_intensity_corrected_qc2_cv', 'calibrated_retention time_qc2', 
 'retention_length_qc2', 'N_of_scans_qc2', 'N_of_BSA_pepts', 'N_qc3_missing_values', 
 'reporter_intensity_corrected_qc3_ave', 'reporter_intensity_corrected_qc3_sd', 
 'reporter_intensity_corrected_qc3_cv', 'RT_for_ATEEQLK', 'Ave_Intensity_for_ATEEQLK', 
 'RT_for_AEFVEVTK', 'Ave_Intensity_for_AEFVEVTK', 'RT_for_QTALVELL', 
 'Ave_Intensity_for_QTALVELL', 'RT_for_TVMENFVAFVDK', 'Ave_Intensity_for_TVMENFVAFVDK', 
 'TMT1_missing_values', 'TMT2_missing_values', 'TMT3_missing_values', 'TMT4_missing_values', 
 'TMT5_missing_values', 'TMT6_missing_values', 'TMT7_missing_values', 'TMT8_missing_values', 
 'TMT9_missing_values', 'TMT10_missing_values', 'TMT11_missing_values', 'qc1_peptide_charges', 
 'calibrated_retention_time_qc1', 'qc2_peptide_charges', 'calibrated_retention_time_qc2', 
 'RT_for_QTALVELLK', 'Ave_Intensity_for_QTALVELLK', 'Missed Cleavages [%]']

qc_columns_options = [c for c in qc_columns_options if c not in qc_columns_always]

assert pd.value_counts(qc_columns_options).max() == 1, pd.value_counts(qc_columns_options)

qc_columns_options.sort()

figure_config = {"toImageButtonOptions": {"width": None, "height": None}}

data_range_options = [
    {'label': 'Last 30', 'value': 'last-30'},
    {'label': 'Last 100', 'value': 'last-100'},
    {'label': 'Last Week', 'value': 'week'},
    {'label': 'Last Two Weeks', 'value': 'two-weeks'},
    {'label': 'Last Month', 'value': 'month'},
    {'label': 'Last Year', 'value': 'year'},
    {'label': 'All Time', 'value': 'all-time'}]
