"""
Vision Analyzer for League of Legends game analysis.

This module uses AI Vision APIs (OpenAI GPT-4 Vision or Claude Vision)
to analyze game screenshots and extract game state information.
"""

import asyncio
import base64
import io
import logging
import os
from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional, Dict, Any, List
from PIL import Image

logger = logging.getLogger(__name__)

# Try importing AI APIs
try:
    import openai
    OPENAI_AVAILABLE = True
except ImportError:
    OPENAI_AVAILABLE = False
    logger.warning("OpenAI package not available")

try:
    import anthropic
    ANTHROPIC_AVAILABLE = True
except ImportError:
    ANTHROPIC_AVAILABLE = False
    logger.warning("Anthropic package not available")


@dataclass
class GameState:
    """Represents the current state of a League of Legends game."""

    # Basic info
    timestamp: datetime = field(default_factory=datetime.now)
    game_time: str = "00:00"
    game_time_minutes: float = 0.0

    # Teams
    blue_team_champions: List[str] = field(default_factory=list)
    red_team_champions: List[str] = field(default_factory=list)

    # Kills/Deaths/Assists
    blue_team_kills: int = 0
    red_team_kills: int = 0
    total_kills: int = 0

    # Gold
    blue_gold: int = 0
    red_gold: int = 0
    gold_difference: int = 0

    # Objectives
    dragons: Dict[str, int] = field(default_factory=lambda: {"blue": 0, "red": 0})
    barons: Dict[str, int] = field(default_factory=lambda: {"blue": 0, "red": 0})
    towers: Dict[str, int] = field(default_factory=lambda: {"blue": 11, "red": 11})
    inhibitors: Dict[str, int] = field(default_factory=lambda: {"blue": 3, "red": 3})

    # Events
    last_killer: str = ""
    last_victim: str = ""
    killer_team: str = ""
    last_dragon_type: str = ""

    # Game status
    in_teamfight: bool = False
    teamfight_participants: int = 0
    teamfight_location: str = ""
    game_ended: bool = False
    winner: str = ""

    # Raw analysis
    raw_analysis: str = ""
    analysis_summary: str = ""

    def to_dict(self) -> Dict[str, Any]:
        """Convert GameState to dictionary."""
        return {
            "timestamp": self.timestamp.isoformat(),
            "game_time": self.game_time,
            "game_time_minutes": self.game_time_minutes,
            "blue_team_champions": self.blue_team_champions,
            "red_team_champions": self.red_team_champions,
            "blue_team_kills": self.blue_team_kills,
            "red_team_kills": self.red_team_kills,
            "total_kills": self.total_kills,
            "blue_gold": self.blue_gold,
            "red_gold": self.red_gold,
            "gold_difference": self.gold_difference,
            "dragons": self.dragons,
            "barons": self.barons,
            "towers": self.towers,
            "inhibitors": self.inhibitors,
            "last_killer": self.last_killer,
            "last_victim": self.last_victim,
            "killer_team": self.killer_team,
            "last_dragon_type": self.last_dragon_type,
            "in_teamfight": self.in_teamfight,
            "teamfight_participants": self.teamfight_participants,
            "teamfight_location": self.teamfight_location,
            "game_ended": self.game_ended,
            "winner": self.winner,
            "raw_analysis": self.raw_analysis,
            "analysis_summary": self.analysis_summary,
        }


