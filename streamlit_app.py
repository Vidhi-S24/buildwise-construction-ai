import os
import json
import time
import hashlib
from datetime import datetime

import streamlit as st
from PIL import Image
from google import genai
from google.genai import types


# ============================================================
# 1. PAGE CONFIGURATION
# ============================================================

st.set_page_config(
    page_title="BuildWise AI",
    page_icon="🏗️",
    layout="wide",
    initial_sidebar_state="expanded",
)


# ============================================================
# 2. CUSTOM STYLING
# ============================================================

st.markdown(
    """
    <style>
        .block-container {
            padding-top: 1.8rem;
            padding-bottom: 2rem;
        }

        .main-title {
            font-size: 2.5rem;
            font-weight: 800;
            margin-bottom: 0.2rem;
        }

        .subtitle {
            color: #9CA3AF;
            font-size: 1rem;
            margin-bottom: 1.5rem;
        }

        .section-heading {
            font-size: 1.5rem;
            font-weight: 700;
            margin-top: 1rem;
        }

        div[data-testid="stMetric"] {
            border: 1px solid rgba(128, 128, 128, 0.25);
            padding: 16px;
            border-radius: 12px;
        }

        .info-card {
            padding: 18px;
            border: 1px solid rgba(128, 128, 128, 0.25);
            border-radius: 12px;
            min-height: 145px;
        }

        .footer {
            color: #9CA3AF;
            text-align: center;
            padding-top: 25px;
            font-size: 0.85rem;
        }
    </style>
    """,
    unsafe_allow_html=True,
)


# ============================================================
# 3. GEMINI API CONFIGURATION
# ============================================================

def get_gemini_client():
    """
    Read the Gemini API key from Streamlit secrets
    or the GEMINI_API_KEY environment variable.
    """

    api_key = os.getenv("GEMINI_API_KEY")

    if not api_key:
        try:
            api_key = st.secrets.get("GEMINI_API_KEY")
        except Exception:
            api_key = None

    if not api_key:
        raise RuntimeError(
            "Gemini API key is missing. Configure GEMINI_API_KEY "
            "in your environment or Streamlit secrets."
        )

    return genai.Client(api_key=api_key)


def analyze_construction_image(image, prompt):
    """
    Analyze a construction-site image using Gemini.

    Retries temporary API errors and returns a Python dictionary.
    """

    client = get_gemini_client()

    image_bytes = image.getvalue()

    last_error = None

    for attempt in range(3):
        try:
            response = client.models.generate_content(
                model="gemini-3.6-flash",
                contents=[
                    types.Part.from_bytes(
                        data=image_bytes,
                        mime_type=image.type,
                    ),
                    prompt,
                ],
                config=types.GenerateContentConfig(
                    response_mime_type="application/json",
                    temperature=0.2,
                ),
            )

            response_text = response.text

            if not response_text:
                raise ValueError(
                    "Gemini returned an empty response. Please try again."
                )

            result = json.loads(response_text)

            if not isinstance(result, dict):
                raise ValueError(
                    "The AI response was not a valid JSON object."
                )

            return result

        except Exception as exc:
            last_error = exc
            error_text = str(exc).lower()

            temporary_error = any(
                term in error_text
                for term in [
                    "503",
                    "unavailable",
                    "429",
                    "resource_exhausted",
                    "rate limit",
                    "500",
                    "internal server error",
                ]
            )

            if temporary_error and attempt < 2:
                time.sleep(2 * (attempt + 1))
                continue

            break

    raise RuntimeError(
        f"Gemini image analysis failed: {last_error}"
    )


# ============================================================
# 4. SHARED HELPER FUNCTIONS
# ============================================================

def make_report(module, data, mode="LIVE_GEMINI_AI"):
    """Create a downloadable JSON report."""

    return {
        "project": "BuildWise AI",
        "module": module,
        "analysis_mode": mode,
        "generated_at": datetime.now().astimezone().isoformat(
            timespec="seconds"
        ),
        "disclaimer": (
            "AI-generated findings are preliminary. They are not a "
            "substitute for an inspection by a qualified construction "
            "safety professional or engineer."
        ),
        "results": data,
    }


def show_download(report, filename):
    """Display a JSON download button."""

    json_data = json.dumps(report, indent=4, ensure_ascii=False)

    st.download_button(
        label="📥 Download JSON Report",
        data=json_data,
        file_name=filename,
        mime="application/json",
        key=f"download_{filename}",
    )


def get_image_hash(image):
    """Generate a unique fingerprint for the uploaded image."""

    return hashlib.sha256(image.getvalue()).hexdigest()


def show_image(upload):
    """Display an uploaded image."""

    image = Image.open(upload).convert("RGB")

    st.image(
        image,
        caption="Uploaded construction-site photograph",
        use_container_width=True,
    )

    return image


