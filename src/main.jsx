import { useEffect, useState } from 'react'
import { createRoot } from 'react-dom/client'
import {
  ArrowDownRight,
  ArrowRight,
  ArrowUp,
  ArrowUpRight,
  BarChart3,
  BriefcaseBusiness,
  Building2,
  Check,
  CircleCheck,
  Clock3,
  Cloud,
  Globe2,
  Mail,
  MapPin,
  Menu,
  Minus,
  Phone,
  Plus,
  Quote,
  ShieldCheck,
  UsersRound,
  X,
} from 'lucide-react'
import Dashboard from './Dashboard'
import './styles.css'

const dashboardUrl = import.meta.env.VITE_DASHBOARD_URL || `${window.location.protocol}//${window.location.hostname}:8501`

const navLinks = [
  { href: '#about', label: 'Why it exists' },
  { href: '#capabilities', label: 'Desk views' },
  { href: '#approach', label: 'Workflow' },
  { href: '#impact', label: 'Run evidence' },
  { href: '#faq', label: 'FAQ' },
]

const deskViews = [
  {
    number: '01',
    label: 'Inputs / network',
    icon: Building2,
    title: 'Map the supply system',
    text: 'Load fictional sources, facilities, routes and district demand into one inspectable network. Every quantity has a unit, a provenance and a visible assumption.',
    detail: '14 nodes · 16 routes · 6 districts',
  },
  {
    number: '02',
    label: 'Scenarios / pressure',
    icon: BriefcaseBusiness,
    title: 'Stress the right part',
    text: 'Try an import shock, route closure, route delay or facility outage. Change one condition at a time so the operational question stays legible.',
    detail: '5 repeatable disruption fixtures',
  },
  {
    number: '03',
    label: 'Plans / comparison',
    icon: BarChart3,
    title: 'Compare two plans',
    text: 'Run baseline and candidate allocations against the same physical constraints. If the plans tie, the desk reports a tie instead of inventing an improvement.',
    detail: 'Priority-aware · independently checked',
  },
  {
    number: '04',
    label: 'Review / export',
    icon: ShieldCheck,
    title: 'Leave an evidence trail',
    text: 'Inspect stocks, shipments, service, unmet demand, cover and assumptions. Record a simulation-only review and export the exact displayed run.',
    detail: 'JSON · CSV · audit ZIP',
  },
]

const workflowSteps = [
  {
    number: '01',
    label: 'Frame the question',
    title: 'Name the disruption before touching the plan.',
    text: 'Choose the source, facility or route under pressure and define the impact window. The desk keeps the scenario separate from the underlying network.',
  },
  {
    number: '02',
    label: 'Run the fixture',
    title: 'Apply the change to the same constrained system.',
    text: 'Supply, demand, route capacity, lead time and stock balance remain visible. There is no hidden fallback feed or silent assumption.',
  },
  {
    number: '03',
    label: 'Inspect the result',
    title: 'Follow the kilograms, not just the headline.',
    text: 'Compare service by group, daily stock, shipments, unmet demand and dependency paths. A risk label is a simulation result, not a forecast.',
  },
  {
    number: '04',
    label: 'Review and export',
    title: 'Make the boundary part of the decision.',
    text: 'A human acknowledges the synthetic case and assumptions before a review is recorded. The app does not dispatch stock or write to an external system.',
  },
]

