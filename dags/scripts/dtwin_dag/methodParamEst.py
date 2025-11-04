"""
Parameter Estimation Methods Module.

Model parameter estimation and optimization routines for digital twin.
"""

# %% Import
import time
import numpy as np
import pandas as pd
from scipy.integrate import solve_ivp
from scipy.optimize import shgo, dual_annealing, minimize
from scipy.optimize import approx_fprime
from copy import deepcopy

import json
from function_simulation import function_simulation

import method_dtwin

import matplotlib.pyplot as plt


# %% Optimization
def update_group(mbr_list):
    with open("DTWIN_state.json") as json_file:
        DTWIN_state = json.load(json_file)
    with open("DTWIN_design.json") as json_file:
        DTWIN_design = json.load(json_file)
    with open("DTWIN_config.json") as json_file:
        DTWIN_config = json.load(json_file)
    with open("DTWIN_prediction.json") as json_file:
        DTWIN_prediction = json.load(json_file)
    with open("db_output.json") as json_file:
        db_output = json.load(json_file)

    # DTWIN_config['Species_regression']=['OD600','Glucose','Acetate','DOT','Fluo_RFP']
    Data = get_data(db_output, mbr_list, DTWIN_config["Species_regression"])

    time_final_absolute = time.time()
    time_final = min(
        DTWIN_config["acceleration"]
        * (time_final_absolute - DTWIN_design["time_start_absolute"])
        / 3600,
        DTWIN_config["experiment_duration"],
    )

    DTWIN_design = method_dtwin.read("db_output.json", DTWIN_design, DTWIN_config)

    New_param = optimize_param(
        mbr_list,
        time_final,
        Data,
        DTWIN_config,
        DTWIN_design,
        DTWIN_state,
        optim_options=[3, 2],
    )

    NEW_DTWIN_config, NEW_DTWIN_state = simulate(
        New_param,
        mbr_list,
        time_final,
        Data,
        DTWIN_config,
        DTWIN_design,
        DTWIN_state,
        mode_sim=2,
    )

    WR = method_dtwin.write(
        "db_dtwin.json", 0, time_final, NEW_DTWIN_state, DTWIN_design, NEW_DTWIN_config
    )

    nn_new = 0
    for i1 in mbr_list:
        nn = DTWIN_config["Brxtor_list"].index(i1)
        DTWIN_config["Params"][str(nn)] = NEW_DTWIN_config["Params"][str(nn_new)]
        DTWIN_state[i1] = deepcopy(NEW_DTWIN_state[i1])
        nn_new = nn_new + 1

    if time_final < DTWIN_config["experiment_duration"]:
        DTWIN_predict = method_dtwin.simulate(
            time_final,
            DTWIN_config["experiment_duration"],
            DTWIN_state,
            DTWIN_design,
            DTWIN_config,
        )
        for i1 in DTWIN_config["Brxtor_list"]:
            for i2 in DTWIN_config["Species_list"]:
                DTWIN_prediction[i1]["Prediction"][i2]["time"] = DTWIN_predict[i1][
                    "All"
                ][i2]["time"]
                DTWIN_prediction[i1]["Prediction"][i2]["Value"] = DTWIN_predict[i1][
                    "All"
                ][i2]["Value"]

    with open("DTWIN_config.json", "w") as outfile:
        json.dump(DTWIN_config, outfile)
    with open("DTWIN_prediction.json", "w") as outfile:
        json.dump(DTWIN_prediction, outfile)

    return DTWIN_config, DTWIN_prediction


