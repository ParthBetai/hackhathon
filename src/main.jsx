import React, { useEffect, useState, useRef } from 'react'
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
  CircleAlert,
  CircleCheck,
  Clock3,
  Cloud,
  Database,
  FileCheck2,
  Flame,
  Globe2,
  HardDrive,
  Info,
  Layers,
  Mail,
  MapPin,
  Menu,
  Minus,
  Network,
  Phone,
  Plus,
  Quote,
  Radio,
  RotateCcw,
  ShieldAlert,
  ShieldCheck,
  Sliders,
  Sparkles,
  TrendingUp,
  Truck,
  UsersRound,
  X,
} from 'lucide-react'
import Dashboard from './Dashboard'
import './styles.css'

const navLinks = [
  { href: '#about', label: 'Why it exists' },
  { href: '#capabilities', label: 'Desk views' },
  { href: '#approach', label: 'Workflow' },
  { href: '#impact', label: 'Run evidence' },
  { href: '#faq', label: 'FAQ' },
  { href: '#contact', label: 'Inquiry' },
]

const tickerItems = [
  'SIMULATING 14-DAY PLANNING HORIZON',
  'LEXICOGRAPHIC PRIORITY OPTIMIZATION (ESSENTIAL > DOMESTIC > COMMERCIAL)',
  'OR-TOOLS GLOP CONTINUOUS LP SOLVER',
  'LOCAL-FIRST PRIVACY · ZERO EXTERNAL DISPATCH',
  'DETERMINISTIC MASS BALANCE: 832,220 KG CONSERVED',
  'HONEST REPORTING · TIES PRESERVED · NO FABRICATED METRICS',
  'HUMAN-IN-THE-LOOP ALLOCATION REVIEW GATE',
  'CRYOGENIC & PRESSURE-VESSEL SUPPLY CORRIDORS MAPPED',
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
    text: 'Run baseline and candidate allocations against the same physical constraints. If the plans tie, the desk reports an honest tie instead of inventing an improvement.',
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
    answer:
      'CommonRoot is a local-first engineering demonstration for testing LPG supply-disruption scenarios. It computes two allocation plans on the same fictional network and exposes stocks, shipments, service, unmet demand and assumptions for human review.',
  },
  {
    question: 'What can I change in the planning desk?',
    answer:
      'You can adjust demand, timing, an asset or a policy preset, then run a new simulation. Bundled fixtures cover import shock, route closure, route delay, facility outage and a normal reference case.',
  },
  {
    question: 'Is this connected to a live supply network?',
    answer:
      'No. The included geography, demand, routes, stocks and policy assumptions are synthetic. The landing page and planning desk run locally, and a recorded review does not authorise rationing, dispatch stock or write to another system.',
  },
  {
    question: 'How are the two plans compared?',
    answer:
      'Baseline and candidate are solved independently against the same adjusted network and physical constraints. The comparison preserves ties and reports when a result cannot be computed instead of fabricating a recommendation.',
  },
  {
    question: 'What does a review or export contain?',
    answer:
      'A successful checked run can be acknowledged as simulation-only, with an optional note. Exports retain the exact scenario, network, policy, adjusted schedules, plan rows, district-risk tables, comparison, paths and warnings shown in the desk.',
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

/* =========================================================================
   BRAND & NAVIGATION
   ========================================================================= */
function Brand({ onClick }) {
  return (
    <a className="brand" href="#home" onClick={onClick} aria-label="CommonRoot home">
      <span className="brand-mark" aria-hidden="true">
        <span>CR</span>
      </span>
      <span className="brand-wordmark">
        <strong>CommonRoot</strong>
        <small>LPG RESILIENCE / 01</small>
      </span>
    </a>
  )
}

function Header({ menuOpen, setMenuOpen, onOpenDashboard, activeSection, scrollPercent }) {
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
      <div className="scroll-progress-bar" style={{ width: `${scrollPercent}%` }} aria-hidden="true" />
      <a className="skip-link" href="#main-content">
        Skip to content
      </a>
      <div className="container header-inner">
        <Brand onClick={closeMenu} />
        <nav className="desktop-nav" aria-label="Primary navigation">
          {navLinks.map((link) => {
            const sectionId = link.href.replace('#', '')
            const isActive = activeSection === sectionId
            return (
              <a key={link.href} href={link.href} className={isActive ? 'is-active-nav' : ''}>
                {link.label}
              </a>
            )
          })}
        </nav>
        <div className="header-actions">
          <button type="button" className="dashboard-launch" onClick={onOpenDashboard}>
            <span>Launch Desk</span>
            <ArrowUpRight size={14} aria-hidden="true" />
          </button>
          <button
            type="button"
            className="menu-toggle"
            aria-expanded={menuOpen}
            aria-controls="site-menu"
            onClick={() => setMenuOpen((v) => !v)}
          >
            <span>{menuOpen ? 'Close' : 'Menu'}</span>
            {menuOpen ? <X size={17} aria-hidden="true" /> : <Menu size={17} aria-hidden="true" />}
          </button>
        </div>
      </div>

      <div className={`menu-overlay ${menuOpen ? 'is-open' : ''}`} onClick={closeMenu} aria-hidden="true" />
      <aside
        id="site-menu"
        className={`site-menu ${menuOpen ? 'is-open' : ''}`}
        aria-label="Site navigation"
        aria-hidden={!menuOpen}
      >
        <div className="menu-top">
          <span className="eyebrow">Navigate / CommonRoot</span>
          <button type="button" className="menu-close" onClick={closeMenu} aria-label="Close navigation">
            <X size={18} aria-hidden="true" />
          </button>
        </div>
        <div className="menu-context">
          Local-first LPG supply-resilience desk
        </div>
        <nav>
          {navLinks.map((link, index) => (
            <a key={link.href} href={link.href} onClick={closeMenu}>
              <span>0{index + 1}</span>
              {link.label}
              <ArrowRight size={15} aria-hidden="true" />
            </a>
          ))}
          <button
            type="button"
            className="menu-dashboard"
            onClick={() => {
              closeMenu()
              onOpenDashboard()
            }}
          >
            <span>ENTER</span>
            Launch Operational Desk
            <ArrowUpRight size={15} aria-hidden="true" />
          </button>
        </nav>
        <div className="menu-footer">
          <span>Built for supply questions that need an auditable answer.</span>
        </div>
      </aside>
    </header>
  )
}

