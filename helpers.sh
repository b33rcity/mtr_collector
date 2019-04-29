#!/usr/bin/env bash

##############################################################################
# Just some commands that were helpful for testing out the main python script.
##############################################################################

function send_msg {
    for arg in "$@"; do
        echo -e "$arg" | openssl s_client -connect 127.0.0.1:22123
    done
}

# Won't work with ssl!
function dump2tcp {
    echo "$1" > /dev/tcp/127.0.0.1/22123
}
# If zsh:
# zmodload zsh/net/tcp
# ztcp 127.0.0.1 22123
# echo "something" >&$RESULT
# ztcp -c $RESULT
