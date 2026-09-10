from pathlib import Path
from typing import Any, Dict, List, Optional
import yaml

from ..utils.logger import get_logger

logger = get_logger("vtu_matcher")


class SkillProfile:
    """Loads and manages skill keywords and weights for technical matching."""

    DEFAULT_SKILLS_PATH = "config/skills.yaml"

    def __init__(self, config_path: Optional[str] = None):
        self.config_path = Path(config_path or self.DEFAULT_SKILLS_PATH)
        self.skills: Dict[str, Dict[str, Any]] = {}
        self.load_profile()

    def load_profile(self) -> None:
        """Loads skills definition from YAML file."""
        if not self.config_path.exists():
            logger.warning(
                f"Skills config not found at {self.config_path}, using built-in defaults"
            )
            self.skills = self._get_fallback_skills()
            return

        try:
            with open(self.config_path, "r", encoding="utf-8") as f:
                data = yaml.safe_load(f) or {}
                self.skills = data.get("skills", {})
        except Exception as e:
            logger.error(f"Failed to parse {self.config_path}: {e}")
            self.skills = self._get_fallback_skills()

    def get_keyword_map(self) -> Dict[str, Dict[str, Any]]:
        """
        Returns mapping from lowercased keyword to skill category and weight.
        """
        keyword_map: Dict[str, Dict[str, Any]] = {}
        for category, info in self.skills.items():
            weight = info.get("weight", 5)
            keywords = info.get("keywords", [])
            for kw in keywords:
                clean_kw = kw.strip().lower()
                if clean_kw:
                    keyword_map[clean_kw] = {
                        "category": category,
                        "weight": weight,
                        "display_name": kw.title(),
                    }
        return keyword_map

    @staticmethod
    def _get_fallback_skills() -> Dict[str, Dict[str, Any]]:
        return {
            "machine_learning": {
                "weight": 10,
                "keywords": ["machine learning", "ml", "deep learning", "pytorch", "tensorflow"],
            },
            "artificial_intelligence": {
                "weight": 10,
                "keywords": ["artificial intelligence", "ai", "generative ai", "gen ai"],
            },
            "python": {
                "weight": 10,
                "keywords": ["python", "pandas", "numpy", "scikit-learn"],
            },
            "computer_vision": {
                "weight": 9,
                "keywords": ["computer vision", "opencv", "yolo", "object detection"],
            },
            "nlp": {
                "weight": 8,
                "keywords": ["nlp", "natural language processing", "transformers"],
            },
            "frontend": {
                "weight": 7,
                "keywords": ["react", "javascript", "typescript", "next.js"],
            },
            "software_engineering": {
                "weight": 8,
                "keywords": ["software development", "backend", "api", "git"],
            },
        }
