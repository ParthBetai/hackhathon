import React, { useEffect, useState, useRef } from 'react'
import { createRoot } from 'react-dom/client'
import {
  ArrowRight,
  ArrowUpRight,
  Building2,
  Check,
  CircleAlert,
  Database,
  FileCheck2,
  Flame,
  Globe2,
  HardDrive,
  Info,
  Layers,
  Network,
  Radio,
  RotateCcw,
  ShieldAlert,
  ShieldCheck,
  Sliders,
  Sparkles,
  TrendingUp,
  Truck,
  Volume2,
  VolumeX,
  X,
} from 'lucide-react'
import Dashboard from './Dashboard'
import './styles.css'

const CH = 'ABCDEFGHIJKLMNOPQRSTUVWXYZ'
const DUR = 400

const CHAPTER_COPY = {
  resilience: {
    rail: '01 RESILIENCE',
    video: 'vision',
    lines: ['We protect the flow ', 'of each cylinder'],
    blurb: [
      'For 14 planning days, CommonRoot secures critical LPG supply across',
      'essential health facilities, domestic households and industrial users.',
      'From import terminal to consumer gate, protecting communities against',
      'energy disruption.',
    ],
  },
  topology: {
    rail: '02 TOPOLOGY',
    video: 'expression',
    lines: ['Fourteen nodes mapped, ', 'zero blind corridors'],
    blurb: [
      'Physical infrastructure cannot be improvised during a crisis. We track',
      'two deep-water terminals, three bulk storage hubs, three bottling plants',
      'and six district delivery zones through sixteen constrained transit',
      'links.',
    ],
  },
  stress: {
    rail: '03 STRESS LAB',
    video: 'craftsmanship',
    lines: ['Five disruptions, ', 'tested before reality'],
    blurb: [
      'From fifty-percent import corridor cuts to six-day bottling outages',
      'and transit delays. Every shock is tested against physical tank bounds',
      'and lead times, revealing trapped inventories before deficits reach the',
      'streets.',
    ],
  },
  solver: {
    rail: '04 GLOP SOLVER',
    video: 'refinement',
    lines: ['Deterministic math, ', 'exact kilograms kept'],
    blurb: [
      'Powered by Google OR-Tools continuous linear programming. Every kilogram',
      'is conserved without hallucinated metrics, solving lexicographic priority',
      'objectives where life-critical demand takes precedence before commercial',
      'allocation.',
    ],
  },
  comparison: {
    rail: '05 DUAL PLANS',
    video: 'balance',
    lines: ['Ties preserved, ', 'no fabricated gains'],
    blurb: [
      'Baseline and candidate policies run independently against identical physical',
      'constraints. When an intervention yields no mathematical delta, the desk',
      'reports an honest tie instead of inventing an illusion of',
      'improvement.',
    ],
  },
  audit: {
    rail: '06 AUDIT VAULT',
    video: 'origin',
    lines: ['Tamper-evident logs, ', 'human in the loop'],
    blurb: [
      'No autonomous dispatch, no unverified rationing. Every run generates',
      'cryptographic JSON evidence, CSV allocation schedules and audit ZIPs,',
      'requiring explicit human operator review before policy',
      'acknowledgment.',
    ],
  },
}

function runDecode(el, originalText, isReducedMotion = false) {
  if (!el) return
  const text = originalText || el.dataset.text || el.textContent || ''
  if (isReducedMotion) {
    el.textContent = text
    return
  }
  const n = text.length
  const t0 = performance.now()
  let lastRoll = 0
  const rand = new Array(n)
  const roll = () => {
    for (let i = 0; i < n; i++) rand[i] = CH.charAt((Math.random() * 26) | 0)
  }
  roll()

  if (el._raf) cancelAnimationFrame(el._raf)
  if (el._t) clearTimeout(el._t)

  const step = (now) => {
    const p = Math.min(1, (now - t0) / DUR)
    const front = p * n
    let out = ''
    if (now - lastRoll > 45) {
      roll()
      lastRoll = now
    }
    for (let i = 0; i < n; i++) {
      const c = text.charAt(i)
      if (i < front) out += c
      else if (i < front + 3.6) out += c === ' ' ? ' ' : rand[i]
      else break
    }
    el.textContent = out
    if (p < 1) {
      el._raf = requestAnimationFrame(step)
    } else {
      el.textContent = text
    }
  }

  el._raf = requestAnimationFrame(step)
  el._t = setTimeout(() => {
    el.textContent = text
  }, DUR + 500)
}

