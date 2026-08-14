from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import cm
from reportlab.lib import colors
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle,
    PageBreak, HRFlowable, KeepTogether
)
from reportlab.lib.enums import TA_LEFT, TA_CENTER, TA_JUSTIFY
from reportlab.platypus import Flowable
from pathlib import Path

WIDTH, HEIGHT = A4
MARGIN = 2.2 * cm

# ── Colour palette ──────────────────────────────────────────────────────────
C_RED      = colors.HexColor("#E8002D")   # F1 red
C_DARK     = colors.HexColor("#0a0a0a")
C_GREY     = colors.HexColor("#1e1e1e")
C_MID      = colors.HexColor("#2d2d2d")
C_LIGHT    = colors.HexColor("#f5f5f5")
C_ACCENT   = colors.HexColor("#ff6b35")
C_WHITE    = colors.white
C_BORDER   = colors.HexColor("#444444")
C_WARN     = colors.HexColor("#c0392b")
C_OK       = colors.HexColor("#27ae60")
C_INFO     = colors.HexColor("#2980b9")

def make_styles():
    base = getSampleStyleSheet()

    styles = {}

    styles['cover_title'] = ParagraphStyle(
        'cover_title', fontSize=28, textColor=C_WHITE,
        fontName='Helvetica-Bold', alignment=TA_CENTER,
        leading=34, spaceAfter=6
    )
    styles['cover_sub'] = ParagraphStyle(
        'cover_sub', fontSize=13, textColor=C_RED,
        fontName='Helvetica-Bold', alignment=TA_CENTER,
        leading=18, spaceAfter=4
    )
    styles['cover_meta'] = ParagraphStyle(
        'cover_meta', fontSize=9, textColor=colors.HexColor("#aaaaaa"),
        fontName='Helvetica', alignment=TA_CENTER, leading=14
    )
    styles['h1'] = ParagraphStyle(
        'h1', fontSize=18, textColor=C_RED,
        fontName='Helvetica-Bold', spaceBefore=18, spaceAfter=8,
        leading=22, borderPad=0
    )
    styles['h2'] = ParagraphStyle(
        'h2', fontSize=13, textColor=C_WHITE,
        fontName='Helvetica-Bold', spaceBefore=14, spaceAfter=6,
        leading=17, backColor=C_MID, borderPad=5,
        leftIndent=0, rightIndent=0
    )
    styles['h3'] = ParagraphStyle(
        'h3', fontSize=11, textColor=C_ACCENT,
        fontName='Helvetica-Bold', spaceBefore=10, spaceAfter=4,
        leading=15
    )
    styles['body'] = ParagraphStyle(
        'body', fontSize=9, textColor=colors.HexColor("#dddddd"),
        fontName='Helvetica', leading=14, spaceAfter=5,
        alignment=TA_JUSTIFY
    )
    styles['bullet'] = ParagraphStyle(
        'bullet', fontSize=9, textColor=colors.HexColor("#cccccc"),
        fontName='Helvetica', leading=13, spaceAfter=3,
        leftIndent=14, bulletIndent=4
    )
    styles['math'] = ParagraphStyle(
        'math', fontSize=9, textColor=colors.HexColor("#ffe082"),
        fontName='Helvetica-Oblique', leading=14, spaceAfter=4,
        leftIndent=20, backColor=colors.HexColor("#1a1a2e"),
        borderPad=5
    )
    styles['code'] = ParagraphStyle(
        'code', fontSize=8, textColor=colors.HexColor("#a8ff78"),
        fontName='Courier', leading=12, spaceAfter=4,
        leftIndent=16, backColor=colors.HexColor("#111111"),
        borderPad=5
    )
    styles['assumption'] = ParagraphStyle(
        'assumption', fontSize=8.5, textColor=colors.HexColor("#f39c12"),
        fontName='Helvetica-Oblique', leading=13, spaceAfter=3,
        leftIndent=14
    )
    styles['toc_entry'] = ParagraphStyle(
        'toc_entry', fontSize=10, textColor=colors.HexColor("#cccccc"),
        fontName='Helvetica', leading=16, leftIndent=0
    )
    styles['toc_sub'] = ParagraphStyle(
        'toc_sub', fontSize=9, textColor=colors.HexColor("#999999"),
        fontName='Helvetica', leading=14, leftIndent=20
    )
    styles['label_red'] = ParagraphStyle(
        'label_red', fontSize=8, textColor=C_WHITE,
        fontName='Helvetica-Bold', alignment=TA_CENTER
    )
    styles['small'] = ParagraphStyle(
        'small', fontSize=7.5, textColor=colors.HexColor("#999999"),
        fontName='Helvetica-Oblique', leading=11, spaceAfter=2
    )
    return styles

S = make_styles()

# ── Reusable helpers ─────────────────────────────────────────────────────────

def sp(n=1):
    return Spacer(1, n * 0.35 * cm)

def hr(color=C_RED, thickness=1):
    return HRFlowable(width="100%", thickness=thickness, color=color, spaceAfter=6, spaceBefore=6)

def h1(text):
    return Paragraph(text, S['h1'])

def h2(text):
    return Paragraph(f"&nbsp;&nbsp;{text}", S['h2'])

def h3(text):
    return Paragraph(text, S['h3'])

def body(text):
    return Paragraph(text, S['body'])

def bullet(text):
    return Paragraph(f"• &nbsp;{text}", S['bullet'])

def math(text):
    return Paragraph(text, S['math'])

def assumption(text):
    return Paragraph(f"⚠ &nbsp;{text}", S['assumption'])

def section_break():
    return PageBreak()

def badge_table(items, colors_list):
    data = [[Paragraph(t, S['label_red']) for t in items]]
    col_colors = colors_list
    style = [
        ('BACKGROUND', (i, 0), (i, 0), col_colors[i]) for i in range(len(items))
    ] + [
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('ROWBACKGROUNDS', (0, 0), (-1, -1), [None]),
        ('TOPPADDING', (0, 0), (-1, -1), 5),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 5),
        ('LEFTPADDING', (0, 0), (-1, -1), 8),
        ('RIGHTPADDING', (0, 0), (-1, -1), 8),
        ('ROUNDEDCORNERS', (0, 0), (-1, -1), 3),
    ]
    t = Table(data, colWidths=[3.5*cm]*len(items))
    t.setStyle(TableStyle(style))
    return t

def make_table(headers, rows, col_widths=None):
    header_row = [Paragraph(f"<b>{h}</b>", ParagraphStyle(
        'th', fontSize=8, textColor=C_WHITE, fontName='Helvetica-Bold',
        alignment=TA_CENTER, leading=11
    )) for h in headers]

    body_rows = []
    for row in rows:
        body_rows.append([
            Paragraph(str(cell), ParagraphStyle(
                'td', fontSize=8, textColor=colors.HexColor("#cccccc"),
                fontName='Helvetica', leading=11, alignment=TA_CENTER
            )) for cell in row
        ])

    data = [header_row] + body_rows
    n_cols = len(headers)
    if col_widths is None:
        avail = WIDTH - 2 * MARGIN
        col_widths = [avail / n_cols] * n_cols

    style = TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), C_RED),
        ('ROWBACKGROUNDS', (0, 1), (-1, -1), [C_MID, C_GREY]),
        ('GRID', (0, 0), (-1, -1), 0.4, C_BORDER),
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('TOPPADDING', (0, 0), (-1, -1), 5),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 5),
        ('LEFTPADDING', (0, 0), (-1, -1), 6),
        ('RIGHTPADDING', (0, 0), (-1, -1), 6),
    ])
    t = Table(data, colWidths=col_widths)
    t.setStyle(style)
    return t

