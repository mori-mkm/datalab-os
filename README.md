<div align="center">

# DataLab OS

### A local-first, hierarchical AI organization for Data Science

**From raw data to analysis, machine learning, independent review and final reporting — with the entire workflow visible in real time.**

<br>

![Status](https://img.shields.io/badge/status-PoC%20v0.2-success?style=for-the-badge)
![Python](https://img.shields.io/badge/Python-3.11%2B-blue?style=for-the-badge)
![LangGraph](https://img.shields.io/badge/orchestration-LangGraph-blueviolet?style=for-the-badge)
![Local First](https://img.shields.io/badge/Local--First-100%25-success?style=for-the-badge)
![API Cost](https://img.shields.io/badge/API%20Cost-%240-success?style=for-the-badge)
![GitHub Stars](https://img.shields.io/github/stars/mori-mkm/datalab-os?style=for-the-badge)

</div>

---

## What is DataLab OS?

**DataLab OS** is an experimental multi-agent system that models a Data Science team as a hierarchy of specialized agents.

Instead of using a single AI assistant, the workflow is divided into departments responsible for:

- Data Engineering
- Analytics
- Data Science
- Independent Review
- Reporting

The organization is executed by **LangGraph** and can be observed through two complementary interfaces:

- **Control Plane** — detailed live execution viewer built with Next.js + React Flow
- **Maestri Runtime Orchestra** — spatial terminal-based view of departments and runtime activity

> **Status:** Functional PoC validated end-to-end for tabular binary classification.

---

## Visual Agent Organization

```text
                 HEAD OF DATA SCIENCE
                         │
                         ▼
                DATA ENGINEERING
                ├── Engineering Lead
                ├── Data Profiler
                └── Quality Analyst
                         │
                         ▼
                    ANALYTICS
                ├── Analytics Lead
                ├── EDA Analyst
                └── Hypothesis Analyst
                         │
                         ▼
                  DATA SCIENCE
                ├── Data Science Lead
                ├── Baseline Modeler
                └── Model Evaluator
                         │
                         ▼
                       REVIEW
                         │
                         ▼
                       REPORT