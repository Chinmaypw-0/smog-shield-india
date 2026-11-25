import os
import re
from pathlib import Path
import streamlit as st
import logic as L

st.set_page_config(page_title="Smog Shield India", page_icon="🌫️", layout="wide")

T = {
 "en": dict(title="🌫️ Smog Shield India", sub="Live air quality + a personalised, explained plan for your household.",
  lang="Language", busy="Google’s AI servers are busy right now (temporary). Showing quick tips instead — click Generate again in a minute.", search="Search any Indian city/town", results="Search results", use="Use this place", searchfail="Place search unavailable right now.", noresults="No match found in India.", sample="Quick sample profile", custom="Custom", city="City", household="Household type",
  mode="Usual commute mode", km="Commute distance (km, one way)", asthma="Asthma / respiratory condition in household",
  mask="Mask you usually wear", cadr="Air purifier CADR in m³/h (0 = none)", room="Room size (m²)",
  outdoor="Minutes outdoors per day", go="Generate my plan", aqi="US AQI", src="Source", upd="Last updated",
  fail="Could not fetch live air-quality data. No numbers are shown or guessed. Please retry.",
  best="Cleanest hours to go out (next 24h)", impact="Estimated impact (assumption-based)",
  n95="Extra PM2.5 inhaled cut if you switch to N95", pur="Indoor PM2.5 cut from your purifier",
  pur250="…with a 250 m³/h purifier", co2="CO₂ saved per week if commuting by", nokey="No Gemini key configured — showing rule-based tips only.",
  disc="Estimates use simple documented assumptions (see README). General guidance, not medical advice.",
  hh=dict(commuter="Daily commuter", young_children="Family with young children", seniors="Senior citizens",
          student_athlete="Student / athlete", gig_worker="Delivery / gig worker"),
  modes=dict(car="Car", two_wheeler="Two-wheeler", auto="Auto-rickshaw", bus="Bus", metro="Metro", cycle_walk="Cycle / walk"),
  masks=dict(none="None", cloth="Cloth", surgical="Surgical", n95="N95 / FFP2"),
  cat=dict(good="Good", moderate="Moderate", usg="Unhealthy for sensitive groups", unhealthy="Unhealthy",
           very_unhealthy="Very unhealthy", hazardous="Hazardous"),
  tips={"low": "Outdoor activity is fine; ventilate rooms in the afternoon.",
        "mid": "Limit long outdoor exercise, keep windows closed at peak hours, wear a surgical mask or better.",
        "high": "Avoid outdoor exertion, use an N95 outdoors, run a purifier indoors, combine trips or use metro."}),
 "hi": dict(title="🌫️ स्मॉग शील्ड इंडिया", sub="लाइव वायु गुणवत्ता + आपके परिवार के लिए समझाई गई व्यक्तिगत योजना।",
  lang="भाषा", busy="Google के AI सर्वर अभी व्यस्त हैं (अस्थायी)। फ़िलहाल संक्षिप्त सुझाव — एक मिनट बाद फिर कोशिश करें।", search="कोई भी भारतीय शहर/कस्बा खोजें", results="खोज परिणाम", use="यह जगह चुनें", searchfail="जगह की खोज अभी उपलब्ध नहीं।", noresults="भारत में कोई मेल नहीं मिला।", sample="नमूना प्रोफ़ाइल", custom="अपना चुनें", city="शहर", household="परिवार का प्रकार",
  mode="आने-जाने का साधन", km="दूरी (किमी, एक तरफ़)", asthma="घर में अस्थमा / साँस की समस्या",
  mask="आम तौर पर मास्क", cadr="एयर प्यूरिफायर CADR (m³/h, 0 = नहीं)", room="कमरे का आकार (m²)",
  outdoor="रोज़ बाहर बिताए मिनट", go="मेरी योजना बनाएँ", aqi="US AQI", src="स्रोत", upd="अंतिम अपडेट",
  fail="लाइव वायु-गुणवत्ता डेटा नहीं मिला। कोई अनुमानित संख्या नहीं दिखाई जा रही। कृपया फिर कोशिश करें।",
  best="बाहर जाने के सबसे साफ़ घंटे (अगले 24 घंटे)", impact="अनुमानित प्रभाव (मान्यताओं पर आधारित)",
  n95="N95 पहनने पर साँस में जाने वाले PM2.5 में अतिरिक्त कमी", pur="आपके प्यूरिफायर से घर के अंदर PM2.5 में कमी",
  pur250="…250 m³/h प्यूरिफायर के साथ", co2="साप्ताहिक CO₂ बचत, यदि जाएँ", nokey="Gemini कुंजी नहीं मिली — केवल नियम-आधारित सुझाव।",
  disc="अनुमान सरल, दर्ज मान्यताओं पर आधारित हैं (README देखें)। यह सामान्य सलाह है, चिकित्सकीय सलाह नहीं।",
  hh=dict(commuter="रोज़ आने-जाने वाले", young_children="छोटे बच्चों वाला परिवार", seniors="वरिष्ठ नागरिक",
          student_athlete="छात्र / खिलाड़ी", gig_worker="डिलीवरी / गिग वर्कर"),
  modes=dict(car="कार", two_wheeler="दोपहिया", auto="ऑटो-रिक्शा", bus="बस", metro="मेट्रो", cycle_walk="साइकिल / पैदल"),
  masks=dict(none="कोई नहीं", cloth="कपड़े का", surgical="सर्जिकल", n95="N95 / FFP2"),
  cat=dict(good="अच्छा", moderate="मध्यम", usg="संवेदनशील समूहों के लिए अस्वास्थ्यकर", unhealthy="अस्वास्थ्यकर",
           very_unhealthy="बहुत अस्वास्थ्यकर", hazardous="खतरनाक"),
  tips={"low": "बाहर की गतिविधि ठीक है; दोपहर में कमरे हवादार करें।",
        "mid": "लंबी बाहरी कसरत सीमित करें, भीड़ के समय खिड़कियाँ बंद रखें, सर्जिकल या बेहतर मास्क पहनें।",
        "high": "बाहर मेहनत से बचें, बाहर N95 पहनें, घर में प्यूरिफायर चलाएँ, यात्राएँ मिलाएँ या मेट्रो लें।"}),
}