# ── Page template ─────────────────────────────────────────────────────────────

def on_page(canvas, doc):
    canvas.saveState()
    # dark background
    canvas.setFillColor(C_DARK)
    canvas.rect(0, 0, WIDTH, HEIGHT, fill=1, stroke=0)
    # top bar
    canvas.setFillColor(C_RED)
    canvas.rect(0, HEIGHT - 0.55*cm, WIDTH, 0.55*cm, fill=1, stroke=0)
    # bottom bar
    canvas.setFillColor(C_GREY)
    canvas.rect(0, 0, WIDTH, 0.7*cm, fill=1, stroke=0)
    # page number
    canvas.setFillColor(colors.HexColor("#aaaaaa"))
    canvas.setFont("Helvetica", 7)
    canvas.drawCentredString(WIDTH/2, 0.22*cm, f"F1 Physics-Based Predictive Pipeline  |  Page {doc.page}")
    canvas.restoreState()

def on_first_page(canvas, doc):
    canvas.saveState()
    canvas.setFillColor(C_DARK)
    canvas.rect(0, 0, WIDTH, HEIGHT, fill=1, stroke=0)
    canvas.restoreState()

# ── Content builders ──────────────────────────────────────────────────────────

def build_cover():
    elems = []
    elems.append(Spacer(1, 3.5*cm))

    # Red accent bar
    elems.append(HRFlowable(width="60%", thickness=3, color=C_RED,
                             spaceAfter=20, spaceBefore=0, hAlign='CENTER'))

    elems.append(Paragraph("F1 PHYSICS-BASED", S['cover_title']))
    elems.append(Paragraph("PREDICTIVE PIPELINE", S['cover_title']))
    elems.append(sp(0.5))
    elems.append(Paragraph("Complete Technical Reference", S['cover_sub']))
    elems.append(sp(0.3))
    elems.append(HRFlowable(width="60%", thickness=3, color=C_RED,
                             spaceAfter=20, spaceBefore=10, hAlign='CENTER'))
    elems.append(sp(2))

    # Pipeline flow visual as table
    pipeline = [["Layer 1", "Layer 2", "Layer 3", "Layer 4", "Layer 5"]]
    labels =   [["Aero", "Alignment", "Racing Line", "Tyre Model", "Strategy"]]
    t = Table(pipeline + labels, colWidths=[3.2*cm]*5)
    t.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,0), C_RED),
        ('BACKGROUND', (0,1), (-1,1), C_MID),
        ('TEXTCOLOR', (0,0), (-1,-1), C_WHITE),
        ('FONTNAME', (0,0), (-1,0), 'Helvetica-Bold'),
        ('FONTNAME', (0,1), (-1,1), 'Helvetica'),
        ('FONTSIZE', (0,0), (-1,0), 9),
        ('FONTSIZE', (0,1), (-1,1), 8),
        ('ALIGN', (0,0), (-1,-1), 'CENTER'),
        ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
        ('TOPPADDING', (0,0), (-1,-1), 7),
        ('BOTTOMPADDING', (0,0), (-1,-1), 7),
        ('GRID', (0,0), (-1,-1), 0.5, C_BORDER),
    ]))
    elems.append(t)
    elems.append(sp(2))

    elems.append(Paragraph(
        "Telemetry  →  Aero  →  Aligned Data  →  Racing Line  →  Tyre Degradation  →  Race Strategy",
        ParagraphStyle('flow', fontSize=9, textColor=C_ACCENT,
                       fontName='Helvetica-Oblique', alignment=TA_CENTER, leading=14)
    ))
    elems.append(sp(2.5))

    meta = [
        "Data Sources: FastF1 · OpenF1 API · Ergast API · OpenStreetMap",
        "Primary Library: FastF1 (Python)  |  2018–2024 seasons",
        "Output: Probabilistic pit strategy · Compound choice · Undercut/Overcut viability · Risk-ranked recommendations",
    ]
    for m in meta:
        elems.append(Paragraph(m, S['cover_meta']))
        elems.append(sp(0.2))

    elems.append(PageBreak())
    return elems


def build_toc():
    elems = []
    elems.append(h1("Table of Contents"))
    elems.append(hr())
    elems.append(sp())

    toc = [
        ("1.", "Project Overview & Core Pipeline"),
        ("2.", "Data Sources & Global Limitations"),
        ("3.", "Uncertainty Propagation Framework"),
        ("4.", "Layer 1 — Aero Parameter Estimation"),
        ("5.", "Layer 2 — Telemetry Alignment"),
        ("6.", "Layer 3 — Optimum Racing Line Engine"),
        ("7.", "Layer 4 — Tyre Thermodynamics & Wear"),
        ("8.", "Layer 5 — Monte Carlo Strategy Engine"),
        ("9.", "Validation Strategy"),
        ("10.", "Documented Assumptions Master List"),
    ]
    subs = {
        "4.": ["Sequential Cd/Cl estimation", "DRS natural experiment", "Track-type routing"],
        "5.": ["Distance drift correction", "Event-segmented DTW", "Dead reckoning upsample", "Weather GP"],
        "6.": ["B-spline curvature", "Point-mass vehicle model", "CVXPY speed profile"],
        "7.": ["Energy dissipation proxy", "Hierarchical Bayesian degradation", "Cliff survival model", "Warm-up model"],
        "8.": ["Joint uncertainty sampling", "SC Poisson process", "Nash equilibrium undercut", "Receding horizon DP"],
    }

    for num, title in toc:
        elems.append(Paragraph(f"<b>{num}</b>  {title}", S['toc_entry']))
        if num in subs:
            for sub in subs[num]:
                elems.append(Paragraph(f"·  {sub}", S['toc_sub']))
        elems.append(sp(0.3))

    elems.append(PageBreak())
    return elems


def build_overview():
    elems = []
    elems.append(h1("1. Project Overview & Core Pipeline"))
    elems.append(hr())
    elems.append(sp(0.5))

    elems.append(body(
        "This project transforms publicly available Formula 1 telemetry and timing data into a "
        "physics-based predictive system. The pipeline is strictly layered — each layer's output "
        "feeds the next as a distribution, not a point estimate, so uncertainty accumulates "
        "honestly rather than being hidden. The final output is a probabilistic race strategy "
        "recommendation with risk ranking."
    ))
    elems.append(sp())

    elems.append(h2("Pipeline Dependency Graph"))
    elems.append(sp(0.5))

    rows = [
        ["L1 → L3", "Cd, Cl posteriors feed speed profile aero-corrected normal force"],
        ["L2 → L3", "Aligned distance-grid telemetry feeds curvature and speed profile"],
        ["L3 → L4", "Racing line curvature and speed profile feed lateral/braking energy"],
        ["L3 ↔ L4", "Circular dependency — resolved by iterative refinement (3–5 passes)"],
        ["L4 → L5", "Degradation posteriors, cliff survival probabilities, warm-up curves"],
        ["L1→5", "All posterior distributions jointly sampled per Monte Carlo scenario"],
    ]
    elems.append(make_table(
        ["Dependency", "Data Passed"],
        rows,
        col_widths=[5*cm, 11.5*cm]
    ))
    elems.append(sp())

    elems.append(h2("Final Outputs"))
    outputs = [
        "Optimal compound sequence and pit lap recommendations",
        "Expected race time distribution across 10,000 simulated scenarios",
        "CVaR-adjusted risk ranking of all viable strategies",
        "Undercut viability: P(undercut viable) and minimum gap threshold g*",
        "Overcut viability updated every 5 laps",
        "Tyre cliff warning: P(cliff within k laps)",
        "SC-robust strategy flags",
        "No-SC vs SC scenario branch comparison",
    ]
    for o in outputs:
        elems.append(bullet(o))

    elems.append(PageBreak())
    return elems


