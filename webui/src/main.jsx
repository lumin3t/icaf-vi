import { useEffect, useMemo, useState } from 'react'
import { CheckCircle2, ChevronRight, ClipboardCheck, Download, FileText, FolderOpen, History, LoaderCircle, MonitorCog, ShieldCheck, XCircle } from 'lucide-react'
import { createRoot } from 'react-dom/client'
import './styles.css'

const initialForm = {
  clause: '1.6.5', profile: 'default', ssh_ip: '10.80.127.211', ssh_user: 'dut', ssh_password: '',
  snmp_user: 'snmpuser', snmp_auth_pass: '', snmp_priv_pass: '', snmp_community: 'community',
  web_login_url: '', web_username: 'admin', web_password: '',
}

function App() {
  const [page, setPage] = useState('configure')
  const [form, setForm] = useState(initialForm)
  const [oamFile, setOamFile] = useState(null)
  const [config, setConfig] = useState({ clauses: {}, profiles: ['default'] })
  const [runs, setRuns] = useState([])
  const [selectedRun, setSelectedRun] = useState(null)
  const [submitting, setSubmitting] = useState(false)
  const [error, setError] = useState('')

  const refreshRuns = async () => {
    const response = await fetch('/api/runs')
    if (response.ok) setRuns(await response.json())
  }

  useEffect(() => {
    fetch('/api/configuration').then(response => response.json()).then(data => {
      setConfig(data)
      if (data.profiles?.length && !data.profiles.includes(form.profile)) setForm(current => ({ ...current, profile: data.profiles[0] }))
    })
    refreshRuns()
  }, [])

  useEffect(() => {
    const hasActiveRun = runs.some(run => run.status === 'queued' || run.status === 'running')
    if (!hasActiveRun) return undefined
    const interval = window.setInterval(refreshRuns, 2500)
    return () => window.clearInterval(interval)
  }, [runs])

  const onField = event => setForm(current => ({ ...current, [event.target.name]: event.target.value }))
  const requiresExtendedConfig = form.clause === '1.1.1'
  const selectedSummary = useMemo(() => runs.find(run => run.id === selectedRun?.id), [runs, selectedRun])

  const startRun = async event => {
    event.preventDefault()
    setError('')
    setSubmitting(true)
    const body = new FormData()
    body.append('payload', JSON.stringify(form))
    if (oamFile) body.append('oam_file', oamFile)
    try {
      const response = await fetch('/api/runs', { method: 'POST', body })
      const data = await response.json()
      if (!response.ok) throw new Error(data.detail || 'Unable to start the run.')
      await refreshRuns()
      setPage('history')
    } catch (requestError) {
      setError(requestError.message)
    } finally {
      setSubmitting(false)
    }
  }

  const openRun = async run => {
    const response = await fetch(`/api/runs/${run.id}`)
    if (response.ok) setSelectedRun(await response.json())
  }

  return <main className="app-shell">
    <aside className="sidebar">
      <div className="brand"><ShieldCheck size={25} /><span>ICAF</span></div>
      <div className="brand-subtitle">Compliance Suite</div>
      <nav aria-label="Primary navigation">
        <NavButton active={page === 'configure'} icon={<MonitorCog />} label="Configure DUT" onClick={() => setPage('configure')} />
        <NavButton active={page === 'history'} icon={<History />} label="Evidences / Run History" onClick={() => setPage('history')} />
      </nav>
      <div className="sidebar-footer"><span className="local-dot" /> Local workspace</div>
    </aside>
    <section className="content">
      {page === 'configure' ? <Configure
        form={form} config={config} oamFile={oamFile} error={error} submitting={submitting}
        extended={requiresExtendedConfig} onField={onField} onFile={setOamFile} onSubmit={startRun}
      /> : <RunHistory runs={runs} selectedRun={selectedSummary || selectedRun} onOpen={openRun} onClose={() => setSelectedRun(null)} />}
    </section>
  </main>
}

function NavButton({ active, icon, label, onClick }) {
  return <button className={`nav-button ${active ? 'active' : ''}`} onClick={onClick}>{icon}<span>{label}</span></button>
}

