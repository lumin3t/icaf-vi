# ICAF — Contributor's Guide

**Project:** ITSAR Compliance Automation Framework (ICAF)
**Location:** `icaf_1.6.5/`
**Engine:** Python (Typer CLI) + FastAPI web backend + React (Vite) frontend

> New to contributing on the **web stack only** (React UI / FastAPI / SQLite)?
> Read **[`CONTRIBUTING_WEB.md`](./CONTRIBUTING_WEB.md)** instead.

This guide covers (1) a summary of the changes made to the framework, (2) the
current project structure, (3) how the framework is wired, and (4) exactly what
must change when you add a new ITSAR clause.

---

## 1. Summary of Changes (internship work)

The framework started as a clause-based, terminal/CLI-only compliance tool. The
internship work extended it and built a GUI around it. Highlights, grouped by
area:

### 1.1 Compliance & test automation (Clause 1.2.1)

- **Extended the existing clause architecture** instead of building a new
  framework. The execution engine, runtime context, terminal management,
  evidence collection, and reporting infrastructure were all reused.
- **Implemented ITSAR Clause 1.2.1 — Authentication Policy** (Section 2 —
  Authentication Attribute Management) for IP routers.
- **Individual, reusable test cases** (not one monolith) covering:
  - SSH — no auth / correct auth / incorrect auth (`tc_4_*`, `tc_5_*`, `tc_6_*`)
  - SFTP — no auth / correct auth / incorrect auth (`tc_7_*`, `tc_8_*`, `tc_9_*`)
  - SCP — no auth / correct auth / incorrect auth (`tc_10_*`, `tc_11_*`, `tc_12_*`)
  - Console TCs (deferred, marked NOT APPLICABLE)
- **Success is verified through actual operations** (remote command execution for
  SSH, subsystem access + file ops for SFTP, real file transfer for SCP), not by
  authentication alone.
- **Temporary test-user lifecycle**: created on the DUT via an authenticated
  baseline SSH session, password set with `chpasswd`, and removed in `cleanup()`
  (`icaf/clauses/clause_1_2_1/clause.py`). Setup/cleanup failures are recorded
  as ERROR results instead of crashing the clause.
- **Standardized result pipeline** for the SSH-only clauses via
  `icaf/core/result_recorder.py` — `record_result()` / `get_results()` /
  `clear_results()`, with PASS / FAIL / ERROR / NOT-APPLICABLE verdicts mapped to
  testcase status.

### 1.2 Web platform (React + FastAPI + SQLite)

The CLI-driven tool was extended into a **GUI-driven compliance platform**:

- **FastAPI backend** in `icaf/web/api.py` exposing a local REST API.
- **SQLite persistence** in `icaf/web/storage.py` — `runs` + `evidence` tables,
  run creation/update/listing/detail, evidence metadata stored as JSON.
- **React frontend** in `webui/` — light-theme, componentized, with a reusable
  top navbar and three pages (Overview / New check / Run history).
- **Run lifecycle**: async/background execution, statuses `queued → running →
  completed | failed`, UTC ISO-8601 timestamps, failure messages persisted,
  unique run UUIDs.
- **Artifact management**: reports and evidence screenshots are copied into the
  run directory, registered in the DB, deduplicated, and served through a
  path-validated endpoint.
- **OAM integration**: optional Excel workbook upload (validated by extension,
  stored under `input/`, passed to the engine).
- **Serialization**: `RUN_LOCK` serializes runs because the terminal/screenshot
  facilities are process-wide.
- **Launcher**: `run_web.py` builds the frontend then starts Uvicorn on
  `127.0.0.1:8000`.

> Deep-dive (endpoints, DB schema, adding UI pages/components, dev workflow):
> see **[`CONTRIBUTING_WEB.md`](./CONTRIBUTING_WEB.md)**.

### 1.3 Additional clause integrations

