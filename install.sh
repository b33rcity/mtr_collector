#!/usr/bin/env bash

[[ $(python3 -V) =~ Python\ 3\.7.* ]] \
    || python3.7 -V > /dev/null \
    || {
         echo "Required Python version not found! You must install Python3.7." >&2
         exit 1
       }
echo "Found python37 interpreter on the system."

which pipenv > /dev/null \
    || {
        echo "You must have 'pipenv' installed."
        echo "'pip install pipenv' oughtta do the trick." >&2
        exit 1
       }
echo "pipenv is installed."

echo "Checking for user systemd directory..."
[ -d ~/.config/systemd/user ] \
    || {
        read -p "~/.config/systemd/user/ not found. Make now? [y|N]" make_it
        if [[ $make_it =~ y|Y ]]; then mkdir -p ~/.config/systemd/user
        else echo "Not making directory; quitting."; exit 0; fi
       }

echo "Prerequisites satisfied; setting up the venv..."
pipenv install
interpreter=$(pipenv --py)

cat > ~/.config/systemd/user/mtr_collector.service << EOF
[Unit]
Description=Service for collecting multiple MTRs into one data stream
After=multi-user.target

[Service]
ExecStart=${interpreter} $(pwd)/mtr_collector.py

[Install]
Alias=mtrcollector
EOF
[ $? -eq 0 ] || exit 1

systemctl --user daemon-reload || exit 1
systemctl --user enable mtr_collector
echo "Finished! Use 'systemctl --user start mtr_collector' to start the server."
