# LoL Announcer AI 설치 및 설정 가이드

## 1. 시스템 요구사항

### 필수
- Python 3.9 이상
- FFmpeg
- 인터넷 연결 (API 호출용)

### 권장
- CUDA 지원 GPU (TTS 성능 향상)
- 16GB 이상 RAM
- Ubuntu 20.04+ / Windows 10+ / macOS 11+

## 2. FFmpeg 설치

### Ubuntu/Debian
```bash
sudo apt-get update
sudo apt-get install ffmpeg
```

### macOS
```bash
brew install ffmpeg
```

### Windows
1. https://ffmpeg.org/download.html 에서 다운로드
2. PATH 환경 변수에 추가

## 3. Python 의존성 설치

```bash
# 가상환경 생성 (권장)
python3 -m venv venv

# 가상환경 활성화
# Linux/macOS:
source venv/bin/activate
# Windows:
venv\Scripts\activate

# 의존성 설치
pip install -r requirements.txt
```

## 4. Discord Bot 생성

### 4.1. Discord Developer Portal 접속
https://discord.com/developers/applications

### 4.2. 새 애플리케이션 생성
1. "New Application" 클릭
2. 애플리케이션 이름 입력 (예: "LoL Announcer AI")

### 4.3. Bot 생성
1. 왼쪽 메뉴에서 "Bot" 선택
2. "Add Bot" 클릭
3. "Reset Token" 클릭하여 토큰 복사 (나중에 사용)

### 4.4. Bot 권한 설정
"Privileged Gateway Intents" 섹션에서:
- ✅ PRESENCE INTENT
- ✅ SERVER MEMBERS INTENT
- ✅ MESSAGE CONTENT INTENT

### 4.5. OAuth2 설정
1. 왼쪽 메뉴에서 "OAuth2" → "URL Generator" 선택
2. SCOPES:
   - ✅ bot
3. BOT PERMISSIONS:
   - ✅ Read Messages/View Channels
   - ✅ Send Messages
   - ✅ Connect (음성)
   - ✅ Speak (음성)
   - ✅ Use Voice Activity
4. 생성된 URL로 봇을 서버에 초대

## 5. Vision API 설정

### 옵션 1: OpenAI (GPT-4 Vision)
1. https://platform.openai.com/api-keys 접속
2. API 키 생성
3. 비용 확인: https://openai.com/pricing

### 옵션 2: Anthropic (Claude Vision)
1. https://console.anthropic.com/ 접속
2. API 키 생성
3. 비용 확인: https://www.anthropic.com/pricing

## 6. TTS 서버 설정

프로젝트에 포함된 `ttsclient-master` 디렉토리를 사용합니다.

### 6.1. Poetry 설치
```bash
# Python 3.9 이상 필요
pip install poetry
```

### 6.2. 의존성 설치

```bash
cd ttsclient-master

# Git submodule 초기화
git submodule update --init --recursive

# Poetry로 의존성 설치
poetry install
```

**Ubuntu 사용자**: 추가 설정이 필요할 수 있습니다.
```bash
# pyopenjtalk 관련 이슈가 있는 경우
sed -i '/pyopenjtalk/d' pyproject.toml
poetry install

# 수동으로 pyopenjtalk 설치
wget "https://files.pythonhosted.org/packages/source/p/pyopenjtalk/pyopenjtalk-0.4.0.tar.gz"
tar xzf pyopenjtalk-0.4.0.tar.gz
sed -i -E 's/cmake_minimum_required\(VERSION[^\)]*\)/cmake_minimum_required(VERSION 3.5...3.31)/' pyopenjtalk-0.4.0/lib/open_jtalk/src/CMakeLists.txt
rm pyopenjtalk-0.4.0.tar.gz
tar czf pyopenjtalk-0.4.0.tar.gz pyopenjtalk-0.4.0/
poetry run pip install pyopenjtalk-0.4.0.tar.gz
```

### 6.3. TTS 서버 실행

```bash
# HTTP 서버 실행 (로컬)
poetry run python -m ttsclient.main cui

# HTTPS 서버 실행 (리모트 접속 허용)
poetry run python -m ttsclient.main cui --https true
```

### 6.4. TTS 서버 확인
브라우저에서 http://localhost:50021 접속하여 TTS UI가 표시되는지 확인

### 6.5. 음성 모델 설정

TTS 서버가 실행되면 웹 UI에서 모델을 설정해야 합니다:

1. **모델 등록**: "モデル選択" → "編集" 클릭
   - GPT-SoVITS 모델 파일 등록
   - 모델이 없다면 GPT-SoVITS 공식 리포지토리에서 학습하거나 사전 학습 모델 다운로드

