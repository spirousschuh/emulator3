import json
import os.path
from pathlib import Path

import pytest
import time


from dags.scripts.emulator_dag.Node_run_emulator import run_emu
from dags.scripts.emulator_dag.Node_start_emulator import start_emu


@pytest.fixture
def emulator_dag_path():
    from dags.scripts import emulator_dag

    return Path(os.path.dirname(emulator_dag.__file__))

def test_node_run_emulator(emulator_dag_path, tmp_path):
    with open(emulator_dag_path / "EMULATOR_config.json") as json_file:
        EMULATOR_config = json.load(json_file)

    acc_factor = EMULATOR_config["acceleration"]

    start_emu(
        db_emulator_template=emulator_dag_path / "db_emulator_template_new.json",
        db_emulator_output=emulator_dag_path / "db_emulator.json",
        emulator_config_file=emulator_dag_path / "EMULATOR_config.json",
        first_state_output_file=tmp_path / "EMULATOR_state.json",
        first_design_output_file=tmp_path / "EMULATOR_design.json",
    )
    for _ in range(2):
        time.sleep(3600 / acc_factor)

        run_emu(
            emulator_state_file=tmp_path / "EMULATOR_state.json",
            emulator_design_file=tmp_path / "EMULATOR_design.json",
            emulator_config_file=emulator_dag_path / "EMULATOR_config.json",
            state_output_file=tmp_path / "EMULATOR_state.json",
        )
        print("PING")

        time.sleep(3600 / acc_factor / 24)  # run every 2.5 min (1/24)

