"""
Digital Twin Initialization Module.

Initializes the digital twin state and configuration at experiment start.
"""

import numpy as np
import json
import time


# %%
def start_dtwin(
        db_twin_template="db_dtwin_template.json",
        db_twin_output="db_dtwin.json",
        config_file="DTWIN_config.json",
        state_output_file="DTWIN_state.json",
        design_output_file="DTWIN_design.json",
        prediction_output_file="DTWIN_prediction.json",
        db_dtwin_output="db_dtwin.json",
):
    """
    Initializes the Digital Twin by setting up the database, state, prediction,
    and design files from configuration.

    Args:
        db_twin_template (str): Path to the digital twin database template JSON file.
        db_twin_output (str): Path to write the initial digital twin database.
        config_file (str): Path to the main digital twin configuration JSON file.
    """
    # Load the digital twin database template.
    with open(db_twin_template) as json_file:
        db_dtwin = json.load(json_file)
    # Write the initial database state to the output file.
    with open(db_twin_output, "w") as outfile:
        json.dump(db_dtwin, outfile)
    # Load the main digital twin configuration.
    with open(config_file) as json_file:
        DTWIN_config = json.load(json_file)

    # Get lists of bioreactors and species from the configuration.
    brxtor_list = DTWIN_config["Brxtor_list"]
    species_list = DTWIN_config["Species_list"]

    # Initialize the state and prediction dictionaries.
    DTWIN_state = {"time_absolute": time.time(), "time": 0, "iter": 0}
    DTWIN_prediction = {}
    for i1 in brxtor_list:
        DTWIN_state[i1] = {"All": {}, "Sample": {}, "Current": {}, "Prediction": {}}
        DTWIN_prediction[i1] = {"Prediction": {}}
        for i2 in species_list:
            # 'All' stores the complete history of the species' values.
            DTWIN_state[i1]["All"][i2] = {
                "time": [0],
                "Value": [DTWIN_config[i1]["IC"][i2]],
            }
            # 'Sample' stores the history of sampled values.
            DTWIN_state[i1]["Sample"][i2] = {"time": [], "Value": []}
            # 'Current' stores the most recent value.
            DTWIN_state[i1]["Current"][i2] = DTWIN_config[i1]["IC"][i2]
            # 'Prediction' stores the predicted future values.
            DTWIN_prediction[i1]["Prediction"][i2] = {
                "time": [0],
                "Value": [DTWIN_config[i1]["IC"][i2]],
            }

    # Initialize the design dictionary with the absolute start time.
    DTWIN_design = {"time_start_absolute": DTWIN_state["time_absolute"]}
    for i1 in brxtor_list:
        DTWIN_design[i1] = {}
        # Set up pulse profiles for different feeds.
        DTWIN_design[i1]["Pulses"] = {
            "time_pulse": DTWIN_config[i1]["Pulse_profile"]["time_pulse"],
            "Feed_pulse": DTWIN_config[i1]["Pulse_profile"]["Feed_pulse"],
            "time_dextrine": DTWIN_config[i1]["Pulse_profile"]["time_dextrine"],
            "Feed_dextrine": DTWIN_config[i1]["Pulse_profile"]["Feed_dextrine"],
            "time_enzyme": DTWIN_config[i1]["Pulse_profile"]["time_enzyme"],
            "Feed_enzyme": DTWIN_config[i1]["Pulse_profile"]["Feed_enzyme"],
            "time_sample": DTWIN_config[i1]["time_sample"]["Xv"],
        }

        # Define sampling times for each species.
        DTWIN_design[i1]["time_sample"] = {}
        for i2 in DTWIN_config["Species_list"]:
            DTWIN_design[i1]["time_sample"][i2] = DTWIN_config[i1]["time_sample"][i2]

        # Set feed concentrations.
        DTWIN_design[i1]["Glucose_feed"] = DTWIN_config[i1]["Glucose_feed"]
        DTWIN_design[i1]["Dextrine_feed"] = DTWIN_config[i1]["Dextrine_feed"]
        DTWIN_design[i1]["Enzyme_feed"] = DTWIN_config[i1]["Enzyme_feed"]

        # Set induction parameters.
        DTWIN_design[i1]["Induction_time"] = DTWIN_config[i1]["Induction_time"]
        DTWIN_design[i1]["Inductor_conc"] = DTWIN_config[i1]["Inductor_conc"]

    # Write the initial state, design, and prediction data to their respective JSON files.
    with open(state_output_file, "w") as outfile:
        json.dump(DTWIN_state, outfile)

    with open(design_output_file, "w") as outfile:
        json.dump(DTWIN_design, outfile)

    with open(prediction_output_file, "w") as outfile:
        json.dump(DTWIN_prediction, outfile)

    # %%  Write feed profiles to the digital twin database (db_dtwin.json)
    for i4 in brxtor_list:

        # Process and write glucose feed setpoints.
        tsf_glucose = DTWIN_design[i4]["Pulses"]["time_pulse"]
        F_glucose = np.cumsum(DTWIN_design[i4]["Pulses"]["Feed_pulse"])
        db_dtwin[i4]["setpoints"]["Feed_glc_cum_setpoints"] = {
            "setpoint_time": {},
            "Feed_glc_cum_setpoints": {},
        }
        for i5 in range(0, len(tsf_glucose)):
            db_dtwin[i4]["setpoints"]["Feed_glc_cum_setpoints"]["setpoint_time"][
                str(i5)
            ] = (tsf_glucose[i5] * 3600)  # Convert time to seconds
            db_dtwin[i4]["setpoints"]["Feed_glc_cum_setpoints"][
                "Feed_glc_cum_setpoints"
            ][str(i5)] = F_glucose[i5]

        # Process and write dextrine feed setpoints.
        tsf_dextrine = DTWIN_design[i4]["Pulses"]["time_dextrine"]
        F_dextrine = np.cumsum(DTWIN_design[i4]["Pulses"]["Feed_dextrine"])
        db_dtwin[i4]["setpoints"]["Feed_dextrine_cum_setpoints"] = {
            "setpoint_time": {},
            "Feed_dextrine_cum_setpoints": {},
        }
        for i5 in range(0, len(tsf_dextrine)):
            db_dtwin[i4]["setpoints"]["Feed_dextrine_cum_setpoints"]["setpoint_time"][
                str(i5)
            ] = (tsf_dextrine[i5] * 3600)  # Convert time to seconds
            db_dtwin[i4]["setpoints"]["Feed_dextrine_cum_setpoints"][
                "Feed_dextrine_cum_setpoints"
            ][str(i5)] = F_dextrine[i5]

        # Process and write enzyme feed setpoints.
        tsf_enzyme = DTWIN_design[i4]["Pulses"]["time_enzyme"]
        F_enzyme = np.cumsum(DTWIN_design[i4]["Pulses"]["Feed_enzyme"])
        db_dtwin[i4]["setpoints"]["Feed_enzyme_cum_setpoints"] = {
            "setpoint_time": {},
            "Feed_enzyme_cum_setpoints": {},
        }
        for i5 in range(0, len(tsf_enzyme)):
            db_dtwin[i4]["setpoints"]["Feed_enzyme_cum_setpoints"]["setpoint_time"][
                str(i5)
            ] = (tsf_enzyme[i5] * 3600)  # Convert time to seconds
            db_dtwin[i4]["setpoints"]["Feed_enzyme_cum_setpoints"][
                "Feed_enzyme_cum_setpoints"
            ][str(i5)] = F_enzyme[i5]

    # Write the updated digital twin database with feed profiles to a JSON file.
    with open(db_dtwin_output, "w") as outfile:
        json.dump(db_dtwin, outfile)
