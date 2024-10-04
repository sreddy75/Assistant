#!/bin/bash

# Your actual values
AZURE_DEVOPS_ORG="kr8it"
AZURE_DEVOPS_PROJECT="AI Assistant"
AZURE_DEVOPS_PAT="fywkd4euoqqe6lpu5njwpo5efqv2d45zeaeumvw43guezbw6iwta"

# URL encode function
urlencode() {
    local string="${1}"
    local strlen=${#string}
    local encoded=""
    local pos c o

    for (( pos=0 ; pos<strlen ; pos++ )); do
        c=${string:$pos:1}
        case "$c" in
            [-_.~a-zA-Z0-9] ) o="${c}" ;;
            * )               printf -v o '%%%02x' "'$c"
        esac
        encoded+="${o}"
    done
    echo "${encoded}"
}

# Encode organization and project names
ENCODED_ORG=$(urlencode "${AZURE_DEVOPS_ORG}")
ENCODED_PROJECT=$(urlencode "${AZURE_DEVOPS_PROJECT}")

# API URL
API_URL="https://dev.azure.com/${ENCODED_ORG}/${ENCODED_PROJECT}/_apis/wit/fields?api-version=6.0"

echo "Querying API URL: ${API_URL}"

# Make the API request and process the output
RESPONSE=$(curl -s -u ":${AZURE_DEVOPS_PAT}" "${API_URL}")

echo "API Response:"
echo "${RESPONSE}" | head -n 20

echo "Processed Output:"
echo "${RESPONSE}" | 
    grep -E '"name"|"referenceName"' | 
    sed -E 's/.*"name": "([^"]+)".*/Name: \1/g; s/.*"referenceName": "([^"]+)".*/Reference: \1/g' |
    sed 'N;s/\n/ - /'

echo "Look for your 'DeploymentFrequency' field in the output above."