#!/bin/bash

set -o nounset
set -o errexit
set -o pipefail

rm -rf $TMPDIR/gdep
GOOS=linux GOARCH=amd64 gdep go build -o blog_app_linux

docker build --tag kjksf/blog:latest --tag blog:latest .
docker run --rm -t -v ~/data/blog:/data -p 5020:80 kjksf/blog:latest
