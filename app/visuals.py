"""Small, escaped report fragments and an input-coordinate supply schematic."""

from html import escape
from math import hypot, isfinite
from textwrap import wrap

from commonroot.schemas import NetworkData

PAPER = "#F5F6F2"
INK = "#172A35"
PETROL = "#164B50"
OCHRE = "#AD762C"
BURGUNDY = "#8A3F4C"
LAVENDER = "#77728D"


def safe(value: object) -> str:
    return escape(str(value), quote=True)


def number(value: float | None, decimals: int = 0) -> str:
    if value is None or not isfinite(value):
        return "Not computable"
    return f"{value:,.{decimals}f}"


def percent(value: float | None) -> str:
    return "Not computable" if value is None else f"{value:.1%}"


def day_label(day: int | None) -> str:
    return "None in horizon" if day is None else f"Day {day}"


def ledger(items: list[tuple[str, str, str]]) -> str:
    """Definition list, deliberately one report strip rather than metric cards."""
    cells = "".join(
        f'<div class="cr-ledger-item"><dt>{safe(label)}</dt>'
        f'<dd>{safe(value)}</dd><span>{safe(detail)}</span></div>'
        for label, value, detail in items
    )
    return f'<dl class="cr-ledger">{cells}</dl>'


def report_header(bundle) -> str:
    manifest = bundle.manifest
    share = manifest.get("synthetic_record_share")
    if share is None:
        provenance = "Record provenance in inputs"
    elif share == 1:
        provenance = "Synthetic data · all records"
    else:
        provenance = f"Mixed inputs · {share:.0%} synthetic records"
    return (
        '<header class="cr-report-header">'
        '<div class="cr-report-top"><span class="cr-eyebrow">COMMONROOT / LOCAL WORKBENCH</span>'
        f'<span class="cr-badge">{safe(provenance)}</span></div>'
        '<h1>Supply planning desk</h1>'
        f'<h2 class="cr-scenario-title">{safe(bundle.scenario.name)}</h2>'
        '<p class="cr-run-meta">Displayed run '
        f'<code>{safe(manifest.get("run_id", "Unavailable"))}</code>'
        f' · Days 1–{safe(bundle.scenario.horizon_days)}'
        f' · {safe(manifest.get("timezone", bundle.network.timezone))}</p>'
        f'<p class="cr-run-meta">Created {safe(manifest.get("created_at", "Unavailable"))}'
        f' · Seed {safe(manifest.get("seed", bundle.network.seed))}'
        f' · {safe(bundle.review.status.replace("_", " "))}</p>'
        '</header>'
    )


