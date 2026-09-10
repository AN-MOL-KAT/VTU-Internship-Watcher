from dataclasses import dataclass, field
from datetime import datetime
from typing import List, Optional


@dataclass
class Internship:
    portal_id: str
    title: str
    company: str
    description: str = ""
    skills: List[str] = field(default_factory=list)
    category: str = ""
    location: str = ""
    mode: str = "Onsite"  # Remote, Hybrid, Onsite
    internship_type: str = "Free"  # Stipend, Free, Paid
    fee: float = 0.0
    stipend: str = ""
    duration: str = ""
    vacancy: str = ""
    application_status: str = "OPEN"
    deadline: str = ""
    url: str = ""
    technical_score: float = 0.0
    matched_skills: List[str] = field(default_factory=list)
    priority_score: float = 0.0
    priority_level: str = "IGNORE"  # VERY_HIGH, HIGH, MEDIUM, LOW, IGNORE
    first_seen: str = field(
        default_factory=lambda: datetime.now().isoformat()
    )
    last_seen: str = field(
        default_factory=lambda: datetime.now().isoformat()
    )
    id: Optional[int] = None

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "portal_id": self.portal_id,
            "title": self.title,
            "company": self.company,
            "description": self.description,
            "skills": self.skills,
            "category": self.category,
            "location": self.location,
            "mode": self.mode,
            "internship_type": self.internship_type,
            "fee": self.fee,
            "stipend": self.stipend,
            "duration": self.duration,
            "vacancy": self.vacancy,
            "application_status": self.application_status,
            "deadline": self.deadline,
            "url": self.url,
            "technical_score": self.technical_score,
            "matched_skills": self.matched_skills,
            "priority_score": self.priority_score,
            "priority_level": self.priority_level,
            "first_seen": self.first_seen,
            "last_seen": self.last_seen,
        }


@dataclass
class Notification:
    internship_id: int
    portal_id: str
    notification_type: str  # telegram, email
    sent_at: str = field(
        default_factory=lambda: datetime.now().isoformat()
    )
    status: str = "SUCCESS"
    id: Optional[int] = None
