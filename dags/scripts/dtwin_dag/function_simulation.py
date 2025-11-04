"""
Fermentation Process Simulation Module.

This module provides simulation capabilities for fed-batch fermentation processes,
including discrete event handling (feeding pulses, sampling, enzyme addition) and
continuous state dynamics. The simulation integrates ODE models with discrete
interventions to accurately model bioreactor behavior.

Key Features:
- Multi-reactor batch simulations
- Discrete event handling (pulses, samples, dextrine, enzyme feeds)
- ODE-based state dynamics
- Medium feeding modeling
"""

import numpy as np
import pandas as pd

import matplotlib.pyplot as plt

from scipy.integrate import solve_ivp


def function_simulation(ts0, Xo0, u0, THs, D0={}):
    """
    Simulates a fed-batch fermentation process over a given time span,
    considering discrete events like feeding pulses and sampling.

    Args:
        ts0 (np.ndarray): Start and end time of the simulation [start, end].
        Xo0 (np.ndarray): Initial state vector of the system.
        u0 (np.ndarray): Vector of control inputs and operational parameters.
        THs (dict): Dictionary of model parameter sets. The key corresponds to u0[1].
        D0 (dict, optional): Dictionary containing time-series data for discrete events
                             (e.g., 'time_pulse', 'Feed_pulse'). Defaults to {}.

    Returns:
        tuple: A tuple containing:
            - tt (np.ndarray): The time points of the simulation.
            - yy (np.ndarray): The state vector at each time point.
    """
    # Select the model parameters based on the control input u0[1]
    TH1 = np.array(THs[str(int(u0[1]))])

    # Define simulation start and end times
    ts_start = ts0[0]
    ts_end = ts0[-1]

    # --- Extract and filter discrete event data for the current simulation window ---
    # Pulse feed events (e.g., glucose)
    time_pulse_all = np.array(D0["time_pulse"])
    t_u_pulse = np.round(
        time_pulse_all[(time_pulse_all >= ts_start) & (time_pulse_all <= ts_end)],
        decimals=6,
    )
    Feed_pulse_all = np.array(D0["Feed_pulse"])
    uu_pulse = Feed_pulse_all[(time_pulse_all >= ts_start) & (time_pulse_all <= ts_end)]

    # Sampling events
    time_sample_all = np.array(D0["time_sample"])
    t_u_sample = np.round(
        time_sample_all[(time_sample_all >= ts_start) & (time_sample_all <= ts_end)],
        decimals=6,
    )

    # Dextrine feed events
    time_dextrine_all = np.array(D0["time_dextrine"])
    t_u_dextrine = np.round(
        time_dextrine_all[
            (time_dextrine_all >= ts_start) & (time_dextrine_all <= ts_end)
        ],
        decimals=6,
    )
    Feed_dextrine_all = np.array(D0["Feed_dextrine"])
    uu_dextrine = Feed_dextrine_all[
        (time_dextrine_all >= ts_start) & (time_dextrine_all <= ts_end)
    ]

    # Enzyme feed events
    time_enzyme_all = np.array(D0["time_enzyme"])
    t_u_enzyme = np.round(
        time_enzyme_all[(time_enzyme_all >= ts_start) & (time_enzyme_all <= ts_end)],
        decimals=6,
    )
    Feed_enzyme_all = np.array(D0["Feed_enzyme"])
    uu_enzyme = Feed_enzyme_all[
        (time_enzyme_all >= ts_start) & (time_enzyme_all <= ts_end)
    ]

    # Medium feed events (continuous addition modeled as discrete steps)
    time_medium_all = np.arange(10 / 60, time_pulse_all[-1] + 10 / 60, 10 / 60)
    t_u_medium = np.round(
        time_medium_all[(time_medium_all >= ts_start) & (time_medium_all <= ts_end)],
        decimals=6,
    )

    # Combine all event times into a single sorted array of unique time points
    time_u_concat = np.concatenate(
        (t_u_pulse, t_u_sample, t_u_dextrine, t_u_enzyme, t_u_medium)
    )
    t_u = np.unique(time_u_concat)

    # If there are no events in the time window, set up for a single integration step
    if len(t_u) == 0:
        t_u = np.array([ts_start, ts_end])
        uu = np.array([0, 0])

    else:
        # Ensure the simulation start and end times are included in the event times
        if ts_start < t_u[0]:
            t_u = np.append(ts_start, t_u)
        if ts_end > t_u[-1]:
            t_u = np.append(t_u, ts_end)

    # Initialize state variables and result arrays
    Xo1 = Xo0.copy()

    tt = np.array(ts_start)
    yy = np.array([Xo1])
    yy = yy.transpose()

    ni = 0

    # --- Main simulation loop: iterate over intervals defined by event times ---
    for i in t_u[:-1]:
        # Define the time span for the current integration step
        ts1 = np.linspace(t_u[ni], t_u[ni + 1], 5 + 1)
        V_old = Xo1[5]  # Volume before discrete event

        # --- Apply discrete changes to the state vector at the beginning of the interval ---
        if i in t_u_pulse:
            index_u_pulse = int(np.where(t_u_pulse == t_u[ni])[0][0])
            Xo1[1] = (
                Xo1[1] + uu_pulse[index_u_pulse] * 1e-6 * u0[0] / 0.01
            )  # Add substrate
            Xo1[5] = Xo1[5] + uu_pulse[index_u_pulse] * 1e-6  # Add volume

        if i in t_u_dextrine:
            index_u_dextrine = int(np.where(t_u_dextrine == t_u[ni])[0][0])
            Xo1[6] = Xo1[6] + uu_dextrine[index_u_dextrine] * 1e-6 * u0[5] / 0.01 * (
                0.46
            )  # Add Gs
            Xo1[7] = Xo1[7] + uu_dextrine[index_u_dextrine] * 1e-6 * u0[5] / 0.01 * (
                1 - 0.46
            )  # Add Gr
            Xo1[5] = Xo1[5] + uu_dextrine[index_u_dextrine] * 1e-6  # Add volume

        if i in t_u_enzyme:
            index_u_enzyme = int(np.where(t_u_enzyme == t_u[ni])[0][0])
            Xo1[8] = (
                Xo1[8] + uu_enzyme[index_u_enzyme] * 1e-6 * u0[6] / 0.01 * 0.7
            )  # Add Enzyme
            Xo1[5] = Xo1[5] + uu_enzyme[index_u_enzyme] * 1e-6  # Add volume

        if i in t_u_sample:
            Xo1[5] = Xo1[5] - 25 * 1e-6  # Remove volume for sampling
        if i in t_u_medium:
            Xo1[5] = Xo1[5] + 1 * 1e-6  # Add volume for medium

        # --- Adjust concentrations for volume changes (dilution effect) ---
        V_new = Xo1[5]
        Xo1 = Xo1 * V_old / V_new  # Dilute all components
        Xo1[5] = V_new  # Reset volume to its new value

        # --- Perform continuous simulation over the interval using the ODE solver ---
        t, y = intM(ts1, Xo1, u0, TH1)
        Xo1 = y[:, -1].copy()  # Update state for the next interval

        # --- Store results ---
        tt = np.append(tt, t[1:])
        yy = np.append(yy, y[:, 1:], axis=1)
        ni = ni + 1

    return tt, yy.transpose()


