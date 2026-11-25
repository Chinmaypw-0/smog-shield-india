import pytest
import logic as L

def test_categories():
    assert L.aqi_category(0)[0] == "good"
    assert L.aqi_category(50)[0] == "good"
    assert L.aqi_category(51)[0] == "moderate"
    assert L.aqi_category(320)[0] == "hazardous"
    with pytest.raises(ValueError):
        L.aqi_category(-1)

def test_mask_and_purifier():
    assert L.mask_exposure(100, "n95") == pytest.approx(20)
    assert L.purifier_reduction(0, 15) == 0
    assert 0.5 < L.purifier_reduction(250, 15) < 1

def test_co2():
    assert L.commute_co2_saved(10, "car", "metro") == pytest.approx(0.14 * 10 * 2 * 5)
    assert L.commute_co2_saved(10, "metro", "car") == 0

def test_best_hours():
    times = [f"2026-11-23T{h:02d}:00" for h in range(24)]
    aqi = [300 - h for h in range(24)]
    out = L.best_hours(times, aqi, "2026-11-23T08:00")
    assert [o[0][11:13] for o in out] == ["21", "20", "19"]

def test_parse():
    data = {"current": {"us_aqi": 150, "pm2_5": 60, "pm10": 90, "time": "2026-11-23T10:00"},
            "timezone_abbreviation": "GMT+5:30"}
    assert L.parse_response(data)["us_aqi"] == 150

def test_prompt_forbids_invention():
    p = L.PROFILES["Delhi commuter"]
    aq = {"us_aqi": 210, "pm2_5": 120, "pm10": 200, "time": "t", "source": L.SOURCE}
    s = L.build_prompt(p, aq, L.impact_summary(p, 120), "hi", [])
    assert "Do NOT invent" in s and "Hindi" in s


def test_parse_places_filters_and_dedupes():
    data = {"results": [
        {"name": "Dehradun", "admin1": "Uttarakhand", "latitude": 30.3, "longitude": 78.0, "country_code": "IN"},
        {"name": "Dehradun", "admin1": "Uttarakhand", "latitude": 30.3, "longitude": 78.0, "country_code": "IN"},
        {"name": "Dehradun", "admin1": "Elsewhere", "latitude": 1, "longitude": 2, "country_code": "US"}]}
    out = L.parse_places(data)
    assert len(out) == 1 and out[0]["label"] == "Dehradun, Uttarakhand"
    assert L.parse_places({}) == []


def _err(code):
    e = RuntimeError(str(code)); e.code = code; return e

def test_fallback_next_model_and_retry_rounds():
    calls = []
    def fake(prompt, key, model):
        calls.append(model)
        if len(calls) < 4:
            raise _err(503)
        return "plan"
    used, sleeps = {}, []
    out = L.plan_with_fallback("p", "k", ["a", "b"], used, call=fake, sleep=sleeps.append)
    assert out == "plan" and used["model"] == "b" and sleeps == [3]   # one wait between rounds

def test_dead_models_are_dropped():
    calls = []
    def fake(prompt, key, model):
        calls.append(model)
        if model == "old":
            raise _err(404)
        raise _err(503)
    with pytest.raises(L.PlanUnavailable) as ei:
        L.plan_with_fallback("p", "k", ["old", "new"], {}, call=fake, sleep=lambda s: None)
    assert calls.count("old") == 1 and calls.count("new") == 2
    assert ("old", "RuntimeError 404") in ei.value.skipped

def test_all_dead_stops_immediately():
    def fake(prompt, key, model):
        raise _err(404)
    with pytest.raises(L.PlanUnavailable):
        L.plan_with_fallback("p", "k", ["a"], {}, call=fake, sleep=lambda s: pytest.fail("should not wait"))

def test_pick_swap():
    assert L.pick_swap("car", 10) == "metro"
    assert L.pick_swap("car", 80) == "bus"
    assert L.pick_swap("metro", 3) == "cycle_walk"

