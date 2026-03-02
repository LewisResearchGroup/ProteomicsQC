import pandas as pd
from pathlib import Path as P

from omics.proteomics import MaxquantReader


PATH = P("tests/omics/data")


class TestMaxquantReader:
    def test__read_tmt11_protein_groups_example1(self):
        fn = PATH / "maxquant" / "tmt11" / "example-1" / "proteinGroups.txt"
        reader = MaxquantReader()
        df = reader.read(fn)
        assert isinstance(df, pd.DataFrame)

    def test__read_tmt11_allPeptides_example0(self):
        fn = PATH / "maxquant" / "tmt11" / "example-0" / "allPeptides.txt"
        reader = MaxquantReader()
        df = reader.read(fn)
        assert isinstance(df, pd.DataFrame), type(df)

    def test__read_tmt11_peptides_example0(self):
        fn = PATH / "maxquant" / "tmt11" / "example-0" / "peptides.txt"
        reader = MaxquantReader()
        df = reader.read(fn)
        assert isinstance(df, pd.DataFrame), type(df)

    def test__read_tmt11_evidence_example0(self):
        fn = PATH / "maxquant" / "tmt11" / "example-0" / "evidence.txt"
        reader = MaxquantReader()
        df = reader.read(fn)
        assert isinstance(df, pd.DataFrame), type(df)

    def test__read_tmt11_msms_example0(self):
        fn = PATH / "maxquant" / "tmt11" / "example-0" / "msms.txt"
        reader = MaxquantReader()
        df = reader.read(fn)
        assert isinstance(df, pd.DataFrame), type(df)

    def test__read_tmt11_mzRange_example0(self):
        fn = PATH / "maxquant" / "tmt11" / "example-0" / "mzRange.txt"
        reader = MaxquantReader()
        df = reader.read(fn)
        assert isinstance(df, pd.DataFrame), type(df)

    def test__read_tmt11_parameters_example0(self):
        fn = PATH / "maxquant" / "tmt11" / "example-0" / "parameters.txt"
        reader = MaxquantReader()
        df = reader.read(fn)
        assert isinstance(df, pd.DataFrame), type(df)

    def test__read_tmt11_protein_groups_example0(self):
        fn = PATH / "maxquant" / "tmt11" / "example-0" / "proteinGroups.txt"
        reader = MaxquantReader()
        df = reader.read(fn)
        assert isinstance(df, pd.DataFrame)

    def test__read_tmt11_summary_example0(self):
        fn = PATH / "maxquant" / "tmt11" / "example-0" / "summary.txt"
        reader = MaxquantReader()
        df = reader.read(fn)
        assert isinstance(df, pd.DataFrame), type(df)
