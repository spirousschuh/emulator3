"""
Database Connector Module.

Provides database connectivity and CRUD operations for bioreactor
experimental data, measurements, and control actions.
"""

import sqlalchemy
import datetime
import json
import pytz
import pandas as pd
import numpy as np
import os
import sys


def get_connection_url():
    """
    Generate database connection URL string.
    
    Constructs the MySQL connection URL for the iLab database using
    hardcoded credentials and connection parameters.
    
    Returns:
        str: SQLAlchemy connection URL in format mysql+mysqlconnector://user:pass@host:port/db
    """
    host = "mysql"  # Database host (use "host.docker.internal" for Docker)
    port = "3306"  # MySQL default port
    user = "dbuser"  # Database username
    password = "dbpassword123"  # Database password
    database = "ilabdb"  # Database name

    return f"mysql+mysqlconnector://{user}:{password}@{host}:{port}/{database}"


# Timezone definition:
local_tz = pytz.timezone("Europe/Amsterdam")

db = get_connection_url()
engine = sqlalchemy.create_engine(db, echo=False)

run_id = 623


# **********************************************************************************
#                       MEASUREMENTS functions
# **********************************************************************************


def save_start_time():
    """
    Save the simulation start time to the database.
    
    Reads the absolute start time from DTWIN_design.json and updates
    the runs table with this timestamp. Converts Unix timestamp to
    Amsterdam timezone.
    """

    # Read time_start_absolute from design file
    with open("DTWIN_design.json", "r") as file:
        design_file = json.load(file)

    # Build UPDATE query with formatted timestamp
    sql_query = " UPDATE runs SET start_time = '{}' WHERE run_id = '{}' ".format(
        datetime.datetime.fromtimestamp(
            design_file["time_start_absolute"], tz=local_tz
        ).strftime("%Y-%m-%d %H:%M:%S"),
        run_id,
    )

    # Execute the update
    conn = engine.connect()
    conn.execute(sqlalchemy.text(sql_query))
    conn.close()


def get_measuring_setup_id(conn, variable_type):
    """
    Get measuring setup ID for a variable type.
    
    Looks up the measuring_setup_id by joining measuring_setup and
    variable_types tables. This ID links measurements to their sensor
    configuration.
    
    Args:
        conn: Database connection object.
        variable_type (str): Canonical name of the variable (e.g., 'OD600', 'DOT').
    
    Returns:
        int: The measuring_setup_id for this variable type and run.
    """

    # Query measuring setup ID by variable type canonical name
    sql_query = f"""
        SELECT measuring_setup_id FROM measuring_setup 
        WHERE run_id = '{run_id}' AND variable_type_id = 
            (SELECT variable_type_id FROM variable_types WHERE canonical_name = '{variable_type}' );
    """
    res_msetup = conn.execute(sqlalchemy.text(sql_query)).mappings().all()

    return res_msetup[0]["measuring_setup_id"]


def delete_measuring_setup_id_data(conn, experiment_id, measuring_setup_id):
    """
    Delete dummy measurements for an experiment and sensor.
    
    Removes all measurements marked as 'dummy' for a specific experiment
    and measuring setup. Used to clean up placeholder data before inserting
    real measurements.
    
    Args:
        conn: Database connection object.
        experiment_id (int): The experiment identifier.
        measuring_setup_id (int): The measuring setup identifier.
    """

    # Delete dummy measurements for this experiment and sensor
    sql_query = f"""
        DELETE FROM measurements_experiments WHERE measuring_setup_id = '{measuring_setup_id}' 
                    AND experiment_id = '{experiment_id}' AND label= 'dummy';
    """

    conn.execute(sqlalchemy.text(sql_query))


def send_data_to_ilab(
    conn, experiment_id, measuring_setup_id, start_time, measurements
):
    """
    Insert measurements into the iLab database.
    
    Bulk inserts measurement records for a specific experiment and sensor.
    Constructs a single SQL INSERT statement with multiple value rows for
    efficiency.
    
    Args:
        conn: Database connection object.
        experiment_id (int): The experiment identifier.
        measuring_setup_id (int): The measuring setup identifier.
        start_time (datetime): The experiment start time for timestamp calculation.
        measurements (dict): Dictionary with 'time' and 'value' arrays.
    """

    # Build bulk INSERT query with all measurement values
    query_all = ""
    for measurement_time, value in measurements:
        timestamp = (
            start_time + datetime.timedelta(seconds=measurement_time)
        ).strftime("%Y-%m-%d %H:%M:%S")
        query_all += f"""({measuring_setup_id}, {experiment_id}, "{timestamp}", 1, 1, {value}, 1, NULL, 'dummy'),"""

    if query_all != "":
        sql_query = f"""
            INSERT INTO measurements_experiments (measuring_setup_id, experiment_id, measurement_time, dilution_factor, valid, measured_value, checksum, sampling_id, label) 
            VALUES {query_all[:-1]};
        """

        conn.execute(sqlalchemy.text(sql_query))


