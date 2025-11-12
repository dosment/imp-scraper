# === Dealership Data + URL Discovery Automation (v1.9h) ===
# PURPOSE
# Collect verified contact data, hours, key URLs, and confirm the website provider.
# Combines: 🔧 Objective (contact/hours) + CarNow URL Discovery + Provider Verification.
# Notes:
# - Address text is always sourced from Google Maps; the Maps link appears ONLY in Evidence.
# - JSON export removed by request (markdown output only).
# - Expanded embedded-credit fingerprints (700Credit, RouteOne, Dealertrack, Secure Accelerate, AutoFi, eLEND Solutions, Darwin, CUDL, Informativ).

automation: Dealership Data + URL Discovery
version: 1.9h
author: BadWolf
editorial_update: GPT-5 Pro
run_mode: sequential
output: markdown
output_style: markdown_codebox_per_dealer
description: >
  Collect verified contact info, business hours, key URLs, website provider data,
  and the dealership's COUNTY. County is displayed directly under the address.
  Address must be taken from the Google Maps business listing (link shown only in Evidence).
  All original behaviors and the exact output order/labels are preserved.

# --------------------------
# INPUT
# --------------------------
Dealer Websites:
https://www.exampledealer1.com/
https://www.exampledealer2.com/
https://www.exampledealer3.com/
# --------------------------
# END INPUT
# --------------------------

# --------------------------
# OPTIONAL URL STAGING (Paste any you have; delete unused lines)
# Format: <Dealer Root URL> | maps: <Google Maps Place URL> | hours: <Hours URL> | service: <Schedule Service URL> | apply: <Credit App URL> | terms: <Privacy/Terms URL> | fb: <Dealer Site (icon start)>
# Example:
# https://www.exampledealer1.com/ | maps: https://maps.google.com/?cid=XXXXXXXXXXXX | hours: https://www.exampledealer1.com/hours/ | service: https://www.exampledealer1.com/service-appointment/ | apply: https://www.exampledealer1.com/finance/apply-for-financing/ | terms: https://www.exampledealer1.com/privacy-policy/ | fb: https://www.exampledealer1.com/
# --------------------------
# END OPTIONAL URL STAGING
# --------------------------

options:
  timezone: America/Chicago
  locale: en-US
  normalize_phone: true
  normalize_hours: true
  capture_confidence_scores: true
  evidence_links_required: true
  use_regional_county_labels: false

# ====================== SOURCE-OF-TRUTH HIERARCHY ========================
source_of_truth:
  address: [Google Maps business listing]      # Printed address text comes from Maps (link only in Evidence)
  county:
    - U.S. Census Bureau Geocoder “Find Geographies” (by address or lat/lng)
    - State/County GIS authoritative site
    - Google Maps administrative_area_level_2 (when explicit)
  phones:
    sales: [Dealer site header, Dealer site footer, Contact page]   # never from Google
  hours:
    sales:   [Dealer Hours/Contact/Locations page]
    service: [Dealer Hours/Contact/Service/Locations page]
    parts:   [Dealer Hours/Contact/Parts/Locations page]
  urls:
    service_scheduler: [Dealer site primary service scheduler page]
    credit_app:        [Dealer site Finance → Apply page]           # same domain, cleaned
    facebook:          [Linked icon in header/footer → final Facebook page]
  provider: [Footer branding, Legal pages (terms/privacy/accessibility), Page source fingerprints, Network requests, Structured data]
  credit_app_embedded_provider:
    - iframe/script src on the Apply page (primary)
    - canonical/data-* attributes and direct vendor links (secondary)
    - network requests on the Apply page (fallback)
    - page source/comments indicating vendor (fallback)
  conflict_rule: "Prefer earlier item in each list; record alternatives in Evidence."

# =========================== NORMALIZATION ===============================
normalize:
  county:
    label: "County"
    label_variants: {LA: "Parish", AK: "Borough", VA_independent_city: "Independent City"}
    enforce_title_case: true
    append_suffix_if_missing: true
  phone:
    regex_extract: '\D*1?\D*(\d{3})\D*(\d{3})\D*(\d{4})\D*'
    output_formats: {pretty: '({area}) {prefix}-{line}', digits: '{area}{prefix}{line}'}
  hours:
    time_range_separator: ' – '              # en dash
    split_hours_separator: '; '
    treat_by_appointment_as_closed: true
    treat_24_hours_as: 'Open 24 hours'
    day_order: [Monday, Tuesday, Wednesday, Thursday, Friday, Saturday, Sunday]
  urls:
    remove_params: [utm_*, gclid, fbclid, mc_cid, mc_eid]
    force_https: true
    keep_trailing_slash_if_present: true

