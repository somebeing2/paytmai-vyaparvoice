#!/usr/bin/env bash
set -e
echo "========================================================="
echo "  PaytmAI VyaparVoice — Merchant Growth Autopilot (MVP)"
echo "  Team SemiTechnical | Builder: Kevin Joseph"
echo "========================================================="
pip install -q -r requirements.txt
python3 tests/qa_battery.py
echo "Starting server on http://0.0.0.0:8000 ..."
exec python3 -m uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