def validate_safety_result(result):
    """
    Validate and normalize the safety-analysis result
    before displaying or exporting it.
    """

    if not isinstance(result, dict):
        raise ValueError("The safety report must be a JSON object.")

    # Validate safety score.
    score = result.get("safety_score")

    if isinstance(score, bool) or not isinstance(score, (int, float)):
        raise ValueError("The AI did not return a valid numeric safety score.")

    if not 0 <= score <= 100:
        raise ValueError("The safety score must be between 0 and 100.")

    result["safety_score"] = round(score)

    # Validate overall status.
    allowed_statuses = {
        "SAFE",
        "CAUTION",
        "UNSAFE",
        "NEEDS_REVIEW",
    }

    status = str(result.get("overall_status", "NEEDS_REVIEW"))
    status = status.strip().upper().replace(" ", "_")

    if status not in allowed_statuses:
        status = "NEEDS_REVIEW"

    result["overall_status"] = status

    # Validate PPE results.
    ppe = result.get("ppe_detection", {})

    if not isinstance(ppe, dict):
        ppe = {}

    ppe_items = [
        "helmet",
        "high_visibility_vest",
        "safety_boots",
        "safety_harness",
    ]

    normalized_ppe = {}

    for item in ppe_items:
        item_result = ppe.get(item, {})

        if isinstance(item_result, str):
            item_result = {"status": item_result}

        if not isinstance(item_result, dict):
            item_result = {}

        ppe_status = str(
            item_result.get("status", "UNCERTAIN")
        ).strip().upper()

        if ppe_status not in {
            "OBSERVED",
            "NOT_OBSERVED",
            "UNCERTAIN",
            "NOT_APPLICABLE",
        }:
            ppe_status = "UNCERTAIN"

        normalized_ppe[item] = {
            "status": ppe_status,
            "notes": str(item_result.get("notes", "No additional details."))
            [:500],
        }

    result["ppe_detection"] = normalized_ppe

    # Validate hazards.
    hazards = result.get("hazards", [])

    if not isinstance(hazards, list):
        hazards = []

    normalized_hazards = []

    for hazard in hazards[:30]:
        if not isinstance(hazard, dict):
            continue

        severity = str(
            hazard.get("severity", "UNKNOWN")
        ).strip().upper()

        if severity not in {
            "LOW",
            "MEDIUM",
            "HIGH",
            "CRITICAL",
            "UNKNOWN",
        }:
            severity = "UNKNOWN"

        normalized_hazards.append(
            {
                "hazard": str(
                    hazard.get("hazard", "Unspecified observation")
                )[:500],
                "severity": severity,
                "remedy": str(
                    hazard.get("remedy", "Request a professional inspection.")
                )[:1000],
            }
        )

    result["hazards"] = normalized_hazards

    result["assessment_note"] = str(
        result.get(
            "assessment_note",
            "AI-generated preliminary assessment. Professional verification is required.",
        )
    )[:1500]

    return result


def format_ppe_name(name):
    """Convert a PPE field name into a readable label."""

    names = {
        "helmet": "Safety helmet",
        "high_visibility_vest": "High-visibility vest",
        "safety_boots": "Safety boots",
        "safety_harness": "Safety harness",
    }

    return names.get(name, name.replace("_", " ").title())


# ============================================================
# 5. SIDEBAR NAVIGATION
# ============================================================

with st.sidebar:
    st.title("🏗️ BuildWise AI")

    st.caption("Construction Intelligence Platform")

    st.divider()

    page = st.radio(
        "Navigation",
        [
            "Dashboard",
            "Site Safety & PPE Audit",
            "Crack Diagnostics",
            "Planning & Valuation",
            "Daily Site Assistant",
        ],
        key="main_navigation",
    )

    st.divider()

    st.subheader("AI Configuration")

    st.info(
        "Live Gemini AI is used for Site Safety & PPE image analysis."
    )

    st.caption(
        "Image analysis requires a valid Gemini API key and available "
        "API quota. Other modules are not yet connected to live AI."
    )


# ============================================================
# 6. DASHBOARD
# ============================================================

if page == "Dashboard":

    st.markdown(
        '<div class="main-title">🏗️ BuildWise AI</div>',
        unsafe_allow_html=True,
    )

    st.markdown(
        '<div class="subtitle">'
        "Your intelligent construction planning and site-inspection workspace."
        "</div>",
        unsafe_allow_html=True,
    )

    st.success(
        "Welcome to BuildWise AI. Select a module from the sidebar "
        "to get started."
    )

    col1, col2, col3, col4 = st.columns(4)

    with col1:
        st.metric("Core Modules", "4")

    with col2:
        st.metric("Image Analysis", "Gemini AI")

    with col3:
        st.metric("Report Format", "JSON")

    with col4:
        st.metric("Platform", "Streamlit")

    st.subheader("Available Modules")

    module_col1, module_col2 = st.columns(2)

    with module_col1:
        st.markdown(
            """
            <div class="info-card">
                <h3>🦺 Site Safety & PPE Audit</h3>
                <p>
                    Analyze uploaded site photographs for visible PPE
                    and potential construction hazards.
                </p>
                <p><b>Status:</b> Live Gemini image analysis</p>
            </div>
            """,
            unsafe_allow_html=True,
        )

        st.write("")

        st.markdown(
            """
            <div class="info-card">
                <h3>📐 Planning & Valuation</h3>
                <p>
                    Estimate construction budgets, expenditure,
                    materials and indicative property value.
                </p>
                <p><b>Status:</b> Rule-based estimates</p>
            </div>
            """,
            unsafe_allow_html=True,
        )

    with module_col2:
        st.markdown(
            """
            <div class="info-card">
                <h3>🧱 Crack Diagnostics</h3>
                <p>
                    Review visible cracks and organize preliminary
                    observations for professional assessment.
                </p>
                <p><b>Status:</b> Demo module; live analysis not connected</p>
            </div>
            """,
            unsafe_allow_html=True,
        )

        st.write("")

        st.markdown(
            """
            <div class="info-card">
                <h3>📋 Daily Site Assistant</h3>
                <p>
                    Review basic site precautions and access
                    predefined construction guidance.
                </p>
                <p><b>Status:</b> Rule-based assistant</p>
            </div>
            """,
            unsafe_allow_html=True,
        )

    st.divider()

    st.subheader("Important Notice")

    st.warning(
        "BuildWise AI provides preliminary AI-generated observations "
        "and planning estimates. It does not replace a qualified safety "
        "officer, structural engineer, quantity surveyor, or on-site "
        "inspection."
    )


# ============================================================
# 7. SITE SAFETY & PPE AUDIT
# ============================================================

