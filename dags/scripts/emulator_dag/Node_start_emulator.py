"""
Emulator Initialization Module.

Initializes the emulator state and configuration at experiment start.
"""

import numpy as np
import json
import time


# %%
def start_emu(
        db_emulator_template="db_emulator_template_new.json",
        db_emulator_output="db_emulator.json",
        emulator_config_file="EMULATOR_config.json",
        first_state_output_file="EMULATOR_state.json",
        first_design_output_file="EMULATOR_design.json",
):
    with open(db_emulator_template) as json_file:
        db_emulator = json.load(json_file)
    with open(db_emulator_output, "w") as outfile:
        json.dump(db_emulator, outfile)
    with open(emulator_config_file) as json_file:
        EMULATOR_config = json.load(json_file)

    brxtor_list = EMULATOR_config["Brxtor_list"]
    species_list = EMULATOR_config["Species_list"]

    EMULATOR_state = {"time_absolute": time.time(), "time": 0, "iter": 0}
    for i1 in brxtor_list:
        EMULATOR_state[i1] = {"All": {}, "Sample": {}, "Current": {}}
        for i2 in species_list:
            EMULATOR_state[i1]["All"][i2] = {
                "time": [0],
                "Value": [EMULATOR_config[i1]["IC"][i2]],
            }
            EMULATOR_state[i1]["Sample"][i2] = {"time": [], "Value": []}
            EMULATOR_state[i1]["Current"][i2] = EMULATOR_config[i1]["IC"][i2]

    EMULATOR_design = {"time_start_absolute": EMULATOR_state["time_absolute"]}
    for i1 in brxtor_list:
        EMULATOR_design[i1] = {}
        EMULATOR_design[i1]["Pulses"] = {
            "time_pulse": EMULATOR_config[i1]["Pulse_profile"]["time_pulse"],
            "Feed_pulse": EMULATOR_config[i1]["Pulse_profile"]["Feed_pulse"],
            "time_dextrine": EMULATOR_config[i1]["Pulse_profile"]["time_dextrine"],
            "Feed_dextrine": EMULATOR_config[i1]["Pulse_profile"]["Feed_dextrine"],
            "time_enzyme": EMULATOR_config[i1]["Pulse_profile"]["time_enzyme"],
            "Feed_enzyme": EMULATOR_config[i1]["Pulse_profile"]["Feed_enzyme"],
            "time_sample": EMULATOR_config[i1]["time_sample"]["Xv"],
        }

        EMULATOR_design[i1]["time_sample"] = {}
        for i2 in EMULATOR_config["Species_list"]:
            EMULATOR_design[i1]["time_sample"][i2] = EMULATOR_config[i1]["time_sample"][
                i2
            ]

        EMULATOR_design[i1]["Glucose_feed"] = EMULATOR_config[i1]["Glucose_feed"]
        EMULATOR_design[i1]["Dextrine_feed"] = EMULATOR_config[i1]["Dextrine_feed"]
        EMULATOR_design[i1]["Enzyme_feed"] = EMULATOR_config[i1]["Enzyme_feed"]

        EMULATOR_design[i1]["Induction_time"] = EMULATOR_config[i1]["Induction_time"]
        EMULATOR_design[i1]["Inductor_conc"] = EMULATOR_config[i1]["Inductor_conc"]

    with open(first_state_output_file, "w") as outfile:
        json.dump(EMULATOR_state, outfile)

    with open(first_design_output_file, "w") as outfile:
        json.dump(EMULATOR_design, outfile)

    # %%  Write profiles to db_emulator
    for i4 in brxtor_list:

        tsf_glucose = EMULATOR_design[i4]["Pulses"]["time_pulse"]
        F_glucose = np.cumsum(EMULATOR_design[i4]["Pulses"]["Feed_pulse"])
        db_emulator[i4]["setpoints"]["Feed_glc_cum_setpoints"] = {
            "setpoint_time": {},
            "Feed_glc_cum_setpoints": {},
        }
        for i5 in range(0, len(tsf_glucose)):
            db_emulator[i4]["setpoints"]["Feed_glc_cum_setpoints"]["setpoint_time"][
                str(i5)
            ] = (tsf_glucose[i5] * 3600)
            db_emulator[i4]["setpoints"]["Feed_glc_cum_setpoints"][
                "Feed_glc_cum_setpoints"
            ][str(i5)] = F_glucose[i5]

        tsf_dextrine = EMULATOR_design[i4]["Pulses"]["time_dextrine"]
        F_dextrine = np.cumsum(EMULATOR_design[i4]["Pulses"]["Feed_dextrine"])
        db_emulator[i4]["setpoints"]["Feed_dextrine_cum_setpoints"] = {
            "setpoint_time": {},
            "Feed_dextrine_cum_setpoints": {},
        }
        for i5 in range(0, len(tsf_dextrine)):
            db_emulator[i4]["setpoints"]["Feed_dextrine_cum_setpoints"][
                "setpoint_time"
            ][str(i5)] = (tsf_dextrine[i5] * 3600)
            db_emulator[i4]["setpoints"]["Feed_dextrine_cum_setpoints"][
                "Feed_dextrine_cum_setpoints"
            ][str(i5)] = F_dextrine[i5]

        tsf_enzyme = EMULATOR_design[i4]["Pulses"]["time_enzyme"]
        F_enzyme = np.cumsum(EMULATOR_design[i4]["Pulses"]["Feed_enzyme"])
        db_emulator[i4]["setpoints"]["Feed_enzyme_cum_setpoints"] = {
            "setpoint_time": {},
            "Feed_enzyme_cum_setpoints": {},
        }
        for i5 in range(0, len(tsf_enzyme)):
            db_emulator[i4]["setpoints"]["Feed_enzyme_cum_setpoints"]["setpoint_time"][
                str(i5)
            ] = (tsf_enzyme[i5] * 3600)
            db_emulator[i4]["setpoints"]["Feed_enzyme_cum_setpoints"][
                "Feed_enzyme_cum_setpoints"
            ][str(i5)] = F_enzyme[i5]

    with open("db_emulator.json", "w") as outfile:
        json.dump(db_emulator, outfile)
