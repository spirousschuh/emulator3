"""
Digital Twin Initialization Module.

Initializes the digital twin state and configuration at experiment start.
"""

import numpy as np
import pandas as pd
import json
import time


# %%
def start_dtwin():
    with open("db_dtwin_template.json") as json_file:
        db_dtwin = json.load(json_file)
    with open("db_dtwin.json", "w") as outfile:
        json.dump(db_dtwin, outfile)
    with open("DTWIN_config.json") as json_file:
        DTWIN_config = json.load(json_file)

    brxtor_list = DTWIN_config["Brxtor_list"]
    species_list = DTWIN_config["Species_list"]

    DTWIN_state = {"time_absolute": time.time(), "time": 0, "iter": 0}
    DTWIN_prediction = {}
    for i1 in brxtor_list:
        DTWIN_state[i1] = {"All": {}, "Sample": {}, "Current": {}, "Prediction": {}}
        DTWIN_prediction[i1] = {"Prediction": {}}
        for i2 in species_list:
            DTWIN_state[i1]["All"][i2] = {
                "time": [0],
                "Value": [DTWIN_config[i1]["IC"][i2]],
            }
            DTWIN_state[i1]["Sample"][i2] = {"time": [], "Value": []}
            DTWIN_state[i1]["Current"][i2] = DTWIN_config[i1]["IC"][i2]
            DTWIN_prediction[i1]["Prediction"][i2] = {
                "time": [0],
                "Value": [DTWIN_config[i1]["IC"][i2]],
            }

    DTWIN_design = {"time_start_absolute": DTWIN_state["time_absolute"]}
    for i1 in brxtor_list:
        DTWIN_design[i1] = {}
        DTWIN_design[i1]["Pulses"] = {
            "time_pulse": DTWIN_config[i1]["Pulse_profile"]["time_pulse"],
            "Feed_pulse": DTWIN_config[i1]["Pulse_profile"]["Feed_pulse"],
            "time_dextrine": DTWIN_config[i1]["Pulse_profile"]["time_dextrine"],
            "Feed_dextrine": DTWIN_config[i1]["Pulse_profile"]["Feed_dextrine"],
            "time_enzyme": DTWIN_config[i1]["Pulse_profile"]["time_enzyme"],
            "Feed_enzyme": DTWIN_config[i1]["Pulse_profile"]["Feed_enzyme"],
            "time_sample": DTWIN_config[i1]["time_sample"]["Xv"],
        }

        DTWIN_design[i1]["time_sample"] = {}
        for i2 in DTWIN_config["Species_list"]:
            DTWIN_design[i1]["time_sample"][i2] = DTWIN_config[i1]["time_sample"][i2]

        DTWIN_design[i1]["Glucose_feed"] = DTWIN_config[i1]["Glucose_feed"]
        DTWIN_design[i1]["Dextrine_feed"] = DTWIN_config[i1]["Dextrine_feed"]
        DTWIN_design[i1]["Enzyme_feed"] = DTWIN_config[i1]["Enzyme_feed"]

        DTWIN_design[i1]["Induction_time"] = DTWIN_config[i1]["Induction_time"]
        DTWIN_design[i1]["Inductor_conc"] = DTWIN_config[i1]["Inductor_conc"]

    with open("DTWIN_state.json", "w") as outfile:
        json.dump(DTWIN_state, outfile)

    with open("DTWIN_design.json", "w") as outfile:
        json.dump(DTWIN_design, outfile)

    with open("DTWIN_prediction.json", "w") as outfile:
        json.dump(DTWIN_prediction, outfile)

    # %%  Write profiles to db_dtwin
    for i4 in brxtor_list:

        tsf_glucose = DTWIN_design[i4]["Pulses"]["time_pulse"]
        F_glucose = np.cumsum(DTWIN_design[i4]["Pulses"]["Feed_pulse"])
        db_dtwin[i4]["setpoints"]["Feed_glc_cum_setpoints"] = {
            "setpoint_time": {},
            "Feed_glc_cum_setpoints": {},
        }
        for i5 in range(0, len(tsf_glucose)):
            db_dtwin[i4]["setpoints"]["Feed_glc_cum_setpoints"]["setpoint_time"][
                str(i5)
            ] = (tsf_glucose[i5] * 3600)
            db_dtwin[i4]["setpoints"]["Feed_glc_cum_setpoints"][
                "Feed_glc_cum_setpoints"
            ][str(i5)] = F_glucose[i5]

        tsf_dextrine = DTWIN_design[i4]["Pulses"]["time_dextrine"]
        F_dextrine = np.cumsum(DTWIN_design[i4]["Pulses"]["Feed_dextrine"])
        db_dtwin[i4]["setpoints"]["Feed_dextrine_cum_setpoints"] = {
            "setpoint_time": {},
            "Feed_dextrine_cum_setpoints": {},
        }
        for i5 in range(0, len(tsf_dextrine)):
            db_dtwin[i4]["setpoints"]["Feed_dextrine_cum_setpoints"]["setpoint_time"][
                str(i5)
            ] = (tsf_dextrine[i5] * 3600)
            db_dtwin[i4]["setpoints"]["Feed_dextrine_cum_setpoints"][
                "Feed_dextrine_cum_setpoints"
            ][str(i5)] = F_dextrine[i5]

        tsf_enzyme = DTWIN_design[i4]["Pulses"]["time_enzyme"]
        F_enzyme = np.cumsum(DTWIN_design[i4]["Pulses"]["Feed_enzyme"])
        db_dtwin[i4]["setpoints"]["Feed_enzyme_cum_setpoints"] = {
            "setpoint_time": {},
            "Feed_enzyme_cum_setpoints": {},
        }
        for i5 in range(0, len(tsf_enzyme)):
            db_dtwin[i4]["setpoints"]["Feed_enzyme_cum_setpoints"]["setpoint_time"][
                str(i5)
            ] = (tsf_enzyme[i5] * 3600)
            db_dtwin[i4]["setpoints"]["Feed_enzyme_cum_setpoints"][
                "Feed_enzyme_cum_setpoints"
            ][str(i5)] = F_enzyme[i5]

    with open("db_dtwin.json", "w") as outfile:
        json.dump(db_dtwin, outfile)