function TickerBar() {
  return (
    <div className="ticker-wrapper" aria-hidden="true">
      <div className="ticker-track">
        {[...tickerItems, ...tickerItems].map((item, index) => (
          <span key={index} className="ticker-item">
            <span className="ticker-bullet">◆</span> {item}
          </span>
        ))}
      </div>
    </div>
  )
}

/* =========================================================================
   ANIMATED LPG INDUSTRIAL CENTERPIECE COMPONENT
   Refinery Distillation Splitter, Horton Spherical Tank, Composite Cylinder
   ========================================================================= */
function LpgIndustrialCenterpiece({ activeFixture, onSelectFixture }) {
  const [activeAsset, setActiveAsset] = useState(null)

  const isShock = activeFixture === 'import_shock'
  const isOutage = activeFixture === 'route_closure'
  const isDelay = activeFixture === 'route_delay'

  return (
    <div className="hero-centerpiece-container" aria-label="Animated LPG Infrastructure Complex">
      {/* Top Scenario Fixture Selector Bar */}
      <div className="centerpiece-header">
        <div className="centerpiece-title-tag">
          <Flame size={15} color="#e8d1cb" aria-hidden="true" />
          <span>LPG SUPPLY & FRACTIONATION INFRASTRUCTURE</span>
        </div>
        <div className="centerpiece-pill-group">
          {[
            { id: 'nominal', label: '01 NOMINAL REFLUX' },
            { id: 'import_shock', label: '02 IMPORT SHOCK (-50%)' },
            { id: 'route_closure', label: '03 BOTTLING OUTAGE' },
            { id: 'route_delay', label: '04 TRANSIT LAG (+3D)' },
          ].map((item) => (
            <button
              key={item.id}
              type="button"
              className={`centerpiece-pill ${activeFixture === item.id ? 'is-active' : ''}`}
              onClick={() => onSelectFixture(item.id)}
            >
              {item.label}
            </button>
          ))}
        </div>
        <div className="centerpiece-badge">
          <span>832,220 KG BALANCED</span>
        </div>
      </div>

      {/* SVG Canvas Area */}
      <div className="lpg-centerpiece-stage">
        <svg className="lpg-centerpiece-svg" viewBox="0 0 1000 360" aria-hidden="true">
          <defs>
            <radialGradient id="sphereGrad" cx="35%" cy="32%" r="68%">
              <stop offset="0%" stopColor="#334155" />
              <stop offset="55%" stopColor="#1e293b" />
              <stop offset="100%" stopColor="#0b101a" />
            </radialGradient>

            <linearGradient id="cylinderGrad" x1="0%" y1="0%" x2="100%" y2="0%">
              <stop offset="0%" stopColor="#0f172a" />
              <stop offset="35%" stopColor="#334155" />
              <stop offset="70%" stopColor="#1e293b" />
              <stop offset="100%" stopColor="#090d16" />
            </linearGradient>

            <linearGradient id="liquidGrad" x1="0%" y1="0%" x2="0%" y2="100%">
              <stop offset="0%" stopColor={isShock ? '#c27a56' : '#15803d'} stopOpacity="0.85" />
              <stop offset="100%" stopColor={isShock ? '#8a4321' : '#0e3d27'} stopOpacity="0.95" />
            </linearGradient>

            <linearGradient id="towerGrad" x1="0%" y1="0%" x2="100%" y2="0%">
              <stop offset="0%" stopColor="#1e293b" />
              <stop offset="45%" stopColor="#475569" />
              <stop offset="85%" stopColor="#1e293b" />
              <stop offset="100%" stopColor="#0f172a" />
            </linearGradient>

            <linearGradient id="flareGrad" x1="0%" y1="100%" x2="0%" y2="0%">
              <stop offset="0%" stopColor="#ef4444" />
              <stop offset="60%" stopColor="#c27a56" />
              <stop offset="100%" stopColor="#fef08a" />
            </linearGradient>

            <clipPath id="sphereClip">
              <circle cx="500" cy="185" r="77" />
            </clipPath>
          </defs>

          {/* Ambient Ground Grid Line */}
          <line x1="60" y1="320" x2="940" y2="320" stroke="rgba(255,255,255,0.12)" strokeWidth="1" strokeDasharray="4 6" />

          {/* ================= 1. REFINERY DISTILLATION COLUMN (LEFT) ================= */}
          <g
            className="lpg-asset-interactive"
            onMouseEnter={() =>
              setActiveAsset({
                title: 'FRACTIONATION SPLITTER C-101',
                subtitle: 'Propane / Butane Fractionation Column',
                spec: 'Design Cap: 40,000 kg/day · 24 Trays',
                state: isShock ? 'THROTTLED (-50% Maritime Inflow)' : 'NOMINAL REFLUX STREAM',
              })
            }
            onMouseLeave={() => setActiveAsset(null)}
          >
            {/* Concrete Pad */}
            <rect x="150" y="310" width="80" height="12" rx="2" fill="#0f172a" stroke="rgba(255,255,255,0.18)" strokeWidth="1" />

            {/* Tower Body */}
            <rect x="160" y="86" width="60" height="224" rx="4" fill="url(#towerGrad)" stroke="#e8d1cb" strokeWidth="1.2" />

            {/* Top Dished Head */}
            <ellipse cx="190" cy="86" rx="30" ry="12" fill="#334155" stroke="#e8d1cb" strokeWidth="1.2" />

            {/* Safety Flare Stack */}
            <line x1="190" y1="74" x2="190" y2="48" stroke="#cbd5e1" strokeWidth="3" />
            <path className="lpg-flare-flame" d="M187 48 C185 40, 190 32, 190 26 C190 32, 195 40, 193 48 Z" fill="url(#flareGrad)" />

            {/* Fractionation Trays with Sight Inspection Windows & Rising Vapor */}
            {[120, 155, 190, 225, 260, 290].map((y, idx) => (
              <g key={idx}>
                <line x1="160" y1={y} x2="220" y2={y} stroke="rgba(255,255,255,0.22)" strokeWidth="1" />
                <rect x="180" y={y - 8} width="20" height="6" rx="3" fill="rgba(194,122,86,0.2)" stroke="#c27a56" strokeWidth="0.8" />
                <circle cx="190" cy={y - 5} r="1.5" fill="#fef08a" className="lpg-vapor-bubble" />
              </g>
            ))}

            {/* Ladder & Structural Cage */}
            <line x1="222" y1="90" x2="222" y2="310" stroke="rgba(255,255,255,0.4)" strokeWidth="1.5" />
            {[100, 130, 160, 190, 220, 250, 280, 305].map((y, i) => (
              <line key={i} x1="219" y1={y} x2="225" y2={y} stroke="rgba(255,255,255,0.3)" strokeWidth="1" />
            ))}

            {/* Reflux Pipe Loop */}
            <path d="M 190 86 C 240 86, 245 140, 220 140" fill="none" stroke="#e8d1cb" strokeWidth="1.6" />

            {/* Text HUD Tags */}
            <text x="190" y="336" textAnchor="middle" className="lpg-hud-tag">
              REFINERY TOWER C-101
            </text>
            <text x="190" y="348" textAnchor="middle" className="lpg-hud-val">
              40,000 kg/d · 24 Trays
            </text>
          </g>

          {/* ================= 2. HORTON SPHERICAL STORAGE TANK (CENTER) ================= */}
          <g
            className="lpg-asset-interactive"
            onMouseEnter={() =>
              setActiveAsset({
                title: 'HORTON SPHERE S-101',
                subtitle: 'Bulk Cryogenic Pressure-Vessel Buffer',
                spec: 'Storage Cap: 120,000 kg · Pressure: 15.2 Bar',
                state: isShock ? 'DRAINING BUFFER (62,400 kg)' : 'STEADY STORAGE (85% Fill)',
              })
            }
            onMouseLeave={() => setActiveAsset(null)}
          >
            {/* Tubular Steel Legs */}
            {[432, 452, 475, 525, 548, 568].map((lx, i) => (
              <g key={i}>
                <line x1={lx} y1="230" x2={lx} y2="315" stroke="rgba(255,255,255,0.35)" strokeWidth="2.5" />
                <rect x={lx - 4} y="313" width="8" height="7" fill="#0f172a" stroke="rgba(255,255,255,0.3)" strokeWidth="1" />
              </g>
            ))}
            {/* Diagonal Bracing */}
            <line x1="432" y1="280" x2="475" y2="240" stroke="rgba(255,255,255,0.2)" strokeWidth="1" />
            <line x1="525" y1="240" x2="568" y2="280" stroke="rgba(255,255,255,0.2)" strokeWidth="1" />

            {/* Pressure Sphere Body */}
            <circle cx="500" cy="185" r="77" fill="url(#sphereGrad)" stroke="#e8d1cb" strokeWidth="1.8" />

            {/* Dynamic Liquid Wave Inside Sphere */}
            <g clipPath="url(#sphereClip)">
              <rect x="420" y={isShock ? '180' : '150'} width="160" height="120" fill="url(#liquidGrad)" />
              <path
                className="lpg-liquid-fill"
                d={
                  isShock
                    ? 'M 410 180 Q 450 174, 500 180 T 590 180 L 590 270 L 410 270 Z'
                    : 'M 410 150 Q 450 144, 500 150 T 590 150 L 590 270 L 410 270 Z'
                }
                fill="url(#liquidGrad)"
                opacity="0.85"
              />
            </g>

            {/* Seam Band */}
            <ellipse cx="500" cy="185" rx="77" ry="16" fill="none" stroke="rgba(255,255,255,0.2)" strokeWidth="1" strokeDasharray="3 4" />

            {/* Relief Valve Dome */}
            <rect x="492" y="100" width="16" height="8" rx="2" fill="#334155" stroke="#e8d1cb" strokeWidth="1" />
            <line x1="500" y1="100" x2="500" y2="88" stroke="#cbd5e1" strokeWidth="2" />
            <circle cx="500" cy="86" r="3.5" fill="#f59e0b" />

            {/* Pressure Readout HUD on Front of Sphere */}
            <rect x="466" y="172" width="68" height="26" rx="4" fill="rgba(4,7,13,0.88)" stroke="rgba(255,255,255,0.2)" strokeWidth="1" />
            <text x="500" y="184" textAnchor="middle" fill="#10b981" fontFamily="JetBrains Mono" fontSize="8" fontWeight="700">
              {isShock ? '62,400 KG' : '120,000 KG'}
            </text>
            <text x="500" y="194" textAnchor="middle" fill="#94a3b8" fontFamily="JetBrains Mono" fontSize="7">
              15.2 BAR · 85%
            </text>

            {/* Text HUD Tags */}
            <text x="500" y="336" textAnchor="middle" className="lpg-hud-tag">
              HORTON SPHERE S-101
            </text>
            <text x="500" y="348" textAnchor="middle" className="lpg-hud-val">
              120,000 kg cap · Pressure Buffer
            </text>
          </g>

          {/* ================= 3. COMPOSITE LPG CYLINDER (RIGHT) ================= */}
          <g
            className="lpg-asset-interactive"
            onMouseEnter={() =>
              setActiveAsset({
                title: 'COMPOSITE CYLINDER B-301',
                subtitle: '14.2 kg Domestic Consumer Cylinder (Type 4)',
                spec: 'Tare Wt: 5.2 kg · Test Pressure: 30 Bar',
                state: isOutage ? 'DISPATCH HALTED (Bottling Outage)' : 'SEALED & INSPECTED',
              })
            }
            onMouseLeave={() => setActiveAsset(null)}
          >
            {/* Stand Ring Base */}
            <path d="M 764 300 L 760 314 L 840 314 L 836 300 Z" fill="#0f172a" stroke="rgba(255,255,255,0.25)" strokeWidth="1" />

            {/* Composite Vessel Body */}
            <rect x="760" y="148" width="80" height="152" rx="22" fill="url(#cylinderGrad)" stroke="#e8d1cb" strokeWidth="1.6" />

            {/* Protective Collar Shroud with Dual Handles */}
            <path d="M 770 148 C 770 120, 830 120, 830 148 Z" fill="#1e293b" stroke="#e8d1cb" strokeWidth="1.4" />
            <rect x="785" y="132" width="30" height="8" rx="4" fill="#04070d" stroke="rgba(255,255,255,0.25)" strokeWidth="1" />

            {/* Brass Valve Handwheel */}
            <rect x="795" y="118" width="10" height="14" fill="#f59e0b" stroke="#d97706" strokeWidth="1" />
            <ellipse cx="800" cy="116" rx="9" ry="3" fill="#b45309" />

            {/* Vertical Inspection Sight Strip */}
            <rect x="796" y="195" width="8" height="60" rx="4" fill="rgba(4,7,13,0.8)" stroke="rgba(255,255,255,0.2)" strokeWidth="0.8" />
            <rect x="797.5" y="210" width="5" height="42" rx="2.5" fill="#10b981" />

            {/* Analog Pressure Gauge with Oscillating Needle */}
            <circle cx="800" cy="278" r="10" fill="#0b101a" stroke="#e8d1cb" strokeWidth="1" />
            <line className="lpg-dial-needle" x1="800" y1="278" x2="800" y2="271" stroke="#ef4444" strokeWidth="1.5" strokeLinecap="round" />

            {/* Text HUD Tags */}
            <text x="800" y="336" textAnchor="middle" className="lpg-hud-tag">
              COMPOSITE CYLINDER B-301
            </text>
            <text x="800" y="348" textAnchor="middle" className="lpg-hud-val">
              14.2 kg Domestic · Type 4
            </text>
          </g>

          {/* ================= 4. CONNECTING PIPELINE MANIFOLDS ================= */}
          {/* Pipe 1: Deepwater Harbor to Splitter */}
          <path d="M 60 210 L 160 210" fill="none" stroke="rgba(255,255,255,0.2)" strokeWidth="4" />
          <path
            className="lpg-pipe-active"
            d="M 60 210 L 160 210"
            fill="none"
            stroke={isShock ? '#c27a56' : '#15803d'}
            strokeWidth="2.5"
          />

          {/* Pipe 2: Splitter Tower to Horton Sphere */}
          <path d="M 220 185 C 330 140, 380 160, 423 185" fill="none" stroke="rgba(255,255,255,0.2)" strokeWidth="4" />
          <path
            className="lpg-pipe-active"
            d="M 220 185 C 330 140, 380 160, 423 185"
            fill="none"
            stroke={isShock ? '#c27a56' : '#15803d'}
            strokeWidth="2.5"
          />

          {/* Pipe 3: Horton Sphere to Bottling Manifold */}
          <path d="M 577 185 C 640 185, 700 210, 760 210" fill="none" stroke="rgba(255,255,255,0.2)" strokeWidth="4" />
          <path
            className="lpg-pipe-active"
            d="M 577 185 C 640 185, 700 210, 760 210"
            fill="none"
            stroke={isOutage ? '#ef4444' : '#15803d'}
            strokeWidth="2.5"
          />

          {/* High-Pressure Pipeline Valves */}
          <circle cx="280" cy="168" r="5" fill="#04070d" stroke="#e8d1cb" strokeWidth="1.2" />
          <circle cx="280" cy="168" r="2.5" fill={isShock ? '#c27a56' : '#15803d'} />

          <circle cx="670" cy="198" r="5" fill="#04070d" stroke="#e8d1cb" strokeWidth="1.2" />
          <circle cx="670" cy="198" r="2.5" fill={isOutage ? '#ef4444' : '#15803d'} />
        </svg>

        {/* Floating Dossier Tooltip */}
        {activeAsset && (
          <div className="lpg-dossier-tooltip">
            <div>
              <strong style={{ display: 'block', fontFamily: 'Plus Jakarta Sans', fontWeight: 700, fontSize: '11px', color: '#e8d1cb', letterSpacing: '0.05em' }}>
                {activeAsset.title}
              </strong>
              <span style={{ fontSize: '11px', color: '#94a3b8' }}>{activeAsset.subtitle}</span>
            </div>
            <div style={{ borderLeft: '1px solid rgba(255,255,255,0.14)', paddingLeft: '14px', fontFamily: 'JetBrains Mono', fontSize: '10.5px' }}>
              <span style={{ display: 'block', color: '#e2e8f0' }}>{activeAsset.spec}</span>
              <span style={{ color: isShock ? '#c27a56' : '#15803d', fontWeight: 700 }}>{activeAsset.state}</span>
            </div>
          </div>
        )}
      </div>
    </div>
  )
}

