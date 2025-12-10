#!/usr/bin/env bash

# niri-compatible screenshot script using wayfreeze + grim + slurp + satty

TEMP=$(mktemp)
wayfreeze --hide-cursor --after-freeze-cmd "slurp > $TEMP; pkill -P $$ wayfreeze"

GEOMETRY=$(cat "$TEMP")
rm "$TEMP"

[ -n "$GEOMETRY" ] && grim -g "$GEOMETRY" - |
  tee >(wl-copy --type image/png) |
  satty --filename - \
    --output-filename "$HOME/Pictures/Screenshots/satty-$(date '+%Y%m%d-%H%M%S').png" \
    --actions-on-enter=save-to-file \
    --actions-on-right-click=exit \
    --early-exit
