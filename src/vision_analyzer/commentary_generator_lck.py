"""
LCK-Style Commentary Generator for League of Legends

롤챔스(LCK) 아나운서 스타일의 해설을 생성하는 모듈
실제 중계 방송의 긴장감과 생동감을 재현합니다.
"""

import logging
import random
from typing import Dict, List, Optional, Any
from datetime import datetime

from .event_detector import GameEvent, EventType

logger = logging.getLogger(__name__)


# LCK-style commentary templates
LCK_COMMENTARY_TEMPLATES = {
    EventType.FIRST_BLOOD: [
        "퍼스트 블러드! {team}팀의 {killer}! 게임의 첫 킬을 가져갑니다!",
        "퍼스트 블러드가 터졌습니다! {killer}! 선제 공격 성공!",
        "첫 피! {team}팀의 {killer}가 게임의 흐름을 잡아갑니다!",
        "오! 퍼스트 블러드! {killer}의 침착한 플레이!",
        "게임의 첫 번째 킬! {team}팀 {killer}! 좋은 출발입니다!",
        "{killer}! 퍼스트 블러드를 따냅니다! {team}팀의 완벽한 시작!",
    ],

    EventType.KILL: [
        "{team}팀의 {killer}! {victim}을 쓰러뜨립니다!",
        "킬이 터졌습니다! {killer}의 완벽한 플레이!",
        "{killer}! 기가 막힌 타이밍으로 {victim}을 제압합니다!",
        "{victim}이 쓰러집니다! {team}팀에게 중요한 한 킬!",
        "아! {killer}의 훌륭한 판단! {victim}을 잡아냅니다!",
        "{killer}! 놓치지 않습니다! {victim} 처치!",
        "와! {killer}! {victim}을 순식간에 녹여버립니다!",
        "{team}팀 {killer}! 멋진 플레이로 킬을 가져갑니다!",
    ],

    EventType.MULTI_KILL: [
        "더블킬! {killer}! 연속 처치입니다!",
        "트리플킬! {killer}가 미쳐 날뛰고 있습니다!",
        "쿼드라킬! {killer}! 믿을 수 없는 플레이!",
        "펜타킬! 펜타킬입니다! {killer}! 완벽한 에이스!",
        "{killer}! 연속 킬! 막을 수가 없습니다!",
        "와! {killer}! 계속해서 처치를 이어갑니다!",
        "{killer}의 캐리력이 폭발합니다! 멀티킬!",
        "이게 되나요?! {killer}! 혼자서 다 해치웁니다!",
    ],

    EventType.DRAGON: [
        "{team}팀! 드래곤을 확보합니다!",
        "드래곤이 넘어갑니다! {team}팀의 오브젝트 컨트롤!",
        "{team}팀! 중요한 드래곤을 가져갑니다!",
        "오브젝트 싸움! {team}팀이 드래곤을 챙겨갑니다!",
        "{team}팀 드래곤 획득! 이제 드래곤 소울이 보이기 시작합니다!",
        "드래곤! {team}팀! 게임을 풀어나가고 있습니다!",
        "{dragon_type} 처치! {team}팀의 완벽한 오브젝트 관리!",
        "{team}팀이 {total_dragons}번째 드래곤을 가져갑니다! 소울이 가까워집니다!",
    ],

    EventType.BARON: [
        "바론 나셔! {team}팀이 잡았습니다!",
        "바론! {team}팀! 게임의 판도가 완전히 바뀔 수 있습니다!",
        "{team}팀! 바론을 확보합니다! 이제 게임이 기울어지기 시작합니다!",
        "중요한 바론 나셔! {team}팀이 가져갑니다!",
        "오! 바론! {team}팀! 이걸로 게임을 끝낼 수 있을까요?!",
        "{team}팀 바론 획득! 엄청난 버프를 받고 밀어붙입니다!",
        "게임을 결정지을 바론! {team}팀이 성공적으로 처치합니다!",
        "바론 버프! {team}팀! 이제 게임을 마무리할 시간입니다!",
    ],

    EventType.TOWER: [
        "타워가 무너집니다! {attacking_team}팀의 압박이 거세집니다!",
        "{attacking_team}팀! 타워를 부숩니다!",
        "타워 철거! {attacking_team}팀이 계속해서 맵을 열어갑니다!",
        "{attacking_team}팀! 한 개씩 타워를 가져갑니다!",
        "타워가 터졌습니다! {attacking_team}팀의 공격이 멈추지 않습니다!",
        "{attacking_team}팀의 밀어붙이기! 타워가 무너집니다!",
        "또 하나의 타워! {attacking_team}팀이 영역을 넓혀갑니다!",
    ],

    EventType.INHIBITOR: [
        "억제기까지 무너집니다! {attacking_team}팀! 이제 넥서스가 보입니다!",
        "억제기! {attacking_team}팀이 밀어붙입니다!",
        "{attacking_team}팀! 억제기를 부숩니다! 게임이 끝날 수도 있습니다!",
        "억제기가 파괴됩니다! {attacking_team}팀의 거센 공세!",
        "{attacking_team}팀! 억제기까지! 슈퍼 미니언이 나옵니다!",
        "중요한 억제기! {attacking_team}팀이 게임을 끝내러 갑니다!",
        "{destroyed_team}팀에게는 위기입니다! 억제기가 무너졌습니다!",
    ],

    EventType.TEAMFIGHT: [
        "대규모 교전이 시작됩니다!",
        "5대5 한타! 양 팀 모두 스킬을 쏟아붓고 있습니다!",
        "팀파이트가 터졌습니다! 누가 이 싸움을 가져갈까요?!",
        "격렬한 교전! 양 팀 모두 물러서지 않습니다!",
        "오! 한타! 승부의 순간입니다!",
        "대치 상황! 그리고 교전 시작! 누가 웃을까요?!",
        "이게 게임을 결정지을 한타가 될 수도 있습니다!",
        "{location}에서 격렬한 교전! {participants}명이 뒤엉켰습니다!",
        "양 팀의 결전! 여기서 게임이 갈립니다!",
        "한타가 벌어집니다! 이 싸움의 승자가 게임을 가져갈 것입니다!",
    ],

    EventType.GAME_END: [
        "게임 종료! {winner}팀의 승리입니다!",
        "{winner}팀! 승리를 가져갑니다!",
        "게임이 끝났습니다! {winner}팀의 완벽한 경기 운영!",
        "넥서스가 무너집니다! {winner}팀의 승리!",
        "{winner}팀! 게임을 마무리합니다! 훌륭한 경기였습니다!",
        "승리! {winner}팀! 압도적인 경기력을 보여줬습니다!",
        "게임 오버! {winner}팀이 최종 승자가 되었습니다!",
        "{winner}팀의 완승! 게임 시간 {game_time}!",
    ],
}


