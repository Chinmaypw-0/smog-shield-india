"""Smog Shield India: Streamlit interface (English and Hindi).

All calculations live in logic.py and all interface text in translations.py.
"""
import os

import streamlit as st

import logic as L
from translations import TEXT

st.set_page_config(page_title="Smog Shield India", page_icon="🌫️", layout="wide")

PROFILE_KEYS = ["city", "household", "mode", "km", "asthma", "mask", "purifier_cadr", "room_m2", "outdoor_min"]


def secret(name, default=None):
    """Read a setting from Streamlit secrets or the process environment."""
    try:
        value = st.secrets.get(name)
    except Exception:  # noqa: BLE001  (no secrets file: the exception type differs by Streamlit version)
        value = None
    if value is not None and str(value).strip():
        return str(value).strip()
    value = os.getenv(name)
    if value and value.strip():
        return value.strip()
    return default


@st.cache_data(ttl=600, show_spinner=False)
def search_places_cached(query):
    """Place search, cached for 10 minutes so typing in the box does not repeat network calls."""
    return L.search_places(query)


@st.cache_data(ttl=600, show_spinner=False)
def get_aqi(lat, lon):
    """Live air quality, cached for 10 minutes."""
    return L.fetch_aqi(lat, lon)


@st.cache_data(ttl=1800, show_spinner=False)
def make_plan(prompt, models, _key):
    """Gemini plan, cached for 30 minutes. The key is excluded from the cache key."""
    used = {}
    text = L.plan_with_fallback(prompt, _key, list(models), used)
    return text, used


def apply_sample():
    """Copy the chosen sample profile into the sidebar widgets."""
    name = st.session_state.sample
    if name in L.PROFILES:
        for key, value in L.PROFILES[name].items():
            st.session_state[key] = value


def use_place():
    """Make the place picked in the search results the selected city."""
    st.session_state.city = st.session_state.pick


def restore_after_language_switch(lang):
    """Older Streamlit resets widgets whose label changed; put the person's choices back."""
    previous = st.session_state.get("_lang_prev")
    if previous not in (None, lang):
        for key, value in st.session_state.get("_keep", {}).items():
            st.session_state[key] = value
    st.session_state["_lang_prev"] = lang


def sidebar_inputs(t):
    """Draw the sidebar and return the person's profile as a dict."""
    ss = st.session_state
    side = st.sidebar
    side.selectbox(t["sample"], ["—"] + list(L.PROFILES), key="sample", on_change=apply_sample)
    ss.setdefault("places", dict(L.CITIES))
    query = side.text_input(t["search"], key="q")
    if len(query.strip()) >= 2:
        try:
            found = search_places_cached(query.strip())
        except Exception:  # noqa: BLE001  (network or geocoder problem)
            found = []
            side.warning(t["searchfail"])
        else:
            if not found:
                side.caption(t["noresults"])
        if found:
            for place in found:
                ss.places[place["label"]] = (place["lat"], place["lon"])
            side.selectbox(t["results"], [place["label"] for place in found], key="pick")
            side.button(t["use"], on_click=use_place)
    side.selectbox(t["city"], list(ss.places), key="city")
    side.selectbox(t["household"], list(t["hh"]), format_func=t["hh"].get, key="household")
    side.selectbox(t["mode"], list(t["modes"]), format_func=t["modes"].get, key="mode")
    side.slider(t["km"], 0, 80, key="km")
    side.checkbox(t["asthma"], key="asthma")
    side.selectbox(t["mask"], list(t["masks"]), format_func=t["masks"].get, key="mask")
    side.number_input(t["cadr"], 0, 1000, step=25, key="purifier_cadr")
    side.slider(t["room"], 6, 50, key="room_m2")
    side.slider(t["outdoor"], 0, 480, step=15, key="outdoor_min")
    profile = {key: ss[key] for key in PROFILE_KEYS}
    ss["_keep"] = dict(profile)
    return profile