def network_svg(
    network: NetworkData,
    affected_nodes: list[str],
    affected_edges: list[str],
    selected: str | None = None,
    *,
    id_prefix: str = "cr-network",
) -> str:
    """Draw only supplied nodes/routes; x/y are diagram coordinates, not geography.

    Quantities are intentionally not encoded in line width: dependency exposure is
    not a shipment assignment. Every user-controlled text fragment is escaped.
    """
    width, height = 1180, 565
    prefix = safe(id_prefix)
    nodes = {node.id: node for node in network.nodes}
    if not nodes:
        return '<p class="cr-empty">No network nodes to draw.</p>'
    xs = [node.x for node in nodes.values()]
    ys = [node.y for node in nodes.values()]
    if not all(isfinite(value) for value in xs + ys):
        return '<p class="cr-empty">Diagram coordinates are not finite.</p>'
    # Scale before subtraction so large but finite uploaded coordinates cannot
    # overflow a viewBox calculation into infinity or NaN.
    xscale, yscale = max(1.0, max(map(abs, xs))), max(1.0, max(map(abs, ys)))
    xs, ys = [x / xscale for x in xs], [y / yscale for y in ys]
    xmin, xmax, ymin, ymax = min(xs), max(xs), min(ys), max(ys)
    xspan, yspan = xmax - xmin, ymax - ymin
    positions = {
        node.id: (
            95 + (node.x / xscale - xmin) / xspan * 900 if xspan else width / 2,
            80 + (node.y / yscale - ymin) / yspan * 390 if yspan else height / 2,
        )
        for node in nodes.values()
    }
    exposed_nodes, exposed_edges = set(affected_nodes), set(affected_edges)
    parts = [
        '<div class="cr-schematic-scroll" tabindex="0" '
        'aria-label="Supply schematic; scroll horizontally on small screens">',
        f'<svg class="cr-schematic" viewBox="0 0 {width} {height}" '
        'xmlns="http://www.w3.org/2000/svg" role="img" '
        f'aria-labelledby="{prefix}-title {prefix}-description">',
        f'<title id="{prefix}-title">Supply network schematic</title>',
        f'<desc id="{prefix}-description">Directed routes drawn using the network input '
        'coordinates. Ochre routes indicate possible downstream exposure, burgundy marks '
        'the selected asset, and dashed lavender routes are originally inactive. '
        'This is a topology diagram, not geography or actual cargo flow.</desc>',
        '<defs>',
    ]
    for key, color in (("regular", PETROL), ("exposed", OCHRE), ("inactive", LAVENDER),
                       ("selected", BURGUNDY)):
        parts.append(
            f'<marker id="{prefix}-arrow-{key}" markerWidth="8" markerHeight="8" '
            'refX="6" refY="3" orient="auto" markerUnits="userSpaceOnUse">'
            f'<path d="M 0 0 L 6 3 L 0 6" fill="none" stroke="{color}" '
            'stroke-width="1.3"/></marker>'
        )
    parts.extend([
        '</defs>',
        f'<rect width="{width}" height="{height}" rx="4" fill="{PAPER}"/>',
        f'<text x="24" y="28" fill="{PETROL}" font-size="11" letter-spacing="1.7">'
        'SUPPLY / HANDLING / DISTRICT SERVICE</text>',
    ])
    # Routes sit behind the nodes, with clear arrow endpoints.
    for edge in network.edges:
        if edge.source not in positions or edge.target not in positions:
            continue
        x1, y1 = positions[edge.source]
        x2, y2 = positions[edge.target]
        distance = hypot(x2 - x1, y2 - y1)
        dx, dy = ((x2 - x1) / distance, (y2 - y1) / distance) if distance else (0, 0)
        active = edge.active and nodes[edge.source].active and nodes[edge.target].active
        kind = "exposed" if edge.id in exposed_edges else "regular"
        if not active:
            kind = "inactive"
        if selected == f"edge:{edge.id}":
            kind = "selected"
        color = {"regular": PETROL, "exposed": OCHRE,
                 "inactive": LAVENDER, "selected": BURGUNDY}[kind]
        dash = ' stroke-dasharray="5 5"' if not active else ""
        thickness = "2.8" if kind == "selected" else "1.6"
        title = (
            f"{edge.id}: {nodes[edge.source].name} → {nodes[edge.target].name}; "
            f"nominal capacity {number(edge.capacity)} kg_LPG/day; "
            f"nominal lead {edge.lead_days} days; "
            f"{'originally active' if active else 'originally inactive'}"
        )
        parts.append(
            f'<g><title>{safe(title)}</title><path '
            f'd="M {x1 + dx * 12:.2f} {y1 + dy * 12:.2f} '
            f'L {x2 - dx * 16:.2f} {y2 - dy * 16:.2f}" '
            f'stroke="{color}" stroke-width="{thickness}" fill="none"{dash} '
            f'marker-end="url(#{prefix}-arrow-{kind})"/></g>'
        )
    for node in network.nodes:
        x, y = positions[node.id]
        selected_node = selected == f"node:{node.id}"
        color = BURGUNDY if selected_node else OCHRE if node.id in exposed_nodes else PETROL
        if not node.active and not selected_node:
            color = LAVENDER
        title = f"{node.name} ({node.id}) · {node.kind} · {'active' if node.active else 'inactive'}"
        parts.append(f'<g><title>{safe(title)}</title>')
        if selected_node:
            parts.append(
                f'<circle cx="{x:.2f}" cy="{y:.2f}" r="17" '
                f'fill="none" stroke="{BURGUNDY}" stroke-width="1"/>'
            )
        if node.kind == "district":
            parts.append(f'<circle cx="{x:.2f}" cy="{y:.2f}" r="7" fill="{color}"/>')
        else:
            parts.append(
                f'<rect x="{x - 8:.2f}" y="{y - 8:.2f}" width="16" height="16" '
                f'rx="{8 if node.kind in {"import", "refinery"} else 2}" '
                f'fill="{PAPER}" stroke="{color}" stroke-width="2.4"/>'
            )
        label_x = x + 18 if node.kind == "district" else x
        label_y = y + 4 if node.kind == "district" else y + 28
        anchor = "start" if node.kind == "district" else "middle"
        # Keep a complete accessible title even when a long imported name wraps.
        lines = wrap(node.name, width=21, break_long_words=True) or [node.id]
        for i, line in enumerate(lines[:3]):
            parts.append(
                f'<text x="{label_x:.2f}" y="{label_y + i * 16:.2f}" '
                f'text-anchor="{anchor}" fill="{INK}" font-size="13">{safe(line)}</text>'
            )
        parts.append('</g>')
    parts.extend(['</svg></div>',
        '<div class="cr-legend">'
        '<span><i class="cr-key cr-key-regular"></i>Originally active route</span>'
        '<span><i class="cr-key cr-key-exposed"></i>Exposed dependency</span>'
        '<span><i class="cr-key cr-key-inactive"></i>Originally inactive</span>'
        '<span><i class="cr-key cr-key-selected"></i>Selected asset</span></div>'])
    return "".join(parts)