2. **참조 화자 등록**: "参照話者選択" → "編集"
   - 참조 음성 파일 업로드 (WAV 권장)
   - 참조 텍스트 입력

3. **테스트**: 텍스트 입력 후 음성 생성 테스트

**중요**: 최소 1개 이상의 모델과 참조 음성이 등록되어 있어야 Announcer AI가 정상 작동합니다.

**모델이 없는 경우**:
- GPT-SoVITS 공식 리포지토리: https://github.com/RVC-Boss/GPT-SoVITS
- 사전 학습 모델이나 직접 음성 데이터로 학습 필요

## 7. 설정 파일 구성

### 7.1. 설정 파일 복사
```bash
cp config.example.yaml config/config.yaml
```

### 7.2. config/config.yaml 편집

```yaml
discord:
  token: "YOUR_DISCORD_BOT_TOKEN"  # Discord Bot 토큰
  prefix: "!"

vision:
  api_provider: "openai"  # "openai" 또는 "claude"
  api_key: "YOUR_API_KEY"  # Vision API 키
  frame_interval: 2  # 2초마다 화면 분석
  model: "gpt-4o"  # OpenAI: "gpt-4o", Claude: "claude-3-5-sonnet-20241022"

tts:
  enabled: true
  tts_server_url: "http://localhost:50021"
  voice_character_slot: 0  # TTS UI에서 설정한 캐릭터 슬롯
  language: "ko"
  speed: 1.0

system:
  log_level: "INFO"
  max_queue_size: 10
  frame_buffer_size: 30
```

### 7.3. 환경 변수 설정 (선택사항)

```bash
# .env 파일 생성
cp .env.example .env

# .env 파일 편집
nano .env
```

```env
DISCORD_BOT_TOKEN=your_discord_bot_token
VISION_API_PROVIDER=openai
VISION_API_KEY=your_api_key
```

## 8. 실행

### 8.1. TTS 서버 실행 (먼저)

```bash
cd ttsclient-master
poetry run python -m ttsclient.main cui
```

서버가 정상 실행되면 브라우저에서 http://localhost:50021 이 열립니다.

### 8.2. Announcer AI 실행
```bash
# 프로젝트 루트 디렉토리에서
python run.py

# 또는
python -m src.main
```

## 9. 사용법

### 9.1. Discord 준비
1. 롤 게임 시작
2. Discord 음성 채널 접속
3. 화면 공유 시작 (롤 게임 화면)

### 9.2. 봇 명령어
```
!join    # 봇을 현재 음성 채널에 초대
!leave   # 봇을 음성 채널에서 퇴장
!status  # 봇 상태 확인
```

### 9.3. 해설 시작
1. `!join` 명령어 실행
2. 봇이 자동으로 화면을 분석하고 해설 시작
3. 게임 종료 후 `!leave` 명령어 실행

## 10. 문제 해결

### FFmpeg 관련 오류
```bash
# FFmpeg 설치 확인
ffmpeg -version
```

### Discord Bot 연결 실패
- Discord Bot 토큰이 올바른지 확인
- Bot이 서버에 초대되었는지 확인
- Bot 권한 설정 확인

### TTS 서버 연결 실패
- TTS 서버가 실행 중인지 확인
- http://localhost:50021 접속 테스트
- 방화벽 설정 확인

### Vision API 오류
- API 키가 올바른지 확인
- API 크레딧이 남아있는지 확인
- 네트워크 연결 확인

### 로그 확인
```bash
# 로그 파일 확인
tail -f logs/announcer_ai.log
```

## 11. 성능 최적화

### TTS 응답 속도 개선
- CUDA 버전 사용 (NVIDIA GPU)
- TTS 서버를 강력한 PC에서 실행

### Vision API 비용 절감
- `frame_interval` 값을 증가 (2초 → 3초)
- 중요한 순간만 분석하도록 이벤트 감지 개선

### 메모리 사용량 감소
- `frame_buffer_size` 감소 (30 → 15)
- `max_queue_size` 감소 (10 → 5)

## 12. 개발자 모드 (테스트)

### Mock 모드 실행
API 키 없이 테스트하려면 config.yaml에서:

```yaml
vision:
  api_key: ""  # 비워두면 Mock 모드로 실행
```

이 경우 랜덤한 게임 상태가 생성되어 해설 시스템만 테스트할 수 있습니다.

## 13. 추가 리소스

- Discord.py 문서: https://discordpy.readthedocs.io/
- OpenAI API 문서: https://platform.openai.com/docs/
- Anthropic API 문서: https://docs.anthropic.com/
- GPT-SoVITS: https://github.com/RVC-Boss/GPT-SoVITS

## 지원

문제가 발생하면 로그 파일(`logs/announcer_ai.log`)을 확인하고 GitHub Issues에 보고해주세요.
