# Windows 설치 가이드

LoL Announcer AI를 Windows에서 설치하고 실행하는 방법입니다.

## 1. 시스템 요구사항

- Windows 10 또는 Windows 11
- Python 3.9 이상
- 인터넷 연결

## 2. Python 설치

### 2.1. Python 다운로드

https://www.python.org/downloads/ 에서 Python 3.9 이상을 다운로드합니다.

**중요**: 설치 시 "Add Python to PATH" 옵션을 반드시 체크하세요!

### 2.2. 설치 확인

명령 프롬프트(CMD) 또는 PowerShell을 열고:

```cmd
python --version
```

`Python 3.9.x` 이상이 표시되면 정상입니다.

## 3. FFmpeg 설치

Discord 음성 재생을 위해 FFmpeg가 필요합니다.

### 방법 1: Chocolatey 사용 (권장)

PowerShell을 **관리자 권한**으로 실행 후:

```powershell
# Chocolatey 설치 (없는 경우)
Set-ExecutionPolicy Bypass -Scope Process -Force; [System.Net.ServicePointManager]::SecurityProtocol = [System.Net.ServicePointManager]::SecurityProtocol -bor 3072; iex ((New-Object System.Net.WebClient).DownloadString('https://community.chocolatey.org/install.ps1'))

# FFmpeg 설치
choco install ffmpeg
```

### 방법 2: 수동 설치

1. https://www.gyan.dev/ffmpeg/builds/ 접속
2. `ffmpeg-release-essentials.zip` 다운로드
3. 압축을 `C:\ffmpeg`에 풀기
4. 환경 변수 PATH에 `C:\ffmpeg\bin` 추가:
   - Windows 검색에서 "환경 변수" 입력
   - "시스템 환경 변수 편집" 클릭
   - "환경 변수" 버튼 클릭
   - "시스템 변수"의 "Path" 선택 후 "편집"
   - "새로 만들기" 클릭 후 `C:\ffmpeg\bin` 입력
   - 모두 확인

### 설치 확인

명령 프롬프트를 **새로 열고**:

```cmd
ffmpeg -version
```

버전 정보가 표시되면 정상입니다.

## 4. 프로젝트 설정

### 4.1. 의존성 설치

명령 프롬프트에서:

```cmd
# 프로젝트 폴더로 이동
cd C:\Users\YourName\announcerAI

# Python 패키지 설치
pip install -r requirements.txt
```

설치에 시간이 걸릴 수 있습니다 (5-10분).

### 4.2. 설정 파일 생성

```cmd
# config 폴더 생성
mkdir config

# 예제 파일 복사
copy config.example.yaml config\config.yaml
```

메모장이나 VSCode로 `config\config.yaml` 파일을 열고 다음을 설정:

```yaml
discord:
  token: "여기에_Discord_Bot_토큰_입력"
  prefix: "!"

vision:
  api_provider: "openai"  # 또는 "claude"
  api_key: "여기에_OpenAI_또는_Claude_API_키_입력"
  frame_interval: 2
  model: "gpt-4o"

tts:
  enabled: true
  tts_server_url: "http://localhost:50021"
  voice_character_slot: 0
  language: "ko"
  speed: 1.0

system:
  log_level: "INFO"
  max_queue_size: 10
  frame_buffer_size: 30
```

## 5. TTS 서버 설정

### 5.1. Poetry 설치

명령 프롬프트에서:

```cmd
pip install poetry
```

### 5.2. TTS 서버 실행

**방법 1: 배치 파일 사용 (추천)**

명령 프롬프트에서:
```cmd
cd ttsclient-master
start_tts_server.bat
```

**방법 2: 수동 실행**

명령 프롬프트에서:

```cmd
# ttsclient-master 폴더로 이동 (중요!)
cd ttsclient-master

# Git submodule 초기화
git submodule update --init --recursive

# Poetry로 의존성 설치 (처음 한 번만)
poetry install

# TTS 서버 실행
poetry run python -m ttsclient.main cui
```

⚠️ **중요**: 반드시 `ttsclient-master` 폴더 **안에서** 실행해야 합니다!

### Poetry 오류 해결

**오류**: `Poetry could not find a pyproject.toml file`

**원인**: 현재 위치가 `ttsclient-master` 폴더가 아닙니다.

**해결**:
```cmd
# 현재 위치 확인
cd

# 프로젝트 루트로 이동
cd C:\Users\YourName\announcerAI

# ttsclient-master로 이동
cd ttsclient-master

# 다시 실행
poetry run python -m ttsclient.main cui
```

브라우저에서 http://localhost:50021 이 자동으로 열립니다.

### 5.3. TTS 모델 설정