def save_measurements():
    """
    Save all measurements for all mini bioreactors (MBRs).
    
    Reads measurements from db_dtwin.json and writes them to the database.
    Deletes existing dummy measurements before inserting new ones to avoid
    duplicates. Processes all measurement types for all experiments in a
    single transaction.
    
    The function handles multiple measurement types including: OD600, DOT,
    metabolites, feeds, and process parameters.
    """

    # Load experiment start time from design file
    with open("DTWIN_design.json", "r") as file:
        design_file = json.load(file)
        file.close()

    start_time = datetime.datetime.fromtimestamp(
        design_file["time_start_absolute"], tz=local_tz
    )

    # Load all measurements from state file
    with open("db_dtwin.json", "r") as file:
        mbrs_measurements = json.load(file)
        file.close()

    # List of all measurement types to process
    # TODO: Make this configurable instead of hardcoded
    measurement_types = [
        "OD600",
        "DOT",
        "Acetate",
        "Glucose",
        "Fluo_RFP",
        "Volume",
        "Temperature",
        "Flow_Air",
        "StirringSpeed",
        "Acid",
        "Base",
        "Cumulated_feed_volume_glucose",
        "Cumulated_feed_volume_medium",
        "Fluo_CFP",
        "Probe_Volume",
        "Volume_evaporated",
        "pH",
        "Cumulated_feed_volume_dextrine",
        "Cumulated_feed_volume_enzyme",
    ]

    conn = engine.connect()

    # Set isolation level to SERIALIZABLE
    # conn.execution_options(isolation_level='SERIALIZABLE')

    # Execute all database operations in a single transaction
    with conn.begin():
        for exp_id in mbrs_measurements:

            # Process each measurement type for this experiment
            # TODO: Optimize by fetching all measurement_setup_ids in one query
            for measurement in measurement_types:
                try:
                    # Get measurements for this type
                    measurement_list = mbrs_measurements[exp_id][
                        "measurements_aggregated"
                    ][measurement]
                    
                    # Get measuring_setup_id for this measurement type
                    measuring_setup_id = get_measuring_setup_id(conn, measurement)

                    # Delete old dummy values for this measurement type
                    delete_measuring_setup_id_data(conn, exp_id, measuring_setup_id)

                    # Insert new measurement data
                    send_data_to_ilab(
                        conn,
                        exp_id,
                        measuring_setup_id,
                        start_time,
                        zip(
                            measurement_list["measurement_time"].values(),
                            measurement_list[measurement].values(),
                        ),
                    )

                except Exception as e:
                    print(f"Error on {exp_id} - {measurement}")
                    pass

    conn.close()


def get_feeds(runID):
    """
    Retrieve feed setpoint profiles for all mini bioreactors (MBRs).
    
    Reads setpoints from database and merges them into the measurements
    dictionary. Updates db_dtwin.json with feed setpoint data for each
    experiment.
    
    Args:
        runID (int): The run identifier to query.
    """

    # Load current measurements file
    with open("db_dtwin.json", "r") as file:
        mbrs_measurements = json.load(file)
        file.close()

    # Query all setpoints from database
    setpoints_groups_df = get_setpoints(runID, engine)

    # Process each setpoint group (by experiment and variable)
    for (exp_id, variable), group in setpoints_groups_df:
        # Rename columns to match expected format
        group.rename(
            columns={"setpoint_value": variable, "cultivation_age": "setpoint_time"},
            inplace=True,
        )

        # Store setpoints in measurements dictionary
        # Reset index to start from 0 for JSON serialization
        mbrs_measurements[str(exp_id)]["setpoints"][variable] = json.loads(
            group.reset_index()[["setpoint_time", variable]].to_json()
        )

    # Write updated measurements back to file
    with open("db_dtwin.json", "w") as file:
        json.dump(mbrs_measurements, file)
        file.close()