def build_data_sources():
    elems = []
    elems.append(h1("2. Data Sources & Global Limitations"))
    elems.append(hr())
    elems.append(sp(0.5))

    elems.append(h2("Data Sources"))
    rows = [
        ["FastF1", "2018–present", "Telemetry, lap timing, weather, stint data, track status"],
        ["OpenF1 API", "2023–present", "Enhanced real-time session data, stint granularity"],
        ["Ergast API", "2003–present", "Historical lap times, pit stops, results, compounds"],
        ["OpenStreetMap", "Current", "Circuit geometry, track boundaries, corner radii"],
        ["F1 Official Site", "Current", "Official circuit lengths, DRS zone locations"],
    ]
    elems.append(make_table(
        ["Source", "Coverage", "Used For"],
        rows,
        col_widths=[3.5*cm, 3*cm, 10*cm]
    ))
    elems.append(sp())

    elems.append(h2("What FastF1 Does NOT Provide"))
    missing = [
        "Tyre surface or carcass temperature (per tyre)",
        "Tyre pressure (per tyre)",
        "Ride height (front or rear)",
        "Real fuel load per lap (modelled as linear depletion)",
        "Brake pressure magnitude (binary on/off only)",
        "Per-tyre load distribution",
        "Camber and toe angles",
        "Aerodynamic balance (front/rear downforce split)",
        "Engine power curve (approximated from RPM + gear)",
    ]
    for m in missing:
        elems.append(bullet(m))

    elems.append(sp())
    elems.append(h2("Telemetry Channel Reference"))
    rows = [
        ["Speed", "~240 Hz", "Savitzky-Golay filtered", "All layers"],
        ["Throttle %", "~240 Hz", "Raw", "L2, L4"],
        ["Brake (bool)", "~240 Hz", "Nearest-neighbour only", "L2, L4"],
        ["DRS (bool)", "~240 Hz", "Nearest-neighbour only", "L1, L2"],
        ["RPM / Gear", "~240 Hz", "Linear interp", "L1"],
        ["X, Y, Z (GPS)", "~4 Hz", "Dead reckoning upsample", "L2, L3"],
        ["Weather", "~1/min", "Hold-last + GP uncertainty", "L1, L4"],
    ]
    elems.append(make_table(
        ["Channel", "Native Rate", "Handling", "Used In"],
        rows,
        col_widths=[3*cm, 2.5*cm, 5*cm, 6*cm]
    ))

    elems.append(PageBreak())
    return elems


def build_uncertainty():
    elems = []
    elems.append(h1("3. Uncertainty Propagation Framework"))
    elems.append(hr())
    elems.append(sp(0.5))

    elems.append(body(
        "Every layer produces distributions, not point estimates. These distributions are sampled "
        "jointly at the start of each Monte Carlo scenario in Layer 5, preserving correlation "
        "structure across the full pipeline. Sensitivity analysis identifies which upstream "
        "uncertainties dominate the final strategy recommendation."
    ))
    elems.append(sp())

    elems.append(h2("Uncertainty Budget by Layer"))
    rows = [
        ["L1 — Aero", "Cd ± 15–20%, Cl ± 20–25%", "Gaussian posteriors from energy method"],
        ["L2 — Alignment", "Segment quality flags", "Consistency check pass/fail per segment"],
        ["L3 — Racing Line", "Speed profile GP residual", "Fitted to qualifying telemetry residuals"],
        ["L4 — Tyre", "Degradation curve posterior", "MCMC posterior from hierarchical model"],
        ["L4 — Tyre", "Cliff timing Weibull", "Survival model P(cliff within k laps)"],
        ["L5 — Strategy", "Pit stop time distribution", "Per-team empirical + heavy tail"],
        ["L5 — Strategy", "SC occurrence Poisson", "Non-homogeneous, circuit specific"],
    ]
    elems.append(make_table(
        ["Layer", "Uncertainty", "Source"],
        rows,
        col_widths=[3.5*cm, 6*cm, 7*cm]
    ))
    elems.append(sp())

    elems.append(h2("Propagation Method"))
    elems.append(body(
        "At each of 10,000 Monte Carlo scenarios, one sample is drawn from every upstream "
        "posterior and held fixed for the entire race simulation. This means each scenario "
        "represents a self-consistent draw from the full joint uncertainty of the pipeline. "
        "Strategy rankings are stable when checked between 5,000 and 10,000 scenarios."
    ))
    elems.append(math("Score_s = w1 * T_s_mean + w2 * CVaR_0.8(T_s)   [w1=0.7, w2=0.3]"))

    elems.append(PageBreak())
    return elems


