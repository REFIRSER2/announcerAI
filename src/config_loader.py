"""
Configuration Loader Module

설정 파일(YAML) 로드 및 검증을 담당하는 모듈
"""

import os
import logging
from pathlib import Path
from typing import Dict, Any, Optional
import yaml

logger = logging.getLogger(__name__)


class ConfigError(Exception):
    """설정 관련 에러"""
    pass


class ConfigLoader:
    """
    설정 파일을 로드하고 검증하는 클래스

    config.yaml 파일을 읽어 애플리케이션 설정을 제공합니다.
    환경 변수를 통한 설정 오버라이드를 지원합니다.
    """

    def __init__(self, config_path: Optional[str] = None):
        """
        Args:
            config_path: 설정 파일 경로. None인 경우 기본 경로 사용
        """
        if config_path is None:
            # 프로젝트 루트의 config/config.yaml
            project_root = Path(__file__).parent.parent
            config_path = project_root / "config" / "config.yaml"

        self.config_path = Path(config_path)
        self._config: Dict[str, Any] = {}

    def load(self) -> Dict[str, Any]:
        """
        설정 파일 로드

        Returns:
            로드된 설정 딕셔너리

        Raises:
            ConfigError: 설정 파일을 찾을 수 없거나 파싱 실패 시
        """
        if not self.config_path.exists():
            raise ConfigError(
                f"설정 파일을 찾을 수 없습니다: {self.config_path}\n"
                f"config.example.yaml을 복사하여 config/config.yaml을 생성하세요."
            )

        try:
            with open(self.config_path, 'r', encoding='utf-8') as f:
                self._config = yaml.safe_load(f)

            logger.info(f"설정 파일 로드 완료: {self.config_path}")

            # 환경 변수로 오버라이드
            self._apply_env_overrides()

            # 설정 검증
            self._validate()

            return self._config

        except yaml.YAMLError as e:
            raise ConfigError(f"설정 파일 파싱 실패: {e}")
        except Exception as e:
            raise ConfigError(f"설정 파일 로드 실패: {e}")

    def _apply_env_overrides(self):
        """환경 변수로 설정 오버라이드"""
        # Discord Token
        discord_token = os.getenv("DISCORD_BOT_TOKEN")
        if discord_token:
            self._config.setdefault("discord", {})["token"] = discord_token
            logger.info("Discord Token을 환경 변수에서 로드했습니다")

        # Vision API Key
        vision_api_key = os.getenv("VISION_API_KEY")
        if vision_api_key:
            self._config.setdefault("vision", {})["api_key"] = vision_api_key
            logger.info("Vision API Key를 환경 변수에서 로드했습니다")

        # Vision API Provider
        vision_provider = os.getenv("VISION_API_PROVIDER")
        if vision_provider:
            self._config.setdefault("vision", {})["api_provider"] = vision_provider

    def _validate(self):
        """설정 검증"""
        required_sections = ["discord", "vision", "tts", "system"]

        for section in required_sections:
            if section not in self._config:
                raise ConfigError(f"필수 설정 섹션이 없습니다: {section}")

        # Discord 설정 검증
        discord_config = self._config.get("discord", {})
        if not discord_config.get("token"):
            logger.warning(
                "Discord Bot Token이 설정되지 않았습니다. "
                "config/config.yaml 또는 환경 변수 DISCORD_BOT_TOKEN을 설정하세요."
            )

        # Vision 설정 검증
        vision_config = self._config.get("vision", {})
        if not vision_config.get("api_key"):
            logger.warning(
                "Vision API Key가 설정되지 않았습니다. "
                "Mock 모드로 실행됩니다."
            )

        provider = vision_config.get("api_provider", "openai")
        if provider not in ["openai", "claude"]:
            raise ConfigError(
                f"지원하지 않는 Vision API Provider: {provider}\n"
                f"'openai' 또는 'claude'를 사용하세요."
            )

    def get(self, key: str, default: Any = None) -> Any:
        """
        설정 값 가져오기

        Args:
            key: 점(.)으로 구분된 설정 키 (예: "discord.token")
            default: 키가 없을 경우 반환할 기본값

        Returns:
            설정 값
        """
        keys = key.split(".")
        value = self._config

        for k in keys:
            if isinstance(value, dict):
                value = value.get(k)
                if value is None:
                    return default
            else:
                return default

        return value

    @property
    def config(self) -> Dict[str, Any]:
        """전체 설정 딕셔너리 반환"""
        return self._config


def load_config(config_path: Optional[str] = None) -> Dict[str, Any]:
    """
    설정 파일 로드 헬퍼 함수

    Args:
        config_path: 설정 파일 경로

    Returns:
        로드된 설정 딕셔너리
    """
    loader = ConfigLoader(config_path)
    return loader.load()