# %% Optimization
def get_data(db_output, mbr_list, species_regression_list):
    Data = {}

    for exp in mbr_list:
        Data[exp] = {}
        data_list = db_output[exp]["measurements_aggregated"]
        for sp in species_regression_list:  # db_output[exp]['measurements_aggregated']:
            Data[exp][sp] = {}
            if sp in data_list:
                try:
                    Data[exp][sp]["measurement_time"] = list(
                        db_output[exp]["measurements_aggregated"][sp][
                            "measurement_time"
                        ].values()
                    )
                    Data[exp][sp][sp] = list(
                        db_output[exp]["measurements_aggregated"][sp][sp].values()
                    )
                    if sp == "OD600":
                        Data[exp]["Xv"] = {
                            "measurement_time": Data[exp]["OD600"]["measurement_time"],
                            "Xv": (
                                np.array(Data[exp]["OD600"]["OD600"]) / 2.7027
                            ).tolist(),
                        }

                except:
                    print(f"error in {sp}")

    return Data


# %% Optimization
# def get_feed(db_output,mbr_list,species_regression_list):
# Data={}

# for exp in mbr_list:
#     Data[exp]={}
#     data_list=db_output[exp]['measurements_aggregated']
#     for sp in species_regression_list:#db_output[exp]['measurements_aggregated']:
#         Data[exp][sp]={}
#         if sp in data_list:
#             try:
#                Data[exp][sp]['measurement_time']=list(db_output[exp]['measurements_aggregated'][sp]['measurement_time'].values())
#                Data[exp][sp][sp]=list(db_output[exp]['measurements_aggregated'][sp][sp].values())
#                if sp=='OD600':
#                    Data[exp]['Xv']={'measurement_time':Data[exp]['OD600']['measurement_time'],'Xv':(np.array(Data[exp]['OD600']['OD600'])/2.7027).tolist()}

#             except:
#                 print(f'error in {sp}')


# return Data
# %% Optimization
def optimize_param(
    mbr_list,
    time_final,
    DATA,
    DTWIN_config,
    DTWIN_design,
    DTWIN_state,
    optim_options=[5, 5],
):

    TH_base = np.array(
        DTWIN_config["Params"]["0"][0:-2]
        + DTWIN_config["Params"]["0"][-2:] * len(mbr_list)
    )
    THmin = TH_base * 0.8
    THmax = TH_base * 1.2

    bounds_th = list(range(len(THmin)))
    for i in range(len(THmin)):
        bounds_th[i] = (THmin[i], THmax[i])

    t_test0 = time.time()
    e1 = error_exp(
        (THmin + THmax) * 0.75 / 2,
        mbr_list,
        time_final,
        DATA,
        DTWIN_config,
        DTWIN_design,
        DTWIN_state,
    )
    e2 = error_exp(
        (THmin + THmax) / 2,
        mbr_list,
        time_final,
        DATA,
        DTWIN_config,
        DTWIN_design,
        DTWIN_state,
    )
    e3 = error_exp(
        (THmin + THmax) * 1.25 / 2,
        mbr_list,
        time_final,
        DATA,
        DTWIN_config,
        DTWIN_design,
        DTWIN_state,
    )

    t_test = (time.time() - t_test0) / 3

    n_fun_eval0 = round(60 * optim_options[0] / (t_test * 1.2))
    n_fun_eval1 = round(60 * optim_options[1] / (t_test * 1.2))
    print(n_fun_eval0, n_fun_eval1)
    nn = 0

    TH_opt00_collect = np.vstack(
        ((THmin + THmax) * 0.75 / 2, (THmin + THmax) / 2, (THmin + THmax) * 1.25 / 2)
    )
    e_00_collect = np.vstack((e1, e2, e3))

    while nn < n_fun_eval0:
        nn = nn + 1
        TH_opt00 = THmin + np.random.rand(len(THmax)) * (THmax - THmin)

        e_00 = error_exp(
            TH_opt00,
            mbr_list,
            time_final,
            DATA,
            DTWIN_config,
            DTWIN_design,
            DTWIN_state,
        )
        TH_opt00_collect = np.vstack((TH_opt00_collect, TH_opt00))
        e_00_collect = np.vstack((e_00_collect, e_00))

    i_e00 = np.argmin(e_00_collect)
    TH_opt0 = TH_opt00_collect[i_e00, :]

    param = minimize(
        lambda TH: error_exp(
            TH, mbr_list, time_final, DATA, DTWIN_config, DTWIN_design, DTWIN_state
        ),
        TH_opt0,
        bounds=bounds_th,
        method="Nelder-Mead",
        options={"maxfev": n_fun_eval1},
    )

    return param.x


