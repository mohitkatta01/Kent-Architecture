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

# -------------------------- Load Model (cached) --------------------------
@st.cache_resource
def load_model():
    with st.spinner("Loading AI engine (first time only — ~15 seconds)..."):
        # Best model for job titles — understands meaning perfectly
        return SentenceTransformer("paraphrase-multilingual-MiniLM-L12-v2")

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

# -------------------------- Pre-compute embeddings (once) --------------------------
@st.cache_resource
def get_embeddings():
    titles = df["Client Job Title"].tolist()
    with st.spinner("Building smart search index..."):
        return model.encode(titles, batch_size=32, show_progress_bar=False)

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
        placeholder="e.g. Senior Drilling Engineer, Head of Projects, Lead HSE"
    )
    
    col1, col2 = st.columns(2)
    grade_options = sorted(df["Grade"].dropna().unique())
    country_options = sorted(df["Country"].dropna().unique())
    
    with col1:
        selected_grade = st.selectbox("Grade", ["All"] + grade_options.tolist())
    with col2:
        selected_country = st.selectbox("Country", ["All"] + country_options.tolist())

    submitted = st.form_submit_button("Search Mapping", type="primary", use_container_width=True)

# -------------------------- AI Search --------------------------
if submitted:
    if not client_role.strip():
        st.error("Please enter a client role.")
    else:
        st.session_state.submitted = True
        st.session_state.client_role = client_role.strip()
        query = client_role.strip()

        # Filter first
        filtered_df = df.copy()
        if selected_grade != "All":
            filtered_df = filtered_df[filtered_df["Grade"] == selected_grade]
        if selected_country != "All":
            filtered_df = filtered_df[filtered_df["Country"] == selected_country]

        if filtered_df.empty:
            st.warning("No titles match the selected filters.")
            st.stop()

        # Get query embedding
        query_emb = model.encode([query])

        # Get embeddings for filtered titles only
        filtered_titles = filtered_df["Client Job Title"].tolist()
        filtered_embs = model.encode(filtered_titles)

        # Cosine similarity
        sims = cosine_similarity(query_emb, filtered_embs)[0]
        top_idx = np.argsort(sims)[-3:][::-1]

        results = filtered_df.iloc[top_idx].copy()
        results["Probability"] = [f"{s:.1%}" for s in sims[top_idx]]

        # Force 100% on exact match
        exact_mask = results["clean_title"] == query.lower()
        results.loc[exact_mask, "Probability"] = "100%"

        cols = ["Client Job Title", "Position Title", "Grade", "Country", "Job Code", "Probability"]
        st.session_state.results = results[cols].reset_index(drop=True)

# -------------------------- Results --------------------------
if st.session_state.submitted:
    st.markdown("---")
    st.subheader(f"Results for: **{st.session_state.client_role}**")
    
    if st.session_state.results is not None and len(st.session_state.results) > 0:
        if st.session_state.results.iloc[0]["Probability"] == "100%":
            st.success("Exact match found!")
        else:
            st.info("AI-powered semantic search — showing best matches:")
        
        st.dataframe(st.session_state.results, use_container_width=True, hide_index=True)
        
        csv = st.session_state.results.to_csv(index=False).encode()
        st.download_button("Download Results", csv, "kent_title_mapping.csv", "text/csv")
    else:
        st.warning("No matches found.")

    if st.button("New Search", type="secondary"):
        st.session_state.clear()
        st.rerun()

st.markdown("---")
st.caption("Kent – AI-Powered Job Title Mapping • Live from Google Sheets • Semantic Search")