# ICAF — Web Contributor's Guide

**Scope:** Everything web in `icaf_1.6.5/` — the **React (Vite)** frontend in
`webui/`, the **FastAPI** backend in `icaf/web/`, and the **SQLite** persistence +
run/artifact handling that glue the GUI to the engine.

> For the general project guide (clause framework, adding a clause end-to-end,
> CLI, reports), see **[`CONTRIBUTING.md`](./CONTRIBUTING.md)**.

---

## 1. Overview of the web platform

The web UI turns the CLI-only ICAF into a **GUI-driven compliance platform**:

1. The React app (`webui/`) lets you configure a run (DUT, profile, clause,
   optional SNMP/web fields, optional OAM workbook) and shows run history with
   downloadable artifacts.
2. It talks to the FastAPI backend (`icaf/web/api.py`) over REST.
3. The backend validates input (Pydantic), persists runs/evidence in SQLite
   (`icaf/web/storage.py`), and executes the compliance run on a background
   thread against the existing `Engine`, then stages the generated report +
   screenshots into the run's artifact directory.
4. The engine remains the sole executor; the web layer is only orchestration +
   persistence + serving.

Because the terminal and screenshot facilities are process-wide, runs are
serialized with a module-level `RUN_LOCK`.

---

## 2. Web-relevant project layout

```
icaf_1.6.5/
├── run_web.py                 # Launcher: npm run build, then uvicorn :8000
├── icaf/web/
│   ├── api.py                 # FastAPI app — endpoints + background _execute_run
│   └── storage.py             # RunStore: SQLite runs/evidence tables, utc_now
└── webui/
    ├── index.html
    ├── vite.config.js         # dev :5173, proxies /api → :8000
    ├── package.json           # react, react-dom, lucide-react, vite
    ├── dist/                  # production build served by FastAPI at "/"
    └── src/
        ├── main.jsx           # App root: state, fetch calls, state-based routing
        ├── styles.css         # single global stylesheet
        ├── components/        # AppLayout, PageHeader, StatusBadge, Field
        └── pages/             # DashboardPage, ConfigurePage, RunHistoryPage
```

---

## 3. REST API (`icaf/web/api.py`)

| Method | Path | Purpose |
|---|---|---|
| GET | `/api/configuration` | `{clauses, profiles, testcases}` — populates UI selectors |
| POST | `/api/runs` | Start a run (multipart: `payload` JSON + optional `oam_file`) → `{id, status}` |
| GET | `/api/runs` | List runs (newest first) |
| GET | `/api/runs/{run_id}` | Run detail + nested `evidence` |
| GET | `/api/runs/{run_id}/artifacts/{path}` | Serve a stored artifact (path-validated) |

Key pieces:

- **`RunRequest`** (Pydantic `BaseModel`) validates the JSON `payload`:
  `clause`, `profile`, `ssh_ip`, `ssh_user`, `ssh_password`, plus optional
  SNMP/web fields. Unknown clause → `422`.
- **`/api/runs` (POST)** creates the run dir
  (`output/web/runs/<uuid>/{report,screenshots,input}`), stores the OAM file if
  uploaded (extension-checked `.xlsx`/`.xls`), inserts the run row as `queued`,
  and spawns `_execute_run()` on a daemon thread.
- **`_execute_run()`** — under `RUN_LOCK`:
  1. marks the run `running` (with `started_at`),
  2. hooks a file logger to `logs.txt`,
  3. (optionally) processes the OAM file, builds an `Engine` (SNMP/web creds are
     only forwarded when `clause == "1.1.1"`), and calls `engine.start()`,
  4. calls `_stage_artifacts()` to copy the report + screenshots into the run
     dir and register them as evidence rows,
  5. marks `completed` (or `failed` with `error_message` on exception),
  6. always registers the execution `log` evidence in `finally`.
- **`_stage_artifacts()`** copies the report file into `report/` and every
  supported image (`png/jpg/jpeg/webp`) from the evidence dir into
  `screenshots/`, using `_unique_path()` to avoid overwrites.
