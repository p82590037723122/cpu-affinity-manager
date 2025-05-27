# affinity_gui/utils.py

import subprocess
import os
import time

DEFAULT_CPU_MASK = "0x00FF00FF"  # Cores 0-7 and 16-23

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

def get_tids_for_pid(pid):
    """Gets all thread IDs (TIDs) for a given PID."""
    try:
        # ps -T -p <PID> -o tid=  (the '=' after tid removes the header)
        result = subprocess.run(['ps', '-T', '-p', str(pid), '-o', 'tid='], capture_output=True, text=True, check=False)
        if result.returncode == 0 and result.stdout:
            return [tid.strip() for tid in result.stdout.strip().split('\n') if tid.strip() and tid.strip().isdigit()]
        else:
            print(f"Could not get TIDs for PID {pid}. ps output: {result.stderr or result.stdout}")
            return []
    except FileNotFoundError:
        print("Error: ps command not found. Please ensure it's installed and in your PATH.")
        return []
    except Exception as e:
        print(f"Error getting TIDs for PID {pid}: {e}")
        return []

def set_affinity_for_tid(tid, cpu_mask, use_sudo=False):
    """Sets CPU affinity for a specific thread ID (TID) using taskset."""
    command = ['taskset', '-p', cpu_mask, str(tid)]
    if use_sudo:
        command.insert(0, 'sudo')
    
    try:
        result = subprocess.run(command, capture_output=True, text=True, check=False)
        if result.returncode == 0:
            # print(f"Successfully set affinity for TID {tid} to {cpu_mask}")
            return True
        else:
            print(f"ERROR: Failed to set affinity for TID {tid} to {cpu_mask}.")
            print(f"  Command: {' '.join(command)}")
            print(f"  Taskset stderr: {result.stderr.strip()}")
            print(f"  Taskset stdout: {result.stdout.strip()}")
            return False
    except FileNotFoundError:
        print(f"Error: {'sudo' if use_sudo else ''} taskset command not found. Please ensure it's installed and in your PATH.")
        return False
    except Exception as e:
        print(f"Exception while trying to set affinity for TID {tid}: {e}")
        return False

def apply_cpu_affinity(process_name, cpu_mask=DEFAULT_CPU_MASK, use_sudo=False, initial_delay=0):
    """
    Applies CPU affinity to all threads of processes matching process_name.
    
    Args:
        process_name (str): Name of the process to set affinity for
        cpu_mask (str): CPU mask in hex format (e.g., "0x00FF00FF")
        use_sudo (bool): Whether to use sudo for taskset commands
        initial_delay (int): Seconds to wait before applying affinity
    
    Returns:
        tuple: (success_status, total_threads_succeeded, total_threads_attempted)
    """
    if initial_delay > 0:
        print(f"Waiting {initial_delay} seconds before applying CPU affinity...")
        time.sleep(initial_delay)

    pids = get_pids_by_name(process_name)
    if not pids:
        print(f"No process found with name: {process_name}")
        return False, 0, 0

    overall_success = True
    total_tids_succeeded = 0
    total_tids_attempted = 0

    for pid in pids:
        print(f"Processing PID {pid} for '{process_name}'...")
        tids = get_tids_for_pid(pid)
        if not tids:
            print(f"  No threads found for PID {pid}, or failed to retrieve them. Attempting on PID {pid} directly.")
            total_tids_attempted += 1
            if set_affinity_for_tid(pid, cpu_mask, use_sudo):
                total_tids_succeeded += 1
            else:
                overall_success = False
            continue

        print(f"  Found threads for PID {pid}: {tids}")
        for tid in tids:
            total_tids_attempted += 1
            if set_affinity_for_tid(tid, cpu_mask, use_sudo):
                total_tids_succeeded += 1
            else:
                overall_success = False

    if total_tids_attempted == 0:
        print(f"Warning: No PIDs or TIDs were processed for '{process_name}'.")
        return False, 0, 0
        
    print(f"Finished applying affinity for '{process_name}'. \n"
          f"Successfully set affinity for {total_tids_succeeded} out of {total_tids_attempted} threads/processes.")
    
    return overall_success and total_tids_succeeded > 0, total_tids_succeeded, total_tids_attempted


# Example Usage (for testing later):
# if __name__ == '__main__':
#     # Create a dummy process to test with: sleep 120
#     # Then run this script
#     # process_to_target = "sleep"
#     # test_mask = "0x00000001" # Core 0
    
#     # Or target an existing process, e.g., your shell if you know its name
#     process_to_target = "bash" # Be careful with this!
#     test_mask = "0x0000000F" # Cores 0-3

#     print(f"Attempting to set affinity for '{process_to_target}' to mask '{test_mask}'")
    
#     # Note: You might need to run the test with sudo depending on the target process
#     # and your system permissions, e.g., python affinity_gui/utils.py
#     # or sudo python affinity_gui/utils.py
#     # For processes owned by your user, sudo might not be needed IF your user has cap_sys_nice capability
#     # or if unprivileged users are allowed to set affinity (less common).
    
#     # For testing without sudo first:
#     # success, succeeded_count, attempted_count = apply_cpu_affinity(process_to_target, test_mask, use_sudo=False)
    
#     # For testing WITH sudo (more likely to succeed for various processes):
#     print("Testing with sudo. You may be prompted for your password.")
#     success, succeeded_count, attempted_count = apply_cpu_affinity(process_to_target, test_mask, use_sudo=True)

#     if success:
#         print(f"Successfully applied affinity for '{process_to_target}'. {succeeded_count}/{attempted_count} threads/PIDs affected.")
#     else:
#         print(f"Failed to apply affinity for '{process_to_target}'. {succeeded_count}/{attempted_count} threads/PIDs affected.")

#     # To verify, you can use: ps -o psr -p $(pgrep -f sleep) OR htop and filter for 'sleep'
#     # Or for the bash example: ps -o psr -p $$ (to check current shell's core) 