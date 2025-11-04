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
    Get all the measurements for a runID from the database. Grouped by (exp_id, measurement)
    """

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


def get_exp_ids(runID, engine):
    """
    Get all exp_ids for a runID from the database.
    """

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
    Get all the setpoints for a runID from the database. Grouped by (exp_id, setpoints)
    """

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


def read_run(runID):
    """
    creates a json file with metadata, setpoints and measurements for an specific runID
    """

    # connect to database
    db = get_connection_url()
    engine = sqlalchemy.create_engine(db, echo=False)

    # initial data
    json_data = {}

    # get metadata
    metadata_df = get_metadata(runID, engine)

    # create template
    exp_ids = get_exp_ids(runID, engine)
    for exp_id in exp_ids:
        json_data[exp_id] = {
            "metadata": {},
            "setpoints": {},
            "measurements_aggregated": {},
        }

    # get setpoints
    setpoints_groups_df = get_setpoints(runID, engine)

    # get measurements
    measurements_groups_df = get_measurements(runID, engine)

    # iterate setpoints groups
    for (exp_id, variable), group in setpoints_groups_df:
        # rename column by variable type
        group.rename(
            columns={"setpoint_value": variable, "cultivation_age": "setpoint_time"},
            inplace=True,
        )

        # Reset index: to start from 0 for each measurement count of the original dataframe
        json_data[exp_id]["setpoints"][variable] = json.loads(
            group.reset_index()[["setpoint_time", variable]].to_json()
        )

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


def query_and_save(runID, filepath):
    """
    Get all the information from a runID
    """

    rootdir = os.getcwd()

    db_json = read_run(runID)

    # save JSON file for historical monitoring
    if not os.path.isdir(os.path.dirname(f"{rootdir}/{filepath}")):
        os.makedirs(os.path.dirname(f"{rootdir}/{filepath}"))

    pd.DataFrame(db_json).to_json(f"{rootdir}/{filepath}")


# **********************************************************************************
#                   FEEDS functions FROM save actions file
# **********************************************************************************


def run2ids(connection, runID):
    """
    Returns the profile ids and name for a given runID

    Parameters
    ----------
    connection: sqlalchemy.engine.Connection
        Connection to mysql db using sqlalchemy.
    runID: int
        Identification number for a experiment.
    """
    query = sqlalchemy.text(
        f"SELECT profiles.profile_id, profiles.profile_name, experiments.experiment_id "
        f"FROM profiles "
        f"INNER JOIN experiments ON profiles.profile_id=experiments.profile_id "
        f"WHERE run_id = {runID};"
    )

    return pd.read_sql(query, connection)


def delete_setpoints(connection, runID, exp_id, from_time=0, type_id=99):
    """
    Deletes setpoints from a given runID and bioreactor, from a given time on.

    Parameters
    ----------
    connection: sqlalchemy.engine.Connection
        Connection to mysql db using sqlalchemy.
    runID: int
        Identification number for a experiment.
    exp_id: int
        The exp_id value for the MBR in the current runID.
    from_time: int/float
        The time (in seconds) from which the setpoints want to be deleted.
    type_id: int
        Which setpoint want to be changed. In the database, this would be the 'variable_type_id' column.

    """
    print(
        f"Attention! This will delete the setpoint data for run {runID} and bioreactor exp_id {exp_id} after experiment"
        f"time {from_time}s. Press enter to continue and q to quit."
    )

    profiles = run2ids(connection, runID)
    profile_id = profiles.loc[profiles["experiment_id"] == exp_id]["profile_id"].iloc[0]
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
    Adds setpoints to a given experiment (runID) in a specific position (profile_name).

    Parameters
    ----------
    connection: sqlalchemy.engine.Connection
        Connection to mysql db using sqlalchemy.
    runID: int
        Identification number for a experiment.
    exp_id: int
        The exp_id value for the MBR in the current runID.
    setpoint_df: pandas.DataFrame
        A dataframe with two columns measurement_time and setpoint_value
    type_id: int
        Which setpoint want to be changed. In the database, this would be the 'variable_type_id' column.

    """
    profiles = run2ids(connection, runID)
    profile_id = profiles.loc[profiles["experiment_id"] == exp_id]["profile_id"].iloc[0]
    setpoint_df.rename(columns={"setpoint_time": "cultivation_age"}, inplace=True)
    setpoint_df.rename(columns={type_name: "setpoint_value"}, inplace=True)
    setpoint_df["profile_id"] = profile_id
    setpoint_df["variable_type_id"] = type_id
    setpoint_df["scope"] = "e"
    setpoint_df["checksum"] = 1  # IDK what is this
    setpoint_df.to_sql(
        "setpoints", con=connection, if_exists="append", index=False, method="multi"
    )


def save_actions(runID, file_path):
    """
    Main function to save all feeding profiles for MBRs for a runID and a file containing the feeds.
    """

    with open(file_path, "r") as file:
        feed = json.load(file)
        file.close()

    setpoints_df = dict()
    for exp_id in feed:
        setpoints_df[exp_id] = pd.DataFrame.from_dict(feed[exp_id])

    # delete setpoint and add new values for each exp_id (mbr)
    with engine.connect() as connection:
        with connection.begin():
            for exp_id in setpoints_df:
                delete_setpoints(connection, runID, int(exp_id))
                add_setpoints(connection, runID, int(exp_id), setpoints_df[exp_id])


def save_multi_actions(runID, file_path):
    """
    Main function to save all setpoints profiles for MBRs from file.
    """

    with open(file_path, "r") as file:
        feed = json.load(file)
        file.close()

    variable_types = [
        (99, "Feed_glc_cum_setpoints"),
        (112, "Feed_enzyme_cum_setpoints"),
        (131, "Feed_dextrine_cum_setpoints"),
    ]

    # delete setpoint and add new values for each exp_id (mbr)
    with engine.connect() as connection:
        with connection.begin():
            for exp_id in feed:

                # delete/add data for each variable type
                for type_id, type_name in variable_types:

                    setpoint_df = pd.DataFrame.from_dict(
                        feed[exp_id]["setpoints"][type_name]
                    )

                    delete_setpoints(connection, runID, int(exp_id), 0, type_id)
                    add_setpoints(
                        connection, runID, int(exp_id), setpoint_df, type_id, type_name
                    )


# **********************************************************************************
#                CLEAN experiment functions FROM delete data file
# **********************************************************************************


def getIDs(run_id, engine):
    """
    Get experiments IDs for a runID
    """

    sql_query = f"""
        SELECT experiment_id FROM experiments exp 
        INNER JOIN bioreactors bio ON exp.bioreactor_id = bio.bioreactor_id
        WHERE bio.run_id = {run_id} ORDER BY container_number ASC"""
    df = pd.read_sql(sql_query, engine)
    min_value = df["experiment_id"].min()
    max_value = df["experiment_id"].max()

    return min_value, max_value


def deleteMeasurements(min_exp, max_exp, engine):
    """
    Delete all the measurements for a range of experiments IDs
    """
    sql_query = f"""
        DELETE FROM measurements_experiments 
        WHERE label = 'dummy' AND  experiment_id BETWEEN {min_exp} AND {max_exp} """
    engine.execute(sql_query)


def delete_data(runID):
    """
    Delete all the information for an specific runID
    """

    if not runID in [623, 671, 672, 770]:
        print(f"Emulator cannot run in the selected run id: {runID}")
        sys.exit()

    print("Deleting measurements for runID: " f"{runID}")

    min_exp, max_exp = getIDs(runID, engine)
    deleteMeasurements(min_exp, max_exp, engine)

    # TODO: delete setpoints
