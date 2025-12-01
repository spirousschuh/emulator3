"""
DOT Controller Configuration Module.

Creates and initializes configuration files for the DOT controller,
setting up batch timing, thresholds, and control parameters.
"""

import numpy as np
import json

# %% Config Panel
mbr_list = np.arange(19419, 19443, 1).astype("str")  # names of the bioreactors
mu_set = np.linspace(0.12, 0.3, len(mbr_list))
# %% Create config
Config_dot = {}
Feed_profile = {}

# %% Fill config
Config_dot["DOT_node_start"] = 3
Config_dot["forget_before"] = 0.5
Config_dot["DOT_threshold"] = 0.7
Config_dot["O2min"] = 20

Config_dot["time_last_exec"] = 0

Config_dot["check_batch"] = {}
Config_dot["time_batchEnd"] = {}
Config_dot["time_batch"] = {}
Config_dot["time_induction"] = {}

time_batchEnd = 7
time_batch = 5
time_induction = 10
time_duration = 16.1

t_pulse = np.arange(time_batch, time_duration, 1 / 6)

nn = 0
for i1 in mbr_list:
    Config_dot["check_batch"][i1] = 1
    Config_dot["time_batchEnd"][i1] = time_batchEnd
    Config_dot["time_batch"][i1] = time_batch
    Config_dot["time_induction"][i1] = time_induction

    Feed_profile[i1] = {"measurement_time": t_pulse.tolist()}
    Feed_profile[i1]["feed_profile"] = (
        (36.33) * mu_set[nn] * np.exp(mu_set[nn] * (t_pulse - t_pulse[0]))
    ).tolist()
    Feed_profile[i1]["setpoint_value"] = (
        np.cumsum(Feed_profile[i1]["feed_profile"])
    ).tolist()

    nn = nn + 1
# %% Save design
with open("Config_dot.json", "w") as outfile:
    json.dump(Config_dot, outfile)

with open("Feed_dot.json", "w") as outfile:
    json.dump(Feed_profile, outfile)