# ============================= EDGE CASES ================================
edge_cases:
  multi_location:
    rule: >
      If multiple rooftops exist, resolve the Sales location Google Maps returns for
      dealer name + primary city. Use Sales address in header; list department hours separately.
  county_in_multiple_counties: >
    Prefer Census for the exact street address; if unavailable, state/county GIS; record conflicts in Evidence.
  independent_city_va: >
    If options.use_regional_county_labels = true and a Virginia independent city is returned,
    label it "Independent City" and print "City of {Name}". Otherwise keep "County: {Name}".
  seasonal_hours: "If seasonal/dated notices conflict with standard hours, prefer the dated notice."
  missing_social_icon: "If no Facebook icon is present, leave blank; do not guess."
  dead_links: "If a target URL 404s or lands on a generic portal, mark as Unsure and include evidence."
  credit_app_missing_or_blank: >
    If Finance → Apply page exists but form fails to load, still record the Apply page URL,
    mark 'Embedded provider: Unsure', and include an evidence link (iframe/src or failed request).

# ========================= WORKFLOW (WITH COUNTY) ========================
# STEP 1 — CONTACT, COUNTY & HOURS
#   • Address → Google Maps (truth; use Optional URL Staging if provided; else discover)
#   • County → Census (prefer); normalize name/suffix.
#   • Sales phone → Site header only.
#   • Hours → Dealer-owned pages only (Hours/Contact/Locations).
# STEP 2 — URL DISCOVERY
#   • Service scheduler (dealer domain or embedded host).
#   • Credit App (Finance → Apply on same domain); detect embedded provider via iframe/script/network/known links.
# STEP 3 — PROVIDER VERIFICATION
# STEP 4 — EVIDENCE CAPTURE (include Maps link; embedded credit provider evidence)
# STEP 5 — SELF-CHECKS (re-verify hours source; re-scan credit embed if empty)
# STEP 6 — OUTPUT (unchanged labels/order)

# ====================== PROVIDER FINGERPRINTS (PRESERVED) ================
provider_fingerprints:
  dealer_com_cox: {display_name: "Dealer.com (Cox Automotive)", footer_text_contains: ["Dealer.com","Cox Automotive"], domain_clues: ["dealer.com"], structured_data_clues: ["Dealer.com"]}
  dealer_inspire: {display_name: "Dealer Inspire", footer_text_contains: ["Dealer Inspire","Cars Commerce"], domain_clues: ["dealerinspire.com","carscommerce.inc"], indicative_hosts: ["secure.dealerinspire.com"]}
  dealer_on: {display_name: "DealerOn", footer_text_contains: ["DealerOn"], domain_clues: ["dealeron.com"]}
  dealer_eprocess: {display_name: "Dealer eProcess", footer_text_contains: ["Dealer eProcess","DEP"], domain_clues: ["dealereprocess.com"]}
  team_velocity_apollo: {display_name: "Team Velocity / Apollo Sites", footer_text_contains: ["Team Velocity","Apollo Sites"], domain_clues: ["teamvelocitymarketing.com"]}
  sokal: {display_name: "Sokal", footer_text_contains: ["Sokal"], domain_clues: ["gosokal.com"]}
  dealer_spike: {display_name: "Dealer Spike", footer_text_contains: ["Dealer Spike"], domain_clues: ["dealerspike.com","dealerspike-secure.com"]}
  dealer_alchemist: {display_name: "Dealer Alchemist", footer_text_contains: ["Dealer Alchemist"], domain_clues: ["dealeralchemist.com"]}
  jazel_auto: {display_name: "Jazel Auto", footer_text_contains: ["Jazel","Jazel Auto"], domain_clues: ["jazel.com","jazelauto.com"]}
  carsforsale: {display_name: "Carsforsale.com (SiteFLEX)", footer_text_contains: ["Carsforsale.com","SiteFLEX"], domain_clues: ["carsforsale.com","dealers.carsforsale.com"]}

