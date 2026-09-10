import re
from typing import Dict, List, Set, Tuple

from .skill_profile import SkillProfile
from ..database.models import Internship


class SkillMatcher:
    """
    Calculates technical relevance between an internship and the user's
    technical skill profile.

    Evidence priority:
        Title       -> strongest
        Skills      -> strong
        Category    -> moderate
        Description -> supporting

    The scoring system is bounded so that an internship mentioning many
    unrelated technologies cannot automatically receive 100%.
    """

    # ==============================================================
    # CATEGORY IMPORTANCE
    # ==============================================================

    CATEGORY_WEIGHTS = {
        "machine_learning": 10.0,
        "artificial_intelligence": 10.0,
        "computer_vision": 10.0,
        "nlp": 9.0,
        "data_science": 9.0,
        "python": 8.0,
        "full_stack": 7.0,
        "data_analytics": 7.0,
        "software_engineering": 6.0,
        "frontend": 5.0,
        "sql": 4.0,
        "java": 4.0,
    }

    # ==============================================================
    # GENERIC KEYWORDS
    # ==============================================================

    GENERIC_KEYWORDS = {
        "ai",
        "ml",
        "js",
        "ts",
        "cv",
        "git",
        "github",
        "sql",
        "html",
        "css",
        "java",
        "python",
        "backend",
        "frontend",
        "api",
        "api development",
        "software development",
        "web development",
        "database",
        "mongodb",
        "mysql",
        "postgres",
        "sqlite",
    }

    # ==============================================================
    # FRONTEND KEYWORDS
    # ==============================================================

    # These are technically common technologies, but together they
    # represent a meaningful frontend skill set.
    FRONTEND_KEYWORDS = {
        "react",
        "react.js",
        "reactjs",
        "javascript",
        "js",
        "typescript",
        "ts",
        "next.js",
        "nextjs",
        "html",
        "css",
        "tailwind",
    }

    # ==============================================================
    # STRONG / CORE KEYWORDS
    # ==============================================================

    STRONG_KEYWORDS = {
        "machine learning",
        "deep learning",
        "computer vision",
        "opencv",
        "yolo",
        "yolov8",
        "object detection",
        "image segmentation",
        "natural language processing",
        "nlp",
        "transformers",
        "bert",
        "huggingface",
        "generative ai",
        "gen ai",
        "genai",
        "llm",
        "large language model",
        "rag",
        "langchain",
        "artificial intelligence",
        "data science",
        "data scientist",
        "predictive modeling",
        "feature engineering",
        "exploratory data analysis",
        "eda",
        "neural network",
        "neural networks",
        "reinforcement learning",
        "supervised learning",
        "unsupervised learning",
        "pytorch",
        "tensorflow",
        "scikit-learn",
        "sklearn",
        "mediapipe",
        "ocr",
        "prompt engineering",
    }

    # ==============================================================
    # EVIDENCE STRENGTH
    # ==============================================================

    TITLE_STRENGTH = 1.00
    SKILLS_STRENGTH = 0.85
    CATEGORY_STRENGTH = 0.55
    DESCRIPTION_STRENGTH = 0.25

    GENERIC_MULTIPLIER = 0.35
    STRONG_MULTIPLIER = 1.00
    NORMAL_MULTIPLIER = 0.65

    # ==============================================================
    # CATEGORY CAPS
    # ==============================================================

    CATEGORY_CAPS = {
        # Core AI/ML
        "machine_learning": 30.0,
        "artificial_intelligence": 25.0,
        "computer_vision": 30.0,
        "nlp": 25.0,
        "data_science": 25.0,

        # Development
        "python": 18.0,
        "full_stack": 22.0,
        "data_analytics": 18.0,
        "software_engineering": 18.0,
        "frontend": 40.0,

        # Supporting technologies
        "sql": 10.0,
        "java": 10.0,
    }

    # ==============================================================
    # ADDITIONAL TECHNOLOGY BONUS
    # ==============================================================

    ADDITIONAL_KEYWORD_BONUS = 4.0
    MAX_ADDITIONAL_KEYWORDS = 3

    # ==============================================================
    # FRONTEND SPECIALIZATION
    # ==============================================================

    # A frontend internship containing several frontend technologies
    # should receive a meaningful score even though technologies such
    # as HTML/CSS/JavaScript are individually generic.
    FRONTEND_BREADTH_BONUS = 4.0
    FRONTEND_ROLE_BONUS = 15.0

    FRONTEND_ROLE_TERMS = {
        "frontend",
        "front end",
        "frontend developer",
        "front-end developer",
        "web developer",
        "ui developer",
        "react developer",
        "reactjs developer",
        "javascript developer",
        "typescript developer",
    }

    # ==============================================================
    # CONSTRUCTOR
    # ==============================================================

    def __init__(self, profile: SkillProfile = None):
        self.profile = profile or SkillProfile()
        self.keyword_map = self.profile.get_keyword_map()

    # ==============================================================
    # TEXT MATCHING
    # ==============================================================

    def _matches_keyword(self, keyword: str, text: str) -> bool:
        """
        Match a complete word or phrase.

        Examples:
            Java -> matches Java
            Java -> does not match JavaScript
            React -> matches React
            Python -> matches Python
        """

        if not keyword or not text:
            return False

        escaped = re.escape(keyword.strip())

        pattern = rf"(?<!\w){escaped}(?!\w)"

        return bool(
            re.search(
                pattern,
                text,
                re.IGNORECASE,
            )
        )

    # ==============================================================
    # KEYWORD IMPORTANCE
    # ==============================================================

    def _keyword_multiplier(self, keyword: str) -> float:
        normalized = keyword.strip().lower()

        # Core AI/ML/CV/NLP technologies.
        if normalized in self.STRONG_KEYWORDS:
            return self.STRONG_MULTIPLIER

        # Frontend technologies get more importance than generic
        # technologies because several of them together indicate
        # genuine frontend capability.
        if normalized in self.FRONTEND_KEYWORDS:
            return 0.80

        # Very generic technologies receive lower importance.
        if normalized in self.GENERIC_KEYWORDS:
            return self.GENERIC_MULTIPLIER

        return self.NORMAL_MULTIPLIER

    # ==============================================================
    # CATEGORY WEIGHT
    # ==============================================================

    def _get_category_weight(
        self,
        category: str,
        profile_weight: float,
    ) -> float:

        return self.CATEGORY_WEIGHTS.get(
            category,
            float(profile_weight),
        )

    # ==============================================================
    # EVIDENCE STRENGTH
    # ==============================================================

    def _get_evidence_strength(
        self,
        keyword: str,
        title: str,
        skills: str,
        category: str,
        description: str,
    ) -> float:

        evidence = 0.0

        # Title is strongest evidence.
        if self._matches_keyword(keyword, title):
            evidence = max(
                evidence,
                self.TITLE_STRENGTH,
            )

        # Explicit skills are strong evidence.
        if self._matches_keyword(keyword, skills):
            evidence = max(
                evidence,
                self.SKILLS_STRENGTH,
            )

        # Category is moderate evidence.
        if self._matches_keyword(keyword, category):
            evidence = max(
                evidence,
                self.CATEGORY_STRENGTH,
            )

        # Description is supporting evidence only.
        if self._matches_keyword(keyword, description):
            evidence = max(
                evidence,
                self.DESCRIPTION_STRENGTH,
            )

        return evidence

    # ==============================================================
    # FRONTEND ROLE DETECTION
    # ==============================================================

    def _is_frontend_role(self, title: str) -> bool:
        """
        Determines whether the internship title explicitly represents
        a frontend/web-development role.
        """

        title_lower = title.lower()

        return any(
            self._matches_keyword(term, title_lower)
            for term in self.FRONTEND_ROLE_TERMS
        )

    # ==============================================================
    # MAIN MATCHING FUNCTION
    # ==============================================================

    def evaluate_internship(
        self,
        internship: Internship,
    ) -> Tuple[float, List[str]]:

        title = internship.title or ""
        description = internship.description or ""
        category = internship.category or ""

        skills_text = (
            " ".join(internship.skills)
            if internship.skills
            else ""
        )

        title_lower = title.lower()
        skills_lower = skills_text.lower()
        category_lower = category.lower()
        description_lower = description.lower()

        matched_skills: Set[str] = set()

        # ==========================================================
        # CATEGORY INFORMATION
        # ==========================================================

        category_scores: Dict[str, float] = {}

        # Every distinct matched keyword for every category.
        category_keywords: Dict[str, Set[str]] = {}

        # Keywords explicitly present in the internship's skills list.
        category_skill_keywords: Dict[str, Set[str]] = {}

        # Strong technical categories.
        strong_categories: Set[str] = set()

        # Strong/core categories found in title.
        title_core_categories: Set[str] = set()

        # ==========================================================
        # SCAN KEYWORDS
        # ==========================================================

        for keyword, info in self.keyword_map.items():

            category_name = info["category"]

            profile_weight = float(
                info["weight"]
            )

            display_name = info["display_name"]

            # ------------------------------------------------------
            # Evidence
            # ------------------------------------------------------

            evidence_strength = self._get_evidence_strength(
                keyword=keyword,
                title=title_lower,
                skills=skills_lower,
                category=category_lower,
                description=description_lower,
            )

            if evidence_strength <= 0:
                continue

            # ------------------------------------------------------
            # Keyword importance
            # ------------------------------------------------------

            keyword_multiplier = self._keyword_multiplier(
                keyword
            )

            # ------------------------------------------------------
            # Category importance
            # ------------------------------------------------------

            category_weight = self._get_category_weight(
                category_name,
                profile_weight,
            )

            normalized_category_weight = min(
                category_weight / 10.0,
                1.0,
            )

            # ------------------------------------------------------
            # Evidence score
            # ------------------------------------------------------

            evidence_score = (
                normalized_category_weight
                * evidence_strength
                * keyword_multiplier
            )

            # ------------------------------------------------------
            # Save strongest evidence for category
            # ------------------------------------------------------

            previous = category_scores.get(
                category_name,
                0.0,
            )

            category_scores[category_name] = max(
                previous,
                evidence_score,
            )

            # ------------------------------------------------------
            # Store distinct keyword
            # ------------------------------------------------------

            if category_name not in category_keywords:
                category_keywords[category_name] = set()

            category_keywords[
                category_name
            ].add(keyword.lower())

            # ------------------------------------------------------
            # Store explicit skill keywords separately
            # ------------------------------------------------------

            if self._matches_keyword(
                keyword,
                skills_lower,
            ):
                if category_name not in category_skill_keywords:
                    category_skill_keywords[category_name] = set()

                category_skill_keywords[
                    category_name
                ].add(keyword.lower())

            # ------------------------------------------------------
            # Matched skill
            # ------------------------------------------------------

            matched_skills.add(
                display_name
            )

            # ------------------------------------------------------
            # Strong category
            # ------------------------------------------------------

            normalized_keyword = keyword.strip().lower()

            if normalized_keyword in self.STRONG_KEYWORDS:

                strong_categories.add(
                    category_name
                )

                if self._matches_keyword(
                    keyword,
                    title_lower,
                ):
                    title_core_categories.add(
                        category_name
                    )

        # ==========================================================
        # NO MATCH
        # ==========================================================

        if not category_scores:
            return 0.0, []

        # ==========================================================
        # CATEGORY CONTRIBUTIONS
        # ==========================================================

        category_contributions: Dict[str, float] = {}

        for category_name, evidence in category_scores.items():

            cap = self.CATEGORY_CAPS.get(
                category_name,
                12.0,
            )

            # ------------------------------------------------------
            # Main category contribution
            # ------------------------------------------------------

            contribution = evidence * cap

            contribution = min(
                contribution,
                cap,
            )

            # ------------------------------------------------------
            # Distinct technology bonus
            # ------------------------------------------------------

            keywords = category_keywords.get(
                category_name,
                set(),
            )

            additional_count = max(
                0,
                len(keywords) - 1,
            )

            additional_count = min(
                additional_count,
                self.MAX_ADDITIONAL_KEYWORDS,
            )

            contribution += (
                additional_count
                * self.ADDITIONAL_KEYWORD_BONUS
            )

            # ------------------------------------------------------
            # Frontend skill breadth
            # ------------------------------------------------------

            if category_name == "frontend":

                explicit_frontend_skills = (
                    category_skill_keywords.get(
                        "frontend",
                        set(),
                    )
                    & self.FRONTEND_KEYWORDS
                )

                # React + JavaScript + HTML + CSS
                # should score considerably higher than React alone.
                breadth_count = min(
                    len(explicit_frontend_skills),
                    4,
                )

                if breadth_count >= 2:
                    contribution += (
                        breadth_count
                        * self.FRONTEND_BREADTH_BONUS
                    )

                # Explicit frontend role in title.
                if self._is_frontend_role(title_lower):
                    contribution += self.FRONTEND_ROLE_BONUS

            # ------------------------------------------------------
            # Hard category cap
            # ------------------------------------------------------

            contribution = min(
                contribution,
                cap,
            )

            category_contributions[
                category_name
            ] = contribution

        # ==========================================================
        # STRONGEST CATEGORIES
        # ==========================================================

        sorted_categories = sorted(
            category_contributions.items(),
            key=lambda item: item[1],
            reverse=True,
        )

        # Only the strongest five areas contribute.
        top_categories = sorted_categories[:5]

        base_score = sum(
            score
            for _, score in top_categories
        )

        # ==========================================================
        # STRONG TECHNICAL AREA BONUS
        # ==========================================================

        strong_count = len(
            strong_categories
        )

        if strong_count >= 3:
            strong_bonus = 15.0

        elif strong_count == 2:
            strong_bonus = 10.0

        elif strong_count == 1:
            strong_bonus = 5.0

        else:
            strong_bonus = 0.0

        # ==========================================================
        # TITLE BONUS
        # ==========================================================

        title_core_count = len(
            title_core_categories
        )

        if title_core_count >= 3:
            title_bonus = 15.0

        elif title_core_count == 2:
            title_bonus = 12.0

        elif title_core_count == 1:
            title_bonus = 10.0

        else:
            title_bonus = 0.0

        # ==========================================================
        # GENERIC-ONLY HANDLING
        # ==========================================================

        if not strong_categories:

            generic_categories = {
                "python",
                "software_engineering",
                "frontend",
                "sql",
                "java",
            }

            only_generic = all(
                category_name in generic_categories
                for category_name, _ in top_categories
            )

            # Only penalize extremely weak generic matches.
            if only_generic and base_score < 12.0:
                base_score *= 0.75

        # ==========================================================
        # FINAL SCORE
        # ==========================================================

        final_score = (
            base_score
            + strong_bonus
            + title_bonus
        )

        final_score = min(
            round(final_score, 1),
            100.0,
        )

        # ==========================================================
        # SORT MATCHED SKILLS
        # ==========================================================

        matched_skills_list = sorted(
            matched_skills,
            key=lambda value: value.lower(),
        )

        return (
            final_score,
            matched_skills_list,
        )