# Situational commentary (game state analysis)
LCK_SITUATIONAL_COMMENTARY = {
    # Gold difference commentary
    "huge_gold_lead": [  # 8000+ gold lead
        "{team}팀의 압도적인 경기 운영! {gold:,}골드 차이! 이대로 게임을 끝낼 수 있을까요?",
        "엄청난 골드 차이입니다! {team}팀이 {gold:,}골드나 앞서가고 있습니다!",
        "{team}팀! 완전히 게임을 장악했습니다! 골드 차이 {gold:,}!",
    ],

    "large_gold_lead": [  # 5000-8000 gold lead
        "{team}팀이 {gold:,}골드 차이로 크게 앞서가고 있습니다!",
        "경제적으로 {team}팀의 우위! 골드 차이가 {gold:,}까지 벌어졌습니다!",
        "{team}팀! 게임을 풀어나가고 있습니다! {gold:,}골드 리드!",
    ],

    "moderate_gold_lead": [  # 3000-5000 gold lead
        "{team}팀이 골드에서 앞서가고 있습니다! 차이는 {gold:,}!",
        "{team}팀의 우위! 약 {gold:,}골드 정도 앞서있습니다!",
    ],

    "close_game": [  # < 1000 gold diff
        "양 팀 모두 한 치의 양보도 없이 팽팽한 경기를 이어가고 있습니다!",
        "팽팽합니다! 누가 이길지 예측하기 어려운 상황!",
        "정말 박빙의 승부! 한 타 한 타가 게임을 가를 수 있습니다!",
        "긴장감이 최고조에 달했습니다! 양 팀 모두 기회를 노리고 있습니다!",
    ],

    "comeback": [  # Trailing team reducing gold diff
        "{team}팀! 포기하지 않고 계속해서 추격합니다! 역전의 기회를 노리고 있습니다!",
        "{team}팀의 반격! 골드 차이를 조금씩 줄여나가고 있습니다!",
        "경기가 다시 흥미로워지고 있습니다! {team}팀이 추격합니다!",
        "역전의 가능성! {team}팀! 게임을 포기하지 않습니다!",
    ],

    # Kill score commentary
    "kill_stomp": [  # 10+ kill difference
        "{team}팀! 킬 스코어에서 압도적인 우위를 점하고 있습니다!",
        "킬 점수를 보세요! {team}팀이 완전히 압도하고 있습니다!",
    ],

    # Early game (0-10 min)
    "early_game_lead": [
        "초반부터 {team}팀이 킬을 계속해서 가져가고 있습니다!",
        "{team}팀의 빠른 템포! 초반 우위를 확실하게 가져갑니다!",
        "초반 게임을 {team}팀이 장악하고 있습니다!",
    ],

    # Late game critical (25+ min, close)
    "late_game_critical": [
        "후반 한타 하나로 게임이 결정날 수 있는 상황입니다!",
        "이제 한 번의 실수가 게임을 가를 수 있습니다!",
        "긴장하세요! 다음 교전이 게임의 승패를 결정할 수 있습니다!",
    ],

    # Domination (multiple objectives + gold lead)
    "domination": [
        "{team}팀의 완벽한 경기 운영! 모든 면에서 앞서가고 있습니다!",
        "{team}팀! 드래곤, 바론, 골드 모든 것을 가져가고 있습니다!",
    ],
}


