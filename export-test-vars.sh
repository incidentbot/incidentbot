#!/bin/bash

# Use to export vars until we setup testing in a KIND cluster setup
secrets=(GOOGLE_ACCOUNT_EMAIL
GOOGLE_SERVICE_ACCOUNT_SECRET
SLACK_APP_TOKEN
SLACK_BOT_TOKEN
SLACK_USER_TOKEN)


function set_vars {
    for secret in ${secrets[@]}
        do 
        export $secret=$(kubectl --context test get secret incident-bot -o jsonpath="{.data.$secret}" -n incident-bot | base64 -D)
    done
}

set_vars 
