# cpu-affinity-manager/utils.py

import subprocess
import os
import time
import re
import gettext

DEFAULT_CPU_MASK = "0x00FF00FF"  # Cores 0-7 and 16-23

def validate_cpu_mask(cpu_mask):
    """Validate CPU mask format (should be 0x followed by hexadecimal digits)."""
    if not cpu_mask:
        return False
    # Check if it matches the pattern 0x followed by one or more hex digits
    if not re.match(r'^0x[0-9a-fA-F]+$', cpu_mask):
        return False
    # Ensure it's not just "0x" with no digits
    if len(cpu_mask) <= 2:
        return False
    return True

def get_pids_by_name(process_name):
    """Finds PIDs matching a given process name."""
    if not process_name:
        return []
    try:
        # Using pgrep -f to match against the full command line
        result = subprocess.run(['pgrep', '-f', process_name], capture_output=True, text=True, check=False)
        if result.returncode == 0 and result.stdout:
            return [pid.strip() for pid in result.stdout.strip().split('\n') if pid.strip()]
        else:
            return [] # No process found or pgrep error
    except FileNotFoundError:
        print("Error: pgrep command not found. Please ensure it's installed and in your PATH.")
        return []
    except Exception as e:
        print(f"Error finding PIDs for '{process_name}': {e}")
        return []

def hex_to_cpu_set(hex_mask):
    """Convert a hex mask string (e.g. '0x03') to a set of CPU integers."""
    # Remove 0x prefix if present and convert to int
    mask_int = int(hex_mask, 16)
    cpus = set()
    cpu_idx = 0
    while mask_int > 0:
        if mask_int & 1:
            cpus.add(cpu_idx)
        mask_int >>= 1
        cpu_idx += 1
    return cpus

def get_tids_for_pid(pid):
    """Gets all thread IDs (TIDs) for a given PID using /proc."""
    try:
        task_dir = f'/proc/{pid}/task'
        if os.path.exists(task_dir):
            return sorted([tid for tid in os.listdir(task_dir) if tid.isdigit()])
    except Exception as e:
        print(f"Error reading threads for PID {pid}: {e}")
    
    # Fallback to ps command if /proc access fails
    try:
        # ps -T -p <PID> -o tid=  (the '=' after tid removes the header)
        result = subprocess.run(['ps', '-T', '-p', str(pid), '-o', 'tid='], capture_output=True, text=True, check=False)
        if result.returncode == 0 and result.stdout:
            return [tid.strip() for tid in result.stdout.strip().split('\n') if tid.strip() and tid.strip().isdigit()]
    except Exception:
        pass
        
    return []

def set_affinity_for_tid(tid, cpu_mask, quiet=False):
    """Sets CPU affinity for a specific thread ID (TID) using os.sched_setaffinity if available."""
    tid_int = int(tid)
    try:
        # Try to use efficient OS call first
        if hasattr(os, 'sched_getaffinity') and hasattr(os, 'sched_setaffinity'):
            target_cpus = hex_to_cpu_set(cpu_mask)
            try:
                current_cpus = os.sched_getaffinity(tid_int)
                if current_cpus == target_cpus:
                    # Already set correctly, skipping
                    return True
            except OSError:
                # Process might have died or permission denied
                pass

            os.sched_setaffinity(tid_int, target_cpus)
            return True

    except Exception as e:
        if not quiet:
            print(f"Native affinity set failed for TID {tid}, falling back to taskset: {e}")

    # Fallback to taskset command
    command = ['taskset', '-p', cpu_mask, str(tid)]
    
    try:
        result = subprocess.run(command, capture_output=True, text=True, check=False)
        if result.returncode == 0:
            return True
        else:
            if not quiet:
                print(f"ERROR: Failed to set affinity for TID {tid} to {cpu_mask}.")
                print(f"  Command: {' '.join(command)}")
                print(f"  Taskset stderr: {result.stderr.strip()}")
                print(f"  Taskset stdout: {result.stdout.strip()}")
            return False
    except FileNotFoundError:
        if not quiet:
            print("Error: taskset command not found. Please ensure it's installed and in your PATH.")
        return False
    except Exception as e:
        if not quiet:
            print(f"Exception while trying to set affinity for TID {tid}: {e}")
        return False

def apply_cpu_affinity(process_name, cpu_mask=DEFAULT_CPU_MASK, initial_delay=0, quiet=False):
    """
    Applies CPU affinity to all threads of processes matching process_name.

    Args:
        process_name (str): Name of the process to set affinity for
        cpu_mask (str): CPU mask in hex format (e.g., "0x00FF00FF")
        initial_delay (int): Seconds to wait before applying affinity
        quiet (bool): If True, suppress standard output/logging

    Returns:
        tuple: (success_status, total_threads_succeeded, total_threads_attempted)
    """
    # Validate CPU mask
    if not validate_cpu_mask(cpu_mask):
        if not quiet:
            print(f"Invalid CPU mask format: {cpu_mask}. Expected format: 0x followed by hexadecimal digits (e.g., 0x00FF00FF)")
        return False, 0, 0

    if initial_delay > 0:
        if not quiet:
            print(f"Waiting {initial_delay} seconds before applying CPU affinity...")
        time.sleep(initial_delay)

    pids = get_pids_by_name(process_name)
    if not pids:
        if not quiet:
            print(f"No process found with name: {process_name}")
        return False, 0, 0

    overall_success = True
    total_tids_succeeded = 0
    total_tids_attempted = 0

    for pid in pids:
        if not quiet:
            print(f"Processing PID {pid} for '{process_name}'...")
        tids = get_tids_for_pid(pid)
        if not tids:
            if not quiet:
                print(f"  No threads found for PID {pid}, or failed to retrieve them. Attempting on PID {pid} directly.")
            total_tids_attempted += 1
            if set_affinity_for_tid(pid, cpu_mask, quiet=quiet):
                total_tids_succeeded += 1
            else:
                overall_success = False
            continue

        if not quiet:
            print(f"  Found threads for PID {pid}: {tids}")
        for tid in tids:
            total_tids_attempted += 1
            if set_affinity_for_tid(tid, cpu_mask, quiet=quiet):
                total_tids_succeeded += 1
            else:
                overall_success = False

    if total_tids_attempted == 0:
        if not quiet:
            print(f"Warning: No PIDs or TIDs were processed for '{process_name}'.")
        return False, 0, 0
        
    if not quiet:
        print(f"Finished applying affinity for '{process_name}'. \n"
              f"Successfully set affinity for {total_tids_succeeded} out of {total_tids_attempted} threads/processes.")
    
    return overall_success and total_tids_succeeded > 0, total_tids_succeeded, total_tids_attempted
