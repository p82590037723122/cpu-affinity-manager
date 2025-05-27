#!/bin/bash

# Usage: ./set_cpu_affinity.sh process_name
# Example: ./set_cpu_affinity.sh myprocess

sleep 20

PROCESS_NAME="$1"
CPU_MASK="0x00FF00FF"  # Cores 0-7 and 16-23

if [[ -z "$PROCESS_NAME" ]]; then
    echo "Usage: $0 <process_name>"
    echo "Example: $0 myprocess"
    exit 1
fi

# Find process IDs matching the name
PIDS=$(pgrep -f "$PROCESS_NAME")

if [[ -z "$PIDS" ]]; then
    echo "No process found with name: $PROCESS_NAME"
    exit 1
fi

# Set CPU affinity for each PID by iterating through its threads
for PID in $PIDS; do
    echo "Processing PID $PID..."
    # Get all thread IDs for this PID, stripping header and extra spaces
    TIDS=$(ps -T -p "$PID" -o tid= | awk '{print $1}')

    if [[ -z "$TIDS" ]]; then
        echo "  No threads found for PID $PID (or ps command failed). Attempting to set for PID $PID itself as a fallback."
        echo "  Setting CPU affinity for PID $PID to $CPU_MASK"
        if taskset -p "$CPU_MASK" "$PID"; then
            echo "    Successfully set affinity for PID $PID."
        else
            echo "    ERROR: Failed to set affinity for PID $PID. Taskset exit code: $?"
        fi
        continue # Move to next PID
    fi

    echo "  Found threads for PID $PID: $TIDS"
    SUCCESS_COUNT=0
    FAILURE_COUNT=0
    for TID in $TIDS; do
        # Ensure TID is a number, skip if not (e.g. if ps output was unexpected)
        if ! [[ "$TID" =~ ^[0-9]+$ ]]; then
            echo "    Skipping invalid TID: $TID"
            continue
        fi
        echo "    Setting CPU affinity for TID $TID (of PID $PID) to $CPU_MASK"
        if taskset -p "$CPU_MASK" "$TID"; then
            # echo "      Successfully set affinity for TID $TID." # Optional: reduce verbosity
            ((SUCCESS_COUNT++))
        else
            echo "      ERROR: Failed to set affinity for TID $TID. Taskset exit code: $?"
            ((FAILURE_COUNT++))
        fi
    done
    echo "  Finished processing PID $PID. Successful thread affinity settings: $SUCCESS_COUNT. Failures: $FAILURE_COUNT."
done
