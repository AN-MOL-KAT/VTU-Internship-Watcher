import pytest
from src.database.models import Internship
from src.matching.priority_scorer import PriorityScorer


@pytest.fixture
def scorer():
    return PriorityScorer()


def test_paid_internship_above_limit_is_ignored(scorer):
    item = Internship(
        portal_id="509",
        title="Data Science Paid Course Intern",
        company="EduAcademy",
        internship_type="Paid",
        fee=3999.0,
        mode="Remote",
        technical_score=95.0,
    )

    should_ignore, reason = scorer.should_ignore(item)
    assert should_ignore is True
    assert "exceeds limit" in reason

    score, level = scorer.calculate_priority(item)
    assert level == "IGNORE"
    assert score == 0.0


def test_stipend_remote_is_very_high_priority(scorer):
    item = Internship(
        portal_id="506",
        title="Gen AI Intern",
        company="QSpiders",
        internship_type="Stipend",
        stipend="₹15,000 / month",
        mode="Remote",
        fee=0.0,
        technical_score=90.0,
    )

    score, level = scorer.calculate_priority(item)
    assert level == "VERY_HIGH"
    assert score >= 90.0


def test_stipend_hybrid_is_high_or_very_high(scorer):
    item = Internship(
        portal_id="511",
        title="AI Research Intern",
        company="VTU Centre",
        internship_type="Stipend",
        stipend="₹10,000",
        mode="Hybrid",
        fee=0.0,
        technical_score=80.0,
    )

    score, level = scorer.calculate_priority(item)
    assert level in ["VERY_HIGH", "HIGH"]


def test_free_remote_priority(scorer):
    item = Internship(
        portal_id="508",
        title="Full Stack Intern",
        company="Startup",
        internship_type="Free",
        mode="Remote",
        fee=0.0,
        technical_score=75.0,
    )

    score, level = scorer.calculate_priority(item)
    assert level == "HIGH"


def test_affordable_paid_internship_is_low(scorer):
    item = Internship(
        portal_id="512",
        title="Python Project Internship",
        company="SkillBuild",
        internship_type="Paid",
        mode="Remote",
        fee=1200.0,
        technical_score=70.0,
    )

    score, level = scorer.calculate_priority(item)
    assert level == "LOW"


def test_below_technical_threshold_is_ignored(scorer):
    item = Internship(
        portal_id="510",
        title="Random Field Intern",
        company="Generic",
        internship_type="Stipend",
        mode="Remote",
        fee=0.0,
        technical_score=30.0,  # Below threshold 50%
    )

    score, level = scorer.calculate_priority(item)
    assert level == "IGNORE"
