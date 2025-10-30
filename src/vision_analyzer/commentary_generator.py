"""
Commentary Generator for League of Legends game analysis.

This module generates natural Korean commentary based on detected events
and game state analysis.
"""

import asyncio
import logging
import random
from dataclasses import dataclass
from enum import Enum
from typing import Dict, List, Optional, Any

from .event_detector import EventType, GameEvent

logger = logging.getLogger(__name__)


class CommentaryPattern(Enum):
    """Types of commentary patterns."""

    KILL_SINGLE = "kill_single"
    KILL_DOUBLE = "kill_double"
    KILL_TRIPLE = "kill_triple"
    FIRST_BLOOD = "first_blood"
    OBJECTIVE_DRAGON = "objective_dragon"
    OBJECTIVE_BARON = "objective_baron"
    TOWER_DESTROYED = "tower_destroyed"
    INHIBITOR_DESTROYED = "inhibitor_destroyed"
    TEAMFIGHT_START = "teamfight_start"
    TEAMFIGHT_END = "teamfight_end"
    GAME_START = "game_start"
    GAME_END = "game_end"
    GOLD_ADVANTAGE = "gold_advantage"
    LEVEL_ADVANTAGE = "level_advantage"


@dataclass
class Commentary:
    """Represents generated commentary."""

    text: str
    priority: int
    event_type: Optional[EventType]
    timestamp: str

    def __str__(self) -> str:
        return f"[{self.timestamp}] {self.text}"


