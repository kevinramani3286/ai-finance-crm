import React, { useEffect, useMemo, useRef, useState } from 'react';
import { createRoot } from 'react-dom/client';
import './style.css';

type Dashboard = {
  financial_year: string;
  total_sales: number;
  total_collections: number;
  outstanding: number;
  overdue: number;
  profit: number;
  expenses: number;
  aging: Record<string, number>;
  top_customers: { name: string; amount: number }[];
  payment_modes: Record<string, number>;
  trend: { label: string; sales: number; collections: number }[];
  invoice_count: number;
  payments_count: number;
};

type OcrResult = {
  file_name: string;
  document_type: string;
  status: string;
  confidence: number;
  fields: Record<string, unknown>;
  text_preview: string;
};

const apiUrl = (import.meta.env.VITE_API_URL ?? 'http://localhost:8000').replace(/\/$/, '');

const nav = [
  ['⌂', 'Dashboard'], ['▤', 'Invoices'], ['₹', 'Payments'], ['▥', 'Quotations'],
  ['♟', 'Customers'], ['▦', 'Products'], ['🛒', 'Purchase'], ['⌁', 'OCR / Import'], ['▤', 'Reports']
];

const quickActions = [
  ['＋', 'New Invoice', 'invoice'], ['▣', 'New Payment', 'payment'], ['▤', 'New Quotation', 'quotation'],
  ['🛒', 'New Purchase', 'purchase'], ['▥', 'Follow-ups', 'invoice'], ['▰', 'Customer Ledger', 'invoice'],
  ['▤', 'Bank Reconciliation', 'bank'], ['🤖', 'OCR Import', 'invoice'], ['♟', 'Owner Dashboard', 'invoice'],
  ['▧', 'Reports Center', 'invoice'], ['⌕', 'Global Search', 'invoice']
];

const ocrTypes = [
  ['invoice', '🧾 Invoice OCR'], ['payment', '💳 Payment OCR'], ['purchase', '🛒 Purchase OCR'],
  ['bank', '🏦 Bank Statement OCR'], ['quotation', '📋 Quotation OCR'], ['expense', '💰 Expense OCR']
];

function money(value: number) {
  return new Intl.NumberFormat('en-IN', { style: 'currency', currency: 'INR', maximumFractionDigits: 0 }).format(value || 0);
}

function compact(value: number) {
  if (Math.abs(value) >= 10000000) return `₹${(value / 10000000).toFixed(2)}Cr`;
  if (Math.abs(value) >= 100000) return `₹${(value / 100000).toFixed(2)}L`;
  if (Math.abs(value) >= 1000) return `₹${(value / 1000).toFixed(1)}K`;
  return money(value);
}

function Donut({ value, total, label }: { value: number; total: number; label: string }) {
  const percent = total ? Math.min(100, Math.max(0, (value / total) * 100)) : 0;
  return <div className="donut" style={{ '--p': `${percent}%` } as React.CSSProperties}><div><strong>{percent.toFixed(1)}%</strong><span>{label}</span></div></div>;
}

function Trend({ data }: { data: Dashboard['trend'] }) {
  const max = Math.max(1, ...data.map(x => Math.max(x.sales, x.collections)));
  const points = data.map((x, i) => `${(i / Math.max(1, data.length - 1)) * 100},${96 - (x.collections / max) * 76}`).join(' ');
  const target = data.map((_, i) => `${(i / Math.max(1, data.length - 1)) * 100},${96 - (i / Math.max(1, data.length - 1)) * 76}`).join(' ');
  return <div className="trend-wrap"><svg viewBox="0 0 100 100" preserveAspectRatio="none" className="trend-svg"><path d="M0 20 H100 M0 45 H100 M0 70 H100 M0 95 H100" className="gridline"/><polyline points={target} className="target-line"/><polyline points={points} className="collection-line"/>{data.map((x, i) => <circle key={x.label} cx={(i / Math.max(1, data.length - 1)) * 100} cy={96 - (x.collections / max) * 76} r="1.1" className="point"/>)}</svg><div className="trend-labels">{data.map(x => <span key={x.label}>{x.label}</span>)}</div></div>;
}

