import gi
gi.require_version('Gtk', '4.0')
gi.require_version('Adw', '1')
from gi.repository import Gtk, Adw, Gio, GLib, Gdk

import sys
import os
import subprocess
import gettext
import locale
import threading
from pathlib import Path
from utils import apply_cpu_affinity, DEFAULT_CPU_MASK, get_pids_by_name, validate_cpu_mask
from settings import SettingsManager

APP_ID = 'io.github.p82590037723122.CPU_Affinity_Manager'

# Get the directory containing this file
BASE_DIR = os.environ.get('APP_DIR', os.path.dirname(os.path.abspath(__file__)))
LOCALE_DIR = os.environ.get('LOCALE_DIR', os.path.join(BASE_DIR, 'locale'))
UI_FILE = os.path.join(BASE_DIR, 'affinity_window.ui')

# Setup gettext
try:
    locale.setlocale(locale.LC_ALL, '')
except locale.Error:
    pass

gettext.bindtextdomain(APP_ID, LOCALE_DIR)
gettext.textdomain(APP_ID)
_ = gettext.gettext

@Gtk.Template(filename=UI_FILE)
class CPUAffinityManagerWindow(Adw.ApplicationWindow):
    __gtype_name__ = "CPUAffinityManagerWindow"

    # Template children
    process_entry = Gtk.Template.Child()
    search_button = Gtk.Template.Child()
    settings_menu_button = Gtk.Template.Child()
    mask_container = Gtk.Template.Child()
    mask_dropdown = Gtk.Template.Child()
    custom_mask_entry = Gtk.Template.Child()
    delay_spin = Gtk.Template.Child()
    preview_label = Gtk.Template.Child()
    status_label = Gtk.Template.Child()
    save_button = Gtk.Template.Child()
    apply_button = Gtk.Template.Child()
    info_button = Gtk.Template.Child()

    def __init__(self, **kwargs):
        super().__init__(**kwargs)

        self.save_button.connect('clicked', self.on_save_clicked)
        self.apply_button.connect('clicked', self.on_apply_clicked)
        self.search_button.connect('clicked', self.on_search_clicked)
        self.info_button.connect('clicked', self.on_info_clicked)
        self.connect('close-request', self.on_close_request)
        
        # Input change handlers
        self.mask_dropdown.connect('notify::selected', self.on_mask_selection_changed)
        self.process_entry.connect('changed', self.update_preview)
        self.custom_mask_entry.connect('changed', self.update_preview)
        self.delay_spin.connect('value-changed', self.update_preview)

        # Initialize settings manager
        self.settings_manager = SettingsManager()
        
        # Track background operations
        self.operation_in_progress = False
        self.operation_thread = None

        # Define untranslated CPU mask data (mask value, is_custom flag)
        # This ensures comparisons work regardless of translation
        self.cpu_mask_data = [
            ("0x00FF00FF", False),  # Default
            ("0xFF00FF00", False),  # Cores (8-15 and 24-31)
            ("0xFFFFFFFF", False),  # Cores (0-31)
            ("0x00000001", False),  # Core 0 only
            ("0x0000000F", False),  # Cores 0-3
            ("0x000000FF", False),  # Cores 0-7
            ("0x0000FF00", False),  # Cores 8-15
            ("0x00FF0000", False),  # Cores 16-23
            ("0xFF000000", False),  # Cores 24-31
            (None, True),           # Custom - no fixed mask value
        ]

        # Setup CPU mask dropdown model
        self.setup_mask_dropdown()

        # Setup settings menu
        self.settings_menu_button.set_popover(self.create_settings_popover())

        # Setup actions
        self.setup_actions()

    def setup_actions(self):
        # Enable service action
        action_enable_service = Gio.SimpleAction.new("enable_service", None)
        action_enable_service.connect("activate", self.on_enable_service_action)
        self.add_action(action_enable_service)

        # Disable service action
        action_disable_service = Gio.SimpleAction.new("disable_service", None)
        action_disable_service.connect("activate", self.on_disable_service_action)
        self.add_action(action_disable_service)

        # Open settings folder action
        action_open_settings = Gio.SimpleAction.new("open_settings_folder", None)
        action_open_settings.connect("activate", self.on_open_settings_folder_action)
        self.add_action(action_open_settings)

        # About action
        action_about = Gio.SimpleAction.new("about", None)
        action_about.connect("activate", self.on_about_action)
        self.add_action(action_about)

    def on_enable_service_action(self, action, param):
        self.on_enable_service_clicked(None)

    def on_disable_service_action(self, action, param):
        self.on_disable_service_clicked(None)

    def on_open_settings_folder_action(self, action, param):
        config_dir = self.settings_manager.config_dir
        if not config_dir.exists():
            config_dir.mkdir(parents=True, exist_ok=True)
        
        try:
            subprocess.run(['xdg-open', str(config_dir)], check=False)
        except Exception as e:
            self.status_label.set_markup(_("<span color='red'>Failed to open settings folder: {}</span>").format(str(e)))

    def on_about_action(self, action, param):
        about = Adw.AboutWindow(
            transient_for=self,
            application_name=_("CPU Affinity Manager"),
            application_icon="preferences-system-performance",
            developer_name="p82590037723122",
            version="1.0",
            website="",
            issue_url="https://github.com/p82590037723122/cpu-affinity-manager/issues",
            comments=_("A simple tool to manage CPU affinity for processes on Linux.")
        )
        about.present()

    def setup_mask_dropdown(self):
        # Create translated display strings for the dropdown
        # These correspond to the cpu_mask_data entries
        self.cpu_mask_options = [
            _("0x00FF00FF - Default (Cores 0-7 and 16-23)"),
            _("0xFF00FF00 - Cores (8-15 and 24-31)"),
            _("0xFFFFFFFF - Cores (0-31)"),
            _("0x00000001 - Core 0 only"),
            _("0x0000000F - Cores 0-3"),
            _("0x000000FF - Cores 0-7"),
            _("0x0000FF00 - Cores 8-15"),
            _("0x00FF0000 - Cores 16-23"),
            _("0xFF000000 - Cores 24-31"),
            _("Custom - Enter your own mask")
        ]
        
        # Create string list model and set it to the dropdown
        model = Gtk.StringList.new(self.cpu_mask_options)
        self.mask_dropdown.set_model(model)
        
        # Set default option (index 0 is the default)
        self.mask_dropdown.set_selected(0)

    def create_settings_popover(self):
        popover = Gtk.Popover()
        box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=6)
        box.set_margin_start(12)
        box.set_margin_end(12)
        box.set_margin_top(12)
        box.set_margin_bottom(12)
        popover.set_child(box)

        # Add a label
        label = Gtk.Label(label=_("Saved Settings"))
        label.set_halign(Gtk.Align.START)
        box.append(label)

        # Add a separator
        separator = Gtk.Separator(orientation=Gtk.Orientation.HORIZONTAL)
        box.append(separator)

        # Create a list box for saved settings
        list_box = Gtk.ListBox()
        list_box.set_selection_mode(Gtk.SelectionMode.NONE)
        list_box.add_css_class('navigation-sidebar')
        box.append(list_box)

        # Add saved processes to the list
        saved_processes = self.settings_manager.get_all_processes()
        if not saved_processes:
            no_settings_label = Gtk.Label(label=_("No saved settings yet."))
            no_settings_label.set_halign(Gtk.Align.CENTER)
            no_settings_label.set_margin_top(6)
            no_settings_label.set_margin_bottom(6)
            box.append(no_settings_label)
        else:
            for process_name in saved_processes:
                row = Gtk.ListBoxRow()
                row_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=12)
                row_box.set_margin_top(6) # Add some spacing for rows
                row_box.set_margin_bottom(6)
                row.set_child(row_box)

                # Process name label
                name_label = Gtk.Label(label=process_name)
                name_label.set_halign(Gtk.Align.START)
                name_label.set_hexpand(True)
                row_box.append(name_label)

                # Load button
                load_button = Gtk.Button.new_from_icon_name("document-open-symbolic")
                load_button.set_tooltip_text(_("Load settings for {}").format(process_name))
                load_button.connect("clicked", lambda btn, p=process_name: self.load_settings(p, popover))
                row_box.append(load_button)

                # Delete button
                delete_button = Gtk.Button.new_from_icon_name("user-trash-symbolic")
                delete_button.set_tooltip_text(_("Delete settings for {}").format(process_name))
                delete_button.connect("clicked", lambda btn, p=process_name: self.delete_settings(p, popover))
                row_box.append(delete_button)

                list_box.append(row)
        return popover

    def load_settings(self, process_name, popover):
        settings = self.settings_manager.get_process_settings(process_name)
        if settings:
            self.process_entry.set_text(process_name)
            self.set_cpu_mask(settings.get('cpu_mask', DEFAULT_CPU_MASK))
            self.delay_spin.set_value(settings.get('initial_delay', 20))
            self.update_preview()
            self.status_label.set_markup(_("<span color='green'>Loaded settings for '{}'</span>").format(process_name))
            # Force close the popover by calling popdown on the passed popover object
            # In GTK4, popover.popdown() works if it's a Gtk.Popover
            popover.popdown()
        else:
            self.status_label.set_markup(_("<span color='red'>Could not load settings for '{}'</span>").format(process_name))

    def delete_settings(self, process_name, popover):
        if self.settings_manager.delete_process_settings(process_name):
            self.status_label.set_markup(_("<span color='green'>Deleted settings for '{}'</span>").format(process_name))
            # Rebuild and show the popover to reflect changes
            new_popover_content = self.create_settings_popover()
            self.settings_menu_button.set_popover(new_popover_content)
            popover.popdown() # Close old popover

        else:
            self.status_label.set_markup(_("<span color='red'>Failed to delete settings for '{}'</span>").format(process_name))

    def on_save_clicked(self, button):
        process_name = self.process_entry.get_text().strip()
        if not process_name:
            self.status_label.set_markup(_("<span color='red'>Please enter a process name</span>"))
            return

        cpu_mask = self.get_current_cpu_mask() or DEFAULT_CPU_MASK
        if not validate_cpu_mask(cpu_mask):
            self.status_label.set_markup(_("<span color='red'>Invalid CPU mask format. Must be in format 0x followed by hexadecimal digits (e.g., 0x00FF00FF)</span>"))
            return

        settings = {
            'cpu_mask': cpu_mask,
            'initial_delay': self.delay_spin.get_value_as_int()
        }

        if self.settings_manager.save_process_settings(process_name, settings):
            self.status_label.set_markup(_("<span color='green'>Saved settings for '{}'</span>").format(process_name))
            # Update the settings menu
            new_popover_content = self.create_settings_popover()
            self.settings_menu_button.set_popover(new_popover_content)
        else:
            self.status_label.set_markup(_("<span color='red'>Failed to save settings for '{}'</span>").format(process_name))

    def update_preview(self, *args):
        process_name = self.process_entry.get_text().strip()
        if not process_name:
            self.preview_label.set_markup(_("<span style='italic'>Enter a process name to see what will be changed</span>"))
            return

        cpu_mask = self.get_current_cpu_mask() or DEFAULT_CPU_MASK
        initial_delay = self.delay_spin.get_value_as_int()

        # Get matching processes
        pids = get_pids_by_name(process_name)
        if not pids:
            self.preview_label.set_markup(_("<span color='orange'>No processes found matching '{}'</span>").format(process_name))
            return

        # Build preview text
        preview_text = _("<b>Will apply the following changes:</b>\n\n")
        preview_text += _("• CPU Mask: {}\n").format(cpu_mask)
        preview_text += _("• Initial Delay: {} seconds\n\n").format(initial_delay)
        preview_text += _("<b>Found {} matching process(es):</b>\n").format(len(pids))
        for pid in pids:
            preview_text += _("• PID: {}\n").format(pid)

        self.preview_label.set_markup(preview_text)

    def on_search_clicked(self, button):
        process_name = self.process_entry.get_text().strip()
        if not process_name:
            self.status_label.set_markup(_("<span color='red'>Please enter a process name to search</span>"))
            return

        pids = get_pids_by_name(process_name)
        if not pids:
            self.status_label.set_markup(_("<span color='orange'>No processes found matching '{}'</span>").format(process_name))
        else:
            self.status_label.set_markup(_("<span color='green'>Found {} matching process(es)</span>").format(len(pids)))
        self.update_preview()

    def on_info_clicked(self, button):
        dialog = Gtk.MessageDialog(
            transient_for=self,
            modal=True,
            message_type=Gtk.MessageType.INFO,
            buttons=Gtk.ButtonsType.OK,
            text=_("CPU Mask Help"),
            secondary_use_markup=True,
            secondary_text=_("The CPU mask determines which CPU cores a process can run on.\n\n"
                "You can select from common presets in the dropdown, including:\n"
                "• Default\n"
                "• Individual cores or core groups\n"
                "• Or choose 'Custom' to enter your own mask.\n\n"
                "Format: 0x followed by hexadecimal number\n"
                "Example: 0x00FF00FF means:\n"
                "• Cores 0-7 and 16-23 are allowed\n"
                "• Other cores are not allowed")
        )
        dialog.connect("response", lambda d, r: d.destroy())
        dialog.present()

    def on_apply_clicked(self, button):
        process_name = self.process_entry.get_text().strip()
        if not process_name:
            self.status_label.set_markup(_("<span color='red'>Please enter a process name</span>"))
            return

        cpu_mask = self.get_current_cpu_mask()
        if not cpu_mask:
            cpu_mask = DEFAULT_CPU_MASK
        elif not validate_cpu_mask(cpu_mask):
            self.status_label.set_markup(_("<span color='red'>Invalid CPU mask format. Must be in format 0x followed by hexadecimal digits (e.g., 0x00FF00FF)</span>"))
            return

        initial_delay = self.delay_spin.get_value_as_int()

        # Disable the button while processing
        self.apply_button.set_sensitive(False)
        self.status_label.set_markup(_("<span>Processing...</span>"))
        self.operation_in_progress = True

        # Run the CPU affinity operation in a background thread to avoid blocking the UI
        self.operation_thread = threading.Thread(
            target=self._apply_affinity_threaded,
            args=(process_name, cpu_mask, initial_delay),
            daemon=True
        )
        self.operation_thread.start()

    def _apply_affinity_threaded(self, process_name, cpu_mask, initial_delay):
        """Run CPU affinity operation in background thread."""
        try:
            success, succeeded, attempted = apply_cpu_affinity(
                process_name, 
                cpu_mask=cpu_mask,
                initial_delay=initial_delay
            )
            
            # Update UI on the main thread
            GLib.idle_add(self._update_apply_status, success, succeeded, attempted)
        except Exception as e:
            # Handle any unexpected errors
            print(f"Error in background affinity operation: {e}")
            GLib.idle_add(self._update_apply_status, False, 0, 0, str(e))

    def _update_apply_status(self, success, succeeded, attempted, error_msg=None):
        """Update UI after CPU affinity operation completes (runs on main thread)."""
        if error_msg:
            status = _("<span color='red'>Error: {}</span>").format(error_msg)
        elif success:
            status = _("<span color='green'>Successfully set affinity for {} out of {} threads</span>").format(succeeded, attempted)
        else:
            status = _("<span color='red'>Failed to set affinity. Check the terminal for details.</span>")

        self.status_label.set_markup(status)
        self.apply_button.set_sensitive(True)

        # Reset operation tracking
        self.operation_in_progress = False
        self.operation_thread = None

        return False  # Don't call this idle callback again

    def on_mask_selection_changed(self, dropdown, pspec):
        """Handle CPU mask dropdown selection changes."""
        selected_index = dropdown.get_selected()
        if selected_index < len(self.cpu_mask_data):
            mask_value, is_custom = self.cpu_mask_data[selected_index]
            if is_custom:
                # Show custom entry, hide dropdown
                self.mask_dropdown.set_visible(False)
                self.custom_mask_entry.set_visible(True)
                self.custom_mask_entry.grab_focus()
            else:
                # Hide custom entry, show dropdown
                self.mask_dropdown.set_visible(True)
                self.custom_mask_entry.set_visible(False)

        self.update_preview()

    def get_current_cpu_mask(self):
        """Get the currently selected CPU mask value."""
        selected_index = self.mask_dropdown.get_selected()
        if selected_index < len(self.cpu_mask_data):
            mask_value, is_custom = self.cpu_mask_data[selected_index]
            if is_custom:
                return self.custom_mask_entry.get_text().strip()
            else:
                return mask_value
        return DEFAULT_CPU_MASK

    def set_cpu_mask(self, mask_value):
        """Set the CPU mask to a specific value."""
        # First try to find it in the predefined mask data
        for i, (preset_mask, is_custom) in enumerate(self.cpu_mask_data):
            if not is_custom and preset_mask == mask_value:
                self.mask_dropdown.set_selected(i)
                self.mask_dropdown.set_visible(True)
                self.custom_mask_entry.set_visible(False)
                return

        # If not found, set to custom mode (last index)
        custom_index = len(self.cpu_mask_data) - 1
        self.mask_dropdown.set_selected(custom_index)
        self.mask_dropdown.set_visible(False)
        self.custom_mask_entry.set_visible(True)
        self.custom_mask_entry.set_text(mask_value)

    def on_close_request(self, window):
        """Handle window close request and clean up background operations."""
        if self.operation_in_progress:
            print("Warning: Application closed while CPU affinity operation was in progress.")
            print("The background thread will continue until completion since it's a daemon thread.")
            # Note: daemon threads are automatically terminated when the main program exits,
            # but any subprocess operations may continue briefly

        return False  # Allow the window to close

    def on_enable_service_clicked(self, button):
        """Enable systemd user service and timer."""
        try:
            # Get paths
            base_dir = Path(BASE_DIR)
            auto_apply_script = base_dir / 'auto_apply.py'
            
            if not auto_apply_script.exists():
                self.status_label.set_markup(_("<span color='red'>Error: auto_apply.py not found. Cannot enable service.</span>"))
                return

            # Determine systemd user directory
            systemd_dir = Path.home() / '.config' / 'systemd' / 'user'
            systemd_dir.mkdir(parents=True, exist_ok=True)

            # Create service file content
            service_content = f"""[Unit]
Description=Apply CPU affinity to saved processes
After=network.target

[Service]
Type=oneshot
ExecStart=/usr/bin/python3 {auto_apply_script}
WorkingDirectory={base_dir}
StandardOutput=null
StandardError=journal
"""
            # Create timer file content
            timer_content = """[Unit]
Description=Timer to apply CPU affinity to saved processes every minute

[Timer]
OnBootSec=1m
OnUnitActiveSec=1m
Unit=cpu-affinity-manager.service

[Install]
WantedBy=timers.target
"""
            # Write files
            service_file = systemd_dir / 'cpu-affinity-manager.service'
            timer_file = systemd_dir / 'cpu-affinity-manager.timer'
            
            with open(service_file, 'w') as f:
                f.write(service_content)
                
            with open(timer_file, 'w') as f:
                f.write(timer_content)

            # Reload systemd and enable timer
            subprocess.run(['systemctl', '--user', 'daemon-reload'], check=True)
            subprocess.run(['systemctl', '--user', 'enable', '--now', 'cpu-affinity-manager.timer'], check=True)

            self.status_label.set_markup(_("<span color='green'>Auto-apply service enabled successfully!</span>"))

        except subprocess.CalledProcessError as e:
             self.status_label.set_markup(_("<span color='red'>Failed to enable service: Command failed with exit code {}</span>").format(e.returncode))
        except Exception as e:
            self.status_label.set_markup(_("<span color='red'>Failed to enable service: {}</span>").format(str(e)))

    def on_disable_service_clicked(self, button):
        """Disable systemd user service and timer."""
        try:
            # Disable and stop timer
            subprocess.run(['systemctl', '--user', 'disable', '--now', 'cpu-affinity-manager.timer'], check=False)
            
            # Remove files
            systemd_dir = Path.home() / '.config' / 'systemd' / 'user'
            service_file = systemd_dir / 'cpu-affinity-manager.service'
            timer_file = systemd_dir / 'cpu-affinity-manager.timer'
            
            if service_file.exists():
                service_file.unlink()
            if timer_file.exists():
                timer_file.unlink()
                
            # Reload systemd
            subprocess.run(['systemctl', '--user', 'daemon-reload'], check=True)

            self.status_label.set_markup(_("<span color='green'>Auto-apply service disabled successfully!</span>"))

        except subprocess.CalledProcessError as e:
             self.status_label.set_markup(_("<span color='red'>Failed to disable service: Command failed with exit code {}</span>").format(e.returncode))
        except Exception as e:
            self.status_label.set_markup(_("<span color='red'>Failed to disable service: {}</span>").format(str(e)))