function Configure({ form, config, oamFile, error, submitting, extended, onField, onFile, onSubmit }) {
  return <>
    <header className="page-header"><div><p className="eyebrow">Compliance execution</p><h1>Configure DUT</h1><p>Set the target device and requirements for this check.</p></div><div className="header-mark"><ClipboardCheck size={22} /></div></header>
    <form onSubmit={onSubmit}>
      <section className="panel"><div className="panel-title"><div><h2>Session parameters</h2><p>Required connection and compliance settings.</p></div></div>
        <div className="form-grid">
          <Field label="Compliance clause"><select name="clause" value={form.clause} onChange={onField}>{Object.entries(config.clauses).map(([value, label]) => <option key={value} value={value}>{value} - {label}</option>)}</select></Field>
          <Field label="DUT profile"><select name="profile" value={form.profile} onChange={onField}>{config.profiles.map(profile => <option key={profile}>{profile}</option>)}</select></Field>
          <Field label="Device IP / hostname"><input required name="ssh_ip" value={form.ssh_ip} onChange={onField} /></Field>
          <Field label="SSH username"><input required name="ssh_user" value={form.ssh_user} onChange={onField} /></Field>
          <Field label="SSH password"><input type="password" name="ssh_password" value={form.ssh_password} onChange={onField} /></Field>
          <Field label="OAM Excel file"><label className="file-input"><FolderOpen size={17} /><span>{oamFile ? oamFile.name : 'Choose workbook'}</span><input type="file" accept=".xlsx,.xls" onChange={event => onFile(event.target.files?.[0] || null)} /></label></Field>
        </div>
      </section>
      {extended && <section className="panel extended-panel"><div className="panel-title"><div><h2>SNMP & web portal</h2><p>Used by clause 1.1.1 secure management protocol checks.</p></div></div>
        <div className="form-grid three-columns">
          <Field label="SNMPv3 user"><input name="snmp_user" value={form.snmp_user} onChange={onField} /></Field>
          <Field label="SNMP auth pass"><input type="password" name="snmp_auth_pass" value={form.snmp_auth_pass} onChange={onField} /></Field>
          <Field label="SNMP priv pass"><input type="password" name="snmp_priv_pass" value={form.snmp_priv_pass} onChange={onField} /></Field>
          <Field label="SNMP community"><input name="snmp_community" value={form.snmp_community} onChange={onField} /></Field>
          <Field label="Web login URL"><input name="web_login_url" placeholder={`http://${form.ssh_ip}/dvwa/login.php`} value={form.web_login_url} onChange={onField} /></Field>
          <Field label="Web username"><input name="web_username" value={form.web_username} onChange={onField} /></Field>
          <Field label="Web password"><input type="password" name="web_password" value={form.web_password} onChange={onField} /></Field>
        </div>
      </section>}
      {error && <div className="error-message"><XCircle size={17} />{error}</div>}
      <div className="action-row"><button className="primary-button" disabled={submitting}>{submitting ? <LoaderCircle className="spin" size={18} /> : <CheckCircle2 size={18} />} {submitting ? 'Starting check...' : 'Start compliance check'}</button><span>Artifacts and logs stay on this machine.</span></div>
    </form>
  </>
}

function Field({ label, children }) { return <label className="field"><span>{label}</span>{children}</label> }

function RunHistory({ runs, selectedRun, onOpen, onClose }) {
  return <>
    <header className="page-header"><div><p className="eyebrow">Local evidence archive</p><h1>Evidences / Run History</h1><p>Reports, logs, and screenshots from previous executions.</p></div><div className="header-mark"><History size={22} /></div></header>
    <section className="history-layout">
      <div className="panel run-list"><div className="panel-title"><div><h2>Runs</h2><p>{runs.length} recorded execution{runs.length === 1 ? '' : 's'}</p></div></div>
        {runs.length === 0 ? <div className="empty-state"><FileText size={27} /><p>No runs yet.</p></div> : <div className="table-wrap"><table><thead><tr><th>Run</th><th>DUT</th><th>Clause</th><th>Status</th><th /></tr></thead><tbody>{runs.map(run => <tr key={run.id} onClick={() => onOpen(run)}><td><strong>{run.id.slice(0, 8)}</strong><small>{formatDate(run.created_at)}</small></td><td>{run.dut_host}<small>{run.profile}</small></td><td>{run.clause}</td><td><Status status={run.status} /></td><td><ChevronRight size={18} /></td></tr>)}</tbody></table></div>}
      </div>
      {selectedRun && <RunDetail run={selectedRun} onClose={onClose} />}
    </section>
  </>
}

function Status({ status }) { return <span className={`status ${status}`}>{status === 'completed' ? 'Completed' : status === 'failed' ? 'Failed' : status === 'running' ? 'Running' : 'Queued'}</span> }

function RunDetail({ run, onClose }) {
  const reports = run.evidence?.filter(item => item.kind === 'report') || []
  const shots = run.evidence?.filter(item => item.kind === 'screenshot') || []
  const logs = run.evidence?.filter(item => item.kind === 'log') || []
  const url = item => `/api/runs/${run.id}/artifacts/${item.relative_path}`
  return <aside className="panel detail-panel"><div className="detail-heading"><div><p className="eyebrow">Run {run.id.slice(0, 8)}</p><h2>{run.dut_host}</h2></div><button className="icon-button" onClick={onClose} aria-label="Close run details">×</button></div><div className="metadata"><span>Clause <strong>{run.clause}</strong></span><span>Profile <strong>{run.profile}</strong></span><span>Status <Status status={run.status} /></span><span>Started <strong>{formatDate(run.started_at || run.created_at)}</strong></span></div>{run.error_message && <div className="error-message"><XCircle size={17} />{run.error_message}</div>}
    <div className="downloads">{reports.map(item => <a className="secondary-button" href={url(item)} key={item.id}><Download size={16} /> Download report</a>)}{logs.map(item => <a className="text-download" href={url(item)} key={item.id}><FileText size={16} /> Download logs</a>)}</div>
    <h3>Screenshots</h3>{shots.length === 0 ? <p className="muted">{run.status === 'completed' ? 'No screenshots were generated for this run.' : 'Screenshots appear when the run completes.'}</p> : <div className="screenshot-grid">{shots.map(item => <a href={url(item)} key={item.id} target="_blank" rel="noreferrer"><img src={url(item)} alt={item.label} /><span>{item.label}</span></a>)}</div>}
  </aside>
}

function formatDate(value) { return value ? new Date(value).toLocaleString() : 'Not started' }

createRoot(document.getElementById('root')).render(<App />)
