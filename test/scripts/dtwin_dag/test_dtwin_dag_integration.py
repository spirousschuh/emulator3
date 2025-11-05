import os
import time
from pathlib import Path

import pytest

from dags.scripts.dtwin_dag.Node_run_dtwin import run_dtwin
from dags.scripts.dtwin_dag.Node_start_dtwin import start_dtwin


@pytest.fixture
def dtwin_dag_path():
    from dags.scripts import dtwin_dag

    return Path(os.path.dirname(dtwin_dag.__file__))


def test_dtwin_dag_integration(dtwin_dag_path, tmp_path):
    save_state_file = tmp_path / "DTWIN_state.json"
    save_design_file = tmp_path / "DTWIN_design.json"
    save_prediction_file = tmp_path / "DTWIN_prediction.json"
    save_dtwin_db_file = tmp_path / "db_dtwin.json"
    db_state = tmp_path / "db_dtwin.json"

    start_dtwin(
        db_twin_template=dtwin_dag_path / "db_dtwin_template.json",
        db_twin_output=db_state,
        config_file=dtwin_dag_path / "DTWIN_config.json",
        state_output_file=save_state_file,
        design_output_file=save_design_file,
        prediction_output_file=save_prediction_file,
        db_dtwin_output=save_dtwin_db_file,
    )
    acc_factor = 3600 * 1

    for _ in range(2):
        time.sleep(3600 / acc_factor)
        run_dtwin(
            state_file=save_state_file,
            design_file=save_design_file,
            config_file=dtwin_dag_path / "DTWIN_config.json",
            db_input_file=db_state,
            db_output_file=db_state,
        )
        print("PING")

        time.sleep(3600 / acc_factor / 1)  # run every 2.5 min (1/24)
