import sys, os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../..")))

import streamlit as st

from src.agent.orchestrator import AgentOrchestrator, AgentResult
from src.agent.tools import ReasoningStep

# ── Page config ───────────────────────────────────────────────────────────────

st.set_page_config(page_title="TuneFit 2.0", layout="wide", page_icon="🎵")

# ── Global CSS ────────────────────────────────────────────────────────────────

st.markdown("""
<style>
  @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700;800&display=swap');

  :root {
    --accent:        #f5a623;
    --accent-soft:   rgba(245, 166, 35, 0.12);
    --accent-border: rgba(245, 166, 35, 0.28);
    --radius:        14px;
  }

  /* Typography */
  html, body, [class*="css"], .stMarkdown, p, li {
    font-family: 'Inter', -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif !important;
  }

  /* ── Song card ───────────────────────────────────────────── */
  .song-card {
    background: var(--secondary-background-color);
    border: 1px solid var(--accent-border);
    border-radius: var(--radius);
    padding: 18px 20px 14px;
    margin-bottom: 10px;
    position: relative;
    overflow: hidden;
    transition: box-shadow 0.2s ease;
  }
  .song-card::before {
    content: '';
    position: absolute;
    inset: 0 auto 0 0;
    width: 3px;
    background: linear-gradient(180deg, var(--accent) 0%, transparent 100%);
    border-radius: 99px 0 0 99px;
  }

  .card-header {
    display: flex;
    align-items: flex-start;
    gap: 14px;
  }
  .rank-num {
    font-size: 2rem;
    font-weight: 800;
    color: var(--accent);
    opacity: 0.18;
    line-height: 1;
    min-width: 38px;
    letter-spacing: -1px;
    font-family: 'Inter', sans-serif;
    user-select: none;
  }
  .song-info { flex: 1; min-width: 0; }
  .song-title {
    font-size: 1rem;
    font-weight: 600;
    color: var(--text-color);
    margin: 0 0 3px;
    white-space: nowrap;
    overflow: hidden;
    text-overflow: ellipsis;
  }
  .song-artist {
    font-size: 0.83rem;
    color: var(--text-color);
    opacity: 0.5;
    margin-bottom: 9px;
  }

  /* ── Tags ────────────────────────────────────────────────── */
  .tag {
    display: inline-block;
    background: var(--accent-soft);
    border: 1px solid var(--accent-border);
    color: var(--accent);
    border-radius: 99px;
    padding: 2px 11px;
    font-size: 0.71rem;
    font-weight: 600;
    margin-right: 5px;
    letter-spacing: 0.4px;
    text-transform: capitalize;
  }

  /* ── Score bar ───────────────────────────────────────────── */
  .score-bar-wrap { margin: 12px 0 6px; }
  .score-bar-track {
    background: rgba(128, 128, 128, 0.15);
    border-radius: 99px;
    height: 5px;
    overflow: hidden;
  }
  .score-bar-fill {
    height: 100%;
    border-radius: 99px;
    background: linear-gradient(90deg, var(--accent) 0%, #ffd166 100%);
  }

  /* ── Score meta row ──────────────────────────────────────── */
  .score-meta {
    display: flex;
    justify-content: space-between;
    align-items: baseline;
    gap: 12px;
    margin-top: 4px;
  }
  .score-breakdown {
    font-family: 'Courier New', monospace;
    font-size: 0.7rem;
    color: var(--text-color);
    opacity: 0.4;
    flex: 1;
    overflow: hidden;
    white-space: nowrap;
    text-overflow: ellipsis;
  }
  .score-total {
    font-family: 'Courier New', monospace;
    font-size: 0.82rem;
    font-weight: 600;
    color: var(--accent);
    white-space: nowrap;
  }

  /* ── Confidence badge ────────────────────────────────────── */
  .conf-badge {
    display: inline-flex;
    align-items: center;
    gap: 7px;
    padding: 5px 14px;
    border-radius: 99px;
    font-size: 0.8rem;
    font-weight: 600;
    border: 1px solid;
    margin-top: 4px;
    letter-spacing: 0.2px;
  }
  .conf-high   { background: rgba(34,197,94,0.1);  border-color: rgba(34,197,94,0.3);  color: #22c55e; }
  .conf-medium { background: rgba(245,158,11,0.1); border-color: rgba(245,158,11,0.3); color: #f59e0b; }
  .conf-low    { background: rgba(239,68,68,0.1);  border-color: rgba(239,68,68,0.3);  color: #ef4444; }

  /* ── Section heading ─────────────────────────────────────── */
  .section-heading {
    display: flex;
    align-items: center;
    gap: 10px;
    margin: 20px 0 14px;
    font-size: 0.78rem;
    font-weight: 700;
    letter-spacing: 1.2px;
    text-transform: uppercase;
    color: var(--text-color);
    opacity: 0.5;
  }
  .section-heading::after {
    content: '';
    flex: 1;
    height: 1px;
    background: linear-gradient(90deg, var(--accent-border), transparent);
  }

  /* ── Reasoning block ─────────────────────────────────────── */
  .reasoning-block {
    font-family: 'Courier New', monospace;
    font-size: 0.77rem;
    line-height: 1.75;
    white-space: pre-wrap;
    background: var(--secondary-background-color);
    border-left: 2px solid var(--accent-border);
    border-radius: 0 8px 8px 0;
    padding: 10px 16px;
    margin-bottom: 8px;
    color: var(--text-color);
    opacity: 0.75;
  }
  .reasoning-tool {
    color: var(--accent);
    font-weight: 700;
    opacity: 1;
  }

  /* ── Sidebar brand ───────────────────────────────────────── */
  .sidebar-logo {
    font-size: 1.35rem;
    font-weight: 800;
    letter-spacing: -0.5px;
    line-height: 1;
    color: var(--accent) !important;
  }
  .sidebar-sub {
    font-size: 0.7rem;
    font-weight: 600;
    letter-spacing: 1.8px;
    text-transform: uppercase;
    color: var(--text-color);
    opacity: 0.4;
    margin-top: 4px;
  }

  /* ── Status pill ─────────────────────────────────────────── */
  .status-pill {
    display: inline-flex;
    align-items: center;
    gap: 6px;
    padding: 5px 13px;
    border-radius: 99px;
    font-size: 0.76rem;
    font-weight: 500;
    background: var(--secondary-background-color);
    border: 1px solid rgba(128,128,128,0.2);
  }
</style>
""", unsafe_allow_html=True)

