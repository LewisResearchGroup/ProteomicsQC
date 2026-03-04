import pandas as pd
import numpy as np

from omics.proteomics.maxquant.MaxquantProteinQuantNormalizer import (
    MaxquantProteinQuantNormalizer,
)


INPUT_COLS = [f"Reporter intensity corrected {i}" for i in range(1, 12)]
RESULTS_COLS = [f"{i:02.0f}" for i in range(2, 12)]


def generate_input(n_proteins=10, generator=lambda r, c: 1):
    df = pd.DataFrame(columns=INPUT_COLS + ["RawFile", "Majority protein IDs"])
    df.loc[:, "RawFile"] = ["A"] * n_proteins
    df.loc[:, "Majority protein IDs"] = [f"Protein-{i}" for i in range(n_proteins)]
    for r in df.index:
        for c in range(11):
            df.iloc[r, c] = generator(r, c)
    df = df.apply(pd.to_numeric, errors="ignore")
    return df


def generate_result(n_proteins=10, generator=lambda r, c: 0):
    df = pd.DataFrame(columns=RESULTS_COLS + ["RawFile", "Majority protein IDs"])
    df.loc[:, "RawFile"] = ["A"] * n_proteins
    df.loc[:, "Majority protein IDs"] = [f"Protein-{i}" for i in range(n_proteins)]
    df = df.set_index(["RawFile", "Majority protein IDs"])
    for r, _ in enumerate(df.index):
        for c in range(10):
            df.iloc[r, c] = generator(r, c)
    df.columns.name = "TMT_CHANNEL"
    df = df.apply(pd.to_numeric, errors="ignore")
    return df


class TestMaxquantProteinQuantNormalizer:
    def test_all_ones_returns_all_zeros(self):
        norm = MaxquantProteinQuantNormalizer()
        df = generate_input()
        norm.df_protein_groups = df
        result = norm.normalize().astype(float)
        expected = generate_result().astype(float)
        assert result.equals(expected)

    def test_mean_removed(self):
        df = generate_input(generator=lambda r, c: 1 + (c * 2))
        norm = MaxquantProteinQuantNormalizer()
        norm.df_protein_groups = df
        result = norm.normalize().astype(float)
        expected = generate_result().astype(float)
        assert result.equals(expected)

    def test_same_results_one_or_more_files(self):
        dfA = generate_input(generator=lambda r, c: np.random.gamma(0.25, 1e7))
        dfB = generate_input(generator=lambda r, c: np.random.gamma(0.25, 1e7)).assign(
            RawFile="B"
        )
        dfAB = pd.concat([dfA, dfB])

        norm = MaxquantProteinQuantNormalizer()
        norm.df_protein_groups = dfA
        result_single = norm.normalize()

        norm.df_protein_groups = dfAB
        output_multiple = norm.normalize()

        result_multiple = output_multiple[
            output_multiple.index.get_level_values("RawFile") == "A"
        ]

        assert result_single.equals(result_multiple)