elif page == "Site Safety & PPE Audit":

    st.title("🦺 Site Safety & PPE Audit")

    st.write(
        "Upload a construction-site photograph to identify visible "
        "personal protective equipment (PPE) and potential hazards."
    )

    st.info(
        "This module uses live Gemini AI when you click Analyze. "
        "Results depend on image quality and must be verified by a "
        "qualified site safety professional."
    )

    uploaded_image = st.file_uploader(
        "Upload a construction-site photograph",
        type=["jpg", "jpeg", "png"],
        key="safety_image_uploader",
        help="Supported formats: JPG, JPEG and PNG.",
    )

    if uploaded_image is not None:

        current_image_hash = get_image_hash(uploaded_image)

        # If the uploaded image changes, remove the previous report.
        previous_hash = st.session_state.get("safety_image_hash")

        if previous_hash != current_image_hash:
            st.session_state.pop("safety_report", None)
            st.session_state["safety_image_hash"] = current_image_hash

        st.subheader("Uploaded Photograph")

        show_image(uploaded_image)

        st.caption(
            f"Image size: {uploaded_image.size / 1024:.1f} KB"
        )

        analyze_button = st.button(
            "🔍 Analyze Site Image with Gemini AI",
            type="primary",
            use_container_width=True,
            key="analyze_safety_button",
        )

        if analyze_button:

            safety_prompt = """
You are a construction-site safety observation assistant.

Analyze the supplied construction-site photograph carefully.
Only describe objects, people, PPE and hazards that are actually
visible in the image. Do not invent people, objects or conditions.

If an item cannot be assessed from the photograph, mark it UNCERTAIN.
If PPE is not visible, do not automatically conclude that a worker
is violating a safety rule. Consider whether the worker is visible,
whether the relevant body area can be seen, and whether the image
provides enough evidence.

Do not claim to certify that a construction site is safe.

Return ONLY a valid JSON object with exactly these fields:

{
  "safety_score": 0,
  "overall_status": "NEEDS_REVIEW",
  "ppe_detection": {
    "helmet": {
      "status": "OBSERVED",
      "notes": "Brief visual evidence or uncertainty."
    },
    "high_visibility_vest": {
      "status": "UNCERTAIN",
      "notes": "Brief visual evidence or uncertainty."
    },
    "safety_boots": {
      "status": "UNCERTAIN",
      "notes": "Brief visual evidence or uncertainty."
    },
    "safety_harness": {
      "status": "NOT_APPLICABLE",
      "notes": "Explain whether a harness assessment is relevant."
    }
  },
  "hazards": [
    {
      "hazard": "Visible potential hazard",
      "severity": "MEDIUM",
      "remedy": "Practical precaution or recommended inspection."
    }
  ],
  "assessment_note": "Short summary and important limitations."
}

Rules:
- safety_score must be a number from 0 to 100.
- overall_status must be SAFE, CAUTION, UNSAFE or NEEDS_REVIEW.
- PPE status must be OBSERVED, NOT_OBSERVED, UNCERTAIN or NOT_APPLICABLE.
- Hazard severity must be LOW, MEDIUM, HIGH, CRITICAL or UNKNOWN.
- Use an empty hazards array if no potential hazards can be identified.
- Do not assume the absence of a visible hazard proves the site is safe.
- Explain uncertainty where the image does not provide enough evidence.
- This is a preliminary visual assessment, not a formal safety certification.
"""

            with st.spinner(
                "Gemini AI is analyzing the uploaded photograph..."
            ):
                try:
                    raw_result = analyze_construction_image(
                        uploaded_image,
                        safety_prompt,
                    )

                    validated_result = validate_safety_result(raw_result)

                    report = make_report(
                        module="Site Safety & PPE Audit",
                        data=validated_result,
                        mode="LIVE_GEMINI_AI",
                    )

                    # Save report and associate it with this exact image.
                    st.session_state["safety_report"] = report
                    st.session_state["safety_report_image_hash"] = (
                        current_image_hash
                    )

                    st.success(
                        "Gemini analysis completed successfully."
                    )

                except Exception as exc:
                    st.error(
                        "The image could not be analyzed. Check your API "
                        "key, model access, network connection and API quota."
                    )

                    with st.expander("Technical error details"):
                        st.code(str(exc))

        # Display only a report generated for the currently uploaded image.
        saved_report = st.session_state.get("safety_report")

        saved_report_hash = st.session_state.get(
            "safety_report_image_hash"
        )

        if (
            saved_report
            and saved_report_hash == current_image_hash
        ):

            result = saved_report["results"]

            st.divider()

            st.subheader("Live Gemini Analysis Results")

            st.caption(
                "Analysis mode: LIVE_GEMINI_AI · "
                f"Generated at {saved_report['generated_at']}"
            )

            score = result["safety_score"]
            status = result["overall_status"]

            score_col, status_col, hazards_col = st.columns(3)

            with score_col:
                st.metric(
                    "AI-Estimated Safety Score",
                    f"{score}/100",
                )

            with status_col:
                st.metric(
                    "Overall Assessment",
                    status.replace("_", " "),
                )

            with hazards_col:
                st.metric(
                    "Potential Hazards Identified",
                    len(result["hazards"]),
                )

            st.progress(score / 100)

            if status == "SAFE":
                st.success(
                    "The image received a SAFE classification. "
                    "This is not proof that the site is hazard-free."
                )
            elif status == "CAUTION":
                st.warning(
                    "The image received a CAUTION classification. "
                    "Review the observations below."
                )
            elif status == "UNSAFE":
                st.error(
                    "Potentially unsafe conditions were identified. "
                    "Arrange an appropriate site assessment."
                )
            else:
                st.warning(
                    "The image needs further review. Do not rely on "
                    "this result as a safety clearance."
                )

            # ----------------------------------------
            # PPE DETECTION
            # ----------------------------------------

            st.subheader("PPE Detection")

            ppe = result["ppe_detection"]

            ppe_columns = st.columns(2)

            ppe_items = list(ppe.items())

            for index, (item_name, item_data) in enumerate(ppe_items):
                with ppe_columns[index % 2]:

                    st.markdown(
                        f"**{format_ppe_name(item_name)}**"
                    )

                    ppe_status = item_data["status"]

                    if ppe_status == "OBSERVED":
                        st.success("Observed")

                    elif ppe_status == "NOT_OBSERVED":
                        st.error("Not observed")

                    elif ppe_status == "NOT_APPLICABLE":
                        st.info("Not applicable")

                    else:
                        st.warning("Uncertain")

                    st.caption(item_data["notes"])

            # ----------------------------------------
            # POTENTIAL HAZARDS
            # ----------------------------------------

            st.subheader("Potential Hazards")

            hazards = result["hazards"]

            if hazards:

                for index, hazard in enumerate(hazards, start=1):

                    with st.expander(
                        f"{index}. {hazard['hazard']} "
                        f"— {hazard['severity']}"
                    ):

                        st.write("**Severity:**", hazard["severity"])

                        st.write("**Recommended precaution:**")

                        st.write(hazard["remedy"])

            else:
                st.info(
                    "Gemini did not identify any potential hazards "
                    "in this photograph. This does not establish that "
                    "the site is safe."
                )

            # ----------------------------------------
            # ASSESSMENT NOTE
            # ----------------------------------------

            st.subheader("AI Assessment Notes")

            st.write(result["assessment_note"])

            st.warning(
                "Verify every finding on site. A photograph may not show "
                "all hazards, PPE requirements, working conditions or "
                "applicable safety regulations."
            )

            show_download(
                saved_report,
                "buildwise_safety_ppe_report.json",
            )

    else:

        st.session_state.pop("safety_report", None)
        st.session_state.pop("safety_report_image_hash", None)
        st.session_state.pop("safety_image_hash", None)

        st.info(
            "Upload a construction-site photograph to begin the live "
            "Gemini safety and PPE analysis."
        )


