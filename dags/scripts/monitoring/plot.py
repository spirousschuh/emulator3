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
    Plot dictionaries with plotly.
    
    Create a multi-panel plot showing simulation and/or experimental data
    for multiple bioreactor experiments. Each state variable gets its own subplot.

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
    
    show_constants: dict, optional
        Dictionary with 'h' for horizontal lines and 'v' for vertical lines to overlay.
    
    layout: dict, optional
        Additional layout parameters for the figure.
    
    Returns
    -------
    plotly.Figure or None
        If return_fig=True, returns the figure object, otherwise None.

    """

    # Extract the list of state variables to plot
    states = list(plot_states.keys())

    # Calculate subplot grid dimensions (2 columns by default)
    div_mod = np.divmod(len(states), 2)
    nx = int(sum(div_mod))  # Number of rows

    # Add extra row for feed plot if needed
    if div_mod[1] == 0:
        nx = nx + bool(feed)

    ny = 2  # Always use 2 columns

    # Initialize subplot counter
    i = 0

    # Create figure with subplots arranged in grid
    fig = make_subplots(rows=nx, cols=ny, shared_xaxes=True)

    # Determine which dataset to use for experiment keys
    if sim_data:
        keys = list(sim_data.keys())
    else:
        keys = list(exp_data.keys())

    # Set up color mapping for different experiments
    cmap = matplotlib.cm.nipy_spectral
    norm = matplotlib.colors.Normalize(vmin=0, vmax=len(keys))
    
    # Iterate through subplot grid
    for row in range(nx):
        for col in range(ny):
            try:
                # Get the state variable for this subplot
                state = states[i]
                
                # Plot data for each experiment key
                for j, key in enumerate(keys):
                    # Add simulation data if provided
                    if sim_data:
                        # Add simulation trace as a line plot
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
                    
                    # Add experimental data if provided
                    if exp_data:
                        # Extract standard deviation if provided for error bars
                        if sd:
                            sd_array = sd[key][state].dropna().values
                        else:
                            sd_array = None
                        # Add experimental measurements with error bars and markers
                        fig.add_trace(
                            go.Scatter(
                                x=exp_data[key][state].dropna().index,
                                y=exp_data[key][state].dropna().values,
                                error_y=dict(
                                    type="data",  # Error bar values given in data coordinates
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

                        # Add horizontal reference line if specified
                        if (
                            "h" in show_constants.keys()
                            and show_constants["h"] is not None
                        ):
                            fig.add_hline(y=show_constants["h"])
                        
                        # Add vertical reference lines if specified
                        if (
                            "v" in show_constants.keys()
                            and show_constants["v"] is not None
                        ):
                            for val in show_constants["v"]:
                                fig.add_vline(x=val)

                # Update axis labels for this subplot
                fig.update_xaxes(title_text="time(h)", row=row + 1, col=col + 1)
                fig.update_yaxes(
                    title_text=state + "(" + plot_states[state] + ")",
                    row=row + 1,
                    col=col + 1,
                )

            except IndexError:
                # Handle case where we run out of states but have feed data to plot
                if i == nx * ny - 1 and bool(feed):
                    for j, key in enumerate(keys):
                        print("Feeeed")
                        # Add feed data as bar chart in the last subplot
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

            # Move to next subplot
            i += 1

    # Apply custom layout parameters if provided
    if layout:
        fig.update_layout(**layout)

    # Display the figure if requested
    if show:
        fig.show()

    # Save figure to HTML file if requested
    if save:
        fig.write_html(path + "/" + fig_name + ".html")

    # Return figure object if requested
    if return_fig:
        return fig