# ================== EMBEDDED CREDIT PROVIDER FINGERPRINTS ===============
credit_app_fingerprints:
  seven_hundred_credit:
    display_name: "700Credit"
    domains:
      - secure.700credit.com
      - 700credit.com
      - www.700dealer.com
      - 700dealer.com
    path_clues:
      - /creditapp
      - /apply
      - /prequal
      - /quickapplication
      - /QuickQualify
      - /quickqualify

  routeone:
    display_name: "RouteOne"
    domains:
      - routeone.net
      - apps.routeone.net
      - www.routeone.net
      - digital-retail-ui.routeone.net
    path_clues:
      - /digital-retail-ui
      - /application
      - /apply
      - /creditapp

  dealertrack:
    display_name: "Dealertrack"
    domains:
      - dealertrack.com
      - suite.dtdrs.dealertrack.com
      - dtprod.dealertrack.com
    path_clues:
      - /creditapp
      - /apply
      - /financing
      - /suite
      - /accountId=
      - /dealerId=

  secure_accelerate:
    display_name: "Secure Accelerate (Dealer.com)"
    domains:
      - secure.accelerate.dealer.com
      - accelerate.dealer.com
      - www.accelerate.dealer.com
    path_clues:
      - /dealer/
      - /accelerate
      - /apply
      - /finance

  autofi:
    display_name: "AutoFi"
    domains:
      - autofi.com
      - app.autofi.com
      - buy.autofi.com
      - dealer.autofi.com
    path_clues:
      - /buy
      - /apply
      - /credit
      - /finance
      - /deal
      - /digital-retail

  elend_solutions:
    display_name: "eLEND Solutions"
    domains:
      - elendsolutions.com
      - app.elendsolutions.com
      - connect.elendsolutions.com
    path_clues:
      - /apply
      - /prequal
      - /creditapp
      - /connect

  darwin:
    display_name: "Darwin Automotive"
    domains:
      - darwinautomotive.com
      - app.darwinautomotive.com
      - dms.darwinautomotive.com
      - retail.darwinautomotive.com
    path_clues:
      - /digitalretail
      - /dr
      - /finance
      - /creditapp
      - /apply

  cudl:
    display_name: "CUDL"
    domains:
      - cudl.com
      - apply.cudl.com
      - www.cudl.com
    path_clues:
      - /apply
      - /application
      - /creditapp

  informativ:
    display_name: "Informativ (formerly Credit Bureau Connection)"
    domains:
      - informativ.com
      - creditbureauconnection.com
      - cbcautomotive.com
      - forms.cbcautomotive.com
    path_clues:
      - /credit
      - /application
      - /apply
      - /cbc
      - /informativ

# =========================== OUTPUT FORMAT (MARKDOWN) ====================
output_format:
  markdown_per_dealer: |
    [DEALERSHIP NAME]
    [GOOGLE MAPS ADDRESS]
    County: [COUNTY NAME]
    Phone: (XXX) XXX-XXXX
    Phone (no dashes): XXXXXXXXXX
    Website: https://www.exampledealer.com/
    Provider: Example Provider

    Sales Hours
    Monday: 8:00 AM – 6:00 PM
    Tuesday: 8:00 AM – 6:00 PM
    Wednesday: 8:00 AM – 6:00 PM
    Thursday: 8:00 AM – 6:00 PM
    Friday: 8:00 AM – 6:00 PM
    Saturday: 9:00 AM – 5:00 PM
    Sunday: Closed

    Service Hours
    Monday: 8:00 AM – 5:00 PM
    Tuesday: 8:00 AM – 5:00 PM
    Wednesday: 8:00 AM – 5:00 PM
    Thursday: 8:00 AM – 5:00 PM
    Friday: 8:00 AM – 5:00 PM
    Saturday: Closed
    Sunday: Closed

    Parts Hours
    Monday: 8:00 AM – 5:00 PM
    Tuesday: 8:00 AM – 5:00 PM
    Wednesday: 8:00 AM – 5:00 PM
    Thursday: 8:00 AM – 5:00 PM
    Friday: 8:00 AM – 5:00 PM
    Saturday: Closed
    Sunday: Closed

    Schedule Service: https://www.exampledealer.com/service-appointment/
    Credit App: https://www.exampledealer.com/finance/apply-for-financing/
      • Embedded provider (if any):
    Facebook: https://www.facebook.com/exampledealer/
    Facebook Page ID:

    Evidence
    - Google Maps (address): https://goo.gl/maps/example
    - County verification: https://<census-or-gis-lookup-url>
    - Dealer homepage (header phone): https://www.exampledealer.com/
    - Dealer hours page (hours): https://www.exampledealer.com/hours/
    - Service verified on: https://www.exampledealer.com/service-appointment/
    - Credit app verified on: https://www.exampledealer.com/finance/apply-for-financing/
    - Credit app embedded provider evidence: <detected vendor + iframe/src or link; see template comment>
    - Facebook start: exampledealer.com → final FB: https://www.facebook.com/exampledealer/
    - Provider verification: https://www.exampledealer.com/footer-or-terms/
    - Captured: YYYY-MM-DD HH:mm (America/Chicago)

