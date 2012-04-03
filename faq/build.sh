#!/bin/bash

set -e
cd "$(dirname "$0")"

target="../html/faq.htm"

cat faq.head >> "$target"
echo "<!-- This file is generated from faq/build.sh, do not edit directly -->" >> "$target"
markdown_py < faq.md >> "$target"
cat faq.foot >> "$target"

echo ":: Created $target"
