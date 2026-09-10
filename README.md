# VTU Internship Watcher

An automated internship monitoring and notification system for the VTU Internyet internship portal.

VTU Internship Watcher continuously monitors available internships, extracts internship information from the dynamically rendered portal, matches opportunities against a configurable technical skill profile, ranks them according to internship type, mode, stipend/fee, and technical relevance, detects important changes, and sends Telegram notifications for relevant opportunities.

The system is designed for **internship discovery and monitoring only**. It does not automatically apply for internships or attempt to bypass CAPTCHA, authentication, or other portal protections.

---

## Table of Contents

* [Overview](#overview)
* [Key Features](#key-features)
* [How It Works](#how-it-works)
* [Project Architecture](#project-architecture)
* [Project Structure](#project-structure)
* [Technology Stack](#technology-stack)
* [Internship Preference System](#internship-preference-system)
* [Technical Skill Matching](#technical-skill-matching)
* [Priority Scoring](#priority-scoring)
* [Change Detection](#change-detection)
* [Telegram Notifications](#telegram-notifications)
* [Database](#database)
* [Configuration](#configuration)
* [Installation](#installation)
* [Environment Variables](#environment-variables)
* [Running the Application](#running-the-application)
* [Command-Line Options](#command-line-options)
* [Testing](#testing)
* [Windows Task Scheduler Automation](#windows-task-scheduler-automation)
* [Monitoring Workflow](#monitoring-workflow)
* [Example Output](#example-output)
* [Logging](#logging)
* [Security](#security)
* [Current Implementation Status](#current-implementation-status)
* [Limitations](#limitations)
* [Future Improvements](#future-improvements)
* [Author](#author)

---

## Overview

Finding suitable internships through a large internship portal can require repeatedly checking listings, comparing technical requirements, identifying newly added opportunities, and determining whether an internship is worth applying for.

VTU Internship Watcher automates this monitoring process.

The system connects to the VTU Internyet internship portal:

`https://vtu.internyet.in/internships`

It uses browser-based rendering to access dynamically loaded internship information and processes the collected data through a multi-stage pipeline.

### Main objectives

1. Monitor the VTU internship portal automatically.
2. Detect newly available internships.
3. Extract internship details such as:

   * Title
   * Company
   * Internship type
   * Internship mode
   * Fee
   * Stipend
   * Location
   * Duration
   * Deadline
   * Vacancy information
   * Application status
   * Technical skills
4. Match internships against a configurable technical skill profile.
5. Calculate a technical relevance score.
6. Apply internship-type and fee constraints.
7. Rank opportunities according to user-defined priorities.
8. Detect important changes to existing internships.
9. Avoid duplicate notifications.
10. Send relevant alerts through Telegram.
11. Run continuously in the background using Windows Task Scheduler.

---

# Key Features

## 1. Dynamic Portal Scraping

The VTU Internyet portal is dynamically rendered using React.

Instead of relying only on the initial HTML response, the project uses browser rendering to load the actual internship listings.

Playwright is used to:

* Launch Chromium
* Open the internship portal
* Wait for the page to render
* Extract rendered internship information
* Follow internship detail pages when required

This makes the collector suitable for a JavaScript-rendered portal.

---

## 2. Internship Data Extraction

The parser extracts and normalizes information from internship cards and detail pages.

Typical information includes:

| Field              | Description                                       |
| ------------------ | ------------------------------------------------- |
| Portal ID          | Unique identifier derived from the internship URL |
| Title              | Internship title                                  |
| Company            | Organization offering the internship              |
| Internship Type    | Free, Paid, or Stipend                            |
| Mode               | Remote, Hybrid, or Onsite                         |
| Location           | Internship location                               |
| Duration           | Internship duration                               |
| Fee                | Internship fee                                    |
| Stipend            | Stipend information                               |
| Deadline           | Application deadline                              |
| Vacancy            | Available vacancy information                     |
| Application Status | Open/closed or available status                   |
| Skills             | Technical skills associated with the internship   |
| Description        | Internship description                            |
| URL                | Portal internship page                            |

The parser also handles cases where the portal uses different URL structures.

---

## 3. New Internship Detection

Each internship is stored in a local SQLite database.

When a monitoring cycle runs, the system compares the newly collected internships against previously stored records.

If an internship has not been seen before, it is classified as a new internship.

This prevents the same internship from being treated as a new opportunity during every monitoring cycle.

---

## 4. Technical Skill Matching

The system evaluates each internship against a configurable skill profile.

Current skill categories include:

* Machine Learning
* Artificial Intelligence
* Python
* Computer Vision
* NLP
* Data Science
* Full Stack Development
* Frontend Development
* Data Analytics
* Software Engineering
* SQL
* Java

The skill profile is stored in:

```text
config/skills.yaml
```

The matching engine considers evidence from multiple parts of an internship listing, including:

* Title
* Listed skills
* Category
* Description

Stronger evidence receives greater importance than weak contextual mentions.

---

## 5. Internship Priority Ranking

Technical relevance alone is not sufficient.

For example, an internship can have a high technical match but still be undesirable if it requires a large fee.

The priority system therefore combines:

* Technical match
* Internship type
* Internship mode
* Stipend
* Fee

The system applies hard filters before assigning the final priority.

---

## 6. Fee Filtering

Paid internships above the configured maximum fee are automatically ignored.

Current maximum paid internship fee:

```text
₹1,500
```

Therefore:

```text
Paid + ₹3,999
```

is ignored regardless of technical relevance.

This prevents expensive internships from generating unnecessary alerts.

---

## 7. Internship Change Detection

The system does not only detect newly added internships.

It also monitors existing internships for important changes.

Tracked fields include:

* Vacancy
* Application status
* Deadline
* Fee
* Mode
* Stipend
* Internship type
* Location
* Duration

Examples of changes that can trigger an alert:

```text
Application status changed
Vacancy information changed
Deadline changed
Fee changed
Mode changed
Stipend changed
```

---

## 8. Duplicate Notification Prevention

The notification system generates an event-specific identifier for detected changes.

A hash is used to identify the specific change event.

This prevents repeated notifications for the exact same update.

For example, if an internship's application status changes from:

```text
Open
```

to:

```text
Closed
```

the system can notify the user once for that event instead of sending the same message during every monitoring cycle.

---

## 9. Telegram Alerts

Telegram is the primary notification channel.

The system supports:

* Test Telegram messages
* New internship alerts
* Important internship updates
* Priority-based notifications

Telegram credentials are stored in `.env` and are never committed to Git.

---

## 10. Local Database

SQLite is used for persistent storage.

The database stores internship information and notification/event state so that the watcher can continue monitoring without losing previous information between runs.

The database is intentionally excluded from Git.

---

## 11. Continuous Monitoring

The watcher can run continuously.

The default monitoring interval is:

```text
30 minutes
```

The system performs a monitoring cycle, processes the collected internships, waits for the configured interval, and then performs another cycle.

---

## 12. Windows Background Automation

The project can run automatically using Windows Task Scheduler.

The intended workflow is:

```text
Windows Startup
      |
      v
Task Scheduler
      |
      v
start_watcher.bat
      |
      v
python run.py --loop --interval 30
      |
      v
VTU Internship Watcher
      |
      v
VTU Internyet Portal
      |
      v
Parse -> Match -> Rank -> Detect Changes
      |
      v
SQLite Database
      |
      v
Telegram Alerts
```

This allows the watcher to operate without manually opening PowerShell.

---

# How It Works

The complete pipeline is divided into several stages.

```text
VTU Internyet Portal
        |
        v
Browser Collector
        |
        v
Rendered Internship Pages
        |
        v
Internship Parser
        |
        v
Normalized Internship Objects
        |
        +--------------------+
        |                    |
        v                    v
Skill Matcher          Database Lookup
        |                    |
        v                    v
Technical Score       New / Existing
        |                    |
        +---------+----------+
                  |
                  v
            Priority Scorer
                  |
                  v
          Change Detection
                  |
                  v
         Notification Filter
                  |
                  v
          Telegram Notifier
                  |
                  v
              User
```

---

# Project Architecture

The application is organized into independent modules.

## Collector Layer

Responsible for communicating with the VTU portal.

```text
src/collector/
├── browser.py
└── vtu_scraper.py
```

### `browser.py`

Provides browser-related functionality using Playwright.

Responsibilities include:

* Browser initialization
* Page loading
* Dynamic page rendering
* Browser lifecycle management

### `vtu_scraper.py`

Collects internship information from the VTU Internyet portal.

Responsibilities include:

* Portal connection
* Listing discovery
* Detail page discovery
* Retry handling
* Browser-based rendering
* Passing collected information to the parser

---

# Parser Layer

```text
src/parser/
├── internship_parser.py
└── detail_parser.py
```

## `internship_parser.py`

Converts portal content into normalized internship records.

The parser includes handling for:

* Dynamic card layouts
* Internship URLs
* Full slug-based identifiers
* Internship type detection
* Stipend detection
* Fee detection
* Metadata extraction
* Skills
* Description
* Fallback parsing

The project uses the full internship URL slug when available to avoid collisions caused by reused numeric prefixes.

---

## `detail_parser.py`

Processes information from internship detail pages and extracts additional metadata that may not be available directly from listing cards.

---

# Matching Layer

```text
src/matching/
├── skill_matcher.py
├── skill_profile.py
└── priority_scorer.py
```

## `skill_profile.py`

Loads the user's technical skill configuration from:

```text
config/skills.yaml
```

The profile is designed to be configurable without modifying Python source code.

---

## `skill_matcher.py`

Calculates technical relevance.

The matcher considers:

### Evidence sources

```text
Title
Skills
Category
Description
```

Title and explicit skill information receive stronger evidence weighting than generic description mentions.

### Skill strength

Keywords are categorized according to their relevance.

Strong technical keywords such as:

```text
Machine Learning
Deep Learning
Computer Vision
OpenCV
YOLO
NLP
Transformers
LLM
RAG
Generative AI
```

receive stronger treatment than generic terms such as:

```text
AI
ML
API
Git
Frontend
Backend
```

This helps prevent generic words from artificially producing very high scores.

---

# Priority Scoring

The priority scorer applies the user's internship preferences after calculating technical relevance.

## Priority Order

The preferred order is:

| Priority | Internship       |
| -------- | ---------------- |
| 1        | Stipend + Remote |
| 2        | Stipend + Hybrid |
| 3        | Stipend + Onsite |
| 4        | Free + Remote    |
| 5        | Free + Hybrid    |
| 6        | Free + Onsite    |
| 7        | Paid ≤ ₹1,500    |
| Ignore   | Paid > ₹1,500    |

Technical relevance is still considered when determining the final priority level.

---

## Hard Fee Rule

The maximum acceptable paid internship fee is configured in:

```text
config/config.yaml
```

Current value:

```yaml
max_paid_fee: 1500
```

Any paid internship above this amount is classified as:

```text
IGNORE
```

regardless of its technical match.

For example:

```text
Machine Learning Internship
Technical Match: 95%
Fee: ₹3,999
```

Result:

```text
Priority: IGNORE
```

---

# Configuration

## `config/config.yaml`

Contains general application configuration.

Important configuration includes:

```yaml
max_paid_fee: 1500
```

This value controls the maximum fee accepted for paid internships.

---

## `config/skills.yaml`

Contains the technical skill profile.

Example structure:

```yaml
skills:
  machine_learning:
    weight: 10
    keywords:
      - ML
      - Machine Learning
      - Deep Learning
      - Neural Networks
      - PyTorch
      - TensorFlow

  artificial_intelligence:
    weight: 10
    keywords:
      - Artificial Intelligence
      - AI
      - Generative AI
      - Gen AI
      - Prompt Engineering
      - RAG
      - LangChain

  python:
    weight: 8
    keywords:
      - Python
      - Python3
      - Pandas
      - NumPy
      - FastAPI
      - Flask

  computer_vision:
    weight: 10
    keywords:
      - Computer Vision
      - OpenCV
      - YOLO
      - YOLOv8
      - Object Detection
      - MediaPipe
```

The complete configuration contains additional categories for NLP, Data Science, Full Stack, Frontend, Data Analytics, Software Engineering, SQL, and Java.

---

# Technology Stack

| Technology             | Purpose                               |
| ---------------------- | ------------------------------------- |
| Python                 | Core application                      |
| Playwright             | Dynamic browser automation            |
| Chromium               | Portal rendering                      |
| SQLite                 | Persistent database                   |
| SQLAlchemy             | Database interaction                  |
| PyYAML                 | YAML configuration                    |
| Requests               | HTTP/API communication where required |
| Telegram Bot API       | Notifications                         |
| Pytest                 | Automated testing                     |
| Windows Task Scheduler | Background execution                  |
| Git/GitHub             | Version control                       |

---

# Project Structure

```text
VTU-Internship-Watcher/
│
├── config/
│   ├── config.yaml
│   └── skills.yaml
│
├── data/
│   └── internships.db
│
├── logs/
│   └── watcher.log
│
├── scripts/
│   └── test_portal.py
│
├── src/
│   ├── collector/
│   │   ├── browser.py
│   │   └── vtu_scraper.py
│   │
│   ├── database/
│   │   ├── database.py
│   │   └── models.py
│   │
│   ├── matching/
│   │   ├── priority_scorer.py
│   │   ├── skill_matcher.py
│   │   └── skill_profile.py
│   │
│   ├── monitoring/
│   │   └── monitor.py
│   │
│   ├── notifications/
│   │   ├── email.py
│   │   └── telegram.py
│   │
│   ├── parser/
│   │   ├── detail_parser.py
│   │   └── internship_parser.py
│   │
│   └── utils/
│       └── logger.py
│
├── tests/
│   ├── test_matcher.py
│   ├── test_parser.py
│   ├── test_scorer.py
│   └── test_scraper.py
│
├── .env
├── .env.example
├── .gitignore
├── requirements.txt
├── run.py
└── start_watcher.bat
```

---

# Installation

## 1. Clone the Repository

```bash
git clone https://github.com/AN-MOL-KAT/VTU-Internship-Watcher.git
cd VTU-Internship-Watcher
```

---

## 2. Install Python Dependencies

```bash
pip install -r requirements.txt
```

---

## 3. Install Playwright Chromium

```bash
playwright install chromium
```

The browser installation is required because the VTU portal is dynamically rendered.

---

# Environment Variables

Create a `.env` file in the project root.

Example:

```env
TELEGRAM_BOT_TOKEN=your_telegram_bot_token_here
TELEGRAM_CHAT_ID=your_telegram_chat_id_here

SMTP_HOST=smtp.gmail.com
SMTP_PORT=587
SMTP_USER=your_email@gmail.com
SMTP_PASS=your_app_password_here
EMAIL_RECEIVER=your_email@gmail.com

VTU_PORTAL_URL=https://vtu.internyet.in

VTU_USERNAME=
VTU_PASSWORD=
```

Do not commit `.env` to Git.

The repository includes:

```text
.env.example
```

as a safe configuration template.

---

# Running the Application

## Single Monitoring Cycle

A single cycle can be executed with:

```bash
python run.py --once
```

This is useful for testing.

---

## Continuous Monitoring

Run:

```bash
python run.py --loop --interval 30
```

This starts continuous monitoring with a 30-minute polling interval.

The watcher performs a scan and then waits before starting the next cycle.

---

## Dry Run

To test the monitoring pipeline without modifying persistent state or sending alerts:

```bash
python run.py --dry-run
```

Dry-run mode is useful when testing parser, matcher, and priority behavior.

---

## Telegram Test

To verify Telegram configuration:

```bash
python run.py --test-telegram
```

This sends a test message through the configured Telegram bot.

---

## Database Statistics

To inspect database statistics:

```bash
python run.py --stats
```

---

## List Stored Internships

To display stored internships sorted by priority:

```bash
python run.py --list
```

---

# Command-Line Options

| Option            | Description                                              |
| ----------------- | -------------------------------------------------------- |
| `--once`          | Run one monitoring cycle and exit                        |
| `--loop`          | Run continuous monitoring                                |
| `--interval`      | Monitoring interval in minutes                           |
| `--dry-run`       | Run without modifying persistent state or sending alerts |
| `--test-telegram` | Test Telegram configuration                              |
| `--stats`         | Display database statistics                              |
| `--list`          | Display stored internships                               |

Example:

```bash
python run.py --loop --interval 30
```

---

# Testing

The project uses Pytest.

Run all tests:

```bash
python -m pytest -q
```

Current project test suite:

```text
21 passed
```

The tests cover the major application components.

---

## Parser Tests

```bash
python -m pytest tests/test_parser.py -q
```

Parser tests verify:

* Internship ID extraction
* Internship type handling
* Stipend detection
* Parsed internship fields

---

## Scraper Tests

```bash
python -m pytest tests/test_scraper.py -q
```

Scraper tests verify:

* Mock listing behavior
* Failure behavior when mock fallback is disabled
* Scraper initialization

---

## Matcher Tests

```bash
python -m pytest tests/test_matcher.py -q
```

Matcher tests verify:

* High technical match
* Unrelated internship detection
* Partial frontend match

---

## Priority Scorer Tests

```bash
python -m pytest tests/test_scorer.py -q
```

Priority tests verify:

* Stipend internships
* Remote/hybrid/onsite priorities
* Free internships
* Affordable paid internships
* Paid internships above the ₹1,500 threshold

---

# Portal Testing

A dedicated portal test script is available:

```bash
python scripts/test_portal.py
```

This can be used to verify:

* Portal accessibility
* Browser rendering
* Internship listing extraction
* Current portal behavior

The VTU portal uses client-side rendering, so a basic HTTP request may return only the React application shell.

Playwright is therefore used to render the page before parsing.

---

# Windows Task Scheduler Automation

The watcher can be configured to start automatically with Windows.

## Launcher

The project contains:

```text
start_watcher.bat
```

The launcher changes into the project directory and starts:

```bash
python run.py --loop --interval 30
```

---

## Recommended Task Scheduler Configuration

Create a Windows Task Scheduler task named:

```text
VTU Internship Watcher
```

### General

Use:

```text
Run only when user is logged on
```

with:

```text
Run with highest privileges
```

This avoids requiring Task Scheduler to store the Windows account password while still allowing automatic startup after logging into Windows.

---

## Trigger

Use:

```text
At startup
```

The Python application itself handles the 30-minute monitoring interval.

Do not create a separate Task Scheduler trigger every 30 minutes.

---

## Action

Program:

```text
C:\Users\anmol\OneDrive\Desktop\VTU-Internship-Watcher\start_watcher.bat
```

Start in:

```text
C:\Users\anmol\OneDrive\Desktop\VTU-Internship-Watcher
```

---

## Recommended Settings

Enable:

```text
Allow task to be run on demand
```

Enable:

```text
Run task as soon as possible after a scheduled start is missed
```

For an already-running task:

```text
Do not start a new instance
```

For failure recovery:

```text
Restart every: 5 minutes
Attempt to restart up to: 3 times
```

---

# Monitoring Workflow

Each monitoring cycle follows this sequence:

```text
1. Start watcher
       |
2. Connect to VTU Internyet
       |
3. Render internship page using Playwright
       |
4. Discover internship listings
       |
5. Parse internship information
       |
6. Compare against database
       |
7. Identify new/existing internships
       |
8. Fetch detail information when necessary
       |
9. Calculate technical match score
       |
10. Apply fee and internship-type rules
       |
11. Calculate priority
       |
12. Detect important changes
       |
13. Determine whether notification is required
       |
14. Send Telegram notification
       |
15. Store current internship state
       |
16. Wait for next monitoring cycle
```

---

# Example Output

A normal monitoring cycle currently produces output similar to:

```text
========================================================
             VTU INTERNSHIP WATCHER
========================================================

Starting monitor...


✓ Portal connection successful
✓ Found 18 internships
✓ 0 new internships
✓ 6 relevant internships
✓ 0 high-priority internships
✓ 0 alerts sent

========================================================
```

The number of internships naturally changes as the portal changes.

---

# Example Priority Analysis

An internship might be processed as:

```text
Title:
Machine Learning and Computer Vision Intern

Technical Match:
92%

Type:
Stipend

Mode:
Remote

Priority:
VERY_HIGH
```

Whereas:

```text
Title:
Data Science + AI Integration Program

Technical Match:
69.7%

Type:
Paid

Fee:
₹3,999

Priority:
IGNORE
```

The second internship is ignored because:

```text
₹3,999 > ₹1,500
```

The fee rule therefore overrides its technical relevance.

---

# Database

The application uses SQLite for persistent storage.

Database location:

```text
data/internships.db
```

The database is ignored by Git using:

```text
*.db
*.sqlite3
data/*.db
```

This ensures that local monitoring state is not committed to the public repository.

The database allows the application to determine whether an internship has:

* Already been seen
* Already been notified
* Changed since the previous scan
* Received a particular update notification

---

# Logging

Application logs are stored in:

```text
logs/watcher.log
```

The log file is excluded from Git.

Logging helps diagnose:

* Portal connection failures
* Browser/rendering issues
* Parser failures
* Notification failures
* Database errors
* Monitoring-cycle errors

---

# Security

The project follows several security practices.

## Credentials

Sensitive credentials are stored in:

```text
.env
```

and `.env` is excluded from Git.

Never commit:

```text
TELEGRAM_BOT_TOKEN
SMTP_PASS
VTU_PASSWORD
```

to the repository.

---

## Telegram Bot Token

If a Telegram bot token is accidentally exposed publicly, it should be rotated immediately through Telegram's bot management interface.

Never place a real token inside:

```text
README.md
.env.example
source code
Git commits
screenshots
```

---

## Portal Interaction

This project is designed for monitoring and does not automate internship applications.

It should not be used to:

* Bypass CAPTCHA
* Circumvent authentication
* Bypass portal security
* Automatically submit internship applications
* Abuse portal rate limits

The watcher should operate at a reasonable polling interval.

---

# Current Implementation Status

## Completed

* [x] VTU Internyet portal integration
* [x] Dynamic browser rendering with Playwright
* [x] Internship listing collection
* [x] Internship detail parsing
* [x] Full internship URL/slug identification
* [x] Internship type detection
* [x] Stipend detection
* [x] Fee extraction
* [x] Skill extraction
* [x] Technical skill matching
* [x] Configurable skill profile
* [x] Technical relevance scoring
* [x] Priority scoring
* [x] ₹1,500 paid internship fee threshold
* [x] New internship detection
* [x] Existing internship monitoring
* [x] Change detection
* [x] Duplicate event prevention
* [x] SQLite persistence
* [x] Telegram notifications
* [x] Telegram testing
* [x] Dry-run mode
* [x] Portal diagnostic script
* [x] Automated Pytest suite
* [x] Windows batch launcher
* [x] Windows Task Scheduler integration
* [x] Git/GitHub repository setup

---

# Test Status

The current automated test suite passes:

```text
21 passed
```

This includes parser, scraper, matching, and priority-scoring tests.

The live portal has also been successfully tested with dynamically rendered listings.

A successful live monitoring cycle has produced:

```text
18 internships detected
6 relevant internships
0 high-priority internships
0 alerts sent
```

These values represent a particular portal state and can change as the portal is updated.

---

# Limitations

## 1. Portal Layout Changes

The scraper depends on the structure of the VTU Internyet website.

If the portal significantly changes:

* HTML structure
* CSS selectors
* URL structure
* React component structure
* Internship card layout

the parser may require updates.

---

## 2. Browser Dependency

Because the portal uses dynamic rendering, Playwright and Chromium are required.

A simple HTTP request may not contain the actual internship listings.

---

## 3. Portal Availability

Temporary portal outages, slow responses, network problems, or browser rendering failures can result in an unsuccessful monitoring cycle.

The watcher should not modify the database as if the portal contained zero internships when a collection failure occurs.

---

## 4. Vacancy Information

The portal's vacancy information may not always provide a separate structured applicant count.

Where the portal exposes vacancy-related information, the system tracks the available field.

---

## 5. No Automatic Applications

The system intentionally stops at:

```text
Discover
      ↓
Analyze
      ↓
Rank
      ↓
Notify
```

It does not continue to:

```text
Apply
```

This keeps the project focused on monitoring and opportunity discovery.

---

# Future Improvements

Potential future improvements include:

## Smarter Matching

* Semantic similarity using embeddings
* NLP-based internship description analysis
* Skill synonym detection
* Experience-level matching
* Project-to-internship relevance scoring

---

## Better Notifications

* Separate Telegram messages for:

  * New opportunities
  * Deadline changes
  * Vacancy changes
  * Application closure
  * High-priority internships
* Daily internship digest
* Morning opportunity summary
* Notification grouping

---

## Advanced Monitoring

* Detect internships removed from the portal
* Detect application reopening
* Track historical fee changes
* Track deadline extensions
* Maintain internship history
* Track company-level opportunities

---

## Analytics

Possible future dashboard metrics:

```text
Internships discovered
Relevant internships
High-priority internships
Ignored paid internships
Remote opportunities
Stipend opportunities
Companies monitored
Applications deadlines
Skill-match distribution
```

---

## Deployment

The project could eventually be deployed to:

* Cloud VM
* GitHub Actions
* Docker
* Lightweight server
* Always-on home server

A deployment should maintain persistent storage and securely manage environment variables.

---

# GitHub

Repository:

`https://github.com/AN-MOL-KAT/VTU-Internship-Watcher`

The repository contains the source code, configuration templates, tests, and documentation required to reproduce the project.

Sensitive runtime files such as `.env`, SQLite databases, logs, and virtual environments are excluded through `.gitignore`.

---

# Author

## Anmol Kathayat

Computer Science Engineering Student
Bengaluru, India

### Technical Interests

* Machine Learning
* Artificial Intelligence
* Computer Vision
* NLP
* Python
* Data Science
* Full Stack Development
* Automation
* Software Engineering

GitHub:

`https://github.com/AN-MOL-KAT`

LinkedIn:

`https://www.linkedin.com/in/anmol-kathayat-41ab63418/`

---

# License

This project is intended for educational, research, and personal internship-monitoring purposes.

Users are responsible for complying with the VTU Internyet portal's terms of use, applicable laws, and reasonable usage limits when operating the monitoring system.