# ── Session state ─────────────────────────────────────────────────────────────

if "orchestrator" not in st.session_state:
    st.session_state["orchestrator"] = AgentOrchestrator()

if "llm_ok" not in st.session_state:
    st.session_state["llm_ok"] = st.session_state["orchestrator"].llm.health_check()

if "messages" not in st.session_state:
    st.session_state["messages"] = []

# ── Sidebar ───────────────────────────────────────────────────────────────────

with st.sidebar:
    st.markdown("""
<div class="sidebar-logo">🎵 TuneFit 2.0</div>
<div class="sidebar-sub">Agentic Music Recommender</div>
""", unsafe_allow_html=True)
    st.markdown("---")

    if st.session_state["llm_ok"]:
        st.markdown('<div class="status-pill">🟢 &nbsp;Groq connected</div>',
                    unsafe_allow_html=True)
    else:
        st.markdown('<div class="status-pill">🔴 &nbsp;LLM unavailable</div>',
                    unsafe_allow_html=True)

    st.markdown("---")

    with st.expander("How it works"):
        st.markdown("""
1. **Interprets your request** using an LLM to extract music preferences
2. **Scores all 18 songs** against your preferences using the scoring engine
3. **Evaluates confidence** and flags weak or conflicting matches
4. **Generates a natural language summary** of the top recommendations
        """)

# ── Helpers ───────────────────────────────────────────────────────────────────

def _confidence_indicator(quality: str) -> str:
    return {"high": "🟢 High confidence", "medium": "🟡 Medium confidence"}.get(
        quality, "🔴 Low confidence"
    )


def render_result(result: AgentResult) -> None:
    if result.error:
        st.error(result.error)
        return

    st.markdown(result.response_text)

    st.markdown('<div class="section-heading">🎵 &nbsp;Top Recommendations</div>',
                unsafe_allow_html=True)

    for rank, scored in enumerate(result.recommendations, start=1):
        song = scored.song
        breakdown_parts = "  ·  ".join(
            f"{k.replace('_', ' ')} +{v:.1f}"
            for k, v in scored.score_breakdown.items()
        )
        pct = min(scored.total_score / 9.0 * 100, 100)

        st.markdown(f"""
<div class="song-card">
  <div class="card-header">
    <div class="rank-num">0{rank}</div>
    <div class="song-info">
      <div class="song-title">{song.title}</div>
      <div class="song-artist">{song.artist}</div>
      <span class="tag">{song.genre}</span>
      <span class="tag">{song.mood}</span>
    </div>
  </div>
  <div class="score-bar-wrap">
    <div class="score-bar-track">
      <div class="score-bar-fill" style="width:{pct:.1f}%"></div>
    </div>
  </div>
  <div class="score-meta">
    <div class="score-breakdown">{breakdown_parts}</div>
    <div class="score-total">{scored.total_score:.1f} / 9.0</div>
  </div>
</div>
""", unsafe_allow_html=True)

    quality = result.confidence.get("quality", "low")
    label = {"high": "High confidence", "medium": "Medium confidence"}.get(quality, "Low confidence")
    dot   = {"high": "🟢", "medium": "🟡"}.get(quality, "🔴")
    st.markdown(
        f'<div class="conf-badge conf-{quality}">{dot} &nbsp;{label}</div>',
        unsafe_allow_html=True,
    )
    if result.confidence.get("warning"):
        st.caption(f"_{result.confidence['warning']}_")

    st.markdown("")
    with st.expander("🔍 Agent Reasoning Steps"):
        for step in result.reasoning_steps:
            st.markdown(f"""
<div class="reasoning-block"><span class="reasoning-tool">[{step.timestamp}]  {step.tool_name.upper()}</span>
↳ In:  {step.input_summary}
↳ Out: {step.output_summary}</div>
""", unsafe_allow_html=True)


# ── Chat history ──────────────────────────────────────────────────────────────

for msg in st.session_state["messages"]:
    if msg["role"] == "user":
        with st.chat_message("user"):
            st.markdown(msg["content"])
    else:
        with st.chat_message("assistant"):
            render_result(msg["result"])

# ── Chat input ────────────────────────────────────────────────────────────────

prompt = st.chat_input("Describe what you want to listen to...")

if prompt:
    if len(prompt) > 500:
        st.warning("Message too long — truncated to 500 characters.")
        prompt = prompt[:500]

    st.session_state["messages"].append({"role": "user", "content": prompt})

    with st.chat_message("user"):
        st.markdown(prompt)

    with st.chat_message("assistant"):
        with st.spinner("🎵 Agent is thinking..."):
            result = st.session_state["orchestrator"].run(prompt)
        render_result(result)

    st.session_state["messages"].append({
        "role": "assistant",
        "content": result.response_text,
        "result": result,
    })

    st.rerun()
