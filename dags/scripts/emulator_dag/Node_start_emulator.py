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
    """
    Initializes the emulator by setting up the database, state, and design
    from configuration files.

    Args:
        db_emulator_template (str): Path to the emulator database template JSON file.
        db_emulator_output (str): Path to write the initial emulator database.
        emulator_config_file (str): Path to the main emulator configuration JSON file.
        first_state_output_file (str): Path to write the initial emulator state.
        first_design_output_file (str): Path to write the initial emulator design.
    """
    # Load the emulator database template.
    with open(db_emulator_template) as json_file:
        db_emulator = json.load(json_file)
    # Write the initial database state to the output file.
    with open(db_emulator_output, "w") as outfile:
        json.dump(db_emulator, outfile)
    # Load the main emulator configuration.
    with open(emulator_config_file) as json_file:
        EMULATOR_config = json.load(json_file)

    # Get lists of bioreactors and species from the configuration.
    brxtor_list = EMULATOR_config["Brxtor_list"]
    species_list = EMULATOR_config["Species_list"]

    # Initialize the state dictionary with current time and iteration count.
    EMULATOR_state = {"time_absolute": time.time(), "time": 0, "iter": 0}
    # Initialize state for each bioreactor.
    for i1 in brxtor_list:
        EMULATOR_state[i1] = {"All": {}, "Sample": {}, "Current": {}}
        # Initialize state for each species within the bioreactor.
        for i2 in species_list:
            # 'All' stores the complete history of the species' values over time.
            EMULATOR_state[i1]["All"][i2] = {
                "time": [0],
                "Value": [EMULATOR_config[i1]["IC"][i2]],  # Set initial condition
            }
            # 'Sample' stores the history of sampled values.
            EMULATOR_state[i1]["Sample"][i2] = {"time": [], "Value": []}
            # 'Current' stores the most recent value for quick access.
            EMULATOR_state[i1]["Current"][i2] = EMULATOR_config[i1]["IC"][i2]

    # Initialize the design dictionary with the absolute start time.
    EMULATOR_design = {"time_start_absolute": EMULATOR_state["time_absolute"]}
    # Configure the design for each bioreactor based on the config file.
    for i1 in brxtor_list:
        EMULATOR_design[i1] = {}
        # Set up pulse profiles for different feeds.
        EMULATOR_design[i1]["Pulses"] = {
            "time_pulse": EMULATOR_config[i1]["Pulse_profile"]["time_pulse"],
            "Feed_pulse": EMULATOR_config[i1]["Pulse_profile"]["Feed_pulse"],
            "time_dextrine": EMULATOR_config[i1]["Pulse_profile"]["time_dextrine"],
            "Feed_dextrine": EMULATOR_config[i1]["Pulse_profile"]["Feed_dextrine"],
            "time_enzyme": EMULATOR_config[i1]["Pulse_profile"]["time_enzyme"],
            "Feed_enzyme": EMULATOR_config[i1]["Pulse_profile"]["Feed_enzyme"],
            "time_sample": EMULATOR_config[i1]["time_sample"]["Xv"],
        }

        # Define sampling times for each species.
        EMULATOR_design[i1]["time_sample"] = {}
        for i2 in EMULATOR_config["Species_list"]:
            EMULATOR_design[i1]["time_sample"][i2] = EMULATOR_config[i1]["time_sample"][
                i2
            ]

        # Set feed concentrations.
        EMULATOR_design[i1]["Glucose_feed"] = EMULATOR_config[i1]["Glucose_feed"]
        EMULATOR_design[i1]["Dextrine_feed"] = EMULATOR_config[i1]["Dextrine_feed"]
        EMULATOR_design[i1]["Enzyme_feed"] = EMULATOR_config[i1]["Enzyme_feed"]

        # Set induction parameters.
        EMULATOR_design[i1]["Induction_time"] = EMULATOR_config[i1]["Induction_time"]
        EMULATOR_design[i1]["Inductor_conc"] = EMULATOR_config[i1]["Inductor_conc"]

    # Write the initial state to a JSON file.
    with open(first_state_output_file, "w") as outfile:
        json.dump(EMULATOR_state, outfile)

    # Write the initial design to a JSON file.
    with open(first_design_output_file, "w") as outfile:
        json.dump(EMULATOR_design, outfile)

    # %%  Write feed profiles to the emulator database (db_emulator.json)
    for i4 in brxtor_list:

        # Process and write glucose feed setpoints.
        tsf_glucose = EMULATOR_design[i4]["Pulses"]["time_pulse"]
        F_glucose = np.cumsum(EMULATOR_design[i4]["Pulses"]["Feed_pulse"])
        db_emulator[i4]["setpoints"]["Feed_glc_cum_setpoints"] = {
            "setpoint_time": {},
            "Feed_glc_cum_setpoints": {},
        }
        for i5 in range(0, len(tsf_glucose)):
            db_emulator[i4]["setpoints"]["Feed_glc_cum_setpoints"]["setpoint_time"][
                str(i5)
            ] = (tsf_glucose[i5] * 3600)  # Convert time to seconds
            db_emulator[i4]["setpoints"]["Feed_glc_cum_setpoints"][
                "Feed_glc_cum_setpoints"
            ][str(i5)] = F_glucose[i5]

        # Process and write dextrine feed setpoints.
        tsf_dextrine = EMULATOR_design[i4]["Pulses"]["time_dextrine"]
        F_dextrine = np.cumsum(EMULATOR_design[i4]["Pulses"]["Feed_dextrine"])
        db_emulator[i4]["setpoints"]["Feed_dextrine_cum_setpoints"] = {
            "setpoint_time": {},
            "Feed_dextrine_cum_setpoints": {},
        }
        for i5 in range(0, len(tsf_dextrine)):
            db_emulator[i4]["setpoints"]["Feed_dextrine_cum_setpoints"][
                "setpoint_time"
            ][str(i5)] = (tsf_dextrine[i5] * 3600)  # Convert time to seconds
            db_emulator[i4]["setpoints"]["Feed_dextrine_cum_setpoints"][
                "Feed_dextrine_cum_setpoints"
            ][str(i5)] = F_dextrine[i5]

        # Process and write enzyme feed setpoints.
        tsf_enzyme = EMULATOR_design[i4]["Pulses"]["time_enzyme"]
        F_enzyme = np.cumsum(EMULATOR_design[i4]["Pulses"]["Feed_enzyme"])
        db_emulator[i4]["setpoints"]["Feed_enzyme_cum_setpoints"] = {
            "setpoint_time": {},
            "Feed_enzyme_cum_setpoints": {},
        }
        for i5 in range(0, len(tsf_enzyme)):
            db_emulator[i4]["setpoints"]["Feed_enzyme_cum_setpoints"]["setpoint_time"][
                str(i5)
            ] = (tsf_enzyme[i5] * 3600)  # Convert time to seconds
            db_emulator[i4]["setpoints"]["Feed_enzyme_cum_setpoints"][
                "Feed_enzyme_cum_setpoints"
            ][str(i5)] = F_enzyme[i5]

    # Write the updated emulator database with feed profiles to a JSON file.
    with open("db_emulator.json", "w") as outfile:
        json.dump(db_emulator, outfile)
