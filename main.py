import gi
gi.require_version('Gtk', '4.0')
gi.require_version('Adw', '1')
from gi.repository import Gtk, Adw, Gio, GLib

import sys
import os
import shutil
from pathlib import Path
from utils import apply_cpu_affinity, DEFAULT_CPU_MASK, get_pids_by_name
from settings import SettingsManager

APP_ID = 'com.example.AffinitySetter'

class AffinitySetterWindow(Adw.ApplicationWindow):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)

        # Initialize settings manager
        self.settings_manager = SettingsManager()

        self.set_title("CPU Affinity Manager")
        self.set_default_size(800, 600)

        # Main layout
        self.main_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=12)
        self.set_content(self.main_box)

        # Header bar
        header = Adw.HeaderBar()
        
        # Add install button to header
        install_button = Gtk.Button()
        install_button.set_icon_name("system-software-install-symbolic")
        install_button.set_tooltip_text("Install to Applications Menu")
        install_button.connect("clicked", self.on_install_clicked)
        header.pack_start(install_button)
        
        self.main_box.append(header)

        # Create a scrolled window for the content
        scrolled = Gtk.ScrolledWindow()
        scrolled.set_policy(Gtk.PolicyType.AUTOMATIC, Gtk.PolicyType.AUTOMATIC)
        scrolled.set_vexpand(True)
        self.main_box.append(scrolled)

        # Content box with padding
        content_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=12)
        content_box.set_margin_start(24)
        content_box.set_margin_end(24)
        content_box.set_margin_top(24)
        content_box.set_margin_bottom(24)
        scrolled.set_child(content_box)

        # Process name entry with search button and saved settings menu
        process_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=12)
        process_label = Gtk.Label(label="Process Name:")
        process_label.set_halign(Gtk.Align.START)
        process_label.set_size_request(120, -1)  # Fixed width for label
        self.process_entry = Gtk.Entry()
        self.process_entry.set_placeholder_text("Enter process name")
        self.process_entry.set_hexpand(True)
        
        # Add search button
        search_button = Gtk.Button()
        search_button.set_icon_name("system-search-symbolic")
        search_button.set_tooltip_text("Search for process")
        search_button.connect("clicked", self.on_search_clicked)

        # Add saved settings menu button
        self.settings_menu_button = Gtk.MenuButton()
        self.settings_menu_button.set_icon_name("document-save-symbolic")
        self.settings_menu_button.set_tooltip_text("Saved Settings")
        self.settings_menu_button.set_popover(self.create_settings_popover())
        
        process_box.append(process_label)
        process_box.append(self.process_entry)
        process_box.append(search_button)
        process_box.append(self.settings_menu_button)
        content_box.append(process_box)

        # CPU Mask entry with info button
        mask_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=12)
        mask_label = Gtk.Label(label="CPU Mask:")
        mask_label.set_halign(Gtk.Align.START)
        mask_label.set_size_request(120, -1)  # Fixed width for label
        self.mask_entry = Gtk.Entry()
        self.mask_entry.set_text(DEFAULT_CPU_MASK)
        self.mask_entry.set_placeholder_text("Enter CPU mask (e.g., 0x00FF00FF)")
        self.mask_entry.set_hexpand(True)
        
        # Add info button
        info_button = Gtk.Button()
        info_button.set_icon_name("help-about-symbolic")
        info_button.set_tooltip_text("Show CPU mask help")
        info_button.connect("clicked", self.on_info_clicked)
        
        mask_box.append(mask_label)
        mask_box.append(self.mask_entry)
        mask_box.append(info_button)
        content_box.append(mask_box)

        # Initial delay spinbutton
        delay_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=12)
        delay_label = Gtk.Label(label="Initial Delay (seconds):")
        delay_label.set_halign(Gtk.Align.START)
        delay_label.set_size_request(120, -1)  # Fixed width for label
        self.delay_spin = Gtk.SpinButton.new_with_range(0, 300, 1)
        self.delay_spin.set_value(20)  # Default 20 seconds delay
        self.delay_spin.set_hexpand(True)
        delay_box.append(delay_label)
        delay_box.append(self.delay_spin)
        content_box.append(delay_box)

        # Use sudo checkbox
        sudo_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=12)
        sudo_box.set_margin_start(120)  # Align with other inputs
        self.sudo_check = Gtk.CheckButton()
        self.sudo_check.set_label("Use sudo (required for some processes)")
        sudo_box.append(self.sudo_check)
        content_box.append(sudo_box)

        # Add a separator
        separator = Gtk.Separator(orientation=Gtk.Orientation.HORIZONTAL)
        separator.set_margin_top(12)
        separator.set_margin_bottom(12)
        content_box.append(separator)

        # Preview section
        preview_frame = Gtk.Frame()
        preview_frame.set_label("Preview")
        preview_frame.set_margin_top(12)
        preview_frame.set_vexpand(True)  # Allow preview to expand
        content_box.append(preview_frame)

        preview_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=12)
        preview_box.set_margin_start(12)
        preview_box.set_margin_end(12)
        preview_box.set_margin_top(12)
        preview_box.set_margin_bottom(12)
        preview_frame.set_child(preview_box)

        self.preview_label = Gtk.Label()
        self.preview_label.set_wrap(True)
        self.preview_label.set_halign(Gtk.Align.START)
        self.preview_label.set_valign(Gtk.Align.START)
        self.preview_label.set_markup("<span style='italic'>Enter a process name to see what will be changed</span>")
        preview_box.append(self.preview_label)

        # Status label
        self.status_label = Gtk.Label()
        self.status_label.set_wrap(True)
        self.status_label.set_markup("<span weight='bold'>Ready to set CPU affinity</span>")
        content_box.append(self.status_label)

        # Button box for Apply and Save buttons
        button_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=12)
        button_box.set_halign(Gtk.Align.END)

        # Save settings button
        self.save_button = Gtk.Button(label="Save Settings")
        self.save_button.connect("clicked", self.on_save_clicked)
        button_box.append(self.save_button)

        # Apply button
        self.apply_button = Gtk.Button(label="Apply CPU Affinity")
        self.apply_button.connect("clicked", self.on_apply_clicked)
        self.apply_button.add_css_class('suggested-action')
        button_box.append(self.apply_button)
        content_box.append(button_box)

        # Connect entry signals for live preview
        self.process_entry.connect("changed", self.update_preview)
        self.mask_entry.connect("changed", self.update_preview)
        self.delay_spin.connect("value-changed", self.update_preview)
        self.sudo_check.connect("toggled", self.update_preview)

    def create_settings_popover(self):
        popover = Gtk.Popover()
        box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=6)
        box.set_margin_start(12)
        box.set_margin_end(12)
        box.set_margin_top(12)
        box.set_margin_bottom(12)
        popover.set_child(box)

        # Add a label
        label = Gtk.Label(label="Saved Settings")
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
            no_settings_label = Gtk.Label(label="No saved settings yet.")
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
                load_button.set_tooltip_text(f"Load settings for {process_name}")
                load_button.connect("clicked", lambda btn, p=process_name: self.load_settings(p, popover))
                row_box.append(load_button)

                # Delete button
                delete_button = Gtk.Button.new_from_icon_name("user-trash-symbolic")
                delete_button.set_tooltip_text(f"Delete settings for {process_name}")
                delete_button.connect("clicked", lambda btn, p=process_name: self.delete_settings(p, popover))
                row_box.append(delete_button)

                list_box.append(row)
        return popover

    def load_settings(self, process_name, popover):
        settings = self.settings_manager.get_process_settings(process_name)
        if settings:
            self.process_entry.set_text(process_name)
            self.mask_entry.set_text(settings.get('cpu_mask', DEFAULT_CPU_MASK))
            self.delay_spin.set_value(settings.get('initial_delay', 20))
            self.sudo_check.set_active(settings.get('use_sudo', False))
            self.update_preview()
            self.status_label.set_markup(f"<span color='green'>Loaded settings for '{process_name}'</span>")
            popover.popdown() # Close popover on load
        else:
            self.status_label.set_markup(f"<span color='red'>Could not load settings for '{process_name}'</span>")

    def delete_settings(self, process_name, popover):
        if self.settings_manager.delete_process_settings(process_name):
            self.status_label.set_markup(f"<span color='green'>Deleted settings for '{process_name}'</span>")
            # Rebuild and show the popover to reflect changes
            new_popover_content = self.create_settings_popover()
            self.settings_menu_button.set_popover(new_popover_content)
            # If the popover was open, this might be tricky. For simplicity, assume it needs to be reopened.
            # For a better UX, we might need to update the existing popover's list_box directly.
            # However, recreating it is safer for now.
            popover.popdown() # Close old popover
            self.settings_menu_button.popup() # Open new one (or user reopens)

        else:
            self.status_label.set_markup(f"<span color='red'>Failed to delete settings for '{process_name}'</span>")

    def on_save_clicked(self, button):
        process_name = self.process_entry.get_text().strip()
        if not process_name:
            self.status_label.set_markup("<span color='red'>Please enter a process name</span>")
            return

        settings = {
            'cpu_mask': self.mask_entry.get_text().strip() or DEFAULT_CPU_MASK,
            'initial_delay': self.delay_spin.get_value_as_int(),
            'use_sudo': self.sudo_check.get_active()
        }

        if self.settings_manager.save_process_settings(process_name, settings):
            self.status_label.set_markup(f"<span color='green'>Saved settings for '{process_name}'</span>")
            # Update the settings menu
            new_popover_content = self.create_settings_popover()
            self.settings_menu_button.set_popover(new_popover_content)
        else:
            self.status_label.set_markup(f"<span color='red'>Failed to save settings for '{process_name}'</span>")

    def update_preview(self, *args):
        process_name = self.process_entry.get_text().strip()
        if not process_name:
            self.preview_label.set_markup("<span style='italic'>Enter a process name to see what will be changed</span>")
            return

        cpu_mask = self.mask_entry.get_text().strip() or DEFAULT_CPU_MASK
        initial_delay = self.delay_spin.get_value_as_int()
        use_sudo = self.sudo_check.get_active()

        # Get matching processes
        pids = get_pids_by_name(process_name)
        if not pids:
            self.preview_label.set_markup(f"<span color='orange'>No processes found matching '{process_name}'</span>")
            return

        # Build preview text
        preview_text = f"<b>Will apply the following changes:</b>\n\n"
        preview_text += f"• CPU Mask: {cpu_mask}\n"
        preview_text += f"• Initial Delay: {initial_delay} seconds\n"
        preview_text += f"• Using sudo: {'Yes' if use_sudo else 'No'}\n\n"
        preview_text += f"<b>Found {len(pids)} matching process(es):</b>\n"
        for pid in pids:
            preview_text += f"• PID: {pid}\n"

        self.preview_label.set_markup(preview_text)

    def on_search_clicked(self, button):
        process_name = self.process_entry.get_text().strip()
        if not process_name:
            self.status_label.set_markup("<span color='red'>Please enter a process name to search</span>")
            return

        pids = get_pids_by_name(process_name)
        if not pids:
            self.status_label.set_markup(f"<span color='orange'>No processes found matching '{process_name}'</span>")
        else:
            self.status_label.set_markup(f"<span color='green'>Found {len(pids)} matching process(es)</span>")
        self.update_preview()

    def on_info_clicked(self, button):
        dialog = Gtk.MessageDialog(
            transient_for=self,
            modal=True,
            message_type=Gtk.MessageType.INFO,
            buttons=Gtk.ButtonsType.OK,
            text="CPU Mask Help"
        )
        dialog.set_markup(
            "The CPU mask determines which CPU cores a process can run on.\n\n"
            "Format: 0x followed by hexadecimal number\n"
            "Example: 0x00FF00FF means:\n"
            "• Cores 0-7 and 16-23 are allowed\n"
            "• Other cores are not allowed\n\n"
            "Common masks:\n"
            "• 0x00000001: Core 0 only\n"
            "• 0x0000000F: Cores 0-3\n"
            "• 0x000000FF: Cores 0-7\n"
            "• 0x00FF00FF: Cores 0-7 and 16-23"
        )
        dialog.connect("response", lambda d, r: d.destroy())
        dialog.present()

    def on_apply_clicked(self, button):
        process_name = self.process_entry.get_text().strip()
        if not process_name:
            self.status_label.set_markup("<span color='red'>Please enter a process name</span>")
            return

        cpu_mask = self.mask_entry.get_text().strip()
        if not cpu_mask:
            cpu_mask = DEFAULT_CPU_MASK

        initial_delay = self.delay_spin.get_value_as_int()
        use_sudo = self.sudo_check.get_active()

        # Disable the button while processing
        self.apply_button.set_sensitive(False)
        self.status_label.set_markup("<span>Processing...</span>")

        # Use GLib.idle_add to run the CPU affinity operation in the background
        GLib.idle_add(self.apply_affinity, process_name, cpu_mask, use_sudo, initial_delay)

    def apply_affinity(self, process_name, cpu_mask, use_sudo, initial_delay):
        success, succeeded, attempted = apply_cpu_affinity(
            process_name, 
            cpu_mask=cpu_mask,
            use_sudo=use_sudo,
            initial_delay=initial_delay
        )

        if success:
            status = f"<span color='green'>Successfully set affinity for {succeeded} out of {attempted} threads</span>"
        else:
            status = f"<span color='red'>Failed to set affinity. Check the terminal for details.</span>"

        self.status_label.set_markup(status)
        self.apply_button.set_sensitive(True)
        return False  # Required for GLib.idle_add

    def on_install_clicked(self, button):
        try:
            # Get the path to the desktop entry file
            desktop_file = Path(__file__).parent / 'com.example.AffinitySetter.desktop'
            if not desktop_file.exists():
                self.status_label.set_markup("<span color='red'>Desktop entry file not found. Make sure 'com.example.AffinitySetter.desktop' is in the same directory as main.py.</span>")
                return

            # Get the user's local applications directory
            local_apps_dir = Path.home() / '.local' / 'share' / 'applications'
            local_apps_dir.mkdir(parents=True, exist_ok=True)

            # Copy the desktop entry file
            target_file = local_apps_dir / 'com.example.AffinitySetter.desktop'
            shutil.copy2(desktop_file, target_file)
            target_file.chmod(0o755) # Ensure it's executable/readable

            # Update desktop database
            # Using Gio for this is more robust if `update-desktop-database` isn't in PATH
            # or for sandboxed environments, though os.system is common.
            # For now, stick to os.system as it's simpler for this context.
            cmd_result = os.system(f'update-desktop-database "{local_apps_dir}"')
            
            if cmd_result == 0:
                self.status_label.set_markup("<span color='green'>Application installed! You may need to log out and back in for it to appear in menus.</span>")
            else:
                self.status_label.set_markup(f"<span color='orange'>Application installed, but failed to update desktop database (exit code: {cmd_result}). It might not appear in menus immediately.</span>")

        except Exception as e:
            self.status_label.set_markup(f"<span color='red'>Failed to install application: {str(e)}</span>")


class AffinitySetterApp(Adw.Application):
    def __init__(self, **kwargs):
        super().__init__(application_id=APP_ID, flags=Gio.ApplicationFlags.HANDLES_OPEN)
        self.window = None

    def do_startup(self):
        # Set up the style manager for dark/light theme support FIRST
        style_manager = Adw.StyleManager.get_default()
        # Using PREFER_LIGHT explicitly for now, was DEFAULT in the last attempt
        style_manager.set_color_scheme(Adw.ColorScheme.PREFER_LIGHT) 

        Adw.Application.do_startup(self) # Chain up AFTER our style manager setup

    def do_activate(self):
        # This function is called when the application is activated (e.g., launched)
        if not self.window:
            self.window = AffinitySetterWindow(application=self)
        self.window.present()

    def do_open(self, files, n_files, hint):
        # This is called when files are opened with the application
        # For this app, we don't do anything special with opened files,
        # just activate the main window.
        self.do_activate()
        return 0


def main():
    app = AffinitySetterApp()
    return app.run(sys.argv)

if __name__ == '__main__':
    sys.exit(main()) 