# ============================================================
# 8. PLACEHOLDERS FOR THE REMAINING MODULES
# ============================================================

elif page == "Crack Diagnostics":

    st.title("🧱 Crack Diagnostics")

    st.write(
        "Upload a photograph of a wall, beam, column, slab, or concrete "
        "surface to identify visible crack patterns and receive a "
        "preliminary AI-generated assessment."
    )

    st.warning(
        "This tool cannot determine structural integrity or certify a "
        "building as safe from a photograph. Consult a qualified "
        "structural engineer for concerning cracks."
    )

    uploaded_crack_image = st.file_uploader(
        "Upload a photograph showing cracks",
        type=["jpg", "jpeg", "png"],
        key="crack_image_uploader",
        help="Use a clear, well-lit photograph. Include a close-up and "
             "a wider view when possible.",
    )

    if uploaded_crack_image is not None:

        current_crack_hash = get_image_hash(uploaded_crack_image)

        previous_crack_hash = st.session_state.get("crack_image_hash")

        if previous_crack_hash != current_crack_hash:
            st.session_state.pop("crack_report", None)
            st.session_state["crack_image_hash"] = current_crack_hash

        st.subheader("Uploaded Photograph")

        show_image(uploaded_crack_image)

        analyze_crack_button = st.button(
            "🔍 Analyze Cracks with Gemini AI",
            type="primary",
            use_container_width=True,
            key="analyze_crack_button",
        )

        if analyze_crack_button:

            crack_prompt = """
You are an assistant that describes visible cracks in building materials.

Analyze the supplied photograph carefully. Describe only what is visible.
Do not invent measurements, hidden damage, causes, or structural conditions.

Return ONLY a valid JSON object with these fields:

{
  "surface_type": "Wall, concrete, ceiling, or uncertain",
  "crack_pattern": "Description of the visible crack pattern",
  "visible_location": "Where the crack appears in the image",
  "apparent_severity": "LOW, MODERATE, HIGH, or UNCERTAIN",
  "visual_width_estimate": "Not measurable from this image",
  "possible_causes": [
    "Possible explanation, clearly labelled as unconfirmed"
  ],
  "warning_signs": [
    "Visible warning sign, if any"
  ],
  "recommended_actions": [
    "Practical next step"
  ],
  "professional_inspection_recommended": true,
  "assessment_note": "Explain uncertainty and limitations"
}

Rules:
- Do not claim to determine structural integrity from a photograph.
- Do not invent crack widths or measurements. If no reference scale is
  visible, state that width cannot be reliably measured.
- Distinguish observed features from possible causes.
- Use LOW, MODERATE, HIGH, or UNCERTAIN for apparent_severity.
- Use an empty array when no items can be identified.
- Recommend prompt professional inspection if there are signs such as
  major displacement, wide or expanding cracks, diagonal cracks near
  openings, exposed or corroded reinforcement, or extensive cracking.
- If the image is unclear or does not show a crack, state that explicitly.
- Do not certify the building or surface as safe.
"""

            with st.spinner(
                "Gemini AI is examining the photograph..."
            ):
                try:
                    raw_crack_result = analyze_construction_image(
                        uploaded_crack_image,
                        crack_prompt,
                    )

                    if not isinstance(raw_crack_result, dict):
                        raise ValueError(
                            "The AI returned an invalid report."
                        )

                    allowed_severities = {
                        "LOW",
                        "MODERATE",
                        "HIGH",
                        "UNCERTAIN",
                    }

                    severity = str(
                        raw_crack_result.get(
                            "apparent_severity", "UNCERTAIN"
                        )
                    ).strip().upper()

                    if severity not in allowed_severities:
                        severity = "UNCERTAIN"

                    def clean_text(value, fallback, limit=1500):
                        if isinstance(value, str) and value.strip():
                            return value.strip()[:limit]
                        return fallback

                    def clean_list(value, limit=10):
                        if not isinstance(value, list):
                            return []

                        return [
                            str(item).strip()[:1000]
                            for item in value[:limit]
                            if isinstance(item, str) and item.strip()
                        ]

                    crack_result = {
                        "surface_type": clean_text(
                            raw_crack_result.get("surface_type"),
                            "Uncertain",
                        ),
                        "crack_pattern": clean_text(
                            raw_crack_result.get("crack_pattern"),
                            "The crack pattern could not be determined.",
                        ),
                        "visible_location": clean_text(
                            raw_crack_result.get("visible_location"),
                            "Uncertain",
                        ),
                        "apparent_severity": severity,
                        "visual_width_estimate": clean_text(
                            raw_crack_result.get("visual_width_estimate"),
                            "Cannot be reliably measured from this image.",
                        ),
                        "possible_causes": clean_list(
                            raw_crack_result.get("possible_causes")
                        ),
                        "warning_signs": clean_list(
                            raw_crack_result.get("warning_signs")
                        ),
                        "recommended_actions": clean_list(
                            raw_crack_result.get("recommended_actions")
                        ),
                        "professional_inspection_recommended": (
                            raw_crack_result.get(
                                "professional_inspection_recommended"
                            )
                            is True
                        ),
                        "assessment_note": clean_text(
                            raw_crack_result.get("assessment_note"),
                            "This is a preliminary visual assessment only.",
                        ),
                    }

                    crack_report = make_report(
                        module="Crack Diagnostics",
                        data=crack_result,
                        mode="LIVE_GEMINI_AI",
                    )

                    st.session_state["crack_report"] = crack_report
                    st.session_state["crack_report_image_hash"] = (
                        current_crack_hash
                    )

                    st.success(
                        "Crack photograph analyzed successfully."
                    )

                except Exception as exc:
                    st.error(
                        "Crack analysis failed. Check your Gemini API "
                        "configuration, model access, connection and quota."
                    )

                    with st.expander("Technical error details"):
                        st.code(str(exc))

        saved_crack_report = st.session_state.get("crack_report")

        saved_crack_hash = st.session_state.get(
            "crack_report_image_hash"
        )

        if (
            saved_crack_report
            and saved_crack_hash == current_crack_hash
        ):

            result = saved_crack_report["results"]

            st.divider()

            st.subheader("Live Gemini Crack Analysis")

            st.caption(
                "Analysis mode: LIVE_GEMINI_AI · "
                f"Generated at {saved_crack_report['generated_at']}"
            )

            col1, col2 = st.columns(2)

            with col1:
                st.metric(
                    "Apparent Severity",
                    result["apparent_severity"],
                )

            with col2:
                st.metric(
                    "Professional Inspection",
                    (
                        "Recommended"
                        if result["professional_inspection_recommended"]
                        else "Not flagged by AI"
                    ),
                )

            st.markdown("### Surface and Crack Observations")

            st.write("**Surface type:**", result["surface_type"])
            st.write("**Visible location:**", result["visible_location"])
            st.write("**Crack pattern:**", result["crack_pattern"])

            st.write(
                "**Width estimate:**",
                result["visual_width_estimate"],
            )

            severity = result["apparent_severity"]

            if severity == "HIGH":
                st.error(
                    "Potentially concerning visible features were identified. "
                    "Arrange a prompt assessment by a qualified structural "
                    "engineer. If there are signs of immediate instability, "
                    "keep people away from the affected area."
                )
            elif severity == "MODERATE":
                st.warning(
                    "Arrange a professional inspection to assess the crack "
                    "and determine whether monitoring or repairs are needed."
                )
            elif severity == "LOW":
                st.info(
                    "The visible features were classified as low apparent "
                    "severity by AI. This does not establish structural safety."
                )
            else:
                st.warning(
                    "The available image is insufficient to assign a "
                    "reliable severity category."
                )

            st.markdown("### Possible Causes")

            if result["possible_causes"]:
                for cause in result["possible_causes"]:
                    st.markdown(f"- {cause}")
            else:
                st.write("No possible causes were identified.")

            st.markdown("### Visible Warning Signs")

            if result["warning_signs"]:
                for sign in result["warning_signs"]:
                    st.markdown(f"- {sign}")
            else:
                st.write(
                    "No specific warning signs were reported. "
                    "This does not prove that none are present."
                )

            st.markdown("### Recommended Actions")

            if result["recommended_actions"]:
                for action in result["recommended_actions"]:
                    st.markdown(f"- {action}")
            else:
                st.write(
                    "Arrange an assessment by a qualified professional "
                    "if the crack is new, growing, displaced or concerning."
                )

            st.markdown("### AI Assessment Notes")

            st.write(result["assessment_note"])

            st.warning(
                "Do not use this AI report alone to decide whether a "
                "building is safe. Crack significance depends on factors "
                "that may not be visible, including structural design, "
                "movement, crack progression and the condition of "
                "surrounding materials."
            )

            show_download(
                saved_crack_report,
                "buildwise_crack_diagnostics_report.json",
            )

    else:
        st.session_state.pop("crack_report", None)
        st.session_state.pop("crack_report_image_hash", None)
        st.session_state.pop("crack_image_hash", None)

        st.info(
            "Upload a photograph to begin crack diagnostics."
        )


