import React from 'react';
import { createRoot } from 'react-dom/client';
import './style.css';

const modules = ['Authentication & RBAC', 'Customers', 'Suppliers', 'Sales invoices', 'Purchase invoices', 'PDF/OCR upload', 'AI extraction', 'Payment tracking', 'WhatsApp & Email reminders', 'Reports'];
const metrics = [{label:'Receivables',value:'$128.4k'}, {label:'Payables',value:'$46.2k'}, {label:'Overdue',value:'18'}, {label:'AI extracted',value:'94%'}];
const cards = [['👥','CRM','Customers and suppliers with tax, contact, and reminder metadata.'], ['📄','Invoices','Sales and purchase invoice lifecycle with upload extraction.'], ['💳','Payments','Partial/full payment tracking and overdue visibility.'], ['📊','Reports','Dashboard KPIs and aging reports for finance operations.']];
function App() {
  return <main className="app"><section className="shell"><nav><div className="brand"><span className="logo">🤖</span><b>AI Finance CRM ERP</b></div><button>Open Workspace</button></nav><div className="hero"><div><p className="eyebrow">Production-ready finance automation</p><h1>CRM, ERP, OCR, and AI invoice extraction in one responsive workspace.</h1><p className="lead">FastAPI, PostgreSQL, JWT authentication, modular APIs, local-cloud-ready uploads, and a React/Vite TypeScript interface designed for finance teams.</p></div><div className="panel">{metrics.map(m => <div key={m.label} className="metric"><span>{m.label}</span><strong>{m.value}</strong></div>)}</div></div><div className="grid cards">{cards.map(([icon,title,body]) => <article className="card" key={title}><span className="icon">{icon}</span><h3>{title}</h3><p>{body}</p></article>)}</div><section className="card modules"><h2>Modules</h2><div>{modules.map(module => <span key={module}>{module}</span>)}</div></section></section></main>;
}
createRoot(document.getElementById('root')!).render(<React.StrictMode><App /></React.StrictMode>);
