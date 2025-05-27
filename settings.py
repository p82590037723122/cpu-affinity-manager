import json
import os
from pathlib import Path

class SettingsManager:
    def __init__(self):
        self.config_dir = Path.home() / '.config' / 'affinity-gui'
        self.settings_file = self.config_dir / 'process_settings.json'
        self.settings = self._load_settings()

    def _load_settings(self):
        """Load settings from the JSON file."""
        if not self.settings_file.exists():
            return {}

        try:
            with open(self.settings_file, 'r') as f:
                return json.load(f)
        except (json.JSONDecodeError, IOError) as e:
            print(f"Error loading settings: {e}")
            return {}

    def _save_settings(self):
        """Save settings to the JSON file."""
        try:
            self.config_dir.mkdir(parents=True, exist_ok=True)
            with open(self.settings_file, 'w') as f:
                json.dump(self.settings, f, indent=4)
            return True
        except IOError as e:
            print(f"Error saving settings: {e}")
            return False

    def save_process_settings(self, process_name, settings):
        """Save settings for a specific process."""
        self.settings[process_name] = settings
        return self._save_settings()

    def get_process_settings(self, process_name):
        """Get settings for a specific process."""
        return self.settings.get(process_name)

    def get_all_processes(self):
        """Get a list of all saved process names."""
        return list(self.settings.keys())

    def delete_process_settings(self, process_name):
        """Delete settings for a specific process."""
        if process_name in self.settings:
            del self.settings[process_name]
            return self._save_settings()
        return False 