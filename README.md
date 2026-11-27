# 🌫️ Smog Shield India

Live air quality for any Indian city or town, plus a personalised, explained plan for your household, in English or Hindi.

**Live app:** [smog-shield-india on Streamlit](https://smog-shield-india-c8wwved3b68vtcze5ugaca.streamlit.app/)

## Chosen vertical and approach

**Vertical:** Environmental health, focused on severe winter smog and urban air pollution.

The assistant combines a live air-quality forecast with a household's location, commute, time outdoors, respiratory needs, mask, and purifier. It uses those details to recommend lower-emission routines, cleaner times to go out, and practical indoor-air changes, while showing the assumptions behind estimated benefits. Gemini explains the plan without inventing measurements; a rule-based plan remains available when the AI service is unavailable.

## What it does

1. Fetches **live** air quality (US AQI, PM2.5, PM10) for the place you choose.
2. Shows the **source and the last-updated time** next to the numbers.
3. Shows the **three cleanest hours** to go out in the next 24 hours (between 6 AM and 9 PM).
4. Shows **estimated impact** cards: switching to an N95, your purifier, and CO₂ saved by a cleaner commute.
5. Generates a **personalised plan** with Gemini. Every recommendation comes with a "why it helps" reason.

Personalisation inputs: household type (daily commuter, family with young children, senior citizens, student/athlete, delivery/gig worker), asthma or respiratory condition, commute mode and distance, usual mask, purifier CADR, room size and minutes outdoors per day.

## Data source and its limits

- **Source:** [Open-Meteo Air Quality API](https://open-meteo.com/en/docs/air-quality-api), which is **CAMS model and satellite-derived** data. It is **not** a reading from a ground monitoring station (such as CPCB stations).
- The numbers are therefore **estimates for the area**, and can differ from a nearby station's reading.
- The AQI shown is the **US AQI** scale, not India's NAQI.
- Place search uses the Open-Meteo geocoding API (India only), so any town it knows can be searched.
- **No number is ever invented.** If the live data cannot be fetched, the app shows an error and no figures. The AI is given the live numbers and only explains them.
- Air-quality data is cached for 10 minutes and generated plans for 30 minutes.

## Privacy and accessibility

- The app has no account or name fields and does not save household profiles to a database.
- Choosing a place sends its coordinates to Open-Meteo. Generating an AI plan sends the selected household details and live air-quality data to Google Gemini; users can use the rule-based plan without configuring an AI key.
- The interface uses labelled Streamlit controls in English and Hindi. AQI categories are shown as text as well as color, and the status uses a screen-reader status role.

## Assumptions behind the estimates

These are simple, approximate values. They are general guidance, not medical advice.

| Item | Assumption |
|---|---|
| Mask reduction in fine particles breathed in (fit-adjusted) | none 0%, cloth 20%, surgical 30%, N95 80% |
| "Extra cut if you switch to N95" | Difference between your current mask and an N95, applied to outdoor PM2.5 |
| Purifier effect | Steady-state fraction of indoor PM2.5 removed = CADR / (CADR + ACH × room volume), with windows closed |
| Natural air changes per hour (ACH) | 0.5 |
| Ceiling height | 2.7 m (room volume = floor area × 2.7) |
| CO₂ per km | car 0.17 kg, two-wheeler 0.04, auto-rickshaw 0.07, bus 0.05, metro 0.03, cycle/walk 0 |
| Weekly CO₂ saving | Round trip, 5 days a week |
| Mode swap compared against | Metro for trips up to 40 km, bus above 40 km. For metro users, cycling/walking if the trip is 5 km or less |
| Trips over 40 km | No whole-trip swap or CO₂ saving is suggested; the plan focuses on cleaner hours, an N95, carpooling and home habits |

## How the AI is kept honest

- The prompt contains only the live data and the computed estimates, and tells the model not to invent any AQI, PM or percentage figure.
- Field names, underscores and raw timestamps are converted to plain words before the model sees them.
- If someone in the household has asthma, the plan must mention it by name and address it first.
- Hindi plans are written fully in Hindi, including headings and units.
- Tone changes with the AQI level (relaxed when Good, urgent when Very unhealthy or Hazardous).
- A plan that was cut off at the model's output limit is never shown or cached.
- **If Gemini is busy or unavailable:** the app tries a chain of models and retries. If every model fails, it shows a full five-section plan, in English or Hindi, built from the live data and the estimates, with a reason for each tip.

## Sample inputs for evaluators

Pick any of these from **Quick sample profile** in the sidebar:

| Profile | City | Household | Commute | Asthma | Mask | Purifier CADR | Room | Outdoors |
|---|---|---|---|---|---|---|---|---|
| Delhi commuter | Delhi | Daily commuter | Two-wheeler, 18 km | No | Cloth | 0 | 15 m² | 90 min |
| Mumbai family with toddlers | Mumbai | Family with young children | Car, 8 km | No | None | 250 | 18 m² | 60 min |
| Bengaluru senior citizen | Bengaluru | Senior citizens | Auto-rickshaw, 4 km | Yes | Surgical | 0 | 14 m² | 45 min |
| Lucknow student athlete | Lucknow | Student / athlete | Cycle / walk, 5 km | No | None | 0 | 12 m² | 150 min |
| Kolkata gig worker | Kolkata | Delivery / gig worker | Two-wheeler, 60 km | No | Cloth | 0 | 10 m² | 360 min |

You can also search any other Indian town in the sidebar and change any input by hand.

## Run it locally

```bash
pip install streamlit requests google-genai pytest
streamlit run app.py
```

Create `.streamlit/secrets.toml` (this file is git-ignored, so the key is never committed):

```toml
GEMINI_API_KEY = "your-key-here"
# optional: GEMINI_MODEL = "gemini-3.5-flash-lite"
```

Without a key the app still shows live air quality and the impact cards, with rule-based tips instead of the AI plan.

## Deploy (Streamlit Community Cloud)

1. Push the project to GitHub. Do **not** include `.streamlit/secrets.toml`.
2. Add a `requirements.txt` with `streamlit`, `requests` and `google-genai`.
3. In the app's **Settings → Secrets**, add `GEMINI_API_KEY = "..."`.

## Testing

All calculations live in `logic.py` (no Streamlit) and all interface text in `translations.py`, so the logic is tested without a browser or network. The whole app is also run headlessly with a fake network and a fake Gemini.

```bash
pytest -v
```

**Result: 45 passed** (pytest, Python, Windows; run `pytest -v` to verify locally).

| Area | What is checked |
|---|---|
| Air-quality data | AQI categories, rejection of invalid or non-numeric readings, response parsing, cleanest-hours selection, India-only place search with de-duplication |
| Estimates | Mask and purifier maths, CO₂ saving, realistic mode swap for short and long trips |
| Prompt safety | The prompt forbids inventing numbers; contains no field names or snake_case words; shows times in plain words; uses µg/m3, not "ug/m3" |
| Personalisation rules | Asthma priority, long-commute rules, Hindi rules (no English phrases for the model to copy), no repeated advice between sections |
| Reliability | Falls back to the next model, retries in rounds, drops models that are out of quota or unavailable, falls back to simpler settings on a 400 error, rejects truncated plans, records which model answered and why others were skipped |
| Offline plan | A complete five-section plan, in English and Hindi, for every sample profile, with no unfilled placeholders or field names |
| Readability | The AQI banner text colour (dark or white) is readable on every category colour |
| Interface | The app runs in English and Hindi; numbers are shown; switching language keeps the person's choices; the plan works with and without a Gemini key; a busy or failing Gemini falls back to the rule-based plan; a failed data fetch shows an error and no numbers; the CO₂ card is hidden for very long commutes |