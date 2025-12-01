"""
State Plotting Module.

Visualization utilities for bioreactor state variables and trajectories.
"""

import numpy as np
import pandas as pd
import json
import time

import matplotlib.pyplot as plt

# %%


with open("DTWIN_state.json") as json_file:
    DTWIN_state = json.load(json_file)
with open("DTWIN_design.json") as json_file:
    DTWIN_design = json.load(json_file)
with open("DTWIN_config.json") as json_file:
    DTWIN_config = json.load(json_file)
with open("db_output.json") as json_file:
    db_dtwin = json.load(json_file)

mbr = "19428"
species = "Glucose"  # ['Xv','Glucose','Acetate','DOT','Fluo_RFP','Volume','Dextrine_S','Dextrine_R','Enzyme']

t = DTWIN_state[mbr]["Prediction"][species]["time"]
y = DTWIN_state[mbr]["Prediction"][species]["Value"]

# plt.plot(t,y,'.')

ts = (
    np.array(
        list(
            db_dtwin[mbr]["measurements_aggregated"][species][
                "measurement_time"
            ].values()
        )
    )
    / 3600
)
ys = np.array(list(db_dtwin[mbr]["measurements_aggregated"][species][species].values()))

plt.plot(ts, ys, ".r", t, y, "b")
#     plt.show()