const faqs = [
  {
    question: 'What is CommonRoot for?',
    answer: 'CommonRoot is a local-first engineering demonstration for testing LPG supply-disruption scenarios. It computes two allocation plans on the same fictional network and exposes the stocks, shipments, service, unmet demand and assumptions for human review.',
  },
  {
    question: 'What can I change in the planning desk?',
    answer: 'You can adjust demand, timing, an asset or a policy preset, then run a new simulation. Bundled fixtures cover import shock, route closure, route delay, facility outage and a normal reference case.',
  },
  {
    question: 'Is this connected to a live supply network?',
    answer: 'No. The included geography, demand, routes, stocks and policy assumptions are synthetic. The landing page and planning desk run locally, and a recorded review does not authorise rationing, dispatch stock or write to another system.',
  },
  {
    question: 'How are the two plans compared?',
    answer: 'Baseline and candidate are solved independently against the same adjusted network and physical constraints. The comparison preserves ties and reports when a result cannot be computed instead of fabricating a recommendation.',
  },
  {
    question: 'What does a review or export contain?',
    answer: 'A successful checked run can be acknowledged as simulation-only, with an optional note. Exports retain the exact scenario, network, policy, adjusted schedules, plan rows, district-risk tables, comparison, paths and warnings shown in the desk.',
  },
]

const insightPrompts = [
  {
    label: 'Question 01',
    title: 'Where is stock trapped?',
    text: 'Follow a facility outage through closing stock, outbound capacity and the districts that depend on it.',
  },
  {
    label: 'Question 02',
    title: 'What arrives too late?',
    text: 'A route can be open and still miss the horizon. Inspect lead time, dispatch day and arrival day together.',
  },
  {
    label: 'Question 03',
    title: 'Which assumption changes the result?',
    text: 'Keep demand, policy, units and provenance close to the output so a number has somewhere to be challenged.',
  },
]

function Brand({ onClick }) {
  return (
    <a className="brand" href="#home" onClick={onClick} aria-label="CommonRoot home">
      <span className="brand-mark" aria-hidden="true"><span>CR</span></span>
      <span className="brand-wordmark"><strong>CommonRoot</strong><small>LPG RESILIENCE / 01</small></span>
    </a>
  )
}

function Header({ menuOpen, setMenuOpen, onOpenDashboard }) {
  const closeMenu = () => setMenuOpen(false)

  useEffect(() => {
    const onKeyDown = (event) => {
      if (event.key === 'Escape') closeMenu()
    }
    document.addEventListener('keydown', onKeyDown)
    return () => document.removeEventListener('keydown', onKeyDown)
  }, [])

  return (
    <header className="site-header">
      <a className="skip-link" href="#main-content">Skip to content</a>
      <div className="container header-inner">
        <Brand onClick={closeMenu} />
        <nav className="desktop-nav" aria-label="Primary navigation">
          {navLinks.slice(0, 4).map((link) => <a key={link.href} href={link.href}>{link.label}</a>)}
        </nav>
        <div className="header-actions">
          <button type="button" className="dashboard-launch" onClick={onOpenDashboard}>
            Launch Dashboard <ArrowUpRight size={15} aria-hidden="true" />
          </button>
          <button type="button" className="menu-toggle" aria-expanded={menuOpen} aria-controls="site-menu" onClick={() => setMenuOpen((value) => !value)}>
            <span>{menuOpen ? 'Close' : 'Menu'}</span>{menuOpen ? <X size={18} aria-hidden="true" /> : <Menu size={19} aria-hidden="true" />}
          </button>
        </div>
      </div>
      <div className={`menu-overlay ${menuOpen ? 'is-open' : ''}`} onClick={closeMenu} aria-hidden="true" />
      <aside id="site-menu" className={`site-menu ${menuOpen ? 'is-open' : ''}`} aria-label="Site navigation" aria-hidden={!menuOpen}>
        <div className="menu-top"><span className="eyebrow">Navigate / CommonRoot</span><button type="button" className="menu-close" onClick={closeMenu} aria-label="Close navigation" tabIndex={menuOpen ? 0 : -1}><X size={18} aria-hidden="true" /></button></div>
        <div className="menu-context"><span className="status-dot is-live" /> Local-first LPG supply-resilience desk</div>
        <nav>
          {navLinks.map((link, index) => <a key={link.href} href={link.href} onClick={closeMenu} tabIndex={menuOpen ? 0 : -1}><span>0{index + 1}</span>{link.label}<ArrowRight size={16} aria-hidden="true" /></a>)}
          <button type="button" className="menu-dashboard" onClick={() => { closeMenu(); onOpenDashboard(); }} tabIndex={menuOpen ? 0 : -1}>
            <span>↗</span>Launch Operational Panel<ArrowUpRight size={16} aria-hidden="true" />
          </button>
        </nav>
        <div className="menu-footer"><span>Built for questions that need a visible answer.</span><a href="#contact" onClick={closeMenu} tabIndex={menuOpen ? 0 : -1}>Start with a scenario <ArrowRight size={15} aria-hidden="true" /></a></div>
      </aside>
    </header>
  )
}