elif page == "Planning & Valuation":

    st.title("📐 Construction Planning & Valuation")

    st.write(
        "Estimate construction costs, expenditure, material quantities, "
        "project progress, and indicative property value."
    )

    st.info(
        "All estimates are preliminary. Actual costs and material "
        "requirements depend on drawings, specifications, local rates, "
        "site conditions and professional quantity surveying."
    )

    # --------------------------------------------------------
    # PROJECT DETAILS
    # --------------------------------------------------------

    st.subheader("1. Project Details")

    with st.form("planning_valuation_form"):

        col1, col2 = st.columns(2)

        with col1:
            project_name = st.text_input(
                "Project name",
                value="My Construction Project",
                max_chars=100,
            )

            structure_type = st.selectbox(
                "Structure type",
                [
                    "Residential",
                    "Commercial",
                    "Industrial",
                ],
            )

            city = st.text_input(
                "City",
                value="Indore",
                max_chars=100,
            )

            city_tier = st.selectbox(
                "Location category",
                [
                    "Tier 1",
                    "Tier 2",
                    "Tier 3",
                ],
                index=1,
                help=(
                    "Used only for a configurable illustrative "
                    "property-value estimate."
                ),
            )

        with col2:
            area = st.number_input(
                "Built-up area (sq. ft.)",
                min_value=100.0,
                max_value=10000000.0,
                value=1500.0,
                step=100.0,
            )

            completion = st.slider(
                "Project completion (%)",
                min_value=0,
                max_value=100,
                value=35,
            )

            construction_rate = st.number_input(
                "Construction rate (₹ per sq. ft.)",
                min_value=100.0,
                max_value=100000.0,
                value=2000.0,
                step=100.0,
                help=(
                    "Enter your estimated local construction rate. "
                    "The default is illustrative, not a market quote."
                ),
            )

            contingency_percent = st.slider(
                "Contingency allowance (%)",
                min_value=0,
                max_value=30,
                value=10,
                help=(
                    "A reserve for unexpected expenses. "
                    "Adjust it according to project requirements."
                ),
            )

        st.subheader("2. Material Estimation Assumptions")

        material_col1, material_col2 = st.columns(2)

        with material_col1:
            cement_factor = st.number_input(
                "Cement factor (bags per sq. ft.)",
                min_value=0.0,
                max_value=10.0,
                value=0.40,
                step=0.05,
                help=(
                    "Illustrative planning factor only. Actual quantities "
                    "must be calculated from structural and architectural "
                    "drawings and the construction method."
                ),
            )

        with material_col2:
            steel_factor = st.number_input(
                "Steel factor (kg per sq. ft.)",
                min_value=0.0,
                max_value=100.0,
                value=4.0,
                step=0.5,
                help=(
                    "Illustrative planning factor only. Actual reinforcement "
                    "quantities require structural drawings and a bar "
                    "bending schedule."
                ),
            )

        st.subheader("3. Indicative Property Valuation")

        city_rates = {
            "Tier 1": 6000.0,
            "Tier 2": 4000.0,
            "Tier 3": 3000.0,
        }

        property_rate = st.number_input(
            "Assumed property value rate (₹ per sq. ft.)",
            min_value=100.0,
            max_value=1000000.0,
            value=city_rates[city_tier],
            step=500.0,
            help=(
                "Editable illustrative assumption. It is not a live "
                "property market valuation."
            ),
        )

        submitted = st.form_submit_button(
            "Calculate Project Estimates",
            type="primary",
            use_container_width=True,
        )

    # --------------------------------------------------------
    # CALCULATIONS AND RESULTS
    # --------------------------------------------------------

    if submitted:

        base_construction_cost = area * construction_rate

        contingency_amount = (
            base_construction_cost
            * contingency_percent
            / 100
        )

        total_estimated_budget = (
            base_construction_cost + contingency_amount
        )

        estimated_expenditure = (
            base_construction_cost * completion / 100
        )

        remaining_base_cost = (
            base_construction_cost - estimated_expenditure
        )

        estimated_cement_bags = area * cement_factor

        estimated_steel_kg = area * steel_factor

        estimated_property_value = area * property_rate

        # Save results so they remain visible during Streamlit reruns.
        planning_results = {
            "project_name": project_name.strip()
            or "Unnamed Construction Project",
            "structure_type": structure_type,
            "city": city.strip() or "Not specified",
            "location_category": city_tier,
            "built_up_area_sq_ft": round(area, 2),
            "completion_percentage": completion,
            "construction_rate_per_sq_ft": round(
                construction_rate, 2
            ),
            "base_construction_cost_inr": round(
                base_construction_cost, 2
            ),
            "contingency_percentage": contingency_percent,
            "contingency_amount_inr": round(
                contingency_amount, 2
            ),
            "total_estimated_budget_inr": round(
                total_estimated_budget, 2
            ),
            "estimated_expenditure_inr": round(
                estimated_expenditure, 2
            ),
            "remaining_base_construction_cost_inr": round(
                remaining_base_cost, 2
            ),
            "cement_factor_bags_per_sq_ft": cement_factor,
            "estimated_cement_bags": round(
                estimated_cement_bags, 2
            ),
            "steel_factor_kg_per_sq_ft": steel_factor,
            "estimated_steel_kg": round(
                estimated_steel_kg, 2
            ),
            "assumed_property_rate_per_sq_ft": round(
                property_rate, 2
            ),
            "indicative_property_value_inr": round(
                estimated_property_value, 2
            ),
            "calculation_notes": [
                "All figures are preliminary estimates.",
                "Expenditure is estimated from completion percentage; "
                "it is not actual recorded expenditure.",
                "Material factors are configurable assumptions, not "
                "a bill of quantities.",
                "Property value uses a manually assumed rate and "
                "is not a live market valuation.",
            ],
        }

        st.session_state["planning_results"] = planning_results

    # --------------------------------------------------------
    # DISPLAY SAVED RESULTS
    # --------------------------------------------------------

    if "planning_results" in st.session_state:

        result = st.session_state["planning_results"]

        st.divider()

        st.subheader("Project Estimate Results")

        st.caption(
            f"Project: {result['project_name']} · "
            f"Location: {result['city']}"
        )

        # Currency formatting in Indian number grouping.
        def format_inr(value):
            value = round(value)
            number = str(abs(value))

            if len(number) > 3:
                last_three = number[-3:]
                remaining = number[:-3]
                groups = []

                while len(remaining) > 2:
                    groups.insert(0, remaining[-2:])
                    remaining = remaining[:-2]

                if remaining:
                    groups.insert(0, remaining)

                formatted_number = (
                    ",".join(groups) + "," + last_three
                )
            else:
                formatted_number = number

            prefix = "-" if value < 0 else ""

            return f"{prefix}₹{formatted_number}"

        metric1, metric2 = st.columns(2)

        with metric1:
            st.metric(
                "Estimated Total Budget",
                format_inr(result["total_estimated_budget_inr"]),
            )

        with metric2:
            st.metric(
                "Estimated Expenditure",
                format_inr(result["estimated_expenditure_inr"]),
            )

        metric3, metric4 = st.columns(2)

        with metric3:
            st.metric(
                "Remaining Base Construction Cost",
                format_inr(
                    result["remaining_base_construction_cost_inr"]
                ),
            )

        with metric4:
            st.metric(
                "Indicative Property Value",
                format_inr(result["indicative_property_value_inr"]),
            )

        st.subheader("Budget Breakdown")

        breakdown_col1, breakdown_col2 = st.columns(2)

        with breakdown_col1:
            st.write(
                "**Base construction cost:**",
                format_inr(result["base_construction_cost_inr"]),
            )

            st.write(
                "**Contingency reserve:**",
                format_inr(result["contingency_amount_inr"]),
            )

            st.write(
                "**Total estimated budget:**",
                format_inr(result["total_estimated_budget_inr"]),
            )

        with breakdown_col2:
            st.write(
                "**Area:**",
                f"{result['built_up_area_sq_ft']:,.2f} sq. ft.",
            )

            st.write(
                "**Construction rate:**",
                format_inr(result["construction_rate_per_sq_ft"])
                + " per sq. ft.",
            )

            st.write(
                "**Project completion:**",
                f"{result['completion_percentage']}%",
            )

        st.subheader("Project Progress")

        st.progress(
            result["completion_percentage"] / 100
        )

        st.write(
            f"{result['completion_percentage']}% completed"
        )

        st.subheader("Illustrative Material Estimates")

        material_col1, material_col2 = st.columns(2)

        with material_col1:
            st.metric(
                "Estimated Cement",
                f"{result['estimated_cement_bags']:,.0f} bags",
            )

        with material_col2:
            st.metric(
                "Estimated Steel",
                f"{result['estimated_steel_kg']:,.0f} kg",
            )

        st.caption(
            "Material quantities are based on your editable factors. "
            "They are not suitable for ordering materials or structural "
            "design without verification against project drawings."
        )

        st.subheader("Property Valuation Assumptions")

        st.write(
            f"Assumed rate: "
            f"{format_inr(result['assumed_property_rate_per_sq_ft'])} "
            "per sq. ft."
        )

        st.write(
            f"Indicative property value: "
            f"{format_inr(result['indicative_property_value_inr'])}"
        )

        st.caption(
            "This calculation is not a market appraisal. Actual property "
            "value depends on locality, land value, age, specifications, "
            "approvals, condition and comparable sales."
        )

        # ----------------------------------------------------
        # DOWNLOAD REPORT
        # ----------------------------------------------------

        report = make_report(
            module="Planning & Valuation",
            data=result,
            mode="RULE_BASED_ESTIMATE",
        )

        show_download(
            report,
            "buildwise_planning_valuation_report.json",
        )

        if st.button(
            "Clear Planning Results",
            key="clear_planning_results",
        ):
            st.session_state.pop("planning_results", None)
            st.rerun()

