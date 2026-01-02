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

st.title("Kent – Indicative Title Mapping")
st.markdown("---")

# -------------------------- Load BEST Model (cached) --------------------------
@st.cache_resource
def load_model():
    # Best model for job titles: understands meaning, synonyms, hierarchy
    return SentenceTransformer('paraphrase-multilingual-MiniLM-L12-v2')

model = load_model()

# -------------------------- Load Data --------------------------
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

# Pre-compute embeddings once (super fast after first load)
@st.cache_resource
def get_embeddings():
    with st.spinner("Preparing smart matching engine... (first load only)"):
        titles = df["Client Job Title"].tolist()
        embeddings = model.encode(titles, show_progress_bar=False)
    return embeddings

embeddings = get_embeddings()

# -------------------------- Session State --------------------------
if "submitted" not in st.session_state:
    st.session_state.submitted = False
    st.session_state.client_role = ""
    st.session_state.results = None

# -------------------------- Form --------------------------
with st.form("mapping_form"):
    st.markdown("### Enter Client Job Title")
    client_role = st.text_input(
        "Client Role *",
        placeholder="e.g. Senior Drilling Engineer, Head of Projects, Lead HSE Advisor"
    )
    
    st.markdown("#### Optional Filters")
    col1, col2 = st.columns(2)
    grade_options = sorted(df["Grade"].dropna().unique().tolist())
    country_options = sorted(df["Country"].dropna().unique().tolist())
    
    with col1:
        selected_grade = st.selectbox("Grade", ["All"] + grade_options)
    with col2:
        selected_country = st.selectbox("Country", ["All"] + country_options)

    submitted = st.form_submit_button("Search Mapping", type="primary", use_container_width=True)

# -------------------------- Smart Search --------------------------
if submitted:
    if not client_role.strip():
        st.error("Please enter a client role.")
    else:
        st.session_state.submitted = True
        st.session_state.client_role = client_role.strip()
        query = client_role.strip()

        # Apply filters first
        filtered_df = df.copy()
        if selected_grade != "All":
            filtered_df = filtered_df[filtered_df["Grade"] == selected_grade]
        if selected_country != "All":
            filtered_df = filtered_df[filtered_df["Country"] == selected_country]

        if filtered_df.empty:
            st.warning("No titles match the selected filters.")
            st.stop()

        # Get query embedding
        query_emb = model.encode([query], show_progress_bar=False)

        # Get embeddings for filtered titles only
        filtered_titles = filtered_df["Client Job Title"].tolist()
        filtered_embs = model.encode(filtered_titles, show_progress_bar=False)

        # Compute similarity
        similarities = cosine_similarity(query_emb, filtered_embs)[0]
        
        # Get top 3
        top_idx = np.argsort(similarities)[-3:][::-1]
        top_scores = similarities[top_idx]
        
        results = filtered_df.iloc[top_idx].copy()
        results["Probability"] = [f"{score:.1%}" for score in top_scores]
        
        # Exact match override?
        exact_match = results[results["clean_title"] == query.lower()]
        if not exact_match.empty:
            results.loc[exact_match.index, "Probability"] = "100%"

        display_cols = ["Client Job Title", "Position Title", "Grade", "Country", "Job Code", "Probability"]
        st.session_state.results = results[display_cols].reset_index(drop=True)

# -------------------------- Results --------------------------
if st.session_state.submitted:
    st.markdown("---")
    st.subheader(f"Results for: **{st.session_state.client_role}**")
    
    if st.session_state.results is not None and len(st.session_state.results) > 0:
        if st.session_state.results.iloc[0]["Probability"] == "100%":
            st.success("Exact match found!")
        else:
            st.info("Powered by AI semantic search – showing best matches:")
        
        st.dataframe(st.session_state.results, use_container_width=True, hide_index=True)
        
        csv = st.session_state.results.to_csv(index=False).encode()
        st.download_button("Download Results", csv, "kent_title_mapping.csv", "text/csv")
    else:
        st.warning("No matches found.")

    if st.button("New Search", type="secondary"):
        st.session_state.clear()
        st.rerun()

# -------------------------- Footer --------------------------
st.markdown("---")
st.caption("Kent – Indicative Title Mapping • AI-Powered Semantic Search • Live from Google Sheets")