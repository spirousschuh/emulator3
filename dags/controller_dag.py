"""
Controller DAG Module.

This module defines the Airflow DAG for the DOT (Dissolved Oxygen Tension)
controller workflow. It manages periodic data queries, controller execution,
and action persistence for bioreactor experiments (currently commented out).
"""

# import json
# import datetime as dt
# from docker.types import Mount
# from airflow.models.dag import DAG
# from airflow.models import Variable
# from airflow.sensors.time_delta import TimeDeltaSensor
# from airflow.utils.task_group import TaskGroup
# from airflow.providers.docker.operators.docker import DockerOperator


# with DAG(
#         dag_id="Test_DAG",
#         description="Management of workflows.",
#         start_date=dt.datetime.now(),
#         schedule_interval=None,
#         catchup=False,
#         is_paused_upon_creation=True
# ) as dag:

#     # ------------------------------------------------------------------------------------------------------------
#     #                                      VARIABLES DEFINITION
#     # ------------------------------------------------------------------------------------------------------------

#     # directory path for mounting the docker volume
#     host_path = Variable.get("host_path", deserialize_json=True)
#     print(f"host_path = {host_path!r}")
#     remote_path = "/opt/airflow/dags"

#     # all units in minutes
#     config = {
#         "experiment_duration": 16 * 60,
#         "time_start_checking_db": 60,
#         "time_bw_check_db": 5,
#         "runID": 623,
#         "exp_ids": [exp_id for exp_id in range(19419, 19443)]
#     }

#     # ------------------------------------------------------------------------------------------------------------
#     #                                        BASE NODES DEFINITION
#     # ------------------------------------------------------------------------------------------------------------

#     def base_docker_node(task_id, command, retries=3, retry_delay=dt.timedelta(minutes=2),
#                         execution_timeout=dt.timedelta(minutes=10), trigger_rule='all_success'):

#         return DockerOperator(
#             task_id=task_id,
#             image="emulator2",
#             auto_remove="force",
#             working_dir=f"{remote_path}/scripts/controller_dag",
#             command=command,
#             mounts=[Mount(source=host_path, target=remote_path, type='bind')],
#             mount_tmp_dir=False,
#             # network_mode="bridge",
#             network_mode='emulator2_default',#"bridge",
#             retries=retries,
#             retry_delay=retry_delay,
#             execution_timeout=execution_timeout,
#             trigger_rule=trigger_rule
#         )


#     # ------------------------------------------------------------------------------------------------------------
#     #                                     DOT CONTROLLER WORKFLOW
#     # ------------------------------------------------------------------------------------------------------------

#     start = base_docker_node(
#         task_id="init",
#         command=["python", "DOT_Create_config.py"]
#         )
#     last_node = start

#     # calculates iterations every 10'
#     iterations = int((config["experiment_duration"] - config["time_start_checking_db"]) / config["time_bw_check_db"])

#     # iterates every 10'
#     for it10 in range(1, iterations + 1):

#         # wait until next query
#         wait = TimeDeltaSensor(
#             task_id=f"{config['time_bw_check_db'] * it10 + config['time_start_checking_db']}_min_wait",
#             poke_interval=30,
#             trigger_rule='all_done',
#             delta=dt.timedelta(minutes=it10 * config['time_bw_check_db'] + config['time_start_checking_db'])
#         )

#         with TaskGroup(group_id=f"controller_{it10}"):

#             # query data from database:
#             get_measurements = base_docker_node(
#                 task_id=f"get_measurements",
#                 command=["python", "query_and_save.py", str(config["runID"]), f"db_output.json"]
#             )

#             # DOT controller
#             DOT_controller = base_docker_node(
#                 task_id=f"DOT_controller",
#                 command=["python", "DOT_sensor.py"]
#             )

#             # save actions in ilab db
#             save_actions = base_docker_node(
#                 task_id=f"save_actions",
#                 command=["python", "save_actions.py", str(config["runID"]), "Feed.json", json.dumps(config["exp_ids"])]
#             )

#             # set dependencies
#             get_measurements >> DOT_controller >> save_actions


#         # set dependencies
#         last_node >> wait >> get_measurements

#         # save last node for next iteration
#         last_node = wait
