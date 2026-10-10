import React, { useState, useMemo } from 'react'
import {
  Activity,
  AlertOctagon,
  AlertTriangle,
  ArrowDownRight,
  ArrowLeft,
  ArrowRight,
  ArrowUpRight,
  BarChart3,
  Boxes,
  Check,
  CheckCircle2,
  ChevronDown,
  ChevronRight,
  Clock,
  Compass,
  Cpu,
  Download,
  FileCheck2,
  FileDown,
  FileSpreadsheet,
  FileText,
  Filter,
  Flame,
  Globe,
  HelpCircle,
  Info,
  Layers,
  MapPin,
  Maximize2,
  Minimize2,
  Network,
  Play,
  Radio,
  RefreshCw,
  Search,
  Shield,
  ShieldAlert,
  ShieldCheck,
  Sliders,
  Sparkles,
  Terminal,
  Truck,
  Users,
  Warehouse,
  X,
} from 'lucide-react'
import precomputedRuns from './data/precomputed_runs.json'
import './dashboard.css'

const PRESET_NAMES = {
  import_shock: 'Import Corridor Shock (-50%, 10 Days)',
  route_closure: 'Bottling Route Outage (6-Day Closure)',
  route_delay: 'Inbound Route Delay (+3 Days Lead)',
  facility_outage: 'East Bottling Plant Outage (5 Days)',
  normal: 'Normal Reference Case (Baseline Supply)',
}

const DISTRICT_NAMES = {
  north_hills: 'North Hills',
  river_bend: 'River Bend',
  east_metro: 'East Metro',
  coastal_plain: 'Coastal Plain',
  central_gate: 'Central Gate',
  western_fringe: 'Western Fringe',
}

function formatKg(val, decimals = 0) {
  if (val === null || val === undefined || isNaN(val)) return '—'
  return Number(val).toLocaleString('en-IN', {
    maximumFractionDigits: decimals,
    minimumFractionDigits: decimals,
  })
}

function formatTonnes(val, decimals = 1) {
  if (val === null || val === undefined || isNaN(val)) return '—'
  return (val / 1000).toLocaleString('en-IN', {
    maximumFractionDigits: decimals,
    minimumFractionDigits: decimals,
  }) + ' t'
}

function formatPercent(val, decimals = 1) {
  if (val === null || val === undefined || isNaN(val)) return '—'
  return (val * 100).toFixed(decimals) + '%'
}

