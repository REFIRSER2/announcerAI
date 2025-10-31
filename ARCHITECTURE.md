# LoL Announcer AI - 프로젝트 아키텍처

## 개요
Discord에서 롤(League of Legends) 화면 공유를 실시간으로 분석하고 TTS로 해설하는 AI 시스템

## 시스템 구성

### 1. Discord Bot 모듈 (`src/discord_bot/`)
- **역할**: Discord 음성 채널 관리 및 스트림 처리
- **기능**:
  - 음성 채널 참가/퇴장 명령어 (`!join`, `!leave`)
  - 화면 공유 스트림 캡처 (프레임 추출)
  - TTS 음성 재생
  - WebSocket을 통한 프레임 전송
- **기술 스택**: discord.py, discord.py[voice], opencv-python
- **출력**: 화면 프레임 (이미지 스트림)

### 2. AI Vision Analyzer 모듈 (`src/vision_analyzer/`)
- **역할**: 게임 화면 실시간 분석 및 해설 생성
- **기능**:
  - 게임 상황 인식 (챔피언, KDA, 골드, 맵 상황 등)
  - OCR을 통한 게임 정보 추출
  - Vision API를 활용한 상황 분석
  - 아나운서 스타일 해설 텍스트 생성
  - 중요 이벤트 감지 (킬, 오브젝트, 팀파이트 등)
- **기술 스택**: OpenAI Vision API / Claude Vision, pytesseract, numpy
- **입력**: 게임 화면 프레임
- **출력**: 해설 텍스트

### 3. TTS Integration 모듈 (`src/tts_integration/`)
- **역할**: 해설 텍스트를 자연스러운 음성으로 변환
- **기능**:
  - ttsclient 라이브러리 통합
  - GPT-SoVITS를 활용한 TTS 생성
  - 음성 스트림 생성 및 버퍼 관리
  - 실시간 음성 생성 최적화
- **기술 스택**: ttsclient, GPT-SoVITS
- **입력**: 해설 텍스트
- **출력**: 음성 파일/스트림

### 4. Main Orchestrator (`src/main.py`)
- **역할**: 모든 모듈 통합 및 실시간 파이프라인 관리
- **기능**:
  - 모듈 간 통신 관리
  - 비동기 처리 및 큐 관리
  - 에러 핸들링 및 로깅
  - 설정 관리
- **기술 스택**: asyncio, multiprocessing

## 데이터 플로우

```
Discord 화면 공유
    ↓
[Discord Bot] - 프레임 캡처
    ↓
[Frame Queue]
    ↓
[AI Vision Analyzer] - 화면 분석 → 해설 텍스트 생성
    ↓
[Text Queue]
    ↓
[TTS Integration] - 음성 변환
    ↓
[Audio Queue]
    ↓
[Discord Bot] - 음성 재생
```

## 기술 스택 요약

### 필수 패키지
- `discord.py[voice]` - Discord 봇
- `opencv-python` - 프레임 처리
- `pillow` - 이미지 처리
- `numpy` - 수치 연산
- `openai` / `anthropic` - Vision API
- `pytesseract` - OCR
- `asyncio` - 비동기 처리
- ttsclient 라이브러리 (GPT-SoVITS)

### 시스템 요구사항
- Python 3.9+
- FFmpeg (음성 처리)
- CUDA 지원 GPU (TTS 성능 향상, 선택사항)

## 설정 파일 구조

```yaml
# config.yaml
discord:
  token: "YOUR_DISCORD_BOT_TOKEN"
  prefix: "!"

vision:
  api_provider: "openai"  # or "claude"
  api_key: "YOUR_API_KEY"
  frame_interval: 2  # 2초마다 분석

tts:
  model_path: "./models/sovits"
  voice_character: "announcer"
  language: "ko"

system:
  log_level: "INFO"
  max_queue_size: 10
```

## 개발 우선순위

1. Discord Bot 기본 기능 (채널 참가/퇴장, 프레임 캡처)
2. TTS Integration (ttsclient 통합)
3. AI Vision Analyzer (화면 분석 및 해설 생성)
4. Main Orchestrator (통합)
5. 최적화 및 안정화
