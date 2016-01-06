#!/bin/bash
set -e
VERSION=$(cat VERSION.txt)

echo "##teamcity[buildNumber '$VERSION+$BUILD_NUMBER']"
echo "##teamcity[setParameter name='releaseVersion' value='$VERSION']"

if [ $# != 4 ]; then
    echo "USAGE release.sh <zip file name> <token> <upload url> <redirect url>"
    exit 1
fi

RELEASE_FILE=$1
TOKEN=$2
UPLOAD_URL=$3
REDIRECT_URL=$4

REDIRECT="latest-sublime-plugin-2"

echo "Uploading '$RELEASE_FILE' to '$UPLOAD_URL'"
UPLOAD_CMD="curl -H 'X-API-Token: $TOKEN' -F \"file=@$RELEASE_FILE\" $UPLOAD_URL"
echo $UPLOAD_CMD
OUTPUT=$(eval $UPLOAD_CMD)
echo
echo $OUTPUT

URL=$(echo $OUTPUT | sed 's/.*"url":"\(.*\)".*/\1/')
echo
echo "Setting '$REDIRECT' to point to '$URL'"

PAYLOAD='{"uri":"'$URL'"}'
echo
echo "Payload is '$PAYLOAD'"

REDIRECT_CMD="curl -H 'Content-Type: application/json' -H 'X-API-Token: $TOKEN' -X PUT -d '$PAYLOAD' $REDIRECT_URL/$REDIRECT"
echo $REDIRECT_CMD
eval $REDIRECT_CMD