- **Clause 1.9.3 (Credential-based Vulnerability Scanning)** wired end-to-end:
  registry loading, SSH-only engine handling, report factory routing, dedicated
  report class, API/UI selector presence, and ITSAR metadata in the runtime
  context.
- **Clause 1.1.3 (RBAC)** clause + 4 testcases (renamed to `tc_113_00N.py`) and
  its report class.
- **Clause 1.6.5** moved to `icaf/clauses/clause_1_6_5/clause.py` with real
  terminal-renderer screenshots.
- **Clause 1.2.4** password-policy testcases use the `tc_124_00N.py` naming
  convention; the hash-storage testcase remains `tc4_hash_storage.py`.

### 1.4 Housekeeping / removals

- The old **PyQt desktop UI** (`run_gui.py`, `icaf/ui/`) was **removed** from the
  working tree; the React/FastAPI web UI is the supported interface now.

---

## 2. Current project structure

```
icaf_1.6.5/
├── run.py                     # CLI entry: icaf.cli.main:main
├── run_web.py                 # Web launcher: builds webui/ then uvicorn on :8000
├── requirements.txt           # Runtime deps (typer, rich, paramiko, fastapi, uvicorn, python-docx ...)
├── requirements2.txt          # Pinned/extra deps including PyQt6 (legacy UI)
├── pyproject.toml             # Package metadata + console script "icaf"
├── test_paramiko.py           # Standalone SSH sanity test (dev tool)
├── CONTRIBUTING.md            # This guide
├── CONTRIBUTING_WEB.md        # Web/UI-specific contribution guide
│
├── icaf/                      # Python package
│   ├── cli/main.py            # Typer CLI: "icaf run", "icaf profile create|list"
│   ├── config/
│   │   ├── settings.py        # Singleton: BASE_DIR, OUTPUT_DIR, LOG_DIR, dir init
│   │   └── profile_loader.py  # Loads YAML/XLSX DUT profiles from icaf/profile/
│   ├── core/
│   │   ├── engine.py          # Orchestrator; _SSH_ONLY_CLAUSES set; returns report/context/results
│   │   ├── clause.py          # BaseClause (add_testcase / run)
│   │   ├── testcase.py        # TestCase: name, steps, evidence, PASS/FAIL/NOT_RUN
│   │   ├── step.py            # abstract Step
│   │   ├── step_runner.py     # runs a list of Steps in sequence
│   │   ├── clause_runner.py   # looks up CLAUSE_REGISTRY, runs a clause
│   │   └── result_recorder.py # record_result/get_results/clear_results for SSH-only clauses
│   ├── clauses/
│   │   ├── registry.py        # Lazy clause registry (CLAUSE_REGISTRY + _CLAUSE_LOADERS)
│   │   ├── catalog.py         # CLAUSE_CATALOG metadata + clause_names() + execution_plan()
│   │   ├── clause_1_1_1/      # Secure Mgmt Protocols — step/terminal/browser based (TC1–TC8)
│   │   ├── clause_1_1_3/      # RBAC — SSH-only, tc_113_001..004
│   │   ├── clause_1_2_1/      # User Authentication — SSH/SFTP/SCP, tc_4..tc_12, test-user lifecycle
│   │   ├── clause_1_2_4/      # Password Policy — SSH-only, tc_124_001..006 + hash-storage TC
│   │   ├── clause_1_6_1/      # Network Security — scanner based (nmap/TLS)
│   │   ├── clause_1_6_5/      # Secure Remote Access / data-at-rest — tc_165_001..003
│   │   └── clause_1_9_3/      # Vuln Scanning — SSH-only, tc_193_001
│   ├── steps/                 # Reusable Step classes (~20: Command, Input, ExpectOneOf,
│   │                          #   Verify/CheckOutput, Screenshot, PcapStart/Stop, Browser*, ...)
│   ├── terminal/              # TerminalManager, visible_terminal (gnome-terminal+tmux+xdotool),
│   │                          #   terminal_renderer (Pillow screenshots), live_window
│   ├── runtime/context.py     # RuntimeContext — shared state + ITSAR requirement metadata
│   ├── reporting/
│   │   ├── report_factory.py  # clause → report class routing
│   │   ├── report_manager.py  # generate() entry point
│   │   ├── helpers.py         # python-docx primitives
│   │   ├── front_page.py      # cover-page builder
│   │   ├── spec_loader.py     # YAML clause-spec loader
│   │   ├── screenshot_generator.py
│   │   └── clause_reports/    # clause_1_1_1_report.py ... clause_1_9_3_report.py
│   ├── web/                   # FastAPI backend + SQLite — SEE CONTRIBUTING_WEB.md
│   │   ├── api.py
│   │   └── storage.py
│   ├── adapters/              # AdapterFactory + base/linux/openwrt/cisco adapters
│   ├── browser/manager.py     # Selenium BrowserManager
│   ├── device/detector.py     # DUT OS detection (currently hardcoded linux)
│   ├── evidence/manager.py    # EvidenceManager: output/runs/<ts>-<clause>/ dir structure
│   ├── oam/                   # oam_manager, excel_parser, protocol_verifier
│   ├── tools/scanners/        # nmap_scan, cipher_support, ssh_verify, TLS_*, force_weak
│   ├── tools/report_helpers/  # legacy report helpers (tables, screenshot, headings)
│   ├── utils/                 # logger, dut_info, login_detector/executor/verifier
│   └── profile/               # default.yaml, alpine.yaml, metasploitable.yaml (+ .xlsx)
│
├── webui/                     # React + Vite frontend — SEE CONTRIBUTING_WEB.md
│   ├── index.html
│   ├── vite.config.js         # dev server :5173, proxies /api → :8000
│   ├── package.json
│   ├── dist/                  # production build (served by FastAPI at "/")
│   └── src/
│       ├── main.jsx           # App root: state, API calls, state-based routing
│       ├── styles.css         # single global stylesheet
│       ├── components/        # AppLayout, PageHeader, StatusBadge, Field
│       └── pages/             # DashboardPage, ConfigurePage, RunHistoryPage
│
├── output/                    # runtime output (gitignored)
│   ├── runs/<ts>-<clause>/    # evidence-manager run dirs (CLI)
│   └── web/runs/<run-uuid>/   # web run dirs: report/ screenshots/ input/ logs.txt
│   └── web/runs.sqlite3       # web persistence DB
├── logs/                      # runtime logs (gitignored)
└── evidence/                  # evidence storage (gitignored)
```

