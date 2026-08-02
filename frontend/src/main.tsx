import React, { useEffect, useMemo, useState } from 'react';
import { createRoot } from 'react-dom/client';
import './style.css';

type LiveMetrics = {
  total_receivables: number;
  total_payables: number;
  overdue_invoices: number;
  open_customers: number;
};

type ApiState = {
  connected: boolean;
  loading: boolean;
  message: string;
  metrics: LiveMetrics | null;
};

const apiUrl = (import.meta.env.VITE_API_URL ?? 'http://localhost:8000').replace(/\/$/, '');
const modules = ['Authentication & RBAC', 'Customers', 'Suppliers', 'Sales invoices', 'Purchase invoices', 'PDF/OCR upload', 'AI extraction', 'Payment tracking', 'WhatsApp & Email reminders', 'Reports'];
const cards = [['👥','CRM','Customers and suppliers with tax, contact, and reminder metadata.'], ['📄','Invoices','Sales and purchase invoice lifecycle with upload extraction.'], ['💳','Payments','Partial/full payment tracking and overdue visibility.'], ['📊','Reports','Dashboard KPIs and aging reports for finance operations.']];

function currency(value: number) {
  return new Intl.NumberFormat('en-US', { style: 'currency', currency: 'USD', maximumFractionDigits: 0 }).format(value);
}

function App() {
  const [api, setApi] = useState<ApiState>({ connected: false, loading: true, message: 'Connecting to live API…', metrics: null });

  useEffect(() => {
    const controller = new AbortController();
    async function loadLiveMetrics() {
      try {
        const health = await fetch(`${apiUrl}/health`, { signal: controller.signal });
        if (!health.ok) throw new Error(`Health check returned ${health.status}`);
        const response = await fetch(`${apiUrl}/api/live-metrics`, { signal: controller.signal });
        if (!response.ok) throw new Error(`Metrics returned ${response.status}`);
        const metrics = await response.json() as LiveMetrics;
        setApi({ connected: true, loading: false, message: 'Live backend connected', metrics });
      } catch (error) {
        if (controller.signal.aborted) return;
        const message = error instanceof Error ? error.message : 'Unable to reach API';
        setApi({ connected: false, loading: false, message, metrics: null });
      }
    }
    loadLiveMetrics();
    return () => controller.abort();
  }, []);

  const metrics = useMemo(() => [
    {label:'Receivables', value: api.metrics ? currency(api.metrics.total_receivables) : '—'},
    {label:'Payables', value: api.metrics ? currency(api.metrics.total_payables) : '—'},
    {label:'Overdue', value: api.metrics ? String(api.metrics.overdue_invoices) : '—'},
    {label:'Customers', value: api.metrics ? String(api.metrics.open_customers) : '—'},
  ], [api.metrics]);

  return <main className="app"><section className="shell"><nav><div className="brand"><span className="logo">🤖</span><b>AI Finance CRM ERP</b></div><a className="button" href={`${apiUrl}/docs`} target="_blank" rel="noreferrer">Open Live API</a></nav><div className="hero"><div><p className="eyebrow">Production-ready finance automation</p><h1>Live CRM, ERP, OCR, and AI invoice extraction.</h1><p className="lead">This workspace now reads operational KPIs from the running FastAPI service, so the landing page reflects live database state instead of static demo numbers.</p><div className={api.connected ? 'status online' : 'status offline'}><span />{api.loading ? 'Checking API status…' : api.message}</div></div><div className="panel">{metrics.map(m => <div key={m.label} className="metric"><span>{m.label}</span><strong>{m.value}</strong></div>)}</div></div><div className="grid cards">{cards.map(([icon,title,body]) => <article className="card" key={title}><span className="icon">{icon}</span><h3>{title}</h3><p>{body}</p></article>)}</div><section className="card modules"><h2>Live modules</h2><div>{modules.map(module => <span key={module}>{module}</span>)}</div></section></section></main>;
}
createRoot(document.getElementById('root')!).render(<React.StrictMode><App /></React.StrictMode>);
