"""Pure logic (no Streamlit) so it can be unit-tested."""
from __future__ import annotations
import requests

API_URL = "https://air-quality-api.open-meteo.com/v1/air-quality"
GEO_URL = "https://geocoding-api.open-meteo.com/v1/search"
SOURCE = "Open-Meteo Air Quality API (CAMS model/satellite-derived)"

CITIES = {
    "Delhi": (28.6139, 77.2090), "Mumbai": (19.0760, 72.8777),
    "Bengaluru": (12.9716, 77.5946), "Kolkata": (22.5726, 88.3639),
    "Chennai": (13.0827, 80.2707), "Hyderabad": (17.3850, 78.4867),
    "Lucknow": (26.8467, 80.9462), "Pune": (18.5204, 73.8567),
    "Ahmedabad": (23.0225, 72.5714), "Jaipur": (26.9124, 75.7873),
    "Patna": (25.5941, 85.1376), "Chandigarh": (30.7333, 76.7794),
    "Gurugram": (28.4595, 77.0266), "Noida": (28.5355, 77.3910),
}

# (upper bound, key, colour)  -- US AQI breakpoints
CATEGORIES = [
    (50, "good", "#2e7d32"), (100, "moderate", "#f9a825"),
    (150, "usg", "#ef6c00"), (200, "unhealthy", "#c62828"),
    (300, "very_unhealthy", "#6a1b9a"), (10_000, "hazardous", "#4e0d1c"),
]

# Documented assumptions (approximate, fit-adjusted real-world values)
MASK_REDUCTION = {"none": 0.0, "cloth": 0.20, "surgical": 0.30, "n95": 0.80}
CO2_KG_PER_KM = {"car": 0.17, "two_wheeler": 0.04, "auto": 0.07,
                 "bus": 0.05, "metro": 0.03, "cycle_walk": 0.0}
NATURAL_ACH = 0.5      # air changes/hour, windows closed
CEILING_M = 2.7

PROFILES = {
    "Delhi commuter": dict(city="Delhi", household="commuter", mode="two_wheeler",
        km=18, asthma=False, mask="cloth", purifier_cadr=0, room_m2=15, outdoor_min=90),
    "Mumbai family with toddlers": dict(city="Mumbai", household="young_children", mode="car",
        km=8, asthma=False, mask="none", purifier_cadr=250, room_m2=18, outdoor_min=60),
    "Bengaluru senior citizen": dict(city="Bengaluru", household="seniors", mode="auto",
        km=4, asthma=True, mask="surgical", purifier_cadr=0, room_m2=14, outdoor_min=45),
    "Lucknow student athlete": dict(city="Lucknow", household="student_athlete", mode="cycle_walk",
        km=5, asthma=False, mask="none", purifier_cadr=0, room_m2=12, outdoor_min=150),
    "Kolkata gig worker": dict(city="Kolkata", household="gig_worker", mode="two_wheeler",
        km=60, asthma=False, mask="cloth", purifier_cadr=0, room_m2=10, outdoor_min=360),
}


def aqi_category(aqi: float) -> tuple[str, str]:
    """Return (category_key, colour) for a US AQI value."""
    if aqi is None or aqi < 0:
        raise ValueError("AQI must be a non-negative number")
    for upper, key, colour in CATEGORIES:
        if aqi <= upper:
            return key, colour
    return CATEGORIES[-1][1], CATEGORIES[-1][2]


def parse_response(data: dict) -> dict:
    cur = data["current"]
    hourly = data.get("hourly", {})
    return {
        "us_aqi": cur["us_aqi"], "pm2_5": cur["pm2_5"], "pm10": cur["pm10"],
        "time": cur["time"], "tz": data.get("timezone_abbreviation", ""),
        "hourly_time": hourly.get("time", []), "hourly_aqi": hourly.get("us_aqi", []),
        "source": SOURCE,
    }


def fetch_aqi(lat: float, lon: float, timeout: int = 10) -> dict:
    """Live reading. Raises on failure -- never fabricate a value."""
    params = {"latitude": lat, "longitude": lon, "timezone": "auto",
              "current": "us_aqi,pm2_5,pm10", "hourly": "us_aqi", "forecast_days": 2}
    r = requests.get(API_URL, params=params, timeout=timeout)
    r.raise_for_status()
    return parse_response(r.json())


def best_hours(times: list[str], aqi: list, now_iso: str, start=6, end=21, n=3) -> list[tuple[str, float]]:
    """Lowest-AQI hours within the next 24h between start and end o'clock."""
    rows = [(t, a) for t, a in zip(times, aqi)
            if a is not None and t >= now_iso[:13] and start <= int(t[11:13]) <= end]
    return sorted(rows[:24], key=lambda x: x[1])[:n]


