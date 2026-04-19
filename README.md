# Empirical SE Investigation System

> A Flask web application for designing, tracking, and analysing software engineering
> investigations — built directly from the **SENG 421: Software Metrics, Chapter 4**
> framework by **B.H. Far, University of Calgary**.

---

## Table of Contents

1. [Overview](#overview)
2. [Chapter 4 Concepts Implemented](#chapter-4-concepts-implemented)
3. [Project Structure](#project-structure)
4. [Quick Start](#quick-start)
5. [Running with Docker / Gunicorn](#running-with-docker--gunicorn)
6. [Database Models](#database-models)
7. [API Endpoints](#api-endpoints)
8. [NRC-CNRC Guideline Coverage](#nrc-cnrc-guideline-coverage)
9. [Environment Variables](#environment-variables)
10. [Tech Stack](#tech-stack)

---

## Overview

This system implements the empirical investigation lifecycle described in Chapter 4:

```
Hypothesis → Technique Selection → Variable Control → Data Collection
     → Analysis → Presentation → Interpretation → Feedback loop
```

It supports all three SE investigation techniques:

| Technique | Description | Chapter 4 Reference |
|-----------|-------------|----------------------|
| **Formal Experiment** | Controlled investigation — research in the small | p. 17, 20 |
| **Case Study** | Documenting a real activity — research in the typical | p. 17, 21 |
| **Survey** | Retrospective across many projects — investigate in the large | p. 17, 22 |

---

## Chapter 4 Concepts Implemented

### SE Investigation (Why / What / Where / When / How)
- **Purpose** choices: Improve, Evaluate, Prove, Disprove, Understand, Compare (slide 6)
- **What** is being measured: person performance, tool usability, program complexity, etc. (slide 7)
- **Where**: field, lab, classroom (slide 8)
- **How**: hypothesis → data collection → evaluation → interpretation → iterative feedback (slide 9)

### Data Sources (First / Second / Third Degree Contact)
- Data points are collected per subject with optional treatment group and block group fields,
  mirroring First Degree (direct participant) and Third Degree (artifact analysis) contacts.

### Investigation Principles
1. **Stating the Hypothesis** — required field, stated prior to study (C2 guideline)
2. **Selecting Investigation Technique** — formal experiment / case study / survey
3. **Maintaining Control over Variables** — independent, dependent, confounding variables;
   causal ordering diagram: `{Independent} ⇒ {Confounding} ⇒ {Dependent}` (Control /3, slide 26)
4. **Making Meaningful Investigation** — results store statistical significance and practical importance

### Formal Experiment Planning Stages (slide 27–28)
The stage tracker on each investigation page shows progression through:
`Conception → Design → Preparation → Execution → Review & Analysis → Dissemination`

### Formal Experiment Principles (slide 29–32)
- **Replication**: multiple data points per variable
- **Randomisation / Blocking**: `block_group` field on each data point
- **Balancing**: assign equal subjects per treatment via the UI
- **Correlation**: summary statistics (mean, min, max) per variable via the API

### Factorial Design (slide 33)
- Variables with crossing/nesting can be entered as separate independent variables
  with treatment group labels representing factor levels.

### Baselines (slide 36)
- The data summary API (`/api/investigations/<id>/summary`) computes mean per variable,
  which can serve as a baseline reference.

---

## Project Structure

```
empirical_investigation/
├── app.py                          # Main Flask application — all models, routes, helpers
├── requirements.txt                # Python dependencies
├── .gitignore
├── README.md
└── templates/
    ├── base.html                   # Navigation, CSS, flash messages
    ├── index.html                  # Landing page
    ├── login.html                  # Authentication
    ├── register.html
    ├── dashboard.html              # Investigation list + stats
    ├── investigation_form.html     # Create / edit investigation
    └── investigation_detail.html   # Full detail: variables, data, results
```

---

## Quick Start

### 1. Clone & set up a virtual environment

```bash
git clone <repo-url>
cd empirical_investigation

python3 -m venv venv
source venv/bin/activate        # Windows: venv\Scripts\activate
pip install -r requirements.txt
```

### 2. Run in development mode

```bash
python app.py
```

The server starts at **http://localhost:5000**.

A demo account is auto-created on first run:
- **Username**: `demo`
- **Password**: `demo1234`

### 3. Open in browser

Navigate to `http://localhost:5000`, log in, and create your first investigation.

---

## Running with Docker / Gunicorn

### Gunicorn (production)

```bash
gunicorn -w 4 -b 0.0.0.0:8000 "app:app"
```

Call `create_tables()` before starting the worker in a production setup:

```python
# wsgi.py
from app import app, create_tables
create_tables()
```

### PostgreSQL

Set the `DATABASE_URL` environment variable:

```bash
export DATABASE_URL="postgresql://user:password@localhost:5432/empirical_db"
```

---

## Database Models

### `User`
| Column | Type | Notes |
|--------|------|-------|
| id | Integer PK | |
| username | String(80) | unique |
| email | String(120) | unique |
| password_hash | String(256) | Werkzeug PBKDF2 |
| created_at | DateTime | |

### `Investigation`
| Column | Type | Chapter 4 Mapping |
|--------|------|-------------------|
| title | String(200) | — |
| purpose | String(50) | SE Investigation: Why? (slide 6) |
| technique | String(50) | Investigation Techniques (slide 17) |
| context | String(50) | Where & When (slide 8) |
| hypothesis | Text | Hypothesis (slide 19), Guideline C2 |
| population | Text | Design Guideline D1 |
| selection_criteria | Text | Design Guideline D2 |
| assignment_process | Text | Design Guideline D3 |
| sample_size | Integer | Design Guideline D6 |
| outcome_measures | Text | Design Guideline D10 |
| status | String(30) | Planning stages (slide 27–28) |

### `Variable`
| Column | Type | Chapter 4 Mapping |
|--------|------|-------------------|
| name | String(100) | — |
| var_type | String(20) | independent / dependent / confounding (Control /1, slide 24) |
| unit | String(50) | Data Collection Guideline DC1 |
| description | Text | — |

### `DataPoint`
| Column | Type | Chapter 4 Mapping |
|--------|------|-------------------|
| subject_id | String(50) | Anonymised (ethics, slide 15) |
| variable_name | String(100) | DC1 |
| value | Float | — |
| treatment_group | String(100) | Factorial design (slide 33) |
| block_group | String(100) | Blocking & Balancing (slide 30–31) |
| dropped_out | Boolean | DC3 — record drop-outs |
| notes | Text | DC4 |

### `Result`
| Column | Type | Chapter 4 Mapping |
|--------|------|-------------------|
| finding | Text | Presentation Guideline P2 |
| statistical_significance | Float | Analysis Guideline A1; Guideline P2 |
| practical_importance | Text | Interpretation Guideline I2 |
| limitations | Text | Interpretation Guideline I3 |
| hypothesis_confirmed | Boolean | Hypothesis (slide 19) |

---

## API Endpoints

| Method | Route | Description |
|--------|-------|-------------|
| GET | `/api/investigations` | List all investigations (JSON) |
| GET | `/api/investigations/<id>/summary` | Stats summary: variable counts, data summary (mean/min/max per variable) |

**Example response** for `/api/investigations/1/summary`:

```json
{
  "id": 1,
  "title": "Agile vs Waterfall Defect Density",
  "technique": "formal_experiment",
  "status": "review",
  "variable_count": 3,
  "data_point_count": 24,
  "result_count": 1,
  "data_summary": {
    "defect_count": { "n": 12, "mean": 4.25, "min": 1.0, "max": 9.0 },
    "time_to_complete": { "n": 12, "mean": 18.4, "min": 10.0, "max": 30.0 }
  }
}
```

---

## NRC-CNRC Guideline Coverage

The system implements all six NRC-CNRC *Preliminary Guidelines for Empirical Research in
Software Engineering* (Kitchenham et al., 2001) — referenced on slide 37 of Chapter 4.

| # | Section | Guidelines | Where in App |
|---|---------|-----------|--------------|
| 1 | Experimental Context | C1, C2, C3 | Investigation form — context, hypothesis, description. Guideline reminders shown inline. |
| 2 | Experimental Design | D1–D10 | Design section of investigation form (population, selection, assignment, sample size, outcome measures). |
| 3 | Data Collection | DC1–DC4 | Data point form — variable name (DC1), notes (DC4), dropped_out checkbox (DC3). |
| 4 | Analysis | A1–A5 | Result form — p-value field (A1). Summary API supports sensitivity analysis data (A3). |
| 5 | Presentation of Results | P1–P5 | Result form — quantitative findings, p-value, practical importance. |
| 6 | Interpretation of Results | I1–I3 | Result form — practical importance (I2), limitations (I3), hypothesis confirmation (I1). |

---

## Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `SECRET_KEY` | `empirical-investigation-secret-key-2024` | Flask session key — **change in production** |
| `DATABASE_URL` | `sqlite:///empirical.db` | SQLAlchemy connection string |

---

## Tech Stack

| Component | Library |
|-----------|---------|
| Web framework | Flask 2.3.3 |
| ORM | Flask-SQLAlchemy 3.1.1 |
| Authentication | Flask-Login 0.6.2 |
| Password hashing | Werkzeug 2.3.7 |
| Production server | Gunicorn 21.2.0 |
| Database | SQLite (dev) / PostgreSQL (prod via psycopg2-binary) |

---

## References

- Far, B.H. *SENG 421: Software Metrics — Empirical Investigation (Chapter 4)*.
  Department of Electrical & Computer Engineering, University of Calgary.
- Kitchenham, B.A., Pfleeger, S.L., Pickard, L.M., Jones, P.W., Hoaglin, D.C.,
  El-Emam, K., and Rosenberg, J. (January 2001).
  *Preliminary Guidelines for Empirical Research in Software Engineering* (ERB-1082).
  NRC-CNRC Institute for Information Technology.
