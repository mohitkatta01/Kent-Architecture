import streamlit as st

# Set page configuration
st.set_page_config(
    page_title="Kent - Indicative title mapping",
    page_icon="🔍",
    layout="centered"
)

# Title of the application
st.title("Kent - Indicative title mapping")

# Add some spacing
st.markdown("---")

# Initialize session state for storing selections
if 'submitted' not in st.session_state:
    st.session_state.submitted = False
    st.session_state.client_role = ""
    st.session_state.dropdown1_selection = None
    st.session_state.dropdown2_selection = None

# Create the form
with st.form("mapping_form"):
    # Text input for client role (mandatory)
    client_role = st.text_input(
        "Client Role *",
        placeholder="Enter client role here...",
        help="Please enter the client's role or job title (This field is required)"
    )
    
    # Add some spacing
    st.markdown("")
    
    # Create two columns for the dropdown boxes
    col1, col2 = st.columns(2)
    
    # Dropdown options (you can update these later)
    grade_options=["L1","L2","L3","L4","A1","A2","A3","A4","P1","P2","P3","P4","P5","P6","M1","M2","M3","M4","PM1","PM2","PM3","PM4","EM1","EM2","EM3"]

    with col1:
        # First dropdown with search functionality
        dropdown1 = st.selectbox(
            "Select Grade",
            options=["None"] + grade_options,
            index=0,
            help="Start typing to search through options"
        )
    
    country_options = ["Australia", "Azerbaijan", "Austria","Brunei","Canada","Colombia","Germany","India","Iraq","Kuwait","Netherlands","Trinidad","United Arab Emirates","United Kingdom","United States"]

    with col2:
        # Second dropdown with search functionality
        dropdown2 = st.selectbox(
            "Select Country",
            options=["None"] + country_options,
            index=0,
            help="Start typing to search through options"
        ) 
    
    # Add some spacing before the button
    st.markdown("")
    
    # Submit button
    submitted = st.form_submit_button("Submit", type="primary", use_container_width=True)

# Handle form submission
if submitted:
    # Check if mandatory field is filled
    if client_role.strip():
        st.session_state.submitted = True
        st.session_state.client_role = client_role
        st.session_state.dropdown1_selection = dropdown1 if dropdown1 != "None" else None
        st.session_state.dropdown2_selection = dropdown2 if dropdown2 != "None" else None
    else:
        st.error("⚠️ Please enter a Client Role. This field is mandatory.")

# Display the results if form was submitted successfully
if st.session_state.submitted:
    st.markdown("---")
    st.subheader("📋 Your Selections:")
    
    # Create a container for better formatting
    with st.container():
        st.write("**Client Role:**", st.session_state.client_role)
        
        col1, col2 = st.columns(2)
        with col1:
            st.write("**Option 1:**", 
                    st.session_state.dropdown1_selection if st.session_state.dropdown1_selection else "Not selected")
        with col2:
            st.write("**Option 2:**", 
                    st.session_state.dropdown2_selection if st.session_state.dropdown2_selection else "Not selected")
    
    # Add a button to reset the form
    if st.button("Clear and Start Over", type="secondary"):
        st.session_state.submitted = False
        st.session_state.client_role = ""
        st.session_state.dropdown1_selection = None
        st.session_state.dropdown2_selection = None
        st.rerun()

# Add footer
st.markdown("---")
st.caption("Kent - Indicative Title Mapping Tool v1.0")