# %%
def odeFB(t, Xo, THo, u):
    """
    Defines the system of Ordinary Differential Equations (ODEs) for the fed-batch process.

    Args:
        t (float): Current time.
        Xo (np.ndarray): Current state vector.
        THo (np.ndarray): Vector of model parameters.
        u (np.ndarray): Vector of control inputs and operational parameters.

    Returns:
        np.ndarray: The derivatives of the state vector (dX/dt).
    """

    X = Xo.copy()
    TH = THo.copy()
    # Ensure state variables are non-negative to avoid numerical issues
    X = np.maximum(X, 1e-9)

    # --- Unpack state variables ---
    Xv = X[0]  # Biomass concentration
    S = X[1]  # Substrate concentration (glucose)
    A = X[2]  # By-product concentration (acetate)
    DOT = X[3]  # Dissolved Oxygen Tension (%)
    P = X[4]  # Product concentration

    V = X[5]  # Volume

    Gs = X[6]  # Soluble dextrin
    Gr = X[7]  # Resistant dextrin
    E = X[8]  # Enzyme concentration

    # Clamp DOT to a maximum of 100%
    DOT = np.minimum(DOT, 100)

    # --- Unpack model parameters ---
    qs_max = TH[0]
    fracc_q_ox_max = TH[1]

    qa_max = TH[2]
    Ksi = TH[3]  # Substrate inhibition constant for acetate uptake

    Ys_ox = TH[4]  # Yield of biomass from substrate (oxidative)
    Ya_p = TH[5]  # Yield of acetate from substrate (overflow)
    Ya_c = TH[6]  # Yield of biomass from acetate
    Kai = TH[7]  # Acetate inhibition constant for acetate uptake
    Yo_ox = TH[8]  # Yield of oxygen from substrate (oxidative)
    Yo_a = TH[9]  # Yield of oxygen from acetate
    Yxs_of = TH[10]  # Yield of biomass from substrate (overflow)
    Y_ps = 1  # Yield of product from substrate

    Ks = TH[11]  # Monod constant for substrate

    Ka = TH[12]  # Monod constant for acetate
    n_ox = 4  # Hill coefficient for oxygen limitation

    Ko = 0.10  # Monod constant for oxygen

    k_s = TH[16]  # Rate constant for soluble dextrin hydrolysis
    k_r = TH[17]  # Rate constant for resistant dextrin hydrolysis
    Krs = TH[18]  # Michaelis-Menten constant for dextrin hydrolysis

    kla = TH[19]  # Volumetric mass transfer coefficient for oxygen
    k_sensor = TH[20]  # Time constant for the DOT sensor

    # --- Constants ---
    DO_star = 100  # Saturated DOT concentration
    H = 13000  # Henry's law constant
    rev = 30 * 1e-6 * 1  # Evaporation rate
    Y_g = 1.11  # Yield of glucose from dextrin hydrolysis

    # Dilution rate due to evaporation
    Dev = rev / V

    # --- Calculate specific rates (q) ---
    # Specific substrate uptake rate (Monod kinetics)
    qs = qs_max * S / (S + Ks)
    q_ox_max = fracc_q_ox_max * qs_max

    # Quasi-steady-state assumption for DOT to calculate its steady-state value (DOT_ss)
    q_ox_ss = qs * (1 / ((qs / q_ox_max) ** n_ox + 1)) ** (1 / n_ox)
    qac_ss = qa_max * A / (A + Ka) * Kai / (Kai + S)
    b_ss = Ko + (q_ox_ss * Yo_ox + qac_ss * Yo_a) * Xv * H / (kla - Dev * 0) - DO_star
    c_ss = -DO_star * Ko
    DOT_ss = (-b_ss + (b_ss * b_ss - 4 * c_ss) ** 0.5) / 2

    # Oxidative substrate consumption rate, limited by DOT
    q_ox = (
        qs * (1 / ((qs / q_ox_max) ** n_ox + 1)) ** (1 / n_ox) * DOT_ss / (DOT_ss + Ko)
    )
    # Overflow (fermentative) substrate consumption rate
    q_of = qs - q_ox

    # Specific acetate consumption rate, limited by DOT
    qac = qa_max * A / (A + Ka) * Kai / (Kai + S) * DOT_ss / (DOT_ss + Ko)

    # Specific acetate production rate from overflow metabolism
    qap = q_of * Ya_p

    # Specific growth rate (mu)
    mu = q_ox * Ys_ox + qac * Ya_c + Yxs_of * q_of

    # Product formation, conditional on time
    if t >= u[3]:
        s_prod = u[4]
    else:
        s_prod = 0

    q_prod = s_prod * Y_ps

    # Dextrin hydrolysis rates
    r_s = k_s * E * Gs / (Gs + Gr + Krs)  # Soluble dextrin
    r_r = k_r * E * Gr / (Gs + Gr + Krs)  # Resistant dextrin

    # --- Define the differential equations ---
    dXv = (mu) * Xv + Dev * Xv  # Biomass change
    dS = -qs * Xv + Y_g * (r_s + r_r) + Dev * S  # Substrate (glucose) change
    dA = qap * Xv - qac * Xv + Dev * A  # By-product (acetate) change
    dDOT = k_sensor * (DOT_ss - DOT)  # DOT sensor dynamics
    dP = q_prod * Xv + Dev * P  # Product change

    dV = -rev  # Volume change (evaporation)

    dGs = -r_s + Dev * Gs  # Soluble dextrin change
    dGr = -r_r + Dev * Gr  # Resistant dextrin change
    dE = Dev * E  # Enzyme change (dilution by evaporation)

    # Assemble the vector of derivatives
    dX = np.array([dXv, dS, dA, dDOT, dP, dV, dGs, dGr, dE])
    return dX


