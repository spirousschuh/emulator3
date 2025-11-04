"""
Monitoring Application Module.

Web application for real-time monitoring of bioreactor experiments.
"""

import datetime
import pytz
import sqlalchemy
import pandas as pd
import streamlit as st
import numpy as np
import plotly.express as px
import plotly.graph_objects as go
from plot import subplot_dict
from query import run2ids, get_start_time, get_info, variable_map, get_feed_setpoints


# @st.cache_data
def get_data(_engine, runID: int):

    sql_query = sqlalchemy.text(
        f"SELECT measurements_experiments.experiment_id, measurements_experiments.measurement_time, "
        f"measurements_experiments.measured_value, measuring_setup.variable_type_id, measuring_setup.run_id "
        f"FROM measurements_experiments "
        f"INNER JOIN measuring_setup ON measurements_experiments.measuring_setup_id = measuring_setup.measuring_setup_id "
        f"WHERE run_id = {runID} "
        f"ORDER BY measurement_time"
    )

    data = pd.read_sql(sql_query, _engine)
    start_t = get_start_time(_engine, runID)
    data["t"] = (data["measurement_time"] - start_t) / np.timedelta64(1, "h")
    data = data.set_index("t")

    return data


# @st.cache_data
def return_dataframes(data, runID: int, expIDs: int):

    var_map = (
        variable_map(engine, runID)
        .set_index("canonical_name")
        .to_dict()["variable_type_id"]
    )
    variables = list(var_map.keys())
    if "OD600" in variables:
        variables.append("Biomass")

    data_copy = dict()

    for expID in expIDs:
        data_i = data.loc[data.experiment_id == expID]
        data_copy[expID] = pd.DataFrame(index=data_i.index, columns=variables)
        for name in variables:
            if name == "Biomass":
                type_id = var_map["OD600"]
                data_copy[expID]["Biomass"] = np.where(
                    data_i["variable_type_id"] == type_id,
                    data_i["measured_value"] * 0.37,
                    np.nan,
                )
            elif name in variables:
                type_id = var_map[name]
                data_copy[expID][name] = np.where(
                    data_i["variable_type_id"] == type_id,
                    data_i["measured_value"],
                    np.nan,
                )

        data_copy[expID] = data_copy[expID].groupby(data_copy[expID].index).mean()

    return data_copy


def build_engine():
    engine = sqlalchemy.create_engine(
        "mysql+mysqlconnector://dbuser:dbpassword123@mysql:3306/ilabdb",
        echo=False,
    )
    return engine


def add_info_cards():
    col1, col2, col3, col4, col5 = st.columns(5)
    info = get_info(engine, runID)

    col1.subheader("Experiment start time")
    col1.text(info[0].strftime("%Y-%m-%d %H:%M:%S"))

    col2.subheader("Experiment end time")
    if info[1] is not None:
        col2.text(info[1].strftime("%Y-%m-%d %H:%M:%S"))
    else:
        col2.text("Experiment is running")

    col3.subheader("Run name")
    col3.text(info[2])

    col4.subheader("Description")
    col4.text(info[3])

    col5.subheader("Experiment elapsed time")
    tz = pytz.timezone("Europe/Amsterdam")
    print(datetime.datetime.now(tz).timestamp(), info[0].replace(tzinfo=tz).timestamp())
    elapsed_time_s = (
        datetime.datetime.now(tz) - info[0].replace(tzinfo=tz)
    ).total_seconds()
    print(elapsed_time_s)
    hours, remainder = divmod(elapsed_time_s, 3600)
    minutes, seconds = divmod(remainder, 60)
    col5.text("{:02}h {:02}min {:02}s".format(int(hours), int(minutes), int(seconds)))


