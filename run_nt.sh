#!/bin/bash
# Cambiar al directorio donde está main.py
cd "$(dirname "$0")"
python main.py
# Clean up pycache directories after the app closes
find "$(dirname "$0")/src" -type d -name "__pycache__" -exec rm -rf {} +
