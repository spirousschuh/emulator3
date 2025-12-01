"""
Design Creation Module.

Generates experimental design parameters for bioreactor experiments.
"""

import numpy as np
import json

# %% Config Panel
t_duration = 14.0


species_list = [
    "Xv",
    "Glucose",
    "Acetate",
    "DOT",
    "Fluo_RFP",
    "Volume",
    "Dextrine_S",
    "Dextrine_R",
    "Enzyme",
]  # Model species used in the model
species_regression_list = [
    "OD600",
    "Glucose",
    "Acetate",
    "DOT",
    "Fluo_RFP",
]  # Species used to fit the model


species_IC = [
    0.18 * 1,
    3,
    0,
    100,
    0,
    0.01,
    15 * 0.45,
    15 * 0.55,
    0,
]  # Initial states for the species listed above
glucose_IC = [3, 4, 4, 4, 4, 4, 4, 4] * 3  # Initial states for the species listed above


time_pulses = np.arange(5 + 5 / 60, t_duration, 10 / 60)  # Time in hours
time_dextrine = np.arange(5 + 10 / 60, t_duration, 2)  # Time in hours
time_enzyme = np.arange(5 + 11 / 60, t_duration, 0.5)  # Time in hours


time_samples_columns = {
    "col1": np.arange(0.33, t_duration, 1).tolist() + [t_duration],
    "col2": np.arange(0.66, t_duration, 1).tolist() + [t_duration],
    "col3": np.arange(0.99, t_duration, 1).tolist() + [t_duration],
}  # Time in hours
sampling_rate_DOT = 2 / 60  # Time in hours

time_samples_analysis = np.arange(1, t_duration, 1).tolist()

Noise_concentration = 5  # in %
Noise_time = 1  # in %

# mbr_list=np.arange(21340,21364,1) #names of the bioreactors
mbr_list = np.arange(19419, 19443, 1)  # names of the bioreactors

Glucose_feed = [200] * len(mbr_list)  # in g/l
Dextrine_feed = [100] * len(mbr_list)  # in U/l
Enzyme_feed = [3000] * len(mbr_list)  # in g/l

Induction_time = [10] * len(mbr_list)  # Time in hours
Inductor_conc = [1] * len(mbr_list)  # 0 to 1 for now

Params_ref = np.array(
    [
        1.2578,
        0.43041,
        0.6439,
        7.0767,
        0.4063,
        0.1143 * 4,
        0.1848 * 4,
        287.74 * 0 + 0.4242,
        1.586 * 0.7,
        1.5874 * 0.7,
        0.3322 * 0.75,
        0.0371,
        0.0818,
        9000,
        0.1,
        5,
        0.5,
        0.002,
        0.001,
    ]
)  # +[850]+[90])
Params = {}

for i in range(mbr_list.shape[0]):
    Params_ref_row = (
        Params_ref * (1 + 0.00 * (np.random.random(len(Params_ref)) - 0.5) / 2)
    ).tolist()
    Params[i] = (
        Params_ref_row
        + (850 * (1 + 0.00 * (np.random.random(1) - 0.5) / 2)).tolist()
        + (90 * (1 + 0.66 * (np.random.random(1) - 0.5) / 2)).tolist()
    )

time_execution = (
    []
)  # np.arange(0,t_duration+1,1).tolist()# # leave empty for Real Time, otherwise use time in hours

acceleration = 4  # =1 for real time, or choose between [2, 4, 60, 54000]

# %% Create & Fill config file
DTWIN_config = {}

DTWIN_config["Params"] = Params

Exp_list = [str(il) for il in mbr_list]
DTWIN_config["Species_list"] = species_list
DTWIN_config["Species_regression"] = species_regression_list
DTWIN_config["Brxtor_list"] = Exp_list

n1 = 0
for i1 in Exp_list:
    DTWIN_config[i1] = {}
    DTWIN_config[i1]["IC"] = {}
    nn = 0
    for i2 in DTWIN_config["Species_list"]:
        DTWIN_config[i1]["IC"][i2] = species_IC[nn] + 0
        nn = nn + 1
    DTWIN_config[i1]["IC"]["Glucose"] = glucose_IC[n1] + 0
    n1 = n1 + 1

n2 = 0
for i1 in Exp_list:
    DTWIN_config[i1]["Glucose_feed"] = float(Glucose_feed[n2])
    DTWIN_config[i1]["Dextrine_feed"] = float(Dextrine_feed[n2])
    DTWIN_config[i1]["Enzyme_feed"] = float(Enzyme_feed[n2])

    DTWIN_config[i1]["Induction_time"] = float(Induction_time[n2])
    DTWIN_config[i1]["Inductor_conc"] = float(Inductor_conc[n2])

    DTWIN_config[i1]["Pulse_profile"] = {
        "time_pulse": time_pulses.tolist(),
        "Feed_pulse": (0 + np.zeros(len(time_pulses.tolist()))).tolist(),
        "time_dextrine": time_dextrine.tolist(),
        "Feed_dextrine": (50 + np.zeros(len(time_dextrine.tolist()))).tolist(),
        "time_enzyme": time_enzyme.tolist(),
        "Feed_enzyme": (25 + np.zeros(len(time_enzyme.tolist()))).tolist(),
    }

    DTWIN_config[i1]["time_sample"] = {}
    for i2 in DTWIN_config["Species_list"]:
        if n2 < 8:
            DTWIN_config[i1]["time_sample"][i2] = time_samples_columns["col1"]
        elif n2 < 16:
            DTWIN_config[i1]["time_sample"][i2] = time_samples_columns["col2"]
        else:
            DTWIN_config[i1]["time_sample"][i2] = time_samples_columns["col3"]
    n2 = n2 + 1

    # DTWIN_config[i1]['time_sample']['DOT']=np.arange(0,t_duration+sampling_rate_DOT,sampling_rate_DOT).tolist()
    DTWIN_config[i1]["time_sample"]["DOT"] = np.linspace(
        0.04, t_duration, int(t_duration) * 25
    ).tolist()


DTWIN_config["number_br"] = len(mbr_list)

DTWIN_config["time_execution"] = time_execution

DTWIN_config["Noise_concentration"] = Noise_concentration / 100
DTWIN_config["Noise_time"] = Noise_time / 100

DTWIN_config["acceleration"] = acceleration
DTWIN_config["experiment_duration"] = t_duration

DTWIN_config["time_samples_analysis"] = time_samples_analysis
# %% Save design
with open("DTWIN_config.json", "w") as outfile:
    json.dump(DTWIN_config, outfile)
