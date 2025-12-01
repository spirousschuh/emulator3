# %% Import

import numpy as np
import pandas as pd

import matplotlib.pyplot as plt

from scipy.integrate import solve_ivp


# %%
def function_simulation(ts0, Xo0, u0, THs, D0={}):
    TH1 = np.array(THs[str(int(u0[1]))])

    ts_start = ts0[0]
    ts_end = ts0[-1]

    time_pulse_all = np.array(D0["time_pulse"])
    t_u_pulse = np.round(
        time_pulse_all[(time_pulse_all >= ts_start) & (time_pulse_all <= ts_end)],
        decimals=6,
    )
    Feed_pulse_all = np.array(D0["Feed_pulse"])
    uu_pulse = Feed_pulse_all[(time_pulse_all >= ts_start) & (time_pulse_all <= ts_end)]

    time_sample_all = np.array(D0["time_sample"])
    t_u_sample = np.round(
        time_sample_all[(time_sample_all >= ts_start) & (time_sample_all <= ts_end)],
        decimals=6,
    )

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

    time_enzyme_all = np.array(D0["time_enzyme"])
    t_u_enzyme = np.round(
        time_enzyme_all[(time_enzyme_all >= ts_start) & (time_enzyme_all <= ts_end)],
        decimals=6,
    )
    Feed_enzyme_all = np.array(D0["Feed_enzyme"])
    uu_enzyme = Feed_enzyme_all[
        (time_enzyme_all >= ts_start) & (time_enzyme_all <= ts_end)
    ]

    time_medium_all = np.arange(10 / 60, time_pulse_all[-1] + 10 / 60, 10 / 60)
    t_u_medium = np.round(
        time_medium_all[(time_medium_all >= ts_start) & (time_medium_all <= ts_end)],
        decimals=6,
    )

    time_u_concat = np.concatenate(
        (t_u_pulse, t_u_sample, t_u_dextrine, t_u_enzyme, t_u_medium)
    )
    t_u = np.unique(time_u_concat)

    if len(t_u) == 0:
        t_u = np.array([ts_start, ts_end])
        uu = np.array([0, 0])

    else:
        if ts_start < t_u[0]:
            t_u = np.append(ts_start, t_u)
        if ts_end > t_u[-1]:
            t_u = np.append(t_u, ts_end)

    Xo1 = Xo0.copy()

    tt = np.array(ts_start)
    yy = np.array([Xo1])
    yy = yy.transpose()

    ni = 0

    for i in t_u[:-1]:
        ts1 = np.linspace(t_u[ni], t_u[ni + 1], 5 + 1)
        V_old = Xo1[5]
        if i in t_u_pulse:
            index_u_pulse = int(np.where(t_u_pulse == t_u[ni])[0][0])
            Xo1[1] = Xo1[1] + uu_pulse[index_u_pulse] * 1e-6 * u0[0] / 0.01
            Xo1[5] = Xo1[5] + uu_pulse[index_u_pulse] * 1e-6
            # add dilution to all species

        if i in t_u_dextrine:
            index_u_dextrine = int(np.where(t_u_dextrine == t_u[ni])[0][0])
            Xo1[6] = Xo1[6] + uu_dextrine[index_u_dextrine] * 1e-6 * u0[5] / 0.01 * (
                0.46
            )
            Xo1[7] = Xo1[7] + uu_dextrine[index_u_dextrine] * 1e-6 * u0[5] / 0.01 * (
                1 - 0.46
            )
            Xo1[5] = Xo1[5] + uu_dextrine[index_u_dextrine] * 1e-6

        if i in t_u_enzyme:
            index_u_enzyme = int(np.where(t_u_enzyme == t_u[ni])[0][0])
            Xo1[8] = Xo1[8] + uu_enzyme[index_u_enzyme] * 1e-6 * u0[6] / 0.01 * 0.7
            Xo1[5] = Xo1[5] + uu_enzyme[index_u_enzyme] * 1e-6

        if i in t_u_sample:
            Xo1[5] = Xo1[5] - 25 * 1e-6
        if i in t_u_medium:
            Xo1[5] = Xo1[5] + 1 * 1e-6

        V_new = Xo1[5]
        Xo1 = Xo1 * V_old / V_new
        Xo1[5] = V_new

        t, y = intM(ts1, Xo1, u0, TH1)
        Xo1 = y[:, -1].copy()

        tt = np.append(tt, t[1:])
        yy = np.append(yy, y[:, 1:], axis=1)
        ni = ni + 1

    return tt, yy.transpose()


