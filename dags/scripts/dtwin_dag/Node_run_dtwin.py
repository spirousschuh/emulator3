"""
Digital Twin Run Node Module.

Executes digital twin prediction and state update iterations.
"""

import numpy as np
import pandas as pd
import json
import time

import method_dtwin

# %%


def run_dtwin():
    with open("DTWIN_state.json") as json_file:
        DTWIN_state = json.load(json_file)
    with open("DTWIN_design.json") as json_file:
        DTWIN_design = json.load(json_file)
    with open("DTWIN_config.json") as json_file:
        DTWIN_config = json.load(json_file)

    time_final_absolute = time.time()
    if len(DTWIN_config["time_execution"]) == 0:
        time_initial_absolute = DTWIN_state["time_absolute"]
        time_start_absolute = DTWIN_design["time_start_absolute"]
        time_initial = (
            DTWIN_config["acceleration"]
            * (time_initial_absolute - time_start_absolute)
            / 3600
        )
        time_final = min(
            DTWIN_config["acceleration"]
            * (time_final_absolute - time_start_absolute)
            / 3600,
            DTWIN_config["experiment_duration"],
        )

    else:
        time_initial = float(DTWIN_config["time_execution"][DTWIN_state["iter"]])
        time_final = float(DTWIN_config["time_execution"][DTWIN_state["iter"] + 1])

    if DTWIN_config["acceleration"] == 60:
        time_initial = round(time_initial)
        time_final = round(time_final)

    DTWIN_state["time_absolute"] = time_final_absolute
    DTWIN_state["time"] = time_final
    DTWIN_state["iter"] = DTWIN_state["iter"] + 1
    print("Time final", time_final)
    # READ FEEDING PROFILE from db_output
    DTWIN_design = method_dtwin.read("db_dtwin.json", DTWIN_design, DTWIN_config)
    # #METHOD SIMULATION
    NEW_DTWIN_state = method_dtwin.simulate(
        time_initial, time_final, DTWIN_state, DTWIN_design, DTWIN_config
    )

    # DTWIN_prediction=method_dtwin.simulate(time_initial,DTWIN_config['experiment_duration'],DTWIN_state,DTWIN_design,DTWIN_config)
    # for i1 in DTWIN_config['Brxtor_list']:
    #     for i2 in DTWIN_config['Species_list']:
    #         NEW_DTWIN_state[i1]['Prediction'][i2]['time']=DTWIN_prediction[i1]['All'][i2]['time']
    #         NEW_DTWIN_state[i1]['Prediction'][i2]['Value']=DTWIN_prediction[i1]['All'][i2]['Value']

    # METHOD OBSERVATION
    NEW_DTWIN_state = method_dtwin.sample(
        time_initial, time_final, NEW_DTWIN_state, DTWIN_design, DTWIN_config
    )

    # WRITE
    WR = method_dtwin.write(
        "db_dtwin.json",
        time_initial,
        time_final,
        NEW_DTWIN_state,
        DTWIN_design,
        DTWIN_config,
    )

    with open("DTWIN_state.json", "w") as outfile:
        json.dump(NEW_DTWIN_state, outfile)
