"""
LoL Announcer AI - Main Orchestrator

Discord에서 롤 화면 공유를 실시간으로 분석하고 TTS로 해설하는 AI 시스템의 메인 실행 파일
"""

import asyncio
import logging
import signal
import sys
from pathlib import Path
from typing import Optional

# 프로젝트 루트를 sys.path에 추가
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from src.config_loader import load_config, ConfigError
from src.discord_bot import AnnouncerBot
from src.vision_analyzer import VisionAnalyzer, EventDetector, CommentaryGenerator
from src.tts_integration import TTSManager

# 로깅 설정
log_dir = project_root / "logs"
log_dir.mkdir(exist_ok=True)
log_file = log_dir / "announcer_ai.log"

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler(log_file, encoding='utf-8')
    ]
)

logger = logging.getLogger(__name__)


class AnnouncerAI:
    """
    LoL Announcer AI 메인 오케스트레이터

    모든 모듈을 통합하고 데이터 플로우를 관리합니다:
    Discord Bot → Vision Analyzer → Commentary Generator → TTS → Discord Bot
    """

    def __init__(self, config_path: Optional[str] = None):
        """
        Args:
            config_path: 설정 파일 경로
        """
        self.config = load_config(config_path)
        self.running = False

        # 비동기 큐
        self.frame_queue: asyncio.Queue = None
        self.text_queue: asyncio.Queue = None
        self.audio_queue: asyncio.Queue = None

        # 모듈 인스턴스
        self.discord_bot: Optional[AnnouncerBot] = None
        self.vision_analyzer: Optional[VisionAnalyzer] = None
        self.event_detector: Optional[EventDetector] = None
        self.commentary_generator: Optional[CommentaryGenerator] = None
        self.tts_manager: Optional[TTSManager] = None

        # 백그라운드 태스크
        self.tasks = []

        logger.info("AnnouncerAI 초기화 완료")

    async def initialize(self):
        """모든 모듈 초기화"""
        logger.info("모듈 초기화 시작...")

        # 큐 생성
        frame_queue_size = self.config.get("system", {}).get("frame_buffer_size", 30)
        text_queue_size = self.config.get("system", {}).get("max_queue_size", 10)
        audio_queue_size = self.config.get("system", {}).get("max_queue_size", 10)

        self.frame_queue = asyncio.Queue(maxsize=frame_queue_size)
        self.text_queue = asyncio.Queue(maxsize=text_queue_size)
        self.audio_queue = asyncio.Queue(maxsize=audio_queue_size)

        logger.info(f"큐 생성 완료 (frame: {frame_queue_size}, text: {text_queue_size}, audio: {audio_queue_size})")

        # Vision Analyzer 초기화
        vision_config = self.config.get("vision", {})
        self.vision_analyzer = VisionAnalyzer(
            api_provider=vision_config.get("api_provider", "openai"),
            api_key=vision_config.get("api_key"),
            model=vision_config.get("model")
        )
        logger.info(f"Vision Analyzer 초기화 완료 (provider: {vision_config.get('api_provider')})")

        # Event Detector 초기화
        self.event_detector = EventDetector(
            cooldown_seconds=3.0,
            enable_multiprocessing=False
        )
        logger.info("Event Detector 초기화 완료")

        # Commentary Generator 초기화
        self.commentary_generator = CommentaryGenerator(
            enable_variations=True,
            enable_context=True
        )
        logger.info("Commentary Generator 초기화 완료")

        # TTS Manager 초기화
        tts_config = self.config.get("tts", {})
        if tts_config.get("enabled", True):
            self.tts_manager = TTSManager(
                tts_server_url=tts_config.get("tts_server_url", "http://localhost:50021"),
                audio_callback=self._audio_callback,
                default_language=tts_config.get("language", "ko"),
                default_speed=tts_config.get("speed", 1.0),
                voice_character_slot_index=tts_config.get("voice_character_slot", 0)
            )
            await self.tts_manager.start()
            logger.info(f"TTS Manager 초기화 완료 (server: {tts_config.get('tts_server_url')})")
        else:
            logger.warning("TTS가 비활성화되어 있습니다")

        # Discord Bot 초기화
        discord_config = self.config.get("discord", {})
        frame_rate = vision_config.get("frame_interval", 2.0)

        self.discord_bot = AnnouncerBot(
            command_prefix=discord_config.get("prefix", "!"),
            frame_queue=self.frame_queue,
            audio_queue=self.audio_queue,
            frame_rate=1.0 / frame_rate  # interval to fps
        )
        logger.info(f"Discord Bot 초기화 완료 (prefix: {discord_config.get('prefix')})")

        logger.info("모든 모듈 초기화 완료")

    async def _audio_callback(self, audio_data: bytes, request):
        """
        TTS Manager에서 생성된 오디오를 Discord Bot으로 전달

        Args:
            audio_data: 생성된 오디오 데이터 (WAV)
            request: TTS 요청 객체
        """
        try:
            await self.audio_queue.put(audio_data)
            logger.debug(f"오디오 큐에 추가: {len(audio_data)} bytes")
        except asyncio.QueueFull:
            logger.warning("오디오 큐가 가득 찼습니다. 오디오를 건너뜁니다.")
        except Exception as e:
            logger.error(f"오디오 콜백 에러: {e}", exc_info=True)

    async def frame_processor(self):
        """프레임 처리 워커: 프레임 → 분석 → 해설 생성 → TTS"""
        logger.info("프레임 처리 워커 시작")

        previous_state = None

        while self.running:
            try:
                # 프레임 큐에서 가져오기 (타임아웃 1초)
                try:
                    frame = await asyncio.wait_for(
                        self.frame_queue.get(),
                        timeout=1.0
                    )
                except asyncio.TimeoutError:
                    continue

                logger.debug("프레임 수신, 분석 시작...")

                # 1. 화면 분석
                game_state = await self.vision_analyzer.analyze_frame(frame)
                if not game_state:
                    logger.warning("게임 상태를 추출할 수 없습니다")
                    continue

                logger.info(
                    f"게임 상태 분석: "
                    f"시간={game_state.game_time}, "
                    f"블루={game_state.blue_team_kills}-{game_state.red_team_kills}=레드"
                )

                # 2. 이벤트 감지
                game_state_dict = game_state.to_dict() if hasattr(game_state, 'to_dict') else vars(game_state)
                events = await self.event_detector.detect_events(
                    game_state_dict,
                    previous_state
                )

                if events:
                    logger.info(f"{len(events)}개의 이벤트 감지됨")

                # 3. 해설 생성
                for event in events:
                    try:
                        commentary = await self.commentary_generator.generate_commentary(
                            event,
                            game_state_dict
                        )

                        if commentary and commentary.text:
                            logger.info(f"해설 생성: {commentary.text}")

                            # 4. TTS 요청
                            if self.tts_manager:
                                await self.tts_manager.add_request(
                                    text=commentary.text,
                                    priority=commentary.priority
                                )
                            else:
                                logger.warning("TTS Manager가 없습니다. 텍스트만 출력합니다.")
                                print(f"[해설] {commentary.text}")

                    except Exception as e:
                        logger.error(f"해설 생성/TTS 요청 실패: {e}", exc_info=True)

                # 이전 상태 저장
                previous_state = game_state_dict

            except Exception as e:
                logger.error(f"프레임 처리 에러: {e}", exc_info=True)
                await asyncio.sleep(1)

        logger.info("프레임 처리 워커 종료")

    async def start(self):
        """애플리케이션 시작"""
        logger.info("=" * 60)
        logger.info("LoL Announcer AI 시작")
        logger.info("=" * 60)

        try:
            # 모듈 초기화
            await self.initialize()

            self.running = True

            # 백그라운드 워커 시작
            self.tasks.append(
                asyncio.create_task(self.frame_processor())
            )

            # Discord Bot 시작
            discord_token = self.config.get("discord", {}).get("token")
            if not discord_token:
                raise ConfigError(
                    "Discord Bot Token이 설정되지 않았습니다.\n"
                    "config/config.yaml 또는 환경 변수 DISCORD_BOT_TOKEN을 설정하세요."
                )

            logger.info("Discord Bot 연결 중...")
            await self.discord_bot.start(discord_token)

        except KeyboardInterrupt:
            logger.info("사용자에 의해 중단됨 (Ctrl+C)")
        except Exception as e:
            logger.error(f"애플리케이션 에러: {e}", exc_info=True)
        finally:
            await self.stop()

    async def stop(self):
        """애플리케이션 종료"""
        logger.info("애플리케이션 종료 중...")

        self.running = False

        # Discord Bot 종료
        if self.discord_bot:
            try:
                await self.discord_bot.close()
                logger.info("Discord Bot 종료 완료")
            except Exception as e:
                logger.error(f"Discord Bot 종료 실패: {e}")

        # TTS Manager 종료
        if self.tts_manager:
            try:
                await self.tts_manager.stop()
                logger.info("TTS Manager 종료 완료")
            except Exception as e:
                logger.error(f"TTS Manager 종료 실패: {e}")

        # 백그라운드 태스크 취소
        for task in self.tasks:
            if not task.done():
                task.cancel()
                try:
                    await task
                except asyncio.CancelledError:
                    pass

        logger.info("애플리케이션 종료 완료")


async def main():
    """메인 함수"""
    # 시그널 핸들러 설정 (Windows 호환)
    def signal_handler(sig, frame):
        logger.info(f"시그널 수신: {sig}")
        sys.exit(0)

    signal.signal(signal.SIGINT, signal_handler)

    # SIGTERM은 Windows에서 지원하지 않음
    if hasattr(signal, 'SIGTERM'):
        signal.signal(signal.SIGTERM, signal_handler)

    # AnnouncerAI 실행
    ai = AnnouncerAI()
    await ai.start()


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n프로그램을 종료합니다.")
    except Exception as e:
        logger.error(f"예상치 못한 에러: {e}", exc_info=True)
        sys.exit(1)