def build_layer1():
    elems = []
    elems.append(h1("4. Layer 1 — Aero Parameter Estimation"))
    elems.append(hr())
    elems.append(sp(0.5))

    elems.append(body(
        "Estimates circuit-specific aerodynamic drag (Cd) and lift (Cl) coefficients as posterior "
        "distributions using a sequential, track-aware pipeline. Energy methods replace "
        "instantaneous force methods to avoid noise amplification from acceleration signals. "
        "DRS acts as a natural experiment providing an independent Cd calibration check."
    ))
    elems.append(sp())

    elems.append(h2("Step 1 — Preprocessing"))
    steps = [
        "Compute air density: rho = P / (Rd * T), Rd = 287.05 J/kg·K",
        "Apply Savitzky-Golay filter to speed channel (window tuned per circuit)",
        "Compute road gradient theta from Z channel differentiated over distance",
        "Flag DRS transitions — exclude 0.3s buffer around open/close events",
        "Exclude SC, VSC, red flag, pit-in/out laps via FastF1 track status channel",
        "Correct distance channel drift using official F1 circuit length as anchor",
    ]
    for s in steps:
        elems.append(bullet(s))
    elems.append(sp())

    elems.append(h2("Step 2 — Cd Estimation (Energy Method)"))
    elems.append(body("On DRS-closed full-throttle straights, energy balance over entry/exit speeds:"))
    elems.append(math("(1/2)*m*(v2^2 - v1^2) = W_engine - Cd*(1/2)*rho*A*integral(v^2 ds) - Frr*ds - mg*dh"))
    params = [
        "m = car mass ~798 kg (fuel-corrected: 1.8 kg/lap burn)",
        "A = reference area fixed at 1.5 m^2",
        "W_engine approximated from RPM + gear (bounded ±8% uncertainty)",
        "Frr = rolling resistance prior ~500–600 N (±15%)",
        "dh = elevation change from Z channel",
    ]
    for p in params:
        elems.append(bullet(p))
    elems.append(body("Aggregate Cd estimates across multiple straights and laps → fit Gaussian: Cd ~ N(mu_Cd, sigma_Cd)"))
    elems.append(sp())

    elems.append(h2("Step 3 — DRS Calibration Check"))
    elems.append(body(
        "Compare DRS-open vs DRS-closed acceleration profiles on the same straight across laps. "
        "Expected delta: delta_Cd = 0.08–0.12 from published literature. If energy-method "
        "estimate falls outside this range, sigma_Cd is widened accordingly."
    ))
    elems.append(math("delta_Cd = Cd_closed - Cd_open ≈ 0.08–0.12"))
    elems.append(sp())

    elems.append(h2("Step 4 — Cl Estimation (Sequential, Cd Fixed)"))
    elems.append(body("In high-speed corners with constant speed (speed variance < 2 km/h):"))
    elems.append(math("Cl = 2*(m*v^2/r - F_mechanical) / (rho*A*v^2)"))
    elems.append(body(
        "Mechanical grip component F_mechanical calibrated from slow corners (v < 80 km/h) "
        "where aero contribution is negligible. Aggregate across corners → Cl ~ N(mu_Cl, sigma_Cl)."
    ))
    elems.append(sp())

    elems.append(h2("Step 5 — Track-Type Routing"))
    rows = [
        ["Low drag (Monza, Montreal)", "Energy method — excellent signal", "Limited high-speed corners", "Best Cd calibration"],
        ["High speed (Spa, Silverstone)", "Energy method — good", "High-speed corners — good", "Best for both"],
        ["Street (Monaco, Baku)", "Poor — use Spa/Silverstone prior", "Slow corners only — poor", "Hold params, widen sigma x1.5"],
        ["Mixed (Bahrain, Abu Dhabi)", "Moderate signal", "Moderate signal", "Estimate fresh, wider CI"],
    ]
    elems.append(make_table(
        ["Circuit Class", "Cd Source", "Cl Source", "Notes"],
        rows,
        col_widths=[4*cm, 4*cm, 4*cm, 4.5*cm]
    ))
    elems.append(sp())

    elems.append(h2("Layer 1 Output"))
    elems.append(math("Cd ~ N(mu_Cd, sigma_Cd)     Cl ~ N(mu_Cl, sigma_Cl)"))
    elems.append(body("Distributions (not point estimates) passed forward to Layers 3 and 5."))

    elems.append(sp())
    elems.append(h3("Documented Assumptions"))
    assumptions = [
        "Car mass known within ±2 kg (linear fuel model, 1.8 kg/lap)",
        "Reference area fixed at 1.5 m^2 (published F1 approximation)",
        "Engine power approximated from RPM/gear (±8% bounded uncertainty)",
        "Rolling resistance treated as prior (±15%)",
        "DRS delta_Cd literature range used as calibration bound, not hard constraint",
    ]
    for a in assumptions:
        elems.append(assumption(a))

    elems.append(PageBreak())
    return elems


def build_layer2():
    elems = []
    elems.append(h1("5. Layer 2 — Telemetry Alignment"))
    elems.append(hr())
    elems.append(sp(0.5))

    elems.append(body(
        "Aligns multi-driver, multi-session telemetry onto a clean consistent distance-based "
        "spatial grid using physics-constrained DTW on event-segmented signals, with drift-corrected "
        "distance reference and channel-aware interpolation."
    ))
    elems.append(sp())

    elems.append(h2("Step 1 — Distance Channel Drift Correction"))
    elems.append(math("drift = d_raw(t_end) - L_official"))
    elems.append(math("d_corrected(t) = d_raw(t) - (t / T_lap) * drift"))
    elems.append(body(
        "Official circuit length L_official used as anchor. Laps deviating >15m from L_official "
        "are flagged as corrupted (SC, pit, track limits) and excluded."
    ))
    elems.append(sp())

    elems.append(h2("Step 2 — Lap Boundary Cleaning"))
    excluded = [
        "In-laps and out-laps (pit entry/exit)",
        "SC, VSC, red flag laps (FastF1 track status channel)",
        "Race lap 1 (standing start anomaly)",
        "Qualifying out-laps and cool-down laps",
    ]
    for e in excluded:
        elems.append(bullet(e))
    elems.append(body("Official sector timestamps used as anchor points on the distance grid."))
    elems.append(sp())

    elems.append(h2("Step 3 — GPS Upsampling via Dead Reckoning"))
    elems.append(body("Upsample 4Hz GPS to ~240Hz between consecutive fixes:"))
    elems.append(math("x(t+n*dt) = x(t) + sum_i [ v(t+i*dt) * cos(psi) * dt ]"))
    elems.append(math("y(t+n*dt) = y(t) + sum_i [ v(t+i*dt) * sin(psi) * dt ]"))
    elems.append(body(
        "Position resets to true GPS fix at each new observation. Maximum positional error "
        "within a single 250ms GPS interval at 300 km/h: ~0.35m."
    ))
    elems.append(sp())

    elems.append(h2("Step 4 — Event Segmentation"))
    rows = [
        ["Braking zone", "Brake=TRUE, speed decreasing", "Align on deceleration profile"],
        ["Corner apex", "Speed local minimum ±5 km/h", "Align on speed minimum position"],
        ["Full throttle", "Throttle >95%, brake=FALSE", "Align on acceleration profile"],
        ["Transition", "Everything else", "Linear interpolation, no DTW"],
    ]
    elems.append(make_table(
        ["Segment Type", "Detection Rule", "DTW Behaviour"],
        rows,
        col_widths=[3.5*cm, 6*cm, 7*cm]
    ))
    elems.append(sp())

    elems.append(h2("Step 5 — Physics-Constrained DTW"))
    elems.append(h3("Constraint 1 — Cross-validated window"))
    elems.append(math("w* = argmin_w (1/N) * sum_i |t_sector_aligned - t_sector_official|"))
    elems.append(body("Window size minimising sector time recovery error across 10+ laps per circuit."))
    elems.append(h3("Constraint 2 — Physics upper bound guard"))
    elems.append(math("w_max = 2.0 * v_segment_mean     [2s maximum inter-driver offset]"))
    elems.append(math("w = min(w*, w_max)"))
    elems.append(body("If w* > w_max, segment flagged as genuine driving difference — not force-aligned."))
    elems.append(sp())

    elems.append(h2("Step 6 — Multi-Driver Consistency Check"))
    elems.append(math("epsilon_ABC = || align(A->C) - align(A->B) o align(B->C) ||"))
    elems.append(body("Threshold ~0.5m. Failures logged — not silently passed to Layer 3."))
    elems.append(sp())

    elems.append(h2("Step 7 — Channel-Specific Interpolation (1m distance grid)"))
    rows = [
        ["Speed, X, Y, Z", "PCHIP", "Smooth first derivative, no oscillations"],
        ["Throttle %", "PCHIP", "Continuous signal"],
        ["RPM", "Linear", "High native rate, linear sufficient"],
        ["Brake (bool)", "Nearest neighbour", "Never interpolate a boolean"],
        ["DRS (bool)", "Nearest neighbour", "Never interpolate a boolean"],
        ["Gear", "Nearest neighbour", "Discrete signal"],
    ]
    elems.append(make_table(
        ["Channel", "Method", "Reason"],
        rows,
        col_widths=[4*cm, 3.5*cm, 9*cm]
    ))
    elems.append(sp())

    elems.append(h2("Step 8 — Weather Channel"))
    elems.append(body(
        "Primary: hold-last-known-value per lap (physically defensible — weather does not un-happen). "
        "Uncertainty: Gaussian Process with squared exponential kernel fitted to session observations."
    ))
    elems.append(math("k(t,t') = sigma_f^2 * exp(-(t-t')^2 / (2*l^2))"))
    elems.append(body("Length scales: l = 5min (track temp), l = 15min (air temp). GP posterior uncertainty propagated to Layer 1 air density and Layer 4 tyre baseline."))

    elems.append(sp())
    elems.append(h3("Documented Assumptions"))
    assumptions = [
        "Official circuit length accurate to ±1m",
        "Maximum inter-driver timing offset bounded at 2.0s for window guard",
        "Dead reckoning positional error bounded at ~0.35m per GPS interval at max speed",
        "Weather GP length scales: 5min track temp, 15min air temp",
        "1m distance grid sufficient for Layer 3 curvature resolution",
    ]
    for a in assumptions:
        elems.append(assumption(a))

    elems.append(PageBreak())
    return elems