def show_air_quality(t, aq):
    """Headline numbers, coloured category banner and source line."""
    cat, colour = L.aqi_category(aq["us_aqi"])
    col_aqi, col_pm25, col_pm10 = st.columns(3)
    col_aqi.metric(t["aqi"], round(aq["us_aqi"]))
    col_pm25.metric("PM2.5 µg/m³", aq["pm2_5"])
    col_pm10.metric("PM10 µg/m³", aq["pm10"])
    st.markdown(f"<div role='status' style='padding:.6rem 1rem;border-radius:8px;background:{colour};"
                f"color:{L.text_colour_for(colour)};font-weight:600'>{t['cat'][cat]}</div>",
                unsafe_allow_html=True)
    st.caption(f"{t['src']}: {aq['source']} · {t['upd']}: {aq['time']} {aq['tz']}")


def show_impact(t, profile, aq, swap):
    """The three estimate cards; the CO2 card only appears when a swap makes sense."""
    imp = L.impact_summary(profile, aq["pm2_5"], swap)
    st.subheader(t["impact"])
    show_co2 = imp["co2_week_kg"] > 0 and profile["km"] <= L.LONG_TRIP_KM
    cols = st.columns(3 if show_co2 else 2)
    cols[0].metric(t["n95"], f"{imp['n95_extra_cut_pct']}%")
    cols[1].metric(t["pur"], f"{imp['purifier_cut_pct']}%", help=f"{t['pur250']}: {imp['purifier_cut_pct_if_250']}%")
    if show_co2:
        cols[2].metric(f"{t['co2']} {t['modes'][swap]}", f"{imp['co2_week_kg']} kg")
    st.caption(t["disc"])
    return imp


def show_plan(t, lang, profile, aq, imp, best):
    """Generate and show the plan: Gemini when a key is set, rule-based tips otherwise or on failure."""
    def show_offline():
        st.markdown(L.offline_plan(profile, aq, imp, lang, best))

    key = secret("GEMINI_API_KEY")
    if not key:
        st.info(t["nokey"])
        show_offline()
        return
    with st.spinner(t["generating"]):
        try:
            prompt = L.build_prompt(profile, aq, imp, lang, best)
            chain = L.model_chain(secret("GEMINI_MODEL", L.DEFAULT_MODEL))
            text, used = make_plan(prompt, tuple(chain), key)
            st.markdown(text)
            st.caption(L.describe_model_use(used))
        except L.PlanUnavailable as err:
            busy = all("503" in why or "429" in why for _, why in err.skipped)
            st.warning(t["busy"] if busy else f"AI plan unavailable: {str(err)[:250]}".replace(key, "***"))
            st.caption("Tried: " + ", ".join(f"{m} ({why})" for m, why in err.skipped))
            show_offline()
        except Exception as err:  # noqa: BLE001
            st.warning(f"AI plan unavailable ({type(err).__name__}).")
            show_offline()


def main():
    lang = st.sidebar.radio("Language / भाषा", ["en", "hi"], format_func=lambda x: "English" if x == "en" else "हिन्दी")
    t = TEXT[lang]
    for key, value in L.PROFILES["Delhi commuter"].items():
        st.session_state.setdefault(key, value)
    restore_after_language_switch(lang)

    st.title(t["title"])
    st.caption(t["sub"])
    profile = sidebar_inputs(t)

    try:
        with st.spinner(t["loading"]):
            aq = get_aqi(*st.session_state.places[profile["city"]])
    except Exception as err:  # noqa: BLE001
        st.error(t["fail"])
        st.caption(f"Error: {type(err).__name__}")
        st.stop()

    show_air_quality(t, aq)
    best = L.best_hours(aq["hourly_time"], aq["hourly_aqi"], aq["time"])
    if best:
        st.write(f"**{t['best']}:** " + ", ".join(f"{h[11:16]} (AQI {round(v)})" for h, v in best))
    imp = show_impact(t, profile, aq, L.pick_swap(profile["mode"], profile["km"]))

    if st.button(t["go"], type="primary"):
        show_plan(t, lang, profile, aq, imp, [(h, round(v)) for h, v in best])


main()