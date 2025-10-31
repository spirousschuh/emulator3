# emulator3
# KIWI biolab Emulator

Management of experimental-computational workflows with Apache Airflow and Docker for a biolab experiment emulation.

This project includes a copy of the SQL database as a Docker container with the necessary data initialized, which will be used only if **the experiment sets the run_id in 623**.

## Requeriments
GIT: to download and manage the source code.

Docker: to manage the dependencies and be able to run this example.

## Installation
After getting all the requirements, clone the repository -*emulator3*- with GIT:

    git clone https://github.com/martinfluna/emulator3

Go into the newly clone repository, where the [docker_compose.yml](/docker-compose.yml) is. The first step is to initialize Airflow running in the command line interface (terminal):

    docker-compose up airflow-init

and then generate and start the rest of the services by running:

    docker-compose up -d
(if it doesn't work try  docker compose up -d)

Wait for a few seconds and should be able to access the KIWI experiment DAGs at http://localhost:8080/.

Log in with user: **airflow** and password: **airflow**.

## Configuration variables in the UI

Update Airflow variables with the tab *Admin/Variables* and select *dags/config_test.json* file to import the variables. 

Change the *host_path* variable, with your local absolute path to */dags* directory: "C:/Users/../some_directory/dags"
(use / even on Windows)

## Run the emulator
1- Create an "EMULATOR_config.json" file using "Create_Design.py" in "C:/Users/../some_directory/dags/scripts/emulator_dag"

2 - Go to Airflow in "http://localhost:8080/" and activate the toggle for the Emulator_3.0_DAG and press the play button.

3 - The Emulator will populate the SQL database in port 3306

3b- In addition to the SQL database, the results are stored in "db_emulator.json"

3c- A monitoring tool for the experiment results made with Streamlit can be accessed at http://localhost:8501/

4 - To stop the emulator, untoggle the DAG in the DAGs tab. If there is a Node running, mark it as Success or Fail. Then, delete the DAG using the delete DAG Action. Wait a minute and refresh the browser. The DAG should reappear when it is ready to run again.