function RouteMap() {
  return (
    <div className="route-map" role="img" aria-label="Illustrative LPG network with source, storage and district nodes connected by routes">
      <svg viewBox="0 0 620 254" aria-hidden="true" focusable="false">
        <path className="route-line route-line-main" d="M92 76 C176 34 226 58 294 111 S421 142 523 71" />
        <path className="route-line route-line-secondary" d="M92 76 C160 142 217 196 304 164 S420 178 523 196" />
        <path className="route-line route-line-secondary" d="M294 111 C315 84 336 68 382 62" />
        <path className="route-line route-line-muted" d="M382 62 C430 93 463 118 523 71" />
        <path className="route-line route-line-alert" d="M304 164 C372 151 424 145 475 143" />
        <circle className="route-node route-node-source" cx="92" cy="76" r="10" />
        <circle className="route-node route-node-hub" cx="294" cy="111" r="9" />
        <circle className="route-node route-node-hub" cx="304" cy="164" r="9" />
        <circle className="route-node route-node-district" cx="523" cy="71" r="8" />
        <circle className="route-node route-node-district" cx="523" cy="196" r="8" />
        <circle className="route-node route-node-district" cx="382" cy="62" r="7" />
        <circle className="route-pulse" cx="475" cy="143" r="18" />
      </svg>
      <span className="map-label map-label-source">IMPORT</span>
      <span className="map-label map-label-hub">HUB / A</span>
      <span className="map-label map-label-district">NORTH HILLS</span>
      <span className="map-label map-label-alert">ROUTE DELAY</span>
      <div className="map-scale"><span /><small>dependency view / not a live map</small></div>
    </div>
  )
}

function HeroConsole() {
  return (
    <div className="hero-console" aria-label="Illustrative CommonRoot planning desk snapshot">
      <div className="console-chrome">
        <div className="console-ident"><span className="window-dot" aria-hidden="true" /><span>RUN / DEMO-042</span></div>
        <span className="console-state"><CircleCheck size={13} aria-hidden="true" /> Checked fixture</span>
      </div>
      <div className="console-content">
        <div className="console-title-row"><div><span className="eyebrow eyebrow-mint">Scenario / import shock</span><h2>Supply pressure, made visible.</h2></div><span className="console-date">DAY 01—14</span></div>
        <div className="console-stats">
          <div><span>Horizon</span><strong>14 <small>days</small></strong></div>
          <div><span>Demand</span><strong>62.45 <small>t/day</small></strong></div>
          <div><span>Opening stock</span><strong>197.22 <small>t</small></strong></div>
        </div>
        <div className="console-workspace">
          <div className="console-map-panel">
            <div className="panel-heading"><span>Network / dependency view</span><span>14 nodes · 16 routes</span></div>
            <RouteMap />
            <div className="map-legend"><span><i className="legend-source" /> source</span><span><i className="legend-hub" /> facility</span><span><i className="legend-alert" /> affected route</span></div>
          </div>
          <div className="console-side-panel">
            <div className="panel-heading"><span>Scenario window</span><Clock3 size={13} aria-hidden="true" /></div>
            <div className="scenario-window"><strong>50%</strong><span>source supply reduction</span><em>DAY 01 — 10</em></div>
            <div className="console-divider" />
            <div className="plan-compare"><span className="panel-heading">Plans / same constraints</span><div><span>Baseline</span><b>READY</b></div><div><span>Candidate</span><b>READY</b></div></div>
            <div className="boundary-chip"><ShieldCheck size={13} aria-hidden="true" /><span>Human review required</span></div>
          </div>
        </div>
        <div className="console-log"><span><i className="status-dot is-live" /> synthetic network</span><span>units / kg LPG</span><span>external writes / 0</span></div>
      </div>
    </div>
  )
}