def build_layer3():
    elems = []
    elems.append(h1("6. Layer 3 — Optimum Racing Line Engine"))
    elems.append(hr())
    elems.append(sp(0.5))

    elems.append(body(
        "Reconstructs track geometry using B-spline/clothoid fitting (not raw GPS differentiation), "
        "optimises the minimum-curvature racing line within OSM-sourced track boundaries, and "
        "generates a theoretical speed profile via CVXPY convex optimisation. Iterative refinement "
        "with Layer 4 resolves the circular traction-circle dependency."
    ))
    elems.append(sp())

    elems.append(h2("Step 1 — Track Geometry via B-spline / Clothoid Fitting"))
    elems.append(body(
        "Curvature is NOT computed by double-differentiating GPS points (numerically unstable). "
        "Instead, fit a parametric B-spline to the aggregated median position across all drivers "
        "and sessions. Curvature is computed analytically from the spline control points."
    ))
    elems.append(math("kappa = (x'*y'' - y'*x'') / (x'^2 + y'^2)^(3/2)   [from spline, not raw GPS]"))
    elems.append(body(
        "Clothoid segments (Euler spirals) used at corner entries and exits — physically motivated "
        "as real circuit geometry is designed to clothoid standards. OSM circuit geometry registered "
        "to telemetry coordinate frame for validation and boundary extraction."
    ))
    elems.append(sp())

    elems.append(h2("Step 2 — Track Width & Boundary Extraction"))
    elems.append(body("Primary: OpenStreetMap track edges registered to telemetry coordinate frame."))
    elems.append(body("Validation: lateral spread of all drivers across full race weekend gives empirical lower bound on track width (typically within 0.5–1m of true edge)."))
    elems.append(body("Kerb detection: Z-channel anomalies identify kerb events → used as boundary anchors at high-usage corners."))
    elems.append(sp())

    elems.append(h2("Step 3 — Racing Line Optimisation"))
    elems.append(body(
        "Solve for the minimum curvature racing line within track boundaries. This is the "
        "geometric optimum — computationally tractable and a well-defined problem. "
        "It is explicitly documented as a geometric approximation to the true minimum-time "
        "optimal control problem."
    ))
    elems.append(math("min integral(kappa(s)^2 ds)   subject to: line within track boundaries"))
    elems.append(body("Late-session laps only (Q3 final runs, final race stints) used for geometry — track is fully evolved and driver lines are closest to physical limit."))
    elems.append(sp())

    elems.append(h2("Step 4 — Point-Mass Vehicle Model"))
    elems.append(body("Traction limit at any point on the racing line:"))
    elems.append(math("F_max = mu * (m*g + (1/2)*rho*A*Cl*v^2)"))
    elems.append(body(
        "The aero downforce term (Cl from Layer 1) makes the traction circle speed-dependent — "
        "grip increases with speed, capturing the most important vehicle dynamics effect. "
        "mu calibrated empirically from qualifying telemetry (Step 5)."
    ))
    elems.append(sp())

    elems.append(h2("Step 5 — Empirical Calibration Against Qualifying"))
    elems.append(body(
        "Find mu such that predicted speed profile matches actual fastest qualifier's speed "
        "profile within tolerance. This absorbs unknown vehicle parameters (brake bias, "
        "suspension geometry, weight transfer) into a single effective friction coefficient "
        "per circuit."
    ))
    elems.append(math("mu* = argmin_mu || v_predicted(s; mu) - v_actual_Q(s) ||^2"))
    elems.append(sp())

    elems.append(h2("Step 6 — Speed Profile via CVXPY Convex Optimisation"))
    elems.append(body("Forward-backward speed profile using convex optimisation:"))
    elems.append(math("Backward pass: max arrival speed at each apex given braking limits"))
    elems.append(math("Forward pass: max speed at each exit given traction limits"))
    elems.append(math("v_profile(s) = min(v_forward(s), v_backward(s))"))
    elems.append(body(
        "Speed-dependent aero traction limit from Layer 1 Cl posterior feeds directly into "
        "the constraint set. CVXPY handles the constrained optimisation cleanly."
    ))
    elems.append(sp())

    elems.append(h2("Step 7 — Iterative Refinement with Layer 4"))
    steps = [
        "Iteration 0: Fixed nominal mu (point-mass, constant, no temperature effect)",
        "Generate racing line and speed profile",
        "Feed load history (lateral force, braking energy) to Layer 4",
        "Layer 4 returns updated grip coefficient mu(E) as function of energy dissipation",
        "Recompute speed profile with updated traction limits",
        "Repeat until speed profile convergence (typically 3–5 iterations)",
    ]
    for i, s in enumerate(steps):
        elems.append(bullet(f"[{i}]  {s}"))
    elems.append(sp())

    elems.append(h2("Validation"))
    elems.append(body(
        "Compare predicted speed-distance profile against actual fastest qualifier. "
        "Target: predicted apex speed within ±5 km/h of actual. Gap between predicted "
        "optimal and actual driver speed quantifies driver performance margin — "
        "a useful output in itself, not a validation failure."
    ))

    elems.append(sp())
    elems.append(h3("Documented Assumptions"))
    assumptions = [
        "Geometric racing line is a documented approximation to true minimum-time optimal control",
        "Point-mass model — weight transfer and suspension dynamics are second-order corrections",
        "mu calibrated per circuit from qualifying; may not reflect wet or degraded conditions",
        "OSM boundary accuracy assumed within ±1m of true track edge",
        "Late-session laps assumed to represent fully-evolved track conditions",
    ]
    for a in assumptions:
        elems.append(assumption(a))

    elems.append(PageBreak())
    return elems


