"""
One-Shot Execution Module.

Provides standalone execution capability for single simulation runs.
"""

import time
import Node_run_dtwin
import Node_start_dtwin

# import numpy as np
# import json

# %%
# Node_design_file.create()
# Node_createDesign_json.create()

Node_start_dtwin.start_dtwin()
time_a = time.time()
# time_b=time.time()
time.sleep(0.934 / 10)
# %%
time_c = time.time()
# Node_run_dtwin.run_dtwin()
Node_run_dtwin.run_dtwin()
time_d = time.time()

print(time_d - time_c)
