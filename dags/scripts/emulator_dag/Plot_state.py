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


with open("EMULATOR_state.json") as json_file:
    EMULATOR_state = json.load(json_file)
with open("EMULATOR_design.json") as json_file:
    EMULATOR_design = json.load(json_file)
with open("EMULATOR_config.json") as json_file:
    EMULATOR_config = json.load(json_file)
with open("db_emulator.json") as json_file:
    db_emulator = json.load(json_file)

mbr = "19419"
species = "DOT"  # ['Xv','Glucose','Acetate','DOT','Fluo_RFP','Volume','Dextrine_S','Dextrine_R','Enzyme']

t = EMULATOR_state[mbr]["All"][species]["time"]
y = EMULATOR_state[mbr]["All"][species]["Value"]

plt.plot(t, y, ".")
