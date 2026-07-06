# Offgrid Minds Foundry Dashboard v1.2

Foundry is the internal Mission Control dashboard for the Offgrid Minds knowledge
factory. It reads real data from the Milestone 1–6 backend in
`internal_tools/ogm_milestone_001`.

Foundry is separate from the Pi5 app, iPhone app, and older control center MVPs.

## What Foundry Does

- Serves a local read-only dashboard UI
- Bootstraps a real North American Outdoor Expert Pack workspace
- Accepts manually submitted candidate sources via CSV import
- Runs Curator-001 evaluation from the CLI (no auto-approval)
- Records human approvals from the CLI
- Vaults approved local-file candidates and bridges them to repository evidence
- Shows real missions, coverage objects, CRS requirements, queue counts, vault counts, and audit events
- Does not crawl, auto-approve, auto-vault, publish, or compile packs

## Step-By-Step Real Source Workflow

### 1. Bootstrap the workspace

From the repository root:

```bash
python3 -m internal_tools.ogm_foundry.bootstrap_workspace
```

This creates:

- Pack: `ogm.pack.north-american-outdoor`
- Coverage objects: Trees, Mushrooms, Camp Stoves, Water Purification, Weather Hazards, Navigation Basics
- Canonical Reference Standard requirements for each topic
- One active mission per coverage object

It does **not** create sources, approvals, vault records, knowledge objects, or fake activity.

Safety:

```bash
# Add missing records without deleting existing data
python3 -m internal_tools.ogm_foundry.bootstrap_workspace --force

# Delete and recreate the workspace (destructive)
python3 -m internal_tools.ogm_foundry.bootstrap_workspace --reset
```

Default workspace location:

```text
internal_tools/ogm_foundry/data/
  intake.db
  repository.db
  vault/
  workspace.json
```

Override with:

```bash
OGM_FOUNDRY_ROOT="/path/to/workspace" python3 -m internal_tools.ogm_foundry.bootstrap_workspace
```

After bootstrap, the dashboard shows six missions, six coverage objects, CRS requirement counts, and zero vault/repository activity.

### 2. Copy the candidate CSV template

```bash
cp internal_tools/ogm_foundry/templates/candidates.csv /path/to/my-candidates.csv
```

Required columns:

- `title`
- `publisher`
- `source_type`
- `mission_id`
- `coverage_object_id`
- `proposed_canonical_reference_type`
- `submitted_by`

Each row must include either `url` or `local_file_path`.

Optional columns:

- `license_status`
- `license_notes`
- `authority_score`
- `authority_reason`
- `risk_notes`
- `notes`

Mission and coverage IDs are written to `workspace.json` after bootstrap.

### 3. Add a real candidate row

Edit the CSV with a real source you control or have rights to review. Example for Trees:

```csv
title,publisher,url,local_file_path,source_type,mission_id,coverage_object_id,proposed_canonical_reference_type,submitted_by,license_status,license_notes,authority_score,authority_reason,risk_notes,notes
USFS Red Maple Guide,United States Forest Service,,/path/to/usfs-trees.txt,government,<mission_id>,<coverage_object_id>,government_publication,human:researcher:001,public_domain_or_government_work,To be verified manually.,0.95,Government forestry publisher.,,Real candidate for intake.
```

Use the mission and coverage object IDs from `workspace.json`.

### 4. Import candidates

```bash
python3 -m internal_tools.ogm_foundry.import_candidates /path/to/my-candidates.csv
```

Import behavior:

- validates required fields
- submits rows into `CandidateIntakeQueue`
- uses existing duplicate detection
- does not download URLs
- does not create human approvals
- does not vault sources automatically

Dry run:

```bash
python3 -m internal_tools.ogm_foundry.import_candidates /path/to/my-candidates.csv --dry-run
```

After import, the dashboard candidate queue shows `submitted` count increase and the candidate table lists the new row.

### 5. Evaluate candidates with Curator-001

```bash
python3 -m internal_tools.ogm_foundry.evaluate_candidates
```

Optional filters:

```bash
python3 -m internal_tools.ogm_foundry.evaluate_candidates --mission-id <mission_id>
python3 -m internal_tools.ogm_foundry.evaluate_candidates --coverage-object-id <coverage_object_id>
python3 -m internal_tools.ogm_foundry.evaluate_candidates --candidate-id <candidate_id>
```

This:

- loads submitted candidates
- runs Curator-001 evaluation using existing logic
- creates curator recommendations
- updates candidate status to `recommended` or `rejected`
- preserves review/audit history
- does **not** approve or vault anything automatically

After evaluation, the dashboard shows recommended/rejected counts and recent review events.

### 6. Approve a recommended candidate

```bash
python3 -m internal_tools.ogm_foundry.approve_candidate <candidate_id> \
  --actor Andrew \
  --notes "Approved as authoritative government forestry reference"
```

This:

- requires an existing curator recommendation
- creates a human approval record
- updates candidate status to `approved_for_intake`
- requires actor/reviewer name and approval notes
- preserves review/audit history

After approval, the dashboard shows `approved_for_intake` count and the candidate appears in the approved-waiting-for-vault list.

### 7. Intake an approved candidate (vault + repository bridge)

```bash
python3 -m internal_tools.ogm_foundry.intake_approved_candidate <candidate_id>
```

This:

- requires candidate status `approved_for_intake`
- requires human approval
- requires a valid `local_file_path` (URL-only candidates cannot be vaulted)
- archives the file into Raw Source Vault
- creates intake ledger records
- bridges to repository evidence via `approved_candidate_to_repository_evidence`
- links evidence to the coverage object
- runs CRS evaluation for the coverage object
- returns `source_uuid`, `revision_uuid`, and `evidence_uuid`
- preserves audit/ACP events where available

After intake, the dashboard shows vault source count, evidence count, updated coverage percentages, and recent vault/repository events.

### 8. Check workspace status

```bash
python3 -m internal_tools.ogm_foundry.workspace_status
```

JSON output:

```bash
python3 -m internal_tools.ogm_foundry.workspace_status --json
```

Prints missions count, coverage objects, CRS requirements, candidates by status, recommendations, approvals, vault sources, evidence, coverage percentages, and next recommended manual actions.

### 9. Refresh the dashboard

```bash
python3 -m internal_tools.ogm_foundry.server
```

Open:

```text
http://127.0.0.1:8790/
```

After the full workflow, verify:

- CRS requirements per coverage object (including missing CRS labels)
- candidate statuses in the queue table
- recommended candidates count
- approved candidates waiting for vault intake
- coverage percentages increased for the intaken topic
- recent candidate review events
- recent vault/repository events

## Run The Dashboard

```bash
python3 -m internal_tools.ogm_foundry.server
```

The dashboard is read-only. Approve and intake actions are CLI-only in v1.2.

## API Endpoints

| Endpoint | Description |
|---|---|
| `/api/dashboard/summary` | Combined dashboard payload |
| `/api/health` | Backend availability |
| `/api/missions` | Mission records |
| `/api/coverage` | Coverage objects |
| `/api/coverage/requirements` | CRS requirements by coverage object (including missing CRS) |
| `/api/candidates/counts` | Candidate queue counts |
| `/api/candidates` | Candidate list with statuses |
| `/api/repository/counts` | Repository counts |
| `/api/vault/counts` | Vault counts |
| `/api/curator/status` | Curator recommendation/approval counts |
| `/api/events/recent?limit=20` | Recent audit/review events |

## CLI Commands Summary

| Command | Purpose |
|---|---|
| `bootstrap_workspace` | Initialize real North American Outdoor workspace |
| `import_candidates <csv>` | Import manual candidate rows |
| `evaluate_candidates` | Run Curator-001 on submitted candidates |
| `approve_candidate <id> --actor --notes` | Record human approval |
| `intake_approved_candidate <id>` | Vault local file and bridge to repository |
| `workspace_status` | Print counts, coverage, and next actions |
| `server` | Serve read-only dashboard |

## Current Limitations

- Read-only dashboard (no edit/approve buttons in the web UI)
- No login/auth
- No browser upload UI
- CSV import is CLI-only
- URL-only candidates remain in the queue until a local file is available for vault intake
- Curator-001 evaluation is CLI-triggered, not automatic
- No OCR, embeddings, pack compilation, or autonomous crawling
- License strict review is optional (`strict_license_review=False` by default in intake CLI)

## Next Recommended Milestone

Foundry v1.3 should add:

- candidate detail pages in the dashboard
- mission detail pages with linked CRS requirements
- browser-based review UI with explicit approve/reject actions (still human-gated)
- workspace manifest panel with bootstrap metadata and file paths

## Tests

```bash
python3 -m unittest discover -s internal_tools/ogm_foundry/tests -v
python3 -m unittest discover -s internal_tools/ogm_milestone_001/tests -v
```
