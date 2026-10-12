#!/bin/bash
# Thin wrapper: runs the same uninstall as 'multicam uninstall'.
exec "$(cd "$(dirname "$(readlink -f "$0")")" && pwd)/bin/multicam" uninstall "$@"
