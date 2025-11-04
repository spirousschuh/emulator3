"""
Data Processing Methods Module.

Data manipulation and processing utilities for experimental measurements.
"""

# %% Import
import time
import numpy as np
import pandas as pd

import matplotlib.pyplot as plt
import json


# %% Get Data
def get_data(filename, Exp_train=[], zero_time_position=0):
    """
    Load and process experimental data from Excel file.
    
    Reads measurement data, design conditions, and probe information from
    a multi-sheet Excel file. Filters data for specified experiments and
    organizes into a hierarchical dictionary structure.
    
    Args:
        filename (str): Path to Excel file with sheets: 0=measurements, 1=design, 2=probes.
        Exp_train (list, optional): List of experiment IDs to include. If empty, uses all. Default: [].
        zero_time_position (int, optional): Time offset for zeroing time series. Default: 0.
    
    Returns:
        dict: Nested dictionary with keys 'Measurement', 'Design', 'Probes', each containing
              experiment-specific data organized by species/variables.
    """
    # Load data from three Excel sheets
    # if type(filename)==str:
    X_data = pd.read_excel(filename, sheet_name=0)  # Measurement data
    u_data = pd.read_excel(filename, sheet_name=1)  # Design/control data
    X_probe = pd.read_excel(filename, sheet_name=2)  # Probe data

    # Use all experiments if none specified
    if len(Exp_train) == 0:
        Exp_train = X_data["Exp"].unique()

    # Filter data for training experiments only
    X_data_train = X_data.loc[X_data["Exp"].isin(Exp_train)]
    u_data_train = u_data.loc[u_data["Exp"].isin(Exp_train)]
    X_probe_train = X_probe.loc[X_probe["Exp"].isin(Exp_train)]

    # Extract available species and variable names
    X_species = list(X_data_train["Species"].unique())
    u_keys = list(u_data_train.keys())
    X_probe_keys = list(X_probe_train.keys())

    # Initialize data structure
    Data = {"Measurement": {}, "Design": {}, "Probes": {}}
    Meas = {}
    Design = {}
    Prob = {}
    
    # Process each experiment
    for j in Exp_train:
        # Extract measurement time series for each species
        Spec = {}
        for i in X_species:
            Spec[str(i)] = {
                "time": X_data_train.loc[
                    (X_data_train["Exp"] == j) & (X_data_train["Species"] == i)
                ]
                .loc[:, ["t"]]
                .to_numpy()
                .flatten()
                .tolist()
            }
            Spec[str(i)]["Value"] = (
                X_data_train.loc[
                    (X_data_train["Exp"] == j) & (X_data_train["Species"] == i)
                ]
                .loc[:, ["Value"]]
                .to_numpy()
                .flatten()
                .tolist()
            )

        # Store measurements for this experiment
        # Meas['Exp'+str(j)]=Spec
        Meas[j] = Spec

        # Extract design conditions and control inputs
        Cond = {}
        for i in u_keys:
            if i == "Fecha":
                # Handle date fields as strings
                Cond[str(i)] = (
                    u_data_train.loc[(u_data_train["Exp"] == j)]
                    .loc[:, i]
                    .astype(str)
                    .tolist()
                )
            elif i == "Hora inoculación":
                # Handle inoculation time field
                Cond[str(i)] = u_data_train.loc[(u_data_train["Exp"] == j)].loc[
                    :, i
                ]  # .to_numpy().tolist()
            else:
                # Handle numeric fields
                Cond[str(i)] = (
                    u_data_train.loc[(u_data_train["Exp"] == j)]
                    .loc[:, i]
                    .to_numpy()
                    .tolist()
                )
        
        # Format inoculation time as string
        Cond["Hora inoculación"] = (
            Cond["Hora inoculación"].apply(lambda x: x.strftime("%H:%M:%S")).tolist()
        )
        # Cond['Fecha']=Cond['Fecha'].apply(lambda x: str(x)).tolist()

        # del(Cond['Fecha'])
        # del(Cond['Hora inoculación'])
        # Design['Exp'+str(j)]=Cond
        
        # Store design for this experiment
        Design[j] = Cond

        # Extract probe data
        Pro = {}

        for i in X_probe_keys:
            if i == "Fecha":
                # Handle date fields as strings
                Pro[str(i)] = (
                    X_probe_train.loc[(X_probe_train["Exp"] == j)]
                    .loc[:, i]
                    .astype(str)
                    .tolist()
                )
            elif i == "Hora":
                Pro[str(i)] = X_probe_train.loc[(X_probe_train["Exp"] == j)].loc[
                    :, i
                ]  # .to_numpy().tolist()
            else:
                Pro[str(i)] = (
                    X_probe_train.loc[(X_probe_train["Exp"] == j)]
                    .loc[:, i]
                    .to_numpy()
                    .tolist()
                )
        Pro["Hora"] = Pro["Hora"].apply(lambda x: x.strftime("%H:%M:%S")).tolist()

        time_data_1 = (
            X_probe_train.loc[(X_probe_train["Exp"] == j)].loc[:, "Fecha"].copy()
        )
        time_data_2 = (
            X_probe_train.loc[(X_probe_train["Exp"] == j)].loc[:, "Hora"].copy()
        )

        u_exp = u_data.loc[u_data["Exp"] == j].copy()
        time_start_indices = [
            u_exp["Fecha"].to_list()[0],
            u_exp["Hora inoculación"].to_list()[0],
        ]
        # print(time_data_1)
        merged_time = pd.to_datetime(
            time_data_1.astype(str) + " " + time_data_2.astype(str)
        )
        correction = pd.to_datetime(
            str(time_start_indices[0]) + " " + str(time_start_indices[1])
        )
        corrected_time_0 = merged_time - correction
        corrected_time_hours = corrected_time_0.dt.total_seconds() / 3600

        Pro["t"] = corrected_time_hours.to_numpy().tolist()

        # Pro['Fecha']=Pro['Fecha'].isoformat()
        # del(Pro['Hora'])#=Pro['Hora'].isoformat())
        # del(Pro['Fecha'])
        # Prob['Exp'+str(j)]=Pro
        Prob[j] = Pro

    Data["Measurement"] = Meas
    Data["Design"] = Design
    Data["Probes"] = Prob

    with open("BIOSIM_data.json", "w") as outfile:
        json.dump(Data, outfile)

    return Data