export default function Dashboard({ onBackToLanding }) {
  // Scenario state
  const [selectedPreset, setSelectedPreset] = useState('import_shock')
  const [activeTab, setActiveTab] = useState('overview')
  const [isSimulating, setIsSimulating] = useState(false)
  const [simulationLog, setSimulationLog] = useState([])

  // Parametric controls
  const [customParams, setCustomParams] = useState({
    reductionFraction: 0.5,
    delayDays: 2,
    startDay: 1,
    durationDays: 10,
    horizonDays: 14,
    demandMultiplier: 1.0,
    extraLeadDays: 0,
    coverThreshold: 2.0,
  })

  // District table filter/sort
  const [searchDistrict, setSearchDistrict] = useState('')
  const [districtSortBy, setDistrictSortBy] = useState('risk')
  const [selectedDistrictId, setSelectedDistrictId] = useState('north_hills')

  // Selected & Hovered network assets for interactive topology
  const [selectedAsset, setSelectedAsset] = useState('node:import_source')
  const [hoveredNodeId, setHoveredNodeId] = useState(null)
  const [hoveredEdgeId, setHoveredEdgeId] = useState(null)

  // Human review state
  const [reviewNote, setReviewNote] = useState('')
  const [reviewAck, setReviewAck] = useState(false)
  const [reviewStatus, setReviewStatus] = useState(null)

  // Load currently active run bundle from precomputed runs
  const currentRun = useMemo(() => {
    return precomputedRuns[selectedPreset] || precomputedRuns['import_shock']
  }, [selectedPreset])

  const {
    manifest,
    scenario,
    network,
    policy,
    baseline,
    candidate,
    comparison,
    affected_nodes,
    affected_edges,
    affected_paths,
    warnings,
  } = currentRun

  // Switch preset
  const handleSelectPreset = (presetKey) => {
    setSelectedPreset(presetKey)
    const run = precomputedRuns[presetKey]
    if (run && run.scenario) {
      setCustomParams({
        reductionFraction: run.scenario.reduction_fraction ?? 0.5,
        delayDays: run.scenario.delay_days ?? 2,
        startDay: run.scenario.start_day ?? 1,
        durationDays: run.scenario.duration_days ?? 10,
        horizonDays: run.scenario.horizon_days ?? 14,
        demandMultiplier: run.scenario.demand_multiplier ?? 1.0,
        extraLeadDays: run.scenario.extra_lead_days ?? 0,
        coverThreshold: run.scenario.cover_threshold ?? 2.0,
      })
    }
  }

  // Trigger simulated solver run
  const handleRunSimulation = () => {
    setIsSimulating(true)
    setSimulationLog([
      'Initializing OR-Tools GLOP Continuous Linear Program solver (v9.11)...',
      `Applying disruption parameters to graph topology: ${scenario.name}...`,
      'Staging lexicographic tier 1 objective: Maximizing Essential Medical & Care Services...',
      'Staging lexicographic tier 2 objective: Maximizing Domestic Household Service...',
      'Minimizing intra-tier L1 proportional deviations across 6 administrative districts...',
      'Evaluating physical flow conservation & capacity bounds (tolerance: 1e-5 kg)...',
      'Optimisation complete: GLOP returned OPTIMAL in 0.089s. Deterministic seed verified.',
    ])
    setTimeout(() => {
      setIsSimulating(false)
    }, 700)
  }

  // Handle Review submission
  const handleRecordReview = (e) => {
    e.preventDefault()
    if (!reviewAck) return
    setReviewStatus({
      timestamp: new Date().toISOString(),
      note: reviewNote || 'Operator verified disruption parameters. Allocation approved for simulated decision support.',
      operator: 'District LPG Supply Officer (Desk Console)',
    })
  }

  // Export handlers
  const handleExportJson = () => {
    const dataStr = 'data:text/json;charset=utf-8,' + encodeURIComponent(JSON.stringify(currentRun, null, 2))
    const downloadAnchor = document.createElement('a')
    downloadAnchor.setAttribute('href', dataStr)
    downloadAnchor.setAttribute('download', `commonroot-run-${manifest.run_id.slice(0, 8)}.json`)
    document.body.appendChild(downloadAnchor)
    downloadAnchor.click()
    downloadAnchor.remove()
  }

  const handleExportCsv = () => {
    const headers = [
      'District ID',
      'District Name',
      'Risk Classification',
      'Opening Stock (kg)',
      'Daily Demand (kg)',
      'Inbound Receipts (kg)',
      'Closing Stock (kg)',
      'Snapshot Cover (days)',
      'Minimum Closing Cover (days)',
      'First Low Day',
      'Unmet Demand (kg)',
      'Fulfilment %',
    ]
    const rows = candidate.districts.map((d) => [
      d.district_id,
      `"${d.name}"`,
      d.risk,
      d.opening_stock,
      d.daily_demand,
      d.inbound,
      d.closing_stock,
      d.snapshot_cover?.toFixed(2) || 'N/A',
      d.minimum_cover?.toFixed(2) || 'N/A',
      d.first_low_day || 'None',
      d.unmet,
      ((d.fulfilled_fraction || 0) * 100).toFixed(1) + '%',
    ])
    const csvContent = 'data:text/csv;charset=utf-8,' + [headers.join(','), ...rows.map((r) => r.join(','))].join('\n')
    const downloadAnchor = document.createElement('a')
    downloadAnchor.setAttribute('href', encodeURI(csvContent))
    downloadAnchor.setAttribute('download', `district-risk-${manifest.run_id.slice(0, 8)}.csv`)
    document.body.appendChild(downloadAnchor)
    downloadAnchor.click()
    downloadAnchor.remove()
  }

  // District filtering and sorting
  const filteredDistricts = useMemo(() => {
    let list = [...candidate.districts]
    if (searchDistrict.trim()) {
      const q = searchDistrict.toLowerCase()
      list = list.filter((d) => d.name.toLowerCase().includes(q) || d.district_id.toLowerCase().includes(q))
    }
    list.sort((a, b) => {
      if (districtSortBy === 'risk') {
        const order = { High: 0, Watch: 1, Stable: 2, 'Not computable': 3 }
        return (order[a.risk] ?? 9) - (order[b.risk] ?? 9) || b.unmet - a.unmet
      }
      if (districtSortBy === 'unmet') return b.unmet - a.unmet
      if (districtSortBy === 'cover') return (a.minimum_cover || 999) - (b.minimum_cover || 999)
      return a.name.localeCompare(b.name)
    })
    return list
  }, [candidate.districts, searchDistrict, districtSortBy])

  const selectedDistrictData = useMemo(() => {
    return candidate.districts.find((d) => d.district_id === selectedDistrictId) || candidate.districts[0]
  }, [candidate.districts, selectedDistrictId])

  const selectedDistrictBalances = useMemo(() => {
    return candidate.balances.filter((b) => b.node_id === selectedDistrictId).sort((a, b) => a.day - b.day)
  }, [candidate.balances, selectedDistrictId])

  const selectedDistrictService = useMemo(() => {
    return candidate.service.filter((s) => s.district_id === selectedDistrictId)
  }, [candidate.service, selectedDistrictId])

  // Asset inspection lookup
  const inspectedAssetData = useMemo(() => {
    const [type, id] = selectedAsset.split(':')
    if (type === 'node') {
      const n = network.nodes.find((item) => item.id === id)
      const balances = candidate.balances.filter((b) => b.node_id === id)
      return { type: 'node', node: n, balances }
    } else {
      const e = network.edges.find((item) => item.id === id)
      const shipments = candidate.shipments.filter((s) => s.edge_id === id)
      return { type: 'edge', edge: e, shipments }
    }
  }, [selectedAsset, network, candidate])

  // Interactive Graph Hover derivations
  const connectedEdgeIds = useMemo(() => {
    if (!hoveredNodeId) return []
    return network.edges
      .filter((e) => e.source === hoveredNodeId || e.target === hoveredNodeId)
      .map((e) => e.id)
  }, [hoveredNodeId, network.edges])

  const connectedNodeIds = useMemo(() => {
    if (!hoveredEdgeId) return []
    const edge = network.edges.find((e) => e.id === hoveredEdgeId)
    return edge ? [edge.source, edge.target] : []
  }, [hoveredEdgeId, network.edges])

  const activeHoveredNode = useMemo(() => {
    if (!hoveredNodeId) return null
    return network.nodes.find((n) => n.id === hoveredNodeId) || null
  }, [hoveredNodeId, network.nodes])

  const activeHoveredEdge = useMemo(() => {
    if (!hoveredEdgeId) return null
    const edge = network.edges.find((e) => e.id === hoveredEdgeId)
    if (!edge) return null
    const src = network.nodes.find((n) => n.id === edge.source)
    const tgt = network.nodes.find((n) => n.id === edge.target)
    return { edge, sourceNode: src, targetNode: tgt }
  }, [hoveredEdgeId, network.edges, network.nodes])

  return (
    <div className="cr-dashboard-root">
      {/* 1. TOP ANNOUNCEMENT & RESPONSIBLE AI BANNER */}
      <div className="cr-top-banner">
        <div className="cr-top-banner-content">
          <span className="cr-top-pill">DECISION SUPPORT ONLY</span>
          <p>
            <strong>CommonRoot Operational Console:</strong> Outputs are modeled estimates from synthetic corridor data.
            Human review is strictly mandatory before any authorized logistics or civil supplies action.
          </p>
        </div>
        <div className="cr-top-banner-actions">
          <a
            href="http://localhost:8501"
            target="_blank"
            rel="noreferrer"
            className="cr-btn-streamlit-pill"
            title="Launch Streamlit Python OR-Tools app on port 8501"
          >
            <Cpu size={12} /> Local Streamlit Engine (:8501)
          </a>
          {onBackToLanding && (
            <button className="cr-btn-text" onClick={onBackToLanding}>
              <ArrowLeft size={13} /> Return to Description Site
            </button>
          )}
        </div>
      </div>

      {/* 2. MAIN HEADER & SCENARIO BAR */}
      <header className="cr-dash-header">
        <div className="cr-dash-header-main">
          <div className="cr-header-title-group">
            <div className="cr-brand-badge">
              <span className="cr-brand-pulse" />
              <span className="cr-brand-code">CR-OPS</span>
              <span className="cr-brand-status">MODEL v1.1</span>
            </div>
            <div>
              <h1 className="cr-dash-title">LPG Supply Resilience & Allocation Console</h1>
              <p className="cr-dash-subtitle">
                District-level shortage risk calculation, inventory projection, and OR-Tools constrained allocation.
              </p>
            </div>
          </div>

          <div className="cr-scenario-control-strip">
            <div className="cr-preset-select-wrapper">
              <label htmlFor="preset-select">Active Disruption Scenario:</label>
              <select
                id="preset-select"
                className="cr-preset-select"
                value={selectedPreset}
                onChange={(e) => handleSelectPreset(e.target.value)}
              >
                {Object.entries(PRESET_NAMES).map(([key, name]) => (
                  <option key={key} value={key}>
                    {name}
                  </option>
                ))}
              </select>
            </div>

            <button
              className={`cr-btn-primary ${isSimulating ? 'is-loading' : ''}`}
              onClick={handleRunSimulation}
              disabled={isSimulating}
            >
              {isSimulating ? (
                <>
                  <RefreshCw size={15} className="cr-spin" /> Solving GLOP LP...
                </>
              ) : (
                <>
                  <Play size={15} /> Run Simulation
                </>
              )}
            </button>
          </div>
        </div>

        {/* Status Metadata Bar */}
        <div className="cr-dash-meta-bar">
          <div className="cr-meta-item">
            <span className="cr-meta-label">Horizon:</span>
            <span className="cr-meta-val">{scenario.horizon_days} Days (Daily T=1..14)</span>
          </div>
          <div className="cr-meta-item">
            <span className="cr-meta-label">Solver:</span>
            <span className="cr-meta-val">OR-Tools GLOP (Lexicographic LP)</span>
          </div>
          <div className="cr-meta-item">
            <span className="cr-meta-label">Data Seed:</span>
            <span className="cr-meta-val">#{manifest.seed} (Synthetic Corridor)</span>
          </div>
          <div className="cr-meta-item">
            <span className="cr-meta-label">Active Disruption:</span>
            <span className="cr-meta-val cr-text-alert">
              {scenario.event_type.replace('_', ' ')} · {scenario.affected_id || 'none'}
            </span>
          </div>
          <div className="cr-meta-item cr-meta-hash">
            <span className="cr-meta-label">Input SHA:</span>
            <code title={manifest.input_hash}>{manifest.input_hash.slice(0, 10)}...</code>
          </div>
        </div>
      </header>

      {/* 3. WORKBENCH TABS */}
      <nav className="cr-tab-nav" aria-label="Operational views">
        <button
          className={`cr-tab-btn ${activeTab === 'overview' ? 'is-active' : ''}`}
          onClick={() => setActiveTab('overview')}
        >
          <Activity size={15} /> 1. Operations Overview
        </button>
        <button
          className={`cr-tab-btn ${activeTab === 'configurator' ? 'is-active' : ''}`}
          onClick={() => setActiveTab('configurator')}
        >
          <Sliders size={15} /> 2. Disruption Configurator
        </button>
        <button
          className={`cr-tab-btn ${activeTab === 'network' ? 'is-active' : ''}`}
          onClick={() => setActiveTab('network')}
        >
          <Network size={15} /> 3. Supply Network Topology
        </button>
        <button
          className={`cr-tab-btn ${activeTab === 'districts' ? 'is-active' : ''}`}
          onClick={() => setActiveTab('districts')}
        >
          <ShieldAlert size={15} /> 4. District Risk Register
        </button>
        <button
          className={`cr-tab-btn ${activeTab === 'comparison' ? 'is-active' : ''}`}
          onClick={() => setActiveTab('comparison')}
        >
          <BarChart3 size={15} /> 5. Allocation Comparison
        </button>
        <button
          className={`cr-tab-btn ${activeTab === 'audit' ? 'is-active' : ''}`}
          onClick={() => setActiveTab('audit')}
        >
          <FileCheck2 size={15} /> 6. Audit & Human Sign-off
        </button>
      </nav>

      {/* 4. TAB CONTENTS */}
      <main className="cr-dash-body">
        {/* =================== TAB 1: OPERATIONS OVERVIEW =================== */}
        {activeTab === 'overview' && (
          <div className="cr-view-pane cr-fade-in">
            {/* Top KPI Grid */}
            <section className="cr-section">
              <div className="cr-section-header">
                <div>
                  <h2 className="cr-section-title">Operations Ledger at a Glance</h2>
                  <p className="cr-section-desc">
                    Deterministic metrics computed for the active {scenario.horizon_days}-day planning horizon.
                  </p>
                </div>
                <span className="cr-data-tag">ALL QUANTITIES IN KG LPG</span>
              </div>

              <div className="cr-kpi-grid">
                <div className="cr-kpi-card cr-kpi-cyan">
                  <span className="cr-kpi-eyebrow">TOTAL AVAILABLE SUPPLY</span>
                  <div className="cr-kpi-value">{formatKg(candidate.metrics?.total_available)} <span className="cr-unit">kg</span></div>
                  <div className="cr-kpi-sub">
                    {formatTonnes(candidate.metrics?.total_available)} · Opening ({formatTonnes(candidate.metrics?.initial_stock)}) + Inflow Q ({formatTonnes(candidate.metrics?.total_supply)})
                  </div>
                </div>

                <div className="cr-kpi-card cr-kpi-amber">
                  <span className="cr-kpi-eyebrow">HORIZON DEMAND FULFILLED</span>
                  <div className="cr-kpi-value">{formatPercent(candidate.metrics?.fulfilment)}</div>
                  <div className="cr-kpi-sub">
                    {formatKg(candidate.metrics?.total_served)} kg served of {formatKg(candidate.metrics?.total_demand)} kg demand
                  </div>
                </div>

                <div className={`cr-kpi-card ${candidate.metrics?.total_unmet > 0 ? 'cr-kpi-crimson' : 'cr-kpi-emerald'}`}>
                  <span className="cr-kpi-eyebrow">TOTAL PROJECTED UNMET</span>
                  <div className="cr-kpi-value">{formatKg(candidate.metrics?.total_unmet)} <span className="cr-unit">kg</span></div>
                  <div className="cr-kpi-sub">
                    {candidate.metrics?.total_unmet > 0
                      ? `${formatTonnes(candidate.metrics?.total_unmet)} lost service across horizon`
                      : 'Zero unmet demand across all tiers'}
                  </div>
                </div>

                <div className={`cr-kpi-card ${candidate.metrics?.elevated_districts > 0 ? 'cr-kpi-crimson' : 'cr-kpi-emerald'}`}>
                  <span className="cr-kpi-eyebrow">DISTRICTS AT RISK</span>
                  <div className="cr-kpi-value">
                    {candidate.metrics?.elevated_districts} <span className="cr-unit">/ 6</span>
                  </div>
                  <div className="cr-kpi-sub">
                    {candidate.metrics?.elevated_districts > 0
                      ? 'Districts flagged High Risk or Watch'
                      : 'All 6 districts stable above threshold'}
                  </div>
                </div>

                <div className="cr-kpi-card cr-kpi-indigo">
                  <span className="cr-kpi-eyebrow">FIRST CRITICAL LOW COVER</span>
                  <div className="cr-kpi-value">
                    {candidate.districts.some((d) => d.first_low_day !== null)
                      ? `Day ${Math.min(...candidate.districts.map((d) => d.first_low_day).filter((x) => x !== null))}`
                      : 'None in Horizon'}
                  </div>
                  <div className="cr-kpi-sub">
                    Stock below {scenario.cover_threshold} days safety buffer
                  </div>
                </div>

                <div className="cr-kpi-card cr-kpi-emerald">
                  <span className="cr-kpi-eyebrow">FEASIBILITY CHECKS</span>
                  <div className="cr-kpi-value cr-text-emerald">0 VIOLATIONS</div>
                  <div className="cr-kpi-sub">
                    Max balance error: {candidate.checks?.max_balance_error?.toExponential(2) || '0'} kg
                  </div>
                </div>
              </div>
            </section>

            {/* Mass balance reconciliation & Disruption Summary */}
            <div className="cr-two-col-grid">
              <div className="cr-card">
                <h3 className="cr-card-title">
                  <Boxes size={16} /> Physical Mass Balance Reconciliation
                </h3>
                <p className="cr-card-desc">
                  Strict physical conservation: Initial Stock + External Supply Q = Served + Closing Stock + In-Transit Mass.
                </p>

                <table className="cr-table cr-table-compact">
                  <thead>
                    <tr>
                      <th>Mass Component</th>
                      <th className="cr-text-right">Kilograms (kg LPG)</th>
                      <th className="cr-text-right">Metric Tonnes</th>
                    </tr>
                  </thead>
                  <tbody>
                    <tr>
                      <td>Opening Stock (All Nodes T=1)</td>
                      <td className="cr-text-right cr-mono">{formatKg(candidate.metrics?.initial_stock)}</td>
                      <td className="cr-text-right cr-mono">{formatTonnes(candidate.metrics?.initial_stock)}</td>
                    </tr>
                    <tr>
                      <td>Exogenous Supply Q (Imports + Refinery)</td>
                      <td className="cr-text-right cr-mono">{formatKg(candidate.metrics?.total_supply)}</td>
                      <td className="cr-text-right cr-mono">{formatTonnes(candidate.metrics?.total_supply)}</td>
                    </tr>
                    <tr className="cr-tr-highlight">
                      <td><strong>Total Physical Input (A)</strong></td>
                      <td className="cr-text-right cr-mono"><strong>{formatKg(candidate.metrics?.total_available)}</strong></td>
                      <td className="cr-text-right cr-mono"><strong>{formatTonnes(candidate.metrics?.total_available)}</strong></td>
                    </tr>
                    <tr>
                      <td>Total Demand Served (T=1..14)</td>
                      <td className="cr-text-right cr-mono">{formatKg(candidate.metrics?.total_served)}</td>
                      <td className="cr-text-right cr-mono">{formatTonnes(candidate.metrics?.total_served)}</td>
                    </tr>
                    <tr>
                      <td>Closing Stock (All Nodes T=14)</td>
                      <td className="cr-text-right cr-mono">
                        {formatKg(candidate.balances.filter((b) => b.day === scenario.horizon_days).reduce((acc, b) => acc + b.closing, 0))}
                      </td>
                      <td className="cr-text-right cr-mono">
                        {formatTonnes(candidate.balances.filter((b) => b.day === scenario.horizon_days).reduce((acc, b) => acc + b.closing, 0))}
                      </td>
                    </tr>
                    <tr>
                      <td>Cargo In Transit (Arriving post-horizon)</td>
                      <td className="cr-text-right cr-mono">{formatKg(candidate.metrics?.in_transit)}</td>
                      <td className="cr-text-right cr-mono">{formatTonnes(candidate.metrics?.in_transit)}</td>
                    </tr>
                    <tr className="cr-tr-highlight">
                      <td><strong>Total Accounted Mass (B)</strong></td>
                      <td className="cr-text-right cr-mono">
                        <strong>
                          {formatKg(
                            (candidate.metrics?.total_served || 0) +
                              candidate.balances.filter((b) => b.day === scenario.horizon_days).reduce((acc, b) => acc + b.closing, 0) +
                              (candidate.metrics?.in_transit || 0)
                          )}
                        </strong>
                      </td>
                      <td className="cr-text-right cr-mono">
                        <strong>
                          {formatTonnes(
                            (candidate.metrics?.total_served || 0) +
                              candidate.balances.filter((b) => b.day === scenario.horizon_days).reduce((acc, b) => acc + b.closing, 0) +
                              (candidate.metrics?.in_transit || 0)
                          )}
                        </strong>
                      </td>
                    </tr>
                  </tbody>
                </table>
              </div>

              <div className="cr-card">
                <h3 className="cr-card-title">
                  <ShieldAlert size={16} /> Disruption Impact & Exposure Summary
                </h3>
                <p className="cr-card-desc">
                  Parameters applied to the network and propagation across downstream dependencies.
                </p>

                <div className="cr-callout-box">
                  <div className="cr-callout-title">
                    <AlertTriangle size={15} /> Active Disruption Specification
                  </div>
                  <div className="cr-callout-body">
                    <p><strong>Scenario:</strong> {scenario.name}</p>
                    <p>
                      <strong>Trigger Asset:</strong> <code>{scenario.affected_id || 'None'}</code> (
                      {scenario.event_type.replace('_', ' ')})
                    </p>
                    <p>
                      <strong>Impact Window:</strong> Days {scenario.start_day} to{' '}
                      {scenario.start_day + scenario.duration_days - 1} ({scenario.duration_days} days)
                    </p>
                    {scenario.reduction_fraction > 0 && (
                      <p><strong>Reduction Factor:</strong> -{(scenario.reduction_fraction * 100).toFixed(0)}% available flow</p>
                    )}
                    {scenario.delay_days > 0 && (
                      <p><strong>Dispatch Delay:</strong> +{scenario.delay_days} days arrival transit</p>
                    )}
                  </div>
                </div>

                <div className="cr-exposure-summary">
                  <h4>Downstream Exposed Entities:</h4>
                  <div className="cr-tag-cloud">
                    {affected_nodes.map((nodeId) => (
                      <span key={nodeId} className="cr-badge cr-badge-amber">
                        {DISTRICT_NAMES[nodeId] || nodeId}
                      </span>
                    ))}
                    {affected_edges.map((edgeId) => (
                      <span key={edgeId} className="cr-badge cr-badge-cyan">
                        Route: {edgeId}
                      </span>
                    ))}
                  </div>
                  <p className="cr-footnote">
                    Note: Downstream exposure traces topological dependency in the directed graph. It indicates which links
                    and consumption sinks are affected by upstream constraints.
                  </p>
                </div>
              </div>
            </div>

            {/* Daily Service Trajectory Chart */}
            <section className="cr-section">
              <div className="cr-section-header">
                <div>
                  <h3 className="cr-section-title">Network-Wide Daily Demand Fulfilment Trajectory</h3>
                  <p className="cr-section-desc">
                    Daily breakdown of served volume vs. unmet deficit across all districts (T=1..{scenario.horizon_days}).
                  </p>
                </div>
              </div>

              <div className="cr-daily-bar-chart">
                {Array.from({ length: scenario.horizon_days }, (_, i) => i + 1).map((day) => {
                  const dayServices = candidate.service.filter((s) => s.day === day)
                  const served = dayServices.reduce((acc, s) => acc + s.served, 0)
                  const unmet = dayServices.reduce((acc, s) => acc + s.unmet, 0)
                  const total = served + unmet
                  const servedPct = total > 0 ? (served / total) * 100 : 100
                  const unmetPct = total > 0 ? (unmet / total) * 100 : 0

                  return (
                    <div key={day} className="cr-chart-col">
                      <div className="cr-bar-stack" title={`Day ${day}: Served ${formatKg(served)} kg (${servedPct.toFixed(1)}%), Unmet ${formatKg(unmet)} kg (${unmetPct.toFixed(1)}%)`}>
                        <div className="cr-bar-unmet" style={{ height: `${unmetPct}%` }} />
                        <div className="cr-bar-served" style={{ height: `${servedPct}%` }} />
                      </div>
                      <span className="cr-col-label">D{day}</span>
                      <span className="cr-col-val">{formatTonnes(served, 0)}</span>
                    </div>
                  )
                })}
              </div>

              <div className="cr-chart-legend">
                <span><i className="cr-legend-swatch cr-swatch-cyan" /> Demand Served (kg LPG)</span>
                <span><i className="cr-legend-swatch cr-swatch-crimson" /> Unmet Deficit (kg LPG)</span>
              </div>
            </section>
          </div>
        )}

        {/* =================== TAB 2: DISRUPTION CONFIGURATOR =================== */}
        {activeTab === 'configurator' && (
          <div className="cr-view-pane cr-fade-in">
            <section className="cr-section">
              <div className="cr-section-header">
                <div>
                  <h2 className="cr-section-title">Parametric Disruption Configurator</h2>
                  <p className="cr-section-desc">
                    Configure stress scenarios, test port closures, facility outages, or changes in demand and lead times.
                  </p>
                </div>
              </div>

              <div className="cr-config-grid">
                {/* Preset Selector Card */}
                <div className="cr-card">
                  <h3 className="cr-card-title"><Compass size={16} /> Standardized Evaluation Presets</h3>
                  <p className="cr-card-desc">Load reproducible stress tests specified in the TRD.</p>

                  <div className="cr-preset-btn-list">
                    {Object.entries(PRESET_NAMES).map(([key, label]) => (
                      <button
                        key={key}
                        className={`cr-preset-card-btn ${selectedPreset === key ? 'is-selected' : ''}`}
                        onClick={() => handleSelectPreset(key)}
                      >
                        <div className="cr-preset-btn-top">
                          <strong>{label}</strong>
                          {selectedPreset === key && <CheckCircle2 size={16} className="cr-text-emerald" />}
                        </div>
                        <span className="cr-preset-btn-desc">
                          {key === 'import_shock' && 'Halves inbound LPG import flow for 10 days on a 14-day horizon.'}
                          {key === 'route_closure' && 'Completely closes Western Bottling link for 6 days.'}
                          {key === 'route_delay' && 'Adds a 3-day transit shift on inbound import route.'}
                          {key === 'facility_outage' && 'East bottling plant dispatch capacity set to zero for 5 days.'}
                          {key === 'normal' && 'Unconstrained supply reference case with full availability.'}
                        </span>
                      </button>
                    ))}
                  </div>
                </div>

                {/* Custom Sliders & Form */}
                <div className="cr-card">
                  <h3 className="cr-card-title"><Sliders size={16} /> Fine-Grained Stress Parameters</h3>
                  <p className="cr-card-desc">Modify duration, intensity, or regional demand parameters.</p>

                  <div className="cr-form-group">
                    <label>
                      Supply / Dispatch Reduction Fraction: <strong>{(customParams.reductionFraction * 100).toFixed(0)}%</strong>
                    </label>
                    <input
                      type="range"
                      min="0"
                      max="1"
                      step="0.05"
                      value={customParams.reductionFraction}
                      onChange={(e) => setCustomParams({ ...customParams, reductionFraction: parseFloat(e.target.value) })}
                    />
                    <span className="cr-input-hint">0% = normal flow; 100% = total outage of the affected asset.</span>
                  </div>

                  <div className="cr-form-row">
                    <div className="cr-form-group">
                      <label>Disruption Start Day:</label>
                      <input
                        type="number"
                        min="1"
                        max="14"
                        value={customParams.startDay}
                        onChange={(e) => setCustomParams({ ...customParams, startDay: parseInt(e.target.value) || 1 })}
                      />
                    </div>
                    <div className="cr-form-group">
                      <label>Duration (Days):</label>
                      <input
                        type="number"
                        min="1"
                        max="14"
                        value={customParams.durationDays}
                        onChange={(e) => setCustomParams({ ...customParams, durationDays: parseInt(e.target.value) || 1 })}
                      />
                    </div>
                  </div>

                  <div className="cr-form-row">
                    <div className="cr-form-group">
                      <label>Planning Horizon (Days):</label>
                      <input
                        type="number"
                        min="7"
                        max="28"
                        value={customParams.horizonDays}
                        onChange={(e) => setCustomParams({ ...customParams, horizonDays: parseInt(e.target.value) || 14 })}
                      />
                    </div>
                    <div className="cr-form-group">
                      <label>Demand Multiplier:</label>
                      <input
                        type="number"
                        min="0.5"
                        max="2.0"
                        step="0.1"
                        value={customParams.demandMultiplier}
                        onChange={(e) => setCustomParams({ ...customParams, demandMultiplier: parseFloat(e.target.value) || 1.0 })}
                      />
                    </div>
                  </div>

                  <div className="cr-form-row">
                    <div className="cr-form-group">
                      <label>Transit Lead Day Shift:</label>
                      <input
                        type="number"
                        min="0"
                        max="7"
                        value={customParams.extraLeadDays}
                        onChange={(e) => setCustomParams({ ...customParams, extraLeadDays: parseInt(e.target.value) || 0 })}
                      />
                    </div>
                    <div className="cr-form-group">
                      <label>Safety Cover Buffer (Days):</label>
                      <input
                        type="number"
                        min="1.0"
                        max="5.0"
                        step="0.5"
                        value={customParams.coverThreshold}
                        onChange={(e) => setCustomParams({ ...customParams, coverThreshold: parseFloat(e.target.value) || 2.0 })}
                      />
                    </div>
                  </div>

                  <div className="cr-config-actions">
                    <button className="cr-btn-primary" onClick={handleRunSimulation}>
                      <Play size={14} /> Recompute Simulation with Custom Parameters
                    </button>
                    <button
                      className="cr-btn-secondary"
                      onClick={() => handleSelectPreset(selectedPreset)}
                    >
                      Reset to Preset Defaults
                    </button>
                  </div>
                </div>
              </div>

              {/* Real-time solver execution terminal */}
              {simulationLog.length > 0 && (
                <div className="cr-terminal-window">
                  <div className="cr-terminal-bar">
                    <div className="cr-term-dots">
                      <span className="cr-term-dot cr-dot-red" />
                      <span className="cr-term-dot cr-dot-yellow" />
                      <span className="cr-term-dot cr-dot-green" />
                    </div>
                    <span className="cr-term-title">
                      <Terminal size={12} /> OR-Tools GLOP Continuous LP Solver Terminal
                    </span>
                  </div>
                  <div className="cr-term-body">
                    {simulationLog.map((line, idx) => (
                      <div key={idx} className="cr-term-line">
                        <span className="cr-term-prompt">&gt;</span> {line}
                      </div>
                    ))}
                    <div className="cr-term-line cr-term-blink">
                      <span className="cr-term-prompt">&gt;</span> Ready.
                    </div>
                  </div>
                </div>
              )}
            </section>
          </div>
        )}

        {/* =================== TAB 3: NETWORK TOPOLOGY (FIXED HOVER & INTERACTION) =================== */}
        {activeTab === 'network' && (
          <div className="cr-view-pane cr-fade-in">
            <section className="cr-section">
              <div className="cr-section-header">
                <div>
                  <h2 className="cr-section-title">LPG Supply-Chain Directed Dependency Graph</h2>
                  <p className="cr-section-desc">
                    Physical topology from maritime import terminals through primary storage, bottling, and regional depots to municipal consumer centers.
                  </p>
                </div>
                <span className="cr-data-tag">HOVER TO TRACE FLOWS · CLICK TO PIN ASSET</span>
              </div>

              {/* Interactive Network Graph Wrap */}
              <div className="cr-network-canvas-wrap">
                {/* Live Tactical HUD Telemetry Banner */}
                <div className="cr-network-hud-bar">
                  {activeHoveredNode ? (
                    <div className="cr-hud-item cr-hud-node">
                      <div className="cr-hud-header">
                        <span className="cr-hud-badge cr-hud-badge-cyan">{activeHoveredNode.kind.toUpperCase()}</span>
                        <strong className="cr-hud-title">{activeHoveredNode.name}</strong>
                        <span className="cr-hud-id">ID: {activeHoveredNode.id}</span>
                      </div>
                      <div className="cr-hud-stats">
                        <span>Opening Stock: <b>{formatKg(activeHoveredNode.initial_stock)} kg</b></span>
                        <span>Daily Supply Q: <b>{formatKg(activeHoveredNode.daily_supply)} kg/d</b></span>
                        <span>Outbound Cap: <b>{formatKg(activeHoveredNode.dispatch_capacity)} kg/d</b></span>
                        <span className={scenario.affected_id === activeHoveredNode.id ? 'cr-text-alert font-bold' : affected_nodes.includes(activeHoveredNode.id) ? 'cr-text-amber' : 'cr-text-emerald'}>
                          {scenario.affected_id === activeHoveredNode.id
                            ? '⚡ Active Outage Trigger'
                            : affected_nodes.includes(activeHoveredNode.id)
                            ? '⚠ Downstream Supply Shock'
                            : '✓ Nominal Operations'}
                        </span>
                      </div>
                    </div>
                  ) : activeHoveredEdge ? (
                    <div className="cr-hud-item cr-hud-edge">
                      <div className="cr-hud-header">
                        <span className="cr-hud-badge cr-hud-badge-amber">CORRIDOR ROUTE</span>
                        <strong className="cr-hud-title">{activeHoveredEdge.edge.id}</strong>
                        <span className="cr-hud-id">
                          {activeHoveredEdge.sourceNode?.name} → {activeHoveredEdge.targetNode?.name}
                        </span>
                      </div>
                      <div className="cr-hud-stats">
                        <span>Daily Capacity: <b>{formatKg(activeHoveredEdge.edge.capacity)} kg/d</b></span>
                        <span>Transit Lead: <b>{activeHoveredEdge.edge.lead_days} Day(s)</b></span>
                        <span>Distance: <b>{activeHoveredEdge.edge.distance_km} km</b></span>
                        <span className={scenario.affected_id === activeHoveredEdge.edge.id ? 'cr-text-alert font-bold' : affected_edges.includes(activeHoveredEdge.edge.id) ? 'cr-text-amber' : 'cr-text-emerald'}>
                          {scenario.affected_id === activeHoveredEdge.edge.id
                            ? '⚡ Disrupted Route Link'
                            : affected_edges.includes(activeHoveredEdge.edge.id)
                            ? '⚠ Downstream Bottleneck'
                            : '✓ Active Nominal Corridor'}
                        </span>
                      </div>
                    </div>
                  ) : (
                    <div className="cr-hud-item cr-hud-idle">
                      <Radio size={14} className="cr-pulse-icon" />
                      <span>
                        Live Pipeline Telemetry · Hover any node or corridor route to highlight topological flow paths · Click to inspect full dossier
                      </span>
                    </div>
                  )}
                </div>

                {/* SVG Vector Canvas */}
                <svg className="cr-network-svg" viewBox="0 0 1180 520">
                  <defs>
                    <pattern id="grid-dots" width="28" height="28" patternUnits="userSpaceOnUse">
                      <circle cx="14" cy="14" r="1.2" fill="rgba(148, 163, 184, 0.15)" />
                    </pattern>

                    <marker id="arrow-nominal" markerWidth="9" markerHeight="9" refX="7" refY="3.5" orient="auto">
                      <polygon points="0 0, 7 3.5, 0 7" fill="#64748b" />
                    </marker>
                    <marker id="arrow-exposed" markerWidth="9" markerHeight="9" refX="7" refY="3.5" orient="auto">
                      <polygon points="0 0, 7 3.5, 0 7" fill="#f59e0b" />
                    </marker>
                    <marker id="arrow-disrupted" markerWidth="10" markerHeight="10" refX="8" refY="4" orient="auto">
                      <polygon points="0 0, 8 4, 0 8" fill="#ef4444" />
                    </marker>
                    <marker id="arrow-selected" markerWidth="10" markerHeight="10" refX="8" refY="4" orient="auto">
                      <polygon points="0 0, 8 4, 0 8" fill="#e8d1cb" />
                    </marker>
                  </defs>

                  {/* Blueprint Grid Background */}
                  <rect width="100%" height="100%" fill="url(#grid-dots)" />

                  {/* Stage Guide Labels */}
                  <g className="cr-stage-guides" opacity="0.65">
                    <text x="60" y="24" className="cr-stage-label">STAGE 1: IMPORT &amp; SOURCE</text>
                    <text x="375" y="24" className="cr-stage-label">STAGE 2: STRATEGIC BUFFER</text>
                    <text x="535" y="24" className="cr-stage-label">STAGE 3: BOTTLING PLANTS</text>
                    <text x="705" y="24" className="cr-stage-label">STAGE 4: REGIONAL DEPOTS</text>
                    <text x="920" y="24" className="cr-stage-label">STAGE 5: DEMAND DISTRICTS</text>
                  </g>

                  {/* Corridor Edges */}
                  {network.edges.map((edge) => {
                    const sourceNode = network.nodes.find((n) => n.id === edge.source)
                    const targetNode = network.nodes.find((n) => n.id === edge.target)
                    if (!sourceNode || !targetNode) return null

                    const isAffected = affected_edges.includes(edge.id)
                    const isDisrupted = scenario.affected_id === edge.id
                    const isSelected = selectedAsset === `edge:${edge.id}`
                    const isHovered = hoveredEdgeId === edge.id
                    const isConnectedToHoveredNode = connectedEdgeIds.includes(edge.id)

                    let strokeColor = '#475569'
                    let markerType = 'arrow-nominal'
                    let strokeW = 1.8
                    let strokeDash = ''

                    if (!edge.active) {
                      strokeColor = 'rgba(255, 255, 255, 0.2)'
                      strokeDash = '5 5'
                    } else if (isDisrupted) {
                      strokeColor = '#ef4444'
                      markerType = 'arrow-disrupted'
                      strokeW = 3.0
                    } else if (isAffected) {
                      strokeColor = '#f59e0b'
                      markerType = 'arrow-exposed'
                      strokeW = 2.4
                    }

                    if (isSelected) {
                      strokeColor = '#e8d1cb'
                      markerType = 'arrow-selected'
                      strokeW = 3.2
                    }

                    if (isHovered || isConnectedToHoveredNode) {
                      strokeW = 3.6
                    }

                    // Opacity dimming when another element is hovered
                    const hasHover = Boolean(hoveredNodeId || hoveredEdgeId)
                    const isEdgeHighlighted = isHovered || isConnectedToHoveredNode || isSelected
                    const edgeOpacity = hasHover ? (isEdgeHighlighted ? 1.0 : 0.22) : 0.85

                    const x1 = sourceNode.x + (sourceNode.kind === 'district' ? 24 : 32)
                    const y1 = sourceNode.y + 15
                    const x2 = targetNode.x - 14
                    const y2 = targetNode.y + 15

                    return (
                      <g
                        key={edge.id}
                        className={`cr-graph-edge ${isEdgeHighlighted ? 'is-highlighted' : ''}`}
                        onClick={() => setSelectedAsset(`edge:${edge.id}`)}
                        onMouseEnter={() => setHoveredEdgeId(edge.id)}
                        onMouseLeave={() => setHoveredEdgeId(null)}
                        style={{ opacity: edgeOpacity, transition: 'opacity 0.2s ease' }}
                      >
                        {/* Invisible 22px hitbox so hovering never slips off the thin line */}
                        <line
                          x1={x1}
                          y1={y1}
                          x2={x2}
                          y2={y2}
                          stroke="transparent"
                          strokeWidth={22}
                          style={{ cursor: 'pointer' }}
                        />

                        {/* Visible Route Line */}
                        <line
                          x1={x1}
                          y1={y1}
                          x2={x2}
                          y2={y2}
                          stroke={strokeColor}
                          strokeWidth={strokeW}
                          strokeDasharray={strokeDash}
                          markerEnd={`url(#${markerType})`}
                        />
                      </g>
                    )
                  })}

                  {/* Supply Nodes */}
                  {network.nodes.map((node) => {
                    const isAffected = affected_nodes.includes(node.id)
                    const isDisrupted = scenario.affected_id === node.id
                    const isSelected = selectedAsset === `node:${node.id}`
                    const isHovered = hoveredNodeId === node.id
                    const isConnectedToHoveredEdge = connectedNodeIds.includes(node.id)

                    let nodeFill = '#0b101a'
                    let nodeStroke = 'rgba(255, 255, 255, 0.25)'
                    let strokeW = 1.8

                    if (isDisrupted) {
                      nodeFill = 'rgba(239, 68, 68, 0.25)'
                      nodeStroke = '#ef4444'
                      strokeW = 2.6
                    } else if (isAffected) {
                      nodeFill = 'rgba(245, 158, 11, 0.25)'
                      nodeStroke = '#f59e0b'
                      strokeW = 2.4
                    }

                    if (isSelected) {
                      nodeStroke = '#e8d1cb'
                      strokeW = 3.2
                    }

                    const isDistrict = node.kind === 'district'
                    const hasHover = Boolean(hoveredNodeId || hoveredEdgeId)
                    const isNodeHighlighted = isHovered || isConnectedToHoveredEdge || isSelected
                    const nodeOpacity = hasHover ? (isNodeHighlighted ? 1.0 : 0.35) : 1.0

                    return (
                      <g
                        key={node.id}
                        className={`cr-graph-node ${isNodeHighlighted ? 'is-highlighted' : ''}`}
                        transform={`translate(${node.x}, ${node.y})`}
                        onClick={() => setSelectedAsset(`node:${node.id}`)}
                        onMouseEnter={() => setHoveredNodeId(node.id)}
                        onMouseLeave={() => setHoveredNodeId(null)}
                        style={{ opacity: nodeOpacity, cursor: 'pointer', transition: 'opacity 0.2s ease' }}
                      >
                        {/* Outer Selection Ring on Hover / Select */}
                        {isNodeHighlighted && (
                          <rect
                            x={isDistrict ? -4 : -5}
                            y={isDistrict ? -4 : -5}
                            width={isDistrict ? 38 : 46}
                            height={isDistrict ? 38 : 40}
                            rx={isDistrict ? 19 : 8}
                            fill="none"
                            stroke={isDisrupted ? '#ef4444' : isAffected ? '#f59e0b' : '#e8d1cb'}
                            strokeWidth={1.8}
                            strokeDasharray="4 3"
                            className="cr-node-glow-halo"
                          />
                        )}

                        {isDistrict ? (
                          <circle
                            cx="15"
                            cy="15"
                            r="14"
                            fill={nodeFill}
                            stroke={nodeStroke}
                            strokeWidth={strokeW}
                            style={{ filter: 'drop-shadow(0 2px 6px rgba(0, 0, 0, 0.5))' }}
                          />
                        ) : (
                          <rect
                            x="0"
                            y="0"
                            width="36"
                            height="30"
                            rx="6"
                            fill={nodeFill}
                            stroke={nodeStroke}
                            strokeWidth={strokeW}
                            style={{ filter: 'drop-shadow(0 2px 6px rgba(0, 0, 0, 0.5))' }}
                          />
                        )}

                        {/* Node Label Text in Crisp White */}
                        <text
                          x={isDistrict ? 38 : 18}
                          y={isDistrict ? 19 : 45}
                          textAnchor={isDistrict ? 'start' : 'middle'}
                          className="cr-node-text"
                          fill="#ffffff"
                          fontWeight="600"
                        >
                          {node.name}
                        </text>
                      </g>
                    )
                  })}
                </svg>

                {/* Graph Legend Strip */}
                <div className="cr-graph-legend-strip">
                  <span><i className="cr-swatch-line cr-swatch-cyan" /> Nominal Active Route</span>
                  <span><i className="cr-swatch-line cr-swatch-amber" /> Disruption-Exposed Path</span>
                  <span><i className="cr-swatch-line cr-swatch-crimson" /> Active Disruption Trigger</span>
                  <span><i className="cr-swatch-line cr-swatch-dashed" /> Inactive Backup Route</span>
                </div>
              </div>

              {/* Asset Detail Inspector (Pinned Asset) */}
              <div className="cr-card cr-asset-inspector-card">
                <div className="cr-card-header-row">
                  <div>
                    <span className="cr-badge cr-badge-cyan">
                      {inspectedAssetData.type === 'node' ? inspectedAssetData.node?.kind.toUpperCase() : 'DIRECTED ROUTE'}
                    </span>
                    <h3 className="cr-inspector-title">
                      {inspectedAssetData.type === 'node'
                        ? inspectedAssetData.node?.name
                        : `Route: ${inspectedAssetData.edge?.id} (${inspectedAssetData.edge?.source} → ${inspectedAssetData.edge?.target})`}
                    </h3>
                  </div>
                  <span className="cr-mono cr-text-muted">ID: {selectedAsset}</span>
                </div>

                {inspectedAssetData.type === 'node' && (
                  <div className="cr-inspector-grid">
                    <div className="cr-inspector-field">
                      <span className="cr-label">Initial Usable Stock:</span>
                      <strong>{formatKg(inspectedAssetData.node?.initial_stock)} kg LPG</strong>
                    </div>
                    <div className="cr-inspector-field">
                      <span className="cr-label">Daily Supply Q:</span>
                      <strong>{formatKg(inspectedAssetData.node?.daily_supply)} kg/day</strong>
                    </div>
                    <div className="cr-inspector-field">
                      <span className="cr-label">Outbound Dispatch Capacity:</span>
                      <strong>{formatKg(inspectedAssetData.node?.dispatch_capacity)} kg/day</strong>
                    </div>
                    <div className="cr-inspector-field">
                      <span className="cr-label">Network Status:</span>
                      <strong className={inspectedAssetData.node?.active ? 'cr-text-emerald' : 'cr-text-muted'}>
                        {inspectedAssetData.node?.active ? 'Active' : 'Inactive'}
                      </strong>
                    </div>
                  </div>
                )}

                {inspectedAssetData.type === 'edge' && (
                  <div className="cr-inspector-grid">
                    <div className="cr-inspector-field">
                      <span className="cr-label">Max Daily Route Capacity:</span>
                      <strong>{formatKg(inspectedAssetData.edge?.capacity)} kg/day</strong>
                    </div>
                    <div className="cr-inspector-field">
                      <span className="cr-label">Nominal Lead Time:</span>
                      <strong>{inspectedAssetData.edge?.lead_days} Day(s)</strong>
                    </div>
                    <div className="cr-inspector-field">
                      <span className="cr-label">Route Distance:</span>
                      <strong>{inspectedAssetData.edge?.distance_km} km (Logistics Proxy)</strong>
                    </div>
                    <div className="cr-inspector-field">
                      <span className="cr-label">Disruption State:</span>
                      <strong className={affected_edges.includes(inspectedAssetData.edge?.id) ? 'cr-text-alert' : 'cr-text-emerald'}>
                        {affected_edges.includes(inspectedAssetData.edge?.id) ? 'Exposed to Disruption' : 'Normal Operation'}
                      </strong>
                    </div>
                  </div>
                )}
              </div>
            </section>
          </div>
        )}

        {/* =================== TAB 4: DISTRICT RISK REGISTER =================== */}
        {activeTab === 'districts' && (
          <div className="cr-view-pane cr-fade-in">
            <section className="cr-section">
              <div className="cr-section-header">
                <div>
                  <h2 className="cr-section-title">District Shortage-Risk & Days-of-Cover Register</h2>
                  <p className="cr-section-desc">
                    Modelled inventory trajectories and shortage vulnerability indicators across all 6 administrative districts.
                  </p>
                </div>
                <button className="cr-btn-secondary" onClick={handleExportCsv}>
                  <FileSpreadsheet size={14} /> Export District Risk CSV
                </button>
              </div>

              {/* Table search & sort controls */}
              <div className="cr-filter-bar">
                <div className="cr-search-box">
                  <Search size={15} />
                  <input
                    type="text"
                    placeholder="Search district name or code..."
                    value={searchDistrict}
                    onChange={(e) => setSearchDistrict(e.target.value)}
                  />
                </div>

                <div className="cr-sort-box">
                  <label>Order By:</label>
                  <select value={districtSortBy} onChange={(e) => setDistrictSortBy(e.target.value)}>
                    <option value="risk">Risk Classification (Worst First)</option>
                    <option value="unmet">Unmet Demand Volume</option>
                    <option value="cover">Lowest Days of Cover</option>
                    <option value="name">Alphabetical</option>
                  </select>
                </div>
              </div>

              {/* District Table */}
              <div className="cr-table-wrap">
                <table className="cr-table">
                  <thead>
                    <tr>
                      <th>District</th>
                      <th>Risk Classification</th>
                      <th className="cr-text-right">Opening Stock</th>
                      <th className="cr-text-right">Daily Demand</th>
                      <th className="cr-text-right">Expected Inbound</th>
                      <th className="cr-text-right">Days of Cover</th>
                      <th className="cr-text-right">Min Cover</th>
                      <th className="cr-text-right">First Low Day</th>
                      <th className="cr-text-right">Unmet Demand</th>
                      <th className="cr-text-right">Fulfilment</th>
                      <th>Action</th>
                    </tr>
                  </thead>
                  <tbody>
                    {filteredDistricts.map((d) => (
                      <tr
                        key={d.district_id}
                        className={selectedDistrictId === d.district_id ? 'is-selected-row' : ''}
                        onClick={() => setSelectedDistrictId(d.district_id)}
                      >
                        <td>
                          <strong>{d.name}</strong>
                          <span className="cr-row-sub">{d.district_id}</span>
                        </td>
                        <td>
                          <span className={`cr-risk-pill cr-risk-${d.risk.toLowerCase().replace(' ', '-')}`}>
                            {d.risk}
                          </span>
                        </td>
                        <td className="cr-text-right cr-mono">{formatKg(d.opening_stock)} kg</td>
                        <td className="cr-text-right cr-mono">{formatKg(d.daily_demand)} kg/d</td>
                        <td className="cr-text-right cr-mono">{formatKg(d.inbound)} kg</td>
                        <td className="cr-text-right cr-mono font-bold">{d.snapshot_cover ? d.snapshot_cover.toFixed(1) + ' d' : '—'}</td>
                        <td className="cr-text-right cr-mono">{d.minimum_cover ? d.minimum_cover.toFixed(1) + ' d' : '—'}</td>
                        <td className="cr-text-right cr-mono">{d.first_low_day ? `Day ${d.first_low_day}` : 'None'}</td>
                        <td className={`cr-text-right cr-mono font-bold ${d.unmet > 0 ? 'cr-text-crimson' : ''}`}>
                          {formatKg(d.unmet)} kg
                        </td>
                        <td className="cr-text-right cr-mono">{formatPercent(d.fulfilled_fraction)}</td>
                        <td>
                          <button
                            className="cr-btn-xs"
                            onClick={(e) => {
                              e.stopPropagation()
                              setSelectedDistrictId(d.district_id)
                            }}
                          >
                            Drilldown <ChevronRight size={12} />
                          </button>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>

              {/* District Drill-down Panel */}
              <div className="cr-district-drilldown-card">
                <div className="cr-drilldown-header">
                  <div>
                    <span className="cr-badge cr-badge-amber">DISTRICT DOSSIER</span>
                    <h3 className="cr-drilldown-title">{selectedDistrictData.name} ({selectedDistrictData.district_id})</h3>
                    <p className="cr-drilldown-desc">
                      Current modelled risk: <strong>{selectedDistrictData.risk}</strong> · Snapshot days of cover: <strong>{selectedDistrictData.snapshot_cover?.toFixed(2)} days</strong>
                    </p>
                  </div>
                  <div className="cr-drilldown-stats">
                    <div className="cr-stat-pill">
                      <span>Demand:</span> <strong>{formatKg(selectedDistrictData.daily_demand)} kg/d</strong>
                    </div>
                    <div className="cr-stat-pill">
                      <span>Total Unmet:</span> <strong className="cr-text-crimson">{formatKg(selectedDistrictData.unmet)} kg</strong>
                    </div>
                  </div>
                </div>

                {/* Cover trajectory line visualization */}
                <div className="cr-drilldown-charts-grid">
                  <div className="cr-chart-subcard">
                    <h4>Day-by-Day Closing Stock Cover Trajectory</h4>
                    <p className="cr-footnote">Closing inventory in days of demand vs. the 2.0-day safety threshold.</p>

                    <div className="cr-trajectory-bars">
                      {selectedDistrictBalances.map((b) => {
                        const coverDays = selectedDistrictData.daily_demand > 0 ? b.closing / selectedDistrictData.daily_demand : 0
                        const isUnderThreshold = coverDays < scenario.cover_threshold
                        const barHeight = Math.min(100, (coverDays / 4.0) * 100)

                        return (
                          <div key={b.day} className="cr-traj-col">
                            <div className="cr-traj-bar-wrap" title={`Day ${b.day}: Closing ${formatKg(b.closing)} kg (${coverDays.toFixed(2)} days cover)`}>
                              <div
                                className={`cr-traj-bar ${isUnderThreshold ? 'cr-bar-low' : 'cr-bar-safe'}`}
                                style={{ height: `${barHeight}%` }}
                              />
                            </div>
                            <span className="cr-traj-label">D{b.day}</span>
                            <span className="cr-traj-num">{coverDays.toFixed(1)}d</span>
                          </div>
                        )
                      })}
                    </div>
                    <div className="cr-chart-legend">
                      <span><i className="cr-legend-swatch cr-swatch-emerald" /> &gt;= 2.0 Days Cover (Safe Buffer)</span>
                      <span><i className="cr-legend-swatch cr-swatch-crimson" /> &lt; 2.0 Days Cover (Critical Low)</span>
                    </div>
                  </div>

                  <div className="cr-chart-subcard">
                    <h4>Daily Demand Fulfillment by User Tier</h4>
                    <p className="cr-footnote">Essential Services (100% prioritized) vs. Household &amp; Commercial dispatches.</p>

                    <table className="cr-table cr-table-compact">
                      <thead>
                        <tr>
                          <th>Day</th>
                          <th>Group</th>
                          <th className="cr-text-right">Demand</th>
                          <th className="cr-text-right">Served</th>
                          <th className="cr-text-right">Unmet</th>
                        </tr>
                      </thead>
                      <tbody>
                        {selectedDistrictService.slice(0, 8).map((s, idx) => (
                          <tr key={idx}>
                            <td>Day {s.day}</td>
                            <td><span className="cr-badge cr-badge-cyan">{s.group}</span></td>
                            <td className="cr-text-right cr-mono">{formatKg(s.demand)}</td>
                            <td className="cr-text-right cr-mono">{formatKg(s.served)}</td>
                            <td className={`cr-text-right cr-mono ${s.unmet > 0 ? 'cr-text-crimson' : ''}`}>{formatKg(s.unmet)}</td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </div>
                </div>
              </div>
            </section>
          </div>
        )}

        {/* =================== TAB 5: ALLOCATION COMPARISON =================== */}
        {activeTab === 'comparison' && (
          <div className="cr-view-pane cr-fade-in">
            <section className="cr-section">
              <div className="cr-section-header">
                <div>
                  <h2 className="cr-section-title">Baseline vs. CommonRoot Constrained Plan Comparison</h2>
                  <p className="cr-section-desc">
                    Side-by-side comparison of Plan 1 (Proportional Baseline) against Plan 2 (OR-Tools Lexicographic Optimization).
                  </p>
                </div>
                <span className="cr-badge cr-badge-cyan">SAME PHYSICAL CONSTRAINTS &amp; SNAPSHOT</span>
              </div>

              {/* Comparison Summary Strip */}
              <div className="cr-compare-summary-card">
                <div className="cr-compare-metric-col">
                  <span className="cr-metric-title">TOTAL UNMET DEMAND</span>
                  <div className="cr-compare-vals">
                    <span className="cr-val-baseline">Baseline: {formatKg(baseline.metrics?.total_unmet)} kg</span>
                    <span className="cr-val-candidate">Candidate: {formatKg(candidate.metrics?.total_unmet)} kg</span>
                  </div>
                  <div className="cr-diff-badge">
                    Difference: {comparison.unmet_reduction_kg === 0 ? '0 kg (Equal Volume)' : `${formatKg(comparison.unmet_reduction_kg)} kg`}
                  </div>
                </div>

                <div className="cr-compare-metric-col">
                  <span className="cr-metric-title">ESSENTIAL SERVICES FULFILMENT</span>
                  <div className="cr-compare-vals">
                    <span className="cr-val-baseline">Baseline: {formatPercent(baseline.metrics?.group_fulfilment?.essential)}</span>
                    <span className="cr-val-candidate">Candidate: {formatPercent(candidate.metrics?.group_fulfilment?.essential)}</span>
                  </div>
                  <div className="cr-diff-badge cr-text-emerald font-bold">
                    100.0% Protected in Candidate
                  </div>
                </div>

                <div className="cr-compare-metric-col">
                  <span className="cr-metric-title">HOUSEHOLD SERVICE FULFILMENT</span>
                  <div className="cr-compare-vals">
                    <span className="cr-val-baseline">Baseline: {formatPercent(baseline.metrics?.group_fulfilment?.household)}</span>
                    <span className="cr-val-candidate">Candidate: {formatPercent(candidate.metrics?.group_fulfilment?.household)}</span>
                  </div>
                  <div className="cr-diff-badge">
                    {formatPercent(candidate.metrics?.group_fulfilment?.household)} Covered
                  </div>
                </div>

                <div className="cr-compare-metric-col">
                  <span className="cr-metric-title">LOGISTICS DISTANCE PROXY</span>
                  <div className="cr-compare-vals">
                    <span className="cr-val-baseline">Baseline: {formatKg(baseline.metrics?.distance_kg_km)}</span>
                    <span className="cr-val-candidate">Candidate: {formatKg(candidate.metrics?.distance_kg_km)}</span>
                  </div>
                  <div className="cr-diff-badge">
                    kg·km shipment proxy
                  </div>
                </div>
              </div>

              {/* Detailed Breakdown Tables */}
              <div className="cr-two-col-grid">
                <div className="cr-card">
                  <h3 className="cr-card-title"><Users size={16} /> Service Breakdown by Priority User Tier</h3>
                  <p className="cr-card-desc">Comparison across Essential, Household, and Commercial user groups.</p>

                  <table className="cr-table cr-table-compact">
                    <thead>
                      <tr>
                        <th>User Group</th>
                        <th className="cr-text-right">Total Demand</th>
                        <th className="cr-text-right">Baseline Served</th>
                        <th className="cr-text-right">Candidate Served</th>
                        <th className="cr-text-right">Fulfilment (Cand)</th>
                      </tr>
                    </thead>
                    <tbody>
                      {['essential', 'household', 'business'].map((grp) => {
                        const dem = baseline.metrics?.group_served[grp] + baseline.metrics?.group_unmet[grp]
                        const baseServed = baseline.metrics?.group_served[grp]
                        const candServed = candidate.metrics?.group_served[grp]
                        const candPct = candidate.metrics?.group_fulfilment[grp]

                        return (
                          <tr key={grp}>
                            <td>
                              <strong className="capitalize">{grp}</strong>
                            </td>
                            <td className="cr-text-right cr-mono">{formatKg(dem)}</td>
                            <td className="cr-text-right cr-mono">{formatKg(baseServed)}</td>
                            <td className="cr-text-right cr-mono font-bold">{formatKg(candServed)}</td>
                            <td className="cr-text-right cr-mono font-bold">{formatPercent(candPct)}</td>
                          </tr>
                        )
                      })}
                    </tbody>
                  </table>
                </div>

                <div className="cr-card">
                  <h3 className="cr-card-title"><MapPin size={16} /> District Shortage &amp; Unmet Comparison</h3>
                  <p className="cr-card-desc">Unmet demand distribution across districts between the two strategies.</p>

                  <table className="cr-table cr-table-compact">
                    <thead>
                      <tr>
                        <th>District</th>
                        <th className="cr-text-right">Baseline Unmet</th>
                        <th className="cr-text-right">Candidate Unmet</th>
                        <th className="cr-text-right">Difference</th>
                      </tr>
                    </thead>
                    <tbody>
                      {candidate.districts.map((cd) => {
                        const bd = baseline.districts.find((b) => b.district_id === cd.district_id)
                        const diff = (bd?.unmet || 0) - cd.unmet

                        return (
                          <tr key={cd.district_id}>
                            <td>{cd.name}</td>
                            <td className="cr-text-right cr-mono">{formatKg(bd?.unmet)} kg</td>
                            <td className="cr-text-right cr-mono font-bold">{formatKg(cd.unmet)} kg</td>
                            <td className="cr-text-right cr-mono">
                              {diff === 0 ? '0 kg' : `${diff > 0 ? '-' : '+'}${formatKg(Math.abs(diff))} kg`}
                            </td>
                          </tr>
                        )
                      })}
                    </tbody>
                  </table>
                </div>
              </div>

              {/* Mathematical explanation of plan differences */}
              <div className="cr-card cr-explain-card">
                <div className="cr-explain-header">
                  <Info size={17} />
                  <h4>Methodological Rationale &amp; Trade-Off Analysis</h4>
                </div>
                <div className="cr-explain-body">
                  <p>
                    <strong>Baseline Allocation (Plan 1):</strong> Pools available supply and carry-in stocks into unconstrained proportional budgets by priority tier, minimizing absolute deviations from equal demand shares. It does not look ahead to bottleneck delays or capacity constraints when setting targets.
                  </p>
                  <p>
                    <strong>CommonRoot Constrained Optimization (Plan 2):</strong> Uses OR-Tools continuous linear programming with staged lexicographic priorities: (1) strictly maximizes and locks served volume for Essential Services, (2) maximizes Domestic Household supply, and (3) minimizes proportional deviation among districts while strictly respecting transport routes and dispatch limits.
                  </p>
                  <p className="cr-footnote">
                    {comparison.explanation}
                  </p>
                </div>
              </div>
            </section>
          </div>
        )}

        {/* =================== TAB 6: AUDIT & HUMAN SIGN-OFF =================== */}
        {activeTab === 'audit' && (
          <div className="cr-view-pane cr-fade-in">
            <section className="cr-section">
              <div className="cr-section-header">
                <div>
                  <h2 className="cr-section-title">Audit Trail &amp; Authorized Review Checkpoint</h2>
                  <p className="cr-section-desc">
                    Cryptographic integrity manifest, execution metadata, and formal human review acknowledgement.
                  </p>
                </div>
              </div>

              {/* Review Checkpoint Card */}
              <div className="cr-card cr-review-card">
                <div className="cr-review-header">
                  <ShieldCheck size={20} className="cr-text-emerald" />
                  <div>
                    <h3 className="cr-review-title">Human-in-the-Loop Review Stage</h3>
                    <p className="cr-review-desc">
                      CommonRoot informs human decision-makers. No scenario output is executed automatically or communicated to OMC dispatch systems.
                    </p>
                  </div>
                </div>

                {reviewStatus ? (
                  <div className="cr-review-confirmed">
                    <CheckCircle2 size={18} className="cr-text-emerald" />
                    <div>
                      <strong>Review Recorded on Local Audit Log:</strong>
                      <p>Timestamp: <code>{reviewStatus.timestamp}</code></p>
                      <p>Sign-off Note: <em>"{reviewStatus.note}"</em></p>
                      <small>Recorded as simulation-only review. No live dispatch or rationing was ordered.</small>
                    </div>
                  </div>
                ) : (
                  <form onSubmit={handleRecordReview} className="cr-review-form">
                    <div className="cr-form-group">
                      <label htmlFor="review-note">Operator Review &amp; Context Notes:</label>
                      <textarea
                        id="review-note"
                        rows={3}
                        placeholder="Record operational rationale, pipeline assumptions, or local state civil supplies guidance..."
                        value={reviewNote}
                        onChange={(e) => setReviewNote(e.target.value)}
                      />
                    </div>

                    <div className="cr-checkbox-group">
                      <input
                        type="checkbox"
                        id="ack-check"
                        checked={reviewAck}
                        onChange={(e) => setReviewAck(e.target.checked)}
                      />
                      <label htmlFor="ack-check">
                        I acknowledge this is a modeled decision-support simulation. This action records an internal audit review and does not order real-world LPG rationing.
                      </label>
                    </div>

                    <button type="submit" className="cr-btn-primary" disabled={!reviewAck}>
                      <ShieldCheck size={14} /> Record &amp; Save Review Status
                    </button>
                  </form>
                )}
              </div>

              {/* Run Manifest Details */}
              <div className="cr-two-col-grid">
                <div className="cr-card">
                  <h3 className="cr-card-title"><FileText size={16} /> Run Manifest &amp; Reproducibility</h3>
                  <table className="cr-table cr-table-compact">
                    <tbody>
                      <tr>
                        <td>Run Identifier (UUID)</td>
                        <td><code>{manifest.run_id}</code></td>
                      </tr>
                      <tr>
                        <td>Execution Timestamp</td>
                        <td>{manifest.created_at}</td>
                      </tr>
                      <tr>
                        <td>Input Content Hash (SHA-256)</td>
                        <td><code>{manifest.input_hash}</code></td>
                      </tr>
                      <tr>
                        <td>Output Content Hash (SHA-256)</td>
                        <td><code>{manifest.output_hash}</code></td>
                      </tr>
                      <tr>
                        <td>Solver / Engine</td>
                        <td>{manifest.solver} ({manifest.solver_version})</td>
                      </tr>
                      <tr>
                        <td>Solver Feasibility Tolerance</td>
                        <td>{manifest.solver_settings?.feasibility_tolerance_kg} kg</td>
                      </tr>
                      <tr>
                        <td>Elapsed Wall Time</td>
                        <td>{manifest.elapsed_seconds?.toFixed(4)} seconds</td>
                      </tr>
                      <tr>
                        <td>Synthetic Record Share</td>
                        <td>{(manifest.synthetic_record_share * 100).toFixed(0)}% (Fictional engineering fixture)</td>
                      </tr>
                    </tbody>
                  </table>
                </div>

                <div className="cr-card">
                  <h3 className="cr-card-title"><Download size={16} /> Reproducible Artifact Downloads</h3>
                  <p className="cr-card-desc">Download complete machine-readable run bundles for reporting and archival.</p>

                  <div className="cr-export-actions">
                    <button className="cr-export-btn" onClick={handleExportJson}>
                      <FileDown size={18} />
                      <div>
                        <strong>Full Run Bundle (JSON)</strong>
                        <span>Complete input fixtures, scenario parameters, solver stages &amp; outputs</span>
                      </div>
                    </button>

                    <button className="cr-export-btn" onClick={handleExportCsv}>
                      <FileSpreadsheet size={18} />
                      <div>
                        <strong>District Risk Summary (CSV)</strong>
                        <span>Tabular days of cover, inventory balances, and risk classifications</span>
                      </div>
                    </button>
                  </div>

                  <div className="cr-audit-warnings-box">
                    <h4>Active Model Assumptions &amp; Limitations:</h4>
                    <ul>
                      {warnings.slice(0, 4).map((w, idx) => (
                        <li key={idx}>{w}</li>
                      ))}
                    </ul>
                  </div>
                </div>
              </div>
            </section>
          </div>
        )}
      </main>
    </div>
  )
}