# ============================== QA CHECKLIST =============================
qa_checklist:
  - [ ] Address matches Google Maps listing (link only in Evidence)
  - [ ] County verified (Census preferred) and printed under address
  - [ ] Sales phone from site header only
  - [ ] En dashes (–) in all time ranges; semicolons for split hours
  - [ ] Hours come from dealer-owned pages
  - [ ] Service scheduler + Credit App URL included; timestamp captured
  - [ ] Credit App embedded provider detected (e.g., secure.700credit.com, routeone.net, dealertrack.com, accelerate.dealer.com, etc.)
  - [ ] “By appointment” treated as Closed
  - [ ] Facebook URL verified (blank if none)
  - [ ] Provider verified or “Unsure” with evidence
  - [ ] Phone pretty + digits both valid (10 digits)
  - [ ] Monday→Sunday order; fill missing with “Closed”
  - [ ] No tracking params in final URLs
  - [ ] Input order preserved in output

# ============================ FAILURE MODES ==============================
failures:
  - condition: "County cannot be verified after one targeted re-check"
    action: "Output County: Unsure; add both candidate counties + verification links in Evidence"
  - condition: "City spans multiple counties and sources disagree"
    action: "Prefer Census; record discarded county in Evidence"
  - condition: "Address or hours conflicts persist"
    action: "Mark fields 'Unsure' and include exact URLs/screens in Evidence"
  - condition: "Credit App page lacks a visible form or errors on load"
    action: "Keep the Apply page URL; set Embedded provider: Unsure; include iframe/src or network attempts in Evidence"

# ===================== COPY-PASTE MICRO-TEMPLATES =======================
templates:
  county_lookup: |
    County Lookup for {{dealer_name}} ({{street}}, {{city}}, {{state}} {{zip}}):
    1) Query U.S. Census Geocoder (Find Geographies) by full address.
       - Record 'County name' (note independent city/parish/borough variants).
    2) If unavailable, check state/county GIS for the parcel/address.
    3) If still unavailable, read Google Maps administrative_area_level_2.
    Normalize to Title Case and ensure suffix ('County' or regional variant).
    If multiple results, prefer Census; otherwise mark 'Unsure' and list both with links in Evidence.

  credit_app_detection: |
    Credit App Detection for {{dealer_name}}:
    1) Navigate dealer site → Finance → Apply for Financing (same domain).
    2) Record the Apply page URL (normalized; remove tracking params).
    3) Inspect the page for an embedded provider:
       - Find <iframe> or <script> src domains (e.g., 700dealer.com, secure.700credit.com, routeone.net, dealertrack.com, secure.accelerate.dealer.com, autofi.com, elendsolutions.com, darwinautomotive.com, cudl.com, informativ.com/cbcautomotive.com).
       - If none visible, check canonical/data-* attributes, then network requests, then page source comments.
    4) Set “Embedded provider (if any)” to the detected vendor display name.
    5) Capture evidence URL (or snippet reference) for the src/request.
    6) If form won’t load or vendor unknown: mark “Unsure” and include evidence links.

  # NEW: short evidence comment for consistency in Evidence section
  credit_embed_evidence_comment: |
    Detected {{vendor_display}} via {{signal_type}}:
      • Source: {{evidence_url_or_hint}}
      • Page: {{apply_page_url}}

postprocess:
  remove_inline_citations_from_hours: true
  move_non_dealer_hour_sources_to_evidence: true