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
| Chosen AI Approach | Not decided yet |

## Module Tracking

Use one of these values: `Not started`, `In progress`, `Done`

| Module | What it should include | Status |
|---|---|---|
| M1 | Proof of Work Monitor | In progress |
| M2 | Block Header Analyzer | Not started |
| M3 | Difficulty History | Not started |
| M4 | AI Component | Not started |

## Current Progress

Write 3 to 5 short lines about what you have already done.

- Accepted the GitHub Classroom assignment and reviewed the repository template.
- Completed the initial README with the project information.
- Executed the first API call to retrieve real Bitcoin blockchain data.
- Printed the latest block height, hash, difficulty, nonce, number of transactions, and bits.

## Next Step

Write the next small step you will do before the next class.

- Improve the API script and start connecting the data to the M1 Proof of Work Monitor.

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
