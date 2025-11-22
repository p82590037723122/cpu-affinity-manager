#!/usr/bin/env python3
import sys
import os

# If running from system install, add APP_DIR to sys.path so imports work
if 'APP_DIR' in os.environ:
    sys.path.append(os.environ['APP_DIR'])

from settings import SettingsManager
from utils import apply_cpu_affinity

def auto_apply():
    """
    Iterate through saved processes and apply CPU affinity settings.
    Designed to be run by a periodic background timer.
    """
    try:
        manager = SettingsManager()
        saved_processes = manager.get_all_processes()
        
        if not saved_processes:
            # No settings saved, nothing to do
            return

        # Check each saved process
        for process_name in saved_processes:
            settings = manager.get_process_settings(process_name)
            if not settings:
                continue

            cpu_mask = settings.get('cpu_mask')
            if not cpu_mask:
                continue

            # Apply affinity with 0 delay and quiet mode
            # We use 0 delay because this script runs periodically, so we don't want to block
            # We use quiet mode to avoid spamming the journal/logs every time it runs
            # It will still apply if the process is found running.
            apply_cpu_affinity(
                process_name, 
                cpu_mask=cpu_mask, 
                initial_delay=0, 
                quiet=True
            )

    except Exception as e:
        # If something goes wrong, print to stderr so it shows up in logs
        print(f"Error in auto-affinity script: {e}", file=sys.stderr)

if __name__ == "__main__":
    auto_apply()