/* =========================================================================
   HERO SECTION
   ========================================================================= */
function HeroSection({ onOpenDashboard }) {
  const [activeFixture, setActiveFixture] = useState('nominal')

  return (
    <section id="home" className="hero-section" aria-labelledby="hero-title">
      <div className="container">
        <div className="hero-header-block">
          <div className="eyebrow hero-kicker">
            <span>SYNTHETIC DEMONSTRATION · LPG SUPPLY RESILIENCE</span>
          </div>
          <h1 id="hero-title" className="hero-title">
            Keep LPG moving when the <span>network shocks.</span>
          </h1>
          <p className="hero-lede">
            CommonRoot is a local-first mathematical planning desk for stress-testing cryogenic and pressure-vessel LPG
            flows across import terminals, bulk hubs, bottling plants and district gates — before a disruption becomes an
            outage.
          </p>
          <div className="hero-actions">
            <button type="button" className="button button-primary" onClick={onOpenDashboard}>
              <span>Launch Operational Desk</span>
              <ArrowRight size={16} aria-hidden="true" />
            </button>
            <a className="button button-quiet" href="#approach">
              <span>Explore 14-Day Loop</span>
              <ArrowDownRight size={16} aria-hidden="true" />
            </a>
          </div>
          <div className="hero-boundary">
            <ShieldCheck size={16} color="#e8d1cb" aria-hidden="true" />
            <span>
              <strong>Deterministic conservation laws.</strong> Strict mass balances (Ending Stock = Starting Stock +
              Inflows - Outflows). Zero hallucinated metrics.
            </span>
          </div>
        </div>

        {/* Dedicated Animated LPG Centerpiece Stage */}
        <LpgIndustrialCenterpiece activeFixture={activeFixture} onSelectFixture={setActiveFixture} />

        {/* Bottom Line Operational Triad */}
        <div className="hero-bottom-line">
          <span>What the desk answers</span>
          <div>
            <span>Where is the bottleneck?</span>
            <span>What can still move?</span>
            <span>What should a human review?</span>
          </div>
          <ArrowDownRight size={16} color="#e8d1cb" aria-hidden="true" />
        </div>
      </div>
    </section>
  )
}