class VisionAnalyzer:
    """
    Analyzes League of Legends game screenshots using AI Vision APIs
    to extract game state and generate commentary.
    """

    def __init__(
        self,
        api_provider: str = "openai",
        api_key: Optional[str] = None,
        model: Optional[str] = None,
        max_tokens: int = 1000,
        temperature: float = 0.7
    ):
        """
        Initialize the Vision Analyzer.

        Args:
            api_provider: "openai" or "anthropic"
            api_key: API key for the chosen provider (if None, uses env var)
            model: Model name (if None, uses default)
            max_tokens: Maximum tokens for API response
            temperature: Temperature for response generation
        """
        self.api_provider = api_provider.lower()
        self.max_tokens = max_tokens
        self.temperature = temperature

        # Set up API client
        if self.api_provider == "openai":
            if not OPENAI_AVAILABLE:
                raise ImportError("OpenAI package not installed. Install with: pip install openai")

            self.api_key = api_key or os.getenv("OPENAI_API_KEY")
            self.model = model or "gpt-4-vision-preview"

            if self.api_key:
                self.client = openai.AsyncOpenAI(api_key=self.api_key)
                logger.info(f"OpenAI client initialized with model: {self.model}")
            else:
                logger.warning("OpenAI API key not provided - running in mock mode")
                self.client = None

        elif self.api_provider == "anthropic":
            if not ANTHROPIC_AVAILABLE:
                raise ImportError("Anthropic package not installed. Install with: pip install anthropic")

            self.api_key = api_key or os.getenv("ANTHROPIC_API_KEY")
            self.model = model or "claude-3-opus-20240229"

            if self.api_key:
                self.client = anthropic.AsyncAnthropic(api_key=self.api_key)
                logger.info(f"Anthropic client initialized with model: {self.model}")
            else:
                logger.warning("Anthropic API key not provided - running in mock mode")
                self.client = None
        else:
            raise ValueError(f"Unsupported API provider: {api_provider}")

        # Analysis prompt
        self.system_prompt = self._create_system_prompt()

        logger.info(
            f"VisionAnalyzer initialized "
            f"(provider={api_provider}, model={self.model})"
        )

    def _create_system_prompt(self) -> str:
        """Create the system prompt for vision analysis."""
        return """당신은 리그 오브 레전드(League of Legends) 전문 게임 해설가이자 분석가입니다.

제공된 게임 화면을 분석하고 다음 정보를 정확하게 파악하세요:

1. **게임 시간**: 현재 게임 진행 시간 (MM:SS 형식)

2. **팀 정보**:
   - 블루팀 챔피언 목록
   - 레드팀 챔피언 목록

3. **점수 정보**:
   - 블루팀 킬 수
   - 레드팀 킬 수
   - 각 팀의 골드

4. **오브젝트**:
   - 드래곤 처치 현황 (어느 팀이 몇 개)
   - 바론 처치 여부
   - 타워 파괴 현황
   - 억제기 상태

5. **현재 상황**:
   - 진행 중인 전투나 교전
   - 최근 발생한 킬
   - 특별한 이벤트나 하이라이트

6. **게임 분석**:
   - 어느 팀이 우세한지
   - 중요한 전략적 포인트
   - 주목할 만한 플레이

응답은 JSON 형식으로 구조화하여 제공하되, 해설 텍스트는 자연스러운 한국어로 작성하세요.
없거나 확인할 수 없는 정보는 null이나 0으로 표시하세요."""

    async def analyze_frame(
        self,
        image: Image.Image,
        additional_context: Optional[str] = None
    ) -> GameState:
        """
        Analyze a game frame and extract game state.

        Args:
            image: PIL Image object of the game frame
            additional_context: Additional context for analysis

        Returns:
            GameState object with extracted information
        """
        try:
            # If no API client, return mock data
            if self.client is None:
                logger.info("Running in mock mode - generating sample data")
                return self._generate_mock_state()

            # Prepare image
            image_data = await self._prepare_image(image)

            # Create prompt
            user_prompt = "위 게임 화면을 분석하고 현재 게임 상황을 상세히 설명해주세요."
            if additional_context:
                user_prompt += f"\n\n추가 컨텍스트: {additional_context}"

            # Call API
            if self.api_provider == "openai":
                response = await self._call_openai_api(image_data, user_prompt)
            else:  # anthropic
                response = await self._call_anthropic_api(image_data, user_prompt)

            # Parse response into GameState
            game_state = await self._parse_response(response)

            logger.info(f"Frame analyzed successfully: {game_state.analysis_summary}")
            return game_state

        except Exception as e:
            logger.error(f"Error analyzing frame: {e}", exc_info=True)
            # Return empty state on error
            return GameState(
                raw_analysis=f"Error: {str(e)}",
                analysis_summary="분석 실패"
            )

    async def _prepare_image(self, image: Image.Image) -> str:
        """
        Prepare image for API call.

        Args:
            image: PIL Image object

        Returns:
            Base64 encoded image string
        """
        try:
            # Resize if too large (max 2048 pixels on longest side)
            max_size = 2048
            if max(image.size) > max_size:
                ratio = max_size / max(image.size)
                new_size = tuple(int(dim * ratio) for dim in image.size)
                image = image.resize(new_size, Image.Resampling.LANCZOS)
                logger.debug(f"Image resized to {new_size}")

            # Convert to RGB if needed
            if image.mode != "RGB":
                image = image.convert("RGB")

            # Encode to base64
            buffer = io.BytesIO()
            image.save(buffer, format="JPEG", quality=85)
            image_bytes = buffer.getvalue()
            base64_image = base64.b64encode(image_bytes).decode("utf-8")

            return base64_image

        except Exception as e:
            logger.error(f"Error preparing image: {e}", exc_info=True)
            raise

    async def _call_openai_api(
        self,
        image_data: str,
        user_prompt: str
    ) -> str:
        """Call OpenAI Vision API."""
        try:
            response = await self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {
                        "role": "system",
                        "content": self.system_prompt
                    },
                    {
                        "role": "user",
                        "content": [
                            {
                                "type": "text",
                                "text": user_prompt
                            },
                            {
                                "type": "image_url",
                                "image_url": {
                                    "url": f"data:image/jpeg;base64,{image_data}"
                                }
                            }
                        ]
                    }
                ],
                max_tokens=self.max_tokens,
                temperature=self.temperature
            )

            return response.choices[0].message.content

        except Exception as e:
            logger.error(f"OpenAI API call failed: {e}", exc_info=True)
            raise

    async def _call_anthropic_api(
        self,
        image_data: str,
        user_prompt: str
    ) -> str:
        """Call Anthropic Vision API."""
        try:
            response = await self.client.messages.create(
                model=self.model,
                max_tokens=self.max_tokens,
                temperature=self.temperature,
                system=self.system_prompt,
                messages=[
                    {
                        "role": "user",
                        "content": [
                            {
                                "type": "image",
                                "source": {
                                    "type": "base64",
                                    "media_type": "image/jpeg",
                                    "data": image_data
                                }
                            },
                            {
                                "type": "text",
                                "text": user_prompt
                            }
                        ]
                    }
                ]
            )

            return response.content[0].text

        except Exception as e:
            logger.error(f"Anthropic API call failed: {e}", exc_info=True)
            raise

    async def _parse_response(self, response: str) -> GameState:
        """
        Parse API response into GameState.

        Args:
            response: Raw API response text

        Returns:
            GameState object
        """
        try:
            import re
            import json

            game_state = GameState()
            game_state.raw_analysis = response

            # Try to extract JSON if present
            json_match = re.search(r'\{.*\}', response, re.DOTALL)
            if json_match:
                try:
                    data = json.loads(json_match.group())

                    # Extract fields from JSON
                    game_state.game_time = data.get("game_time", "00:00")
                    game_state.blue_team_kills = data.get("blue_team_kills", data.get("blue_kills", 0))
                    game_state.red_team_kills = data.get("red_team_kills", data.get("red_kills", 0))
                    game_state.total_kills = game_state.blue_team_kills + game_state.red_team_kills
                    game_state.blue_gold = data.get("blue_gold", 0)
                    game_state.red_gold = data.get("red_gold", 0)
                    game_state.gold_difference = game_state.blue_gold - game_state.red_gold

                    if "dragons" in data:
                        game_state.dragons = data["dragons"]
                    if "barons" in data:
                        game_state.barons = data["barons"]
                    if "summary" in data:
                        game_state.analysis_summary = data["summary"]

                except json.JSONDecodeError:
                    logger.warning("Failed to parse JSON from response")

            # Generate summary if not present
            if not game_state.analysis_summary:
                # Extract first meaningful sentence
                sentences = response.split('.')
                game_state.analysis_summary = sentences[0][:200] if sentences else response[:200]

            return game_state

        except Exception as e:
            logger.error(f"Error parsing response: {e}", exc_info=True)
            return GameState(
                raw_analysis=response,
                analysis_summary=response[:200]
            )

    def _generate_mock_state(self) -> GameState:
        """Generate mock game state for testing without API."""
        import random

        game_state = GameState()
        game_state.game_time = f"{random.randint(5, 30):02d}:{random.randint(0, 59):02d}"
        game_state.blue_team_kills = random.randint(0, 20)
        game_state.red_team_kills = random.randint(0, 20)
        game_state.total_kills = game_state.blue_team_kills + game_state.red_team_kills
        game_state.blue_gold = random.randint(10000, 50000)
        game_state.red_gold = random.randint(10000, 50000)
        game_state.gold_difference = game_state.blue_gold - game_state.red_gold

        game_state.blue_team_champions = ["야스오", "리신", "아리", "징크스", "레오나"]
        game_state.red_team_champions = ["다리우스", "리 신", "조이", "케이틀린", "쓰레쉬"]

        game_state.dragons = {"blue": random.randint(0, 4), "red": random.randint(0, 4)}
        game_state.barons = {"blue": random.randint(0, 1), "red": random.randint(0, 1)}

        game_state.raw_analysis = "[Mock Mode] 게임이 진행 중입니다."
        game_state.analysis_summary = f"현재 {game_state.game_time}, 블루팀 {game_state.blue_team_kills} vs 레드팀 {game_state.red_team_kills}"

        logger.debug(f"Generated mock state: {game_state.analysis_summary}")
        return game_state

    async def analyze_batch(
        self,
        images: List[Image.Image],
        batch_size: int = 5
    ) -> List[GameState]:
        """
        Analyze multiple frames in batch.

        Args:
            images: List of PIL Image objects
            batch_size: Number of concurrent analyses

        Returns:
            List of GameState objects
        """
        results = []

        for i in range(0, len(images), batch_size):
            batch = images[i:i + batch_size]
            tasks = [self.analyze_frame(img) for img in batch]
            batch_results = await asyncio.gather(*tasks, return_exceptions=True)

            for result in batch_results:
                if isinstance(result, Exception):
                    logger.error(f"Batch analysis error: {result}")
                    results.append(GameState(
                        raw_analysis=f"Error: {str(result)}",
                        analysis_summary="분석 실패"
                    ))
                else:
                    results.append(result)

        logger.info(f"Batch analysis complete: {len(results)} frames processed")
        return results
