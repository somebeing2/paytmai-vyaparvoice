@echo off
echo =========================================================
echo   PaytmAI VyaparVoice - Merchant Growth Autopilot (MVP)
echo   Team SemiTechnical ^| Builder: Kevin Joseph
echo =========================================================
pip install -r requirements.txt
echo.
echo Running QA Verification Battery...
python tests\qa_battery.py
echo.
echo Starting FastAPI Server at http://127.0.0.1:8000 ...
start http://127.0.0.1:8000
python -m uvicorn app.main:app --host 127.0.0.1 --port 8000 --reload
