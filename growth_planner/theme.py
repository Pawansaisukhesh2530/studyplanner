"""Small presentation helpers. Application rules stay in service.py."""

from html import escape
from pathlib import Path

import streamlit as st


def apply_theme():
    css = Path(__file__).with_name("styles.css").read_text(encoding="utf-8")
    st.markdown("<style>" + css + "</style>", unsafe_allow_html=True)


def brand():
    st.markdown('''<div class="gp-masthead">
      <div class="gp-brand"><span class="gp-logo" aria-hidden="true">↗</span>
      <div>Student Growth Planner<span class="gp-brand-sub">LEARNING, WITH DIRECTION</span></div></div>
      <span class="gp-masthead-note">Small steps. Meaningful growth.</span>
    </div>''', unsafe_allow_html=True)


def sidebar_profile(user):
    initials = "".join(word[0] for word in user["name"].split()[:2]).upper()
    with st.sidebar:
        st.markdown('''<div class="gp-sidebar-brand"><span class="gp-logo">↗</span>
          <div>Growth Planner<small>YOUR COLLEGE COMPANION</small></div></div>''', unsafe_allow_html=True)
        st.markdown(f'''<div class="gp-profile"><span class="gp-avatar">{escape(initials)}</span>
          <div><strong>{escape(user["name"])}</strong><span>{escape(user["role"].title())} workspace</span>
          <small>{escape(user["username"])}</small></div></div>''', unsafe_allow_html=True)


def auth_intro(setup):
    st.markdown(f'''<div class="gp-auth-intro">
      <span class="gp-eyebrow">YOUR NEXT CHAPTER STARTS HERE</span>
      <h1>A little progress.<br><span class="gp-highlight">A bigger future.</span></h1>
      <p>Make room for better learning and everything college has to offer.
      Keep your studies, plans, and campus experiences connected.</p>
      <div class="gp-auth-features">
        <div><span>01</span><section><strong>Understand your progress</strong><small>Turn academic records into a clear direction.</small></section></div>
        <div><span>02</span><section><strong>Find your people</strong><small>Explore clubs that fit your interests and time.</small></section></div>
        <div><span>03</span><section><strong>Build your own story</strong><small>Plan your work. Record what you achieve.</small></section></div>
      </div>
      <div class="gp-path" aria-hidden="true">
        <span class="gp-path-label">LEARN</span><span class="gp-path-line"></span>
        <span class="gp-path-label">PLAN</span><span class="gp-path-line"></span><span class="gp-path-label">GROW ↗</span>
      </div>
    </div>''', unsafe_allow_html=True)


def section_note(eyebrow, description):
    st.markdown(f'''<div class="gp-section-note"><span class="gp-eyebrow">{escape(eyebrow)}</span>
      <p>{escape(description)}</p></div>''', unsafe_allow_html=True)


def empty_state(title="No records yet", description="Your saved records will appear here."):
    st.markdown(f'''<div class="gp-empty"><span aria-hidden="true">＋</span>
      <div><strong>{escape(title)}</strong><p>{escape(description)}</p></div></div>''', unsafe_allow_html=True)


def status_badge(text, tone="green"):
    tone = tone if tone in ("green", "amber", "neutral") else "neutral"
    st.markdown(f'<span class="gp-badge gp-badge-{tone}">{escape(text)}</span>', unsafe_allow_html=True)


def overview_stats(items):
    for column, (label, value) in zip(st.columns(len(items)), items):
        with column:
            st.metric(label, value)


def club_heading(club, score):
    st.markdown(f'''<div class="gp-club-heading"><span class="gp-badge gp-badge-neutral">{escape(club["category"])}</span>
      <span class="gp-match">{score} <small>match points</small></span></div>''', unsafe_allow_html=True)


def submit_button(label):
    return st.form_submit_button(label, type="primary", width="stretch")