function HeroSection({ onOpenDashboard }) {
  return (
    <section id="home" className="hero-section" aria-labelledby="hero-title">
      <div className="hero-grid container">
        <div className="hero-copy">
          <div className="eyebrow hero-kicker"><span className="status-dot is-live" /> LPG SUPPLY RESILIENCE / DECISION SUPPORT</div>
          <h1 id="hero-title">Keep LPG moving when the <span>network changes.</span></h1>
          <p className="hero-lede">CommonRoot is a local-first planning desk for testing supply disruptions across sources, facilities, routes and district demand — before a scenario becomes a service gap.</p>
          <div className="hero-actions">
            <button type="button" className="button button-primary" onClick={onOpenDashboard}>
              Launch Operational Dashboard <ArrowRight size={16} aria-hidden="true" />
            </button>
            <a className="button button-quiet" href="#approach">
              See the operating loop <ArrowDownRight size={16} aria-hidden="true" />
            </a>
          </div>
          <div className="hero-boundary"><ShieldCheck size={16} aria-hidden="true" /><span><strong>Synthetic engineering demonstration.</strong> It computes reviewable scenarios; it does not dispatch stock or write to an operational system.</span></div>
        </div>
        <div className="hero-visual"><HeroConsole /><div className="hero-visual-caption"><span>01 / desk snapshot</span><span>Fictional network · explicit assumptions</span></div></div>
      </div>
      <div className="container hero-bottom-line"><span>What the desk answers</span><div><span>Where is the constraint?</span><span>What can still move?</span><span>What should a human review?</span></div><ArrowDownRight size={16} aria-hidden="true" /></div>
    </section>
  )
}

function SignalBand() {
  return (
    <section className="signal-band" aria-label="CommonRoot scope">
      <div className="container signal-band-grid">
        <div><span className="signal-label">Scope</span><strong>One network</strong><small>sources → facilities → districts</small></div>
        <div><span className="signal-label">Method</span><strong>Two plans</strong><small>same constraints, independently checked</small></div>
        <div><span className="signal-label">Unit</span><strong>kg LPG / day</strong><small>mass is explicit; assumptions are visible</small></div>
        <div><span className="signal-label">Boundary</span><strong>Review first</strong><small>no live dispatch or external writeback</small></div>
      </div>
    </section>
  )
}

function AboutSection() {
  return (
    <section id="about" className="section about-section" aria-labelledby="about-title">
      <div className="container about-grid">
        <div className="section-intro"><span className="eyebrow">Why this exists / 01</span><div className="section-index">CR<span>→</span>OPS</div></div>
        <div className="about-copy"><h2 id="about-title">A decision-support desk for the 24 hours before the decision.</h2><p>Supply networks become difficult to reason about when disruption, timing and competing demand arrive at once. CommonRoot turns a specific “what if?” into a bounded, inspectable run.</p><p>Load the network. Change one condition. Compare two plans. Then look at the rows that make the headline true.</p><a className="text-link" href="#capabilities">See what is inside the desk <ArrowRight size={15} aria-hidden="true" /></a></div>
        <div className="about-notes"><div className="note-card note-card-dark"><Cloud size={19} aria-hidden="true" /><span className="eyebrow eyebrow-mint">Local-first by design</span><strong>No account. No API key. No hidden feed.</strong><p>The bundled fixtures run on the machine and keep the scenario boundary in view.</p></div><div className="note-list"><div><span>01</span><p>Fictional geography, demand and routes</p></div><div><span>02</span><p>Explicit units, policy and provenance</p></div><div><span>03</span><p>Human acknowledgement before review</p></div></div></div>
      </div>
    </section>
  )
}