class CommentaryGenerator:
    """
    Generates natural Korean commentary for League of Legends games
    based on detected events and game state.
    """

    def __init__(
        self,
        enable_variations: bool = True,
        enable_context: bool = True
    ):
        """
        Initialize the Commentary Generator.

        Args:
            enable_variations: Enable multiple commentary variations
            enable_context: Enable contextual commentary based on game state
        """
        self.enable_variations = enable_variations
        self.enable_context = enable_context
        self.last_commentary: Optional[str] = None
        self.commentary_history: List[Commentary] = []

        # Commentary templates
        self._init_templates()

        logger.info(f"CommentaryGenerator initialized (variations={enable_variations}, context={enable_context})")

    def _init_templates(self) -> None:
        """Initialize commentary templates for various events."""

        self.templates: Dict[EventType, List[str]] = {
            EventType.FIRST_BLOOD: [
                "퍼스트 블러드! {team}팀의 {killer}가 {victim}를 제압했습니다!",
                "게임 시작부터 {team}팀이 우위를 점했습니다! {killer}의 퍼스트 블러드!",
                "첫 번째 킬이 발생했습니다! {team}팀 {killer}의 완벽한 플레이입니다!",
            ],
            EventType.KILL: [
                "{team}팀의 {killer}가 {victim}를 처치했습니다!",
                "{killer}의 멋진 플레이로 {victim}가 쓰러졌습니다!",
                "{team}팀이 킬을 가져갑니다! {killer}가 {victim}를 제압했습니다!",
                "또 한 명이 쓰러졌습니다! {killer}의 활약입니다!",
            ],
            EventType.MULTI_KILL: [
                "멀티킬! {kill_count}명이 동시에 쓰러졌습니다!",
                "대단한 교전입니다! {kill_count}킬이 한 번에 터졌습니다!",
                "순식간에 {kill_count}명이 처치되었습니다! 엄청난 플레이입니다!",
            ],
            EventType.DRAGON: [
                "{team}팀이 {dragon_type}을 획득했습니다!",
                "{dragon_type} 처치! {team}팀의 오브젝트 컨트롤이 빛을 발합니다!",
                "{team}팀이 드래곤을 가져갑니다! 현재 드래곤 {total_dragons}개를 보유하고 있습니다!",
                "중요한 오브젝트를 확보했습니다! {team}팀의 {dragon_type} 처치!",
            ],
            EventType.BARON: [
                "바론! {team}팀이 바론을 처치했습니다!",
                "게임의 흐름이 바뀔 수 있습니다! {team}팀의 바론 처치!",
                "중요한 순간입니다! {team}팀이 바론 나셔를 확보했습니다!",
                "{team}팀이 바론 버프를 획득했습니다! 이제 공세를 펼칠 시간입니다!",
            ],
            EventType.TOWER: [
                "{attacking_team}팀이 타워를 파괴했습니다!",
                "타워가 무너집니다! {attacking_team}팀의 압박이 계속됩니다!",
                "{destroyed_team}팀의 타워가 파괴되었습니다! {attacking_team}팀이 영역을 넓혀갑니다!",
                "또 하나의 타워가 무너졌습니다! {attacking_team}팀의 공세가 거세집니다!",
            ],
            EventType.INHIBITOR: [
                "억제기가 파괴되었습니다! {attacking_team}팀이 큰 우위를 점했습니다!",
                "{attacking_team}팀이 {destroyed_team}팀의 억제기를 파괴했습니다! 슈퍼 미니언이 등장합니다!",
                "중요한 억제기가 무너졌습니다! {destroyed_team}팀에게는 위기입니다!",
                "억제기 파괴! {attacking_team}팀이 승기를 잡아가고 있습니다!",
            ],
            EventType.TEAMFIGHT: [
                "대규모 교전이 시작되었습니다! {participants}명이 뒤엉켰습니다!",
                "{location}에서 팀파이트가 벌어지고 있습니다!",
                "양 팀이 격돌했습니다! {location}에서 {participants}명의 대규모 전투!",
                "결정적인 순간입니다! 양 팀의 격렬한 교전이 시작되었습니다!",
            ],
            EventType.GAME_END: [
                "게임 종료! {winner}팀의 승리입니다!",
                "{winner}팀이 승리를 거머쥐었습니다! 게임 시간 {game_time}!",
                "넥서스가 파괴되었습니다! {winner}팀의 완벽한 승리입니다!",
                "게임이 끝났습니다! {winner}팀이 최종 승자가 되었습니다!",
            ],
        }

        # Situational commentary templates
        self.situational_templates: Dict[str, List[str]] = {
            "gold_lead": [
                "{team}팀이 {gold}골드 차이로 앞서가고 있습니다!",
                "현재 {team}팀이 경제적으로 우위를 점하고 있습니다. 골드 차이 {gold}!",
            ],
            "level_advantage": [
                "{team}팀이 평균 레벨에서 앞서고 있습니다!",
                "레벨 차이가 벌어지고 있습니다. {team}팀의 성장이 더 빠릅니다!",
            ],
            "close_game": [
                "팽팽한 경기가 이어지고 있습니다!",
                "양 팀의 실력이 팽팽합니다! 누가 이길지 예측하기 어렵습니다!",
            ],
            "comeback": [
                "{team}팀이 추격하고 있습니다! 역전의 가능성이 보입니다!",
                "경기가 다시 흥미로워지고 있습니다! {team}팀의 반격!",
            ],
        }

    async def generate_commentary(
        self,
        event: GameEvent,
        game_state: Optional[Dict[str, Any]] = None
    ) -> Commentary:
        """
        Generate commentary for a detected event.

        Args:
            event: GameEvent to generate commentary for
            game_state: Current game state (optional)

        Returns:
            Commentary object with generated text
        """
        try:
            templates = self.templates.get(event.event_type, [])

            if not templates:
                logger.warning(f"No templates found for event type: {event.event_type}")
                return Commentary(
                    text=event.description,
                    priority=event.priority,
                    event_type=event.event_type,
                    timestamp=event.timestamp.strftime("%H:%M:%S")
                )

            # Select template
            if self.enable_variations:
                template = random.choice(templates)
            else:
                template = templates[0]

            # Format template with event details
            try:
                text = template.format(**event.details)
            except KeyError as e:
                logger.warning(f"Missing key in event details: {e}")
                text = event.description

            # Add situational commentary if context is enabled
            if self.enable_context and game_state:
                situational = await self._generate_situational_commentary(game_state)
                if situational:
                    text = f"{text} {situational}"

            commentary = Commentary(
                text=text,
                priority=event.priority,
                event_type=event.event_type,
                timestamp=event.timestamp.strftime("%H:%M:%S")
            )

            self.last_commentary = text
            self.commentary_history.append(commentary)

            logger.info(f"Generated commentary: {text}")
            return commentary

        except Exception as e:
            logger.error(f"Error generating commentary: {e}", exc_info=True)
            # Fallback to event description
            return Commentary(
                text=event.description,
                priority=event.priority,
                event_type=event.event_type,
                timestamp=event.timestamp.strftime("%H:%M:%S")
            )

    async def generate_batch_commentary(
        self,
        events: List[GameEvent],
        game_state: Optional[Dict[str, Any]] = None
    ) -> List[Commentary]:
        """
        Generate commentary for multiple events.

        Args:
            events: List of GameEvents
            game_state: Current game state (optional)

        Returns:
            List of Commentary objects
        """
        commentaries = []

        for event in sorted(events, key=lambda e: e.priority, reverse=True):
            commentary = await self.generate_commentary(event, game_state)
            commentaries.append(commentary)

        return commentaries

    async def _generate_situational_commentary(
        self,
        game_state: Dict[str, Any]
    ) -> Optional[str]:
        """
        Generate additional situational commentary based on game state.

        Args:
            game_state: Current game state

        Returns:
            Additional commentary text or None
        """
        try:
            # Gold advantage
            gold_diff = game_state.get("gold_difference", 0)
            if abs(gold_diff) > 3000:
                team = "블루" if gold_diff > 0 else "레드"
                templates = self.situational_templates["gold_lead"]
                template = random.choice(templates) if self.enable_variations else templates[0]
                return template.format(team=team, gold=abs(gold_diff))

            # Close game
            if abs(gold_diff) < 1000:
                templates = self.situational_templates["close_game"]
                return random.choice(templates) if self.enable_variations else templates[0]

            return None

        except Exception as e:
            logger.warning(f"Error generating situational commentary: {e}")
            return None

    async def generate_periodic_commentary(
        self,
        game_state: Dict[str, Any]
    ) -> Optional[Commentary]:
        """
        Generate periodic commentary for ongoing game state.
        Used when no specific events are detected but commentary is needed.

        Args:
            game_state: Current game state

        Returns:
            Commentary object or None
        """
        try:
            commentary_text = None
            priority = 5

            # Check for gold advantage
            gold_diff = game_state.get("gold_difference", 0)
            if abs(gold_diff) > 5000:
                team = "블루" if gold_diff > 0 else "레드"
                commentary_text = f"{team}팀이 {abs(gold_diff)}골드 차이로 크게 앞서가고 있습니다!"
                priority = 6

            # Check kill score
            elif game_state.get("total_kills", 0) > 20:
                commentary_text = "양 팀의 치열한 공방이 계속되고 있습니다!"
                priority = 5

            # Check game time
            elif game_state.get("game_time_minutes", 0) > 30:
                commentary_text = "경기가 30분을 넘어가고 있습니다. 긴장감이 고조되고 있습니다!"
                priority = 6

            if commentary_text:
                from datetime import datetime
                return Commentary(
                    text=commentary_text,
                    priority=priority,
                    event_type=None,
                    timestamp=datetime.now().strftime("%H:%M:%S")
                )

            return None

        except Exception as e:
            logger.error(f"Error generating periodic commentary: {e}", exc_info=True)
            return None

    def get_recent_commentaries(self, count: int = 10) -> List[Commentary]:
        """
        Get recent commentaries.

        Args:
            count: Number of recent commentaries to retrieve

        Returns:
            List of recent Commentary objects
        """
        return self.commentary_history[-count:] if self.commentary_history else []

    def clear_history(self) -> None:
        """Clear commentary history."""
        self.commentary_history.clear()
        self.last_commentary = None
        logger.info("Commentary history cleared")
