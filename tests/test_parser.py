import pytest
from src.database.models import Internship
from src.parser.detail_parser import DetailParser
from src.parser.internship_parser import InternshipParser
from src.utils.helpers import (
    clean_text,
    format_currency,
    normalize_mode,
    normalize_type,
    parse_fee_amount,
)


def test_clean_text():
    raw = "  Hello \xa0 World\n\n  Engineering  "
    assert clean_text(raw) == "Hello World Engineering"
    assert clean_text(None) == ""


def test_parse_fee_amount():
    assert parse_fee_amount("₹3,999") == 3999.0
    assert parse_fee_amount("Rs. 1,500.00") == 1500.0
    assert parse_fee_amount("Free") == 0.0
    assert parse_fee_amount("Nil") == 0.0
    assert parse_fee_amount("0") == 0.0
    assert parse_fee_amount(None) == 0.0


def test_normalize_mode():
    assert normalize_mode("Work From Home / Online") == "Remote"
    assert normalize_mode("Virtual Mode") == "Remote"
    assert normalize_mode("Hybrid working model") == "Hybrid"
    assert normalize_mode("Onsite in Bengaluru office") == "Onsite"
    assert normalize_mode("") == "Unknown"


def test_normalize_type():
    assert normalize_type("Free", fee=0.0) == "Free"
    assert normalize_type("Paid", fee=3999.0) == "Paid"
    assert normalize_type("Stipendiary", fee=0.0, stipend="₹10,000") == "Stipend"
    assert normalize_type("Training", fee=1200.0) == "Paid"


def test_internship_card_parsing():
    sample_html = """
    <div class="card internship-card" data-id="506">
        <h4 class="card-title"><a href="/internship/506">Gen AI with Python Program</a></h4>
        <div class="company">QSpiders Global</div>
        <p class="details">
            Location: Remote | Mode: Online | Fee: Free | Stipend: ₹15,000 / month | Duration: 3 Months
        </p>
        <span class="deadline">Deadline: 2026-09-30</span>
    </div>
    """
    parser = InternshipParser()
    results = parser.parse_cards_html(sample_html)

    assert len(results) == 1
    item = results[0]
    assert item.portal_id == "506"
    assert "Gen AI with Python" in item.title
    assert "QSpiders" in item.company
    assert item.mode == "Remote"
    assert item.internship_type == "Stipend"
    assert item.fee == 0.0


def test_detail_enrichment():
    base_item = Internship(
        portal_id="506",
        title="Gen AI Intern",
        company="QSpiders",
        url="https://internship.vtu.ac.in/internship/506",
    )

    detail_html = """
    <div class="container">
        <h1>Gen AI Intern at QSpiders</h1>
        <div class="skills-section">
            <h3>Skills Required</h3>
            <span class="badge">Python</span>
            <span class="badge">Machine Learning</span>
            <span class="badge">PyTorch</span>
            <span class="badge">OpenCV</span>
        </div>
        <div class="info">
            <p>Vacancies: 10</p>
            <p>Category: Artificial Intelligence</p>
            <p>Stipend: ₹15,000 / month</p>
            <a href="#" class="btn btn-primary">Apply Now</a>
        </div>
        <div class="description">
            Complete hands-on Generative AI project with Python and LLM prompt engineering.
        </div>
    </div>
    """
    detail_parser = DetailParser()
    enriched = detail_parser.enrich_internship(base_item, detail_html)

    assert "Python" in enriched.skills
    assert "Machine Learning" in enriched.skills
    assert "PyTorch" in enriched.skills
    assert "OpenCV" in enriched.skills
    assert enriched.vacancy == "10"
    assert enriched.application_status == "OPEN"
    assert enriched.category == "Artificial Intelligence"
    assert enriched.internship_type == "Stipend"