function CapabilitiesSection() {
  return (
    <section id="capabilities" className="section capabilities-section" aria-labelledby="capabilities-title">
      <div className="container"><div className="section-heading section-heading-split"><div><span className="eyebrow eyebrow-teal">Inside the desk / 02</span><h2 id="capabilities-title">Four views. One operational question.</h2></div><p>CommonRoot keeps inputs, scenario changes, allocation results and review evidence close together so you can trace a number back to its cause.</p></div><div className="desk-view-grid">{deskViews.map(({ number, label, icon: Icon, title, text, detail }) => <article className="desk-view-card" key={number}><div className="desk-view-top"><span className="card-number">{number}</span><span className="desk-view-icon"><Icon size={19} aria-hidden="true" /></span></div><span className="card-label">{label}</span><h3>{title}</h3><p>{text}</p><div className="card-detail"><Check size={13} aria-hidden="true" /> {detail}</div></article>)}</div></div>
    </section>
  )
}

function ApproachSection() {
  return (
    <section id="approach" className="section workflow-section" aria-labelledby="workflow-title">
      <div className="container"><div className="section-heading section-heading-split"><div><span className="eyebrow eyebrow-mint">Operating loop / 03</span><h2 id="workflow-title">From disruption question to reviewable run.</h2></div><p>The workflow is deliberately plain. Each step leaves a visible trace, and no result is presented as more certain than its inputs allow.</p></div><div className="workflow-list">{workflowSteps.map((step) => <article className="workflow-row" key={step.number}><div className="workflow-number">{step.number}</div><div className="workflow-label">{step.label}</div><div className="workflow-copy"><h3>{step.title}</h3><p>{step.text}</p></div><ArrowRight className="workflow-arrow" size={17} aria-hidden="true" /></article>)}</div><div className="workflow-cta"><Quote size={21} aria-hidden="true" /><p><strong>The useful answer is not always “choose candidate.”</strong> Sometimes the honest result is that both plans are equal, the inputs are infeasible or the boundary needs a human decision.</p><a className="text-link text-link-light" href={dashboardUrl}>Open an illustrative run <ArrowUpRight size={15} aria-hidden="true" /></a></div></div>
    </section>
  )
}

function ImpactSection() {
  return (
    <section id="impact" className="section evidence-section" aria-labelledby="evidence-title">
      <div className="container evidence-grid"><div className="evidence-intro"><span className="eyebrow eyebrow-orange">Run evidence / 04</span><h2 id="evidence-title">Numbers with a place to go.</h2><p>A CommonRoot run is not a glossy score. It is a compact record of the scenario, constraints, plan outputs and checks a person can inspect.</p><div className="evidence-list"><div><span>01</span><p>Scenario and adjusted schedules</p></div><div><span>02</span><p>Stocks, shipments and service rows</p></div><div><span>03</span><p>Risk, comparison and warnings</p></div></div><a className="button button-outline-light" href={dashboardUrl}>Inspect the planning desk <ArrowRight size={16} aria-hidden="true" /></a></div><div className="run-board"><div className="run-board-top"><span><i className="status-dot is-live" /> RUN / IMPORT SHOCK</span><span>DEMO-042 · CHECKED</span></div><div className="run-board-heading"><div><span className="eyebrow eyebrow-mint">Synthetic fixture / seed 42</span><h3>Same network.<br />Different pressure.</h3></div><span className="run-board-mark">CR<br /><small>01</small></span></div><div className="run-kpis"><div><strong>14</strong><span>day horizon</span></div><div><strong>62.45t</strong><span>demand / day</span></div><div><strong>197.22t</strong><span>opening stock</span></div></div><div className="run-table"><div className="run-table-head"><span>Review item</span><span>State</span></div><div><span>Source reduction</span><b>50% / days 01—10</b></div><div><span>Baseline plan</span><b className="state-ready">INDEPENDENT CHECK</b></div><div><span>Candidate plan</span><b className="state-ready">INDEPENDENT CHECK</b></div><div><span>External write</span><b>NONE</b></div></div><div className="run-board-foot"><ShieldCheck size={14} aria-hidden="true" /><span>Review boundary active — simulation only</span></div></div></div>
    </section>
  )
}

