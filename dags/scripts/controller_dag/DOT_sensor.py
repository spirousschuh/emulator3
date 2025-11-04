"""
DOT (Dissolved Oxygen Tension) Sensor Controller Module.

This module implements a feedback control system for managing dissolved oxygen
levels in bioreactors during fermentation experiments. It monitors DOT measurements,
adjusts feeding strategies based on batch progression, and applies pulse control
when oxygen levels drop critically.

The controller implements two main strategies:
1. Batch timing optimization based on DOT trends
2. Pulse feed adjustment when DOT falls below minimum thresholds
"""

import json
import numpy as np
import matplotlib.pyplot as plt

import time
from scipy.signal import savgol_filter as smooth_filter

# Load configuration and measurement data
with open("db_output.json") as json_file:
    data = json.load(json_file)
with open("Config_dot.json") as json_file:
    Config_dot = json.load(json_file)
with open("Feed_dot.json") as json_file:
    Feed_profile = json.load(json_file)


# Process measurement data for each bioreactor
list_br = list(data.keys())
t_last = np.zeros(len(list_br))

nn = 0
for i in list_br:
    nn = nn + 1

    # Extract time and DOT measurements from database
    tt = np.array(
        list(data[i]["measurements_aggregated"]["DOT"]["measurement_time"].values())
    )
    ddot_raw = np.array(list(data[i]["measurements_aggregated"]["DOT"]["DOT"].values()))

    # Apply smoothing filter to reduce noise in DOT measurements
    try:
        ddot = smooth_filter(ddot_raw, window_length=5, polyorder=0)
    except Exception:
        # If smoothing fails (e.g., not enough data points), use raw data
        ddot = ddot_raw.copy()

    # Convert time from seconds to hours
    tt = tt / 3600
    t_last[nn - 1] = float(tt[-1])

    # Check batch progression status
    if tt[-1] < Config_dot["DOT_node_start"]:
        # Mark batch as still in initial phase
        Config_dot["check_batch"][i] = 1
    else:
        # Filter out early time points before 'forget_before' threshold
        ddot = ddot[tt > Config_dot["forget_before"]]
        tt = tt[tt > Config_dot["forget_before"]]

    # Evaluate batch timing adjustment based on DOT trend
    if (Config_dot["check_batch"][i] == 1) and (tt[-1] >= Config_dot["DOT_node_start"]):
        # Find minimum DOT point (indicates maximum oxygen consumption)
        i_t_min = np.argmin(ddot)

        # Criteria 1: Ensure minimum occurred before current time
        criteria_1 = tt[i_t_min] < tt[-1]

        # Criteria 2: Check if DOT has recovered sufficiently from minimum
        criteria_2 = (max(ddot) - ddot[i_t_min]) * Config_dot["DOT_threshold"] < (
            ddot[-1] - ddot[i_t_min]
        )

        # Decide on batch timing adjustment
        if (criteria_1) and (criteria_2) and (tt[-1] < Config_dot["time_batchEnd"][i]):
            # Shorten batch: DOT recovered faster than expected
            time_batch = round(tt[-1] * 6) / 6
            Config_dot["check_batch"][i] = 0
            print(time_batch, "criteria 2 ", criteria_2, i, "shortened")

        elif tt[-1] >= (Config_dot["time_batch"][i] - 10 / 60):
            # Delay batch: approaching scheduled time without meeting criteria
            time_batch = round(Config_dot["time_batch"][i] * 6) / 6 + 10 / 60
            print(time_batch, i, "delayed")

        else:
            # No change: keep original batch schedule
            time_batch = round(Config_dot["time_batch"][i] * 6) / 6
            print(time_batch, i, "no change")

        # Update batch timing configuration
        Config_dot["time_batch"][i] = time_batch + 0
        Config_dot["time_batchEnd"][i] = time_batch + 0
        delta_time_batch = time_batch - Feed_profile[i]["measurement_time"][0]

        # Shift all feeding times by the batch time delta
        Feed_profile[i]["measurement_time"] = (
            np.array(Feed_profile[i]["measurement_time"]) + delta_time_batch
        ).tolist()

        # Also adjust induction time accordingly
        Config_dot["time_induction"][i] = (
            Config_dot["time_induction"][i] + delta_time_batch
        )

    # Check for pulse feed adjustment after batch phase ends
    if tt[-1] > Config_dot["time_batchEnd"][i]:
        print("pulse check")
        # Reload time data for pulse check (without smoothing)
        tt = (
            np.array(
                list(
                    data[i]["measurements_aggregated"]["DOT"][
                        "measurement_time"
                    ].values()
                )
            )
            / 3600
        )
        ddot = ddot_raw[tt > Config_dot["forget_before"]]
        tt = tt[tt > Config_dot["forget_before"]]

        # Visualize DOT trend for debugging
        plt.plot(tt, ddot)
        plt.show()

        # Check if DOT dropped below minimum threshold
        if min(ddot) < Config_dot["O2min"]:
            # Apply emergency pulse feed to prevent oxygen starvation
            time_uu_corrected = np.array(Feed_profile[i]["measurement_time"])
            uu_corrected = np.array(Feed_profile[i]["feed_profile"])
            # Set future feed rates to 5 (emergency pulse rate)
            uu_corrected[time_uu_corrected > tt[-1]] = 5
            Feed_profile[i]["feed_profile"] = uu_corrected.tolist()
            Feed_profile[i]["setpoint_value"] = np.cumsum(uu_corrected).tolist()

            print("feedback on " + i)


# Update execution time tracker
Config_dot["time_last_exec"] = max(t_last)
plt.show()

# Save updated configuration
with open("Config_dot.json", "w") as outfile:
    json.dump(Config_dot, outfile)

# Save updated feed profiles
with open("Feed_dot.json", "w") as outfile:
    json.dump(Feed_profile, outfile)

# Prepare feed profiles for database upload
for i in list_br:
    # Convert measurement times from hours to seconds
    Feed_profile[i]["measurement_time"] = [
        int(m * 3600) for m in Feed_profile[i]["measurement_time"]
    ]

    # Remove intermediate feed_profile column (not needed in database)
    del Feed_profile[i]["feed_profile"]

# Save final feed profile for database upload
with open("Feed.json", "w") as outfile:
    json.dump(Feed_profile, outfile)
