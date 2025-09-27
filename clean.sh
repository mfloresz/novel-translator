#!/bin/bash

# Limpiar cachés de Python
find "$(dirname "$0")/" -type d -name "__pycache__" -exec rm -rf {} +