function InsightsSection() {
  return (
    <section id="insights" className="section insights-section" aria-labelledby="insights-title">
      <div className="container"><div className="section-heading section-heading-split"><div><span className="eyebrow eyebrow-teal">Questions to bring / 05</span><h2 id="insights-title">Start with the constraint, not the dashboard.</h2></div><p>Use the desk to make one operational question more precise. These are the questions the synthetic fixtures are designed to help you test.</p></div><div className="prompt-grid">{insightPrompts.map((item) => <article className="prompt-card" key={item.label}><span className="card-label">{item.label}</span><h3>{item.title}</h3><p>{item.text}</p><a className="text-link" href={dashboardUrl}>Take it to the desk <ArrowRight size={15} aria-hidden="true" /></a></article>)}</div></div>
    </section>
  )
}

function FaqSection() {
  const [openIndex, setOpenIndex] = useState(0)
  return (
    <section id="faq" className="section faq-section" aria-labelledby="faq-title">
      <div className="container faq-grid"><div className="faq-intro"><span className="eyebrow eyebrow-teal">Questions / 06</span><h2 id="faq-title">Keep the boundary clear.</h2><p>Plain answers for a synthetic planning tool. The first useful step is knowing exactly what a run can and cannot claim.</p><a className="text-link" href="#contact">Ask a question <ArrowRight size={15} aria-hidden="true" /></a></div><div className="faq-list">{faqs.map((item, index) => { const isOpen = openIndex === index; const answerId = `faq-answer-${index}`; return <div className={`faq-item ${isOpen ? 'is-open' : ''}`} key={item.question}><button type="button" className="faq-question" aria-expanded={isOpen} aria-controls={answerId} onClick={() => setOpenIndex(isOpen ? -1 : index)}><span>{item.question}</span><span className="faq-icon">{isOpen ? <Minus size={17} aria-hidden="true" /> : <Plus size={17} aria-hidden="true" />}</span></button><div id={answerId} className="faq-answer" role="region" hidden={!isOpen}><p>{item.answer}</p></div></div> })}</div></div>
    </section>
  )
}