- **Artifact serving** resolves the requested path and refuses anything outside
  the run's own `artifact_dir` (no path traversal).

### Adding an endpoint

Add a `@app.get(...)` / `@app.post(...)` in `api.py`. Return plain dicts/lists
(detail from `RunStore`) so FastAPI serializes them. Raise `HTTPException(status_code, detail=...)`
for bad requests. If you add endpoints that the UI should read, call them from
`main.jsx` with `fetch`.

---

## 4. Persistence (`icaf/web/storage.py`)

`RunStore(path)` initializes the schema on construction:

```sql
CREATE TABLE runs (
    id TEXT PRIMARY KEY,           -- UUID
    clause TEXT NOT NULL,
    profile TEXT NOT NULL,
    dut_host TEXT NOT NULL,
    ssh_user TEXT NOT NULL,
    status TEXT NOT NULL,          -- queued | running | completed | failed
    created_at TEXT NOT NULL,
    started_at TEXT,
    finished_at TEXT,
    error_message TEXT,
    artifact_dir TEXT NOT NULL
);
CREATE TABLE evidence (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    run_id TEXT NOT NULL REFERENCES runs(id) ON DELETE CASCADE,
    kind TEXT NOT NULL,            -- report | screenshot | log
    label TEXT NOT NULL,
    relative_path TEXT NOT NULL,
    created_at TEXT NOT NULL,
    metadata_json TEXT NOT NULL DEFAULT '{}'
);
CREATE INDEX evidence_run_id_idx ON evidence(run_id);
```

