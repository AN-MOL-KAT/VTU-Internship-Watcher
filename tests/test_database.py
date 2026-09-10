import os
import pytest
from src.database.database import Database
from src.database.models import Internship


@pytest.fixture
def temp_db(tmp_path):
    db_file = tmp_path / "test_internships.db"
    return Database(str(db_file))


def test_database_crud(temp_db):
    assert temp_db.is_internship_seen("101") is False

    item = Internship(
        portal_id="101",
        title="ML Engineer Intern",
        company="Tech Corp",
        skills=["Python", "PyTorch"],
        mode="Remote",
        internship_type="Stipend",
        stipend="₹20,000",
        fee=0.0,
        technical_score=92.0,
        priority_score=98.0,
        priority_level="VERY_HIGH",
    )

    row_id = temp_db.save_internship(item)
    assert row_id is not None
    assert temp_db.is_internship_seen("101") is True

    fetched = temp_db.get_internship_by_portal_id("101")
    assert fetched is not None
    assert fetched.title == "ML Engineer Intern"
    assert fetched.skills == ["Python", "PyTorch"]
    assert fetched.priority_level == "VERY_HIGH"


def test_notification_deduplication(temp_db):
    item = Internship(
        portal_id="202",
        title="CV Intern",
        company="Vision AI",
        priority_level="HIGH",
    )
    row_id = temp_db.save_internship(item)

    assert temp_db.is_notification_sent("202", "telegram") is False

    temp_db.record_notification(row_id, "202", "telegram")
    assert temp_db.is_notification_sent("202", "telegram") is True
    # Email should still be false
    assert temp_db.is_notification_sent("202", "email") is False


def test_database_stats(temp_db):
    temp_db.save_internship(
        Internship(portal_id="1", title="A", company="C", priority_level="VERY_HIGH")
    )
    temp_db.save_internship(
        Internship(portal_id="2", title="B", company="C", priority_level="HIGH")
    )
    temp_db.save_internship(
        Internship(portal_id="3", title="C", company="C", priority_level="IGNORE")
    )

    stats = temp_db.get_stats()
    assert stats["total_internships"] == 3
    assert stats["priority_counts"].get("VERY_HIGH") == 1
    assert stats["priority_counts"].get("HIGH") == 1
    assert stats["priority_counts"].get("IGNORE") == 1
