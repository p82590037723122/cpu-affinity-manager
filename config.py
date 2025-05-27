# affinity_gui/config.py

import json
import os

PROFILES_FILE = "game_profiles.json" # Or a path within user's config directory

def load_profiles():
    """Loads game/process profiles from the JSON file."""
    if not os.path.exists(PROFILES_FILE):
        return {}
    try:
        with open(PROFILES_FILE, 'r') as f:
            profiles = json.load(f)
        return profiles
    except (json.JSONDecodeError, IOError) as e:
        print(f"Error loading profiles: {e}")
        return {}

def save_profiles(profiles):
    """Saves the given profiles to the JSON file."""
    try:
        with open(PROFILES_FILE, 'w') as f:
            json.dump(profiles, f, indent=4)
        print(f"Profiles saved to {PROFILES_FILE}")
        return True
    except IOError as e:
        print(f"Error saving profiles: {e}")
        return False

# Example Usage (for testing later):
# if __name__ == '__main__':
#     test_profiles = {
#         "game1": {"process_name": "game1.exe", "cpu_mask": "0xFF"},
#         "game2": {"process_name": "another_app", "cpu_mask": "0xF0F0"}
#     }
#     save_profiles(test_profiles)
#     loaded = load_profiles()
#     print(f"Loaded: {loaded}") 