if __name__ == "__main__":

    st.set_page_config(layout="wide", initial_sidebar_state="expanded")

    st.markdown("# iLab monitoring")

    with open("style.css") as f:
        st.markdown(f"<style>{f.read()}</style>", unsafe_allow_html=True)

    engine = build_engine()

    runID = int(st.number_input("runID", value=623))

    # Update page
    st.button(label="Update")

    # INFO: gets runs table from iLab db and writes 4 column cards
    with st.container():
        add_info_cards()

    # Plot experimental data
    st.markdown("## Data")
    data_dict = dict()
    var_map = variable_map(engine, runID)
    variables_in_run = var_map["canonical_name"].to_list()

    try:
        data_all = get_data(engine, runID)
        if "OD600" in variables_in_run:
            variables_in_run.append("Biomass")
    except TypeError:
        print("No data available for the selected run ID.")
        data_all = pd.DataFrame()

    print(variables_in_run)

    plot_variables = st.multiselect(
        "Plot variables", variables_in_run, variables_in_run
    )

    tab1, tab2 = st.tabs(["iLab streaming", "Data"])

    id_df = run2ids(engine, runID)
    exp_list = id_df.experiment_id.to_list()
    print(exp_list)
    expids = st.multiselect("expID", exp_list, exp_list)

    # Data plot:
    _lock = st.empty()

    try:
        with tab1:
            data_dict = return_dataframes(data_all, runID, expids)

            fig = subplot_dict(
                exp_data=data_dict,
                plot_states=dict(
                    zip(plot_variables, np.repeat("", len(plot_variables)))
                ),
                return_fig=True,
                show=False,
            )
            fig.update_layout(autosize=False, width=200, height=800)

            st.plotly_chart(fig, use_container_width=True)

        with tab2:
            for expID in expids:
                st.markdown("### " + str(expID))
                st.dataframe(data_dict[expID])

        rows = np.unique([BR[0] for BR in id_df.profile_name.values])
        cols = np.unique([BR[1] for BR in id_df.profile_name.values])

        summary1, summary2, summary3, summary4, summary5 = st.tabs(
            [
                "Minimum oxygen per bioreactor",
                "Feed setpoints",
                "Total yield max(X)/max(cum_S)",
                "Cumulative yields biomass/glucose",
                "Cumulative yields product/glucose",
            ]
        )

        summary = pd.DataFrame(index=rows, columns=cols, dtype=float)

        with summary1:
            col1, col2 = st.columns(2)
            try:
                with col2:
                    t1, t2 = st.slider(
                        "Select time interval",
                        0.0,
                        max(data_dict[expids[0]]["DOT"].index),
                        (0.0, max(data_dict[expids[0]]["DOT"].index)),
                    )
                with col1:
                    for expid in expids:
                        BR = id_df.loc[id_df["experiment_id"] == expid][
                            "profile_name"
                        ].values[0]
                        summary.loc[BR[0], BR[1]] = min(
                            data_dict[expid]["DOT"].dropna().loc[t1:t2]
                        )
                    fig = px.imshow(summary, text_auto=True)
                    st.plotly_chart(fig)
            except:
                st.text(
                    "Probably there are not DOT measurements for the selected experiment IDs."
                )

        with summary2:
            col1, col2 = st.columns(2)
            with col1:
                for expid in expids:
                    feed_df = get_feed_setpoints(
                        engine,
                        id_df.loc[id_df["experiment_id"] == expid]["profile_id"].values[
                            0
                        ],
                    )
                    BR = id_df.loc[id_df.experiment_id == expid]["profile_name"].values[
                        0
                    ]
                    summary.loc[BR[0], BR[1]] = np.max(feed_df["setpoint_value"])

                    fig = px.bar(
                        feed_df,
                        x="cultivation_age",
                        y="setpoint_value",
                        title=f"Experiment ID: {id_df.loc[id_df['experiment_id']==expid]['profile_name'].values}",
                    )
                    st.plotly_chart(fig)
            with col2:
                fig = px.imshow(
                    summary, text_auto=True, labels=dict(x="2mag column", y="2mag row")
                )
                st.plotly_chart(fig)

        with summary3:
            col1, col2 = st.columns(2)
            with col1:
                try:
                    for expid in expids:
                        BR = id_df.loc[id_df.experiment_id == expid][
                            "profile_name"
                        ].values[0]
                        summary.loc[BR[0], BR[1]] = max(
                            data_dict[expid]["Biomass"].dropna()
                        ) / max(
                            data_dict[expid]["Cumulated_feed_volume_glucose"].dropna()
                        )
                    fig = px.imshow(summary, text_auto=True)
                    st.plotly_chart(fig)
                except Exception as e:
                    st.text(f"{e} not in selected dataset")
            with col2:
                st.dataframe(id_df)

        with summary4:
            col1, col2 = st.columns(2)
            with col1:
                try:
                    for expid in expids:
                        feed = 5e-2 + 200e-6 * (
                            data_dict[expid][
                                "Cumulated_feed_volume_glucose"
                            ].interpolate(method="linear")
                        )
                        BR = id_df.loc[id_df.experiment_id == expid][
                            "profile_name"
                        ].values[0]
                        summary.loc[BR[0], BR[1]] = np.nansum(
                            (data_dict[expid]["Biomass"].dropna() * 10**-2) / feed
                        )
                    fig = px.imshow(summary, text_auto=True)
                    st.plotly_chart(fig)

                except KeyError as e:
                    st.text(f"{e} not in selected dataset")
            with col2:

                try:
                    yield_dict = dict()
                    for expid in expids:
                        feed = 5e-2 + 200e-6 * (
                            data_dict[expid][
                                "Cumulated_feed_volume_glucose"
                            ].interpolate(method="linear")
                        )
                        yield_dict[expid] = pd.DataFrame(
                            data_dict[expid]["Biomass"].dropna() * 10**-2 / feed,
                            columns=["yield"],
                        )

                    fig = subplot_dict(
                        exp_data=yield_dict,
                        plot_states={"yield": "Biomass / Total glucose"},
                        return_fig=True,
                        show=False,
                    )
                    st.plotly_chart(fig)
                except KeyError as e:
                    st.text(f"{e} not in selected dataset")

    except AttributeError:
        print("No data available for the selected run ID.")
