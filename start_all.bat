@echo off
REM LoL Announcer AI - 전체 시스템 시작 스크립트

echo ================================================
echo    LoL Announcer AI - 전체 시스템 시작
echo ================================================
echo.
echo 이 스크립트는 두 개의 창을 엽니다:
echo   1. TTS 서버 (ttsclient)
echo   2. Announcer AI 봇
echo.
echo 시작하려면 아무 키나 누르세요...
pause >nul

REM TTS 서버 시작 (새 창)
echo.
echo [1/2] TTS 서버 시작 중...
start "TTS Server" cmd /k "cd ttsclient-master && start_tts_server.bat"

REM 5초 대기 (TTS 서버가 시작될 시간)
echo TTS 서버가 시작될 때까지 5초 대기 중...
timeout /t 5 /nobreak >nul

REM Announcer AI 봇 시작 (새 창)
echo.
echo [2/2] Announcer AI 봇 시작 중...
start "Announcer AI Bot" cmd /k "run.bat"

echo.
echo ================================================
echo 두 개의 창이 열렸습니다:
echo   - TTS Server: http://localhost:50021
echo   - Announcer AI Bot
echo.
echo Discord에서 !join 명령어로 봇을 초대하세요.
echo ================================================
echo.
echo 이 창은 닫아도 됩니다.
pause
