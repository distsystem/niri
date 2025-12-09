#!/usr/bin/env bash
# Auto-adjust window width: 100% for single window, default for multiple

check_and_resize() {
    local workspace_id=$1

    # Get all non-floating window IDs in this workspace
    local windows_info
    windows_info=$(niri msg -j windows | jq -r "[.[] | select(.workspace_id == $workspace_id and .is_floating == false)] | length, .[].id")

    local count
    count=$(echo "$windows_info" | head -1)
    local window_ids
    window_ids=$(echo "$windows_info" | tail -n +2)

    if [[ "$count" -eq 1 ]]; then
        # Single window: set to 100%
        echo "$window_ids" | while read -r wid; do
            [[ -n "$wid" ]] && niri msg action set-window-width --id "$wid" 100%
        done
    elif [[ "$count" -gt 1 ]]; then
        # Multiple windows: set all to default 50%
        echo "$window_ids" | while read -r wid; do
            [[ -n "$wid" ]] && niri msg action set-window-width --id "$wid" 50%
        done
    fi
}

niri msg -j event-stream | while read -r event; do
    # New window opened or existing window changed
    if [[ "$event" == *'"WindowOpenedOrChanged"'* ]]; then
        workspace_id=$(echo "$event" | jq -r '.WindowOpenedOrChanged.window.workspace_id')
        is_floating=$(echo "$event" | jq -r '.WindowOpenedOrChanged.window.is_floating')

        [[ "$is_floating" == "true" ]] && continue
        [[ -z "$workspace_id" || "$workspace_id" == "null" ]] && continue

        check_and_resize "$workspace_id"

    # Window closed - check if remaining window should expand
    elif [[ "$event" == *'"WindowClosed"'* ]]; then
        # Get focused window info to find workspace
        focused=$(niri msg -j focused-window 2>/dev/null)
        [[ -z "$focused" || "$focused" == "null" ]] && continue

        workspace_id=$(echo "$focused" | jq -r '.workspace_id')

        check_and_resize "$workspace_id"
    fi
done
