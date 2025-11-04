"""
Plotting Utilities Module.

Visualization functions for monitoring dashboard and data analysis.
"""

import numpy as np
import matplotlib
import plotly.io as pio
import plotly.graph_objects as go
from plotly.subplots import make_subplots

try:
    pio.renderers.default = "browser"
except:
    pass

import pandas as pd

dissimilar_colors = [
    "#000000",
    "#1CE6FF",
    "#FF34FF",
    "#FF4A46",
    "#008941",
    "#006FA6",
    "#A30059",
    "#FFDBE5",
    "#7A4900",
    "#0000A6",
    "#63FFAC",
    "#B79762",
    "#004D43",
    "#8FB0FF",
    "#997D87",
    "#5A0007",
    "#809693",
    "#FEFFE6",
    "#1B4400",
    "#4FC601",
    "#3B5DFF",
    "#4A3B53",
    "#FF2F80",
    "#61615A",
    "#BA0900",
    "#6B7900",
    "#00C2A0",
    "#FFAA92",
    "#FF90C9",
    "#B903AA",
    "#D16100",
    "#DDEFFF",
    "#000035",
    "#7B4F4B",
    "#A1C299",
    "#300018",
    "#0AA6D8",
    "#013349",
    "#00846F",
    "#372101",
    "#FFB500",
    "#C2FFED",
    "#A079BF",
    "#CC0744",
    "#C0B9B2",
    "#C2FF99",
    "#001E09",
    "#00489C",
    "#6F0062",
    "#0CBD66",
    "#EEC3FF",
    "#456D75",
    "#B77B68",
    "#7A87A1",
    "#788D66",
    "#885578",
    "#FAD09F",
    "#FF8A9A",
    "#D157A0",
    "#BEC459",
    "#456648",
    "#0086ED",
    "#886F4C",
    "#34362D",
    "#B4A8BD",
    "#00A6AA",
    "#452C2C",
    "#636375",
    "#A3C8C9",
    "#FF913F",
    "#938A81",
    "#575329",
    "#00FECF",
    "#B05B6F",
    "#8CD0FF",
    "#3B9700",
    "#04F757",
    "#C8A1A1",
    "#1E6E00",
    "#7900D7",
    "#A77500",
    "#6367A9",
    "#A05837",
    "#6B002C",
    "#772600",
    "#D790FF",
    "#9B9700",
    "#549E79",
    "#FFF69F",
    "#201625",
    "#72418F",
    "#BC23FF",
    "#99ADC0",
    "#3A2465",
    "#922329",
    "#5B4534",
    "#FDE8DC",
    "#404E55",
    "#0089A3",
    "#CB7E98",
    "#A4E804",
    "#324E72",
    "#6A3A4C",
]


def subplot_dict(
    sim_data=dict(),
    exp_data=dict(),
    sd=dict(),
    plot_states={"X": "g/L", "S": "g/L", "A": "g/L", "DOTm": "%"},
    feed=dict(),
    exp_data_lw=0,
    save=False,
    fig_name="noname",
    path=".",
    show=True,
    return_fig=False,
    show_constants=dict(h=None, v=None),
    layout=dict(),
):
    """
    Plot dictionaries with plotly

    Parameters
    ----------
    sim_data: dict, optional
        Dictionary with user defined keys with pandas.DataFrames with simulation results in values. Default: dict().

    exp_data: dict, optional
        Dictionary with user defined keys with pandas.DataFrames in values. Default: dict().

    plot_states: dict, optional
        Dictionary with states names and units in the values.
        Default::
            {'X': 'g/L',
             'S': 'g/L',
             'A': 'g/L',
             'DOTm': '%'
             }

    exp_data_lw: int, optional
        Line width for experimental data. Default: 0.

    save: bool, optional
        Save output html figure. Default: False.

    fig_name: str, optional
        Name for the figure if save=True. Default: "noname"

    path: str, optional
        Path to where to save the figure if save=True. Default: "."

    show: bool, optional
        If True shows figure. Default: True.

    return_fig: bool, optional
        If True returns plotly.Figure. Default: False.

    """

    states = list(plot_states.keys())

    div_mod = np.divmod(len(states), 2)
    nx = int(sum(div_mod))

    if div_mod[1] == 0:
        nx = nx + bool(feed)

    ny = 2

    # if len(states) == 4:
    #    nx = 2
    #    ny = 2
    # else:
    #    nx = len(states)
    #    ny = 1

    i = 0

    fig = make_subplots(rows=nx, cols=ny, shared_xaxes=True)

    if sim_data:
        keys = list(sim_data.keys())
    else:
        keys = list(exp_data.keys())

    cmap = matplotlib.cm.nipy_spectral
    norm = matplotlib.colors.Normalize(vmin=0, vmax=len(keys))
    for row in range(nx):
        for col in range(ny):
            try:
                state = states[i]
                for j, key in enumerate(keys):
                    if sim_data:
                        fig.add_trace(
                            go.Scatter(
                                x=sim_data[key].index,
                                y=sim_data[key][state],
                                name=str(key) + "_sim_" + state,
                                mode="lines",
                                legendgroup=str(key),
                                legendgrouptitle_text=str(key),
                                line=dict(color=dissimilar_colors[j]),
                            ),
                            row=row + 1,
                            col=col + 1,
                        )
                    if exp_data:
                        # Experimental data
                        if sd:
                            sd_array = sd[key][state].dropna().values
                        else:
                            sd_array = None
                        fig.add_trace(
                            go.Scatter(
                                x=exp_data[key][state].dropna().index,
                                y=exp_data[key][state].dropna().values,
                                error_y=dict(
                                    type="data",  # value of error bar given in data coordinates
                                    array=sd_array,
                                    visible=True,
                                ),
                                name=str(key) + "_meas_" + state,
                                mode="lines+markers",
                                legendgroup=str(key),
                                legendgrouptitle_text=str(key),
                                marker=dict(color=dissimilar_colors[j]),
                                line=dict(
                                    color=dissimilar_colors[j], width=exp_data_lw
                                ),
                            ),
                            row=row + 1,
                            col=col + 1,
                        )

                        if (
                            "h" in show_constants.keys()
                            and show_constants["h"] is not None
                        ):
                            fig.add_hline(y=show_constants["h"])
                        if (
                            "v" in show_constants.keys()
                            and show_constants["v"] is not None
                        ):
                            for val in show_constants["v"]:
                                fig.add_vline(x=val)

                fig.update_xaxes(title_text="time(h)", row=row + 1, col=col + 1)
                fig.update_yaxes(
                    title_text=state + "(" + plot_states[state] + ")",
                    row=row + 1,
                    col=col + 1,
                )

            except IndexError:
                if i == nx * ny - 1 and bool(feed):
                    for j, key in enumerate(keys):
                        print("Feeeed")
                        fig.add_trace(
                            go.Bar(
                                x=feed[key]["ts"],
                                y=feed[key]["value"],
                                name=str(key) + "_feed",
                                legendgroup=str(key),
                                legendgrouptitle_text=str(key),
                                marker_color=dissimilar_colors[j],
                            ),
                            row=row + 1,
                            col=col + 1,
                        )

            i += 1

    if layout:
        fig.update_layout(**layout)

    if show:
        fig.show()

    if save:
        fig.write_html(path + "/" + fig_name + ".html")

    if return_fig:
        return fig