def create_feed_json(filename_db, filename_feed):
    """
    Convert feed profile to database-compatible JSON format.
    
    Reads pulse feed profiles and converts them to cumulative feed volumes
    over time. Creates directory structure if needed.
    
    Args:
        filename_db (str): Output path for database JSON file.
        filename_feed (str): Input path for feed profile JSON file.
    """

    # Load feed profiles
    with open(filename_feed) as json_file:
        Feed_dict = json.load(json_file)

    new_profile = {}

    # Process experiments 19419 to 19442
    for i1 in range(19419, 19443):

        # Extract pulse feeds and times
        f_pulse_new = np.array(list(Feed_dict[str(i1)]["Pulse_profile"]["Feed_pulse"]))
        tf_new = (
            np.array(list(Feed_dict[str(i1)]["Pulse_profile"]["time_pulse"])) * 3600
        )

        # Convert to cumulative feed volumes
        new_profile[str(i1)] = {}
        new_profile[str(i1)]["measurement_time"] = tf_new.astype(int).tolist()
        new_profile[str(i1)]["setpoint_value"] = np.cumsum(f_pulse_new).tolist()

    # Create directory if it doesn't exist
    if not os.path.isdir(os.path.dirname(filename_db)):
        os.makedirs(os.path.dirname(filename_db))

    # Write output file
    with open(filename_db, "w") as file:
        json.dump(new_profile, file)
        file.close()


# **********************************************************************************
#          GET measurements, metadata, setpoints FROM query and save file
# **********************************************************************************


def get_metadata(runID, engine):
    """
    Query metadata for a run from the database.
    
    Retrieves run metadata, currently only the start_time field.
    
    Args:
        runID (int): The run identifier.
        engine: SQLAlchemy database engine.
    
    Returns:
        pd.DataFrame: DataFrame with run metadata.
    """

    # Query start_time for this run
    # TODO: Expand to include additional metadata fields
    sql_metadata = f""" 
        SELECT start_time FROM runs WHERE run_id = '{runID}' 
    """
    conn = engine.connect()
    res = conn.execute(sqlalchemy.text(sql_metadata))
    conn.close()
    return pd.DataFrame(res)


def get_measurements(runID, engine):
    """
    Retrieve all measurements for a run from the database.
    
    Performs complex join across bioreactors, experiments, measurements,
    measuring setup, and variable types tables. Returns grouped by
    experiment and measurement type.
    
    Args:
        runID (int): The run identifier.
        engine: SQLAlchemy database engine.
    
    Returns:
        pd.DataFrameGroupBy or pd.DataFrame: Measurements grouped by (experiment_id, canonical_name),
                                              or empty DataFrame if no data.
    """

    # Complex query joining multiple tables to get complete measurement data
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

    # Convert to DataFrame and group by experiment and measurement type
    res_df = pd.DataFrame(res)
    return (
        res_df.groupby(["experiment_id", "canonical_name"])
        if res_df.shape[0]  # Return grouped data if rows exist
        else res_df  # Return empty DataFrame if no data
    )


def get_exp_ids(runID, engine):
    """
    Retrieve all experiment IDs for a run.
    
    Queries the database to get the list of experiment IDs associated
    with a specific run.
    
    Args:
        runID (int): The run identifier.
        engine: SQLAlchemy database engine.
    
    Returns:
        pd.Series: Series of experiment IDs for this run.
    """

    # Query experiment IDs by joining bioreactors, runs, and experiments
    sql_setpoints = f"""
        SELECT exp.experiment_id 
        FROM bioreactors bio
        INNER JOIN runs ON bio.run_id = runs.run_id 
        INNER JOIN experiments exp ON bio.bioreactor_id = exp.bioreactor_id
        WHERE runs.run_id = {runID}
    """
    conn = engine.connect()
    res = conn.execute(sqlalchemy.text(sql_setpoints))
    conn.close()

    return pd.DataFrame(res)["experiment_id"]