1. TTS 웹 UI에서 "모델 선택" → "편집" 클릭
2. GPT-SoVITS 모델 등록
3. "참조 화자" 등록 및 참조 음성 설정

**모델이 없다면**: https://github.com/RVC-Boss/GPT-SoVITS 에서 다운로드하거나 학습 필요

## 6. Discord Bot 설정

### 6.1. Bot 생성

1. https://discord.com/developers/applications 접속
2. "New Application" 클릭
3. Bot 이름 입력 (예: "LoL Announcer AI")

### 6.2. Bot 설정

1. 왼쪽 메뉴 "Bot" 클릭
2. "Reset Token" 클릭하여 토큰 복사
3. `config\config.yaml`의 `discord.token`에 붙여넣기

### 6.3. Bot 권한 설정

"Bot" 페이지에서:
- ✅ PRESENCE INTENT
- ✅ SERVER MEMBERS INTENT
- ✅ MESSAGE CONTENT INTENT

### 6.4. Bot 초대

1. 왼쪽 메뉴 "OAuth2" → "URL Generator" 클릭
2. SCOPES: ✅ bot
3. BOT PERMISSIONS:
   - ✅ Read Messages/View Channels
   - ✅ Send Messages
   - ✅ Connect
   - ✅ Speak
4. 생성된 URL로 봇을 Discord 서버에 초대

## 7. 실행

### 방법 1: 자동 시작 (추천)

프로젝트 루트 폴더에서:

```cmd
start_all.bat
```

이 배치 파일이 자동으로:
1. TTS 서버를 새 창에서 시작
2. 5초 대기
3. Announcer AI 봇을 새 창에서 시작

### 방법 2: 수동 시작

#### 7.1. TTS 서버 먼저 실행

**명령 프롬프트 창 #1**:
```cmd
cd ttsclient-master
start_tts_server.bat
```

또는 수동으로:
```cmd
cd ttsclient-master
poetry run python -m ttsclient.main cui
```

#### 7.2. Announcer AI 실행

**명령 프롬프트 창 #2** (새 창):
```cmd
# 프로젝트 루트 폴더에서
run.bat
```

또는 직접 실행:
```cmd
python src\main.py
```

## 8. 사용 방법

### 8.1. Discord에서

1. 롤 게임 시작
2. Discord 음성 채널 접속
3. 화면 공유 시작 (롤 게임 화면)

### 8.2. 봇 명령어

Discord 채팅에서:
```
!join    # 봇을 현재 음성 채널에 초대
!leave   # 봇을 음성 채널에서 퇴장
!status  # 봇 상태 확인
```

## 9. 문제 해결

### Python을 찾을 수 없음

- Python 설치 시 "Add Python to PATH" 체크했는지 확인
- 명령 프롬프트를 다시 열어야 PATH가 적용됨

### FFmpeg를 찾을 수 없음

- 환경 변수 PATH 설정 확인
- 명령 프롬프트를 다시 열어서 시도

### 모듈을 찾을 수 없음 (ModuleNotFoundError)

```cmd
# 의존성 다시 설치
pip install -r requirements.txt --upgrade
```

### Discord Bot 연결 실패

- `config\config.yaml`의 토큰이 정확한지 확인
- Bot이 서버에 초대되었는지 확인
- 인터넷 연결 확인

### TTS 서버 시작 실패

- Poetry가 설치되어 있는지 확인: `poetry --version`
- ttsclient-master 폴더에서 실행하는지 확인

### "Access Denied" 또는 권한 오류

- 명령 프롬프트를 **관리자 권한**으로 실행
- 안티바이러스가 차단하는지 확인

### 로그 확인

문제 발생 시 로그 파일 확인:
```cmd
type logs\announcer_ai.log
```

## 10. 성능 최적화

### GPU 사용 (NVIDIA)

TTS 속도 향상을 위해:

```cmd
cd ttsclient-master
poetry add onnxruntime-gpu==1.20.1
poetry remove torch
poetry add torch==2.4.1 torchaudio==2.4.1 --source torch_cuda12
```

CUDA 11.8 또는 12.x가 설치되어 있어야 합니다.

## 11. 자동 시작 (선택)

### 작업 스케줄러 사용

1. Windows 검색에서 "작업 스케줄러" 실행
2. "기본 작업 만들기"
3. 트리거: 시스템 시작 시
4. 동작: `C:\Users\YourName\announcerAI\run.bat` 실행

## 도움말

더 자세한 정보는 [SETUP_GUIDE.md](SETUP_GUIDE.md)를 참조하세요.

문제가 해결되지 않으면 GitHub Issues에 보고해주세요:
https://github.com/REFIRSER2/announcerAI/issues