SECRETS_FILE = Path(__file__).parent / ".streamlit" / "secrets.toml"

def secret(name, default=None):
    """Look in Streamlit secrets, env vars, then the secrets file next to app.py."""
    try:
        v = st.secrets.get(name)
        if v:
            return str(v).strip()
    except Exception:
        pass
    v = os.getenv(name)
    if v:
        return v.strip()
    try:
        text = SECRETS_FILE.read_text(encoding="utf-8-sig")
        m = re.search(rf"^\s*{re.escape(name)}\s*=\s*[\"'“”‘’]([^\"'“”‘’]+)[\"'“”‘’]", text, re.M)
        if m:
            return m.group(1).strip()
    except Exception:
        pass
    return default

lang = st.sidebar.radio("Language / भाषा", ["en", "hi"], format_func=lambda x: "English" if x == "en" else "हिन्दी")
t = T[lang]
d = L.PROFILES["Delhi commuter"]
for k, v in d.items():
    st.session_state.setdefault(k, v)

def apply_sample():
    name = st.session_state.sample
    if name in L.PROFILES:
        for k, v in L.PROFILES[name].items():
            st.session_state[k] = v

st.title(t["title"]); st.caption(t["sub"])
st.sidebar.selectbox(t["sample"], ["—"] + list(L.PROFILES), key="sample", on_change=apply_sample)
ss = st.session_state
c1 = st.sidebar
ss.setdefault("places", dict(L.CITIES))
def use_place():
    ss.city = ss.pick
q = c1.text_input(t["search"], key="q")
if len(q.strip()) >= 2:
    try:
        found = L.search_places(q)
    except Exception:
        found = []
        c1.warning(t["searchfail"])
    else:
        if not found:
            c1.caption(t["noresults"])
    if found:
        for f in found:
            ss.places[f["label"]] = (f["lat"], f["lon"])
        c1.selectbox(t["results"], [f["label"] for f in found], key="pick")
        c1.button(t["use"], on_click=use_place)
c1.selectbox(t["city"], list(ss.places), key="city")
c1.selectbox(t["household"], list(t["hh"]), format_func=t["hh"].get, key="household")
c1.selectbox(t["mode"], list(t["modes"]), format_func=t["modes"].get, key="mode")
c1.slider(t["km"], 0, 80, key="km")
c1.checkbox(t["asthma"], key="asthma")
c1.selectbox(t["mask"], list(t["masks"]), format_func=t["masks"].get, key="mask")
c1.number_input(t["cadr"], 0, 1000, step=25, key="purifier_cadr")
c1.slider(t["room"], 6, 50, key="room_m2")
c1.slider(t["outdoor"], 0, 480, step=15, key="outdoor_min")
profile = {k: ss[k] for k in ["city", "household", "mode", "km", "asthma", "mask", "purifier_cadr", "room_m2", "outdoor_min"]}

