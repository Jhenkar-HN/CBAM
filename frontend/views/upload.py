"""Multi-Format Upload & Ingestion View."""

import requests
import streamlit as st
from app.modules.document_ai.extractor import run_document_ai_extraction

API_BASE_URL = "http://localhost:8000/api/v1"


def render_upload_view():
    st.subheader("📤 Document Ingestion & Cryptographic Ledger")
    st.caption("Upload factory invoices, power bills, mill certificates, and weighbridge logs. Each document is cryptographically hashed with SHA-256.")

    if "uploaded_documents" not in st.session_state:
        st.session_state["uploaded_documents"] = {}

    # File uploader
    uploaded_files = st.file_uploader(
        "Choose raw business records (PDF, Scanned Image, CSV, Excel)",
        type=["pdf", "png", "jpg", "jpeg", "csv", "xlsx", "xls"],
        accept_multiple_files=True,
    )

    # Ingestion button
    if uploaded_files:
        for file_obj in uploaded_files:
            file_bytes = file_obj.getvalue()
            filename = file_obj.name

            # Check if already processed
            already_processed = any(
                doc.get("filename") == filename
                for doc in st.session_state["uploaded_documents"].values()
            )

            if not already_processed:
                with st.spinner(f"Ingesting & extracting: {filename}..."):
                    extraction_data = None

                    # 1. Try FastAPI endpoint
                    try:
                        files = {"file": (filename, file_bytes, file_obj.type or "application/octet-stream")}
                        data = {"workspace_id": st.session_state.get("workspace", {}).get("installation_id", "default_workspace")}
                        resp = requests.post(f"{API_BASE_URL}/documents/upload", files=files, data=data, timeout=5)
                        if resp.status_code == 201:
                            extraction_data = resp.json()
                    except Exception:
                        pass

                    # 2. Local fallback if API is not running as a daemon
                    if not extraction_data:
                        result_obj = run_document_ai_extraction(file_bytes, filename)
                        extraction_data = result_obj.model_dump()

                    # Save to session state
                    doc_hash = extraction_data["document_hash"]
                    st.session_state["uploaded_documents"][doc_hash] = {
                        "filename": filename,
                        "document_hash": doc_hash,
                        "file_size_bytes": len(file_bytes),
                        "page_count": extraction_data.get("page_count", 1),
                        "extracted_fields": extraction_data.get("extracted_fields", []),
                    }
                    st.toast(f"Parsed {filename}", icon="✅")

    # Ingestion Manifest / Ledger Table
    docs = st.session_state["uploaded_documents"]
    if docs:
        st.markdown("### 📋 Cryptographic Document Ledger (SHA-256)")
        for doc_hash, doc in docs.items():
            with st.expander(f"📄 {doc['filename']} ({doc['file_size_bytes'] / 1024:.1f} KB)", expanded=True):
                meta_col1, meta_col2 = st.columns([3, 1])
                with meta_col1:
                    st.code(f"SHA-256: {doc['document_hash']}", language="bash")
                with meta_col2:
                    st.metric("Candidate Fields", len(doc["extracted_fields"]))

                if doc["extracted_fields"]:
                    st.markdown("**Extracted Candidates:**")
                    table_rows = []
                    for f in doc["extracted_fields"]:
                        table_rows.append({
                            "Field Name": f["field_name"],
                            "Quantity": f["extracted_value"],
                            "Unit": f["unit"],
                            "Confidence": f"{f['confidence_score'] * 100:.0f}%",
                            "Page": f["evidence_page"],
                            "Verbatim Snippet": f["evidence_snippet"],
                        })
                    st.dataframe(table_rows, use_container_width=True)
                else:
                    st.info("No numerical activity candidates identified in this file.")

    else:
        st.info("No documents uploaded yet. Upload your factory electricity bills, fuel receipts, or production sheets above.")

        # Quick Demo Loader
        st.markdown("---")
        st.markdown("##### 🧪 Or Load Pre-Populated Benchmark Documents for Steel Fasteners")
        if st.button("📥 Load Benchmark Document Suite (Cold Forging Fasteners)"):
            # Synthetic document 1: Electricity invoice
            doc1_text = "DHBVN Power Bill - Active Energy Consumption: 250,000 kWh for billing month October 2026."
            res1 = run_document_ai_extraction(doc1_text.encode("utf-8"), "DHBVN_Electricity_Oct2026.csv")

            # Synthetic document 2: Furnace oil slip
            doc2_text = "Indian Oil Delivery Challan - Furnace Oil Dispatched: 15,000 litres. Density 0.94."
            res2 = run_document_ai_extraction(doc2_text.encode("utf-8"), "IOCL_Furnace_Oil_Invoice.csv")

            # Synthetic document 3: Wire rod cert
            doc3_text = "Jindal Steel Mill Cert - Precursor Wire Rod: 520 tonnes alloy steel grade 10B21."
            res3 = run_document_ai_extraction(doc3_text.encode("utf-8"), "Steel_Wire_Rod_Mill_Cert.csv")

            # Synthetic document 4: Production output
            doc4_text = "Plant Weighbridge & Packing Summary: Net Production Output: 500 tonnes of Cold Forged Screws."
            res4 = run_document_ai_extraction(doc4_text.encode("utf-8"), "Factory_Production_Summary.csv")

            for res in [res1, res2, res3, res4]:
                st.session_state["uploaded_documents"][res.document_hash] = {
                    "filename": res.filename,
                    "document_hash": res.document_hash,
                    "file_size_bytes": 1024,
                    "page_count": 1,
                    "extracted_fields": [f.model_dump() for f in res.extracted_fields],
                }
            st.success("Loaded 4 benchmark documents into cryptographic ledger!")
            st.rerun()