def mask_exposure(pm25: float, mask: str) -> float:
    return pm25 * (1 - MASK_REDUCTION[mask])


def purifier_reduction(cadr_m3h: float, room_m2: float) -> float:
    """Steady-state fraction of indoor PM2.5 removed: CADR / (CADR + ACH*V)."""
    if cadr_m3h <= 0:
        return 0.0
    vol = room_m2 * CEILING_M
    return cadr_m3h / (cadr_m3h + NATURAL_ACH * vol)


def commute_co2_saved(km_one_way: float, from_mode: str, to_mode: str, days_per_week=5) -> float:
    """kg CO2 saved per week by swapping modes (round trip)."""
    diff = CO2_KG_PER_KM[from_mode] - CO2_KG_PER_KM[to_mode]
    return max(0.0, diff * km_one_way * 2 * days_per_week)


def impact_summary(p: dict, pm25: float, swap_to: str = "metro") -> dict:
    cur_dose = mask_exposure(pm25, p["mask"])
    n95_dose = mask_exposure(pm25, "n95")
    return {
        "n95_extra_cut_pct": round(100 * (cur_dose - n95_dose) / cur_dose) if cur_dose else 0,
        "purifier_cut_pct": round(100 * purifier_reduction(p["purifier_cadr"], p["room_m2"])),
        "purifier_cut_pct_if_250": round(100 * purifier_reduction(250, p["room_m2"])),
        "co2_week_kg": round(commute_co2_saved(p["km"], p["mode"], swap_to), 1),
        "swap_to": swap_to,
    }


HOUSEHOLD_HINT = {
    "commuter": "Focus on the commute: timing, mode swap, mask fit, trip-combining.",
    "young_children": "Children breathe faster and are more sensitive: school/park timing, keep play indoors on bad days, clean air in their sleeping room.",
    "seniors": "Older adults are more sensitive: limit morning walks on bad days, keep medicines/inhaler handy, one clean-air room.",
    "student_athlete": "Move hard training indoors or to the cleanest hours; avoid intense exercise near traffic when AQI is high.",
    "gig_worker": "Long hours outdoors: well-fitted N95, breaks in cleaner indoor spots, routes away from heavy traffic where possible.",
}
TONE = {
    "good": "Relaxed and positive: air is fine, give a light tip or two.",
    "moderate": "Calm: only unusually sensitive people need to take care.",
    "usg": "Cautious: sensitive groups (children, seniors, asthma) should limit long outdoor time.",
    "unhealthy": "Clear and firm: everyone should reduce exposure; protect sensitive people.",
    "very_unhealthy": "Urgent: avoid outdoor exertion, use N95 outdoors, clean-air room indoors.",
    "hazardous": "Very urgent: stay indoors as much as possible, N95 if you must go out.",
}


NICE = {
    "two_wheeler": "two-wheeler", "cycle_walk": "cycling/walking", "auto": "auto-rickshaw",
    "young_children": "family with young children", "seniors": "senior citizens",
    "student_athlete": "student/athlete", "gig_worker": "delivery/gig worker", "commuter": "daily commuter",
    "usg": "unhealthy for sensitive groups", "very_unhealthy": "very unhealthy",
}


def nice(x: str) -> str:
    return NICE.get(x, x)


def fmt_hour(iso: str, now_iso: str) -> str:
    h = int(iso[11:13])
    day = "today" if iso[:10] == now_iso[:10] else "tomorrow"
    return f"{h % 12 or 12} {'AM' if h < 12 else 'PM'} {day}"


def plain_facts(p: dict, impact: dict, hi: bool = False) -> list[str]:
    """Estimates as plain sentences (no variable names reach the model)."""
    week = "सप्ताह में 5 दिन मानकर" if hi else "assuming a 5-day week"
    facts = []
    if p["mask"] == "n95":
        facts.append("The person already wears an N95, so there is no extra mask benefit; only stress a tight fit and replacing it when worn out.")
    else:
        facts.append(f"Switching from a {p['mask']} mask to an N95 would cut roughly {impact['n95_extra_cut_pct']}% of the fine particles they breathe in outdoors (estimate).")
    if p["purifier_cadr"] > 0:
        facts.append(f"Their purifier (rated {p['purifier_cadr']} m3/h) removes roughly {impact['purifier_cut_pct']}% of indoor PM2.5 in a {p['room_m2']} m2 room with windows closed (estimate).")
    else:
        facts.append(f"They have no purifier; a 250 m3/h unit would cut roughly {impact['purifier_cut_pct_if_250']}% of indoor PM2.5 in a {p['room_m2']} m2 room (estimate).")
    if p["km"] > LONG_TRIP_KM:
        pass
    elif impact["co2_week_kg"] > 0:
        facts.append(f"Switching a {p['km']} km one-way commute from {nice(p['mode'])} to {nice(impact['swap_to'])} saves about {impact['co2_week_kg']} kg CO2 per week (estimate, {week}).")
    else:
        facts.append(f"Their commute mode ({nice(p['mode'])}) is already low-emission; do not suggest a swap for CO2 reasons.")
    return facts


