import datetime as dt
import json
import os.path

from airflow.models.dag import DAG
from airflow.models import Variable
from airflow.providers.docker.operators.docker import DockerOperator
from airflow.sensors.time_delta import TimeDeltaSensor
from airflow.utils.task_group import TaskGroup
from airflow import AirflowException
from docker.types import Mount


try:
    host_path = Variable.get("host_path", deserialize_json=True)
except:
    print("Host path has not been addded to the airflow UI variables or it has not been done correctly!")
    host_path = os.path.dirname(__file__)
    print(host_path)

remote_path = "/opt/airflow/dags"


with open(f'{remote_path}/scripts/emulator_dag/EMULATOR_config.json') as json_file:   
    emulator_config = json.load(json_file)


t_duration = emulator_config["experiment_duration"]
acceleration = emulator_config["acceleration"]

# Check values of acceleration
if acceleration not in [1, 2, 4, 60, 54000]:
    raise AirflowException(f"Acceleration {acceleration} is not a valid value [1, 2, 4, 60, 54000]")


def base_docker_node(task_id, command, retries=3, retry_delay=dt.timedelta(minutes=2), 
                     execution_timeout=dt.timedelta(minutes=10), trigger_rule='all_success'):
    
    return DockerOperator(
        task_id=task_id,
        image="emulator2",
        auto_remove="force",
        working_dir=f"{remote_path}/scripts/emulator_dag",
        command=command,
        mounts=[Mount(source=host_path, target=remote_path, type='bind')],
        mount_tmp_dir=False,
        network_mode='emulator3_default',#"bridge",
        retries=retries,
        retry_delay=retry_delay,
        execution_timeout=execution_timeout,
        trigger_rule=trigger_rule 
    )


with DAG(
        dag_id="Emulator_3.0_DAG",
        description="Kiwi experiment emulator.",
        start_date=dt.datetime.now(),
        schedule_interval=None,
        catchup=False,
        is_paused_upon_creation=True
) as dag:

    clean_db = base_docker_node(
        task_id=f"clean_db",
        command=["python", "-c", "from database_connector import delete_data; delete_data(623)"]
    )    

    start_emu = base_docker_node(
        task_id=f"start_emu",
        command=["python", "-c", "from Node_start_emulator import start_emu; start_emu()"],
    )

    save_start_time = base_docker_node(
        task_id=f"save_start_time",
        command=["python", "-c", "from database_connector import save_start_time; save_start_time()"],
    )

    save_feeds = base_docker_node(
        task_id=f"save_feeds",
        command=["python", "-c", "from database_connector import save_multi_actions; save_multi_actions(623, 'db_emulator.json')"]
    ) 

    get_feeds = base_docker_node(
        task_id=f"get_feeds",
        command=["python", "-c", "from database_connector import get_feeds; get_feeds(623)"],
    )

    clean_db >> start_emu >> save_start_time >> save_feeds >> get_feeds
    last_node = get_feeds


    # -----------------------------  one shot  ---------------------------------
    if acceleration == 54000:

        run_emu = base_docker_node(
            task_id=f"run_emu",
            command=["python", "-c", "from Node_run_emulator import run_emu; run_emu()"],
        )

        save_measurements = base_docker_node(
            task_id=f"save_measurements",
            command=["python", "-c", "from database_connector import save_measurements; save_measurements()"],
        )

        get_measurements = base_docker_node(
            task_id=f"get_measurements",
            command=["python", "-c", "from database_connector import query_and_save; query_and_save(623, 'db_output.json')"],
        )

        last_node >> run_emu >> save_measurements >> get_measurements

    # ----------------------------- iterations ---------------------------------
    else:
    
        # iterations every hour to group tasks
        for hours in range(int(t_duration)):

            with TaskGroup(group_id=f"{hours + 1}_hour{'s' if hours+1 > 1 else ''}_tasks"):

                #  iter_minutes[] / acceleration = real time wait
                if acceleration in [1, 2, 4]:
                    iter_minutes = [5, 10, 15, 20, 25, 30, 35, 40, 45, 50, 55, 60]

                if acceleration == 60:
                    iter_minutes = [60]

                for minutes in iter_minutes:

                    time = (hours * 60 + minutes) / acceleration

                    wait = TimeDeltaSensor(
                        task_id=f"wait_{time}_min", 
                        poke_interval=10, trigger_rule='all_done', 
                        delta=dt.timedelta(minutes=time)
                    )

                    get_feeds = base_docker_node(
                        task_id=f"get_feeds_{hours * 60 + minutes}_min",
                        command=["python", "-c", "from database_connector import get_feeds; get_feeds(623)"],
                    )

                    run_emu = base_docker_node(
                        task_id=f"run_emu_{hours * 60 + minutes}_min",
                        command=["python", "-c", "from Node_run_emulator import run_emu; run_emu()"],
                    )

                    save_db_emu = base_docker_node(
                        task_id=f"save_db_{hours * 60 + minutes}_min",
                        command=["python", "-c", "from database_connector import save_measurements; save_measurements()"],
                    )

                    last_node >> wait >> get_feeds >> run_emu >> save_db_emu
                    last_node = save_db_emu
    