
import json
from datetime import datetime

import streamlit as st
from PIL import Image

st.set_page_config(
    page_title="BuildWise AI",
    page_icon="🏗️",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ---------- Styling ----------
st.markdown("""
<style>
.stApp {
    background-color: #f5f7fb;
}
.block-container {
    padding-top: 2rem;
    padding-bottom: 2rem;
    max-width: 1400px;
}
[data-testid="stMetric"] {
    background: white;
    border: 1px solid #e1e7ef;
    border-radius: 12px;
    padding: 18px;
}
div[data-testid="stVerticalBlockBorderWrapper"] {
    background: white;
    border-radius: 12px;
}
h1, h2, h3 {
    color: #172b4d;
}
</style>
""", unsafe_allow_html=True)


# ---------- Helpers ----------
def make_report(module, data):
    return {
        "application": "BuildWise AI",
        "module": module,
        "generated_at": datetime.now().isoformat(timespec="seconds"),
        "mode": "DEMO - Not AI-verified",
        "disclaimer": (
            "This report is illustrative and is not a certified "
            "construction, safety, structural, or valuation assessment."
        ),
        "results": data,
    }


def show_download(report, filename):
    st.download_button(
        "⬇️ Download JSON report",
        data=json.dumps(report, indent=2, ensure_ascii=False),
        file_name=filename,
        mime="application/json",
        use_container_width=True,
    )


def show_image(upload):
    if upload is not None:
        try:
            image = Image.open(upload).convert("RGB")
            st.image(image, caption="Uploaded image",
                     use_container_width=True)
            return image
        except Exception:
            st.error("This image could not be opened. Please try another JPG or PNG.")
    return None


# ---------- Sidebar ----------
with st.sidebar:
    st.markdown("# 🏗️ BuildWise AI")
    st.caption("Construction Intelligence Platform")
    st.divider()

    page = st.radio(
        "NAVIGATION",
        [
            "Dashboard",
            "Site Safety & PPE Audit",
            "Crack Diagnostics",
            "Planning & Valuation",
            "Daily Site Assistant",
        ],
    )

    st.divider()
    st.markdown("### System status")
    st.success("Application running")
    st.info("AI mode: Demonstration")
    st.caption("No API key or database required for this demo.")
    st.caption("SkillWallet Capstone Project 1")


# ---------- Header ----------
st.title("🏗️ BuildWise AI")
st.caption("Multimodal Construction Intelligence Platform")
st.markdown(
    "An interactive prototype for construction safety, "
    "surface inspection, project estimation and daily site guidance."
)

# ---------- Dashboard ----------
if page == "Dashboard":
    st.subheader("Project Overview")

    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Core Modules", "4")
    c2.metric("Database", "Not required")
    c3.metric("AI Integration", "Demo mode")
    c4.metric("Estimated API Cost", "₹0")

    st.markdown("### Your construction workspace")

    modules = [
        (
            "🦺 Site Safety & PPE Audit",
            "Review an uploaded site photograph and view a sample "
            "PPE checklist and hazard report.",
        ),
        (
            "🧱 Crack Diagnostics",
            "Preview a surface photograph and explore a sample "
            "preliminary defect report.",
        ),
        (
            "📐 Planning & Valuation",
            "Estimate a construction budget, material quantities "
            "and indicative property value.",
        ),
        (
            "🌦️ Daily Site Assistant",
            "Explore weather-related precautions and ask a "
            "construction-related question.",
        ),
    ]

    cols = st.columns(2)
    for i, (title, description) in enumerate(modules):
        with cols[i % 2]:
            with st.container(border=True):
                st.markdown(f"### {title}")
                st.write(description)

    st.markdown("### Getting started")
    st.write(
        "Select a module from the sidebar. Start with an image upload "
        "or enter your project details. The image reports in this version "
        "are illustrative examples, not actual AI image recognition."
    )

    st.warning(
        "Safety notice: This prototype does not certify PPE compliance, "
        "structural integrity, construction costs or property valuations. "
        "Consult qualified professionals before making real-world decisions."
    )


# ---------- Site Safety ----------
elif page == "Site Safety & PPE Audit":
    st.subheader("🦺 Site Safety & PPE Audit")
    st.write(
        "Upload a site photograph to preview it and generate a clearly "
        "labeled demonstration report."
    )

    upload = st.file_uploader(
        "Choose a construction-site image",
        type=["jpg", "jpeg", "png"],
        key="safety_upload",
    )

    if upload:
        image = show_image(upload)

        if image is not None:
            st.info(
                "DEMO MODE: The following sample findings are not "
                "derived from your uploaded photograph."
            )

            if st.button("Generate sample safety report",
                         type="primary"):
                report_data = {
                    "safety_score": 75,
                    "overall_status": "Sample assessment - review required",
                    "ppe_detection": {
                        "helmet": "Not verified",
                        "high_visibility_vest": "Not verified",
                        "safety_boots": "Not verified",
                        "safety_harness": "Not verified",
                    },
                    "hazards": [
                        {
                            "hazard": "Unprotected elevated work area",
                            "severity": "High",
                            "remedy": (
                                "Have a qualified site supervisor inspect "
                                "edge protection and fall-prevention controls."
                            ),
                        },
                        {
                            "hazard": "Housekeeping and trip risks",
                            "severity": "Medium",
                            "remedy": (
                                "Inspect walkways and remove obstructions "
                                "using approved site procedures."
                            ),
                        },
                    ],
                    "assessment_note": (
                        "Illustrative sample only. No actual hazards "
                        "or PPE items have been detected."
                    ),
                }

                st.session_state.safety_report = make_report(
                    "Site Safety & PPE Audit", report_data
                )

            if "safety_report" in st.session_state:
                report = st.session_state.safety_report
                result = report["results"]

                a, b = st.columns(2)
                a.metric("Sample Safety Score",
                         f"{result['safety_score']}/100")
                b.metric("Sample Hazards", len(result["hazards"]))

                st.markdown("### PPE checklist")
                st.json(result["ppe_detection"])

                st.markdown("### Illustrative hazards")
                for hazard in result["hazards"]:
                    with st.container(border=True):
                        st.markdown(
                            f"**{hazard['hazard']}** — "
                            f"{hazard['severity']}"
                        )
                        st.write(hazard["remedy"])

                st.warning(result["assessment_note"])
                show_download(report, "buildwise_safety_report.json")


# ---------- Crack Diagnostics ----------
elif page == "Crack Diagnostics":
    st.subheader("🧱 Crack Diagnostics")
    st.write(
        "Upload a wall or concrete photograph to preview the image "
        "and explore a sample preliminary inspection report."
    )

    upload = st.file_uploader(
        "Choose a concrete or wall image",
        type=["jpg", "jpeg", "png"],
        key="crack_upload",
    )

    if upload:
        image = show_image(upload)

        if image is not None:
            st.info(
                "DEMO MODE: The sample defect below has not been "
                "identified from your photograph."
            )

            if st.button("Generate sample crack report",
                         type="primary"):
                report_data = {
                    "defect_type": "Hairline crack - illustrative example",
                    "estimated_width_mm": None,
                    "width_note": (
                        "Not measured. A photograph without a calibrated "
                        "reference scale cannot establish actual crack width."
                    ),
                    "severity": "Undetermined",
                    "possible_causes": [
                        "Drying shrinkage",
                        "Thermal movement",
                        "Settlement or structural movement",
                    ],
                    "recommended_next_steps": [
                        "Arrange an inspection by a qualified structural engineer.",
                        "Document crack location, length and changes over time.",
                        "Check for water ingress, displacement and related damage.",
                    ],
                    "urgency": "Professional review required",
                    "assessment_note": (
                        "Illustrative example only. No crack has been "
                        "classified from the uploaded photograph."
                    ),
                }

                st.session_state.crack_report = make_report(
                    "Crack Diagnostics", report_data
                )

            if "crack_report" in st.session_state:
                report = st.session_state.crack_report
                result = report["results"]

                st.markdown("### Preliminary report example")
                st.markdown(f"**Defect category:** {result['defect_type']}")
                st.markdown(f"**Severity:** {result['severity']}")
                st.markdown(f"**Urgency:** {result['urgency']}")

                st.markdown("**Possible causes to investigate**")
                for cause in result["possible_causes"]:
                    st.write(f"- {cause}")

                st.markdown("**Recommended next steps**")
                for action in result["recommended_next_steps"]:
                    st.write(f"- {action}")

                st.caption(result["width_note"])
                st.warning(result["assessment_note"])
                show_download(report, "buildwise_crack_report.json")


# ---------- Planning & Valuation ----------
elif page == "Planning & Valuation":
    st.subheader("📐 Project Planning & Real Estate Valuation")
    st.write(
        "Calculate indicative costs using editable assumptions. "
        "These rates are examples, not current market quotations."
    )

    with st.form("planning_form"):
        structure = st.selectbox(
            "Structure type",
            ["Residential", "Commercial", "Industrial"],
        )

        city = st.text_input(
            "City or location",
            value="Indore, Madhya Pradesh",
        )

        tier = st.selectbox(
            "City tier",
            ["Tier 1", "Tier 2", "Tier 3"],
            index=1,
        )

        area = st.number_input(
            "Built-up area (sq ft)",
            min_value=100,
            max_value=1000000,
            value=1200,
            step=100,
        )

        completion = st.slider(
            "Construction completion (%)",
            min_value=0,
            max_value=100,
            value=25,
        )

        rates = {
            "Residential": 2000,
            "Commercial": 2800,
            "Industrial": 1700,
        }

        default_rate = rates[structure]
        construction_rate = st.number_input(
            "Assumed construction rate (₹/sq ft)",
            min_value=500,
            max_value=20000,
            value=default_rate,
            step=100,
        )

        material_buffer = st.slider(
            "Contingency (%)",
            min_value=0,
            max_value=30,
            value=10,
        )

        submitted = st.form_submit_button(
            "Calculate project estimates",
            type="primary",
            use_container_width=True,
        )

    if submitted:
        base_cost = area * construction_rate
        contingency = base_cost * material_buffer / 100
        total_budget = base_cost + contingency
        incurred = total_budget * completion / 100

        # Illustrative material planning assumptions only.
        cement_bags = area * 0.4
        steel_kg = area * 4.0

        # Explicitly illustrative valuation multiplier.
        valuation_rate = {
            "Tier 1": 6000,
            "Tier 2": 4000,
            "Tier 3": 3000,
        }[tier]

        estimated_property_value = area * valuation_rate

        st.markdown("### Estimated project metrics")
        a, b = st.columns(2)
        a.metric("Indicative construction budget",
                 f"₹{total_budget:,.0f}")
        b.metric("Estimated cost incurred",
                 f"₹{incurred:,.0f}")

        c, d = st.columns(2)
        c.metric("Illustrative cement quantity",
                 f"{cement_bags:,.0f} bags")
        d.metric("Illustrative steel quantity",
                 f"{steel_kg:,.0f} kg")

        st.markdown("### Indicative property valuation")
        st.metric("Estimated property value",
                  f"₹{estimated_property_value:,.0f}")
        st.caption(
            "The property value uses an illustrative rate per square foot. "
            "It is not a verified market valuation for your location."
        )

        st.markdown("### Construction milestone")
        st.progress(completion / 100)
        st.write(f"Reported completion: {completion}%")

        planning_report = make_report(
            "Planning & Valuation",
            {
                "structure_type": structure,
                "location": city,
                "city_tier": tier,
                "area_sqft": area,
                "completion_percent": completion,
                "construction_rate_inr_per_sqft": construction_rate,
                "contingency_percent": material_buffer,
                "estimated_budget_inr": round(total_budget, 2),
                "estimated_cost_incurred_inr": round(incurred, 2),
                "illustrative_cement_bags": round(cement_bags),
                "illustrative_steel_kg": round(steel_kg),
                "assumed_property_rate_inr_per_sqft": valuation_rate,
                "illustrative_property_value_inr": round(
                    estimated_property_value, 2
                ),
                "limitations": (
                    "Material quantities depend on structural design, "
                    "foundation, concrete grade and other specifications. "
                    "Property values require local market evidence."
                ),
            },
        )

        show_download(planning_report, "buildwise_planning_report.json")


# ---------- Daily Assistant ----------
elif page == "Daily Site Assistant":
    st.subheader("🌦️ Daily Site Assistant")
    st.write(
        "Select the observed weather condition for general site precautions."
    )

    weather_advice = {
        "Normal": (
            "Continue routine site inspections, follow the approved safety "
            "plan, and verify equipment and access routes."
        ),
        "High Wind": (
            "Check equipment-specific wind limits and site procedures. "
            "Suspend crane or elevated operations when required by the "
            "manufacturer, supervisor or site safety plan."
        ),
        "Heavy Rain": (
            "Inspect drainage, excavation stability, slippery walkways "
            "and electrical equipment. Restrict unsafe access."
        ),
        "Extreme Heat": (
            "Provide drinking water, shade, appropriate rest breaks "
            "and heat-stress monitoring. Follow local heat safety guidance."
        ),
    }

    weather = st.selectbox(
        "Observed weather condition",
        list(weather_advice.keys()),
    )

    st.markdown("### Weather advisory")
    st.warning(weather_advice[weather])
    st.caption(
        "Weather is manually selected. This prototype does not retrieve "
        "live weather data."
    )

    st.divider()
    st.markdown("### Construction Q&A assistant")
    st.caption(
        "Demonstration assistant with predefined general guidance; "
        "not connected to a live language model yet."
    )

    if "chat_messages" not in st.session_state:
        st.session_state.chat_messages = []

    for message in st.session_state.chat_messages:
        with st.chat_message(message["role"]):
            st.write(message["content"])

    question = st.chat_input(
        "Ask about site inspections, PPE or project planning..."
    )

    if question:
        st.session_state.chat_messages.append(
            {"role": "user", "content": question}
        )

        q = question.lower()

        if any(word in q for word in ["helmet", "ppe", "safety", "hazard"]):
            answer = (
                "Demo guidance: Inspect required PPE, access routes, "
                "guardrails, housekeeping and task-specific hazards. "
                "Follow the approved site safety plan and have a qualified "
                "supervisor verify site conditions."
            )
        elif any(word in q for word in ["crack", "concrete", "wall", "structure"]):
            answer = (
                "Demo guidance: Record the defect location and changes "
                "over time. If cracking is widening, displaced, associated "
                "with deformation, or otherwise concerning, restrict "
                "potentially unsafe access and seek a qualified structural "
                "engineer's assessment."
            )
        elif any(word in q for word in ["cost", "budget", "cement", "steel"]):
            answer = (
                "Use the Planning & Valuation module for illustrative "
                "estimates. Actual quantities and costs require project "
                "drawings, specifications, local quotations and professional "
                "quantity estimation."
            )
        else:
            answer = (
                "This demo assistant supports general construction topics. "
                "For site-specific decisions, consult the responsible "
                "engineer and approved site procedures. Live AI answers "
                "will be integrated in a later version."
            )

        st.session_state.chat_messages.append(
            {"role": "assistant", "content": answer}
        )
        st.rerun()

    if st.button("Clear conversation"):
        st.session_state.chat_messages = []
        st.rerun()


# ---------- Footer ----------
st.divider()
st.caption(
    "BuildWise AI | SkillWallet Capstone Project 1 | "
    "Prototype and demonstration mode"
)