LONG_TRIP_KM = 40


def pick_swap(mode: str, km: float) -> str:
    """A realistic mode to compare against (no metro for very long trips)."""
    if mode == "metro":
        return "cycle_walk" if km <= 5 else "metro"
    return "metro" if km <= LONG_TRIP_KM else "bus"


def build_prompt(p: dict, aq: dict, impact: dict, lang: str, best: list) -> str:
    cat, _ = aqi_category(aq["us_aqi"])
    hi = lang == "hi"
    language = "Hindi (Devanagari script)" if hi else "English"
    why = "यह क्यों मदद करता है:" if hi else "Why it helps:"
    week = "सप्ताह में 5 दिन मानकर" if hi else "assuming a 5-day week"
    hours = ", ".join(f"{fmt_hour(t, aq['time'])} (AQI {a})" for t, a in best) or "not available"
    timing_first = bool(best) and best[0][1] <= aq["us_aqi"] - 20
    facts = "\n".join(f"- {f}" for f in plain_facts(p, impact, hi))
    extra = []
    if p["asthma"]:
        extra.append("HEALTH PRIORITY: someone in this household has asthma or a respiratory condition. Mention asthma by name "
                     "in section 1 and in section 5, and make the first recommendation address it (mask fit, keeping the "
                     "inhaler/medicines handy, when to stay indoors), together with the household focus.")
    if p["km"] > LONG_TRIP_KM:
        extra.append(f"LONG COMMUTE: {p['km']} km one way is too far for a whole-trip swap. Do NOT suggest metro, cycling or "
                     "walking for the full trip and do NOT mention CO2 savings; suggest cleaner hours, an N95, carpooling or "
                     "combining trips instead. For section 4 (Sustainable swap) do NOT use carpooling, trip-combining, travel timing "
                     "or masks, because sections 2 and 3 already cover them; pick a home habit instead, such as "
                     "using the kitchen exhaust while cooking, not burning waste or incense indoors, or damp-mopping "
                     "instead of dry sweeping.")
    if timing_first:
        extra.append("LEAD with timing: the air is much cleaner at the cleanest hours than right now, so tell them to move "
                     "outdoor trips and exercise to those hours.")
    if hi:
        extra.append(f'LANGUAGE: write EVERY word in Hindi, including section headings and the label "{why}". '
                     'Write units in Hindi: km as किमी, kg as किग्रा, minutes as मिनट, hours as घंटे; '
                     'write times the Hindi way (for example "9 PM tomorrow" as "कल रात 9 बजे"). '
                     'Only names such as N95, PM2.5, AQI and the units µg/m3 and m3/h stay in Latin letters.')
    extra_text = "\n".join(extra)
    return f"""You are a friendly urban air-quality assistant for Indian families. Write in {language}.

LIVE DATA ({aq['source']}, observed {aq['time']} local): US AQI {aq['us_aqi']} ({nice(cat)}), PM2.5 {aq['pm2_5']} µg/m3, PM10 {aq['pm10']} µg/m3.
Cleanest hours in the next 24h: {hours}.
PERSON: city {p['city']}; household type {nice(p['household'])}; commute {p['km']} km one way by {nice(p['mode'])}; respiratory condition: {'yes' if p['asthma'] else 'no'}; {p['outdoor_min']} minutes outdoors per day.
ESTIMATES YOU MAY USE (always call them estimates):
{facts}

TONE: {TONE[cat]}
HOUSEHOLD FOCUS: {HOUSEHOLD_HINT.get(p['household'], '')}
{extra_text}

RULES
- Use ONLY the numbers above. Do NOT invent or guess any AQI, PM or percentage.
- Use only details given about this person. Do not invent roads, routes, vehicle types, number of days or schedules; if you mention a work week say "{week}".
- Plain, warm language. Never show field names, underscores, code-style labels or raw timestamps; say "9 PM tomorrow", not an ISO date.
- In section 1, give the current PM2.5 reading once, in plain words, to explain why the advice is what it is. Do not repeat any other number twice.
- Every recommendation must be followed by "{why}" giving a real reason (what physically changes), not a restatement of the advice. Use an estimate there only when it fits.
- Each section must give different advice. Never repeat a tip from an earlier section (for example, if section 1 says to keep children indoors, section 5 must add something new).
- Write the unit micrograms per cubic metre as µg/m3, never "ug/m3".
- Be concrete and specific to this person; no generic filler. Maximum about 300 words, short bullets.

STRUCTURE
1. Right now (what to DO today, not just repeating numbers)
2. Low-emission daily routine (commute, trip-combining, timing)
3. Indoor air (purifier placement, sealing gaps, ventilate when outdoor air is cleanest, cooking exhaust; plants only as a minor extra)
4. Sustainable swap (a lower-emission or cleaner-air habit change; never a mask, and never advice already given in section 2)
5. Extra care for this household
End with one short line: general guidance, not medical advice."""