/* =========================================================================
   SIGNAL BAND
   ========================================================================= */
function SignalBand() {
  return (
    <section className="signal-band" aria-label="CommonRoot scope">
      <div className="container signal-band-grid">
        <div>
          <span className="signal-label">01 Scope</span>
          <strong>14-Node System</strong>
          <small>Terminals → Hubs → Bottling → Districts</small>
        </div>
        <div>
          <span className="signal-label">02 Determinism</span>
          <strong>OR-Tools GLOP</strong>
          <small>Continuous linear programming, ties kept</small>
        </div>
        <div>
          <span className="signal-label">03 Unit of Truth</span>
          <strong>832,220 kg LPG</strong>
          <small>Strict physical mass balance conserved</small>
        </div>
        <div>
          <span className="signal-label">04 Safety Gate</span>
          <strong>Local-First Review</strong>
          <small>Zero external dispatch; human certified</small>
        </div>
      </div>
    </section>
  )
}

/* =========================================================================
   ABOUT SECTION
   ========================================================================= */
function AboutSection({ onOpenDashboard }) {
  return (
    <section id="about" className="section about-section" aria-labelledby="about-title">
      <div className="container about-grid">
        <div className="section-intro">
          <span className="eyebrow">Why this exists / 01</span>
          <div className="section-index">
            CR<span>→</span>OPS
          </div>
        </div>
        <div className="about-copy">
          <h2 id="about-title">A decision-support desk for the 24 hours before the decision.</h2>
          <p>
            Supply networks become difficult to reason about when disruption, timing and competing demand arrive at once.
            CommonRoot turns a specific “what if?” into a bounded, inspectable run.
          </p>
          <p>
            Load the network. Change one condition. Compare two plans. Then inspect the rows that make the headline true.
          </p>
          <div className="about-actions-row">
            <a className="text-link" href="#capabilities">
              <span>See what is inside the desk</span>
              <ArrowRight size={14} aria-hidden="true" />
            </a>
            <button type="button" className="text-link text-link-accent" onClick={onOpenDashboard}>
              <span>Launch interactive desk</span>
              <ArrowUpRight size={14} aria-hidden="true" />
            </button>
          </div>
        </div>
        <div className="about-notes">
          <div className="note-card">
            <Cloud size={19} color="#e8d1cb" aria-hidden="true" />
            <span className="eyebrow eyebrow-mint">Local-first by design</span>
            <strong>No account. No external API key. No hidden feed.</strong>
            <p>The bundled fixtures run on the machine and keep the scenario boundary in view.</p>
          </div>
          <div className="note-list">
            <div>
              <span>01</span>
              <p>Fictional geography, demand and routes</p>
            </div>
            <div>
              <span>02</span>
              <p>Explicit units, policy and provenance</p>
            </div>
            <div>
              <span>03</span>
              <p>Human acknowledgement before review</p>
            </div>
          </div>
        </div>
      </div>
    </section>
  )
}

