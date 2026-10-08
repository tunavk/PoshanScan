#!/bin/sh
# Start the PoshanScan WhatsApp server on port 8000 (loads .env if present).
cd "$(dirname "$0")"
[ -f .env ] && set -a && . ./.env && set +a
exec .venv/bin/uvicorn poshanscan.server:app --host 0.0.0.0 --port 8000