function App() {
  const [data, setData] = useState<Dashboard | null>(null);
  const [apiOnline, setApiOnline] = useState(false);
  const [moreOpen, setMoreOpen] = useState(false);
  const [ocrOpen, setOcrOpen] = useState(false);
  const [ocrType, setOcrType] = useState('invoice');
  const [ocrResult, setOcrResult] = useState<OcrResult | null>(null);
  const [ocrBusy, setOcrBusy] = useState(false);
  const [toast, setToast] = useState('');
  const inputRef = useRef<HTMLInputElement>(null);

  const load = async () => {
    try {
      const health = await fetch(`${apiUrl}/health`);
      if (!health.ok) throw new Error('API unavailable');
      const res = await fetch(`${apiUrl}/api/dashboard/summary`);
      if (!res.ok) throw new Error(`Dashboard ${res.status}`);
      setData(await res.json());
      setApiOnline(true);
    } catch {
      setApiOnline(false);
      setData(null);
    }
  };

  useEffect(() => { load(); const id = window.setInterval(load, 30000); return () => window.clearInterval(id); }, []);

  const kpis = useMemo(() => data ? [
    ['Total Sales', data.total_sales, 'Live'], ['Total Collections', data.total_collections, 'Payments received'],
    ['Outstanding', data.outstanding, 'Active receivables'], ['Overdue', data.overdue, 'Needs action'],
    ['Profit (Net)', data.profit, 'Current FY'], ['Expenses', data.expenses, 'Tracked FY']
  ] : [], [data]);

  const agingTotal = data ? Object.values(data.aging).reduce((a, b) => a + b, 0) : 0;
  const paymentTotal = data ? Object.values(data.payment_modes).reduce((a, b) => a + b, 0) : 0;

  async function runOcr(file?: File) {
    if (!file) return;
    setOcrBusy(true); setOcrResult(null);
    try {
      const form = new FormData(); form.append('file', file);
      const res = await fetch(`${apiUrl}/api/ocr/analyze?document_type=${encodeURIComponent(ocrType)}`, { method: 'POST', body: form });
      if (!res.ok) throw new Error(`OCR ${res.status}`);
      setOcrResult(await res.json());
      setToast('OCR completed — review extracted fields before posting.');
    } catch (e) {
      setToast(e instanceof Error ? e.message : 'OCR failed');
    } finally { setOcrBusy(false); }
  }

  return <div className="app">
    <header className="topbar">
      <div className="brand"><span className="briefcase">💼</span><div><b>RIT Business OS <small>V27</small></b><span>Sales · Collections · Finance · Inventory · Intelligence</span></div></div>
      <div className="top-controls"><select defaultValue="FY 2026-27"><option>FY 2026-27</option><option>FY 2025-26</option></select><select defaultValue="Midnight"><option>Midnight</option><option>Classic Blue</option><option>Emerald</option></select><button className="backup">💾 Backup</button><button>▣ App</button></div>
    </header>

    <div className="page">
      <nav className="main-nav">
        {nav.map(([icon, label], i) => <button key={label} className={i === 0 ? 'active' : ''} onClick={() => label === 'OCR / Import' && setOcrOpen(true)}><span>{icon}</span>{label}</button>)}
        <button onClick={() => setMoreOpen(v => !v)}>••• More⌄</button>
        {moreOpen && <div className="more-menu">{['Allocation','Bank Reconciliation','Purchases','Owner Dashboard','Global Search','Product Merge','OCR Review','FY Control','Audit Log','Backup','Control Center'].map(x => <button key={x} onClick={() => x.toLowerCase().includes('ocr') ? setOcrOpen(true) : setToast(`${x} module ready to connect.`)}>{x}</button>)}</div>}
      </nav>

      <section className="fybar"><b>Financial Year: {data?.financial_year ?? 'FY 2026-27'}</b><span>All dashboard figures follow the selected FY.</span><em>• {apiOnline ? 'Live business view' : 'Offline demo view'}</em></section>

      <section className="kpi-grid">
        <div className="kpi fy"><span>Financial Year</span><strong>2026-27</strong><small>1 Apr – 31 Mar</small></div>
        {kpis.map(([label, value, sub]) => <div className="kpi" key={String(label)}><span>{label}</span><strong>{money(Number(value))}</strong><small className={label === 'Overdue' ? 'red' : 'green'}>{sub}</small></div>)}
        <div className="kpi"><span>Last Backup</span><strong>{apiOnline ? 'Ready' : 'Check API'}</strong><small>Local data protection</small></div>
      </section>

      <section className="row three">
        <article className="card collection-card"><div className="card-head"><h3>Collection vs Target</h3><button className="pill">This FY</button></div><div className="collection-body"><Donut value={data?.total_collections ?? 0} total={data?.total_sales ?? 0} label="Achieved"/><div className="stats"><div><span>Target</span><b>{money(data?.total_sales ?? 0)}</b></div><div><span>Collected</span><b>{money(data?.total_collections ?? 0)}</b></div><div><span>Balance</span><b>{money(Math.max(0, (data?.total_sales ?? 0) - (data?.total_collections ?? 0)))}</b></div></div></div><small className="muted">Compared with payment target for this FY</small></article>
        <article className="card trend-card"><div className="card-head"><h3>Collection Trend <span>(This FY)</span></h3><div className="legend"><i/> Collections <i className="blue"/> Target</div></div><Trend data={data?.trend ?? []}/></article>
        <article className="card aging-card"><div className="card-head"><h3>Receivable Aging</h3><button className="link">View Details</button></div><div className="aging-grid">{[['0-7','0-7 Days'],['8-30','8-30 Days'],['31-60','31-60 Days'],['61-90','61-90 Days'],['90+','90+ Days']].map(([key,label]) => <div key={key} className={key === '90+' ? 'danger aging-box' : 'aging-box'}><span>{label}</span><b>{money(data?.aging[key] ?? 0)}</b><small>{agingTotal ? `${(((data?.aging[key] ?? 0) / agingTotal) * 100).toFixed(1)}%` : '0.0%'}</small></div>)}</div></article>
      </section>

      <section className="row three lower">
        <article className="card priority"><div className="card-head"><h3>Priority Collection List</h3><button className="link">View All</button></div>{(data?.top_customers ?? []).slice(0, 5).map((x, i) => <div className="priority-row" key={x.name}><div><b>{x.name}</b><small>Outstanding customer #{i + 1}</small></div><strong>{money(x.amount)}</strong><button onClick={() => setToast(`Reminder prepared for ${x.name}`)}>Remind</button></div>)}{!data?.top_customers.length && <div className="empty">No priority collections yet.</div>}</article>
        <article className="card quick"><div className="card-head"><h3>Quick Actions</h3></div><div className="quick-grid">{quickActions.map(([icon,label,type]) => <button key={label} onClick={() => type === 'bank' || label === 'OCR Import' ? (setOcrType(type), setOcrOpen(true)) : setToast(`${label} opened.`)}><span>{icon}</span><b>{label}</b>{['New Invoice','New Payment','New Purchase','Bank Reconciliation','OCR Import'].includes(label) && <small>OCR</small>}</button>)}</div></article>
        <article className="card top-customers"><div className="card-head"><h3>Top 5 Customers by Outstanding</h3><button className="link">View All</button></div>{(data?.top_customers ?? []).map((x, i) => <div className="bar-row" key={x.name}><span>{x.name}</span><div><i style={{ width: `${Math.max(10, ((x.amount / Math.max(1, data?.top_customers[0]?.amount ?? 1)) * 100))}%` }}/></div><b>{money(x.amount)}</b></div>)}{!data?.top_customers.length && <div className="empty">No customer balances yet.</div>}</article>
      </section>

      <section className="row transactions"><article className="card"><div className="card-head"><h3>Recent Transactions</h3><div className="tabs"><button className="selected">All</button><button>Invoices</button><button>Payments</button><button>Purchases</button><button>Quotations</button></div></div><div className="transaction-empty">{data ? <><b>{data.invoice_count}</b> sales invoices and <b>{data.payments_count}</b> payments are recorded for this FY.</> : 'Connect the API to load live transactions.'}</div></article><article className="card payment-mode"><div className="card-head"><h3>Payment Mode <span>(This FY)</span></h3></div><div className="payment-flex"><Donut value={paymentTotal} total={paymentTotal || 1} label="Total"/><div>{Object.entries(data?.payment_modes ?? {}).slice(0, 6).map(([k,v]) => <div className="mode-row" key={k}><i/> <span>{k}</span><b>{money(v)}</b></div>)}{!paymentTotal && <p className="muted">No payments recorded.</p>}</div></div></article></section>

      <section className="row four bottom">
        <article className="card alerts"><div className="card-head"><h3>Alerts & Reminders</h3><button className="link">View All</button></div><p>🔴 Invoices Overdue <b>{data ? data.overdue ? 'Needs Action' : '0' : '—'}</b></p><p>🟠 OCR Review Pending <b>{ocrResult?.status === 'review' ? '1' : '0'}</b></p><p>🟡 Unallocated Receipts <b>0</b></p><p>🔵 Low Stock Products <b>0</b></p><p>🟣 Follow-ups Due <b>0</b></p></article>
        <article className="card health"><div className="card-head"><h3>Business Health Score</h3></div><Donut value={data ? Math.max(0, 100 - Math.min(100, data.overdue / Math.max(1, data.outstanding) * 100)) : 0} total={100} label="Good"/><ul><li>✓ Collection Performance <b>Good</b></li><li>✓ Overdue Management <b>{data?.overdue ? 'Needs Action' : 'Good'}</b></li><li>✓ Sales Growth <b>Good</b></li><li>✓ Expense Control <b>Good</b></li><li>✓ Profitability <b>Good</b></li></ul></article>
        <article className="card highlights"><div className="card-head"><h3>Highlights <span>(This FY)</span></h3></div><p>🏆 Best Customer <b>{data?.top_customers[0]?.name ?? '—'}</b></p><p>📦 Invoices Created <b>{data?.invoice_count ?? 0}</b></p><p>💳 Payments Received <b>{data?.payments_count ?? 0}</b></p><p>💰 Profit <b>{money(data?.profit ?? 0)}</b></p><p>🤖 OCR Engine <b>Ready</b></p></article>
        <article className="card shortcuts"><div className="card-head"><h3>Shortcuts</h3></div><div>{['Customer Statements','Product Margins','Aging Report','Sales Vs Purchase','Profit Report','Payment Allocation','Bank Statement Import','FY Control Center','Audit Log','Quotation OCR','Backup / Restore'].map(x => <button key={x} onClick={() => x.includes('OCR') || x.includes('Bank') ? setOcrOpen(true) : setToast(`${x} opened.`)}>{x}</button>)}</div></article>
      </section>
    </div>

    <footer>© 2026 RIT Business OS. All rights reserved. <span>Designed for growing businesses 💚</span><b>Version V27.1.0</b></footer>

    {ocrOpen && <div className="modal-backdrop" onMouseDown={() => !ocrBusy && setOcrOpen(false)}><div className="ocr-modal" onMouseDown={e => e.stopPropagation()}><div className="modal-head"><div><h2>Smart OCR Center</h2><p>One OCR engine for invoices, payments, purchases, banks, quotations and expenses.</p></div><button onClick={() => setOcrOpen(false)}>✕</button></div><div className="ocr-types">{ocrTypes.map(([type,label]) => <button key={type} className={ocrType === type ? 'selected' : ''} onClick={() => { setOcrType(type); setOcrResult(null); }}>{label}</button>)}</div><div className="dropzone" onClick={() => inputRef.current?.click()}><input ref={inputRef} type="file" accept=".pdf,.png,.jpg,.jpeg,.tif,.tiff,.webp" hidden onChange={e => runOcr(e.target.files?.[0])}/><span>🤖</span><b>{ocrBusy ? 'Reading document…' : 'Drop PDF / image here or click to upload'}</b><small>Scanned PDFs use Tesseract OCR · text PDFs use direct extraction</small></div>{ocrResult && <div className="ocr-result"><div className="result-head"><b>{ocrResult.file_name}</b><span className={ocrResult.confidence >= .8 ? 'good-badge' : 'review-badge'}>{Math.round(ocrResult.confidence * 100)}% confidence · {ocrResult.status}</span></div><div className="field-grid">{Object.entries(ocrResult.fields).filter(([k]) => !['document_type','text_length'].includes(k)).map(([k,v]) => <label key={k}><span>{k.replaceAll('_',' ')}</span><b>{String(v || '—')}</b></label>)}</div><details><summary>OCR text preview</summary><pre>{ocrResult.text_preview}</pre></details></div>}<div className="modal-foot"><span>OCR is review-first: extracted data is not posted automatically.</span><button className="primary" onClick={() => inputRef.current?.click()}>📄 Choose Document</button></div></div></div>}
    {toast && <button className="toast" onClick={() => setToast('')}>{toast} ✕</button>}
  </div>;
}

createRoot(document.getElementById('root')!).render(<React.StrictMode><App /></React.StrictMode>);
