[![Review Assignment Due Date](https://classroom.github.com/assets/deadline-readme-button-22041afd0340ce965d47ae6ef1cefeee28c7c493a6346c4f15d667ab976d596c.svg)](https://classroom.github.com/a/N3kLi3ZO)
[![Open in Visual Studio Code](https://classroom.github.com/assets/open-in-vscode-2e0aaae1b6195c2367325f4f02e2d04e9abb55f0b24a779b69b11b9e10269abc.svg)](https://classroom.github.com/online_ide?assignment_repo_id=23640592&assignment_repo_type=AssignmentRepo)

# Blockchain Dashboard Project

Use this repository to build your blockchain dashboard project.  
Update this README every week.

## Student Information

| Field | Value |
|---|---|
| Student Name | CLAUDIA CORONA BLANCO |
| GitHub Username | claudiacorona065 |
| Project Title | Blockchain Dashboard |
| Chosen AI Approach | Anomaly detector for abnormal block inter-arrival times |

## Module Tracking

Use one of these values: `Not started`, `In progress`, `Done`

| Module | What it should include | Status |
|---|---|---|
| M1 | Proof of Work Monitor | Done |
| M2 | Block Header Analyzer | Done |
| M3 | Difficulty History | Done |
| M4 | AI Component | Done |
| M6 | Optional Security Score | Done |
## Current Progress

- Implemented M1, M2, M3 and M4 in the Streamlit dashboard.
- Added global automatic refresh with a 60-second polling interval.
- Implemented M4 as an anomaly detector for abnormal Bitcoin block inter-arrival times.
- Added optional M6 Security Score with 51% attack cost estimation.
- Added confirmation-depth risk visualisation based on Nakamoto's double-spend analysis.

## Next Step

- Prepare the final PDF report and perform final dashboard polish.

## Main Problem or Blocker

Write here if you are stuck with something.

- No blocker at the moment.

## How to Run

```bash
pip install -r requirements.txt
streamlit run app.py
```

## Project Structure

```text
blockchain-dashboard-claudiacorona065/
|-- README.md
|-- requirements.txt
|-- .gitignore
|-- app.py
|-- api/
|   |-- __init__.py
|   `-- blockchain_client.py
`-- modules/
    |-- __init__.py
    |-- m1_pow_monitor.py
    |-- m2_block_header.py
    |-- m3_difficulty_history.py
    `-- m4_ai_component.py

<!-- student-repo-auditor:teacher-feedback:start -->
## Teacher Feedback

### Kick-off Review

Review time: 2026-04-29 20:31 CEST
Status: Green

Strength:
- I can see the dashboard structure integrating the checkpoint modules.

Improve now:
- M1 still needs clearer evidence of a working Proof of Work monitor in the dashboard.

Next step:
- Turn M1 into a working dashboard view with live Proof of Work metrics, not just a placeholder.
<!-- student-repo-auditor:teacher-feedback:end -->
