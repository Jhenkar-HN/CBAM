"""Mass allocation inputs entered from the installation's production records."""

import streamlit as st


def _positive_number(raw: str, label: str) -> float:
    try:
        number = float(raw)
    except (TypeError, ValueError) as exc:
        raise ValueError(f"Enter {label} from your production records.") from exc
    if number <= 0:
        raise ValueError(f"{label} must be greater than zero.")
    return number


def render_allocation_view() -> None:
    st.subheader("Mass allocation & shared utility setup")
    st.caption("Enter production totals from the reporting period. The allocation factor is target product output divided by total installation output.")

    if not st.session_state.get("workspace"):
        st.info("Save the company, installation, reporting period, and product details first.")
        return

    alloc = st.session_state.get("allocation_data", {})
    target_text = st.text_input(
        "Net production quantity of target product (tonnes)",
        value=str(alloc.get("target_production_tonnes", "")),
        placeholder="From your production record",
    )
    total_text = st.text_input(
        "Total installation production (tonnes)",
        value=str(alloc.get("total_facility_production_tonnes", "")),
        placeholder="From your installation production record",
    )
    allocation_basis = [None, "shared", "product_only"]
    fuel_basis = st.selectbox(
        "Fuel record covers",
        allocation_basis,
        index=allocation_basis.index(alloc["fuel_allocation_basis"]) if alloc.get("fuel_allocation_basis") in allocation_basis else 0,
        format_func=lambda value: {None: "Select from your metering / invoice records", "shared": "Shared installation use", "product_only": "Target product line only"}[value],
    )
    electricity_basis = st.selectbox(
        "Electricity record covers",
        allocation_basis,
        index=allocation_basis.index(alloc["electricity_allocation_basis"]) if alloc.get("electricity_allocation_basis") in allocation_basis else 0,
        format_func=lambda value: {None: "Select from your metering / invoice records", "shared": "Shared installation use", "product_only": "Target product line only"}[value],
    )

    target = total = None
    try:
        target = _positive_number(target_text, "target product output")
        total = _positive_number(total_text, "total installation output")
        if target > total:
            raise ValueError("Target product output cannot exceed total installation output.")
        alpha = target / total
        left, middle, right = st.columns(3)
        left.metric("Target product share", f"{alpha:.2%}")
        middle.metric("Installation remainder", f"{1 - alpha:.2%}")
        right.metric("Allocation factor αₚ", f"{alpha:.4f}")
        st.progress(alpha, text=f"Allocation factor: {alpha:.2%}")
    except ValueError as exc:
        st.info(str(exc))

    if st.button("Save allocation parameters", type="primary", use_container_width=True):
        if target is None or total is None or fuel_basis is None or electricity_basis is None:
            st.error("Enter production quantities and allocation basis for both utility records before saving.")
            return
        st.session_state["allocation_data"] = {
            "target_production_tonnes": target,
            "total_facility_production_tonnes": total,
            "fuel_allocation_basis": fuel_basis,
            "electricity_allocation_basis": electricity_basis,
            "apply_allocation_to_shared_energy": fuel_basis == "shared" or electricity_basis == "shared",
            "alpha_p": target / total,
        }
        st.success("Production quantities saved.")
