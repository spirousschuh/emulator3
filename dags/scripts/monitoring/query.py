"""
Database Query Utilities Module.

Query utilities for retrieving monitoring data from the database.
"""

import sqlalchemy
import pandas as pd


def run2ids(engine, runID: int):
    """
    Get profile and experiment IDs associated with a run.
    
    Retrieves all profiles and their corresponding experiments for a given run ID
    by joining the profiles and experiments tables.
    
    Args:
        engine: SQLAlchemy database engine.
        runID (int): The run identifier.
    
    Returns:
        pd.DataFrame: DataFrame with columns profile_id, profile_name, experiment_id.
    """
    # Build SQL query to join profiles and experiments tables
    query = sqlalchemy.text(
        f"SELECT profiles.profile_id, profiles.profile_name, experiments.experiment_id "
        f"FROM profiles "
        f"INNER JOIN experiments ON profiles.profile_id=experiments.profile_id "
        f"WHERE run_id = {runID};"
    )
    return pd.read_sql(query, engine)


def get_start_time(engine, runID: int):
    """
    Get the start time of a run.
    
    Queries the runs table to retrieve when a specific run was started.
    
    Args:
        engine: SQLAlchemy database engine.
        runID (int): The run identifier.
    
    Returns:
        datetime: The start time of the run.
    """
    # Query the runs table for start_time
    sql_query = sqlalchemy.text(
        f"SELECT start_time " f"FROM runs " f"WHERE run_id={runID} "
    )
    # Execute query and extract the first result
    with engine.connect() as conn:
        result = conn.execute(sql_query)

    return [r for r in result][0][0]


def get_info(engine, runID):
    """
    Get comprehensive information about a run.
    
    Retrieves all key metadata for a run including start time, end time,
    run name, and description.
    
    Args:
        engine: SQLAlchemy database engine.
        runID (int): The run identifier.
    
    Returns:
        tuple: A tuple containing (start_time, end_time, run_name, description).
    """
    # Query all run metadata fields
    sql_query = sqlalchemy.text(
        f"SELECT start_time, end_time, run_name, description "
        f"FROM runs "
        f"WHERE run_id={runID} "
    )
    # Execute query and return the first row as a tuple
    with engine.connect() as conn:
        result = conn.execute(sql_query)

    return [r for r in result][0]


def variable_map(engine, runID):
    """
    Get mapping of variable types that have measurements for a run.
    
    Retrieves the variable type IDs and canonical names for all variables
    that have actual measurement values recorded for the specified run.
    Uses a subquery to filter only variables with measurements.
    
    Args:
        engine: SQLAlchemy database engine.
        runID (int): The run identifier.
    
    Returns:
        pd.DataFrame: DataFrame with columns variable_type_id and canonical_name.
    """
    # Query variable types that have measurements in this run
    # Uses a subquery to filter variable types with actual data
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
    """
    Get feed setpoints for a specific profile.
    
    Retrieves glucose feed setpoints (variable_type_id=99) for a profile
    and converts units from seconds to hours and from µL to mL.
    
    Args:
        engine: SQLAlchemy database engine.
        profile_id (int): The profile identifier.
    
    Returns:
        pd.DataFrame: DataFrame with cultivation_age (hours) and setpoint_value (mL).
    """
    # Query setpoints for glucose feed (variable_type_id=99)
    get_feed_query = sqlalchemy.text(
        f" SELECT cultivation_age, setpoint_value "
        f" FROM setpoints "
        f" WHERE profile_id={profile_id} AND variable_type_id=99 "
    )
    feed_df = pd.read_sql(get_feed_query, engine)
    
    # Convert cultivation age from seconds to hours
    feed_df["cultivation_age"] = feed_df["cultivation_age"] / 3600
    
    # Convert setpoint value from µL to mL (multiply by 10^-6)
    feed_df["setpoint_value"] = feed_df["setpoint_value"] * 10 ** (-6)
    feed_df.set_index("cultivation_age")

    return feed_df
