#!/bin/bash

# Toggle wvkbd virtual keyboard visibility
# If wvkbd is not running, start it and show
# If running, toggle visibility
#
# Usage:
#   Mod+K { spawn "bash" "~/.config/niri/scripts/wvkbd_toggle.sh"; }

if pgrep wvkbd > /dev/null; then
    pkill -RTMIN wvkbd
else
    wvkbd-mobintl &
fi
