"""
Auxiliary Database Module.

Helper functions for database operations and data transformations.
"""

import numpy as np
import pandas as pd
import json
import time


with open("db_emulator_template.json") as json_file:
    db_emulator = json.load(json_file)

for i1 in db_emulator:
    for i2 in ["Cumulated_feed_volume_dextrine", "Cumulated_feed_volume_enzyme"]:
        db_emulator[i1]["measurements_aggregated"][i2] = {
            "measurement_time": {},
            i2: {},
        }

    for i3 in [
        "Feed_glc_cum_setpoints",
        "Feed_dextrine_cum_setpoints",
        "Feed_enzyme_cum_setpoints",
    ]:
        db_emulator[i1]["setpoints"][i3] = {"setpoint_time": {}, i3: {}}

with open("db_emulator_template_new.json", "w") as out_file:
    json.dump(db_emulator, out_file)