def get_lck_commentary(event_type: EventType, details: Dict[str, Any]) -> str:
    """
    Get LCK-style commentary for an event.

    Args:
        event_type: Type of event
        details: Event details for template formatting

    Returns:
        Commentary text
    """
    templates = LCK_COMMENTARY_TEMPLATES.get(event_type, [])
    if not templates:
        return f"{event_type.value} 이벤트가 발생했습니다!"

    template = random.choice(templates)

    try:
        return template.format(**details)
    except KeyError as e:
        logger.warning(f"Missing key {e} in event details, using default")
        return templates[0].format(**{k: "" for k in details.keys()})


def get_situational_commentary(game_state: Dict[str, Any]) -> Optional[str]:
    """
    Get LCK-style situational commentary based on game state.

    Args:
        game_state: Current game state

    Returns:
        Situational commentary or None
    """
    try:
        blue_kills = game_state.get("blue_team_kills", 0)
        red_kills = game_state.get("red_team_kills", 0)
        gold_diff = game_state.get("gold_difference", 0)
        game_time = game_state.get("game_time", "00:00")

        # Parse game time
        try:
            time_parts = game_time.split(":")
            minutes = int(time_parts[0]) if len(time_parts) > 0 else 0
        except:
            minutes = 0

        # Determine leading team
        leading_team = "블루" if gold_diff > 0 else "레드"
        trailing_team = "레드" if gold_diff > 0 else "블루"
        abs_gold_diff = abs(gold_diff)

        # Early game (0-10 min)
        if minutes < 10:
            if abs(blue_kills - red_kills) >= 3:
                kill_leader = "블루" if blue_kills > red_kills else "레드"
                return random.choice(LCK_SITUATIONAL_COMMENTARY["early_game_lead"]).format(team=kill_leader)

        # Late game (25+ min)
        elif minutes >= 25:
            # Huge gold lead
            if abs_gold_diff > 8000:
                return random.choice(LCK_SITUATIONAL_COMMENTARY["huge_gold_lead"]).format(
                    team=leading_team, gold=abs_gold_diff
                )
            # Close late game
            elif abs_gold_diff < 2000:
                return random.choice(LCK_SITUATIONAL_COMMENTARY["late_game_critical"])
            # Comeback in late game
            elif abs_gold_diff > 3000:
                return random.choice(LCK_SITUATIONAL_COMMENTARY["comeback"]).format(team=trailing_team)

        # Mid game (10-25 min)
        else:
            # Large gold difference
            if abs_gold_diff > 5000:
                return random.choice(LCK_SITUATIONAL_COMMENTARY["large_gold_lead"]).format(
                    team=leading_team, gold=abs_gold_diff
                )
            # Moderate gold difference
            elif abs_gold_diff > 3000:
                return random.choice(LCK_SITUATIONAL_COMMENTARY["moderate_gold_lead"]).format(
                    team=leading_team, gold=abs_gold_diff
                )
            # Very close game
            elif abs_gold_diff < 1000 and abs(blue_kills - red_kills) <= 2:
                return random.choice(LCK_SITUATIONAL_COMMENTARY["close_game"])

        # Kill difference (any time)
        kill_diff = abs(blue_kills - red_kills)
        if kill_diff >= 10:
            kill_leader = "블루" if blue_kills > red_kills else "레드"
            return random.choice(LCK_SITUATIONAL_COMMENTARY["kill_stomp"]).format(team=kill_leader)

        return None

    except Exception as e:
        logger.error(f"Error generating situational commentary: {e}", exc_info=True)
        return None