class CPUAffinityManagerApp(Adw.Application):
    def __init__(self, **kwargs):
        super().__init__(application_id=APP_ID, flags=Gio.ApplicationFlags.HANDLES_OPEN)
        self.window = None

    def do_startup(self):
        # Set up the style manager for dark/light theme support FIRST
        style_manager = Adw.StyleManager.get_default()
        style_manager.set_color_scheme(Adw.ColorScheme.PREFER_LIGHT)

        Adw.Application.do_startup(self) # Chain up AFTER our style manager setup

    def do_activate(self):
        # This function is called when the application is activated (e.g., launched)
        if not self.window:
            self.window = CPUAffinityManagerWindow(application=self)
        self.window.present()

    def do_open(self, files, n_files, hint):
        # This is called when files are opened with the application
        # For this app, we don't do anything special with opened files,
        # just activate the main window.
        self.do_activate()
        return 0

    def do_shutdown(self):
        """Handle application shutdown and ensure cleanup."""
        # The window's close handler should take care of cleanup,
        # but this provides an additional safety net
        if self.window and hasattr(self.window, 'operation_in_progress') and self.window.operation_in_progress:
            print("Application shutting down while CPU affinity operation was in progress.")

        Adw.Application.do_shutdown(self)


def main():
    app = CPUAffinityManagerApp()
    return app.run(sys.argv)

if __name__ == '__main__':
    sys.exit(main())