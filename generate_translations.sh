#!/bin/bash
set -e

# Create locale directory
mkdir -p locale

echo "Extracting strings..."

# Extract strings from Python files
# We use --from-code=UTF-8 to handle special characters in source
xgettext --language=Python --keyword=_ --from-code=UTF-8 --output=locale/cpu_affinity_manager.pot main.py utils.py

# Extract strings from UI file
# The --join-existing flag appends/merges with the existing pot file
if xgettext --help | grep -q "Glade"; then
    xgettext --language=Glade --join-existing --keyword=_ --from-code=UTF-8 --output=locale/cpu_affinity_manager.pot affinity_window.ui
else
    echo "Warning: Your xgettext does not appear to support Glade/UI files directly."
    echo "You may need to use intltool or a newer version of gettext."
fi

echo "Template created at locale/cpu_affinity_manager.pot"
echo ""
echo "To initialize a new language (e.g., Spanish):"
echo "  msginit --locale=es --input=locale/cpu_affinity_manager.pot --output=locale/es.po"
echo ""
echo "To compile translations:"
echo "  mkdir -p locale/es/LC_MESSAGES"
echo "  msgfmt locale/es.po -o locale/es/LC_MESSAGES/io.github.p82590037723122.CPU_Affinity_Manager.mo"