def get_setpoints(runID, engine):
    """
    Retrieve all setpoints for a run from the database.
    
    Queries setpoints (control action targets) for all experiments in a run.
    Joins across multiple tables to get complete setpoint information including
    variable types and cultivation age.
    
    Args:
        runID (int): The run identifier.
        engine: SQLAlchemy database engine.
    
    Returns:
        pd.DataFrameGroupBy or pd.DataFrame: Setpoints grouped by (experiment_id, canonical_name),
                                              or empty DataFrame if no data.
    """

    # Query setpoints by joining bioreactors, experiments, and variable types
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

    # Convert to DataFrame and group by experiment and setpoint type
    res_df = pd.DataFrame(res)
    return (
        res_df.groupby(["experiment_id", "canonical_name"])
        if res_df.shape[0]  # Return grouped data if rows exist
        else res_df  # Return empty DataFrame if no data
    )


def read_run(runID):
    """
    Create a comprehensive JSON structure with all run data.
    
    Retrieves metadata, setpoints, and measurements for a run and
    organizes them into a hierarchical JSON structure. Converts absolute
    timestamps to relative times from experiment start.
    
    Args:
        runID (int): The run identifier to read.
    
    Returns:
        dict: Nested dictionary with structure:
              {experiment_id: {metadata: {}, setpoints: {}, measurements_aggregated: {}}}
    """

    # Connect to database
    db = get_connection_url()
    engine = sqlalchemy.create_engine(db, echo=False)

    # Initialize data structure
    json_data = {}

    # Get run metadata (start time, etc.)
    metadata_df = get_metadata(runID, engine)

    # Create template structure for each experiment
    exp_ids = get_exp_ids(runID, engine)
    for exp_id in exp_ids:
        json_data[exp_id] = {
            "metadata": {},
            "setpoints": {},
            "measurements_aggregated": {},
        }

    # Retrieve setpoints and measurements from database
    setpoints_groups_df = get_setpoints(runID, engine)
    measurements_groups_df = get_measurements(runID, engine)

    # Process setpoints for each experiment and variable
    for (exp_id, variable), group in setpoints_groups_df:
        # Rename columns to match expected format
        group.rename(
            columns={"setpoint_value": variable, "cultivation_age": "setpoint_time"},
            inplace=True,
        )

        # Store setpoints in JSON structure (reset index for clean serialization)
        json_data[exp_id]["setpoints"][variable] = json.loads(
            group.reset_index()[["setpoint_time", variable]].to_json()
        )

    # Process measurements for each experiment and variable
    for (exp_id, variable), group in measurements_groups_df:
        # Rename columns to match expected format
        group.rename(columns={"measured_value": variable}, inplace=True)
        group["time"] = group["measurement_time"]

        # Convert absolute timestamps to relative time from start
        def calculate_sample_time(measurement):
            return pd.Timedelta(
                measurement[["time"]][0] - metadata_df["start_time"][0]
            ).total_seconds()

        group["measurement_time"] = group.apply(calculate_sample_time, axis=1)

        # Store measurements in JSON structure (reset index for clean serialization)
        json_data[exp_id]["measurements_aggregated"][variable] = json.loads(
            group.reset_index()[["measurement_time", variable]].to_json()
        )

    return json_data


def query_and_save(runID, filepath):
    """
    Query all run data and save to JSON file.
    
    Retrieves complete run information (metadata, setpoints, measurements)
    and saves it to a JSON file for historical monitoring and analysis.
    Creates directory structure if needed.
    
    Args:
        runID (int): The run identifier to query.
        filepath (str): Relative path for output JSON file.
    """

    # Get current working directory
    rootdir = os.getcwd()

    # Query all data for this run
    db_json = read_run(runID)

    # Create directory if it doesn't exist
    if not os.path.isdir(os.path.dirname(f"{rootdir}/{filepath}")):
        os.makedirs(os.path.dirname(f"{rootdir}/{filepath}"))

    # Save to JSON file
    pd.DataFrame(db_json).to_json(f"{rootdir}/{filepath}")


# **********************************************************************************
#                   FEEDS functions FROM save actions file
# **********************************************************************************


def run2ids(connection, runID):
    """
    Get profile IDs and names for a run.
    
    Retrieves the mapping between experiments and their profiles for
    a specific run. Useful for translating between experiment IDs and
    profile configurations.

    Parameters
    ----------
    connection: sqlalchemy.engine.Connection
        Connection to MySQL database using SQLAlchemy.
    runID: int
        Identification number for an experiment run.
    
    Returns
    -------
    pd.DataFrame
        DataFrame with columns: profile_id, profile_name, experiment_id.
    """
    # Query profile and experiment associations for this run
    query = sqlalchemy.text(
        f"SELECT profiles.profile_id, profiles.profile_name, experiments.experiment_id "
        f"FROM profiles "
        f"INNER JOIN experiments ON profiles.profile_id=experiments.profile_id "
        f"WHERE run_id = {runID};"
    )

    return pd.read_sql(query, connection)


