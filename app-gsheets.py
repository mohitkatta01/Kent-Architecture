# app.py
import streamlit as st
import pandas as pd
import numpy as np
from sentence_transformers import SentenceTransformer
from sklearn.metrics.pairwise import cosine_similarity

# -------------------------- Page Config --------------------------
st.set_page_config(
    page_title="Kent - Indicative Title Mapping",
    page_icon="search",
    layout="centered",
    initial_sidebar_state="expanded"
)

st.title("Kent – AI-Powered Title Mapping")
st.markdown("---")

# -------------------------- Load AI Model (cached) --------------------------
@st.cache_resource
def load_model():
    with st.spinner("Loading AI engine (first run only – ~15 seconds)..."):
        return SentenceTransformer("paraphrase-multilingual-MiniLM-L12-v2")

model = load_model()

# -------------------------- Load Data from Google Sheets --------------------------
@st.cache_data(ttl=600)
def load_data():
    url = st.secrets["DATA_URL"]
    df = pd.read_csv(url)
    
    df = df.dropna(how='all').reset_index(drop=True)
    df = df[df["Client Job Title"].notna() & (df["Client Job Title"].str.strip() != "")]
    df.columns = df.columns.str.strip()
    
    required = ["Client Job Title", "Position Title", "Grade", "Country", "Job Code"]
    if not all(col in df.columns for col in required):
        st.error(f"Missing columns: {required}")
        st.stop()
    
    df["clean_title"] = df["Client Job Title"].str.strip().str.lower()
    return df.reset_index(drop=True)

df = load_data()

# -------------------------- Pre-compute embeddings --------------------------
@st.cache_resource
def get_embeddings():
    titles = df["Client Job Title"].tolist()
    with st.spinner("Building AI search index..."):
        return model.encode(titles, batch_size=32, show_progress_bar=False)

embeddings = get_embeddings()

# -------------------------- Session State --------------------------
if "results" not in st.session_state:
    st.session_state.results = None
    st.session_state.client_role = ""

# -------------------------- FORM (NOW WITH WORKING SUBMIT BUTTON) --------------------------
with st.form("mapping_form"):
    st.markdown("### Enter Client Job Title")
    client_role = st.text_input(
        "Client Role *",
        placeholder="e.g. Senior Drilling Engineer, Lead Process, Head of Projects"
    )
    
    st.markdown("#### Optional Filters")
    col1, col2 = st.columns(2)
    
    # Safe way to get unique values
    grades = ["All"] + sorted(df["Grade"].dropna().unique().tolist())
    countries = ["All"] + sorted(df["Country"].dropna().unique().tolist())
    
    with col1:
        selected_grade = st.selectbox("Grade", grades)
    with col2:
        selected_country = st.selectbox("Country", countries)

    # THIS WAS MISSING → NOW FIXED!
    submitted = st.form_submit_button("Search Mapping", type="primary", use_container_width=True)

# -------------------------- AI SEARCH LOGIC --------------------------
if submitted:
    if not client_role.strip():
        st.error("Please enter a client role.")
    else:
        st.session_state.client_role = client_role.strip()
        query = client_role.strip()

        # Apply filters
        filtered_df = df.copy()
        if selected_grade != "All":
            filtered_df = filtered_df[filtered_df["Grade"] == selected_grade]
        if selected_country != "All":
            filtered_df = filtered_df[filtered_df["Country"] == selected_country]

        if filtered_df.empty:
            st.warning("No titles match the selected filters.")
        else:
            # AI semantic search
            query_emb = model.encode([query])
            filtered_titles = filtered_df["Client Job Title"].tolist()
            filtered_embs = model.encode(filtered_titles)
            sims = cosine_similarity(query_emb, filtered_embs)[0]
            
            top_idx = np.argsort(sims)[-3:][::-1]
            results = filtered_df.iloc[top_idx].copy()
            results["Probability"] = [f"{s:.1%}" for s in sims[top_idx]]
            
            # Force 100% on exact match
            results.loc[results["clean_title"] == query.lower(), "Probability"] = "100%"
            
            cols = ["Client Job Title", "Position Title", "Grade", "Country", "Job Code", "Probability"]
            st.session_state.results = results[cols].reset_index(drop=True)

# -------------------------- DISPLAY RESULTS --------------------------
if st.session_state.results is not None:
    st.markdown("---")
    st.subheader(f"Results for: **{st.session_state.client_role}**")
    
    if len(st.session_state.results) > 0:
        if st.session_state.results.iloc[0]["Probability"] == "100%":
            st.success("Exact match found!")
        else:
            st.info("AI-powered semantic search – showing top 3 matches:")
        
        st.dataframe(st.session_state.results, use_container_width=True, hide_index=True)
        
        csv = st.session_state.results.to_csv(index=False).encode()
        st.download_button("Download Results", csv, "kent_title_mapping.csv", "text/csv")
    else:
        st.warning("No matches found.")

    if st.button("New Search", type="secondary"):
        st.session_state.results = None
        st.session_state.client_role = ""
        st.rerun()

# -------------------------- Footer --------------------------
st.markdown("---")
st.caption("Kent – AI-Powered Job Title Mapping • Live from Google Sheets • Semantic Search Engine")