def generate_plan(prompt: str, api_key: str, model: str = "gemini-2.5-flash") -> str:
    from google import genai
    client = genai.Client(api_key=api_key)
    return client.models.generate_content(model=model, contents=prompt).text


def parse_places(data: dict) -> list[dict]:
    """Turn a geocoding response into [{label, lat, lon}], India only, de-duplicated."""
    out, seen = [], set()
    for r in data.get("results") or []:
        if r.get("country_code", "IN") != "IN":
            continue
        label = ", ".join(x for x in (r.get("name"), r.get("admin1")) if x)
        if label in seen:
            continue
        seen.add(label)
        out.append({"label": label, "lat": r["latitude"], "lon": r["longitude"]})
    return out


def search_places(query: str, timeout: int = 10) -> list[dict]:
    """Search any Indian town/city by name (Open-Meteo geocoding, no key)."""
    query = query.strip()
    if len(query) < 2:
        return []
    r = requests.get(GEO_URL, params={"name": query, "count": 8, "language": "en",
                                      "format": "json", "countryCode": "IN"}, timeout=timeout)
    r.raise_for_status()
    return parse_places(r.json())


class PlanUnavailable(Exception):
    """Every model failed on every round. `.skipped` lists (model, error) pairs."""
    def __init__(self, last: Exception, skipped: list):
        super().__init__(str(last))
        self.last, self.skipped = last, skipped


class PlanText(str):
    """The plan text, carrying the model's finish reason (STOP, MAX_TOKENS, ...)."""
    finish = None


class Truncated(RuntimeError):
    """The model hit its output limit mid-plan; never show or cache a cut-off plan."""


def generate_text(prompt: str, api_key: str, model: str) -> str:
    """Ask for low 'thinking' and a big output budget (new models count thinking against the cap).
    If a model rejects a setting (HTTP 400) or the SDK is too old, fall back to simpler settings."""
    from google import genai
    from google.genai import types
    client = genai.Client(api_key=api_key)
    tiers = [
        lambda: types.GenerateContentConfig(max_output_tokens=8192,
                                            thinking_config=types.ThinkingConfig(thinking_level="LOW")),
        lambda: types.GenerateContentConfig(max_output_tokens=8192),
        lambda: None,
    ]
    last = None
    for make in tiers:
        try:
            cfg = make()
        except Exception as e:  # noqa: BLE001  (SDK without thinking_level)
            last = e
            continue
        try:
            kw = {"config": cfg} if cfg is not None else {}
            r = client.models.generate_content(model=model, contents=prompt, **kw)
        except Exception as e:  # noqa: BLE001
            if getattr(e, "code", None) == 400:
                last = e
                continue
            raise
        if not r.text:
            raise RuntimeError("empty response")
        fr = r.candidates[0].finish_reason if getattr(r, "candidates", None) else None
        if "MAX_TOKENS" in str(fr):
            raise Truncated("plan cut off at the output limit")
        out = PlanText(r.text)
        out.finish = str(fr).split(".")[-1] if fr is not None else None
        return out
    raise last


def plan_with_fallback(prompt: str, api_key: str, models: list[str], used: dict,
                       rounds: int = 2, pauses=(3, 6), call=generate_text, sleep=None) -> str:
    """Try each model in order; if all are busy (503/429) wait and go round again.
    Models that are gone (401/403/404) or out of quota (429) are dropped for the rest of the run."""
    import time
    sleep = sleep or time.sleep
    used["skipped"] = []
    dead, last = set(), None
    for rnd in range(rounds):
        for m in models:
            if m in dead:
                continue
            try:
                text = call(prompt, api_key, m)
                used["model"] = m
                used["finish"] = getattr(text, "finish", None)
                used["skipped"] = list(dict.fromkeys(used["skipped"]))   # each failure once
                return str(text)
            except Exception as e:  # noqa: BLE001
                last = e
                code = getattr(e, "code", None)
                used["skipped"].append((m, f"{type(e).__name__} {code or ''}".strip()))
                if code in (401, 403, 404, 429):   # 429 = quota; retrying it only burns more
                    dead.add(m)
        if len(dead) == len(models):
            break
        if rnd < rounds - 1:
            sleep(pauses[min(rnd, len(pauses) - 1)])
    raise PlanUnavailable(last, list(dict.fromkeys(used["skipped"])))