@st.cache_data(ttl=600, show_spinner="…")
def get_aqi(lat, lon):
    return L.fetch_aqi(lat, lon)

try:
    aq = get_aqi(*ss.places[profile["city"]])
except Exception as e:
    st.error(t["fail"]); st.caption(f"Error: {type(e).__name__}"); st.stop()

def text_on(hex_colour):
    h = str(hex_colour).lstrip("#")
    if len(h) == 3:
        h = "".join(c * 2 for c in h)
    if len(h) != 6:
        return "#111"
    def lin(part):
        c = int(part, 16) / 255
        return c / 12.92 if c <= 0.03928 else ((c + 0.055) / 1.055) ** 2.4
    lum = 0.2126 * lin(h[0:2]) + 0.7152 * lin(h[2:4]) + 0.0722 * lin(h[4:6])
    return "#111" if (lum + 0.05) / 0.05 > 1.05 / (lum + 0.05) else "#fff"
cat, colour = L.aqi_category(aq["us_aqi"])
a, b, c = st.columns(3)
a.metric(t["aqi"], round(aq["us_aqi"])); b.metric("PM2.5 µg/m³", aq["pm2_5"]); c.metric("PM10 µg/m³", aq["pm10"])
st.markdown(f"<div role='status' style='padding:.6rem 1rem;border-radius:8px;background:{colour};color:{text_on(colour)};"
            f"font-weight:600'>{t['cat'][cat]}</div>", unsafe_allow_html=True)
st.caption(f"{t['src']}: {aq['source']} · {t['upd']}: {aq['time']} {aq['tz']}")

best = L.best_hours(aq["hourly_time"], aq["hourly_aqi"], aq["time"])
if best:
    st.write(f"**{t['best']}:** " + ", ".join(f"{h[11:16]} (AQI {round(v)})" for h, v in best))

swap = L.pick_swap(profile["mode"], profile["km"])
imp = L.impact_summary(profile, aq["pm2_5"], swap)
st.subheader(t["impact"])
show_co2 = imp["co2_week_kg"] > 0 and profile["km"] <= L.LONG_TRIP_KM
cols = st.columns(3 if show_co2 else 2)
cols[0].metric(t["n95"], f"{imp['n95_extra_cut_pct']}%")
cols[1].metric(t["pur"], f"{imp['purifier_cut_pct']}%", help=f"{t['pur250']}: {imp['purifier_cut_pct_if_250']}%")
if show_co2:
    cols[2].metric(f"{t['co2']} {t['modes'][swap]}", f"{imp['co2_week_kg']} kg")
st.caption(t["disc"])

@st.cache_data(ttl=1800, show_spinner=False)
def make_plan(prompt, models, _key):
    used = {}
    text = L.plan_with_fallback(prompt, _key, list(models), used)
    return text, used

def show_offline():
    st.markdown(L.offline_plan(profile, aq, imp, lang, [(h, round(v)) for h, v in best]))

if st.button(t["go"], type="primary"):
    key = secret("GEMINI_API_KEY")
    if not key:
        st.info(t["nokey"])
        st.caption(f"Looked for GEMINI_API_KEY in: {SECRETS_FILE} (file exists: {SECRETS_FILE.exists()})")
        show_offline()
    else:
        with st.spinner("…"):
            try:
                prompt = L.build_prompt(profile, aq, imp, lang, [(h, round(v)) for h, v in best])
                primary = secret("GEMINI_MODEL", "gemini-3.5-flash-lite")
                # free tier: the two Lite models allow 500 requests/day, the others only 20/day, so Lite goes first
                chain = list(dict.fromkeys([primary, "gemini-3.5-flash-lite", "gemini-3.1-flash-lite",
                                            "gemini-3.8-flash", "gemini-3.6-flash", "gemini-3.5-flash"]))
                text, used = make_plan(prompt, tuple(chain), key)
                st.markdown(text)
                skipped = ", ".join(f"{m} ({e})" for m, e in used["skipped"])
                st.caption(f"Generated by {used.get('model')}" + (f" · finish: {used['finish']}" if used.get("finish") else "")
                           + (f" · skipped: {skipped}" if skipped else ""))
            except L.PlanUnavailable as e:
                busy = all("503" in err or "429" in err for _, err in e.skipped)
                st.warning(t["busy"] if busy else f"AI plan unavailable: {str(e)[:250]}".replace(key, "***"))
                st.caption("Tried: " + ", ".join(f"{m} ({err})" for m, err in e.skipped))
                show_offline()
            except Exception as e:
                st.warning(f"AI plan unavailable ({type(e).__name__}).")
                show_offline()