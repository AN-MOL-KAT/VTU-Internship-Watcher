from unittest.mock import Mock

from src.database.models import Internship
from src.monitoring.monitor import InternshipMonitor


def make_internship(
    portal_id="test-123",
    vacancy="10",
    status="OPEN",
    deadline="2026-09-30",
    fee=0.0,
    mode="Remote",
    stipend="₹15,000 / month",
):
    return Internship(
        portal_id=portal_id,
        title="Machine Learning Intern",
        company="AI Labs",
        description="Machine learning and Python development.",
        skills=[
            "Python",
            "Machine Learning",
            "Computer Vision",
        ],
        category="Artificial Intelligence",
        location="Bengaluru",
        mode=mode,
        internship_type="Stipend",
        fee=fee,
        stipend=stipend,
        duration="3 Months",
        vacancy=vacancy,
        application_status=status,
        deadline=deadline,
        url=f"mock://{portal_id}",
        technical_score=90.0,
        matched_skills=[
            "Python",
            "Machine Learning",
            "Computer Vision",
        ],
        priority_score=100.0,
        priority_level="VERY_HIGH",
    )


def test_vacancy_change_is_detected():
    monitor = InternshipMonitor()

    old = make_internship(vacancy="10")
    new = make_internship(vacancy="5")

    changes = monitor.detect_changes(old, new)

    assert "vacancy" in changes
    assert changes["vacancy"] == ("10", "5")


def test_open_to_closed_is_detected():
    monitor = InternshipMonitor()

    old = make_internship(status="OPEN")
    new = make_internship(status="CLOSED")

    changes = monitor.detect_changes(old, new)

    assert "application_status" in changes
    assert changes["application_status"] == (
        "OPEN",
        "CLOSED",
    )


def test_deadline_change_is_detected():
    monitor = InternshipMonitor()

    old = make_internship(
        deadline="2026-09-30"
    )

    new = make_internship(
        deadline="2026-10-05"
    )

    changes = monitor.detect_changes(old, new)

    assert "deadline" in changes
    assert changes["deadline"] == (
        "2026-09-30",
        "2026-10-05",
    )


def test_fee_change_is_detected():
    monitor = InternshipMonitor()

    old = make_internship(fee=999.0)
    new = make_internship(fee=1499.0)

    changes = monitor.detect_changes(old, new)

    assert "fee" in changes
    assert changes["fee"] == (
        "999.0000",
        "1499.0000",
    )


def test_mode_change_is_detected():
    monitor = InternshipMonitor()

    old = make_internship(mode="Remote")
    new = make_internship(mode="Hybrid")

    changes = monitor.detect_changes(old, new)

    assert "mode" in changes
    assert changes["mode"] == (
        "Remote",
        "Hybrid",
    )


def test_stipend_change_is_detected():
    monitor = InternshipMonitor()

    old = make_internship(
        stipend="₹10,000 / month"
    )

    new = make_internship(
        stipend="₹15,000 / month"
    )

    changes = monitor.detect_changes(old, new)

    assert "stipend" in changes
    assert changes["stipend"] == (
        "₹10,000 / month",
        "₹15,000 / month",
    )


def test_no_change_returns_empty_dictionary():
    monitor = InternshipMonitor()

    old = make_internship()
    new = make_internship()

    changes = monitor.detect_changes(old, new)

    assert changes == {}


def test_different_vacancy_events_have_different_keys():
    monitor = InternshipMonitor()

    first_change = {
        "vacancy": ("10", "5")
    }

    second_change = {
        "vacancy": ("5", "2")
    }

    key1 = monitor.build_event_key(
        "test-123",
        first_change,
    )

    key2 = monitor.build_event_key(
        "test-123",
        second_change,
    )

    assert key1 != key2


def test_same_event_has_same_key():
    monitor = InternshipMonitor()

    changes = {
        "vacancy": ("10", "5"),
        "application_status": (
            "OPEN",
            "CLOSED",
        ),
    }

    key1 = monitor.build_event_key(
        "test-123",
        changes,
    )

    key2 = monitor.build_event_key(
        "test-123",
        changes,
    )

    assert key1 == key2