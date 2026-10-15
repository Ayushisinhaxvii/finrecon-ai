from rag.streamlit_workflow import render_investigator
import json
from pathlib import Path

import duckdb
import pandas as pd
import streamlit as st

from rag.sql_rag_router import build_graph


# ============================================================
# 1. CONFIGURATION
# ============================================================

ROOT = Path(__file__).resolve().parent
DB_PATH = ROOT / "dev.duckdb"
AUDIT_PATH = ROOT / "metadata" / "approval_audit.jsonl"
RUNS_PATH = ROOT / "metadata" / "pipeline_runs.jsonl"
LINEAGE_PATH = ROOT / "metadata" / "data_lineage.jsonl"

st.set_page_config(
    page_title="FINRECON AI | Reconciliation Intelligence",
    page_icon="◈",
    layout="wide",
    initial_sidebar_state="expanded",
)


# ============================================================
# 2. DESIGN SYSTEM
# ============================================================

st.markdown(
    """
    <style>
    @import url('https://fonts.googleapis.com/css2?family=DM+Sans:wght@400;500;600;700&family=Manrope:wght@400;500;600;700;800&display=swap');

    :root {
        --bg: #F4F7FB;
        --ink: #17233B;
        --muted: #718096;
        --line: #E4EAF2;
        --navy: #101B33;
        --teal: #00BFA6;
        --blue: #4361EE;
        --red: #D94F61;
        --amber: #C9851B;
    }

    html, body, [class*="css"] {
        font-family: 'DM Sans', sans-serif;
    }

    .stApp {
        background: var(--bg);
        color: var(--ink);
    }

    [data-testid="stHeader"] {
        background: transparent;
    }

    [data-testid="stSidebar"] {
        background: #101B33;
        border-right: 1px solid #26334B;
    }

    [data-testid="stSidebar"] * {
        color: #E7EEF9;
    }

    [data-testid="stSidebar"] [data-testid="stRadio"] label {
        padding: 9px 10px;
        border-radius: 9px;
    }

    [data-testid="stSidebar"] [data-testid="stRadio"] label:hover {
        background: #1D2B45;
    }

    [data-testid="stSidebar"] hr {
        border-color: #2C3952;
    }

    .brand {
        font-family: 'Manrope', sans-serif;
        font-size: 23px;
        font-weight: 800;
        letter-spacing: -0.8px;
        color: white;
        padding: 8px 0 0;
    }

    .brand-accent {
        color: #00D4B4;
    }

    .brand-sub {
        font-size: 11px;
        color: #9AAAC4;
        letter-spacing: 1.5px;
        text-transform: uppercase;
        margin: 3px 0 20px;
    }

    .side-status {
        background: #192842;
        border: 1px solid #2C3B55;
        border-radius: 12px;
        padding: 13px;
        font-size: 12px;
        color: #B7C6DC;
        line-height: 1.8;
    }

    .side-dot {
        color: #00D4B4;
        font-size: 15px;
    }

    .hero {
        background: linear-gradient(115deg, #101B33 0%, #1D3152 75%, #175D68 130%);
        border-radius: 20px;
        padding: 28px 30px;
        color: white;
        margin-bottom: 22px;
        border: 1px solid #243B5C;
    }

    .eyebrow {
        color: #76E6D5;
        font-size: 11px;
        text-transform: uppercase;
        letter-spacing: 2px;
        font-weight: 700;
        margin-bottom: 9px;
    }

    .hero-title {
        font-family: 'Manrope', sans-serif;
        font-size: clamp(25px, 3vw, 35px);
        font-weight: 800;
        letter-spacing: -1.2px;
        line-height: 1.2;
        margin: 0 0 10px;
        color: #FFFFFF;
    }

    .hero-copy {
        font-size: 14px;
        color: #C5D2E6;
        line-height: 1.7;
        max-width: 720px;
    }

    .hero-tag {
        display: inline-block;
        margin-top: 16px;
        padding: 6px 10px;
        background: #183C4B;
        color: #8CF2E0;
        border: 1px solid #286274;
        border-radius: 7px;
        font-size: 11px;
        font-weight: 700;
        letter-spacing: .5px;
    }

    .section-heading {
        font-family: 'Manrope', sans-serif;
        color: #17233B;
        font-size: 19px;
        font-weight: 800;
        letter-spacing: -.45px;
        margin: 6px 0 3px;
    }

    .section-copy {
        color: #718096;
        font-size: 12px;
        margin-bottom: 15px;
        line-height: 1.6;
    }

    .metric-card {
        background: #FFFFFF;
        border: 1px solid #E4EAF2;
        border-radius: 15px;
        padding: 17px 17px 15px;
        min-height: 132px;
        box-shadow: 0 3px 12px rgba(28, 47, 78, .025);
    }

    .metric-top {
        display: flex;
        align-items: center;
        justify-content: space-between;
        gap: 6px;
    }

    .metric-label {
        color: #718096;
        font-size: 11px;
        font-weight: 700;
        text-transform: uppercase;
        letter-spacing: .6px;
    }

    .metric-icon {
        background: #EFF5FB;
        color: #4361EE;
        border-radius: 8px;
        padding: 5px 8px;
        font-size: 14px;
    }

    .metric-value {
        font-family: 'Manrope', sans-serif;
        color: #17233B;
        font-size: 30px;
        font-weight: 800;
        letter-spacing: -1px;
        margin-top: 13px;
        line-height: 1.1;
    }

    .metric-note {
        color: #8290A5;
        font-size: 11px;
        margin-top: 8px;
    }

    .panel {
        background: #FFFFFF;
        border: 1px solid #E4EAF2;
        border-radius: 15px;
        padding: 19px;
        margin-bottom: 14px;
    }

    .panel-title {
        font-family: 'Manrope', sans-serif;
        font-size: 15px;
        font-weight: 800;
        color: #17233B;
        margin-bottom: 3px;
    }

    .panel-subtitle {
        font-size: 11px;
        color: #8290A5;
        margin-bottom: 15px;
    }

    .insight {
        background: #EAF8F5;
        border: 1px solid #C7EEE5;
        border-left: 4px solid #00A991;
        padding: 15px 16px;
        border-radius: 11px;
        color: #245D55;
        font-size: 13px;
        line-height: 1.7;
        margin: 10px 0 16px;
    }

    .warning-box {
        background: #FFF6E8;
        border: 1px solid #F4DDB8;
        border-left: 4px solid #D99528;
        padding: 13px 15px;
        border-radius: 10px;
        color: #815A1F;
        font-size: 12px;
        line-height: 1.7;
        margin: 12px 0;
    }

    .status-pill {
        display: inline-block;
        border-radius: 6px;
        padding: 4px 8px;
        font-size: 10px;
        font-weight: 800;
        letter-spacing: .5px;
    }

    .status-high {
        background: #FDEBED;
        color: #B72E43;
    }

    .status-medium {
        background: #FFF2D9;
        color: #986215;
    }

    .status-ok {
        background: #DDF8EF;
        color: #08795F;
    }

    .status-neutral {
        background: #EDF1F7;
        color: #58677E;
    }

    .evidence-label {
        color: #7A899E;
        font-size: 10px;
        font-weight: 700;
        text-transform: uppercase;
        letter-spacing: .7px;
        margin-bottom: 4px;
    }

    .evidence-value {
        color: #17233B;
        font-family: 'Manrope', sans-serif;
        font-size: 18px;
        font-weight: 800;
        overflow-wrap: anywhere;
    }

    .evidence-box {
        background: #F7F9FC;
        border: 1px solid #E6ECF4;
        border-radius: 11px;
        padding: 13px;
        min-height: 77px;
        margin-bottom: 8px;
    }

    .flow-step {
        border: 1px solid #E4EAF2;
        background: #FFFFFF;
        border-radius: 11px;
        padding: 13px;
        margin-bottom: 8px;
        color: #17233B;
        font-size: 12px;
        line-height: 1.6;
    }

    .flow-num {
        display: inline-flex;
        background: #E4F8F4;
        color: #078C79;
        width: 25px;
        height: 25px;
        align-items: center;
        justify-content: center;
        border-radius: 8px;
        font-weight: 800;
        margin-right: 8px;
    }

    .footer {
        text-align: center;
        color: #8A98AB;
        font-size: 10px;
        padding: 20px 0 10px;
        letter-spacing: .5px;
    }

    div[data-testid="stMetric"] {
        background: #FFFFFF;
        border: 1px solid #E4EAF2;
        padding: 13px;
        border-radius: 12px;
    }

    div[data-testid="stMetricLabel"] {
        color: #718096;
    }

    div[data-testid="stMetricValue"] {
        color: #17233B;
    }

    .stButton button {
        border-radius: 9px;
        font-weight: 700;
        min-height: 40px;
    }

    div[data-testid="stDataFrame"] {
        border: 1px solid #E4EAF2;
        border-radius: 10px;
        overflow: hidden;
    }

    #MainMenu, footer {
        visibility: hidden;
    }
    </style>
    """,
    unsafe_allow_html=True,
)