# %% Pretreat Data
def pretreat_data(Exp_train=[]):

    with open("BIOSIM_data.json") as json_file:
        Data = json.load(json_file)

    Data_probes = Data["Probes"]
    Data_design = Data["Design"]
    Data_measurement = Data["Measurement"]

    if len(Exp_train) == 0:
        Exp_train = Data_probes.keys()

    for j in Exp_train:
        Data_probe_time = np.array(Data_probes[j]["t"]).copy()
        for i in Data_probes[j].keys():
            if i != "t":
                Data_probe_j = np.array(Data_probes[j][i]).copy()
                Data_probes[j][i] = Data_probe_j[Data_probe_time >= 0].tolist()
        Data_probes[j]["t"] = Data_probe_time[Data_probe_time >= 0].tolist()
    print(Data_probes[j]["dO2"])
    for j in Exp_train:
        # Data_probes[j]['dO2'],Data_probes[j]['LacH_prod']=probe_model(Data_probes[j],Data_design[j])
        t_interpolation = np.array(Data_measurement[j]["DO"]["time"])
        interpolated_values = np.interp(
            t_interpolation,
            np.array(Data_probes[j]["t"]),
            np.array(Data_probes[j]["dO2"]),
        )
        Data_measurement[j]["DO"]["Value"] = interpolated_values.tolist()

    # return Data_probes,Data_measurement

    Data["Probes"] = Data_probes
    Data["Measurement"] = Data_measurement

    with open("BIOSIM_data.json", "w") as outfile:
        json.dump(Data, outfile)

    return Data
