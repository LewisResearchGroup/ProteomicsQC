from ...plotly_tools import set_template
import plotly.graph_objects as go
try:
    from plotly_resampler import FigureResampler, register_plotly_resampler
except ImportError:  # graceful fallback if dependency missing
    FigureResampler = None
    def register_plotly_resampler():
        return None

colors = ["rgba(100, 0, 0, 0.5)", "rgba(0, 100, 0, 0.5)", "rgba(0, 0, 100, 0.5)"]
DEFAULT_MAX_SAMPLES = 1000  # how many points to show per trace when resampling

set_template()
register_plotly_resampler()


def lines_plot(rawtools_matrix, cols, colors=colors, title=None, **kwargs):
    # Prefer FigureResampler for interactive downsampling; fall back to plain Plotly
    if FigureResampler:
        try:
            fig = FigureResampler(
                go.Figure(), default_n_shown_samples=DEFAULT_MAX_SAMPLES
            )
        except Exception:
            fig = go.Figure()
    else:
        fig = go.Figure()

    for i, col in enumerate(cols):
        trace = go.Scattergl(  # Scattergl for better performance on dense series
            x=rawtools_matrix.index,
            y=rawtools_matrix[col],
            name=col,
            mode="lines",
            line=dict(width=0.5, color=colors[i]),
            **kwargs
        )
        if FigureResampler and isinstance(fig, FigureResampler):
            fig.add_trace(trace, max_n_samples=DEFAULT_MAX_SAMPLES)
        else:
            fig.add_trace(trace)

    fig.update_layout(
        legend_title_text="",
        autosize=True,
        title=title,
        legend=dict(orientation="h"),
        margin=dict(l=70, r=10, b=50, t=50, pad=0),
    )

    fig.update_xaxes(title_text=rawtools_matrix.index.name)
    fig.update_yaxes(ticks="outside", ticklen=8, automargin=True)

    return fig


def histograms(
    rawtools_matrix,
    cols=["ParentIonMass"],
    title=None,
    colors=colors,
    xbins=None,
    nbinsx=None,
):
    fig = go.Figure()
    if len(cols) == 1:
        fig.update_layout(title=cols[0])
        fig.update_layout(showlegend=False)
    for i, col in enumerate(cols):
        fig.add_trace(
            go.Histogram(
                x=rawtools_matrix[col],
                xbins=xbins,
                nbinsx=nbinsx,
                visible="legendonly" if i > 0 else None,
                name=col,
                marker_color=colors[i],
            )
        )
    fig.update_layout(legend_title_text="")
    fig.update_layout(barmode="overlay")
    fig.update_traces(opacity=0.75)
    fig.update_layout(title=title)

    fig.update_layout(
        legend_title_text="",
        autosize=True,
        title=title,
        legend=dict(orientation="h"),
        margin=dict(l=70, r=10, b=50, t=50, pad=0),
    )

    fig.update_yaxes(ticks="outside", ticklen=8, automargin=True)

    return fig
