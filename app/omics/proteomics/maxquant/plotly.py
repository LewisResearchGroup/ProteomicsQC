import pandas as pd
import plotly.express as px


def plot_spectrum(
    df: pd.DataFrame, annot_threshold=1e4, threshold=0, show_fig=True, **kwargs
):
    """Plots spectral data. df is a pandas.DataFrame() with the columns
    mz_array
    intensity
    spectrum
    raw_file
    retention_time[min]
    Scan index
    """
    df = df[df.intensity > threshold]
    df["_index_"] = range(len(df))

    df1 = df.copy()
    df1["Text"] = df1.mz_array.astype(str)
    df1.loc[df1.intensity < annot_threshold, "Text"] = None
    df1.Text.notnull().sum()

    df2 = df.copy()
    df2["intensity"] = 0

    df3 = pd.concat([df1, df2]).sort_values(["_index_", "intensity"])

    grps = df3.groupby("Scan index")

    figs = []
    for label, grp in grps:
        fig = px.line(
            grp,
            x="mz_array",
            y="intensity",
            color="_index_",
            text="Text",
            hover_data={"Text": False, "_index_": False},
            **kwargs,
        )

        fig.update_layout(showlegend=False, title=f"Scan index: {label}")
        fig.update_traces(line=dict(width=1, color="grey"))
        fig.update_traces(textposition="top center")
        fig.update_layout(hovermode="x unified")

        if show_fig:
            fig.show()
        figs.append(fig)

    return figs