---

## 3. How the framework is wired (the touch points)

### 3.1 Clause registry — `icaf/clauses/registry.py`

A lazy-loading proxy. Every clause ID maps to a loader function returning the
clause **class**:

```python
def _load_clause_121():
    from icaf.clauses.clause_1_2_1.clause import Clause_1_2_1
    return Clause_1_2_1

_CLAUSE_LOADERS = {
    "1.1.1": _load_clause_111,
    "1.2.4": _load_clause_124,
    "1.6.1": _load_clause_161,
    "1.6.5": _load_clause_165,
    "1.9.3": _load_clause_193,
    "1.1.3": _load_clause_113,
    "1.2.1": _load_clause_121,
}

class _LazyRegistry(dict):
    def _load(self, key):
        if not dict.__contains__(self, key) and key in _CLAUSE_LOADERS:
            self[key] = _CLAUSE_LOADERS[key]()
    def __getitem__(self, key):
        self._load(key)
        return super().__getitem__(key)
    def __contains__(self, key):
        self._load(key)
        return dict.__contains__(self, key)

CLAUSE_REGISTRY = _LazyRegistry()
```

### 3.2 Clause metadata — `icaf/clauses/catalog.py`

`CLAUSE_CATALOG` maps clause ID → `{"name": ..., "testcases": [...]}`. This
populates the CLI/Web selectors and the execution-plan preview:

```python
CLAUSE_CATALOG = {
    ...
    "1.2.1": {
        "name": "User Authentication",
        "testcases": [
            {"id": "TC4", "name": "SSH — no authentication", "description": "..."},
            ...
        ],
    },
}
```

### 3.3 Engine enablement — `icaf/core/engine.py`

Clauses that only need SSH (no browser) are listed in `_SSH_ONLY_CLAUSES`. They
get a single `"dut"` terminal and no browser. Anything else gets a browser plus
`"tester"` and `"dut"` terminals:

```python
_SSH_ONLY_CLAUSES = {"1.1.3", "1.2.1", "1.2.4", "1.6.5", "1.9.3"}
```

### 3.4 ITSAR metadata — `icaf/runtime/context.py`

```python
self.itsar_requirement = {
    "1.1.1": "1.1.1 Management Protocols Entity Mutual Authentication",
    "1.2.4": "1.2.4 Password Policy Compliance",
    "1.6.1": "1.6.1 Software Update",
    "1.6.5": "1.6.5 Protecting Data and Information in Storage",
    "1.9.3": "1.9.3 Vulnerability Scanning",
    "1.2.1": "1.2.1 Authentication Policy",
}.get(clause or "", "ITSAR Compliance")
```

### 3.5 Report factory — `icaf/reporting/report_factory.py`

```python
class ReportFactory:
    @staticmethod
    def create(context, results):
        clause = context.clause
        if clause == "1.1.1":
            from icaf.reporting.clause_reports.clause_1_1_1_report import Clause111Report
            return Clause111Report(context, results)
        ...  # one if-block per clause
        raise Exception(f"No report template for clause {clause}")
```

> Web wiring (`icaf/web/api.py`, `storage.py`, `webui/`): see
> **[`CONTRIBUTING_WEB.md`](./CONTRIBUTING_WEB.md)**.

---

## 4. Adding a new clause — end-to-end checklist

Suppose you are adding clause **`1.X.Y`** ("Some Security Feature"). Follow every
step, in order:

1. **Clause metadata** — `icaf/clauses/catalog.py`
   Add to `CLAUSE_CATALOG`:
   ```python
   "1.X.Y": {
       "name": "Some Security Feature",
       "testcases": [
           {"id": "TC1", "name": "...", "description": "..."},
       ],
   },
   ```
   This immediately makes the clause appear in the CLI and web selectors and the
   execution-plan preview. The CLI validates against `clause_names()` (in
   `icaf/cli/main.py`).

2. **Clause package** — create `icaf/clauses/clause_1_x_y/`
   - `clause.py` with a class extending `icaf.core.clause.BaseClause`.
   - Testcases either as step-composed with `self.add_testcase(...)` (step-based
     clauses like 1.1.1), or as a `TEST_CASES` manifest + `run()` orchestration
     using `result_recorder` (SSH-only clauses like 1.2.1 / 1.6.5 / 1.9.3).
     Follow whichever pattern matches the clause's needs.
   - Add a `testcases/` subdirectory for the individual test modules.
   - If the clause creates anything on the DUT (users, files), add setup +
     cleanup like `clause_1_2_1/clause.py` and handle setup-failure gracefully
     (return a SETUP ERROR result).

3. **Registry** — `icaf/clauses/registry.py`
   Add a loader + register it:
   ```python
   def _load_clause_1xy():
       from icaf.clauses.clause_1_x_y.clause import Clause_1_X_Y
       return Clause_1_X_Y

   _CLAUSE_LOADERS = { ..., "1.X.Y": _load_clause_1xy, }
   ```

4. **Engine enablement** — `icaf/core/engine.py`
   - SSH-only → add `"1.X.Y"` to `_SSH_ONLY_CLAUSES`.
   - Browser/step-based → no change (browser + both terminals are the default).

5. **ITSAR metadata** — `icaf/runtime/context.py`
   Add to the `itsar_requirement` dict:
   ```python
   "1.X.Y": "1.X.Y Some Security Feature",
   ```

