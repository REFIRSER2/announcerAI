@echo off
REM LoL Announcer AI 실행 스크립트 (Windows)

echo ====================================
echo    LoL Announcer AI 시작
echo ====================================
echo.

REM Python 설치 확인
python --version >nul 2>&1
if errorlevel 1 (
    echo [오류] Python이 설치되어 있지 않습니다.
    echo Python 3.9 이상을 설치해주세요: https://www.python.org/downloads/
    pause
    exit /b 1
)

REM 의존성 확인
echo [1/3] 의존성 확인 중...
python -c "import discord" >nul 2>&1
if errorlevel 1 (
    echo [경고] 일부 의존성이 설치되어 있지 않습니다.
    echo 다음 명령어를 먼저 실행하세요:
    echo   pip install -r requirements.txt
    echo.
    choice /C YN /M "지금 설치하시겠습니까?"
    if errorlevel 2 goto skip_install
    if errorlevel 1 (
        echo.
        echo 의존성 설치 중...
        pip install -r requirements.txt
        if errorlevel 1 (
            echo [오류] 의존성 설치 실패
            pause
            exit /b 1
        )
    )
)

:skip_install

REM 설정 파일 확인
echo [2/3] 설정 파일 확인 중...
if not exist "config\config.yaml" (
    echo [경고] config/config.yaml 파일이 없습니다.
    if exist "config.example.yaml" (
        echo config.example.yaml을 복사합니다...
        mkdir config 2>nul
        copy config.example.yaml config\config.yaml
        echo.
        echo [중요] config/config.yaml 파일을 편집하여 다음을 설정하세요:
        echo   - Discord Bot Token
        echo   - Vision API Key (OpenAI 또는 Claude)
        echo.
        pause
    ) else (
        echo [오류] config.example.yaml 파일을 찾을 수 없습니다.
        pause
        exit /b 1
    )
)

REM 애플리케이션 실행
echo [3/3] LoL Announcer AI 실행 중...
echo.
python src\main.py

if errorlevel 1 (
    echo.
    echo [오류] 애플리케이션 실행 중 오류가 발생했습니다.
    echo 로그 파일을 확인하세요: logs\announcer_ai.log
    pause
    exit /b 1
)

pause