def delete_setpoints(connection, runID, exp_id, from_time=0, type_id=99):
    """
    Delete setpoints from a specific time onwards.
    
    Removes setpoint records for a bioreactor experiment starting from
    a specified cultivation age. Prompts for confirmation before deletion.
    Typically used to clear old setpoints before updating with new values.

    Parameters
    ----------
    connection: sqlalchemy.engine.Connection
        Connection to MySQL database using SQLAlchemy.
    runID: int
        Identification number for the experiment run.
    exp_id: int
        The experiment ID for the mini bioreactor in the current run.
    from_time: int/float, optional
        The cultivation age (in seconds) from which setpoints should be deleted. Default is 0.
    type_id: int, optional
        The variable_type_id for the setpoint to delete (99 = glucose feed). Default is 99.
    """
    # Warn user about deletion
    print(
        f"Attention! This will delete the setpoint data for run {runID} and bioreactor exp_id {exp_id} after experiment"
        f"time {from_time}s. Press enter to continue and q to quit."
    )

    # Get profile ID for this experiment
    profiles = run2ids(connection, runID)
    profile_id = profiles.loc[profiles["experiment_id"] == exp_id]["profile_id"].iloc[0]
    
    # Build and execute DELETE query
    query = (
        f" DELETE FROM setpoints "
        f" WHERE profile_id = {profile_id} AND variable_type_id = {type_id} AND cultivation_age > {from_time}; "
    )

    connection.execute(sqlalchemy.text(query))


def add_setpoints(
    connection,
    runID,
    exp_id,
    setpoint_df,
    type_id=99,
    type_name="Feed_glc_cum_setpoints",
):
    """
    Add setpoints to an experiment profile.
    
    Inserts new setpoint records into the database for a specific experiment.
    Setpoints define the target values for control variables (e.g., feed rates)
    over time during cultivation.

    Parameters
    ----------
    connection: sqlalchemy.engine.Connection
        Connection to MySQL database using SQLAlchemy.
    runID: int
        Identification number for the experiment run.
    exp_id: int
        The experiment ID for the mini bioreactor in the current run.
    setpoint_df: pandas.DataFrame
        DataFrame with columns: measurement_time (or setpoint_time) and setpoint_value.
    type_id: int, optional
        The variable_type_id for the setpoint (99 = glucose feed). Default is 99.
    type_name: str, optional
        Name of the setpoint column in the input DataFrame. Default is "Feed_glc_cum_setpoints".
    """
    # Get profile ID for this experiment
    profiles = run2ids(connection, runID)
    profile_id = profiles.loc[profiles["experiment_id"] == exp_id]["profile_id"].iloc[0]
    
    # Rename columns to match database schema
    setpoint_df.rename(columns={"setpoint_time": "cultivation_age"}, inplace=True)
    setpoint_df.rename(columns={type_name: "setpoint_value"}, inplace=True)
    
    # Add required metadata columns
    setpoint_df["profile_id"] = profile_id
    setpoint_df["variable_type_id"] = type_id
    setpoint_df["scope"] = "e"  # Experiment scope
    setpoint_df["checksum"] = 1  # Checksum for data integrity (TODO: clarify purpose)
    
    # Bulk insert setpoints into database
    setpoint_df.to_sql(
        "setpoints", con=connection, if_exists="append", index=False, method="multi"
    )


def save_actions(runID, file_path):
    """
    Save feeding profiles for all mini bioreactors in a run.
    
    Reads feed setpoints from a JSON file and updates the database.
    Deletes existing setpoints before inserting new ones to ensure
    clean updates. All operations occur in a single transaction.
    
    Args:
        runID (int): The run identifier.
        file_path (str): Path to JSON file containing feed profiles.
    """

    # Load feed profiles from file
    with open(file_path, "r") as file:
        feed = json.load(file)
        file.close()

    # Convert feed data to DataFrames
    setpoints_df = dict()
    for exp_id in feed:
        setpoints_df[exp_id] = pd.DataFrame.from_dict(feed[exp_id])

    # Update database: delete old setpoints and add new ones
    # Execute in single transaction for atomicity
    with engine.connect() as connection:
        with connection.begin():
            for exp_id in setpoints_df:
                delete_setpoints(connection, runID, int(exp_id))
                add_setpoints(connection, runID, int(exp_id), setpoints_df[exp_id])


