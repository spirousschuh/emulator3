"""
Node Testing Module.

Test harness for validating individual DAG nodes and workflows.
"""

import time
import json
import Node_run_emulator
import Node_start_emulator

# %%
with open("EMULATOR_config.json") as json_file:
    EMULATOR_config = json.load(json_file)
acc_factor = EMULATOR_config["acceleration"]

Node_start_emulator.start_emulator()
while 1:

    time.sleep(3600 / acc_factor)

    Node_run_emulator.run_emu()
    print("PING")

    time.sleep(3600 / acc_factor / 24)  # run every 2.5 min (1/24)
