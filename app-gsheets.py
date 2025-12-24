import streamlit as st
import pandas as pd
from rapidfuzz import process, fuzz

# -------------------------- Page Config --------------------------
st.set_page_config(
    page_title="Kent - Indicative Title Mapping",
    page_icon="search",
    layout="centered",
    initial_sidebar_state="expanded"
)

st.title("Kent – Indicative Title Mapping")
st.markdown("---")

# -------------------------- Load Data from Google Sheets --------------------------
@st.cache_data(ttl=600)  # Refreshes max every 10 minutes
def load_data():
    # Your published Google Sheet CSV URL (kept safe in secrets)
    url = st.secrets["DATA_URL"]
    
    try:
        df = pd.read_csv(url)
    except Exception as e:
        st.error("Could not load the latest job title database. Please contact the admin.")
        st.stop()
    
    df.columns = df.columns.str.strip()
    required = ["Client Job Title", "Position Title", "Grade", "Country", "Job Code"]
    if not all(col in df.columns for col in required):
        st.error(f"Google Sheet is missing columns: {required}")
        st.stop()
    
    df = df.dropna(subset=["Client Job Title"]).copy()
    df["clean_title"] = df["Client Job Title"].str.strip().str.lower()
    return df

df = load_data()

# -------------------------- Session State --------------------------
if "submitted" not in st.session_state:
    st.session_state.submitted = False
    st.session_state.client_role = ""
    st.session_state.results = None

# -------------------------- Main Form --------------------------
with st.form("mapping_form"):
    st.markdown("### Enter Client Job Title")
    client_role = st.text_input(
        "Client Role *",
        placeholder="e.g. Senior Drilling Engineer, Lead Process Engineer, Project Manager",
        help="Type the exact or approximate job title"
    )
    
    st.markdown("#### Optional Filters")
    col1, col2 = st.columns(2)
    
    grade_options = sorted(df["Grade"].unique().tolist())
    country_options = sorted(df["Country"].unique().tolist())
    
    with col1:
        selected_grade = st.selectbox("Grade", ["All"] + grade_options)
    with col2:
        selected_country = st.selectbox("Country", ["All"] + country_options)

    submitted = st.form_submit_button("Search Mapping", type="primary", use_container_width=True)

# -------------------------- Search Logic --------------------------
if submitted:
    if not client_role.strip():
        st.error("Please enter a client role.")
    else:
        st.session_state.submitted = True
        st.session_state.client_role = client_role.strip()
        
        query = client_role.strip().lower()
        
        # Apply filters
        mask = pd.Series([True] * len(df))
        if selected_grade != "All":
            mask &= (df["Grade"] == selected_grade)
        if selected_country != "All":
            mask &= (df["Country"] == selected_country)
        filtered = df[mask].copy()
        
        # Exact match?
        exact = filtered[filtered["clean_title"] == query]
        if not exact.empty:
            results = exact.copy()
            results["Probability"] = "100%"
        else:
            # Fuzzy top 3
            choices = filtered["clean_title"].tolist()
            matches = process.extract(query, choices, scorer=fuzz.token_sort_ratio, limit=3)
            indices = [m[2] for m in matches]
            scores = [m[1] for m in matches]
            results = filtered.iloc[indices].copy()
            results["Probability"] = [f"{s:.1f}%" for s in scores]
        
        st.session_state.results = results[["Position Title", "Grade", "Country", "Job Code", "Probability"]].reset_index(drop=True)

# -------------------------- Show Results --------------------------
if st.session_state.submitted:
    st.markdown("---")
    st.subheader(f"Results for: **{st.session_state.client_role}**")
    
    if st.session_state.results is not None and len(st.session_state.results) > 0:
        if st.session_state.results.iloc[0]["Probability"] == "100%":
            st.success("Exact match found!")
        else:
            st.info("Showing top 3 closest matches:")
        
        st.dataframe(st.session_state.results, use_container_width=True, hide_index=True)
        
        csv = st.session_state.results.to_csv(index=False).encode()
        st.download_button("Download Results", csv, "kent_title_mapping.csv", "text/csv")
    else:
        st.warning("No matches found with current filters.")
    
    if st.button("New Search", type="secondary"):
        st.session_state.clear()
        st.rerun()

# -------------------------- Footer --------------------------
st.markdown("---")
st.caption("Kent – Indicative Title Mapping Tool • Live data from Google Sheets • Always up-to-date")