def test_asthma_long_trip_and_language_rules():
    p = dict(L.PROFILES["Mumbai family with toddlers"], asthma=True, km=80)
    aq = {"us_aqi": 120, "pm2_5": 40, "pm10": 60, "time": "2026-11-23T10:00", "source": L.SOURCE}
    s = L.build_prompt(p, aq, L.impact_summary(p, 40, L.pick_swap(p["mode"], p["km"])), "hi", [])
    assert "HEALTH PRIORITY" in s and "LONG COMMUTE" in s
    assert "CO2 per week" not in s                 # no CO2 saving fact for 80 km
    assert "यह क्यों मदद करता है:" in s and 'Why it helps:' not in s
    p2 = dict(p, asthma=False, km=10)
    s2 = L.build_prompt(p2, aq, L.impact_summary(p2, 40), "en", [])
    assert "HEALTH PRIORITY" not in s2 and "Why it helps:" in s2


def test_prompt_is_plain_english_and_formats_time():
    p = dict(L.PROFILES["Delhi commuter"], asthma=True, purifier_cadr=250, mask="n95")
    aq = {"us_aqi": 185, "pm2_5": 68, "pm10": 68.5, "time": "2026-11-23T10:00", "source": L.SOURCE}
    best = [("2026-11-24T21:00", 31), ("2026-11-24T20:00", 32)]
    s = L.build_prompt(p, aq, L.impact_summary(p, 68), "en", best)
    for raw in ("n95_extra_cut_pct", "purifier_cut_pct", "co2_week_kg", "swap_to", "T21:00"):
        assert raw not in s
    assert "9 PM tomorrow" in s
    assert "already wears an N95" in s
    assert "LEAD with timing" in s


def test_fmt_hour():
    assert L.fmt_hour("2026-11-23T00:00", "2026-11-23T10:00") == "12 AM today"
    assert L.fmt_hour("2026-11-24T12:00", "2026-11-23T10:00") == "12 PM tomorrow"


def test_no_snake_case_words_in_prompt():
    p = L.PROFILES["Kolkata gig worker"]
    aq = {"us_aqi": 250, "pm2_5": 150, "pm10": 200, "time": "2026-11-23T10:00", "source": L.SOURCE}
    s = L.build_prompt(p, aq, L.impact_summary(p, 150), "en", [])
    for raw in ("two_wheeler", "gig_worker", "very_unhealthy", "young_children"):
        assert raw not in s


def test_hindi_prompt_has_no_english_phrases_to_copy():
    p = L.PROFILES["Delhi commuter"]
    aq = {"us_aqi": 177, "pm2_5": 60, "pm10": 80, "time": "2026-11-23T10:00", "source": L.SOURCE}
    imp = L.impact_summary(p, 60, "metro")
    hi = L.build_prompt(p, aq, imp, "hi", [("2026-11-24T21:00", 40)])
    assert "सप्ताह में 5 दिन मानकर" in hi and "किमी" in hi and "कल रात 9 बजे" in hi
    assert "5-day week" not in hi
    en = L.build_prompt(p, aq, imp, "en", [])
    assert "assuming a 5-day week" in en and "किमी" not in en


def _fake_genai(monkeypatch, behaviour):
    """Install a fake google.genai so generate_text can be tested offline."""
    import sys, types as T
    class Cfg:
        def __init__(self, **kw): self.__dict__.update(kw)
    class Resp:
        def __init__(self, text, fr="STOP"):
            self.text = text; self.candidates = [T.SimpleNamespace(finish_reason=fr)]
    class Models:
        def generate_content(self, model, contents, config=None):
            return behaviour(config, Resp)
    class Client:
        def __init__(self, api_key): self.models = Models()
    types_m = T.ModuleType("google.genai.types")
    types_m.GenerateContentConfig = Cfg
    types_m.ThinkingConfig = Cfg
    genai_m = T.ModuleType("google.genai"); genai_m.Client = Client; genai_m.types = types_m
    google_m = T.ModuleType("google"); google_m.genai = genai_m
    for n, m in (("google", google_m), ("google.genai", genai_m), ("google.genai.types", types_m)):
        monkeypatch.setitem(sys.modules, n, m)

def test_generate_text_falls_back_on_400(monkeypatch):
    def behaviour(cfg, Resp):
        if cfg is not None and hasattr(cfg, "thinking_config"):
            raise _err(400)
        return Resp("full plan")
    _fake_genai(monkeypatch, behaviour)
    assert L.generate_text("p", "k", "m") == "full plan"