def save_multi_actions(runID, file_path):
    """
    Save multiple types of setpoint profiles for all mini bioreactors.
    
    Reads setpoints for glucose, enzyme, and dextrine feeds from a JSON file
    and updates the database. Handles multiple variable types simultaneously.
    Deletes existing setpoints before inserting new ones.
    
    Args:
        runID (int): The run identifier.
        file_path (str): Path to JSON file containing multiple setpoint types.
    """

    # Load setpoints from file
    with open(file_path, "r") as file:
        feed = json.load(file)
        file.close()

    # Define variable types to process
    # (variable_type_id, column_name_in_file)
    variable_types = [
        (99, "Feed_glc_cum_setpoints"),      # Glucose feed
        (112, "Feed_enzyme_cum_setpoints"),   # Enzyme feed
        (131, "Feed_dextrine_cum_setpoints"), # Dextrine feed
    ]

    # Update database: delete old setpoints and add new ones
    # Execute in single transaction for atomicity
    with engine.connect() as connection:
        with connection.begin():
            for exp_id in feed:

                # Process each variable type for this experiment
                for type_id, type_name in variable_types:

                    # Extract setpoints for this variable type
                    setpoint_df = pd.DataFrame.from_dict(
                        feed[exp_id]["setpoints"][type_name]
                    )

                    # Delete old setpoints from time 0 onwards
                    delete_setpoints(connection, runID, int(exp_id), 0, type_id)
                    
                    # Add new setpoints
                    add_setpoints(
                        connection, runID, int(exp_id), setpoint_df, type_id, type_name
                    )


# **********************************************************************************
#                CLEAN experiment functions FROM delete data file
# **********************************************************************************


def getIDs(run_id, engine):
    """
    Get the range of experiment IDs for a run.
    
    Retrieves the minimum and maximum experiment IDs associated with
    a run, ordered by container number. Useful for batch operations
    on all experiments in a run.
    
    Args:
        run_id (int): The run identifier.
        engine: SQLAlchemy database engine.
    
    Returns:
        tuple: (min_experiment_id, max_experiment_id).
    """

    # Query experiment IDs ordered by container number
    sql_query = f"""
        SELECT experiment_id FROM experiments exp 
        INNER JOIN bioreactors bio ON exp.bioreactor_id = bio.bioreactor_id
        WHERE bio.run_id = {run_id} ORDER BY container_number ASC"""
    df = pd.read_sql(sql_query, engine)
    
    # Find the ID range
    min_value = df["experiment_id"].min()
    max_value = df["experiment_id"].max()

    return min_value, max_value


def deleteMeasurements(min_exp, max_exp, engine):
    """
    Delete dummy measurements for a range of experiments.
    
    Removes all measurements labeled as 'dummy' within the specified
    experiment ID range. Used to clean up placeholder data before
    inserting real measurements.
    
    Args:
        min_exp (int): Minimum experiment ID in range (inclusive).
        max_exp (int): Maximum experiment ID in range (inclusive).
        engine: SQLAlchemy database engine.
    """
    # Delete dummy measurements in the experiment ID range
    sql_query = f"""
        DELETE FROM measurements_experiments 
        WHERE label = 'dummy' AND  experiment_id BETWEEN {min_exp} AND {max_exp} """
    engine.execute(sql_query)


def delete_data(runID):
    """
    Delete all measurement data for a specific run.
    
    Safety function to clean measurement data for emulator runs.
    Only works with whitelisted run IDs to prevent accidental deletion
    of real experimental data. Removes all dummy measurements.
    
    Args:
        runID (int): The run identifier to clean.
    
    Exits:
        If runID is not in the whitelist [623, 671, 672, 770].
    """

    # Whitelist of emulator run IDs that can be safely deleted
    if not runID in [623, 671, 672, 770]:
        print(f"Emulator cannot run in the selected run id: {runID}")
        sys.exit()

    print("Deleting measurements for runID: " f"{runID}")

    # Get experiment ID range for this run
    min_exp, max_exp = getIDs(runID, engine)
    
    # Delete all dummy measurements in this range
    deleteMeasurements(min_exp, max_exp, engine)

    # TODO: Also delete setpoints in future implementation
