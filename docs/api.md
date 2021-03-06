# API

NOTE: The  API is work in progress. We aim to make the API more RESTful in the future. In the following an overview of available routes are provided, as well as, usage examples using CURL.


## `/api/projects`

Returns a json object with information about all projects on the server.

Example: 

    curl -X POST --data project=lsarp  https://example.com/api/projects

    >>>
    [
        {
            "pk": 1, 
            "name": "LSARP", 
            "description": "This project is very large and applied", 
            "slug": "lsarp"
        }, 
        {
            "pk": 2, 
            "name": "Saliva project", 
            "description": "The project is about...", 
            "slug": "saliva"
        }, 
        {
            "pk": 3, 
            "name": "SARS-CoV-2 Detection", 
            "description": "Detection of SARS-CoV-2 Proteins from Patient Samples.",
            "slug": "sars-cov-2-detection"
        }
    ]


## `/api/pipelines`

Returns a json object with information about all MaxQuant pipelines in a certain project.

Example:

    curl -X POST --data project=lsarp  https://example.com/api/pipelines

    >>>
    [
        {
            "slug": "staphylococcus-aureus-tmt11", 
            "name": "Staphylococcus aureus (TMT11)", 
            "url": "https://example.com/datalake/P/P1/P1MQ1"
        }
    ]


## `/api/upload/raw`

Submits a raw file to an existing pipeline. Raw files can be submitted to an existing pipeline using the API. 
To submit a raw file the **UUID of the user and the target pipeline** are required which can be found in 
the **admin detail view** of the respective user and pipeline:

- [https://example.com/admin/user/user/1/change/](https://example.com/admin/user/user/1/change/)

- [https://example.com/admin/maxquant/maxquantpipeline/1/change/](https://example.com/admin/maxquant/maxquantpipeline/1/change/)


Example:
    
    curl -v -i -F orig_file="@</your/file.raw>" -F pid=xxx-yyy-zzz -F uid=xxx-yyy-zzz https://example.com/api/upload/raw

Alternatively, the python script `lrg_upload_raw_file_to_qc_pipeline.py` that is part of the [lrg_omics](https://github.com/LSARP/lrg-omics) packages can be used:
    
```
python lrg_upload_raw_file_to_qc_pipeline.py --raw your/file.raw --host https://example.com --uid xxx-yyy-zzz --pid xxx-yyy-zzz
```


## `/api/qc-data`

This route can be used to download the quality control data from a certain pipeline.

Example:

    curl -X POST --data project=lsarp --data pipeline=sa-tmt11 https://example.com/api/qc-data


    {"RawFile": ["SA021_210531_C", "SA021_210531_D", "SA021_210531_E", "SA021_210531_F", "SA021_210531_H"], "Index": [1.0, 2.0, 3.0, 4.0, 5.0], "DateAcquired": [1622476527000000000, 1622483222000000000, 1622492621000000000, 1622499315000000000, 1622512688000000000], "Instrument": ["Orbitrap Fusion Lumos", "Orbitrap Fusion Lumos", "Orbitrap Fusion Lumos", "Orbitrap Fusion Lumos", "Orbitrap Fusion Lumos"], "ExperimentMsOrder": ["Ms2", "Ms2", "Ms2", "Ms2", "Ms2"], "TotalAnalysisTime(min)": [99.9253922346667, 99.9313123146833, 99.9273881533167, 99.926844868, 99.9257958661333], "TotalScans": [43032, 42644, 42711, 42369, 42833], "NumMs1Scans": [5996, 6173, 6133, 6355, 6043], "NumMs2Scans": [37036, 36471, 36578, 36014, 36790], "NumMs3Scans": [0, 0, 0, 0, 0], "Ms1ScanRate(/s)": [1.00007947027767, 1.02954050087278, 1.02290942008649, 1.05994206868614, 1.00791458095158], "Ms2ScanRate(/s)": [6.17727539379646, 6.08267805075833, 6.10076321016201, 6.00672756281079, 6.13621999556653], "Ms3ScanRate(/s)": [0, 0, 0, 0, 0], "MeanDutyCycle(s)": [0.951965903999792, 0.949594528000013, 0.94862161599977, 0.947536128000124, 0.950974272000025], "MeanMs2TriggerRate(/Ms1Scan)": [6.17678452301534, 5.90814838814191, 5.96412848524376, 5.66703383162864, 6.08803574383584], "Ms1MedianSummedIntensity": [1373091496.7832, 1174184979.02734, 1279266962.39844, 1161303464.01563, 1282214517.42188], "Ms2MedianSummedIntensity": [1633995.80926514, 1355357.38024902, 1461732.65924072, 1285265.38223267, 1572994.36050415], "MedianPrecursorIntensity": [572243.96875, 482155.71875, 521451.96875, 445561.140625, 521398.25], "MedianMs1IsolationInterence": [0.267313288607806, 0.264238075086116, 0.26554694172683, 0.259529487636828, 0.262508095447206], "MedianMs2PeakFractionConsumingTop80PercentTotalIntensity": [0.354166666666667, 0.364238410596026, 0.36, 0.363636363636364, 0.356006893386657], "NumEsiInstabilityFlags": [1, 3, 0, 12, 4], "MedianMs1FillTime(ms)": [1.27314174175262, 1.48821616172791, 1.39801180362701, 1.55530488491058, 1.34955477714539], "MedianMs2FillTime(ms)": [86, 86, 86, 86, 86], "MedianMs3FillTime(ms)": [NaN, NaN, NaN, NaN, NaN], "MedianPeakWidthAt10%H(s)": [28.8155269614892, 29.3934068747652, 29.6827481566525, 30.4683510280734, 30.0636003825315], "MedianPeakWidthAt50%H(s)": [11.5410179871052, 11.6453049168208, 11.7461342388454, 11.8654403906942, 11.9581356904507], "MedianAsymmetryAt10%H": [1.09751979427411, 1.10183101679795, 1.09483975707686, 1.09099972704928, 1.09248235122764], "MedianAsymmetryAt50%H": [1.03279572756282, 1.04327639108573, 1.0352354303321, 1.03152921372008, 1.03189153541257], "MeanCyclesPerAveragePeak": [30.2694947796108, 30.9536396936407, 31.2903982536486, 32.1553449285148, 31.6134739579271], "PeakCapacity": [519.856808750705, 515.231833432065, 510.789046637421, 505.650368184351, 501.725438255992], "TimeBeforeFirstExceedanceOf10%MaxIntensity": [11.2920304712, 11.0928231656, 10.8445925642667, 10.94502254, 10.72725291625], "TimeAfterLastExceedanceOf10%MaxIntensity": [5.25216392423333, 5.26415371870002, 5.22221408105, 5.22979773493333, 5.23404510213335], "FractionOfRunAbove10%MaxIntensity": [0.834549143222103, 0.836431098158571, 0.839324531675301, 0.838245443052445, 0.840379061914724], "RawFilePath": ["/datalake/P/P36/P36MQ36/inputs/SA021_210531_C", "/datalake/P/P36/P36MQ36/inputs/SA021_210531_D", "/datalake/P/P36/P36MQ36/inputs/SA021_210531_E", "/datalake/P/P36/P36MQ36/inputs/SA021_210531_F", "/datalake/P/P36/P36MQ36/inputs/SA021_210531_H"], "Date": ["2021-05-31", "2021-05-31", "2021-05-31", "2021-05-31", "2021-06-01"], "Day": ["2021-151", "2021-151", "2021-151", "2021-151", "2021-152"], "Week": ["2021-22", "2021-22", "2021-22", "2021-22", "2021-22"], "Month": ["2021-5", "2021-5", "2021-5", "2021-5", "2021-6"], "Year": ["2021", "2021", "2021", "2021", "2021"], "LRG_omics version": [NaN, NaN, NaN, NaN, NaN], "Pipeline": [NaN, NaN, NaN, NaN, NaN], "FastaFile": [NaN, NaN, NaN, NaN, NaN], "MaxQuantPar": [NaN, NaN, NaN, NaN, NaN], "MS": [5996.0, 6173.0, 6133.0, 6355.0, 6043.0], "MS/MS": [37036.0, 36471.0, 36578.0, 36014.0, 36790.0], "MS3": [0.0, 0.0, 0.0, 0.0, 0.0], "MS/MS Submitted": [43432.0, 42954.0, 42987.0, 42425.0, 43084.0], "MS/MS Identified": [125.0, 89.0, 78.0, 123.0, 163.0], "MS/MS Identified [%]": [0.29, 0.21, 0.18, 0.29, 0.38], "Peptide Sequences Identified": [87.0, 60.0, 50.0, 78.0, 86.0], "Av. Absolute Mass Deviation [mDa]": [157970.0, 143820.0, 147220.0, 149600.0, 136680.0], "Mass Standard Deviation [mDa]": [168260.0, 151340.0, 156740.0, 158360.0, 146430.0], "N_protein_groups": [49, 37, 27, 33, 31], "N_protein_true_hits": [3, 3, 3, 3, 3], "N_protein_potential_contaminants": [46, 34, 24, 30, 28], "N_protein_reverse_seq": [0, 0, 0, 0, 0], "Protein_mean_seq_cov [%]": [68.06666666666666, 68.06666666666666, 68.06666666666666, 68.06666666666666, 68.06666666666666], "TMT1_missing_values": [0, 0, 0, 1, 1], "TMT2_missing_values": [0, 0, 0, 1, 1], "TMT3_missing_values": [0, 0, 0, 1, 1], "TMT4_missing_values": [0, 0, 0, 1, 1], "TMT5_missing_values": [0, 0, 0, 1, 1], "TMT6_missing_values": [0, 0, 0, 1, 1], "TMT7_missing_values": [0, 0, 0, 1, 1], "TMT8_missing_values": [0, 0, 0, 1, 1], "TMT9_missing_values": [0, 0, 0, 1, 1], "TMT10_missing_values": [0, 0, 0, 1, 1], "TMT11_missing_values": [0, 0, 0, 1, 1], "N_peptides": [87.0, 60.0, 50.0, 78.0, 86.0], "N_peptides_potential_contaminants": [84.0, 57.0, 47.0, 75.0, 83.0], "N_peptides_reverse": [0.0, 0.0, 0.0, 0.0, 0.0], "Oxidations [%]": [5.75, 3.33, 4.0, 2.56, 3.49], "N_missed_cleavages_total": [34.0, 21.0, 12.0, 30.0, 31.0], "N_missed_cleavages_eq_0 [%]": [60.92, 65.0, 76.0, 61.54, 63.95], "N_missed_cleavages_eq_1 [%]": [29.89, 31.67, 18.0, 19.23, 30.23], "N_missed_cleavages_eq_2 [%]": [9.2, 3.33, 6.0, 19.23, 5.81], "N_missed_cleavages_gt_3 [%]": [0.0, 0.0, 0.0, 0.0, 0.0], "N_peptides_last_amino_acid_K [%]": [68.97, 66.67, 66.0, 61.54, 53.49], "N_peptides_last_amino_acid_R [%]": [29.89, 31.67, 32.0, 37.18, 44.19], "N_peptides_last_amino_acid_other [%]": [1.15, 1.67, 2.0, 1.28, 2.33], "Mean_parent_int_frac": [0.76, 0.76, 0.76, 0.76, 0.76], "Uncalibrated - Calibrated m/z [ppm] (ave)": [2.7415011627906978, 2.576863793103448, 2.690334090909091, 2.646644943820225, 2.898638775510204], "Uncalibrated - Calibrated m/z [ppm] (sd)": [0.4648552158928993, 0.5576167642368961, 0.3183931831322439, 0.9044888200638536, 0.4135656221237233], "Uncalibrated - Calibrated m/z [Da] (ave)": [0.001353795116279, 0.0012787048275862, 0.0014107493181818, 0.0011941075280898, 0.0015648651020408], "Uncalibrated - Calibrated m/z [Da] (sd)": [0.0003500341425564, 0.0004812526933493, 0.0004056083979731, 0.0004082370373463, 0.0003700619876708], "Peak Width(ave)": [0.8557468807339449, 0.8981167901234568, 0.9357113846153846, 0.8475711428571429, 0.8682191071428571], "Peak Width (std)": [0.3173496083683649, 0.3055485354338097, 0.2629870508358037, 0.2870181767441759, 0.3747969534331546], "qc1_peptide_charges": ["[2]", "[2, 3]", "[2]", "[2, 3]", "[2, 3]"], "N_qc1_missing_values": ["[0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0]", "[0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0]", "[0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0]", "[0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0]", "[0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0]"], "reporter_intensity_corrected_qc1_ave": [118403.54545454546, 336068.1818181818, 121905.0, 216885.45454545456, 321740.9090909091], "reporter_intensity_corrected_qc1_sd": [15546.72921674662, 33090.07014421034, 23883.441677522867, 25961.51255000944, 60109.87386059956], "reporter_intensity_corrected_qc1_cv": [13.13029027725773, 9.846237143066578, 19.591847485765857, 11.970149222048663, 18.682695349634663], "calibrated_retention_time_qc1": [28.592, 28.832, 28.492, 28.89, 28.856], "retention_length_qc1": [0.67593, 0.8974, 0.80298, 1.0287, 0.97924], "N_of_scans_qc1": [35.0, 44.0, 44.0, 57.0, 42.0], "qc2_peptide_charges": ["[3]", "[3]", "[3]", "[3]", "[3]"], "N_qc2_missing_values": ["[0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0]", "[0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0]", "[0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0]", "[0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0]", "[0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0]"], "reporter_intensity_corrected_qc2_ave": [10655.045454545456, 10466.681818181818, 9551.090909090908, 7102.845454545453, 10960.081818181818], "reporter_intensity_corrected_qc2_sd": [1899.459126537981, 1617.258841271063, 2520.185209808108, 1322.017686144682, 1245.894167997924], "reporter_intensity_corrected_qc2_cv": [17.826851463385072, 15.451495224223786, 26.386359776026712, 18.612508108263278, 11.36756265752592], "calibrated_retention_time_qc2": [65.516, 65.615, 65.91, 66.219, 65.817], "retention_length_qc2": [0.6997, 0.64079, 0.6447, 0.75824, 0.74315], "N_of_scans_qc2": [33.0, 28.0, 33.0, 36.0, 34.0], "N_of_Protein_qc_pepts": ["['11;11']", "['15;15;3']", "['12;12;2']", "['14;14']", "['14;14']"], "N_Protein_qc_missing_values": ["[0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0]", "[0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0]", "[0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0]", "[0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0]", "[0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0]"], "reporter_intensity_corrected_Protein_qc_ave": [2147163.636363636, 2617475.4545454546, 2348207.272727273, 2407727.272727273, 2548828.1818181816], "reporter_intensity_corrected_Protein_qc_sd": [628648.0215838767, 846443.44322007, 762162.9915049896, 705718.5546286192, 811398.0259327745], "reporter_intensity_corrected_Protein_qc_cv": [29.278067630119413, 32.33816163395739, 32.457228131305136, 29.310568627203367, 31.834159388255497], "Missed Cleavages [%]": [39.08, 35.0, 24.0, 38.46, 36.05], "Flagged": [false, false, false, false, false], "Use Downstream": [true, true, true, true, true]}


## `/api/protein-names`

This route provides a list of all protein-groups idnentified in a range of files of a specific pipeline. This downlodas a list of protein groups, the fasta headers, the average score, and average intensity.


Example:

    curl -X POST -H 'Content-Type: application/json' --data '{"project": "lsarp", "pipeline": "s-aureus-new-pan-proteome", "data_range": None, "add_con": "False", "add_rev": "False"}' https:/proteomics.resistancedb.org/api/protein-names

    {"protein_names": ["CON__ENSEMBL:ENSBTAP00000038253", "CON__Q05B55", "CON__Q7Z3Y8", "CON__Q7Z3Y9", "CON__Q2YDI2", "CON__ENSEMBL:ENSBTAP00000016285", "CON__ENSEMBL:ENSBTAP00000007350;CON__P01030", "CON__Q03247", "CON__P01966", "CON__H-INV:HIT000292931", "CON__Q3KUS7", "CON__Q2HJF0", "CON__A2A5Y0", "CON__P19012", "CON__Q9H552", "CON__Q0V8M9", "CON__P02777", "CON__Q6KB66-1", "CON__P02662", "CON__Q0VCM5", "CON__P05784", "CON__Q148H6", "CON__Q2UVX4", "CON__REFSEQ:XP_932229", "CON__Q3MHN5;CON__ENSEMBL:ENSBTAP00000018229", "CON__P20930", "CON__Q5D862", "CON__Q922U2", "CON__Q1A7A4", "CON__Q28085", "CON__Q3SX28", "CON__ENSEMBL:ENSBTAP00000025008", "CON__P04258", "CON__Q9N2I2", "CON__Streptavidin", "CON__P50448", "CON__Q3ZAW8;CON__P08779;CON__P02533;CON__Q9Z2K1;CON__P08727;CON__P19001;CON__Q7Z3Y9;CON__O76013;CON__Q7Z3Y8;CON__A2A4G1;CON__Q497I4;CON__A2AB72;CON__Q6IFX2;CON__Q7Z3Z0;CON__Q9QWL7;CON__Q04695;CON__Q92764;CON__Q9UE12;CON__Q15323;CON__A2A5Y0;CON__Q14525;CON__REFSEQ:XP_986630", "CON__Q8BGZ7;CON__O95678", "CON__ENSEMBL:ENSBTAP00000016046", "CON__Q2KIF2", "CON__P17697", "CON__Q95121", "CON__H-INV:HIT000292931;CON__P05787", "CON__Q32PJ2", "CON__P02070;CON__Q3SX09", "CON__P08727", "CON__ENSEMBL:ENSBTAP00000001528", "CON__Q28194", "CON__Q3TTY5", "CON__REFSEQ:XP_001252647;CON__A2I7N3", "CON__P00711", "CON__Q3MHN2", "CON__P07744", "CON__Q32MB2", "CON__Q2TBQ1", "CON__Q3ZBS7", "CON__P02676", "CON__Q148H6;CON__Q7Z3Y7", "CON__Q9D312", "CON__Q6NXH9", "CON__Q05443", "CON__Q3T052", "CON__Q9C075", "CON__Q6IFX2", "CON__H-INV:HIT000292931;CON__P05787;CON__Q9H552", "CON__P28800", "CON__Q2KJ62;CON__P01044-1", "CON__P02666", "CON__Q32PI4", "CON__Q95M17", "CON__Q28107", "CON__Q8N1N4-2;CON__Q7RTT2", "CON__Q3SY84", "CON__Q3SX14", "CON__Q3ZBD7", "CON__Q6IFU6", "CON__P50446", "QC2|Peptide2", "CON__P35908v2;CON__P35908", "CON__Q9R0H5;CON__Q14CN4-1;CON__Q6IME9;CON__Q3SY84;CON__Q6NXH9", "CON__P50446;CON__P48668;CON__P04259;CON__P02538", "CON__Q6IME9;CON__Q6NXH9", "CON__O43790;CON__Q6NT21;CON__P78385;CON__Q14533", "CON__P02672", "CON__P19013;CON__P07744", "CON__P35527", "CON__ENSEMBL:ENSBTAP00000024466;CON__ENSEMBL:ENSBTAP00000024462", "CON__ENSEMBL:ENSBTAP00000032840", "823|Adapter_protein_MecA_1|100.0%", "CON__P02768-1", "CON__P13645", "CON__P02535-1;CON__P13645", "CON__P13645;CON__P02535-1", "CON__P0C1U8", "QC1|Peptide1", "CON__P04264", "CON__ENSEMBL:ENSBTAP00000038253;CON__P04264", "CON__P04264;CON__ENSEMBL:ENSBTAP00000038253", "CON__P15636", "QC3|BSA;CON__P02769", "CON__P02769;QC3|BSA"], "Score": [-2.0, -0.00035682, -0.00015709, 0.0004502, 0.0028997, 0.005782, 0.0086608, 0.018453, 0.019632, 0.031172, 0.03314, 0.046157, 0.12325, 0.14458, 0.17288, 0.25441, 0.30094, 0.59944, 2.6436, 2.8874465, 2.9975735, 3.00492895, 3.185175, 3.2554, 3.44062, 3.971716666666667, 4.001147896666667, 4.0085880000000005, 4.3311, 4.4275805, 4.5179325, 4.9009, 5.710233333333334, 5.7197000000000005, 5.7626, 5.7626, 5.763, 5.7638, 5.7649, 5.7687, 5.7785, 5.7842, 5.7953, 5.8015, 5.8088, 5.8106, 5.8204095, 5.8263, 5.8278, 5.8287, 5.8348, 5.8358, 5.8404, 5.8412, 5.8507, 5.85985, 5.86625, 5.869, 5.8716, 5.8869, 5.888, 5.9492, 5.9554, 5.9554, 5.9554, 5.9554, 5.9619, 5.9619, 6.0408, 6.0565, 6.0921, 6.0939499999999995, 6.1446, 6.1618, 6.1975, 6.5082, 7.5403, 8.193838, 9.253181750000001, 11.529, 11.74, 11.991, 12.225, 12.7810075, 14.165, 22.374, 23.05566, 23.7471, 28.115699999999997, 48.947333333333326, 71.044, 114.85, 122.03105, 266.104, 270.058, 305.36999999999995, 323.31, 323.31, 323.31, 323.31, 323.31], "Intensity": [8409900.0, 11054000.0, 0.0, 0.0, 6152600.0, 45442000.0, 252630000.0, 821110000.0, 7537300.0, 0.0, 3730600.0, 46085000.0, 3750700.0, 26828000.0, 24939000.0, 7565600.0, 0.0, 23059000.0, 0.0, 25551700.0, 114805000.0, 53888500.0, 35133000.0, 3966400.0, 47051000.0, 95932400.0, 22793666.666666668, 0.0, 15673750.0, 17165500.0, 41640500.0, 64577666.666666664, 79765666.66666667, 249340000.0, 14302000.0, 12215000.0, 42996000.0, 3811400.0, 25339000.0, 0.0, 84044000.0, 0.0, 126100000.0, 11582000.0, 12202000.0, 25058000.0, 197860500.0, 0.0, 0.0, 909560000.0, 45582000.0, 0.0, 0.0, 74963000.0, 39938000.0, 28655500.0, 0.0, 12411000.0, 690640000.0, 0.0, 15069000.0, 2750966.6666666665, 6625600.0, 10556000.0, 200210000.0, 32296000.0, 0.0, 0.0, 0.0, 3608400.0, 784210000.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 13143400.0, 21867650.0, 8087300.0, 195500000.0, 0.0, 12589000.0, 32299750.0, 0.0, 524486900.0, 84901200.0, 0.0, 3372080.0, 132846000.0, 1957750.0, 14506000.0, 51801000.0, 458806000.0, 98255000.0, 140660666.66666666, 15708000.0, 20379000.0, 3445960000.0, 3721633333.3333335, 3967550000.0]}


## `/api/protein-groups`

Use this route to download protein groups related data such as TMT intensities, for specific protein groups and specific raw files. 

Example:

    curl -H 'Content-Type: application/json' --data '{"project": "lsarp", "pipeline": "sa-tmt11", "columns": ["Reporter intensity corrected"], "protein_names": ["QC1|Peptide1"]}'  https://example.com/api/protein-groups

    "{\"RawFile\":{\"0\":\"SA021_210531_C.raw\",\"1\":\"SA021_210531_D.raw\",\"2\":\"SA021_210531_E.raw\",\"3\":\"SA021_210531_F.raw\",\"4\":\"SA021_210531_H.raw\"},\"Majority protein IDs\":{\"0\":\"QC1|Peptide1\",\"1\":\"QC1|Peptide1\",\"2\":\"QC1|Peptide1\",\"3\":\"QC1|Peptide1\",\"4\":\"QC1|Peptide1\"},\"Reporter intensity corrected 1\":{\"0\":93489.0,\"1\":351390.0,\"2\":103270.0,\"3\":216110.0,\"4\":228090.0},\"Reporter intensity corrected 2\":{\"0\":131730.0,\"1\":434210.0,\"2\":103280.0,\"3\":301800.0,\"4\":378080.0},\"Reporter intensity corrected 3\":{\"0\":103320.0,\"1\":447160.0,\"2\":125940.0,\"3\":314060.0,\"4\":429110.0},\"Reporter intensity corrected 4\":{\"0\":123840.0,\"1\":428800.0,\"2\":132820.0,\"3\":326520.0,\"4\":374890.0},\"Reporter intensity corrected 5\":{\"0\":140250.0,\"1\":508560.0,\"2\":189750.0,\"3\":303540.0,\"4\":480840.0},\"Reporter intensity corrected 6\":{\"0\":137110.0,\"1\":416800.0,\"2\":123850.0,\"3\":372190.0,\"4\":516980.0},\"Reporter intensity corrected 7\":{\"0\":128280.0,\"1\":405080.0,\"2\":117990.0,\"3\":317570.0,\"4\":415010.0},\"Reporter intensity corrected 8\":{\"0\":129650.0,\"1\":465560.0,\"2\":112340.0,\"3\":333770.0,\"4\":471380.0},\"Reporter intensity corrected 9\":{\"0\":105690.0,\"1\":387750.0,\"2\":123200.0,\"3\":280420.0,\"4\":426380.0},\"Reporter intensity corrected 10\":{\"0\":106280.0,\"1\":355900.0,\"2\":96945.0,\"3\":287530.0,\"4\":425780.0},\"Reporter intensity corrected 11\":{\"0\":102800.0,\"1\":420890.0,\"2\":111570.0,\"3\":290750.0,\"4\":361690.0}}"


## `/api/rawfile`
This route can be used to modify raw files. Actions are:

- flag - Flag a raw file as anomaly.
- unflag - Unflag a raw file.
- accept - Accept file for downstream use.
- reject - Reject file for downstream use.

The json block has to contain the user UID from the QC pipeline for authentification, project and pipeline slug, and a list of raw file names to be modified.

Example:
    
    curl -H 'Content-Type: application/json' --data '{"project": "lsarp", "pipeline": "sa-tmt11", "raw_file": ["SA001.raw"], "action": "unflag", "uid": "xxx-yyy-zzz"}'