def test_generate_text_rejects_truncated_plan(monkeypatch):
    _fake_genai(monkeypatch, lambda cfg, Resp: Resp("half a pl", fr="FinishReason.MAX_TOKENS"))
    with pytest.raises(L.Truncated):
        L.generate_text("p", "k", "m")

def test_unit_is_micrograms_not_ug():
    p = L.PROFILES["Delhi commuter"]
    aq = {"us_aqi": 150, "pm2_5": 60, "pm10": 80, "time": "2026-11-23T10:00", "source": L.SOURCE}
    s = L.build_prompt(p, aq, L.impact_summary(p, 60), "en", [])
    data_line = next(x for x in s.splitlines() if x.startswith("LIVE DATA"))
    assert "µg/m3" in data_line and "ug/m3" not in data_line.replace("µg/m3", "")


def test_long_commute_swap_section_is_not_commute_or_mask():
    p = dict(L.PROFILES["Delhi commuter"], km=60)
    aq = {"us_aqi": 150, "pm2_5": 60, "pm10": 80, "time": "2026-11-23T10:00", "source": L.SOURCE}
    s = L.build_prompt(p, aq, L.impact_summary(p, 60, L.pick_swap(p["mode"], p["km"])), "en", [])
    assert "section 4" in s and "pick a home habit" in s
    short = L.build_prompt(dict(p, km=10), aq, L.impact_summary(dict(p, km=10), 60), "en", [])
    assert "pick a home habit" not in short


def test_prompt_forbids_repeated_advice_between_sections():
    p = L.PROFILES["Delhi commuter"]
    aq = {"us_aqi": 150, "pm2_5": 60, "pm10": 80, "time": "2026-11-23T10:00", "source": L.SOURCE}
    s = L.build_prompt(p, aq, L.impact_summary(p, 60), "en", [])
    assert "Never repeat a tip from an earlier section" in s


def test_success_lists_each_failed_model_once_and_records_finish():
    n = {"i": 0}
    def fake(prompt, key, model):
        n["i"] += 1
        if n["i"] < 5:
            raise _err(503)
        out = L.PlanText("plan"); out.finish = "STOP"; return out
    used = {}
    out = L.plan_with_fallback("p", "k", ["a", "b"], used, call=fake, sleep=lambda s: None, rounds=3)
    assert out == "plan" and type(out) is str
    assert used["finish"] == "STOP"
    assert used["skipped"] == [("a", "RuntimeError 503"), ("b", "RuntimeError 503")]


def test_generate_text_reports_finish_reason(monkeypatch):
    _fake_genai(monkeypatch, lambda cfg, Resp: Resp("done", fr="FinishReason.STOP"))
    assert L.generate_text("p", "k", "m").finish == "STOP"


def test_quota_429_is_not_retried_for_that_model():
    calls = []
    def fake(prompt, key, model):
        calls.append(model)
        if model == "big":
            raise _err(429)
        raise _err(503)
    with pytest.raises(L.PlanUnavailable):
        L.plan_with_fallback("p", "k", ["big", "lite"], {}, call=fake, sleep=lambda s: None)
    assert calls.count("big") == 1 and calls.count("lite") == 2
def test_offline_plan_is_complete_and_follows_rules():
    
    aq = {"us_aqi": 160, "pm2_5": 70.0, "time": "2026-11-25T15:30"}
    best = [("2026-11-25T16:00", 150)]

    def plan(profile_name, lang):
        p = L.PROFILES[profile_name]
        imp = L.impact_summary(p, aq["pm2_5"], L.pick_swap(p["mode"], p["km"]))
        return L.offline_plan(p, aq, imp, lang, best)

    for lang in ("en", "hi"):
        text = plan("Bengaluru senior citizen", lang)
        assert text.count("**") == 10                      # five headings
        assert "_" not in text                             # no field names leak
    assert "asthma" in plan("Bengaluru senior citizen", "en").lower()
    assert "अस्थमा" in plan("Bengaluru senior citizen", "hi")
    assert "CO2" not in plan("Kolkata gig worker", "en")   # 60 km: no CO2 swap advice