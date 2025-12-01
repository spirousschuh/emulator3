"""
Action Persistence Module.

Saves controller actions and feeding strategies to the database.
"""

import sys
import pandas as pd
import sqlalchemy
import json


def get_connection_url():
    host = "mysql"  # "host.docker.internal"
    port = "3306"
    user = "dbuser"
    password = "dbpassword123"
    database = "ilabdb"

    return f"mysql+mysqlconnector://{user}:{password}@{host}:{port}/{database}"


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


def add_setpoints(connection, runID, exp_id, setpoint_df, type_id=99):
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
    setpoint_df.rename(columns={"measurement_time": "cultivation_age"}, inplace=True)
    setpoint_df["profile_id"] = profile_id
    setpoint_df["variable_type_id"] = type_id
    setpoint_df["scope"] = "e"
    setpoint_df["checksum"] = 1  # IDK what is this
    setpoint_df.to_sql(
        "setpoints", con=connection, if_exists="append", index=False, method="multi"
    )


# %%
if __name__ == "__main__":

    runID = int(sys.argv[1])
    file_path = sys.argv[2]
    exp_ids = json.loads(sys.argv[3])

    # runID = 623
    # file_path = f"dags/results/623/feed/feed_0.json"
    # exp_ids = [exp_id for exp_id in range(19419, 19423)]

    # if runID == 623:
    #     db = 'mysql+mysqlconnector://dbuser:dbpassword123@host.docker.internal:3306/ilabdb'
    # else:
    #     db = 'mysql+mysqlconnector://Autobio:bvt1autobio!@ht-server.bioprocess.tu-berlin.de:3306/ilabdb'
    db = get_connection_url()

    engine = sqlalchemy.create_engine(db, echo=False)

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