# ============================================================
# 3. DATA ACCESS
# ============================================================

@st.cache_data(ttl=30)
def load_incidents() -> pd.DataFrame:
    if not DB_PATH.exists():
        raise FileNotFoundError(f"Database not found: {DB_PATH}")

    connection = duckdb.connect(str(DB_PATH), read_only=True)

    try:
        return connection.execute(
            """
            SELECT *
            FROM fct_reconciliation_incidents
            ORDER BY order_id
            """
        ).fetchdf()
    finally:
        connection.close()


def read_jsonl(path: Path) -> list[dict]:
    if not path.exists():
        return []

    records = []

    with path.open("r", encoding="utf-8") as file:
        for line_number, line in enumerate(file, start=1):
            if not line.strip():
                continue

            try:
                records.append(json.loads(line))
            except json.JSONDecodeError:
                # Preserve the rest of the log if one line is malformed.
                continue

    return records


def value_of(row, key, default="—"):
    value = row.get(key, default)

    if value is None or pd.isna(value):
        return default

    return value


def money(value, currency="INR"):
    try:
        number = float(value)
        if currency == "INR":
            return f"₹{number:,.2f}"
        return f"{currency} {number:,.2f}"
    except (ValueError, TypeError):
        return "Not available"


def show_metric(label, value, note, symbol):
    st.markdown(
        f"""
        <div class="metric-card">
            <div class="metric-top">
                <span class="metric-label">{label}</span>
                <span class="metric-icon">{symbol}</span>
            </div>
            <div class="metric-value">{value}</div>
            <div class="metric-note">{note}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def show_section(title, subtitle):
    st.markdown(
        f"""
        <div class="section-heading">{title}</div>
        <div class="section-copy">{subtitle}</div>
        """,
        unsafe_allow_html=True,
    )


# ============================================================
# 4. SIDEBAR
# ============================================================

NAVIGATION_OPTIONS = [
    "Command Center",
    "Incident Explorer",
    "Audit Trail",
    "System Health",
    "AI Investigator",
]

# The Command Center button requests a page change before Streamlit reruns.
# Apply that request to the radio widget's state before creating the widget.
if "requested_page" in st.session_state:
    requested_page = st.session_state.pop("requested_page")
    if requested_page in NAVIGATION_OPTIONS:
        st.session_state["page_navigation"] = requested_page

with st.sidebar:
    st.markdown(
        """
        <div class="brand">FINRECON<span class="brand-accent"> AI</span></div>
        <div class="brand-sub">Reconciliation intelligence</div>
        """,
        unsafe_allow_html=True,
    )

    st.markdown("### WORKSPACE")

    page = st.radio(
        "Navigate",
        NAVIGATION_OPTIONS,
        key="page_navigation",
        label_visibility="collapsed",
    )

    st.divider()

    st.markdown(
        """
        <div class="side-status">
            <span class="side-dot">●</span> LOCAL DATABASE<br>
            Read-only financial access<br>
            <span style="color:#8EA2BE">
            AI recommendations require human review
            </span>
        </div>
        """,
        unsafe_allow_html=True,
    )

    st.write("")
    if st.button("↻ Refresh dashboard", use_container_width=True):
        st.cache_data.clear()
        st.rerun()

    st.caption("FINRECON AI · Portfolio edition")


# ============================================================
# 5. LOAD DATA
# ============================================================

try:
    incidents = load_incidents()
except (duckdb.Error, OSError, FileNotFoundError) as exc:
    st.error(f"Unable to load reconciliation incidents: {exc}")
    st.caption(f"Expected database location: {DB_PATH}")
    st.stop()

if incidents.empty:
    st.warning("No incidents found in the reconciliation model.")
    st.stop()

audit_records = read_jsonl(AUDIT_PATH)
pipeline_runs = read_jsonl(RUNS_PATH)
lineage_records = read_jsonl(LINEAGE_PATH)

total = len(incidents)

severity_series = (
    incidents["incident_severity"]
    if "incident_severity" in incidents.columns
    else pd.Series(dtype=str)
)

high_count = int(severity_series.eq("HIGH").sum())
medium_count = int(severity_series.eq("MEDIUM").sum())

type_counts = incidents["incident_type"].value_counts()

missing_count = int(type_counts.get("MISSING_PAYMENT", 0))
settlement_count = int(type_counts.get("SETTLEMENT_MISMATCH", 0))


# ============================================================
# 6. COMMAND CENTER
# ============================================================

if page == "Command Center":
    st.markdown(
        f"""
        <div class="hero">
            <div class="eyebrow">FINANCIAL OPERATIONS · OVERVIEW</div>
            <div class="hero-title">Reconciliation command center</div>
            <div class="hero-copy">
                One place to understand financial discrepancies, inspect
                evidence, and track investigation decisions. Financial facts
                are calculated by SQL; recommendations remain subject to
                human review.
            </div>
            <span class="hero-tag">● DATABASE CONNECTED · READ ONLY</span>
        </div>
        """,
        unsafe_allow_html=True,
    )

    show_section(
        "Today's control view",
        "A summary of incidents currently present in the reconciliation model. "
        "These are dataset totals, not a count of incidents created today.",
    )

    metrics = st.columns(4)

    with metrics[0]:
        show_metric(
            "Total incidents",
            f"{total:,}",
            "Records flagged for investigation",
            "◎",
        )

    with metrics[1]:
        show_metric(
            "High severity",
            f"{high_count:,}",
            "Requires priority review",
            "!",
        )

    with metrics[2]:
        show_metric(
            "Missing payments",
            f"{missing_count:,}",
            "Orders without a matching payment",
            "↗",
        )

    with metrics[3]:
        show_metric(
            "Settlement mismatches",
            f"{settlement_count:,}",
            "Settlement calculation needs review",
            "≠",
        )

    st.write("")

    left, right = st.columns([1.15, 0.85], gap="large")

    with left:
        st.markdown(
            '<div class="panel-title">Incident distribution</div>'
            '<div class="panel-subtitle">'
            'How flagged records are split by incident type'
            '</div>',
            unsafe_allow_html=True,
        )

        distribution = (
            incidents["incident_type"]
            .value_counts()
            .rename_axis("Incident type")
            .reset_index(name="Incidents")
        )

        st.bar_chart(
            distribution,
            x="Incident type",
            y="Incidents",
            horizontal=True,
        )

        st.caption(
            "A missing payment and a settlement mismatch are different "
            "problems and require different investigation steps."
        )

    with right:
        st.markdown(
            '<div class="panel-title">Severity overview</div>'
            '<div class="panel-subtitle">'
            'Distribution of the assigned incident severity'
            '</div>',
            unsafe_allow_html=True,
        )

        severity_data = (
            severity_series.value_counts()
            .rename_axis("Severity")
            .reset_index(name="Incidents")
        )

        if not severity_data.empty:
            st.bar_chart(
                severity_data,
                x="Severity",
                y="Incidents",
            )

        st.markdown(
            """
            <div class="insight">
                <b>How to read this:</b><br>
                HIGH means the current rule assigns higher investigation
                priority. MEDIUM means the issue still needs review.
                Severity is a prioritization label, not proof of financial loss.
            </div>
            """,
            unsafe_allow_html=True,
        )

    show_section(
        "Recent records",
        "A quick preview of incidents available for investigation.",
    )

    preview_columns = [
        c for c in [
            "order_id",
            "payment_id",
            "incident_type",
            "incident_severity",
            "suspected_cause",
        ]
        if c in incidents.columns
    ]

    st.dataframe(
        incidents[preview_columns].head(10),
        use_container_width=True,
        hide_index=True,
    )

    if st.button("Explore all incidents →", type="primary"):
        st.session_state["requested_page"] = "Incident Explorer"
        st.rerun()


# ============================================================
# 7. INCIDENT EXPLORER
# ============================================================

elif page == "Incident Explorer":
    st.markdown(
        """
        <div class="hero">
            <div class="eyebrow">INVESTIGATION WORKSPACE</div>
            <div class="hero-title">Find the discrepancy. Inspect the evidence.</div>
            <div class="hero-copy">
                Filter incidents, locate an affected order, and compare the
                recorded financial values. The figures below come from the
                reconciliation database.
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    filtered = incidents.copy()

    filter1, filter2, filter3 = st.columns([1, 1, 1.2])

    types = sorted(filtered["incident_type"].dropna().unique().tolist())

    with filter1:
        selected_types = st.multiselect(
            "Incident type",
            options=types,
            default=types,
        )

    with filter2:
        severities = (
            sorted(filtered["incident_severity"].dropna().unique().tolist())
            if "incident_severity" in filtered.columns
            else []
        )

        selected_severities = st.multiselect(
            "Severity",
            options=severities,
            default=severities,
        )

    with filter3:
        search = st.text_input(
            "Search order or payment ID",
            placeholder="e.g. ORD000907",
        ).strip()

    filtered = filtered[filtered["incident_type"].isin(selected_types)]

    if "incident_severity" in filtered.columns:
        filtered = filtered[
            filtered["incident_severity"].isin(selected_severities)
        ]

    if search:
        mask = pd.Series(False, index=filtered.index)

        for column in ["order_id", "payment_id"]:
            if column in filtered.columns:
                mask |= (
                    filtered[column]
                    .astype("string")
                    .str.contains(search, case=False, na=False)
                )

        filtered = filtered[mask]

    st.write("")
    st.metric("Matching incidents", f"{len(filtered):,}")

    st.dataframe(
        filtered,
        use_container_width=True,
        hide_index=True,
    )

    st.divider()
    show_section(
        "Evidence room",
        "Select a matching incident below to see its recorded values "
        "and, where possible, the expected settlement calculation.",
    )

    if filtered.empty:
        st.info("No incidents match your current filters.")
    else:
        choices = filtered.index.tolist()

        selected_index = st.selectbox(
            "Choose an incident",
            options=choices,
            format_func=lambda idx: (
                f"{value_of(filtered.loc[idx], 'incident_type')}  ·  "
                f"{value_of(filtered.loc[idx], 'order_id')}  ·  "
                f"{value_of(filtered.loc[idx], 'payment_id')}"
            ),
        )

        row = filtered.loc[selected_index]

        order_currency = str(value_of(row, "order_currency", "INR"))
        payment_currency = str(value_of(row, "payment_currency", "INR"))

        st.markdown(
            f"""
            <div class="panel">
                <div class="eyebrow" style="color:#078C79">
                    SELECTED INCIDENT
                </div>
                <div class="panel-title" style="font-size:20px">
                    {value_of(row, 'incident_type')}
                </div>
                <div style="margin:8px 0 12px">
                    <span class="status-pill {
                        'status-high'
                        if value_of(row, 'incident_severity') == 'HIGH'
                        else 'status-medium'
                    }">
                        {value_of(row, 'incident_severity')}
                    </span>
                    &nbsp;
                    <span class="status-pill status-neutral">
                        ORDER {value_of(row, 'order_id')}
                    </span>
                </div>
                <div class="section-copy" style="margin-bottom:0">
                    {value_of(row, 'suspected_cause')}
                </div>
            </div>
            """,
            unsafe_allow_html=True,
        )

        evidence_columns = st.columns(4)

        evidence_fields = [
            ("Order amount", "order_amount", order_currency),
            ("Payment amount", "payment_amount", payment_currency),
            ("Refund amount", "refund_amount", payment_currency),
            ("Settlement amount", "settlement_amount", payment_currency),
        ]

        for column, (label, key, currency) in zip(
            evidence_columns, evidence_fields
        ):
            with column:
                amount = money(value_of(row, key, None), currency)
                st.markdown(
                    f"""
                    <div class="evidence-box">
                        <div class="evidence-label">{label}</div>
                        <div class="evidence-value">{amount}</div>
                    </div>
                    """,
                    unsafe_allow_html=True,
                )

        # This calculation follows the current project rule:
        # expected settlement = payment amount - refund amount.
        payment = pd.to_numeric(
            pd.Series([value_of(row, "payment_amount", None)]),
            errors="coerce",
        ).iloc[0]

        refund = pd.to_numeric(
            pd.Series([value_of(row, "refund_amount", None)]),
            errors="coerce",
        ).iloc[0]

        settlement = pd.to_numeric(
            pd.Series([value_of(row, "settlement_amount", None)]),
            errors="coerce",
        ).iloc[0]

        if pd.notna(payment) and pd.notna(refund) and pd.notna(settlement):
            expected = payment - refund
            difference = settlement - expected

            st.markdown(
                '<div class="panel-title">Settlement calculation</div>'
                '<div class="panel-subtitle">'
                'Using the project rule: payment amount minus refund amount. '
                'Other fees or adjustments are not modeled in this calculation.'
                '</div>',
                unsafe_allow_html=True,
            )

            calc1, calc2, calc3 = st.columns(3)

            with calc1:
                st.metric("Expected settlement", money(expected, payment_currency))

            with calc2:
                st.metric("Recorded settlement", money(settlement, payment_currency))

            with calc3:
                st.metric(
                    "Difference (recorded − expected)",
                    money(difference, payment_currency),
                )

            if abs(difference) > 0.01:
                st.markdown(
                    f"""
                    <div class="warning-box">
                        <b>Mismatch detected by the current rule.</b><br>
                        The recorded settlement differs from the calculated
                        expected settlement by {money(difference, payment_currency)}.
                        This is evidence of a discrepancy, not proof of its root cause.
                    </div>
                    """,
                    unsafe_allow_html=True,
                )
            else:
                st.success(
                    "The settlement values match under the current rule."
                )

        st.markdown("#### Recommended next check")

        st.write(value_of(row, "recommended_action"))

        st.markdown(
            """
            <div class="warning-box">
                This dashboard is read-only. It does not repair transactions
                or change financial records. Verify source records before
                proposing any correction.
            </div>
            """,
            unsafe_allow_html=True,
        )

        with st.expander("View complete evidence record"):
            st.json(row.to_dict())


# ============================================================
# 8. AUDIT TRAIL
# ============================================================

elif page == "Audit Trail":
    st.markdown(
        """
        <div class="hero">
            <div class="eyebrow">GOVERNANCE & ACCOUNTABILITY</div>
            <div class="hero-title">Approval audit trail</div>
            <div class="hero-copy">
                Review decisions recorded by the human-approval workflow.
                Approval records document decisions; they do not prove that
                a financial correction was executed.
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    if not audit_records:
        st.markdown(
            """
            <div class="panel">
                <div class="panel-title">No decisions recorded yet</div>
                <div class="section-copy">
                    Once the approval workflow saves a decision, its audit
                    record will appear here.
                </div>
            </div>
            """,
            unsafe_allow_html=True,
        )
    else:
        audit_df = pd.DataFrame(audit_records)

        a, b, c = st.columns(3)

        a.metric("Total recorded decisions", len(audit_df))

        if "approval_status" in audit_df.columns:
            b.metric(
                "Approved",
                int(audit_df["approval_status"].eq("APPROVED").sum()),
            )
            c.metric(
                "Rejected",
                int(audit_df["approval_status"].eq("REJECTED").sum()),
            )

        st.dataframe(
            audit_df,
            use_container_width=True,
            hide_index=True,
        )

        st.download_button(
            "Export audit records as CSV",
            data=audit_df.to_csv(index=False).encode("utf-8"),
            file_name="finrecon_approval_audit.csv",
            mime="text/csv",
        )


# ============================================================
# 9. SYSTEM HEALTH
# ============================================================

elif page == "System Health":
    st.markdown(
        """
        <div class="hero">
            <div class="eyebrow">PIPELINE OBSERVABILITY</div>
            <div class="hero-title">System health & data lineage</div>
            <div class="hero-copy">
                Inspect the metadata recorded by the ingestion pipeline.
                Run history and lineage help explain what was processed and
                how data moved through the system.
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    health1, health2, health3 = st.columns(3)

    health1.metric("Pipeline run records", len(pipeline_runs))
    health2.metric("Lineage records", len(lineage_records))
    health3.metric("Incident records", total)

    st.write("")

    st.markdown(
        '<div class="panel-title">Pipeline run history</div>'
        '<div class="panel-subtitle">'
        'Latest recorded run metadata, if available'
        '</div>',
        unsafe_allow_html=True,
    )

    if pipeline_runs:
        runs_df = pd.DataFrame(pipeline_runs)
        st.dataframe(
            runs_df.tail(20).iloc[::-1],
            use_container_width=True,
            hide_index=True,
        )
    else:
        st.info(
            "No pipeline run metadata file was found yet, or it contains "
            "no records."
        )

    st.write("")

    st.markdown(
        '<div class="panel-title">Data lineage</div>'
        '<div class="panel-subtitle">'
        'Recorded source-to-target processing metadata'
        '</div>',
        unsafe_allow_html=True,
    )

    if lineage_records:
        lineage_df = pd.DataFrame(lineage_records)
        st.dataframe(
            lineage_df.tail(20).iloc[::-1],
            use_container_width=True,
            hide_index=True,
        )
    else:
        st.info(
            "No lineage records were found. Check metadata/data_lineage.jsonl."
        )

    st.markdown(
        """
        <div class="insight">
            <b>Why this matters:</b> A reliable data system needs to do more
            than produce a result. It should also record what ran, what data
            moved, and whether processing succeeded or failed.
        </div>
        """,
        unsafe_allow_html=True,
    )


# ============================================================
# 10. AI INVESTIGATOR — SQL + RAG QUESTION ANSWERING
# ============================================================



# ============================================================
# 10. AI INVESTIGATOR — MCP AGENT + HUMAN APPROVAL
# ============================================================

elif page == "AI Investigator":
    render_investigator()


# ============================================================
# 11. FOOTER
# ============================================================

st.markdown(
    """
    <div class="footer">
        FINRECON AI &nbsp;·&nbsp; DATA ENGINEERING + INVESTIGATION
        <br><br>
        LOCAL PORTFOLIO APPLICATION &nbsp;·&nbsp;
        READ-ONLY FINANCIAL DATA &nbsp;·&nbsp;
        HUMAN REVIEW REQUIRED
    </div>
    """,
    unsafe_allow_html=True,
)