def build_layer4():
    elems = []
    elems.append(h1("7. Layer 4 — Tyre Thermodynamics & Wear"))
    elems.append(hr())
    elems.append(sp(0.5))

    elems.append(body(
        "Models tyre wear state, grip decay, and cliff probability using cumulative energy "
        "dissipation as the wear state variable — replacing an underdetermined full thermal "
        "simulator with a physically motivated proxy. A hierarchical Bayesian degradation "
        "model fitted across multiple circuits and seasons provides compound-specific "
        "degradation curves with honest uncertainty."
    ))
    elems.append(sp())

    elems.append(h2("Step 1 — Circuit Dominance Classification"))
    elems.append(math("D = [sum_L(kappa_L * v^2) - sum_R(kappa_R * v^2)] / [sum(kappa * v^2)]"))
    elems.append(body(
        "D > 0: left-dominant (e.g. Silverstone). D < 0: right-dominant (e.g. Bahrain). "
        "Identifies the most-stressed front tyre. Stress multiplier alpha_dominant = 1.15–1.25 "
        "scales energy dissipation for that tyre."
    ))
    elems.append(sp())

    elems.append(h2("Step 2 — Energy Dissipation Estimation"))
    elems.append(math("E_brake = integral[ F_brake(s) * v(s) ds ]"))
    elems.append(math("F_brake = m*|a_decel| - F_drag - F_rr"))
    elems.append(math("E_lateral = integral[ F_lateral(s) * v_slip(s) ds ]   [F_lat = m*v^2*kappa]"))
    elems.append(math("E_traction = integral[ F_traction(s) * v_slip_long(s) ds ]"))
    elems.append(math("E_total(n) = alpha_dominant * sum_i=1^n (E_brake + E_lateral + E_traction)_i"))
    elems.append(body("Uncertainty sigma_E(n) propagated via standard error propagation from noisy speed gradient and Layer 1 aero uncertainty."))
    elems.append(sp())

    elems.append(h2("Step 3 — Lap Time Decomposition"))
    elems.append(math("delta_t_lap(n) = f_fuel(n) + f_track(n) + f_tyre(E_total(n)) + epsilon(n)"))
    elems.append(h3("Components:"))
    elems.append(math("f_fuel(n) = -k_fuel * m_dot_fuel * n     [k_fuel = 0.03 s/kg, m_dot = 1.8 kg/lap]"))
    elems.append(math("f_track(n) ~ GP(0, k_track)     [exponential saturation kernel, shared across drivers]"))
    elems.append(math("f_tyre(E) = delta_t_lap - f_fuel - f_track     [isolated tyre signal]"))
    elems.append(body("Late-session laps (Q3, final race stints) used where f_track ≈ 0, simplifying decomposition."))
    elems.append(sp())

    elems.append(h2("Step 4 — Hierarchical Bayesian Degradation Model"))
    elems.append(math("f_tyre(E|theta) = beta0 + beta1*E + beta2*E^2 + gamma*1[E > E_cliff]"))
    elems.append(body("Hierarchical structure across circuits and compounds:"))
    elems.append(math("beta1^(c,k) ~ N(mu_beta1^(k), sigma_beta1^(k))"))
    elems.append(body("Compound-level mean shared across all circuits. Circuit-level deviates from mean."))
    elems.append(h3("Physically motivated priors:"))
    priors = [
        "beta1 > 0  (degradation monotone in energy — tyres don't improve with use)",
        "E_cliff within plausible stint window",
        "gamma > 0  (cliff always increases lap time)",
        "Compound ordering: beta1_C5 > beta1_C4 > ... > beta1_C1  (softer = faster degradation)",
    ]
    for p in priors:
        elems.append(bullet(p))
    elems.append(body("Calibration: Qualifying multi-run lap time delta (same tyre set, run 1 vs run 2) used as primary compound calibration — least confounded signal in public data."))
    elems.append(body("Fitting: PyMC MCMC across all available races (2018–2024) for each circuit-compound combination."))
    elems.append(sp())

    elems.append(h2("Step 5 — Tyre Cliff Survival Model"))
    elems.append(math("S(E) = P(no cliff before E) = exp(-integral_0^E h(e) de)"))
    elems.append(math("h(E) = (beta/lambda) * (E/lambda)^(beta-1)     [Weibull hazard]"))
    elems.append(math("P(cliff within k laps) = 1 - S(E + k*E_lap_mean) / S(E)"))
    elems.append(body("Cliff events identified from historical data as lap time jumps >1.5s not explained by SC, traffic, or weather."))
    elems.append(sp())

    elems.append(h2("Step 6 — Post-Pitstop Warm-up Model"))
    elems.append(math("mu(n_out) = mu_cold + (mu_opt - mu_cold) * (1 - exp(-n_out / tau))"))
    elems.append(math("tau = tau_0 * C_hardness / (T_track - T_ambient)"))
    elems.append(body(
        "mu_cold ≈ 0.75 * mu_opt (literature approximation). "
        "C_hardness index: C1=5, C2=4, C3=3, C4=2, C5=1. "
        "Warm-up curve feeds Layer 5 out-lap time prediction for undercut/overcut calculations."
    ))
    elems.append(sp())

    elems.append(h2("Step 7 — Cooling Model (Speed-Dependent)"))
    elems.append(math("E_effective(n) = E_total(n) * (1 - eta_cool)"))
    rows = [
        ["Monza / Montreal", "~230", "High", "Low eta_cool"],
        ["Spa / Silverstone", "~210", "Medium-high", "Medium-low eta_cool"],
        ["Bahrain / Abu Dhabi", "~195", "Medium", "Medium eta_cool"],
        ["Monaco / Singapore", "~160", "Low", "High eta_cool"],
    ]
    elems.append(make_table(
        ["Circuit Class", "Avg Speed (km/h)", "Cooling Rate", "Effect"],
        rows,
        col_widths=[4.5*cm, 4*cm, 3.5*cm, 4.5*cm]
    ))

    elems.append(sp())
    elems.append(h2("Layer 4 Output Summary"))
    rows = [
        ["Grip coefficient mu(n)", "Posterior distribution", "L3 refinement, L5"],
        ["Cumulative energy E_total(n)", "Point estimate + sigma_E", "L5"],
        ["Cliff probability P_cliff(n,k)", "Probability distribution", "L5 Monte Carlo"],
        ["Out-lap grip mu(n_out)", "Warm-up curve", "L5 undercut/overcut"],
        ["Degradation curve f_tyre(E)", "Posterior predictive", "L5 strategy window"],
    ]
    elems.append(make_table(
        ["Output", "Form", "Fed To"],
        rows,
        col_widths=[5.5*cm, 5*cm, 6*cm]
    ))

    elems.append(sp())
    elems.append(h3("Documented Assumptions"))
    assumptions = [
        "Most-stressed-tyre approximation with alpha_dominant = 1.15–1.25",
        "Fuel burn linear at 1.8 kg/lap, lap time sensitivity 0.03 s/kg",
        "Lateral slip angle approximated from path-heading deviation",
        "Cooling modelled as energy retention modifier, not explicit temperature tracking",
        "Compound ordering constraint encoded as prior (softer = faster degradation)",
        "Cliff identification threshold: >1.5s single-lap jump not explained by external events",
        "Warm-up cold grip = 0.75 x optimal grip (literature approximation)",
        "Track evolution modelled as GP with exponential saturation kernel",
    ]
    for a in assumptions:
        elems.append(assumption(a))

    elems.append(PageBreak())
    return elems


