import streamlit as st
from data_loader import load_data

# Import the tab modules
from tabs import tab_exceptions, tab_network, tab_revenue, tab_dead_stock

st.set_page_config(page_title="TheLook Warehouse Dashboard", layout="wide")

# 1. Load Data
df = load_data()

if not df.empty:
    st.title("📦 TheLook Warehouse Fulfillment Dashboard")
    
    # 2. Create the Tab Structure
    tab1, tab2, tab3, tab4= st.tabs([
        "🚨 Fulfillment Exceptions", 
        "🌍 Delivery Network",  
        "🏚️ Dead Stock",
        "💸 Revenue Leakage"
    ])

    # 3. Render Tabs
    with tab1:
        tab_exceptions.render_tab(df)
        
    with tab2:
        tab_network.render_tab(df)
        
    with tab3:
        tab_dead_stock.render_tab(df)

    with tab4:
        tab_revenue.render_tab(df)

else:
    st.warning("Please place 'warehouse_data.csv' in the 'data/' folder to begin.")