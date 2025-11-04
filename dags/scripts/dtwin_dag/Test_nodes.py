"""
Node Testing Module.

Test harness for validating individual DAG nodes and workflows.
"""

import time
import Node_run_dtwin
import Node_start_dtwin

# %%
# runfile('Node_start_dtwin.py')
Node_start_dtwin.start_dtwin()
while 1:
    acc_factor = 60 * 1
    time.sleep(3600 / acc_factor)
    # runfile('Node_run_dtwin.py')
    Node_run_dtwin.run_dtwin()
    print("PING")

    time.sleep(3600 / acc_factor / 1)  # run every 2.5 min (1/24)
