#! /bin/bash
# Autostart script template (adjust per host)

set +e

xrdb merge ~/.Xresources

# ime input
fcitx5 --replace -d 2>/dev/null &

# keep clipboard content
wl-clip-persist --clipboard regular --reconnect-tries 0 &

# clipboard content manager
wl-paste --type text --watch cliphist store &

gnome-keyring &

env -u XDG_SESSION_TYPE nutstore &
clash-verge &
# QT_SCALE_FACTOR=1 input-leap &
# swww-daemon &
QT_SCALE_FACTOR=1 copyq --start-server &
sleep 2
GDK_SCALE=2 feishu &

# Keep script alive - wait for any non-daemonizing child process
wait