/* =========================================================================
   CAPABILITIES SECTION
   ========================================================================= */
function CapabilitiesSection({ onOpenDashboard }) {
  return (
    <section id="capabilities" className="section capabilities-section" aria-labelledby="capabilities-title">
      <div className="container">
        <div className="section-heading section-heading-split">
          <div>
            <span className="eyebrow eyebrow-teal">Inside the desk / 02</span>
            <h2 id="capabilities-title">Four views. One operational question.</h2>
          </div>
          <p>
            CommonRoot keeps inputs, scenario changes, allocation results and review evidence close together so you can
            trace any number back to its physical cause.
          </p>
        </div>
        <div className="desk-view-grid">
          {deskViews.map(({ number, label, icon: Icon, title, text, detail }) => (
            <article
              className="desk-view-card"
              key={number}
              onClick={onOpenDashboard}
              role="button"
              tabIndex={0}
              onKeyDown={(e) => {
                if (e.key === 'Enter') onOpenDashboard()
              }}
            >
              <div className="desk-view-top">
                <span className="card-number">{number}</span>
                <span className="desk-view-icon">
                  <Icon size={19} aria-hidden="true" />
                </span>
              </div>
              <span className="card-label">{label}</span>
              <h3>{title}</h3>
              <p>{text}</p>
              <div className="card-detail">
                <span>
                  <Check size={12} color="#10b981" aria-hidden="true" /> {detail}
                </span>
                <span className="card-click-hint">Inspect →</span>
              </div>
            </article>
          ))}
        </div>
      </div>
    </section>
  )
}

