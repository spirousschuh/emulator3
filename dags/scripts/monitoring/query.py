"""
Database Query Utilities Module.

Query utilities for retrieving monitoring data from the database.
"""

import sqlalchemy
import pandas as pd


def run2ids(engine, runID: int):
    query = sqlalchemy.text(
        f"SELECT profiles.profile_id, profiles.profile_name, experiments.experiment_id "
        f"FROM profiles "
        f"INNER JOIN experiments ON profiles.profile_id=experiments.profile_id "
        f"WHERE run_id = {runID};"
    )
    return pd.read_sql(query, engine)


def get_start_time(engine, runID: int):
    sql_query = sqlalchemy.text(
        f"SELECT start_time " f"FROM runs " f"WHERE run_id={runID} "
    )
    with engine.connect() as conn:
        result = conn.execute(sql_query)

    return [r for r in result][0][0]


def get_info(engine, runID):
    sql_query = sqlalchemy.text(
        f"SELECT start_time, end_time, run_name, description "
        f"FROM runs "
        f"WHERE run_id={runID} "
    )
    with engine.connect() as conn:
        result = conn.execute(sql_query)

    return [r for r in result][0]


def variable_map(engine, runID):
    """
    Variable map of the variables with values in the measurements table
    """
    sql_query = sqlalchemy.text(
        f"SELECT variable_type_id, canonical_name "
        f"FROM variable_types "
        f"WHERE variable_type_id IN "
        f"(SELECT distinct(measuring_setup.variable_type_id) "
        f" FROM measurements_experiments INNER JOIN measuring_setup "
        f"  ON measurements_experiments.measuring_setup_id = measuring_setup.measuring_setup_id "
        f" WHERE run_id = {runID})"
    )

    return pd.read_sql(sql_query, engine)


def get_feed_setpoints(engine, profile_id):
    get_feed_query = sqlalchemy.text(
        f" SELECT cultivation_age, setpoint_value "
        f" FROM setpoints "
        f" WHERE profile_id={profile_id} AND variable_type_id=99 "
    )
    feed_df = pd.read_sql(get_feed_query, engine)
    feed_df["cultivation_age"] = feed_df["cultivation_age"] / 3600
    feed_df["setpoint_value"] = feed_df["setpoint_value"] * 10 ** (-6)
    feed_df.set_index("cultivation_age")

    return feed_df
