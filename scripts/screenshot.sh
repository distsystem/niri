#!/usr/bin/env bash

# niri-compatible screenshot script using wayfreeze + grim + slurp + satty

TEMP_IMG=$(mktemp --suffix=.png)

wayfreeze --hide-cursor --after-freeze-cmd "
    GEOMETRY=\$(slurp)
    if [ -n \"\$GEOMETRY\" ]; then
        grim -g \"\$GEOMETRY\" '$TEMP_IMG'
    fi
    pkill -P $$ wayfreeze
"

[ -s "$TEMP_IMG" ] &&
    cat "$TEMP_IMG" |
    tee >(wl-copy --type image/png) |
    satty --filename - \
        --output-filename "$HOME/Pictures/Screenshots/satty-$(date '+%Y%m%d-%H%M%S').png" \
        --actions-on-enter=save-to-file \
        --actions-on-right-click=exit \
        --early-exit

rm -f "$TEMP_IMG"
