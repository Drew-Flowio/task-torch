# OGM Agent Control Center MVP

Local Mission Control dashboard for Offgrid Minds.

This is a separate internal tool. It does not modify the Pi5 runtime, iPhone
app, Insight desktop app, research agents, pack compiler, or publishing flow.

## Run

From the repository root:

```bash
python3 -m internal_tools.ogm_control_center.app
```

Then open:

```text
http://127.0.0.1:8765
```

Optional environment variables:

```bash
OGM_CONTROL_CENTER_PORT=8770 python3 -m internal_tools.ogm_control_center.app
OGM_CONTROL_CENTER_DB=/tmp/ogm-control-center.db python3 -m internal_tools.ogm_control_center.app
```

## What Works

- Local web dashboard.
- SQLite database.
- Create and view missions.
- Edit mission status with human approval notes.
- Add source candidates manually.
- Approve or reject sources.
- Track source class, source quality, and relevance scores.
- Track coverage.
- Track Knowledge Debt.
- View mission events, approvals, CKO logs, and audit trail.
- Add manual placeholder CKO recommendations.

## What Is Intentionally Disabled

- Autonomous internet crawling.
- Research agents.
- Autonomous publishing.
- Expert Pack compilation.
- Automatic source approval.

Every official source and mission state decision in this MVP is human-entered
and audit logged.
