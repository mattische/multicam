#!/bin/bash
# Tunn omslag: kör samma avinstallation som 'multicam uninstall'.
exec "$(cd "$(dirname "$(readlink -f "$0")")" && pwd)/bin/multicam" uninstall "$@"