function App() {
  const [activePage, setActivePage] = useState('overview') // 'overview', 'network', 'scenarios', 'dashboard', 'audit', 'stratum'
  const [chapter, setChapter] = useState('resilience')
  const [swapping, setSwapping] = useState(false)
  const [telemetryMode, setTelemetryMode] = useState(false)
  const [audioActive, setAudioActive] = useState(true)
  const [menuOpen, setMenuOpen] = useState(false)
  const [activeNodeHover, setActiveNodeHover] = useState(null)

  const bgRef = useRef(null)
  const videoRefs = useRef({})
  const menuLabelRef = useRef(null)
  const audioLabelRef = useRef(null)

  const isReducedMotion = typeof window !== 'undefined' && window.matchMedia && window.matchMedia('(prefers-reduced-motion: reduce)').matches

  // Sync hash routing
  useEffect(() => {
    const handleHash = () => {
      const h = window.location.hash.replace('#/', '').replace('#', '')
      if (['network', 'scenarios', 'dashboard', 'audit', 'stratum'].includes(h)) {
        setActivePage(h)
      } else {
        setActivePage('overview')
      }
    }
    handleHash()
    window.addEventListener('hashchange', handleHash)
    return () => window.removeEventListener('hashchange', handleHash)
  }, [])

  const navigateTo = (page) => {
    setActivePage(page)
    window.location.hash = page === 'overview' ? '' : `#/${page}`
    setMenuOpen(false)
  }

  // Label width reservation & initial decode
  useEffect(() => {
    const reserveAndBoot = () => {
      const labels = Array.from(document.querySelectorAll('.t'))
      labels.forEach((el) => {
        el.dataset.text = el.dataset.text || el.textContent
        el.style.width = ''
      })
      labels.forEach((el) => {
        const w = el.getBoundingClientRect().width
        el.style.width = `${Math.ceil(w * 100) / 100}px`
      })

      if (!isReducedMotion) {
        labels.forEach((el, i) => {
          setTimeout(() => runDecode(el, el.dataset.text, isReducedMotion), 350 + i * 35)
        })
      }
    }

    if (document.fonts && document.fonts.ready) {
      document.fonts.ready.then(reserveAndBoot)
    } else {
      window.addEventListener('load', reserveAndBoot)
    }

    const onResize = () => {
      const labels = Array.from(document.querySelectorAll('.t'))
      labels.forEach((el) => {
        el.style.width = ''
        const w = el.getBoundingClientRect().width
        el.style.width = `${Math.ceil(w * 100) / 100}px`
      })
    }
    window.addEventListener('resize', onResize)
    return () => window.removeEventListener('resize', onResize)
  }, [chapter, activePage])

  // Parallax background movement
  useEffect(() => {
    if (isReducedMotion) return
    let tx = 0, ty = 0, cx = 0, cy = 0, running = false

    const tick = () => {
      cx += (tx - cx) * 0.045
      cy += (ty - cy) * 0.045
      const w = window.innerWidth
      const h = window.innerHeight
      const dx = -cx * w * 0.0156
      const dy = -cy * h * 0.015
      const cover = 2 * Math.max(Math.abs(dx) / w, Math.abs(dy) / h)
      const sc = 1 + cover + 0.014 * Math.max(0, cy)

      if (bgRef.current) {
        bgRef.current.style.transform = `translate3d(${dx.toFixed(2)}px, ${dy.toFixed(2)}px, 0) scale(${sc.toFixed(4)})`
      }

      if (Math.abs(tx - cx) < 0.0004 && Math.abs(ty - cy) < 0.0004) {
        running = false
        return
      }
      requestAnimationFrame(tick)
    }

    const wake = () => {
      if (!running) {
        running = true
        requestAnimationFrame(tick)
      }
    }

    const onPointerMove = (e) => {
      if (e.pointerType === 'touch') return
      tx = (e.clientX / window.innerWidth) * 2 - 1
      ty = (e.clientY / window.innerHeight) * 2 - 1
      wake()
    }

    const onPointerLeave = () => {
      tx = 0
      ty = 0
      wake()
    }

    window.addEventListener('pointermove', onPointerMove, { passive: true })
    document.addEventListener('pointerleave', onPointerLeave)
    return () => {
      window.removeEventListener('pointermove', onPointerMove)
      document.removeEventListener('pointerleave', onPointerLeave)
    }
  }, [isReducedMotion])

  // Chapter swap with masked headline transitions
  const selectChapter = (chId) => {
    if (chId === chapter || swapping) return
    setSwapping(true)

    // Play next video clip
    const nextVideoKey = CHAPTER_COPY[chId].video
    const nextVid = videoRefs.current[nextVideoKey]
    if (nextVid) {
      if (!nextVid.getAttribute('src') && nextVid.dataset.src) {
        nextVid.preload = 'auto'
        nextVid.src = nextVid.dataset.src
        nextVid.load()
      }
      try {
        nextVid.currentTime = 0
        const pr = nextVid.play()
        if (pr && pr.catch) pr.catch(() => {})
      } catch (err) {}
    }

    setTimeout(() => {
      setChapter(chId)
      setSwapping(false)
    }, isReducedMotion ? 0 : 500)
  }

  // Toggle Audio state
  const toggleAudio = () => {
    const next = !audioActive
    setAudioActive(next)
    if (audioLabelRef.current) {
      audioLabelRef.current.dataset.text = next ? 'AUDIO ON' : 'AUDIO OFF'
      runDecode(audioLabelRef.current, next ? 'AUDIO ON' : 'AUDIO OFF', isReducedMotion)
    }
  }

  // Toggle Menu flyout
  const toggleMenu = () => {
    const next = !menuOpen
    setMenuOpen(next)
    if (menuLabelRef.current) {
      const txt = next ? 'CLOSE' : 'MENU'
      menuLabelRef.current.dataset.text = txt
      runDecode(menuLabelRef.current, txt, isReducedMotion)
    }
  }

  const currentCopy = CHAPTER_COPY[chapter]

  // Render Operational Decision-Support Desk if active
  if (activePage === 'dashboard') {
    return <Dashboard onBackToLanding={() => navigateTo('overview')} />
  }

  return (
    <div className={`stage ${menuOpen ? 'nav-open' : ''}`}>
      {/* ---------- Background Stage & Video Layers ---------- */}
      <div
        className="bg"
        ref={bgRef}
        role="img"
        aria-label="Monolithic architectural stone arch in still mountain waters at dusk"
      >
        <video
          ref={(el) => (videoRefs.current.vision = el)}
          className={currentCopy.video === 'vision' ? 'on' : ''}
          data-chapter="vision"
          src="/assets/video/background.mp4"
          poster="/assets/img/background.webp"
          autoPlay
          muted
          loop
          playsInline
          preload="auto"
          aria-hidden="true"
        />
        <video
          ref={(el) => (videoRefs.current.expression = el)}
          className={currentCopy.video === 'expression' ? 'on' : ''}
          data-chapter="expression"
          data-src="/assets/video/expression.mp4"
          muted
          loop
          playsInline
          preload="none"
          aria-hidden="true"
        />
        <video
          ref={(el) => (videoRefs.current.craftsmanship = el)}
          className={currentCopy.video === 'craftsmanship' ? 'on' : ''}
          data-chapter="craftsmanship"
          data-src="/assets/video/craftsmanship.mp4"
          muted
          loop
          playsInline
          preload="none"
          aria-hidden="true"
        />
        <video
          ref={(el) => (videoRefs.current.refinement = el)}
          className={currentCopy.video === 'refinement' ? 'on' : ''}
          data-chapter="refinement"
          data-src="/assets/video/refinement.mp4"
          muted
          loop
          playsInline
          preload="none"
          aria-hidden="true"
        />
        <video
          ref={(el) => (videoRefs.current.balance = el)}
          className={currentCopy.video === 'balance' ? 'on' : ''}
          data-chapter="balance"
          data-src="/assets/video/balance.mp4"
          muted
          loop
          playsInline
          preload="none"
          aria-hidden="true"
        />
        <video
          ref={(el) => (videoRefs.current.origin = el)}
          className={currentCopy.video === 'origin' ? 'on' : ''}
          data-chapter="origin"
          data-src="/assets/video/origin.mp4"
          muted
          loop
          playsInline
          preload="none"
          aria-hidden="true"
        />

        {/* Dynamic Telemetry Graph Layer */}
        <div className={`bg-telemetry-layer ${telemetryMode ? 'on' : ''}`}>
          <svg className="telemetry-svg" viewBox="0 0 1280 800" aria-hidden="true">
            <defs>
              <linearGradient id="corridorGlow" x1="0%" y1="0%" x2="100%" y2="100%">
                <stop offset="0%" stopColor="#38bdf8" stopOpacity="0.8" />
                <stop offset="100%" stopColor="#818cf8" stopOpacity="0.2" />
              </linearGradient>
            </defs>
            {/* Supply Routes */}
            <path d="M 220 280 C 380 240, 480 340, 640 380" stroke="url(#corridorGlow)" strokeWidth="1.5" strokeDasharray="4 6" fill="none" />
            <path d="M 640 380 C 780 420, 890 320, 1040 340" stroke="url(#corridorGlow)" strokeWidth="1.5" strokeDasharray="4 6" fill="none" />
            <path d="M 220 280 C 420 460, 560 520, 780 500" stroke="rgba(255,255,255,0.2)" strokeWidth="1" fill="none" />
            <path d="M 780 500 C 920 490, 980 420, 1060 460" stroke="rgba(255,255,255,0.2)" strokeWidth="1" fill="none" />

            {/* Interactive Nodes */}
            {[
              { id: 'T1', label: 'IMPORT TERMINAL NORTH', x: 220, y: 280, type: 'terminal', cap: '40,000 kg/d' },
              { id: 'H1', label: 'CENTRAL BULK STORAGE', x: 640, y: 380, type: 'hub', cap: '120,000 kg cap' },
              { id: 'B1', label: 'EAST BOTTLING PLANT', x: 780, y: 500, type: 'plant', cap: '80,000 kg cap' },
              { id: 'D1', label: 'NORTH HILLS DISTRICT', x: 1040, y: 340, type: 'district', cap: '4.50 t/d demand' },
              { id: 'D2', label: 'RIVER BEND DISTRICT', x: 1060, y: 460, type: 'district', cap: '8.20 t/d demand' },
            ].map((node) => (
              <g
                key={node.id}
                onMouseEnter={() => setActiveNodeHover(node)}
                onMouseLeave={() => setActiveNodeHover(null)}
                style={{ cursor: 'pointer' }}
              >
                <circle cx={node.x} cy={node.y} r="18" fill="rgba(4,7,13,0.8)" stroke="#e8d1cb" strokeWidth="1.2" />
                <circle cx={node.x} cy={node.y} r="4" fill="#e8d1cb" />
                <text x={node.x + 24} y={node.y + 4} fill="#e3e8f2" fontFamily="Chakra S" fontSize="10" letterSpacing="1">
                  {node.id} · {node.label}
                </text>
              </g>
            ))}
          </svg>
        </div>
      </div>

      {/* ---------- Architectural Frame (30u Inset & Corner Chamfers) ---------- */}
      <div className="frame">
        <span className="ln ln-t" />
        <span className="ln ln-b" />
        <span className="ln ln-l" />
        <span className="ln ln-r" />
        <span className="cn cn-tl" />
        <span className="cn cn-tr" />
        <span className="cn cn-bl" />
        <span className="cn cn-br" />

        {/* Wordmark Logo */}
        <a
          className="logo"
          href="#/"
          onClick={(e) => {
            e.preventDefault()
            navigateTo('overview')
          }}
          aria-label="CommonRoot home"
          onMouseEnter={(e) => {
            const t = e.currentTarget.querySelector('.t')
            if (t) runDecode(t, t.dataset.text, isReducedMotion)
          }}
        >
          <svg className="logo-svg" viewBox="0 0 24 24" fill="none" stroke="#e8d1cb" strokeWidth="1.8">
            <path d="M12 2L2 7l10 5 10-5-10-5zM2 17l10 5 10-5M2 12l10 5 10-5" />
          </svg>
          <span className="logo-title">
            <span className="t" data-text="COMMONROOT">
              COMMONROOT
            </span>
          </span>
          <span className="logo-badge">LPG / 01</span>
        </a>

        {/* Masthead Navigation */}
        <nav className="masthead" aria-label="Main">
          <div className="navset" id="navset">
            <div className="links lbl">
              {[
                { id: 'overview', label: 'OVERVIEW' },
                { id: 'network', label: 'NETWORK' },
                { id: 'scenarios', label: 'SCENARIOS' },
                { id: 'audit', label: 'AUDIT' },
                { id: 'stratum', label: 'STRATUM' },
              ].map((link) => (
                <button
                  key={link.id}
                  type="button"
                  className={activePage === link.id ? 'is-active-link' : ''}
                  onClick={() => navigateTo(link.id)}
                  onPointerEnter={(e) => {
                    const t = e.currentTarget.querySelector('.t')
                    if (t) runDecode(t, t.dataset.text, isReducedMotion)
                  }}
                >
                  <span className="t" data-text={link.label}>
                    {link.label}
                  </span>
                </button>
              ))}
            </div>

            <button
              type="button"
              className="pill enter lbl"
              onClick={() => navigateTo('dashboard')}
              onPointerEnter={(e) => {
                const t = e.currentTarget.querySelector('.t')
                if (t) runDecode(t, t.dataset.text, isReducedMotion)
              }}
            >
              <svg className="ico" viewBox="0 0 7 11" xmlns="http://www.w3.org/2000/svg" aria-hidden="true">
                <rect x="0" y="0" width="4" height="5" />
                <rect x="3" y="4" width="4" height="4" />
                <rect x="0" y="7" width="4" height="4" />
              </svg>
              <span className="t" data-text="ENTER">
                ENTER
              </span>
            </button>
          </div>

          <button
            className="pill menu lbl"
            type="button"
            aria-expanded={menuOpen}
            aria-controls="navset"
            onClick={toggleMenu}
            onPointerEnter={(e) => {
              const t = e.currentTarget.querySelector('.t')
              if (t) runDecode(t, t.dataset.text, isReducedMotion)
            }}
          >
            <svg className="ico" viewBox="0 0 10 10" xmlns="http://www.w3.org/2000/svg" aria-hidden="true">
              <rect x="0" y="0" width="4" height="4" rx=".8" />
              <rect x="6" y="0" width="4" height="4" rx=".8" />
              <rect x="0" y="6" width="4" height="4" rx=".8" />
              <rect x="6" y="6" width="4" height="4" rx=".8" />
            </svg>
            <span className="t" ref={menuLabelRef} data-text="MENU">
              MENU
            </span>
          </button>
        </nav>

        {/* Section / Chapter Index Rail (Left) */}
        <ul className="index" aria-label="Operational Chapters">
          {Object.entries(CHAPTER_COPY).map(([key, item]) => {
            const isActive = chapter === key
            return (
              <li key={key} className={isActive ? 'on' : ''}>
                <button
                  type="button"
                  aria-current={isActive ? 'true' : undefined}
                  onClick={() => selectChapter(key)}
                  onPointerEnter={(e) => {
                    const t = e.currentTarget.querySelector('.t')
                    if (t) runDecode(t, t.dataset.text, isReducedMotion)
                  }}
                >
                  <span className="t" data-text={item.rail}>
                    {item.rail}
                  </span>
                </button>
              </li>
            )
          })}
        </ul>

        {/* Hero Headline, Blurb & Glass Octagon CTA */}
        <div className={`hero ${swapping ? 'swapping' : ''}`}>
          <h1 className="headline">
            <span className="hrow">
              <span className="hrise">{currentCopy.lines[0]}</span>
            </span>
            <span className="hrow">
              <span className="hrise">{currentCopy.lines[1]}</span>
            </span>
          </h1>

          <p className="blurb">
            {currentCopy.blurb[0]}
            <br />
            {currentCopy.blurb[1]}
            <br />
            {currentCopy.blurb[2]}
            <br />
            {currentCopy.blurb[3]}
          </p>

          <button
            type="button"
            className="cta lbl"
            onClick={() => navigateTo('dashboard')}
            onPointerEnter={(e) => {
              const t = e.currentTarget.querySelector('.t')
              if (t) runDecode(t, t.dataset.text, isReducedMotion)
            }}
          >
            <span className="cta-glass" />
            <svg className="cta-edge" viewBox="0 0 190 41" preserveAspectRatio="none" aria-hidden="true">
              <path d="M3.5.5 H179.5 L189.5 10.5 V37.5 L186.5 40.5 H10.5 L.5 30.5 V3.5 Z" vectorEffect="non-scaling-stroke" />
            </svg>
            <span className="cta-in">
              <svg className="ico" viewBox="0 0 7 11" xmlns="http://www.w3.org/2000/svg" aria-hidden="true">
                <rect x="0" y="0" width="4" height="5" />
                <rect x="3" y="4" width="4" height="4" />
                <rect x="0" y="7" width="4" height="4" />
              </svg>
              <span className="t" data-text="UNCOVER OUR APPROACH">
                UNCOVER OUR APPROACH
              </span>
            </span>
          </button>
        </div>

        {/* Dock (Bottom Row) */}
        <div className="dock">
          <span className="rule" />
          <span className="div div-l" />
          <span className="div div-r" />

          {/* Left: Mode / Audio Toggle */}
          <button
            type="button"
            className={`audio lbl ${!audioActive ? 'muted' : ''}`}
            aria-pressed={audioActive}
            onClick={toggleAudio}
            onPointerEnter={(e) => {
              const t = e.currentTarget.querySelector('.t')
              if (t) runDecode(t, t.dataset.text, isReducedMotion)
            }}
          >
            <svg className="ico" viewBox="0 0 14 11" xmlns="http://www.w3.org/2000/svg" aria-hidden="true">
              <path d="M7 0 L7 11 L0.6 7.6 L0.6 3.4 Z" stroke="none" />
              <path className="wave" d="M9.4 2.2 C10.9 4 10.9 7 9.4 8.8" fill="none" strokeWidth="1.3" strokeLinecap="round" />
              <path className="wave" d="M11.9 0.6 C14.1 3.3 14.1 7.7 11.9 10.4" fill="none" strokeWidth="1.3" strokeLinecap="round" />
              <path className="slash" d="M9.2 2.4 L13.8 8.6 M13.8 2.4 L9.2 8.6" fill="none" strokeWidth="1.3" strokeLinecap="round" />
            </svg>
            <span className="t" ref={audioLabelRef} data-text={audioActive ? 'AUDIO ON' : 'AUDIO OFF'}>
              {audioActive ? 'AUDIO ON' : 'AUDIO OFF'}
            </span>
          </button>

          {/* Center: Telemetry Canvas Toggle */}
          <button
            type="button"
            className="scroll lbl"
            onClick={() => setTelemetryMode((prev) => !prev)}
            onPointerEnter={(e) => {
              const t = e.currentTarget.querySelector('.t')
              if (t) runDecode(t, t.dataset.text, isReducedMotion)
            }}
          >
            <svg className="ico" viewBox="0 0 5 7" xmlns="http://www.w3.org/2000/svg" aria-hidden="true">
              <path d="M0 0 H5 L2.5 3 Z" />
              <path d="M0 4 H5 L2.5 7 Z" />
            </svg>
            <span className="t" data-text={telemetryMode ? 'CINEMATIC VIEW' : 'NETWORK TELEMETRY'}>
              {telemetryMode ? 'CINEMATIC VIEW' : 'NETWORK TELEMETRY'}
            </span>
          </button>

          {/* Right: Talk with us / Audit */}
          <button
            type="button"
            className="talk lbl"
            onClick={() => navigateTo('audit')}
            onPointerEnter={(e) => {
              const t = e.currentTarget.querySelector('.t')
              if (t) runDecode(t, t.dataset.text, isReducedMotion)
            }}
          >
            <span className="t" data-text="TALK WITH US">
              TALK WITH US
            </span>
            <svg className="ico" viewBox="0 0 16 15" xmlns="http://www.w3.org/2000/svg" aria-hidden="true">
              <path d="M8 .8 C12 .8 15.2 3.8 15.2 7.4 C15.2 11 12 14 8 14 C6.6 14 5.3 13.6 4.2 13 L.9 13.9 L1.9 10.9 C1.2 9.9 .8 8.7 .8 7.4 C.8 3.8 4 .8 8 .8 Z" />
              <g fill="currentColor" stroke="none">
                <circle cx="5.2" cy="7.4" r=".95" />
                <circle cx="8" cy="7.4" r=".95" />
                <circle cx="10.8" cy="7.4" r=".95" />
              </g>
            </svg>
          </button>
        </div>
      </div>

      {/* ================= MULTI-PAGE VIEW OVERLAYS ================= */}

      {/* PAGE 1: NETWORK TOPOLOGY BLUEPRINT */}
      <div className={`page-overlay ${activePage === 'network' ? 'is-active' : ''}`}>
        <div className="page-container">
          <div className="page-header-row">
            <div>
              <span className="page-tagline">Physical Infrastructure · 14-Node System</span>
              <h2 className="page-heading">LPG Supply Network & Corridor Architecture</h2>
            </div>
            <button type="button" className="page-close-btn" onClick={() => navigateTo('overview')}>
              <span>ESC</span>
              <X size={14} />
            </button>
          </div>

          <div className="arch-grid">
            <div className="arch-card">
              <span className="arch-card-tag">NODE T1 & T2 · SOURCE INGESTION</span>
              <h3 className="arch-card-title">Deep-Water Terminals</h3>
              <p className="arch-card-desc">
                Continuous baseline maritime import streams with physical daily throughput capacity (40,000 kg/day per terminal). Serves as the origin for the 832,220 kg recorded planning mass balance.
              </p>
              <div className="arch-card-metric">
                <span>TOTAL HARBOR STORAGE</span>
                <strong>180,000 kg</strong>
              </div>
            </div>

            <div className="arch-card">
              <span className="arch-card-tag">NODE H1, H2, H3 · STORAGE BASINS</span>
              <h3 className="arch-card-title">Bulk Storage Hubs</h3>
              <p className="arch-card-desc">
                Intermediate pressure-vessel tanks acting as regional buffers. Governed by minimum buffer thresholds and maximum tank capacities to absorb rail and pipeline transit swings.
              </p>
              <div className="arch-card-metric">
                <span>BUFFER CAPACITY</span>
                <strong>320,000 kg</strong>
              </div>
            </div>

            <div className="arch-card">
              <span className="arch-card-tag">NODE B1, B2, B3 · BOTTLING PLANTS</span>
              <h3 className="arch-card-title">Cylinder Bottling Facilities</h3>
              <p className="arch-card-desc">
                Transformation tier converting bulk liquefied petroleum gas into 14.2 kg domestic and 19 kg commercial cylinders. Outbound dispatch constrained by truck turnaround cycles.
              </p>
              <div className="arch-card-metric">
                <span>BOTTLING THROUGHPUT</span>
                <strong>65,000 kg/d</strong>
              </div>
            </div>

            <div className="arch-card">
              <span className="arch-card-tag">NODE D1 - D6 · DISTRICT GATES</span>
              <h3 className="arch-card-title">Six Demand Districts</h3>
              <p className="arch-card-desc">
                Hierarchical consumption tiers classified by strict social criticality: Tier 1 Essential (hospitals, emergency centers), Tier 2 Domestic, and Tier 3 Commercial.
              </p>
              <div className="arch-card-metric">
                <span>DAILY AGGREGATE DEMAND</span>
                <strong>62,450 kg/d</strong>
              </div>
            </div>
          </div>

          <div style={{ textAlign: 'center', marginTop: '24px' }}>
            <button
              type="button"
              className="page-close-btn"
              style={{ display: 'inline-flex', padding: '12px 28px' }}
              onClick={() => navigateTo('dashboard')}
            >
              <span>OPEN FULL INTERACTIVE NETWORK IN OPERATIONAL DESK</span>
              <ArrowRight size={15} />
            </button>
          </div>
        </div>
      </div>

      {/* PAGE 2: DISRUPTION LAB & SCENARIOS */}
      <div className={`page-overlay ${activePage === 'scenarios' ? 'is-active' : ''}`}>
        <div className="page-container">
          <div className="page-header-row">
            <div>
              <span className="page-tagline">Repeatable Stress Fixtures · 14-Day Horizon</span>
              <h2 className="page-heading">Disruption Scenarios & Stress Testing Lab</h2>
            </div>
            <button type="button" className="page-close-btn" onClick={() => navigateTo('overview')}>
              <span>ESC</span>
              <X size={14} />
            </button>
          </div>

          <div className="arch-grid">
            <div className="arch-card">
              <span className="arch-card-tag">FIXTURE 01 · DEMO-042</span>
              <h3 className="arch-card-title">Import Corridor Shock</h3>
              <p className="arch-card-desc">
                A 50% supply contraction at Import Terminal North from Day 01 through Day 10. Tests system buffer endurance before domestic rationing is triggered.
              </p>
              <div className="arch-card-metric">
                <span>DURATION / SEVERITY</span>
                <strong style={{ color: '#ef4444' }}>10 DAYS · -50% INFLOW</strong>
              </div>
            </div>

            <div className="arch-card">
              <span className="arch-card-tag">FIXTURE 02 · DEMO-088</span>
              <h3 className="arch-card-title">Bottling Route Outage</h3>
              <p className="arch-card-desc">
                Complete physical severance of the primary arterial route between Bulk Hub Central and East Bottling Plant for 6 consecutive days.
              </p>
              <div className="arch-card-metric">
                <span>BOTTLENECK IMPACT</span>
                <strong style={{ color: '#f59e0b' }}>6 DAYS · 0 KG/D LINK FLOW</strong>
              </div>
            </div>

            <div className="arch-card">
              <span className="arch-card-tag">FIXTURE 03 · DEMO-103</span>
              <h3 className="arch-card-title">Corridor Transit Delay</h3>
              <p className="arch-card-desc">
                Logistics bottleneck increasing highway transit lead time from 1 day to 4 days across critical mountain corridors from Day 02 to Day 14.
              </p>
              <div className="arch-card-metric">
                <span>LATENCY SURGE</span>
                <strong style={{ color: '#38bdf8' }}>+3 DAYS TRANSIT LAG</strong>
              </div>
            </div>

            <div className="arch-card">
              <span className="arch-card-tag">FIXTURE 04 · DEMO-150</span>
              <h3 className="arch-card-title">Bottling Plant Fire Outage</h3>
              <p className="arch-card-desc">
                Catastrophic equipment outage shutting East Bottling Plant for 7 days. Compels candidate policy to reroute bulk fuel to South Plant.
              </p>
              <div className="arch-card-metric">
                <span>FACILITY OUTAGE</span>
                <strong style={{ color: '#ef4444' }}>7 DAYS · 0 CAPACITY</strong>
              </div>
            </div>
          </div>

          <div style={{ textAlign: 'center', marginTop: '24px' }}>
            <button
              type="button"
              className="page-close-btn"
              style={{ display: 'inline-flex', padding: '12px 28px' }}
              onClick={() => navigateTo('dashboard')}
            >
              <span>RUN ALLOCATION SOLVER ON THESE SCENARIOS</span>
              <ArrowRight size={15} />
            </button>
          </div>
        </div>
      </div>

      {/* PAGE 3: EVIDENCE VAULT & AUDIT TRAIL */}
      <div className={`page-overlay ${activePage === 'audit' ? 'is-active' : ''}`}>
        <div className="page-container">
          <div className="page-header-row">
            <div>
              <span className="page-tagline">Mathematical Proof · Local-First Privacy</span>
              <h2 className="page-heading">Evidence Vault & Human-in-the-Loop Gate</h2>
            </div>
            <button type="button" className="page-close-btn" onClick={() => navigateTo('overview')}>
              <span>ESC</span>
              <X size={14} />
            </button>
          </div>

          <div className="arch-grid">
            <div className="arch-card">
              <span className="arch-card-tag">CORE PRINCIPLE · LAW 01</span>
              <h3 className="arch-card-title">Mass Balance Conservation</h3>
              <p className="arch-card-desc">
                Strict physical balance enforced at every node: Ending Stock = Starting Stock + Inflows - Outflows. The solver will reject any plan that invents or deletes a single kilogram.
              </p>
              <div className="arch-card-metric">
                <span>VERIFICATION STATUS</span>
                <strong style={{ color: '#10b981' }}>100% CONSERVED</strong>
              </div>
            </div>

            <div className="arch-card">
              <span className="arch-card-tag">CORE PRINCIPLE · LAW 02</span>
              <h3 className="arch-card-title">Honest Tie Preservation</h3>
              <p className="arch-card-desc">
                When candidate and baseline policies yield identical objective values or zero deficit mitigation, the platform reports an honest mathematical tie instead of hallucinating artificial gains.
              </p>
              <div className="arch-card-metric">
                <span>OBJECTIVE COMPARISON</span>
                <strong style={{ color: '#38bdf8' }}>ZERO FABRICATED DELTAS</strong>
              </div>
            </div>

            <div className="arch-card">
              <span className="arch-card-tag">CORE PRINCIPLE · LAW 03</span>
              <h3 className="arch-card-title">Human-in-the-Loop Review</h3>
              <p className="arch-card-desc">
                No automatic dispatch or external API actuation. Recommendations remain strictly decision-support until certified by a human operations officer with audit trail logging.
              </p>
              <div className="arch-card-metric">
                <span>DISPATCH GATE</span>
                <strong style={{ color: '#f59e0b' }}>LOCAL-FIRST PRIVACY</strong>
              </div>
            </div>
          </div>
        </div>
      </div>

      {/* PAGE 4: STRATUM HERO SHOWCASE / LIVE PREVIEW */}
      <div className={`page-overlay ${activePage === 'stratum' ? 'is-active' : ''}`}>
        <div className="page-container">
          <div className="page-header-row">
            <div>
              <span className="page-tagline">Original Reference Architecture</span>
              <h2 className="page-heading">Stratum — Single-Page Real-Estate Hero Site</h2>
            </div>
            <div style={{ display: 'flex', gap: '12px' }}>
              <a
                href="/stratum.html"
                target="_blank"
                rel="noreferrer"
                className="page-close-btn"
                style={{ textDecoration: 'none' }}
              >
                <span>OPEN FULLSCREEN</span>
                <ArrowUpRight size={14} />
              </a>
              <button type="button" className="page-close-btn" onClick={() => navigateTo('overview')}>
                <span>ESC</span>
                <X size={14} />
              </button>
            </div>
          </div>

          <div className="stratum-frame-box">
            <iframe
              src="/stratum.html"
              title="Stratum Original Hero Page"
              className="stratum-iframe"
              loading="lazy"
            />
          </div>
        </div>
      </div>
    </div>
  )
}

createRoot(document.getElementById('root')).render(<App />)