# %% Error calculation
def simulate(
    TH, mbr_list, time_final, DATA, DTWIN_config, DTWIN_design, DTWIN_state, mode_sim=1
):

    list_total = DTWIN_config["Brxtor_list"]

    DTWIN_state_IC = deepcopy(DTWIN_state)
    NEW_DTWIN_config = deepcopy(DTWIN_config)

    NEW_DTWIN_config["Brxtor_list"] = []
    NEW_DTWIN_config["Params"] = {}
    nn = 0
    for i1 in mbr_list:
        # nn=list_total.index(i1)
        NEW_DTWIN_config["Brxtor_list"].append(i1)

        NEW_DTWIN_config["Params"][str(nn)] = (
            TH[0:19].tolist() + TH[[19 + 2 * nn]].tolist() + TH[[20 + 2 * nn]].tolist()
        )
        for i2 in NEW_DTWIN_config["Species_list"]:
            DTWIN_state_IC[i1]["All"][i2] = {
                "time": [0],
                "Value": [NEW_DTWIN_config[i1]["IC"][i2]],
            }
            DTWIN_state_IC[i1]["Sample"][i2] = {"time": [], "Value": []}
            DTWIN_state_IC[i1]["Current"][i2] = NEW_DTWIN_config[i1]["IC"][i2]
        nn = nn + 1

    NEW_DTWIN_state = method_dtwin.simulate(
        0, time_final, DTWIN_state_IC, DTWIN_design, NEW_DTWIN_config
    )
    if mode_sim == 2:
        NEW_DTWIN_config["Noise_concentration"] = 0
        NEW_DTWIN_state = method_dtwin.sample(
            0, time_final, NEW_DTWIN_state, DTWIN_design, NEW_DTWIN_config
        )

    return NEW_DTWIN_config, NEW_DTWIN_state


# %% Error calculation
def error_exp(TH, mbr_list, time_final, DATA, DTWIN_config, DTWIN_design, DTWIN_state):

    er_X = np.array([])

    NEW_DTWIN_config, NEW_DTWIN_state = simulate(
        TH, mbr_list, time_final, DATA, DTWIN_config, DTWIN_design, DTWIN_state
    )
    species_list = DTWIN_config["Species_list"]
    for i1 in mbr_list:
        for i2 in species_list:  # NEW_DTWIN_config['Species_list']:
            if i2 in DATA[i1]:
                ts_samples = np.array(DATA[i1][i2]["measurement_time"]) / 3600
                tt = np.array(NEW_DTWIN_state[i1]["All"][i2]["time"])
                yy = np.array(NEW_DTWIN_state[i1]["All"][i2]["Value"])

                y_ts = np.interp(ts_samples, tt, yy)
                y_exp = np.array(DATA[i1][i2][i2])

                er_X = np.append(er_X, error_f(y_exp, y_ts))
                # if i2=='Xv':
                #     plt.plot(ts_samples,y_exp,'.r',tt,yy,'b')
            #     plt.show()

    print("error er_X: ", sum(abs(er_X)))
    return sum(abs(er_X))


def error_f(yexp, ysim):
    y_model = ysim.flatten()
    y_exp = yexp.flatten()

    er_x0 = abs(y_model - y_exp)
    er_x1 = er_x0 / (max(y_exp) + 1e-6)

    return np.sum(er_x1) / er_x1.size


# %% Error calculation
if __name__ == "__main__":
    NEW_DTWIN_config, NEW_DTWIN_prediction = update_group(
        ["19419", "19420", "19427", "19428", "19435", "19436"]
    )
