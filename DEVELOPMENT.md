# 개발자 가이드

## 프로젝트 구조

```
announcerAI/
├── src/
│   ├── __init__.py
│   ├── main.py                    # 메인 오케스트레이터
│   ├── config_loader.py           # 설정 로더
│   ├── discord_bot/               # Discord 봇 모듈
│   │   ├── __init__.py
│   │   ├── bot.py                 # 메인 봇 클래스
│   │   ├── stream_capture.py     # 스트림 캡처
│   │   └── audio_player.py       # 오디오 재생
│   ├── vision_analyzer/           # AI 비전 분석 모듈
│   │   ├── __init__.py
│   │   ├── analyzer.py            # 화면 분석
│   │   ├── event_detector.py     # 이벤트 감지
│   │   └── commentary_generator.py # 해설 생성
│   └── tts_integration/           # TTS 통합 모듈
│       ├── __init__.py
│       ├── tts_client.py          # TTS 클라이언트
│       └── tts_manager.py         # TTS 매니저
├── config/
│   └── config.yaml                # 설정 파일
├── tests/                         # 테스트
├── models/                        # TTS 모델
├── logs/                          # 로그 파일
├── ttsclient-master/              # TTS 클라이언트
├── requirements.txt
├── run.py                         # 실행 스크립트
├── setup.py
└── README.md
```

## 아키텍처

### 데이터 플로우

```
Discord 화면 공유
    ↓
[StreamCapture] - 프레임 추출 (1-2 fps)
    ↓
[frame_queue] ← asyncio.Queue
    ↓
[VisionAnalyzer] - OpenAI/Claude Vision API로 화면 분석
    ↓
[GameState] - 게임 상태 데이터
    ↓
[EventDetector] - 중요 이벤트 감지
    ↓
[GameEvent] - 이벤트 데이터
    ↓
[CommentaryGenerator] - 해설 텍스트 생성
    ↓
[text_queue] ← asyncio.Queue
    ↓
[TTSManager] - TTS 생성 요청
    ↓
[TTSClient] - ttsclient 서버와 통신
    ↓
[audio_queue] ← asyncio.Queue
    ↓
[AudioPlayer] - Discord 음성 채널에서 재생
```

### 비동기 처리

모든 주요 컴포넌트는 asyncio를 사용하여 비동기로 동작합니다:
- Discord Bot: discord.py의 비동기 이벤트 루프
- Vision API: aiohttp를 사용한 비동기 HTTP 요청
- TTS: 비동기 큐 기반 처리
- 프레임 처리: 백그라운드 워커 태스크

## 주요 모듈 설명

### 1. Discord Bot (`src/discord_bot/`)

**bot.py**
- `AnnouncerBot`: Discord.py Bot 클래스
- 명령어: `!join`, `!leave`, `!status`
- 백그라운드 태스크:
  - `frame_processor_task`: 화면 공유 모니터링
  - `audio_player_task`: 오디오 재생

**stream_capture.py**
- `StreamCapture`: 화면 공유 스트림에서 프레임 추출
- `FrameBuffer`: 슬라이딩 윈도우 프레임 버퍼

**audio_player.py**
- `AudioPlayer`: FFmpeg 기반 오디오 재생
- `AudioQueueManager`: 자동 큐 모니터링 및 재생

### 2. Vision Analyzer (`src/vision_analyzer/`)

**analyzer.py**
- `VisionAnalyzer`: Vision API 통합
- `GameState`: 게임 상태 데이터 클래스
- OpenAI GPT-4 Vision 또는 Claude Vision 지원

**event_detector.py**
- `EventDetector`: 프레임 간 비교로 이벤트 감지
- `EventType`: 이벤트 타입 Enum
- `GameEvent`: 이벤트 데이터 클래스

**commentary_generator.py**
- `CommentaryGenerator`: 해설 텍스트 생성
- 다양한 해설 패턴 및 변형
- 상황별 추가 해설

### 3. TTS Integration (`src/tts_integration/`)

**tts_client.py**
- `TTSClient`: ttsclient REST API 클라이언트
- aiohttp를 사용한 비동기 HTTP 통신

**tts_manager.py**
- `TTSManager`: TTS 요청 큐 관리
- 자동 재시도 로직
- 우선순위 기반 처리

## 개발 가이드

### 새로운 이벤트 타입 추가

1. `src/vision_analyzer/event_detector.py`에서 `EventType` Enum에 추가
2. `EventDetector.detect_events()` 메서드에 감지 로직 추가
3. `src/vision_analyzer/commentary_generator.py`에 해설 패턴 추가

```python
# event_detector.py
class EventType(str, Enum):
    NEW_EVENT = "new_event"

# commentary_generator.py
EventType.NEW_EVENT: [
    "새로운 이벤트가 발생했습니다!",
    "중요한 순간입니다!",
]
```

### 새로운 Vision API Provider 추가

`src/vision_analyzer/analyzer.py`의 `VisionAnalyzer` 클래스:

```python
async def analyze_frame(self, image):
    if self.api_provider == "openai":
        return await self._analyze_with_openai(image)
    elif self.api_provider == "claude":
        return await self._analyze_with_claude(image)
    elif self.api_provider == "new_provider":
        return await self._analyze_with_new_provider(image)
```

### 테스트 작성

```python
# tests/test_event_detector.py
import pytest
from src.vision_analyzer import EventDetector, GameState

@pytest.mark.asyncio
async def test_kill_detection():
    detector = EventDetector()

    current_state = {
        "blue_team_kills": 5,
        "red_team_kills": 3,
    }

    previous_state = {
        "blue_team_kills": 4,
        "red_team_kills": 3,
    }

    events = await detector.detect_events(current_state, previous_state)

    assert len(events) == 1
    assert events[0].event_type == EventType.KILL
```

## 디버깅

### 로그 레벨 설정

`config/config.yaml`:
```yaml
system:
  log_level: "DEBUG"  # DEBUG, INFO, WARNING, ERROR
```

### 특정 모듈만 디버그

```python
# main.py에 추가
logging.getLogger("src.vision_analyzer").setLevel(logging.DEBUG)
```

### Mock 모드로 테스트

API 키 없이 테스트:
```yaml
vision:
  api_key: ""  # Mock 모드로 실행
```

## 성능 프로파일링

```python
import cProfile
import pstats

# main.py
if __name__ == "__main__":
    profiler = cProfile.Profile()
    profiler.enable()

    asyncio.run(main())

    profiler.disable()
    stats = pstats.Stats(profiler)
    stats.sort_stats('cumtime')
    stats.print_stats(20)
```

## 배포

### Docker (예정)

```dockerfile
FROM python:3.9-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install -r requirements.txt

COPY . .

CMD ["python", "run.py"]
```

### 프로덕션 체크리스트

- [ ] 모든 API 키가 환경 변수로 설정되었는지 확인
- [ ] 로그 레벨을 INFO로 설정
- [ ] 에러 알림 시스템 구성 (Sentry 등)
- [ ] 리소스 모니터링 (CPU, 메모리, 네트워크)
- [ ] API 비용 모니터링
- [ ] 백업 및 복구 계획

## 기여 가이드

1. Fork 및 브랜치 생성
```bash
git checkout -b feature/new-feature
```

2. 코드 작성 및 테스트
```bash
pytest tests/
```

3. 커밋
```bash
git commit -m "Add new feature"
```

4. Pull Request 생성

### 코딩 스타일

- PEP 8 준수
- 타입 힌팅 사용
- Docstring 작성 (Google 스타일)
- 에러 핸들링 필수

## 라이선스

MIT License