# %%
def intM(ts0, Xo0, u0, TH0):
    """
    Integrates the ODE system over a specified time interval.

    This function is a wrapper around scipy.integrate.solve_ivp.

    Args:
        ts0 (np.ndarray): Time points for the integration, including start and end.
        Xo0 (np.ndarray): Initial state vector.
        u0 (np.ndarray): Vector of control inputs and operational parameters.
        TH0 (np.ndarray): Vector of model parameters.

    Returns:
        tuple: A tuple containing:
            - sol.t (np.ndarray): The time points at which the solution was evaluated.
            - y_return (np.ndarray): The solution (state vector) at each time point.
    """
    # Define the integration time span [start, end]
    tspan = np.array([ts0[0], ts0[-1]])
    Xo1 = Xo0.tolist().copy()

    # Call the ODE solver (solve_ivp)
    # The ODE function is passed as a lambda function to fix the TH0 and u0 arguments.
    # Method "BDF" is suitable for stiff ODEs.
    sol = solve_ivp(
        lambda t, y: odeFB(t, y, TH0, u0),
        tspan,
        Xo1,
        method="BDF",
        rtol=1e-3,
        atol=1e-3,
        t_eval=ts0,
    )

    # Post-processing: ensure no negative concentrations
    y_interm = sol.y
    y_interm[y_interm < 0] = 0
    y_return = y_interm.copy()

    return sol.t, y_return
