import pytest
from src.database.models import Internship
from src.matching.skill_matcher import SkillMatcher
from src.matching.skill_profile import SkillProfile


@pytest.fixture
def matcher():
    return SkillMatcher()


def test_high_technical_match(matcher):
    item = Internship(
        portal_id="506",
        title="Machine Learning & Computer Vision Intern",
        company="AI Labs",
        skills=["Python", "Machine Learning", "OpenCV", "TensorFlow", "YOLO"],
        description="Develop deep learning computer vision models with Python and OpenCV.",
        category="Artificial Intelligence",
    )

    score, matched = matcher.evaluate_internship(item)
    assert score >= 85.0
    assert any("Python" in s for s in matched)
    assert any("Machine Learning" in s or "Ml" in s for s in matched)
    assert any("Computer Vision" in s or "Cv" in s for s in matched)


def test_unrelated_skill_zero_or_low_match(matcher):
    item = Internship(
        portal_id="510",
        title="Civil Structural Drafter",
        company="BuildCon Ltd",
        skills=["AutoCAD", "Surveying", "Concrete Design"],
        description="Drafting building layout plans and site inspection.",
        category="Civil Engineering",
    )

    score, matched = matcher.evaluate_internship(item)
    assert score == 0.0
    assert len(matched) == 0


def test_partial_frontend_match(matcher):
    item = Internship(
        portal_id="508",
        title="React Frontend Developer Intern",
        company="TechCorp",
        skills=["React", "JavaScript", "HTML", "CSS"],
        description="Build web user interfaces using React and modern JavaScript.",
        category="Web Development",
    )

    score, matched = matcher.evaluate_internship(item)
    assert 40.0 <= score <= 80.0
    assert any("React" in s for s in matched)
    assert any("Javascript" in s for s in matched)