def build_layer5():
    elems = []
    elems.append(h1("8. Layer 5 — Monte Carlo Strategy Engine"))
    elems.append(hr())
    elems.append(sp(0.5))

    elems.append(body(
        "Simulates 10,000 race scenarios by jointly sampling all upstream posterior distributions, "
        "models safety car as a non-homogeneous Poisson process, uses historical opponent strategy "
        "archetypes and 2-player Nash equilibrium for undercut decisions, and solves for optimal "
        "pit strategy via receding horizon dynamic programming updated every 5 laps."
    ))
    elems.append(sp())

    elems.append(h2("Step 1 — Race State Initialisation (Laps 1–3)"))
    elems.append(body("Laps 1–3 are NOT physics-modelled. Empirical approach:"))
    elems.append(math("P(delta_p_i | p_grid_i)  from historical 2018–2024 race data"))
    elems.append(math("P(SC_lap1) = 3 * lambda_base_circuit     [elevated first-lap SC rate]"))
    elems.append(body("Race state s4 = (position, gap, E_tyre, stint_n, compound, SC_status) initialised at lap 4."))
    elems.append(sp())

    elems.append(h2("Step 2 — Joint Upstream Uncertainty Sampling"))
    elems.append(body("Per scenario j, draw one consistent sample from all upstream posteriors:"))
    elems.append(math("Cd^(j) ~ N(mu_Cd, sigma_Cd),   Cl^(j) ~ N(mu_Cl, sigma_Cl)"))
    elems.append(math("v_profile^(j)(s) = v_bar(s) + epsilon_v(s),   epsilon_v ~ GP(0, k_v)"))
    elems.append(math("beta^(j), E_cliff^(j) ~ P(beta, E_cliff | data)     [Layer 4 MCMC posterior]"))
    elems.append(math("t_pit^(j) ~ Empirical_team  OR  Empirical_team + U(3,8)  [w/ prob p_issue]"))
    elems.append(body("All samples held fixed for entire race simulation — preserves inter-layer correlation."))
    elems.append(sp())

    elems.append(h2("Step 3 — Compound Strategy Space"))
    elems.append(h3("Dominance pruning:"))
    elems.append(body("Strategy A dominates B if total race time A <= B across all plausible degradation scenarios. Typically reduces search space by 40–60%."))
    elems.append(h3("Vectorised evaluation:"))
    elems.append(math("S in R^(N_strategies x N_laps)     evaluated via NumPy broadcasting"))
    elems.append(body("Degradation model pre-computed as lookup table over (compound, energy dissipation) pairs."))
    elems.append(sp())

    elems.append(h2("Step 4 — Safety Car Model"))
    elems.append(math("lambda(n) = lambda_base^(c) * phi(n)"))
    rows = [
        ["Laps 1–3", "3.0x", "Historically elevated crash rate"],
        ["Laps 4 – 80% race", "1.0x", "Baseline mid-race rate"],
        ["Final 20% laps", "1.3x", "Increased risk on worn tyres"],
    ]
    elems.append(make_table(
        ["Lap Range", "phi(n) Multiplier", "Rationale"],
        rows,
        col_widths=[4*cm, 4*cm, 8.5*cm]
    ))
    elems.append(sp(0.5))
    elems.append(body("Scenario branching: run parallel no-SC and SC-at-lap-N/3 branches. Strategies robust to both branches flagged as highest-confidence recommendations."))
    elems.append(sp())

    elems.append(h2("Step 5 — Opponent Strategy Modelling"))
    rows = [
        ["Aggressive", "Early stop, 2-stop preferred", "Red Bull 2022–23"],
        ["Conservative", "Late stop, 1-stop preferred", "Mercedes 2021"],
        ["Reactive", "Responds to leader within 2 laps", "Most midfield"],
        ["Opportunistic", "SC-triggered, flexible", "Alpine, McLaren"],
    ]
    elems.append(make_table(
        ["Archetype", "Characteristics", "Example"],
        rows,
        col_widths=[4*cm, 8*cm, 4.5*cm]
    ))
    elems.append(sp(0.5))
    elems.append(h3("2-player Nash equilibrium for undercut:"))
    elems.append(body("When gap falls below threshold, solve 2x2 simultaneous game (you pit / stay vs opponent pit / stay). Payoffs from Layer 4 warm-up model, degradation curve, pit loss samples. Closed-form Nash equilibrium mixing probability reported as undercut confidence."))
    elems.append(sp())

    elems.append(h2("Step 6 — Traffic Model"))
    rows = [
        ["Clean air (gap > 2s)", "0.0s"],
        ["DRS range (0.5 < gap <= 1.0s)", "-0.1s (DRS benefit)"],
        ["DRS train (gap <= 0.5s)", "+0.3–0.5s"],
        ["Midfield pack (gap <= 0.3s)", "+0.5–1.0s"],
    ]
    elems.append(make_table(
        ["Situation", "Lap Time Penalty"],
        rows,
        col_widths=[9*cm, 7.5*cm]
    ))
    elems.append(sp(0.5))
    elems.append(body("Post-hoc correction: optimise assuming clean air, apply traffic penalty by predicted position, iterate once. Tyre energy dissipation multiplied by alpha_traffic = 1.08–1.12 during traffic laps."))
    elems.append(sp())

    elems.append(h2("Step 7 — Undercut / Overcut Viability"))
    elems.append(math("W_undercut^(j) = t_opp_degraded^(j) - t_out_fresh^(j) - t_pitloss^(j) - g_current^(j)"))
    elems.append(math("P(undercut viable) = (1/N_MC) * sum_j 1[W_undercut^(j) > 0]"))
    elems.append(math("g* = gap s.t. P(undercut viable | gap = g*) = 0.70     [decision threshold]"))
    elems.append(body("g* recomputed every 5 laps as tyre states evolve. Overcut viability symmetric — stays out while opponent loses more time on worn tyres than the pit stop costs."))
    elems.append(sp())

    elems.append(h2("Step 8 — Receding Horizon Dynamic Programming"))
    elems.append(math("s_n = (E_tyre, position, gap, compound, stint_n, SC_status)"))
    elems.append(math("V(s_n) = min_a E[ sum_{k=n}^{N} t_lap(s_k, a_k) + t_pitloss * 1[a_k=pit] ]"))
    elems.append(math("V(s_k) = min_{a_k} [ t_lap(s_k, a_k) + E[V(s_{k+1}) | s_k, a_k] ]"))
    elems.append(body("Re-solved every 5 laps. Immediate re-solve triggered by: SC deployment/end, unexpected opponent pit, cliff probability > 0.40, gap crossing g*."))
    elems.append(sp())

    elems.append(h2("Step 9 — Aggregation & Scoring"))
    elems.append(math("Score_s = w1 * T_s_mean + w2 * CVaR_0.8(T_s)     [w1=0.7, w2=0.3]"))
    elems.append(body("10,000 scenarios. Convergence verified by checking strategy ranking stability between 5,000 and 10,000 runs."))
    elems.append(sp())

    elems.append(h2("Layer 5 Final Output"))
    rows = [
        ["Optimal strategy", "Compound sequence + pit laps, ranked by Score"],
        ["Expected race time", "Distribution over 10,000 scenarios"],
        ["Risk ranking", "CVaR-adjusted strategy scores"],
        ["Undercut viability", "P(undercut viable) + g* threshold"],
        ["Overcut viability", "P(overcut viable), updated every 5 laps"],
        ["SC robustness R_s", "P(strategy remains optimal | SC at any lap)"],
        ["Cliff warning", "P(cliff within k laps) from Layer 4 survival model"],
        ["Scenario branches", "No-SC optimal vs SC-at-peak-impact optimal"],
    ]
    elems.append(make_table(
        ["Output", "Form"],
        rows,
        col_widths=[6*cm, 10.5*cm]
    ))

    elems.append(sp())
    elems.append(h3("Documented Assumptions"))
    assumptions = [
        "Laps 1–3 modelled empirically, not from physics",
        "Traffic penalty calibrated from historical clean-air vs traffic lap time deltas",
        "Opponent archetypes fitted from 2018–2024 — may not reflect current team strategies",
        "Unsafe release probability: 0.005–0.02 per stop (team specific)",
        "SC lap multipliers: 3.0x laps 1–3, 1.0x mid-race, 1.3x final 20%",
        "Nash equilibrium assumes rational opponent with full information",
        "10,000 scenarios sufficient for strategy ranking convergence",
        "Receding horizon re-solve every 5 laps or on trigger events",
    ]
    for a in assumptions:
        elems.append(assumption(a))

    elems.append(PageBreak())
    return elems


