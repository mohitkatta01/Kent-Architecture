# app.py
import streamlit as st
import pandas as pd
import os
from rapidfuzz import process, fuzz

# -------------------------- Page Config --------------------------
st.set_page_config(
    page_title="Kent - Indicative Title Mapping",
    page_icon="search",
    layout="centered"
)

st.title("Kent - Indicative Title Mapping")
st.markdown("---")

# -------------------------- Load Data --------------------------
@st.cache_resource
def load_data():
    # Change this to your actual file name
    file_path = "data.csv"          # or "data.csv"
    
    if not os.path.exists(file_path):
        st.error(f"Data file not found: `{file_path}`\n\n"
                 "Please make sure your Excel/CSV file is in the same folder as this script "
                 "and is named exactly `data.xlsx` (or change the filename above).")
        st.stop()
    
    # Load Excel or CSV
    if file_path.lower().endswith(('.xlsx', '.xls')):
        df = pd.read_excel(file_path)
    else:
        df = pd.read_csv(file_path)
    
    # Clean column names
    df.columns = df.columns.str.strip()
    
    required_columns = ["Client Job Title", "Position Title", "Grade", "Country", "Job Code"]
    missing = [col for col in required_columns if col not in df.columns]
    if missing:
        st.error(f"Missing required columns: {missing}")
        st.stop()
    
    # Clean data
    df = df.dropna(subset=["Client Job Title"]).copy()
    df["clean_title"] = df["Client Job Title"].str.strip().str.lower()
    
    return df

df = load_data()

# -------------------------- Session State --------------------------
if "submitted" not in st.session_state:
    st.session_state.submitted = False
    st.session_state.client_role = ""
    st.session_state.results = None

# -------------------------- Form --------------------------
with st.form("mapping_form"):
    client_role = st.text_input(
        "Client Role *",
        placeholder="e.g. Senior Drilling Engineer, Lead Process Engineer, Project Manager",
        help="Enter the exact or approximate job title of the client"
    )
    
    st.markdown("")
    col1, col2 = st.columns(2)
    
    # Grade & Country options (feel free to edit)
    grade_options = ["L1","L2","L3","L4","A1","A2","A3","A4","P1","P2","P3","P4","P5","P6",
                     "M1","M2","M3","M4","PM1","PM2","PM3","PM4","EM1","EM2","EM3"]
    country_options = ["Australia","Azerbaijan","Austria","Brunei","Canada","Colombia",
                       "Germany","India","Iraq","Kuwait","Netherlands","Trinidad",
                       "United Arab Emirates","United Kingdom","United States"]

    with col1:
        selected_grade = st.selectbox("Filter by Grade (optional)", ["All"] + grade_options, index=0)
    with col2:
        selected_country = st.selectbox("Filter by Country (optional)", ["All"] + country_options, index=0)

    st.markdown("")
    submitted = st.form_submit_button("Submit", type="primary", use_container_width=True)

# -------------------------- Processing --------------------------
if submitted:
    if not client_role.strip():
        st.error("Please enter a Client Role.")
    else:
        st.session_state.submitted = True
        st.session_state.client_role = client_role.strip()
        
        query = client_role.strip().lower()
        
        # Apply optional filters
        mask = pd.Series([True] * len(df))
        if selected_grade != "All":
            mask &= (df["Grade"] == selected_grade)
        if selected_country != "All":
            mask &= (df["Country"] == selected_country)
        
        filtered_df = df[mask].copy()
        
        # Exact match first
        exact_matches = filtered_df[filtered_df["clean_title"] == query]
        if not exact_matches.empty:
            results = exact_matches.copy()
            results["Probability"] = "100%"
            st.session_state.results = results[["Position Title", "Grade", "Country", "Job Code", "Probability"]]
        else:
            # Fuzzy matching – top 3
            choices = filtered_df["clean_title"].tolist()
            matches = process.extract(
                query,
                choices,
                scorer=fuzz.token_sort_ratio,   # very good for job titles
                limit=3
            )
            indices = [m[2] for m in matches]
            scores  = [m[1] for m in matches]   # already out of 100
            
            results = filtered_df.iloc[indices].copy()
            results["Probability"] = [f"{score:.1f}%" for score in scores]
            st.session_state.results = results[["Position Title", "Grade", "Country", "Job Code", "Probability"]].reset_index(drop=True)

# -------------------------- Display Results --------------------------
if st.session_state.submitted:
    st.markdown("---")
    st.subheader(f"Results for: **{st.session_state.client_role}**")
    
    if st.session_state.results is not None:
        if len(st.session_state.results) > 0 and st.session_state.results.iloc[0]["Probability"] == "100%":
            st.success("Exact match found!")
        else:
            st.info("No exact match – showing the 3 closest titles:")
        
        st.dataframe(
            st.session_state.results,
            use_container_width=True,
            hide_index=True
        )
        
        # Download button
        csv = st.session_state.results.to_csv(index=False).encode()
        st.download_button(
            label="Download Results as CSV",
            data=csv,
            file_name="kent_title_mapping_results.csv",
            mime="text/csv"
        )
    
    if st.button("Clear and Start Over", type="secondary"):
        st.session_state.submitted = False
        st.session_state.client_role = ""
        st.session_state.results = None
        st.rerun()

# -------------------------- Footer --------------------------
st.markdown("---")
st.caption("Kent – Indicative Title Mapping Tool v2.0 | Powered by RapidFuzz (no ML dependencies)")