/* =========================================================================
   APPROACH SECTION
   ========================================================================= */
function ApproachSection({ onOpenDashboard }) {
  return (
    <section id="approach" className="section workflow-section" aria-labelledby="workflow-title">
      <div className="container">
        <div className="section-heading section-heading-split">
          <div>
            <span className="eyebrow eyebrow-mint">Operating loop / 03</span>
            <h2 id="workflow-title">From disruption question to reviewable run.</h2>
          </div>
          <p>
            The workflow is deliberately plain. Each step leaves a visible trace, and no result is presented as more
            certain than its inputs allow.
          </p>
        </div>
        <div className="workflow-list">
          {workflowSteps.map((step) => (
            <article className="workflow-row" key={step.number}>
              <div className="workflow-number">{step.number}</div>
              <div className="workflow-label">{step.label}</div>
              <div className="workflow-copy">
                <h3>{step.title}</h3>
                <p>{step.text}</p>
              </div>
              <ArrowRight className="workflow-arrow" size={16} aria-hidden="true" />
            </article>
          ))}
        </div>
        <div className="workflow-cta">
          <Quote size={20} color="#e8d1cb" aria-hidden="true" />
          <p>
            <strong>The useful answer is not always “choose candidate.”</strong> Sometimes the honest result is that both
            plans tie, the inputs are physically infeasible or the boundary needs a human decision.
          </p>
          <button type="button" className="button button-primary" onClick={onOpenDashboard}>
            <span>Open an illustrative run</span>
            <ArrowUpRight size={15} aria-hidden="true" />
          </button>
        </div>
      </div>
    </section>
  )
}

/* =========================================================================
   IMPACT & RUN EVIDENCE SECTION
   ========================================================================= */
function ImpactSection({ onOpenDashboard }) {
  return (
    <section id="impact" className="section evidence-section" aria-labelledby="evidence-title">
      <div className="container evidence-grid">
        <div className="evidence-intro">
          <span className="eyebrow eyebrow-orange">Run evidence / 04</span>
          <h2 id="evidence-title">Numbers with a place to go.</h2>
          <p>
            A CommonRoot run is not a glossy black-box score. It is a compact record of the scenario, constraints, plan
            outputs and physical checks an operator can verify.
          </p>
          <div className="evidence-list">
            <div>
              <span>01</span>
              <p>Scenario and adjusted dispatch schedules</p>
            </div>
            <div>
              <span>02</span>
              <p>Stocks, shipments and priority-ordered service rows</p>
            </div>
            <div>
              <span>03</span>
              <p>District vulnerability and human-in-the-loop warnings</p>
            </div>
          </div>
          <button type="button" className="button button-outline-light" onClick={onOpenDashboard}>
            <span>Inspect the planning desk</span>
            <ArrowRight size={15} aria-hidden="true" />
          </button>
        </div>
        <div className="run-board">
          <div className="run-board-top">
            <span>RUN / IMPORT SHOCK</span>
            <span>DEMO-042 · CHECKED</span>
          </div>
          <div className="run-board-heading">
            <div>
              <span className="eyebrow eyebrow-mint">Synthetic fixture / seed 42</span>
              <h3>
                Same network.
                <br />
                Different pressure.
              </h3>
            </div>
            <span className="run-board-mark">
              CR
              <br />
              <small>01</small>
            </span>
          </div>
          <div className="run-kpis">
            <div>
              <strong>14</strong>
              <span>day horizon</span>
            </div>
            <div>
              <strong>62.45t</strong>
              <span>demand / day</span>
            </div>
            <div>
              <strong>197.22t</strong>
              <span>opening stock</span>
            </div>
          </div>
          <div className="run-table">
            <div className="run-table-head">
              <span>Review item</span>
              <span>State</span>
            </div>
            <div>
              <span>Source reduction</span>
              <b>50% / days 01—10</b>
            </div>
            <div>
              <span>Baseline plan</span>
              <b className="state-ready">INDEPENDENT CHECK</b>
            </div>
            <div>
              <span>Candidate plan</span>
              <b className="state-ready">INDEPENDENT CHECK</b>
            </div>
            <div>
              <span>External write</span>
              <b>NONE</b>
            </div>
          </div>
          <div className="run-board-foot">
            <ShieldCheck size={14} color="#10b981" aria-hidden="true" />
            <span>Review boundary active — simulation only</span>
          </div>
        </div>
      </div>
    </section>
  )
}

/* =========================================================================
   INSIGHTS SECTION
   ========================================================================= */
function InsightsSection({ onOpenDashboard }) {
  return (
    <section id="insights" className="section insights-section" aria-labelledby="insights-title">
      <div className="container">
        <div className="section-heading section-heading-split">
          <div>
            <span className="eyebrow eyebrow-teal">Questions to bring / 05</span>
            <h2 id="insights-title">Start with the constraint, not the dashboard.</h2>
          </div>
          <p>
            Use the desk to make one operational question more precise. These are the questions the synthetic fixtures are
            designed to help you stress-test.
          </p>
        </div>
        <div className="prompt-grid">
          {insightPrompts.map((item) => (
            <article
              className="prompt-card"
              key={item.label}
              onClick={onOpenDashboard}
              role="button"
              tabIndex={0}
              onKeyDown={(e) => {
                if (e.key === 'Enter') onOpenDashboard()
              }}
            >
              <span className="card-label">{item.label}</span>
              <h3>{item.title}</h3>
              <p>{item.text}</p>
              <span className="text-link">
                <span>Take it to the desk</span>
                <ArrowRight size={14} aria-hidden="true" />
              </span>
            </article>
          ))}
        </div>
      </div>
    </section>
  )
}

