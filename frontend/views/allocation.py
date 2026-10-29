"""Mass Allocation Setup View."""

import streamlit as st


def render_allocation_view():
    st.subheader("⚖️ Mass Allocation & Shared Utility Setup")
    st.caption("Under official CBAM rules, unmetered shared plant energy (lighting, boilers, auxiliary lines) must be apportioned using mass allocation.")

    if "allocation_data" not in st.session_state:
        st.session_state["allocation_data"] = {
            "target_production_tonnes": 500.0,
            "total_facility_production_tonnes": 625.0,
            "target_product_family": "Steel Fasteners (CN 7318 15 82)",
            "apply_allocation_to_shared_energy": True,
            "scrap_tonnes": 20.0,
        }

    alloc = st.session_state["allocation_data"]

    col1, col2 = st.columns(2)
    with col1:
        target_prod = st.number_input(
            "Net Production Quantity of Target Product (tonnes)",
            min_value=0.1,
            value=float(alloc["target_production_tonnes"]),
            step=10.0,
            format="%.2f",
            help="Net saleable volume of covered CBAM fasteners produced during the reporting period.",
        )
    with col2:
        total_prod = st.number_input(
            "Total Facility Production Across All Products (tonnes)",
            min_value=target_prod,
            value=max(target_prod, float(alloc["total_facility_production_tonnes"])),
            step=10.0,
            format="%.2f",
            help="Combined physical production volume of the entire plant / installation across all product lines.",
        )

    # Calculate alpha_p
    alpha_p = target_prod / total_prod if total_prod > 0 else 1.0

    st.markdown("#### 📊 Allocation Ratio Breakdown ($\alpha_p$)")
    m_col1, m_col2, m_col3 = st.columns(3)
    with m_col1:
        st.metric("Target Product Family Share", f"{alpha_p * 100:.2f}%")
    with m_col2:
        st.metric("Facility Remainder Share", f"{(1.0 - alpha_p) * 100:.2f}%")
    with m_col3:
        st.metric("Mass Allocation Factor (alpha_p)", f"{alpha_p:.4f}")

    st.progress(alpha_p, text=f"Target Share: {alpha_p * 100:.1f}% of plant throughput")

    st.markdown("---")
    st.markdown("#### ⚡ Shared Utility Policy Configuration")

    shared_toggle = st.toggle(
        "Apply Mass Allocation (alpha_p) to Shared Unmetered Utilities",
        value=alloc["apply_allocation_to_shared_energy"],
        help="If enabled, gross facility furnace oil and electricity bills will be multiplied by alpha_p to isolate emissions for the target product family.",
    )

    scrap_val = st.number_input(
        "Reported Production Scrap / Off-cuts (tonnes)",
        min_value=0.0,
        value=float(alloc.get("scrap_tonnes", 0.0)),
        step=5.0,
    )

    if st.button("💾 Save Allocation Parameters", type="primary", use_container_width=True):
        st.session_state["allocation_data"] = {
            "target_production_tonnes": target_prod,
            "total_facility_production_tonnes": total_prod,
            "target_product_family": st.session_state.get("workspace", {}).get("target_product_family", "Steel Fasteners"),
            "apply_allocation_to_shared_energy": shared_toggle,
            "scrap_tonnes": scrap_val,
            "alpha_p": alpha_p,
        }
        st.success(f"Allocation factor saved: alpha_p = {alpha_p:.4f}")
