import streamlit as st
import pandas as pd

# We use @st.cache_data so the app doesn't reload the 50MB CSV every time you click a button.
@st.cache_data
def load_data(filepath='data/BigQuery_Output_20251206_v1.csv'):
    """
    Loads the Master Dataset and enforces correct data types.
    """
    try:
        df = pd.read_csv(filepath)
        
        # 1. Convert Timestamp columns from Strings to Datetime objects
        # Using errors='coerce' turns invalid dates (like "NULL") into NaT (Not a Time) automatically.
        date_cols = ['created_at', 'shipped_at', 'delivered_at', 'inventory_stocked_at']
        
        for col in date_cols:
            if col in df.columns:
                df[col] = pd.to_datetime(df[col], errors='coerce')

        return df
    
    except FileNotFoundError:
        st.error(f"⚠️ Could not find the file: {filepath}. Please export your BigQuery results to the 'data/' folder.")
        return pd.DataFrame() # Return empty DF to prevent app crash