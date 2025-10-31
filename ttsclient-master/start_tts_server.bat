@echo off
REM TTS 서버 시작 스크립트 (Windows)

echo ====================================
echo    TTS 서버 시작
echo ====================================
echo.

REM 현재 디렉토리 확인
if not exist "pyproject.toml" (
    echo [오류] 이 스크립트는 ttsclient-master 폴더에서 실행해야 합니다.
    echo.
    echo 사용법:
    echo   1. 명령 프롬프트를 열고
    echo   2. cd C:\Users\YourName\announcerAI\ttsclient-master
    echo   3. start_tts_server.bat
    echo.
    pause
    exit /b 1
)

echo [1/3] Poetry 확인 중...
poetry --version >nul 2>&1
if errorlevel 1 (
    echo [경고] Poetry가 설치되어 있지 않습니다.
    echo.
    choice /C YN /M "지금 Poetry를 설치하시겠습니까?"
    if errorlevel 2 goto no_poetry
    if errorlevel 1 (
        echo.
        echo Poetry 설치 중...
        pip install poetry
        if errorlevel 1 (
            echo [오류] Poetry 설치 실패
            pause
            exit /b 1
        )
    )
)

echo [2/3] TTS 서버 의존성 확인 중...

REM Git submodule 초기화 (있는 경우)
if exist ".gitmodules" (
    echo Git submodule 초기화 중...
    git submodule update --init --recursive 2>nul
)

REM Poetry 의존성 설치
echo Poetry 의존성 설치 중... (시간이 걸릴 수 있습니다)
poetry install
if errorlevel 1 (
    echo [오류] 의존성 설치 실패
    pause
    exit /b 1
)

echo [3/3] TTS 서버 실행 중...
echo.
echo =======================================
echo TTS 서버가 시작됩니다.
echo 브라우저에서 http://localhost:50021 이 열립니다.
echo.
echo 종료하려면 Ctrl+C를 누르세요.
echo =======================================
echo.

poetry run python -m ttsclient.main cui

:no_poetry
echo.
echo Poetry가 필요합니다. 다음 명령어로 설치하세요:
echo   pip install poetry
echo.
pause
exit /b 1
