"""
Database Loader Module.

Handles loading of experimental data from the iLab database system.
"""

import sqlalchemy
import pandas as pd
import json
import sys
from datetime import datetime

# __


def get_connection_url():
    host = "mysql"  # "host.docker.internal"
    port = "3306"
    user = "dbuser"
    password = "dbpassword123"
    database = "ilabdb"

    return f"mysql+mysqlconnector://{user}:{password}@{host}:{port}/{database}"


# Get metadata for a runID from the database
# TODO: just start_time by now
def get_metadata(runID, engine):
    sql_metadata = f""" 
        SELECT start_time FROM runs WHERE run_id = '{runID}' 
    """
    conn = engine.connect()
    res = conn.execute(sqlalchemy.text(sql_metadata))
    conn.close()
    return pd.DataFrame(res)


# Get all the measurements for a runID from the database. Grouped by (exp_id, measurement)
def get_measurements(runID, engine):
    sql_measurements = f"""
        SELECT exp.experiment_id, vt.canonical_name, m_exp.measurement_time, m_exp.measured_value 
        FROM bioreactors bio
        LEFT JOIN runs ON bio.run_id = runs.run_id 
        LEFT JOIN experiments exp ON bio.bioreactor_id = exp.bioreactor_id
        INNER JOIN measurements_experiments m_exp ON m_exp.experiment_id = exp.experiment_id
        INNER JOIN measuring_setup m_set ON m_exp.measuring_setup_id = m_set.measuring_setup_id
        INNER JOIN variable_types vt ON vt.variable_type_id = m_set.variable_type_id
        WHERE runs.run_id = {runID}
    """
    conn = engine.connect()
    res = conn.execute(sqlalchemy.text(sql_measurements))
    conn.close()

    res_df = pd.DataFrame(res)
    return (
        res_df.groupby(["experiment_id", "canonical_name"])
        if res_df.shape[0]
        else res_df
    )


# Get all the setpoints for a runID from the database. Grouped by (exp_id, setpoints)
def get_setpoints(runID, engine):
    sql_setpoints = f"""
        SELECT exp.experiment_id, vt.canonical_name, sp.cultivation_age, sp.setpoint_value 
        FROM bioreactors bio
        INNER JOIN runs ON bio.run_id = runs.run_id 
        INNER JOIN experiments exp ON bio.bioreactor_id = exp.bioreactor_id
        INNER JOIN setpoints sp ON sp.profile_id = exp.profile_id
        INNER JOIN variable_types vt ON vt.variable_type_id = sp.variable_type_id
        WHERE runs.run_id = {runID}
    """
    conn = engine.connect()
    res = conn.execute(sqlalchemy.text(sql_setpoints))
    conn.close()

    res_df = pd.DataFrame(res)
    return (
        res_df.groupby(["experiment_id", "canonical_name"])
        if res_df.shape[0]
        else res_df
    )


# creates a json file with metadata, setpoints and measurements for an specific runID
def read_run(runID):

    # connect to database
    # if runID == 623:
    # db = 'mysql+mysqlconnector://dbuser:dbpassword123@host.docker.internal:3306/ilabdb'
    # else:
    #     db = 'mysql+mysqlconnector://Autobio:bvt1autobio!@ht-server.bioprocess.tu-berlin.de:3306/ilabdb'

    db = get_connection_url()

    engine = sqlalchemy.create_engine(db, echo=False)

    # initial data
    json_data = {}

    # get metadata
    metadata_df = get_metadata(runID, engine)
    # metadata_df["start_time"]

    # get setpoints
    setpoints_groups_df = get_setpoints(runID, engine)

    # get measurements
    measurements_groups_df = get_measurements(runID, engine)

    # iterate setpoints groups
    for (exp_id, variable), group in setpoints_groups_df:
        # rename column by variable type
        group.rename(columns={"setpoint_value": variable}, inplace=True)

        # init template for each exp id. Add setpoint as json with 11 null values.
        # Reset index: to start from 0 for each measurement count of the original dataframe
        json_data[exp_id] = {
            "metadata": {},
            "setpoints": json.loads(
                group.reset_index()[["cultivation_age", variable]]
                .shift(periods=11)
                .to_json()
            ),
            "measurements_aggregated": {},
        }

    # iterate measurements groups
    for (exp_id, variable), group in measurements_groups_df:
        # rename column by variable type
        group.rename(columns={"measured_value": variable}, inplace=True)
        group["time"] = group["measurement_time"]

        # calculate relative time (measurement_time - experiment start time)
        def calculate_sample_time(measurement):
            return pd.Timedelta(
                measurement[["time"]][0] - metadata_df["start_time"][0]
            ).total_seconds()

        group["measurement_time"] = group.apply(calculate_sample_time, axis=1)

        # add measurements for each exp id.
        # Reset index: to start from 0 for each measurement count of the original dataframe
        json_data[exp_id]["measurements_aggregated"][variable] = json.loads(
            group.reset_index()[["measurement_time", variable]].to_json()
        )

    return json_data


if __name__ == "__main__":
    runID = 623
    read_run(runID)
