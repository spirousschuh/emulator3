import datetime as dt
import json
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


remote_path = "/opt/airflow/dags"


with open(f'{remote_path}/scripts/dtwin_dag/DTWIN_config.json') as json_file:   
    dtwin_config = json.load(json_file)


t_duration = dtwin_config["experiment_duration"]
acceleration =  dtwin_config["acceleration"]

# Check values of acceleration
if acceleration not in [1, 2, 4, 60, 54000]:
    raise AirflowException(f"Acceleration {acceleration} is not a valid value [1, 2, 4, 60, 54000]")


def base_docker_node(task_id, command, retries=1, retry_delay=dt.timedelta(minutes=2), 
                     execution_timeout=dt.timedelta(minutes=10), trigger_rule='all_success'):
    
    return DockerOperator(
        task_id=task_id,
        image="emulator2",
        auto_remove="force",
        working_dir=f"{remote_path}/scripts/dtwin_dag",
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
        dag_id="DTwin_3.0_DAG",
        description="Kiwi experiment dtwin.",
        start_date=dt.datetime.now(),
        schedule_interval=None,
        catchup=False,
        is_paused_upon_creation=True
) as dag:

    start_dtwin = base_docker_node(
        task_id=f"start_dtwin",
        command=["python", "-c", "from Node_start_dtwin import start_dtwin; start_dtwin()"],
    )


    last_node = start_dtwin
    
    last_node_update = start_dtwin

# -----------------------------  DTwin  ---------------------------------
    
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



                run_dtwin = base_docker_node(
                    task_id=f"run_dtwin_{hours * 60 + minutes}_min",
                    command=["python", "-c", "from Node_run_dtwin import run_dtwin; run_dtwin()"],
                )

                last_node >> wait >> run_dtwin 
                last_node = run_dtwin    
# ----------------------------- Update Param ---------------------------------

    # iterations every hour to group tasks
    for hours in range(int(t_duration)):

        with TaskGroup(group_id=f"{hours + 2}_hour{'s' if hours+1 > 1 else ''}_update_tasks"):


            iter_minutes_dtwin_update = [60]

            for minutes in iter_minutes_dtwin_update:

                time = (hours * 60 + minutes+70) / acceleration

                wait_update = TimeDeltaSensor(
                    task_id=f"wait_{time}_min", 
                    poke_interval=10, trigger_rule='all_done', 
                    delta=dt.timedelta(minutes=time)
                )

                get_measurements = base_docker_node(
                    task_id=f"get_measurements",
                    command=["python", "-c", "from database_connector import query_and_save; query_and_save(623, 'db_output.json')"],
                )
                update_dtwin = base_docker_node(
                    task_id=f"update_dtwin_{hours * 60 + minutes}_min",
                    command=["python", "-c", "from methodParamEst import update_group; update_group(['19419','19420','19427','19428','19435','19436'])"],
                )

                last_node_update >> wait_update >> get_measurements >> update_dtwin 
                last_node_update = wait_update