Use `create_run()`, `update_run()`, `add_evidence()`, `list_runs()`,
`get_run()` (which attaches the run's evidence). Timestamps are UTC ISO-8601 via
`utc_now()`. Artifacts live on disk in:

```
output/web/runs/<run-uuid>/
    report/          compliance report (pdf/docx)
    screenshots/     evidence images (png/jpg/jpeg/webp)
    input/           uploaded OAM workbook
    logs.txt         execution log
```

---

## 5. Frontend architecture

- **Stack:** React (no TypeScript), Vite, `lucide-react` icons.
- **No router library.** Navigation is state-driven in `main.jsx`:
  a `page` state plus a `pages` object rendered inside `AppLayout`:
  ```jsx
  const pages = {
    dashboard: <DashboardPage ... />,
    configure: <ConfigurePage ... />,
    history:   <RunHistoryPage ... />,
  }
  return <AppLayout activePage={page} onNavigate={navigate} ...>{pages[page]}</AppLayout>
  ```
- **State lives in `main.jsx`**: `form`, `oamFile`, `config`, `runs`,
  `selectedRun`, `submitting`, `error`, `configuredPlan`. Pages are mostly
  presentational and receive props + callbacks.
- **Data flow:** `main.jsx` fetches `/api/configuration` on mount and
  `/api/runs` (plus 2.5 s polling while any run is `queued`/`running`).
  Starting a run POSTs `FormData` (`payload` JSON + optional `oam_file`), then
  navigates to the history page.
- **Styles:** one file, `webui/src/styles.css`. Reuse classes (`panel`,
  `panel-title`, `form-grid`, `field`, `primary-button`, `secondary-button`,
  `error-message`, `tab-nav`, `status-badge`, tables, …). No CSS modules.

---

## 6. Dev workflow

```bash
# Backend on :8000 (rebuilds the frontend too)
python run_web.py

# Fastest React iteration: backend with reload + Vite dev server
uvicorn icaf.web.api:app --reload          # terminal 1, on :8000
cd webui && npm install && npm run dev     # terminal 2, Vite on :5173
```

Vite on **:5173** proxies `/api` → `:8000` (see `vite.config.js`), so UI edits
hot-reload while the backend stays up. For production, the built `webui/dist/`
is mounted by FastAPI at `/` (`html=True`, so unknown paths fall back to
`index.html` to support client-side routes).

---

## 7. Adding a new page

1. Create `webui/src/pages/YourPage.jsx` (mirror an existing page's shape —
   `PageHeader` + panels + `Field`/`StatusBadge` as needed).
2. Register it in `webui/src/main.jsx`:
   ```jsx
   import YourPage from './pages/YourPage'
   ...
   const pages = {
     dashboard: <DashboardPage ... />,
     configure: <ConfigurePage ... />,
     history:   <RunHistoryPage ... />,
     yourPage:  <YourPage ... />,
   }
   ```
3. Add the nav tab in `webui/src/components/AppLayout.jsx`:
   ```jsx
   import { YourIcon } from 'lucide-react'
   const navigation = [
     { id: 'dashboard', label: 'Overview', icon: LayoutDashboard },
     { id: 'configure', label: 'New check', icon: ClipboardCheck },
     { id: 'history', label: 'Run history', icon: History },
     { id: 'yourPage', label: 'Your page', icon: YourIcon },   // ADD THIS
   ]
   ```
4. Wire any shared state/API through `main.jsx` props — keep the page
   presentational. For polling/refresh, reuse the existing interval pattern in
   `main.jsx`.

---

## 8. Adding / reusing components

- Put new components in `webui/src/components/`.
- Presentational only: receive data + callbacks as props, use classes from
  `styles.css`.
- Good templates: `PageHeader.jsx`, `Field.jsx`, `StatusBadge.jsx`.
- Icons: import from `lucide-react`, render at `size={16–22}`.

---

## 9. Adding a conditional clause form section

If a clause needs extra inputs (like 1.1.1's SNMP/web block):

1. **Backend first** — extend `RunRequest` in `icaf/web/api.py`, e.g.:
   ```python
   class RunRequest(BaseModel):
       ...
       your_field: str = ""
   ```
   and forward it to `Engine(...)` inside `_execute_run()` (mirror how SNMP/web
   fields are gated on `if request.clause == "1.1.1"`).

2. **Frontend** — `webui/src/pages/ConfigurePage.jsx`:
   ```jsx
   const extended = form.clause === '1.1.1'     // existing example
   const yourSection = form.clause === '1.X.Y'  // your new gate
   ...
   {yourSection && <section className="panel extended-panel">
     <div className="form-grid three-columns">
       <Field label="Your field"><input name="your_field" value={form.your_field} onChange={onField} /></Field>
       ...
     </div>
   </section>}
   ```

3. Add sensible defaults for the new fields to `initialForm` in `main.jsx`.

> Clauses with **no** extra fields need zero frontend changes — the selector is
> populated automatically from `/api/configuration` (which reads
> `catalog.py`).

---

## 10. Rebuilding & verifying checklist

- [ ] `cd webui && npm run build` — commit `dist/` so the backend serves the new
      UI out of the box (`run_web.py` also rebuilds automatically).
- [ ] Verify at `http://127.0.0.1:8000` (production) **and** `:5173` (dev).
- [ ] Keep icons from `lucide-react`, consistent class names, responsive layout.
- [ ] Don't hardcode clause lists/names in JSX — load from `/api/configuration`.
- [ ] Backend changes: `python -m compileall icaf` and `git diff --check`.
- [ ] Run a real clause end-to-end from the UI; confirm status transitions and
      report/screenshot/log downloads.

---

## 11. Web-specific gotchas

- **Global state / concurrency:** the engine's terminals and
  `terminal_renderer` are process-wide singletons. Do **not** remove or relax
  `RUN_LOCK` serialization without a serialization strategy first.
- **Path safety:** always resolve artifact paths and verify they stay inside the
  run's `artifact_dir` (see `/api/runs/{id}/artifacts/…`).
- **OAM uploads:** validate by extension (`.xlsx`/`.xls`) and store inside the
  run's `input/` dir, not in shared locations.
- **Credentials:** never log or return `ssh_password` in API responses. The
  report output is staged to disk only.
- **Static mount order:** the SPA static mount lives at the end of `api.py` so
  API routes take precedence over `index.html` fallback.
