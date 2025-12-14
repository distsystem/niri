#!/usr/bin/env bash
set -euo pipefail

# Monitor all processes and send notifications when CPU usage exceeds threshold

# Configurable parameters
CPU_THRESHOLD="${CPU_THRESHOLD:-100}"          # CPU usage threshold (%)
CHECK_INTERVAL="${CHECK_INTERVAL:-5}"          # Check interval (seconds)
NOTIFY_COOLDOWN="${NOTIFY_COOLDOWN:-30}"       # Min interval between notifications (seconds)

# State variables
declare -A last_notify_times
declare -A prev_high_procs  # Processes that were high in previous check

cleanup() {
  echo "Stopping CPU monitor..."
  exit 0
}
trap cleanup SIGTERM SIGINT

# Get processes exceeding CPU threshold
get_high_cpu_processes() {
  ps -eo comm,pcpu --sort=-pcpu | \
    awk -v threshold="$CPU_THRESHOLD" \
      'NR>1 && $NF+0 > threshold {printf "%s %.0f\n", $1, $NF}'
}

# Send notification with per-process rate limiting
notify_high_cpu() {
  local proc=$1
  local cpu=$2
  local current_time
  current_time=$(date +%s)

  local last_time=${last_notify_times[$proc]:-0}
  if (( current_time - last_time >= NOTIFY_COOLDOWN )); then
    notify-send -u critical \
      "High CPU: $proc" \
      "CPU usage: ${cpu}% (threshold: ${CPU_THRESHOLD}%)"
    last_notify_times[$proc]=$current_time
  fi
}

monitor_cpu() {
  echo "Starting CPU monitor (threshold: ${CPU_THRESHOLD}%, interval: ${CHECK_INTERVAL}s)"

  while true; do
    declare -A curr_high_procs

    while read -r proc cpu; do
      [[ -z "$proc" ]] && continue
      curr_high_procs[$proc]=$cpu

      # Only notify if process was also high in previous check
      if [[ -v prev_high_procs[$proc] ]]; then
        notify_high_cpu "$proc" "$cpu"
      fi
    done < <(get_high_cpu_processes)

    # Update previous state for next iteration
    prev_high_procs=()
    for proc in "${!curr_high_procs[@]}"; do
      prev_high_procs[$proc]=${curr_high_procs[$proc]}
    done

    sleep "$CHECK_INTERVAL"
  done
}

case "${1:-monitor}" in
  monitor)
    monitor_cpu
    ;;
  test)
    echo "Processes exceeding ${CPU_THRESHOLD}% CPU:"
    get_high_cpu_processes | while read -r proc cpu; do
      echo "  $proc: ${cpu}%"
    done
    ;;
  *)
    echo "Usage: $0 [monitor|test]"
    exit 2
    ;;
esac
