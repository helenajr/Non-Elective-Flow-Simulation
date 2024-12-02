import streamlit as st

pg = st.navigation([
        st.Page("home_page.py", title="Welcome!", icon=":material/add_circle:"),
        st.Page("app.py", title="Run Simulation", icon=":material/laptop:")
     ])

pg.run()