import streamlit as st

def render_tab(df):
    st.header("Feature Under Construction 🚧")
    st.write("This feature is being developed.")
    
    # Simple data check to prove connection works
    st.write(f"Data available for analysis: {len(df)} rows")
    st.dataframe(df.head())