import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go

DEFAULT_AGE_THRESHOLD = 90

def render_tab(df: pd.DataFrame):


    st.header("Dead Stock Report (Aging Inventory)")
    st.markdown("""
        **Overview:** This tab aggregates and visualizes the aging inventory across different categories and distribution centers.
    """)


    # ============================================================
    # FILTERS (Collapsible Card)
    # ============================================================
    with st.expander("Filters", expanded=True):
        
        # 1. Deadstock Age Threshold (Slider)
        age_threshold = st.slider(
            "Dead stock threshold (days in inventory)",
            min_value=30, 
            max_value=730, 
            value=DEFAULT_AGE_THRESHOLD, 
            step=30,
            help="Items older than this number of days will be flagged as Dead Stock.",
            key="ds_threshold_slider"
        )

        st.markdown("---")

        # 2. Category & Distribution Center Filters (MultiSelect)
        col1, col2 = st.columns(2)

        with col1:
            # Define the full list first
            all_cats = sorted(df["category"].dropna().unique())
            
            categories = st.multiselect(
                "Filter by category",
                options=all_cats,
                default=all_cats,
                key="ds_category_filter"
            )

        with col2:
            # Define the full list first
            all_dcs = sorted(df["dc_name"].dropna().unique())
            
            dcs = st.multiselect(
                "Filter by distribution center",
                options=all_dcs,
                default=all_dcs,
                key="ds_dc_filter"
            )

    # LOGIC: Apply Filters
    inv_df = df.copy()

    if categories:
        inv_df = inv_df[inv_df["category"].isin(categories)]
    else:
        pass 

    # Apply DC Filter
    if dcs:
        inv_df = inv_df[inv_df["dc_name"].isin(dcs)]
    else:
        pass

    # Apply Threshold Definition
    dead = inv_df[inv_df["inventory_age_days"] >= age_threshold]

    # CALCULATIONS: KPIs
    col1, col2, col3 = st.columns(3)
    col1.metric("Dead stock items", f"{len(dead):,}")

    avg_age = dead["inventory_age_days"].mean() if not dead.empty else None
    col2.metric("Avg age (days)", f"{avg_age:.0f}" if avg_age is not None else "–")

    pct_dead = (len(dead) / len(inv_df) * 100) if len(inv_df) > 0 else None
    col3.metric("Dead stock as % of inventory",
                f"{pct_dead:.1f}%" if pct_dead is not None else "–")

    # ============================================================
    # Visualization 1: Stacked bar (Category x DC)
    # ============================================================
    st.divider()
    st.subheader(f"Dead Stock (≥ {age_threshold} Days) by Category and Distribution Center")
    
    if dead.empty:
        st.info("No items meet the dead-stock threshold with current filters.")
        return

    agg = (
        dead.groupby(["category", "dc_name"])
        .size()
        .reset_index(name="dead_stock_count")
    )

    # Sort categories by total dead stock
    total_by_cat = (
        agg.groupby("category")["dead_stock_count"]
        .sum()
        .sort_values(ascending=False)
    )
    cat_order = total_by_cat.index.tolist()
    agg["category"] = pd.Categorical(agg["category"], categories=cat_order, ordered=True)

    # COLOR MAPPING (Matched to Network Tab)
    dc_color_map = {
        # Northeast (Blues/Purples)
        'Port Authority of New York/New Jersey NY/NJ': '#0064ff', # Royal Blue
        'Philadelphia PA': '#8a2be2',                             # Blue Violet
        'Charleston SC': '#4682b4',                               # Steel Blue

        # Midwest (Greens)
        'Chicago IL': '#228b22',                                  # Forest Green
        'Memphis TN': '#32cd32',                                  # Lime Green

        # South (Reds/Oranges)
        'Houston TX': '#ff4500',                                  # Red-Orange
        'New Orleans LA': '#ff8c00',                              # Dark Orange
        'Savannah GA': '#dc143c',                                 # Crimson
        'Mobile AL': '#ffa500',                                   # Orange

        # West (Pinks/Purples)
        'Los Angeles CA': '#c71585',                              # Medium Violet Red
    }

    fig1 = px.bar(
        agg,
        x="category",
        y="dead_stock_count",
        color="dc_name",
        color_discrete_map=dc_color_map, 
        category_orders={"category": cat_order},
    )
    
    fig1.update_layout(
        xaxis_title="Product Category",
        yaxis_title="Count of Dead Stock Items",
        xaxis_tickangle=-45,
        legend_title="Distribution Center",
        plot_bgcolor="#FFFFFF",
        paper_bgcolor="#FFFFFF",
    )
    
    st.plotly_chart(fig1, use_container_width=True)

    # ============================================================
    # Visualization 2: Pareto chart (Category priorities)
    # ============================================================
    st.divider()
    st.subheader("Pareto Chart of Dead Stock by Category")

    cat_df = (
        dead.groupby("category")["inventory_age_days"]
        .count()
        .reset_index(name="dead_count")
        .sort_values("dead_count", ascending=False)
    )
    cat_df["cum_pct"] = cat_df["dead_count"].cumsum() / cat_df["dead_count"].sum() * 100

    fig2 = go.Figure()
    fig2.add_bar(
        x=cat_df["category"],
        y=cat_df["dead_count"],
        name="Dead Stock Count",
        marker_color="#DC143C",
    )
    fig2.add_scatter(
        x=cat_df["category"],
        y=cat_df["cum_pct"],
        name="Cumulative %",
        mode="lines+markers",
        marker=dict(color="#FFA500", size=6),
        line=dict(color="#FFA500", width=3),
        yaxis="y2",
    )
    fig2.add_shape(
        type="line",
        x0=-0.5,
        x1=len(cat_df) - 0.5,
        y0=80,
        y1=80,
        yref="y2",
        line=dict(color="#AAAAAA", width=2, dash="dash"),
    )
    fig2.update_layout(
        xaxis=dict(title="Category", tickangle=-45),
        yaxis=dict(title="Dead Stock Volume"),
        yaxis2=dict(
            title="Cumulative %",
            overlaying="y",
            side="right",
            range=[0, 110],
        ),
        plot_bgcolor="#FFFFFF",
        paper_bgcolor="#FFFFFF",
        legend=dict(
            orientation="h",
            yanchor="bottom",
            y=1.05,
            xanchor="center",
            x=0.5,
        ),
    )
    st.plotly_chart(fig2, use_container_width=True)

    # ============================================================
    # Visualization 3: Treemap (Age buckets x Category)
    # ============================================================
    st.divider()
    st.subheader("Inventory Age Distribution by Category (Treemap)")
    st.markdown("""
        Map Guide: Click on the age bucket to filter the treemap by that range.
    """)

    bins = [0, 30, 60, 90, 180, 365, 99999]
    labels = ["0-30", "30-60", "60-90", "90-180", "180-365", "365+"]

    inv_df = inv_df.copy()
    inv_df["age_bucket"] = pd.cut(
        inv_df["inventory_age_days"], bins=bins, labels=labels, right=False
    )

    fig3 = px.treemap(
        inv_df,
        path=["age_bucket", "category"],
        values="inventory_age_days",
        color="age_bucket",
        color_discrete_map={
            "0-30":   "#FFE0B2",  
            "30-60":  "#FFCC80",  
            "60-90":  "#FFA500",  
            "90-180": "#FF8A65",  
            "180-365":"#FF6B6B",  
            "365+":   "#C62828",  
        }
    )
    fig3.update_layout(
        paper_bgcolor="#FFFFFF",
        plot_bgcolor="#FFFFFF",
    )
    st.plotly_chart(fig3, use_container_width=True)

    # Optional: table of oldest items
    with st.expander("**View oldest items (top 50)**"):
        cols = [
            "inventory_stocked_at",
            "inventory_age_days",
            "category",
            "dc_name",
            "status",
            "sale_price",
            "cost",
        ]
        existing_cols = [c for c in cols if c in dead.columns]
        st.dataframe(
            dead[existing_cols]
            .sort_values("inventory_age_days", ascending=False)
            .head(50)
        )
