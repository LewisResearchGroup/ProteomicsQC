
# The datalake

The datalake is the central data storage of the proteomics pipelines framework.
Its location is shared with the web-site and celery workers. The location of the
data lake on the host system can be controled with the 
`DATALAKE=/var/www/html/omics/datalake`
variable in the `.env` file. 

```
/var/www/html/omics/datalake/
├── P
│   └── P1
│       └── P1MQ1
│           ├── config
│           │   ├── fasta.faa
│           │   └── mqpar.xml
│           ├── inputs
│           │   ├── fake3
│           │   ├── SA001-R1-A-200507
│           │   │   └── SA001-R1-A-200507.raw
│           │   ├── SA001-R1-B-200507
│           │   │   └── SA001-R1-B-200507.raw
...
```

The proteomics jobs read the input files from the datalake from the `config` and `input` folders
of the current project and write the _MaxQuant_ and _RawTools_ output to the corresponding `output` directory.
The **output directory is organized by file**, so that all data from one file is collected in one subfolder.

```
...
│           ├── output
│           │   ├── SA001-R1-A-200507.raw
│           │   │   ├── maxquant
│           │   │   │   ├── allPeptides.txt
│           │   │   │   ├── evidence.txt
│           │   │   │   ├── libraryMatch.txt
│           │   │   │   ├── matchedFeatures.txt
│           │   │   │   ├── maxquant_quality_control.csv
│           │   │   │   ├── modificationSpecificPeptides.txt
│           │   │   │   ├── ms3Scans.txt
│           │   │   │   ├── msmsScans.txt
│           │   │   │   ├── msms.txt
│           │   │   │   ├── mzRange.txt
│           │   │   │   ├── Oxidation (M)Sites.txt
│           │   │   │   ├── parameters.txt
│           │   │   │   ├── peptides.txt
│           │   │   │   ├── proteinGroups.txt
│           │   │   │   ├── summary.txt
│           │   │   │   └── tables.pdf
│           │   │   ├── rawtools
│           │   │   │   ├── rawtools_log.txt
│           │   │   │   ├── rawtools_metrics.err
│           │   │   │   ├── rawtools_metrics.out
│           │   │   │   ├── SA001-R1-A-200507.raw_Matrix.txt
│           │   │   │   ├── SA001-R1-A-200507.raw_Metrics.txt
│           │   │   │   ├── SA001-R1-A-200507.raw.mgf
│           │   │   │   ├── SA001-R1-A-200507.raw_Ms2_BP_chromatogram.txt
│           │   │   │   ├── SA001-R1-A-200507.raw_Ms2_TIC_chromatogram.txt
│           │   │   │   ├── SA001-R1-A-200507.raw_Ms_BP_chromatogram.txt
│           │   │   │   └── SA001-R1-A-200507.raw_Ms_TIC_chromatogram.txt
│           │   │   └── rawtools_qc
│           │   │       ├── QcDataTable.csv
│           │   │       ├── QC.xml
│           │   │       ├── rawtools_log.txt
│           │   │       ├── rawtools_qc.err
│           │   │       └── rawtools_qc.out
...
```

Certain fractions of the data are cleaned and stored in a columnar data format (_parquet_) 
to enable fast reads. This data is a simplified and standardized version of the data in the `output` folder
and can be regenerated easily and is organized by data type rather than by 
input file, in contrast to the `output` directory. 

```
│           ├── parquet
│           │   └── protein_groups
│           │       ├── SA001-R1-A-200507.parquet
│           │       ├── SA001-R1-B-200507.parquet
│           │       ├── SA001-R1-blank-200507.parquet
│           │       ├── SA001-R1-C-200507.parquet
│           │       ├── SA001-R1-D-200507.parquet
│           │       ├── SA001-R1-E-200507.parquet
...
```