6. **Report class** — `icaf/reporting/clause_reports/clause_1_x_y_report.py`
   Create `Clause1XYReport(context, results)` implementing `generate() ->
   str` (absolute report path). Use `icaf.reporting.helpers` for python-docx
   primitives. Two existing patterns:
   - YAML-spec-driven with optional AI enrichment: `clause_1_1_1_report.py`
   - Fully hardcoded sections: `clause_1_2_4_report.py`, `clause_1_6_5_report.py`

7. **Report factory** — `icaf/reporting/report_factory.py`
   Add one if-block:
   ```python
   if clause == "1.X.Y":
       from icaf.reporting.clause_reports.clause_1_x_y_report import Clause1XYReport
       return Clause1XYReport(context, results)
   ```

8. **CLI** — `icaf/cli/main.py`
   If the clause needs extra/limited credential prompts, add an
   `elif clause == "1.X.Y":` branch (mirror the `1.2.1` SSH-only or `1.1.1`
   SNMP/web branches).

9. **Web API / UI** — only if the clause needs extra form fields
   See the web guide: pack the fields in `RunRequest`
   (`icaf/web/api.py`) and optionally add a conditional section in
   `webui/src/pages/ConfigurePage.jsx`. Without extra fields, **no web change is
   needed** — `catalog.py` step (1) automatically updates the web selectors.

10. **Verify**
    - `python -m compileall icaf` and `git diff --check`.
    - CLI: `python run.py run --clause 1.X.Y --profile default`
    - Web: start the backend, confirm the clause appears in the selector, run
      it, and check run status + report/screenshot downloads.

---

## 5. Running the project

```bash
# CLI (interactive credentials)
python run.py run --clause 1.2.1 --profile default
python run.py run --clause 1.1.1 --oam /path/plan.xlsx

# Web UI (builds frontend, then serves on http://127.0.0.1:8000)
python run_web.py

# Sanity checks
python -m compileall icaf
cd webui && npm run build
```

`python run.py profile create|list` manages DUT profiles (YAML under
`icaf/profile/`).

---

## 6. Reports

- Entry point: `ReportManager.generate(context, results)`
  (`icaf/reporting/report_manager.py`)
- Routing: `ReportFactory.create(context, results)`
- Generated artifacts land in the evidence run dir and are copied by the web
  runner into `output/web/runs/<uuid>/report/`.
- Two style patterns exist (YAML-spec + AI-enriched vs hardcoded); pick one and
  match the clause's existing report module.

---

## 7. Evidence & artifacts

- CLI/evidence-manager layout:
  `output/runs/<YYYY-MM-DD_HH-MM-SS>-<clause>/<clause>/<testcase>/{screenshots,logs,pcap}/`
- Web layout (per run) and the SQLite schema:
  see **[`CONTRIBUTING_WEB.md`](./CONTRIBUTING_WEB.md)**.

---

## 8. Known issues & gotchas

1. **Global state:** terminals and `terminal_renderer` are process-wide
   singletons; runs must stay serialized (`RUN_LOCK` in `api.py`).
2. **Credentials in output:** the CLI prompts with insecure defaults
   (`reaper@123` in `cli/main.py`). Keep test-case output redacting passwords,
   and never commit real `.env`/credentials.
3. **Profile duplication:** profiles exist twice (YAML + XLSX). When changing
   parameters, update both.

---

## 9. Contribution workflow

- Create a feature branch: `feat/clause-<id>-<thing>` or `fix/<thing>`.
- One logical change per PR: a new clause spans catalog + registry + engine +
  context + report + api; keep it together but reviewable.
- Run `git diff --check` and `python -m compileall icaf` before pushing.
- Never commit `output/`, `logs/`, `evidence/`, `venv/`, node_modules artifacts,
  or real credentials (`git status` should stay clean except intended files).
- Match the commit-message style in `git log` (short imperative subject).
