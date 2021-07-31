# RawTools

RawTools is an open-source and freely available package designed to perform scan data parsing and quantification, and quality control analysis of Thermo Orbitrap raw mass spectrometer files. 
More information is available in the Github [repository](https://github.com/kevinkovalchik/RawTools).

> Kovalchik KA, Colborne S, Spencer SE, Sorensen PH, Chen DDY, Morin GB, et al. RawTools: Rapid and Dynamic Interrogation of Orbitrap Data Files for Mass Spectrometer System Management. J Proteome Res. 2018. doi:10.1021/acs.jproteome.8b00721

## Parameters
Here is the help text that explains the different parameters of _RawTools_ that are relevant for _Proteomics QC_. However, not all of them were tested.


```raw
========== PARAMETERS HELP ==========

Below you will find information on all the parameters available to this application. 
The Parameter field is a (hopefully) descriptive name of the parameter which might 
be referenced when encountering an error. Short form and Long form are how you invoke
the parameters on the command line. You can use either form. 

Required indicates whether the application requires the parameter have a value in order to run.

INFO         DESCRIPTION                                                          ---------------

Parameter: RawFiles                 Indicates input file(s) to be processed, separated by a space if
Short form: -f                      there are multiple files. Must be Thermo .raw files. You must use 
Long form: -files                   either -f or -d to indicate the file(s) to process. 
Required: False

Parameter: Parse                    Parses raw file meta and scan data and writes the output to a 
Short form: -p                      tab-delimited text file. Typically either this output or the 
Long form: -parse                   quant output (-q) is used unless your aim is to simply create 
                                    an MGF or to observe broad metrics using -x.
Long form: -parse
Required: False 

Parameter: Quant                    Similar to parse (-p), but also quantifies reporter ions and write 
Short form: -q                      results to output matrix. Use of this flag requires you also specify 
Long form: -quant                   the reagents used for isobaric labeling with the -r argument 
Required: False                     (e.g. -r TMT10)

Parameter: LabelingReagent          Required for reporter ion quantification. Reagents used to label
Short form: -r                      peptides, required if using quant option. Available options are: 
Long form: -labellingreagent        {TMT0, TMT2, TMT6, TMT10, TMT11, TMT16, iTRAQ4, iTRAQ8}.
Required: False 

Parameter: UnlabeledQuant           Calculate areas of precursor peaks and writes them to the parse or 
Short form: -u                      quant file (ParentPeakArea column). This option is to be used in 
Long form: -unlabeledquant          combination with -p or -q.
Required: False 

Parameter: WriteMGF                 Writes a standard MGF file. To specify a mass cutoff use the -c 
Short form: -m                      argument.
Long form: -mgf
Required: False 

Parameter: MgfMassCutoff            Specify a mass cutoff to be applied when generating MGF files. 
Short form: -c                      May be of use if removal of reporter ions is desired prior to 
Long form: -masscutoff              searching of MS2 spectra. Default is 0.
Required: False 

Parameter: OutputDirectory          The directory in which to write output. Can be a relative or 
Short form: -o                      absolute path to the directory. If it is a relative path it 
Long form: -out                     will be placed inside the directory containing the respective 
Required: False                     raw file. Note that relative paths should not start with a slash. 
                                    If this is left blank the directory where the raw file is stored 
                                    will be used by default.

Parameter: Metrics                  Write a txt file containing general metrics about the MS run.
Short form: -x  
Long form: -metrics
Required: False 

Parameter: Chromatogram             Write a chromatogram to disk. Should be in the format 
Short form: -chro                   "-chro [order][type]", where order is the MS order (or a combination
Long form: -chromatograms           of orders) and type is T, B, or TB (TIC, base peak and both, 
Required: False                     respectively). For example, to generate MS1 and MS2 TIC and base 
                                    peak chromatograms, invoke "-chro 12TB". Or, to generate a MS2 TIC, 
                                    invoke "-chro 2T".
       
Parameter: RefineMassCharge         Refine precursor charge and monoisotopic mass assignments. 
Short form: -R                      Highly recommended if monoisotopic precursor selection was 
Long form: -refinemasscharge        turned off in the instrument method (or peptide match on a 
Required: False                     QE instrument).

Parameter: MinCharge                The minimum charge to consider when refining precursor 
Short form: -min                    mass and charge.
Long form: -mincharge
Required: False 

Parameter: MaxCharge                The maximum charge to consider when refining precursor 
Short form: -max                    mass and charge.
Long form: -maxcharge
Required: False 

Parameter: FastaDB                  Required for an X! Tandem search during QC. Path to a 
Short form: -db                     fasta protein database.
Long form: -fastadb
Required: False 

Parameter: FixedModifications       Fixed modifications to pass to the search, if desired. 
Short form: -fmods                  Use mass@aminoacid1,mass@aminoacid2 format. It is important 
Long form: -fixedmods               that the values are separated with a comma and not spaces. 
Required: False                     Invoke ">RawTools -modifications" to see examples of some 
                                    common modifications         

Parameter: VariableModifications    Variable modifications to pass to the search, if desired. 
Short form: -vmods                  Use mass@aminoacid1,mass@aminoacid2 format. It is important 
Long form: -variablemods            that the values are separated with a comma and not spaces. 
Required: False                     Invoke ">RawTools -modifications" to see examples of some 
                                    common modifications     

Parameter: XTandemDirectory         Specify the path to the X! Tandem directory (the directory 
Short form: -X                      containing "tandem.exe") if you want to run a database search 
Long form: -xtandem                 as part of QC.
Required: False 

Parameter: NumberSpectra            The number of MS2 spectra to be passes to the search engine as 
Short form: -N                      an MGF file. Defaults to 10,000. If N is greater than the number
Long form: -numberspectra           of MS2 scans in a raw file, all MS2 scans will be used.
Required: False 

Parameter: LogDump                  Write the instrument logs from all provided raw files to disk.
Short form: -l  
Long form: -logdump
Required: False 
```