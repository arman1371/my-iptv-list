#!/bin/bash

REGEX_QUERY='(?<=hlsManifestUrl":").*\.m3u8'

BBC_URL=$(curl -s 'https://www.youtube.com/@BBCNewsPersian/live' | grep -oP $REGEX_QUERY)
ESCAPED_BBC_URL=$(printf '%s\n' "$BBC_URL" | sed -e 's/[\/&]/\\&/g')
sed -i "7s/.*/$ESCAPED_BBC_URL/" ../ir.m3u