function ContactSection({ onSubmitted }) {
  const [form, setForm] = useState({ name: '', email: '', organisation: '', message: '' })
  const [errors, setErrors] = useState({})
  const [submitted, setSubmitted] = useState(false)

  const update = (key, value) => {
    setForm((current) => ({ ...current, [key]: value }))
    if (errors[key]) setErrors((current) => ({ ...current, [key]: '' }))
    if (submitted) setSubmitted(false)
  }

  const submit = (event) => {
    event.preventDefault()
    const nextErrors = {}
    if (!form.name.trim()) nextErrors.name = 'Please add your name.'
    if (!/^\S+@\S+\.\S+$/.test(form.email)) nextErrors.email = 'Use a valid work email.'
    if (!form.message.trim() || form.message.trim().length < 20) nextErrors.message = 'Tell us a little more — 20 characters is enough to start.'
    setErrors(nextErrors)
    if (Object.keys(nextErrors).length > 0) return
    setSubmitted(true)
    onSubmitted?.()
  }

  const resetForm = () => {
    setSubmitted(false)
    setErrors({})
    setForm({ name: '', email: '', organisation: '', message: '' })
  }

  return (
    <section id="contact" className="contact-section" aria-labelledby="contact-title"><div className="container contact-grid"><div className="contact-copy"><span className="eyebrow eyebrow-mint">Start a scenario / 07</span><h2 id="contact-title">Bring the question that feels stuck.</h2><p>You do not need a perfect brief. Tell us what changed, what you cannot see yet and what a useful first run would help you decide.</p><div className="contact-points"><div><Mail size={17} aria-hidden="true" /><span><strong>Email</strong><a href="mailto:hello@commonroot.co">hello@commonroot.co</a></span></div><div><Phone size={17} aria-hidden="true" /><span><strong>Call</strong><a href="tel:+442080501240">+44 (0)20 8050 1240</a></span></div><div><MapPin size={17} aria-hidden="true" /><span><strong>Build location</strong><span>Local machine · synthetic network</span></span></div></div><div className="contact-boundary"><ShieldCheck size={16} aria-hidden="true" /><span>Client-side demonstration form. No message is sent from this page.</span></div></div><div className="contact-form-wrap">{submitted ? <div className="form-success"><span className="success-icon"><Check size={23} aria-hidden="true" /></span><span className="eyebrow eyebrow-teal">Message received</span><h3>We’ll be in touch shortly.</h3><p>Thanks for sharing the context. A member of the CommonRoot team will reply within two working days.</p><button type="button" className="button button-primary" onClick={resetForm}>Send another note <ArrowRight size={16} aria-hidden="true" /></button></div> : <form className="contact-form" onSubmit={submit} noValidate><div className="form-heading"><span className="eyebrow eyebrow-teal">No sales script / useful first reply</span><h3>What should we pressure-test?</h3></div><div className="form-row"><label htmlFor="contact-name">Full name<input id="contact-name" type="text" value={form.name} onChange={(event) => update('name', event.target.value)} aria-invalid={Boolean(errors.name)} aria-describedby={errors.name ? 'name-error' : undefined} autoComplete="name" />{errors.name ? <small id="name-error" className="field-error">{errors.name}</small> : null}</label><label htmlFor="contact-email">Work email<input id="contact-email" type="email" value={form.email} onChange={(event) => update('email', event.target.value)} aria-invalid={Boolean(errors.email)} aria-describedby={errors.email ? 'email-error' : undefined} autoComplete="email" />{errors.email ? <small id="email-error" className="field-error">{errors.email}</small> : null}</label></div><label htmlFor="contact-organisation">Organisation <span className="optional">optional</span><input id="contact-organisation" type="text" value={form.organisation} onChange={(event) => update('organisation', event.target.value)} autoComplete="organization" /></label><label htmlFor="contact-message">The operating question<textarea id="contact-message" value={form.message} onChange={(event) => update('message', event.target.value)} aria-invalid={Boolean(errors.message)} aria-describedby={errors.message ? 'message-error' : undefined} placeholder="For example: what happens if an import source is reduced for ten days?" />{errors.message ? <small id="message-error" className="field-error">{errors.message}</small> : null}</label><div className="form-submit-row"><span><CircleCheck size={14} aria-hidden="true" /> Your note stays in this demo</span><button type="submit" className="button button-primary">Send the question <ArrowRight size={16} aria-hidden="true" /></button></div></form>}</div></div></section>
  )
}

