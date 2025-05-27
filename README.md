# CPU Affinity Manager

A GTK4/Libadwaita application to manage CPU affinity for processes on Linux.

## Features

*   **Set CPU Affinity:** Assign specific CPU cores to running processes and their threads.
*   **Process Search:** Find processes by name.
*   **Thread-Level Control:** Applies affinity to all threads of a target process.
*   **Configurable CPU Mask:** Specify which CPU cores a process can use (e.g., "0x00FF00FF").
*   **Initial Delay:** Option to wait a specified number of seconds before applying affinity (useful for games or apps that take time to fully load).
*   **Sudo Privileges:** Option to use `sudo` for `taskset` commands if required for certain processes.
*   **Live Preview:** See which processes will be affected and what settings will be applied before committing.
*   **Save & Load Settings:** Save affinity configurations (CPU mask, delay, sudo preference) per process name for quick re-application.
    *   Settings are stored in `~/.config/affinity-gui/process_settings.json`.
*   **Desktop Integration:** Includes a `.desktop` file and an in-app installer to add the application to your desktop's application menu (e.g., GNOME Overview).

## Requirements

*   Python 3.x
*   GTK4
*   Libadwaita 1
*   The following command-line utilities must be installed and in your PATH:
    *   `pgrep` (usually part of `procps` or `procps-ng`)
    *   `ps` (usually part of `procps` or `procps-ng`)
    *   `taskset` (usually part of `util-linux`)

## Installation

1.  **Clone the repository or download the source files.**
2.  **Ensure all requirements listed above are installed on your system.**
3.  **Run the application:**
    ```bash
    python3 /path/to/affinity_gui/main.py
    ```
4.  **Install to Application Menu (Optional):**
    *   Once the application is running, click the "Install to Applications Menu" button (software install icon) in the header bar.
    *   This will copy the `com.example.AffinitySetter.desktop` file to `~/.local/share/applications/` and update the desktop database.
    *   You might need to log out and log back in for the application to appear in your system's application menu.

## Usage

1.  **Launch the Application:** Either from the command line (as shown above) or from your desktop's application menu if installed.
2.  **Enter Process Name:** Type the name (or part of the name) of the process you want to manage.
    *   Click the search icon to verify if any processes match.
3.  **Configure Settings:**
    *   **CPU Mask:** Enter the desired CPU mask (e.g., `0x000000FF` for cores 0-7). Click the info icon for help on mask format.
    *   **Initial Delay:** Set the number of seconds to wait before applying affinity.
    *   **Use sudo:** Check this box if the target process requires root privileges to modify its affinity.
4.  **Preview:** The "Preview" section will update live, showing which PIDs are found and the settings that will be applied.
5.  **Apply Affinity:** Click the "Apply CPU Affinity" button.
6.  **Save Settings (Optional):**
    *   If you want to reuse these settings for this process name later, click "Save Settings".
7.  **Load Settings (Optional):**
    *   Click the "Saved Settings" menu button (document-save icon) next to the process name entry.
    *   A popover will appear listing all saved process configurations.
    *   Click the "Load" icon next to a saved setting to populate the fields.
    *   Click the "Delete" icon to remove a saved setting.

## How to Run from Source

Navigate to the directory containing `main.py` and run:

```bash
python3 main.py
```

Ensure you have Python 3, GTK4, and Libadwaita development libraries installed.
For example, on a Debian/Ubuntu-based system:

```bash
sudo apt install python3-gi python3-gi-cairo gir1.2-gtk-4.0 gir1.2-adw-1
```

And the command-line tools:

```bash
sudo apt install procps util-linux
```

## Configuration File

Saved process settings are stored in a JSON file located at:
`~/.config/affinity-gui/process_settings.json`

You can manually edit or back up this file if needed. 