/* =========================================================================
   FAQ SECTION
   ========================================================================= */
function FaqSection() {
  const [openIndex, setOpenIndex] = useState(0)

  return (
    <section id="faq" className="section faq-section" aria-labelledby="faq-title">
      <div className="container faq-grid">
        <div className="faq-intro">
          <span className="eyebrow eyebrow-teal">Questions / 06</span>
          <h2 id="faq-title">Keep the boundary clear.</h2>
          <p>
            Plain answers for a synthetic planning tool. The first useful step is knowing exactly what a run can and cannot
            claim.
          </p>
          <a className="text-link" href="#contact">
            <span>Ask a question</span>
            <ArrowRight size={14} aria-hidden="true" />
          </a>
        </div>
        <div className="faq-list">
          {faqs.map((item, index) => {
            const isOpen = openIndex === index
            const answerId = `faq-answer-${index}`
            return (
              <div className={`faq-item ${isOpen ? 'is-open' : ''}`} key={item.question}>
                <button
                  type="button"
                  className="faq-question"
                  aria-expanded={isOpen}
                  aria-controls={answerId}
                  onClick={() => setOpenIndex(isOpen ? -1 : index)}
                >
                  <span>{item.question}</span>
                  <span className="faq-icon">
                    {isOpen ? <Minus size={16} aria-hidden="true" /> : <Plus size={16} aria-hidden="true" />}
                  </span>
                </button>
                <div id={answerId} className="faq-answer" role="region" hidden={!isOpen}>
                  <p>{item.answer}</p>
                </div>
              </div>
            )
          })}
        </div>
      </div>
    </section>
  )
}

/* =========================================================================
   CONTACT SECTION
   ========================================================================= */
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
    if (!form.message.trim() || form.message.trim().length < 20) {
      nextErrors.message = 'Tell us a little more — 20 characters is enough to start.'
    }
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
    <section id="contact" className="contact-section" aria-labelledby="contact-title">
      <div className="container contact-grid">
        <div className="contact-copy">
          <span className="eyebrow eyebrow-mint">Start a scenario / 07</span>
          <h2 id="contact-title">Bring the question that feels stuck.</h2>
          <p>
            You do not need a perfect brief. Tell us what changed, what you cannot see yet and what a useful first run
            would help you decide.
          </p>
          <div className="contact-points">
            <div>
              <Mail size={16} color="#e8d1cb" aria-hidden="true" />
              <span>
                <strong>Email</strong>
                <a href="mailto:operations@commonroot.internal">operations@commonroot.internal</a>
              </span>
            </div>
            <div>
              <Phone size={16} color="#e8d1cb" aria-hidden="true" />
              <span>
                <strong>Operations Desk</strong>
                <a href="tel:+442080501240">+44 (0)20 8050 1240</a>
              </span>
            </div>
            <div>
              <MapPin size={16} color="#e8d1cb" aria-hidden="true" />
              <span>
                <strong>Build location</strong>
                <span>Local workstation · synthetic LPG network</span>
              </span>
            </div>
          </div>
          <div className="contact-boundary">
            <ShieldCheck size={16} color="#10b981" aria-hidden="true" />
            <span>Local demo mode: inquiries are stored in session memory without external writes.</span>
          </div>
        </div>
        <div className="contact-form-wrap">
          {submitted ? (
            <div className="form-success">
              <span className="success-icon">
                <Check size={22} aria-hidden="true" />
              </span>
              <span className="eyebrow eyebrow-teal">Scenario Request Logged</span>
              <h3>Operational inquiry received.</h3>
              <p>The scenario parameters have been recorded in the local session audit register.</p>
              <button type="button" className="button button-primary" onClick={resetForm}>
                <span>Send another note</span>
                <ArrowRight size={15} aria-hidden="true" />
              </button>
            </div>
          ) : (
            <form className="contact-form" onSubmit={submit} noValidate>
              <div className="form-heading">
                <span className="eyebrow eyebrow-teal">No sales script / direct engineering reply</span>
                <h3>What should we pressure-test?</h3>
              </div>
              <div className="form-row">
                <label htmlFor="contact-name">
                  Full name
                  <input
                    id="contact-name"
                    type="text"
                    value={form.name}
                    onChange={(e) => update('name', e.target.value)}
                    aria-invalid={Boolean(errors.name)}
                    autoComplete="name"
                  />
                  {errors.name ? <small className="field-error">{errors.name}</small> : null}
                </label>
                <label htmlFor="contact-email">
                  Work email
                  <input
                    id="contact-email"
                    type="email"
                    value={form.email}
                    onChange={(e) => update('email', e.target.value)}
                    aria-invalid={Boolean(errors.email)}
                    autoComplete="email"
                  />
                  {errors.email ? <small className="field-error">{errors.email}</small> : null}
                </label>
              </div>
              <label htmlFor="contact-organisation">
                Organisation <span className="optional">optional</span>
                <input
                  id="contact-organisation"
                  type="text"
                  value={form.organisation}
                  onChange={(e) => update('organisation', e.target.value)}
                  autoComplete="organization"
                />
              </label>
              <label htmlFor="contact-message">
                The operating question
                <textarea
                  id="contact-message"
                  value={form.message}
                  onChange={(e) => update('message', e.target.value)}
                  aria-invalid={Boolean(errors.message)}
                  placeholder="For example: what happens if import corridor supply drops by 50% for 10 days?"
                />
                {errors.message ? <small className="field-error">{errors.message}</small> : null}
              </label>
              <div className="form-submit-row">
                <span>
                  <CircleCheck size={14} color="#10b981" aria-hidden="true" /> Local privacy preserved
                </span>
                <button type="submit" className="button button-primary">
                  <span>Log Scenario</span>
                  <ArrowRight size={15} aria-hidden="true" />
                </button>
              </div>
            </form>
          )}
        </div>
      </div>
    </section>
  )
}

