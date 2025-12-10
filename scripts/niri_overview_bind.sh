#!/bin/bash

# Use: niri_overview_bind.sh 'command with overview open' 'command with overview closed'
IS_IN_OVERVIEW=$(niri msg -j overview-state | jq .is_open)
if $IS_IN_OVERVIEW; then
  niri msg action $1
else
  niri msg action $2
fi