function Footer() {
  return (
    <footer className="site-footer"><div className="container footer-grid"><div className="footer-brand"><Brand /><p>Local-first LPG supply-resilience decision support for synthetic, reviewable scenarios.</p><div className="footer-meta"><span><i className="status-dot is-live" /> Built for inspection</span><span>© 2026 CommonRoot</span></div></div><div className="footer-links"><div><span className="eyebrow">Explore</span><a href="#about">Why it exists</a><a href="#capabilities">Desk views</a><a href="#impact">Run evidence</a></div><div><span className="eyebrow">Use the desk</span><a href={dashboardUrl}>Open planning desk</a><a href="#approach">Operating loop</a><a href="#faq">FAQ</a></div></div><div className="footer-social"><span className="eyebrow">Signal</span><div><a href="https://www.linkedin.com/" target="_blank" rel="noreferrer" aria-label="LinkedIn"><Globe2 size={16} aria-hidden="true" /></a><a href="mailto:hello@commonroot.co" aria-label="Email CommonRoot"><Mail size={16} aria-hidden="true" /></a><a href="#contact" aria-label="Contact CommonRoot"><UsersRound size={16} aria-hidden="true" /></a></div></div></div><div className="container footer-bottom"><span>Illustrative content / synthetic network / no operational writeback</span><span><a href="#home">Privacy</a><a href="#home">Terms</a><a href="#home">Back to top <ArrowUp size={13} aria-hidden="true" /></a></span></div></footer>
  )
}

function BackToTop() {
  const [visible, setVisible] = useState(false)
  useEffect(() => {
    const onScroll = () => setVisible(window.scrollY > 560)
    window.addEventListener('scroll', onScroll, { passive: true })
    onScroll()
    return () => window.removeEventListener('scroll', onScroll)
  }, [])
  const goToTop = () => {
    const reduceMotion = window.matchMedia('(prefers-reduced-motion: reduce)').matches
    window.scrollTo({ top: 0, behavior: reduceMotion ? 'auto' : 'smooth' })
  }
  return <button type="button" className={`back-to-top ${visible ? 'is-visible' : ''}`} onClick={goToTop} aria-label="Back to top"><ArrowUp size={17} aria-hidden="true" /></button>
}

function checkIsDashboard() {
  const path = window.location.pathname.toLowerCase()
  const hash = window.location.hash.toLowerCase()
  return path.includes('dashboard') || path.includes('app') || hash.includes('dashboard') || hash.includes('app')
}

function App() {
  const [view, setView] = useState(() => (checkIsDashboard() ? 'dashboard' : 'landing'))
  const [menuOpen, setMenuOpen] = useState(false)
  const [notice, setNotice] = useState('')

  useEffect(() => {
    const handlePopState = () => {
      setView(checkIsDashboard() ? 'dashboard' : 'landing')
    }
    window.addEventListener('popstate', handlePopState)
    window.addEventListener('hashchange', handlePopState)
    return () => {
      window.removeEventListener('popstate', handlePopState)
      window.removeEventListener('hashchange', handlePopState)
    }
  }, [])

  const openDashboard = () => {
    window.location.hash = '#/dashboard'
    setView('dashboard')
    window.scrollTo({ top: 0, behavior: 'instant' })
  }

  const backToLanding = () => {
    window.location.hash = ''
    setView('landing')
    window.scrollTo({ top: 0, behavior: 'instant' })
  }

  const onSubmitted = () => {
    setNotice('Thanks — your question is on its way.')
    window.setTimeout(() => setNotice(''), 4200)
  }

  if (view === 'dashboard') {
    return <Dashboard onBackToLanding={backToLanding} />
  }

  return (
    <div className="control-room-site">
      <Header menuOpen={menuOpen} setMenuOpen={setMenuOpen} onOpenDashboard={openDashboard} />
      <main id="main-content">
        <HeroSection onOpenDashboard={openDashboard} />
        <SignalBand />
        <AboutSection />
        <CapabilitiesSection />
        <ApproachSection />
        <ImpactSection />
        <InsightsSection />
        <FaqSection />
        <ContactSection onSubmitted={onSubmitted} />
      </main>
      <Footer />
      <BackToTop />
      {notice ? (
        <div className="site-toast" role="status" aria-live="polite">
          <CircleCheck size={16} aria-hidden="true" />
          {notice}
        </div>
      ) : null}
    </div>
  )
}

createRoot(document.getElementById('root')).render(<App />)