elif page == "Daily Site Assistant":

    st.title("📋 Daily Site Assistant")

    st.write(
        "Get basic construction-site precautions and quick guidance "
        "for common site-management questions."
    )

    st.info(
        "This version uses predefined guidance. Weather conditions must "
        "be selected manually; the app does not fetch live weather data."
    )

    # --------------------------------------------------------
    # 1. WEATHER AND SITE PRECAUTIONS
    # --------------------------------------------------------

    st.subheader("🌦️ Weather-Based Site Precautions")

    with st.form("weather_precautions_form"):

        weather_condition = st.selectbox(
            "Current weather condition",
            [
                "Sunny / Hot",
                "Rainy",
                "Heavy Rain",
                "Windy",
                "Thunderstorm / Lightning",
                "Foggy / Low Visibility",
                "Normal / Mild",
            ],
        )

        work_activity = st.selectbox(
            "Main site activity",
            [
                "General Construction",
                "Concrete Pouring",
                "Working at Height",
                "Excavation",
                "Electrical Work",
                "Material Handling",
            ],
        )

        weather_submitted = st.form_submit_button(
            "Get Site Precautions",
            type="primary",
            use_container_width=True,
        )

    weather_guidance = {
        "Sunny / Hot": {
            "risk": "Heat stress and dehydration",
            "precautions": [
                "Provide drinking water and encourage regular hydration.",
                "Schedule suitable rest breaks in shaded or cool areas.",
                "Monitor workers for dizziness, confusion, weakness or other signs of heat illness.",
                "Use suitable sun protection and follow the site's heat-management plan.",
            ],
        },
        "Rainy": {
            "risk": "Slippery surfaces and water accumulation",
            "precautions": [
                "Inspect walkways and remove slip and trip hazards.",
                "Keep electrical equipment and connections protected from water.",
                "Check access routes, ladders and scaffolding before use.",
                "Protect cement and other moisture-sensitive materials.",
            ],
        },
        "Heavy Rain": {
            "risk": "Flooding, unstable ground and reduced visibility",
            "precautions": [
                "Pause affected activities when conditions become unsafe.",
                "Inspect excavations for water accumulation and possible collapse risks.",
                "Check temporary structures and access routes before restarting work.",
                "Keep personnel away from flooded electrical areas.",
                "Resume work only after the responsible site supervisor has assessed conditions.",
            ],
        },
        "Windy": {
            "risk": "Falling objects and unstable lifting operations",
            "precautions": [
                "Secure loose materials, sheets, tools and temporary coverings.",
                "Follow crane and lifting-equipment wind limits.",
                "Stop lifting or work-at-height activities when required by site procedures or equipment limits.",
                "Inspect temporary structures and exposed work areas.",
            ],
        },
        "Thunderstorm / Lightning": {
            "risk": "Lightning strike and electrical hazards",
            "precautions": [
                "Suspend exposed outdoor work when lightning threatens the site.",
                "Move personnel to a substantial enclosed shelter or suitable hard-topped vehicle.",
                "Avoid cranes, scaffolds, exposed metal structures and isolated tall objects during lightning risk.",
                "Follow the site's emergency plan and official weather warnings before resuming work.",
            ],
        },
        "Foggy / Low Visibility": {
            "risk": "Vehicle collisions and poor visibility",
            "precautions": [
                "Reduce vehicle speeds and maintain safe separation distances.",
                "Use appropriate warning signs, lighting and high-visibility clothing.",
                "Use trained spotters where required for reversing or moving equipment.",
                "Pause activities if operators cannot see workers, signals or hazards clearly.",
            ],
        },
        "Normal / Mild": {
            "risk": "Routine construction hazards",
            "precautions": [
                "Conduct the daily toolbox talk and site hazard review.",
                "Check required PPE before work begins.",
                "Keep access routes clear and materials properly stored.",
                "Inspect tools and equipment before use.",
            ],
        },
    }

    activity_guidance = {
        "General Construction": [
            "Maintain housekeeping and clearly marked access routes.",
            "Use PPE appropriate to the task and site risk assessment.",
        ],
        "Concrete Pouring": [
            "Inspect formwork and supports before pouring.",
            "Use suitable gloves and eye protection when handling wet concrete.",
            "Prevent skin contact with wet cement and provide washing facilities.",
        ],
        "Working at Height": [
            "Use suitable collective fall protection wherever practicable.",
            "Inspect working platforms and access equipment before use.",
            "Use required fall-arrest equipment and approved anchor arrangements.",
            "Do not work at height when conditions exceed site safety limits.",
        ],
        "Excavation": [
            "Check for underground utilities before excavation.",
            "Use appropriate protective systems where collapse is possible.",
            "Keep spoil piles and equipment away from excavation edges as required by the site plan.",
            "Inspect excavations after rain or changing ground conditions.",
        ],
        "Electrical Work": [
            "Use qualified personnel for electrical work.",
            "Isolate and verify energy sources before maintenance.",
            "Keep electrical equipment protected from moisture.",
            "Never handle damaged cables or exposed live conductors.",
        ],
        "Material Handling": [
            "Check load weight, lifting equipment and lifting accessories.",
            "Keep people clear of suspended loads.",
            "Use suitable lifting methods and trained personnel.",
            "Store materials securely to prevent rolling, sliding or collapse.",
        ],
    }

    if weather_submitted:

        selected_weather = weather_guidance[weather_condition]

        st.session_state["daily_site_weather_result"] = {
            "weather_condition": weather_condition,
            "work_activity": work_activity,
            "risk": selected_weather["risk"],
            "weather_precautions": selected_weather["precautions"],
            "activity_precautions": activity_guidance[work_activity],
        }

    if "daily_site_weather_result" in st.session_state:

        weather_result = st.session_state[
            "daily_site_weather_result"
        ]

        st.divider()

        st.subheader("Recommended Site Precautions")

        st.write(
            "**Selected weather:**",
            weather_result["weather_condition"],
        )

        st.write(
            "**Main activity:**",
            weather_result["work_activity"],
        )

        st.warning(
            f"Main weather-related concern: {weather_result['risk']}"
        )

        st.markdown("**Weather precautions**")

        for precaution in weather_result["weather_precautions"]:
            st.markdown(f"- {precaution}")

        st.markdown("**Activity-specific precautions**")

        for precaution in weather_result["activity_precautions"]:
            st.markdown(f"- {precaution}")

        weather_report = make_report(
            module="Daily Site Assistant - Weather Precautions",
            data=weather_result,
            mode="RULE_BASED_GUIDANCE",
        )

        show_download(
            weather_report,
            "buildwise_daily_site_precautions.json",
        )

    # --------------------------------------------------------
    # 2. CONSTRUCTION FAQ ASSISTANT
    # --------------------------------------------------------

    st.divider()

    st.subheader("💬 Construction FAQ Assistant")

    st.write(
        "Choose a common construction question to receive "
        "practical, predefined guidance."
    )

    construction_faq = {
        "What PPE should workers wear?": {
            "answer": (
                "PPE depends on the task and the site's risk assessment. "
                "Common equipment includes a suitable hard hat, safety "
                "footwear, high-visibility clothing and task-specific "
                "eye, hand, hearing or respiratory protection. Fall "
                "protection may be required for work at height."
            ),
            "category": "Personal Protective Equipment",
        },
        "How long should concrete be cured?": {
            "answer": (
                "Concrete curing depends on the mix, cement type, "
                "temperature, exposure and project specification. "
                "Seven days is a common minimum reference for many "
                "ordinary Portland cement applications under suitable "
                "conditions, but some mixes and specifications require "
                "different periods. Follow the approved mix design, "
                "applicable standards and engineer's instructions."
            ),
            "category": "Concrete Work",
        },
        "How should scaffolding be checked?": {
            "answer": (
                "Scaffolding should be erected, altered and inspected "
                "by competent personnel according to applicable rules "
                "and site procedures. Check foundations, ties, bracing, "
                "platforms, access, guardrails, toe boards and visible "
                "damage. Do not use a scaffold that is incomplete, "
                "damaged or marked unsafe."
            ),
            "category": "Work at Height",
        },
        "What should be checked before excavation?": {
            "answer": (
                "Confirm underground utilities, ground conditions, "
                "excavation layout, access and egress, nearby structures, "
                "water accumulation and spoil placement. Where collapse "
                "is possible, use a suitable protective system designed "
                "or selected by a competent person. Inspect after "
                "conditions change."
            ),
            "category": "Excavation Safety",
        },
        "How can cracks in a wall be assessed?": {
            "answer": (
                "Record the crack's location, pattern, approximate width "
                "using a suitable scale, and whether it changes over time. "
                "Look for displacement, water ingress, recurring cracks, "
                "corrosion or related movement. A photograph alone cannot "
                "establish structural safety. Ask a qualified structural "
                "engineer to assess significant, growing or concerning cracks."
            ),
            "category": "Crack Assessment",
        },
        "How can construction costs be controlled?": {
            "answer": (
                "Use approved drawings and a bill of quantities, compare "
                "planned costs with actual expenditure, track material "
                "wastage, record variations, check supplier quotations "
                "and update forecasts regularly. Keep contingency separate "
                "from ordinary expenditure and document changes."
            ),
            "category": "Project Management",
        },
        "What should a daily site inspection include?": {
            "answer": (
                "Review housekeeping, PPE, access routes, work-at-height "
                "protection, excavation conditions, lifting operations, "
                "electrical hazards, equipment condition, emergency "
                "access and changes in weather. Record findings, assign "
                "corrective actions and verify their completion."
            ),
            "category": "Site Inspection",
        },
    }

    selected_question = st.selectbox(
        "Select your question",
        list(construction_faq.keys()),
        key="construction_faq_question",
    )

    if st.button(
        "Get Answer",
        type="primary",
        key="get_construction_faq_answer",
    ):

        selected_answer = construction_faq[selected_question]

        st.session_state["daily_site_faq_result"] = {
            "question": selected_question,
            "category": selected_answer["category"],
            "answer": selected_answer["answer"],
        }

    if "daily_site_faq_result" in st.session_state:

        faq_result = st.session_state["daily_site_faq_result"]

        st.markdown("### Answer")

        st.caption(f"Category: {faq_result['category']}")

        st.write(faq_result["answer"])

        faq_report = make_report(
            module="Daily Site Assistant - Construction FAQ",
            data=faq_result,
            mode="RULE_BASED_GUIDANCE",
        )

        show_download(
            faq_report,
            "buildwise_construction_faq.json",
        )

    st.divider()

    st.caption(
        "Guidance is general and educational. Always follow the approved "
        "construction drawings, applicable regulations, site procedures "
        "and instructions from qualified professionals."
    )


# ============================================================
# 9. FOOTER
# ============================================================

st.divider()

st.markdown(
    """
    <div class="footer">
        BuildWise AI · Construction Intelligence Prototype<br>
        AI-generated observations are preliminary and require professional verification.
    </div>
    """,
    unsafe_allow_html=True,
)