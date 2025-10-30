"""
Event Detector for League of Legends game analysis.

This module detects important game events by comparing consecutive frames
and analyzing game state changes.
"""

import asyncio
import logging
from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from typing import Optional, Dict, Any, List

logger = logging.getLogger(__name__)


class EventType(Enum):
    """Types of game events that can be detected."""

    KILL = "kill"
    OBJECTIVE = "objective"
    TEAMFIGHT = "teamfight"
    TOWER = "tower"
    GAME_END = "game_end"
    FIRST_BLOOD = "first_blood"
    MULTI_KILL = "multi_kill"
    BARON = "baron"
    DRAGON = "dragon"
    INHIBITOR = "inhibitor"


@dataclass
class GameEvent:
    """Represents a detected game event."""

    event_type: EventType
    timestamp: datetime
    description: str
    priority: int  # 1-10, higher = more important
    details: Dict[str, Any]

    def __str__(self) -> str:
        return f"[{self.event_type.value}] {self.description} (Priority: {self.priority})"


class EventDetector:
    """
    Detects important events in League of Legends games by analyzing
    consecutive frames and game state changes.
    """

    def __init__(
        self,
        cooldown_seconds: float = 3.0,
        teamfight_threshold: int = 3,
        enable_multiprocessing: bool = False
    ):
        """
        Initialize the Event Detector.

        Args:
            cooldown_seconds: Minimum time between similar events
            teamfight_threshold: Minimum participants for teamfight detection
            enable_multiprocessing: Whether to enable multiprocessing (currently unused)
        """
        self.cooldown_seconds = cooldown_seconds
        self.teamfight_threshold = teamfight_threshold
        self.enable_multiprocessing = enable_multiprocessing
        self.previous_state: Optional[Dict[str, Any]] = None
        self.event_history: List[GameEvent] = []
        self.last_event_time: Dict[EventType, datetime] = {}

        logger.info(
            f"EventDetector initialized with cooldown={cooldown_seconds}s, "
            f"teamfight_threshold={teamfight_threshold}"
        )

    async def detect_events(
        self,
        current_state: Dict[str, Any],
        previous_state: Optional[Dict[str, Any]] = None
    ) -> List[GameEvent]:
        """
        Detect events by comparing current state with previous state.

        Args:
            current_state: Current game state from vision analyzer
            previous_state: Previous game state (optional, uses cached if None)

        Returns:
            List of detected GameEvent objects
        """
        try:
            if previous_state is None:
                previous_state = self.previous_state

            # First frame, no comparison possible
            if previous_state is None:
                self.previous_state = current_state
                logger.debug("First frame, no events to detect")
                return []

            events: List[GameEvent] = []

            # Detect various event types
            events.extend(await self._detect_kills(current_state, previous_state))
            events.extend(await self._detect_objectives(current_state, previous_state))
            events.extend(await self._detect_towers(current_state, previous_state))
            events.extend(await self._detect_teamfights(current_state, previous_state))
            events.extend(await self._detect_game_end(current_state, previous_state))

            # Filter events based on cooldown
            filtered_events = self._filter_cooldown_events(events)

            # Update state
            self.previous_state = current_state
            self.event_history.extend(filtered_events)

            # Update last event times
            for event in filtered_events:
                self.last_event_time[event.event_type] = event.timestamp

            if filtered_events:
                logger.info(f"Detected {len(filtered_events)} events: {[e.event_type.value for e in filtered_events]}")

            return filtered_events

        except Exception as e:
            logger.error(f"Error detecting events: {e}", exc_info=True)
            return []

    async def _detect_kills(
        self,
        current: Dict[str, Any],
        previous: Dict[str, Any]
    ) -> List[GameEvent]:
        """Detect kill events."""
        events = []

        try:
            current_kills = current.get("total_kills", 0)
            previous_kills = previous.get("total_kills", 0)

            if current_kills > previous_kills:
                kill_diff = current_kills - previous_kills

                # Check for multi-kill
                if kill_diff > 1:
                    event = GameEvent(
                        event_type=EventType.MULTI_KILL,
                        timestamp=datetime.now(),
                        description=f"{kill_diff}명의 챔피언이 동시에 처치되었습니다!",
                        priority=9,
                        details={"kill_count": kill_diff}
                    )
                    events.append(event)
                else:
                    # Check for first blood
                    is_first_blood = current_kills == 1 and previous_kills == 0

                    killer = current.get("last_killer", "알 수 없는 챔피언")
                    victim = current.get("last_victim", "적 챔피언")
                    team = current.get("killer_team", "")

                    event_type = EventType.FIRST_BLOOD if is_first_blood else EventType.KILL
                    priority = 10 if is_first_blood else 7

                    description = (
                        f"퍼스트 블러드! {team}팀의 {killer}가 {victim}를 처치했습니다!"
                        if is_first_blood
                        else f"{team}팀의 {killer}가 {victim}를 처치했습니다!"
                    )

                    event = GameEvent(
                        event_type=event_type,
                        timestamp=datetime.now(),
                        description=description,
                        priority=priority,
                        details={
                            "killer": killer,
                            "victim": victim,
                            "team": team,
                            "is_first_blood": is_first_blood
                        }
                    )
                    events.append(event)

        except Exception as e:
            logger.warning(f"Error detecting kills: {e}")

        return events

    async def _detect_objectives(
        self,
        current: Dict[str, Any],
        previous: Dict[str, Any]
    ) -> List[GameEvent]:
        """Detect objective events (Dragon, Baron, etc.)."""
        events = []

        try:
            # Dragon detection
            current_dragons = current.get("dragons", {"blue": 0, "red": 0})
            previous_dragons = previous.get("dragons", {"blue": 0, "red": 0})

            for team in ["blue", "red"]:
                if current_dragons.get(team, 0) > previous_dragons.get(team, 0):
                    dragon_type = current.get("last_dragon_type", "드래곤")

                    event = GameEvent(
                        event_type=EventType.DRAGON,
                        timestamp=datetime.now(),
                        description=f"{team.upper()}팀이 {dragon_type}을 획득했습니다!",
                        priority=8,
                        details={
                            "team": team,
                            "dragon_type": dragon_type,
                            "total_dragons": current_dragons.get(team, 0)
                        }
                    )
                    events.append(event)

            # Baron detection
            current_barons = current.get("barons", {"blue": 0, "red": 0})
            previous_barons = previous.get("barons", {"blue": 0, "red": 0})

            for team in ["blue", "red"]:
                if current_barons.get(team, 0) > previous_barons.get(team, 0):
                    event = GameEvent(
                        event_type=EventType.BARON,
                        timestamp=datetime.now(),
                        description=f"{team.upper()}팀이 바론을 처치했습니다!",
                        priority=10,
                        details={
                            "team": team,
                            "total_barons": current_barons.get(team, 0)
                        }
                    )
                    events.append(event)

        except Exception as e:
            logger.warning(f"Error detecting objectives: {e}")

        return events

    async def _detect_towers(
        self,
        current: Dict[str, Any],
        previous: Dict[str, Any]
    ) -> List[GameEvent]:
        """Detect tower destruction events."""
        events = []

        try:
            current_towers = current.get("towers", {"blue": 11, "red": 11})
            previous_towers = previous.get("towers", {"blue": 11, "red": 11})

            for team in ["blue", "red"]:
                if current_towers.get(team, 11) < previous_towers.get(team, 11):
                    towers_lost = previous_towers.get(team, 11) - current_towers.get(team, 11)
                    opposing_team = "RED" if team == "blue" else "BLUE"

                    event = GameEvent(
                        event_type=EventType.TOWER,
                        timestamp=datetime.now(),
                        description=f"{opposing_team}팀이 {team.upper()}팀의 타워를 파괴했습니다!",
                        priority=7,
                        details={
                            "destroyed_team": team,
                            "attacking_team": opposing_team.lower(),
                            "towers_lost": towers_lost,
                            "remaining_towers": current_towers.get(team, 11)
                        }
                    )
                    events.append(event)

            # Inhibitor detection
            current_inhibs = current.get("inhibitors", {"blue": 3, "red": 3})
            previous_inhibs = previous.get("inhibitors", {"blue": 3, "red": 3})

            for team in ["blue", "red"]:
                if current_inhibs.get(team, 3) < previous_inhibs.get(team, 3):
                    opposing_team = "RED" if team == "blue" else "BLUE"

                    event = GameEvent(
                        event_type=EventType.INHIBITOR,
                        timestamp=datetime.now(),
                        description=f"{opposing_team}팀이 {team.upper()}팀의 억제기를 파괴했습니다!",
                        priority=9,
                        details={
                            "destroyed_team": team,
                            "attacking_team": opposing_team.lower()
                        }
                    )
                    events.append(event)

        except Exception as e:
            logger.warning(f"Error detecting towers: {e}")

        return events

    async def _detect_teamfights(
        self,
        current: Dict[str, Any],
        previous: Dict[str, Any]
    ) -> List[GameEvent]:
        """Detect teamfight events."""
        events = []

        try:
            in_teamfight = current.get("in_teamfight", False)
            was_in_teamfight = previous.get("in_teamfight", False)

            # Teamfight started
            if in_teamfight and not was_in_teamfight:
                participants = current.get("teamfight_participants", 0)
                location = current.get("teamfight_location", "중앙")

                if participants >= self.teamfight_threshold:
                    event = GameEvent(
                        event_type=EventType.TEAMFIGHT,
                        timestamp=datetime.now(),
                        description=f"{location}에서 {participants}명이 참여하는 대규모 교전이 시작되었습니다!",
                        priority=8,
                        details={
                            "participants": participants,
                            "location": location
                        }
                    )
                    events.append(event)

        except Exception as e:
            logger.warning(f"Error detecting teamfights: {e}")

        return events

    async def _detect_game_end(
        self,
        current: Dict[str, Any],
        previous: Dict[str, Any]
    ) -> List[GameEvent]:
        """Detect game end events."""
        events = []

        try:
            game_ended = current.get("game_ended", False)
            was_ended = previous.get("game_ended", False)

            if game_ended and not was_ended:
                winner = current.get("winner", "")
                game_time = current.get("game_time", "알 수 없음")

                event = GameEvent(
                    event_type=EventType.GAME_END,
                    timestamp=datetime.now(),
                    description=f"게임이 종료되었습니다! {winner}팀의 승리! (게임 시간: {game_time})",
                    priority=10,
                    details={
                        "winner": winner,
                        "game_time": game_time
                    }
                )
                events.append(event)

        except Exception as e:
            logger.warning(f"Error detecting game end: {e}")

        return events

    def _filter_cooldown_events(self, events: List[GameEvent]) -> List[GameEvent]:
        """Filter out events that are within cooldown period."""
        filtered = []
        current_time = datetime.now()

        for event in events:
            last_time = self.last_event_time.get(event.event_type)

            if last_time is None:
                filtered.append(event)
            else:
                time_diff = (current_time - last_time).total_seconds()
                if time_diff >= self.cooldown_seconds:
                    filtered.append(event)
                else:
                    logger.debug(
                        f"Filtered event {event.event_type.value} due to cooldown "
                        f"({time_diff:.1f}s < {self.cooldown_seconds}s)"
                    )

        return filtered

    def get_recent_events(self, count: int = 10) -> List[GameEvent]:
        """
        Get the most recent events.

        Args:
            count: Number of recent events to retrieve

        Returns:
            List of recent GameEvent objects
        """
        return self.event_history[-count:] if self.event_history else []

    def clear_history(self) -> None:
        """Clear event history and reset state."""
        self.event_history.clear()
        self.last_event_time.clear()
        self.previous_state = None
        logger.info("Event history cleared")