# %%
def odeFB(t, Xo, THo, u):

    X = Xo.copy()
    TH = THo.copy()
    X = np.maximum(X, 1e-9)

    Xv = X[0]
    S = X[1]
    A = X[2]
    DOT = X[3]
    P = X[4]

    V = X[5]

    Gs = X[6]
    Gr = X[7]
    E = X[8]

    DOT = np.minimum(DOT, 100)

    qs_max = TH[0]
    fracc_q_ox_max = TH[1]

    qa_max = TH[2]
    Ksi = TH[3]  #

    Ys_ox = TH[4]
    Ya_p = TH[5]
    Ya_c = TH[6]
    Kai = TH[7]  #
    Yo_ox = TH[8]
    Yo_a = TH[9]
    Yxs_of = TH[10]
    Y_ps = 1

    Ks = TH[11]

    Ka = TH[12]
    n_ox = 4

    Ko = 0.10  #

    k_s = TH[16]
    k_r = TH[17]
    Krs = TH[18]

    kla = TH[19]
    k_sensor = TH[20]

    DO_star = 100
    H = 13000  #
    rev = 30 * 1e-6 * 1
    Y_g = 1.11

    Dev = rev / V

    qs = qs_max * S / (S + Ks)
    q_ox_max = fracc_q_ox_max * qs_max

    q_ox_ss = qs * (1 / ((qs / q_ox_max) ** n_ox + 1)) ** (1 / n_ox)
    qac_ss = qa_max * A / (A + Ka) * Kai / (Kai + S)
    b_ss = Ko + (q_ox_ss * Yo_ox + qac_ss * Yo_a) * Xv * H / (kla - Dev * 0) - DO_star
    c_ss = -DO_star * Ko
    DOT_ss = (-b_ss + (b_ss * b_ss - 4 * c_ss) ** 0.5) / 2

    q_ox = (
        qs * (1 / ((qs / q_ox_max) ** n_ox + 1)) ** (1 / n_ox) * DOT_ss / (DOT_ss + Ko)
    )
    q_of = qs - q_ox

    qac = qa_max * A / (A + Ka) * Kai / (Kai + S) * DOT_ss / (DOT_ss + Ko)

    qap = q_of * Ya_p

    mu = q_ox * Ys_ox + qac * Ya_c + Yxs_of * q_of

    if t >= u[3]:
        s_prod = u[4]
    else:
        s_prod = 0

    q_prod = s_prod * Y_ps

    r_s = k_s * E * Gs / (Gs + Gr + Krs)
    r_r = k_r * E * Gr / (Gs + Gr + Krs)

    dXv = (mu) * Xv + Dev * Xv
    dS = -qs * Xv + Y_g * (r_s + r_r) + Dev * S
    dA = qap * Xv - qac * Xv + Dev * A
    dDOT = k_sensor * (DOT_ss - DOT)
    dP = q_prod * Xv + Dev * P

    dV = -rev

    dGs = -r_s + Dev * Gs
    dGr = -r_r + Dev * Gr
    dE = Dev * E
    dX = np.array([dXv, dS, dA, dDOT, dP, dV, dGs, dGr, dE])
    return dX


# %%
def intM(ts0, Xo0, u0, TH0):

    tspan = np.array([ts0[0], ts0[-1]])
    Xo1 = Xo0.tolist().copy()

    sol = solve_ivp(
        lambda t, y: odeFB(t, y, TH0, u0),
        tspan,
        Xo1,
        method="BDF",
        rtol=1e-3,
        atol=1e-3,
        t_eval=ts0,
    )
    y_interm = sol.y
    y_interm[y_interm < 0] = 0
    y_return = y_interm.copy()

    return sol.t, y_return