def build_validation():
    elems = []
    elems.append(h1("9. Validation Strategy"))
    elems.append(hr())
    elems.append(sp(0.5))

    elems.append(h2("Per-Layer Validation"))
    rows = [
        ["L1 — Aero", "Cd/Cl posteriors vs published F1 aero configs and DRS delta_Cd literature range"],
        ["L2 — Alignment", "Sector time recovery error < 0.05s; transitivity check epsilon_ABC < 0.5m"],
        ["L3 — Racing Line", "Predicted apex speed within ±5 km/h of fastest qualifier telemetry"],
        ["L4 — Tyre", "Degradation curve vs multi-stint race data; cliff timing vs historical cliff events"],
        ["L5 — Strategy", "SC timing distribution vs historical; pit stop distribution vs FastF1 records"],
    ]
    elems.append(make_table(
        ["Layer", "Validation Method"],
        rows,
        col_widths=[4*cm, 12.5*cm]
    ))
    elems.append(sp())

    elems.append(h2("Counterfactual Backtesting Circuits"))
    elems.append(body("Validate on strategy-dominant circuits where the best strategy almost always wins regardless of SC timing:"))
    circuits = ["Monaco 2022 — minimal overtaking, pure strategy race",
                "Singapore 2023 — street circuit, strategy decisive",
                "Hungary 2022 — low overtaking, strategy dominant"]
    for c in circuits:
        elems.append(bullet(c))
    elems.append(sp())

    elems.append(h2("SC Robustness Metric"))
    elems.append(math("R_s = P(strategy s remains optimal | SC occurs at any lap)"))
    elems.append(body("Strategies with R_s > 0.65 flagged as SC-robust recommendations."))
    elems.append(sp())

    elems.append(h2("Driver Performance Margin"))
    elems.append(body(
        "Gap between predicted optimal speed profile and actual driver speed is not a validation "
        "failure — it quantifies how much performance the driver left available due to tyre "
        "management, traffic, or setup compromise. This is an additional useful output."
    ))

    elems.append(PageBreak())
    return elems


def build_assumptions():
    elems = []
    elems.append(h1("10. Documented Assumptions Master List"))
    elems.append(hr())
    elems.append(sp(0.5))

    elems.append(body(
        "All assumptions are documented here for transparency. These are the known approximations "
        "the model makes due to data limitations. Any result should be interpreted in light of these."
    ))
    elems.append(sp())

    sections = {
        "Layer 1 — Aero": [
            ("Car mass", "798 kg with driver, ±2 kg"),
            ("Fuel burn", "Linear, 1.8 kg/lap"),
            ("Lap time fuel sensitivity", "0.03 s/kg"),
            ("Reference area A", "1.5 m^2 (published F1 approximation)"),
            ("Engine power", "Approximated from RPM/gear (±8%)"),
            ("Rolling resistance", "Prior 500–600 N (±15%)"),
            ("DRS delta_Cd", "0.08–0.12 (literature range, calibration bound)"),
            ("Street circuit params", "Inherited from similar config race, sigma widened x1.5"),
        ],
        "Layer 2 — Alignment": [
            ("Circuit length", "Official F1 figure, accurate to ±1m"),
            ("Max timing offset", "2.0s inter-driver upper bound for DTW window"),
            ("Dead reckoning error", "~0.35m per 250ms GPS interval at max speed"),
            ("Weather GP — track temp", "Length scale l = 5 minutes"),
            ("Weather GP — air temp", "Length scale l = 15 minutes"),
            ("Distance grid", "1m spacing sufficient for Layer 3 curvature"),
        ],
        "Layer 3 — Racing Line": [
            ("Racing line type", "Geometric minimum curvature — approximation to minimum time"),
            ("Vehicle model", "Point mass — weight transfer is second-order correction"),
            ("mu calibration", "Per circuit from qualifying; may not reflect wet conditions"),
            ("OSM boundaries", "Accurate to ±1m of true track edge"),
            ("Track evolution", "Late-session laps assumed fully evolved"),
        ],
        "Layer 4 — Tyre": [
            ("Tyre model", "Energy-based wear proxy, not full thermal simulator"),
            ("Stress multiplier", "alpha_dominant = 1.15–1.25 for most-stressed tyre"),
            ("Cliff threshold", ">1.5s single-lap jump not explained by external events"),
            ("Cold grip", "mu_cold = 0.75 * mu_opt (literature approximation)"),
            ("Compound hardness", "C1=5, C2=4, C3=3, C4=2, C5=1 index"),
            ("Cooling", "Modelled as energy retention modifier, not explicit temperature"),
            ("Compound ordering", "Softer compound = faster degradation (prior constraint)"),
        ],
        "Layer 5 — Strategy": [
            ("Race start", "Laps 1–3 empirical, not physics-modelled"),
            ("Traffic penalty", "Calibrated from historical clean-air vs traffic deltas"),
            ("Opponent archetypes", "Fitted 2018–2024 — may not reflect current strategies"),
            ("Unsafe release prob", "0.005–0.02 per stop (team specific)"),
            ("SC lap 1 multiplier", "3.0x baseline SC rate"),
            ("SC final 20% multiplier", "1.3x baseline SC rate"),
            ("Nash equilibrium", "Assumes rational opponent with full information"),
            ("MC convergence", "10,000 scenarios; verified by 5k vs 10k stability check"),
            ("DP re-solve frequency", "Every 5 laps or on trigger events"),
        ],
    }

    for section, items in sections.items():
        elems.append(h2(section))
        rows = [[name, value] for name, value in items]
        elems.append(make_table(
            ["Assumption", "Value / Notes"],
            rows,
            col_widths=[6*cm, 10.5*cm]
        ))
        elems.append(sp(0.5))

    return elems


# ── Build document ────────────────────────────────────────────────────────────

def build():
    path = Path(__file__).resolve().parent / "F1_Pipeline_Technical_Reference.pdf"

    doc = SimpleDocTemplate(
        str(path),
        pagesize=A4,
        leftMargin=MARGIN, rightMargin=MARGIN,
        topMargin=1.5*cm, bottomMargin=1.2*cm,
        title="F1 Physics-Based Predictive Pipeline",
        author="Gaurav",
        subject="Technical Reference Document"
    )

    story = []
    story += build_cover()
    story += build_toc()
    story += build_overview()
    story += build_data_sources()
    story += build_uncertainty()
    story += build_layer1()
    story += build_layer2()
    story += build_layer3()
    story += build_layer4()
    story += build_layer5()
    story += build_validation()
    story += build_assumptions()

    doc.build(
        story,
        onFirstPage=on_first_page,
        onLaterPages=on_page
    )
    print(f"PDF written to {path}")

build()