/* =========================================================================
   FOOTER
   ========================================================================= */
function Footer({ onOpenDashboard }) {
  return (
    <footer className="site-footer">
      <div className="container footer-grid">
        <div className="footer-brand">
          <Brand />
          <p>Local-first LPG supply-resilience decision support for deterministic, reviewable scenarios.</p>
          <div className="footer-meta">
            <span>Built for inspection</span>
            <span>© 2026 CommonRoot</span>
          </div>
        </div>
        <div className="footer-links">
          <div>
            <span className="eyebrow">Explore</span>
            <a href="#about">Why it exists</a>
            <a href="#capabilities">Desk views</a>
            <a href="#impact">Run evidence</a>
          </div>
          <div>
            <span className="eyebrow">Use the desk</span>
            <button type="button" className="footer-btn-link" onClick={onOpenDashboard}>
              Open planning desk
            </button>
            <a href="#approach">Operating loop</a>
            <a href="#faq">FAQ</a>
            <a href="#contact">Contact</a>
          </div>
        </div>
        <div className="footer-social">
          <span className="eyebrow">Signal</span>
          <div>
            <a href="#home" aria-label="Globe">
              <Globe2 size={16} aria-hidden="true" />
            </a>
            <a href="mailto:operations@commonroot.internal" aria-label="Email CommonRoot">
              <Mail size={16} aria-hidden="true" />
            </a>
            <a href="#contact" aria-label="Contact CommonRoot">
              <UsersRound size={16} aria-hidden="true" />
            </a>
          </div>
        </div>
      </div>
      <div className="container footer-bottom">
        <span>Illustrative content · synthetic network · no operational dispatch writeback</span>
        <span>
          <a href="#home">Privacy</a>
          <a href="#home">Terms</a>
          <a href="#home">
            Back to top <ArrowUp size={12} aria-hidden="true" />
          </a>
        </span>
      </div>
    </footer>
  )
}

/* =========================================================================
   BACK TO TOP
   ========================================================================= */
function BackToTop() {
  const [visible, setVisible] = useState(false)
  useEffect(() => {
    const onScroll = () => setVisible(window.scrollY > 480)
    window.addEventListener('scroll', onScroll, { passive: true })
    onScroll()
    return () => window.removeEventListener('scroll', onScroll)
  }, [])
  const goToTop = () => {
    window.scrollTo({ top: 0, behavior: 'smooth' })
  }
  return (
    <button
      type="button"
      className={`back-to-top ${visible ? 'is-visible' : ''}`}
      onClick={goToTop}
      aria-label="Back to top"
    >
      <ArrowUp size={17} aria-hidden="true" />
    </button>
  )
}

/* =========================================================================
   MAIN APP ROUTER
   ========================================================================= */
function checkIsDashboard() {
  const path = window.location.pathname.toLowerCase()
  const hash = window.location.hash.toLowerCase()
  return path.includes('dashboard') || path.includes('app') || hash.includes('dashboard') || hash.includes('app')
}

function App() {
  const [view, setView] = useState(() => (checkIsDashboard() ? 'dashboard' : 'landing'))
  const [menuOpen, setMenuOpen] = useState(false)
  const [activeSection, setActiveSection] = useState('about')
  const [scrollPercent, setScrollPercent] = useState(0)

  // Sync hash routing
  useEffect(() => {
    const onHashChange = () => {
      setView(checkIsDashboard() ? 'dashboard' : 'landing')
    }
    window.addEventListener('hashchange', onHashChange)
    return () => window.removeEventListener('hashchange', onHashChange)
  }, [])

  // Scroll spy & progress bar
  useEffect(() => {
    if (view === 'dashboard') return
    const onScroll = () => {
      const total = document.documentElement.scrollHeight - window.innerHeight
      if (total > 0) {
        setScrollPercent(Math.min(100, Math.max(0, (window.scrollY / total) * 100)))
      }

      // Detect active section
      const sections = ['about', 'capabilities', 'approach', 'impact', 'insights', 'faq', 'contact']
      for (const s of sections) {
        const el = document.getElementById(s)
        if (el) {
          const rect = el.getBoundingClientRect()
          if (rect.top <= 200 && rect.bottom >= 200) {
            setActiveSection(s)
            break
          }
        }
      }
    }
    window.addEventListener('scroll', onScroll, { passive: true })
    onScroll()
    return () => window.removeEventListener('scroll', onScroll)
  }, [view])

  const openDashboard = () => {
    window.location.hash = '#/dashboard'
    setView('dashboard')
  }

  const backToLanding = () => {
    window.location.hash = ''
    setView('landing')
  }

  if (view === 'dashboard') {
    return <Dashboard onBackToLanding={backToLanding} />
  }

  return (
    <div id="main-content">
      <Header
        menuOpen={menuOpen}
        setMenuOpen={setMenuOpen}
        onOpenDashboard={openDashboard}
        activeSection={activeSection}
        scrollPercent={scrollPercent}
      />
      <main>
        <TickerBar />
        <HeroSection onOpenDashboard={openDashboard} />
        <SignalBand />
        <AboutSection onOpenDashboard={openDashboard} />
        <CapabilitiesSection onOpenDashboard={openDashboard} />
        <ApproachSection onOpenDashboard={openDashboard} />
        <ImpactSection onOpenDashboard={openDashboard} />
        <InsightsSection onOpenDashboard={openDashboard} />
        <FaqSection />
        <ContactSection onSubmitted={() => {}} />
      </main>
      <Footer onOpenDashboard={openDashboard} />
      <BackToTop />
    </div>
  )
}

createRoot(document.getElementById('root')).render(<App />)
