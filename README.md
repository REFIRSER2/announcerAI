# LoL Announcer AI

Discord에서 롤(League of Legends) 화면 공유를 실시간으로 분석하고 아나운서처럼 해설하는 AI 시스템

## 기능

- Discord 음성 채널에서 실시간 화면 공유 분석
- AI Vision을 통한 게임 상황 인식
- 자연스러운 한국어 TTS 해설
- 대회 아나운서 스타일의 해설

## 설치

### 1. 시스템 요구사항
- Python 3.9 이상
- FFmpeg
- (선택) CUDA 지원 GPU (TTS 성능 향상)

### 2. 의존성 설치

```bash
# Python 패키지 설치
pip install -r requirements.txt

# FFmpeg 설치 (Ubuntu/Debian)
sudo apt-get install ffmpeg

# FFmpeg 설치 (macOS)
brew install ffmpeg
```

### 3. TTS 서버 설정

**옵션 1: Hugging Face 배포 버전 (권장)**
```bash
# https://huggingface.co/wok000/ttsclient000/tree/main 에서 다운로드
# 압축 해제 후
start_http.bat  # Windows
./start_http.command  # Mac
```

**옵션 2: 소스 코드 버전 (고급)**
```bash
cd ttsclient-master
pip install poetry
poetry install
poetry run python -m ttsclient.main cui
```

자세한 내용은 [SETUP_GUIDE.md](SETUP_GUIDE.md)를 참조하세요.

### 4. 설정 파일 생성

```bash
cp config.example.yaml config/config.yaml
```

`config/config.yaml` 파일을 편집하여 다음을 설정:
- Discord Bot Token
- Vision API Key (OpenAI 또는 Claude)
- TTS 설정

## 사용법

### 1. 봇 실행

```bash
python src/main.py
```

### 2. Discord 명령어

- `!join` - 봇을 현재 음성 채널에 참가시킵니다
- `!leave` - 봇을 음성 채널에서 퇴장시킵니다
- `!status` - 봇의 현재 상태를 확인합니다

### 3. 게임 해설 시작

1. 롤 게임을 시작하고 Discord 화면 공유를 켭니다
2. `!join` 명령어로 봇을 채널에 초대합니다
3. 봇이 자동으로 화면을 분석하고 해설을 시작합니다

## 프로젝트 구조

```
announcerAI/
├── src/
│   ├── main.py              # 메인 오케스트레이터
│   ├── discord_bot/         # Discord 봇 모듈
│   ├── vision_analyzer/     # AI 비전 분석 모듈
│   └── tts_integration/     # TTS 통합 모듈
├── config/
│   └── config.yaml          # 설정 파일
├── models/                  # TTS 모델 (추가 필요)
├── tests/                   # 테스트
└── ttsclient-master/        # TTS 클라이언트
```

## 개발

상세한 아키텍처는 [ARCHITECTURE.md](ARCHITECTURE.md)를 참조하세요.

## 라이선스

MIT License