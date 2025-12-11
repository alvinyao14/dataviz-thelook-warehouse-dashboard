# tabs/tab_revenue.py

"""
Revenue Leakage tab

Goal:
    Calculate and visualize money lost to returns and cancellations
    so executives can see WHICH warehouses, products, and statuses
    are driving the most lost revenue and profit.

Expected columns in df:
    - is_revenue_lost (0/1)
    - sale_price
    - gross_margin
    - cost
    - category
    - dc_name
    - status
    - created_at
    - order_id
"""

import pandas as pd
import streamlit as st
import plotly.express as px


def _ensure_datetime(df: pd.DataFrame, col: str) -> pd.Series:
    """Safely convert a column to datetime if it isn't already."""
    if pd.api.types.is_datetime64_any_dtype(df[col]):
        return df[col]
    return pd.to_datetime(df[col], errors="coerce")


def render_tab(df: pd.DataFrame) -> None:
    """
    Render the Revenue Leakage tab.

    Parameters
    ----------
    df : pd.DataFrame
        Master dataset loaded by data_loader.py
    """

    st.header("Revenue Leakage Monitor")
    st.markdown("""
        **Overview:** This tab calculates and visualizes money lost to returns.
    """)

    # ------------------------------------------------------------------
    # 1. Filter to revenue lost rows
    # ------------------------------------------------------------------
    if "is_revenue_lost" not in df.columns:
        st.error("Column `is_revenue_lost` is missing from the dataset.")
        return

    lost_df = df[df["is_revenue_lost"] == 1].copy()

    if lost_df.empty:
        st.info("No revenue leakage rows found (is_revenue_lost == 1).")
        return

    # ------------------------------------------------------------------
    # 2. Ensure datetime & derive date range (fixes your TypeError)
    # ------------------------------------------------------------------
    if "created_at" not in lost_df.columns:
        st.error("Column `created_at` is required for date filtering.")
        return

    lost_df["created_at"] = _ensure_datetime(lost_df, "created_at")

    # Normalize to midnight timestamps for comparison
    order_date_ts = lost_df["created_at"].dt.normalize()
    lost_df["order_date"] = order_date_ts.dt.date  # for display / filtering

    # Use only non-null timestamps for min/max (this avoids the mixed-type error)
    valid_dates = order_date_ts.dropna()

    if valid_dates.empty:
        st.info("No valid `created_at` dates available for revenue leakage records.")
        return

    min_ts = valid_dates.min()
    max_ts = valid_dates.max()
    min_date = min_ts.date()
    max_date = max_ts.date()

    # =================================================================
    # Filters
    # =================================================================
       
    with st.expander("Filters", expanded=True):
        
        row1_col1, row1_col2 = st.columns(2)
        row2_col1, row2_col2 = st.columns(2)

        # --- Filter 1: Date Range (Top Left) ---
        with row1_col1:
            date_range = st.date_input(
                "Order date range",
                value=(min_date, max_date),
                min_value=min_date,
                max_value=max_date,
                key="rev_date_filter" # Unique key prevents conflict with other tabs
            )

        # --- Filter 2: Distribution Center (Top Right) ---
        with row1_col2:
            if "dc_name" in lost_df.columns:
                dc_options = sorted(lost_df["dc_name"].dropna().unique().tolist())
            else:
                dc_options = []
            
            selected_dcs = st.multiselect(
                "Distribution Centers",
                options=dc_options,
                default=dc_options,
                key="rev_dc_filter"
            )

        # --- Filter 3: Category (Bottom Left) ---
        with row2_col1:
            if "category" in lost_df.columns:
                cat_options = sorted(lost_df["category"].dropna().unique().tolist())
            else:
                cat_options = []

            selected_cats = st.multiselect(
                "Product Categories",
                options=cat_options,
                default=cat_options,
                key="rev_cat_filter"
            )

    # Date Logic
    if isinstance(date_range, tuple) and len(date_range) == 2:
        start_date, end_date = date_range
        mask_date = (lost_df["order_date"] >= start_date) & (lost_df["order_date"] <= end_date)
        lost_df = lost_df[mask_date]

    # DC Logic
    if selected_dcs and "dc_name" in lost_df.columns:
        lost_df = lost_df[lost_df["dc_name"].isin(selected_dcs)]

    # Category Logic
    if selected_cats and "category" in lost_df.columns:
        lost_df = lost_df[lost_df["category"].isin(selected_cats)]

    # Empty check
    if lost_df.empty:
        st.warning("No rows match the current filters.")
        return

    # =================================================================
    # 4. KPI Cards
    # =================================================================

    st.markdown(
        "These metrics quantify **money lost due to cancelled and returned orders** "
        "for the selected warehouses, categories, and time period."
    )

    total_lost_revenue = (
        lost_df["sale_price"].sum() if "sale_price" in lost_df.columns else 0.0
    )
    total_lost_margin = (
        lost_df["gross_margin"].sum() if "gross_margin" in lost_df.columns else 0.0
    )
    total_cost = lost_df["cost"].sum() if "cost" in lost_df.columns else 0.0
    num_leak_orders = (
        lost_df["order_id"].nunique()
        if "order_id" in lost_df.columns
        else len(lost_df)
    )

    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Lost Revenue (Top-line)", f"${total_lost_revenue:,.0f}")
    c2.metric("Lost Gross Margin", f"${total_lost_margin:,.0f}")
    c3.metric("Sunk Cost", f"${total_cost:,.0f}")
    c4.metric("Orders w/ Leakage", f"{num_leak_orders:,}")

    # ------------------------------------------------------------------
    # 5. Lost Revenue by DC & Status (stacked bar)
    # ------------------------------------------------------------------
    st.divider()
    st.subheader("Lost Revenue by Distribution Center")

    if {"dc_name", "status", "sale_price"}.issubset(lost_df.columns):
        dc_status = (
            lost_df.groupby(["dc_name", "status"], dropna=False)["sale_price"]
            .sum()
            .reset_index()
        )

        fig_dc = px.bar(
            dc_status,
            x="dc_name",
            y="sale_price",
            color="status",
            barmode="stack",
            labels={
                "dc_name": "Distribution Center",
                "sale_price": "Lost Revenue ($)",
                "status": "Status",
            },
            color_discrete_sequence=['#FFA500']

        )
        fig_dc.update_layout(
            xaxis_title="Distribution Center",
            yaxis_title="Lost Revenue ($)",
        )
        st.plotly_chart(fig_dc, use_container_width=True)
    else:
        st.info(
            "Missing one of: `dc_name`, `status`, `sale_price` – "
            "cannot plot DC breakdown."
        )

# ------------------------------------------------------------------
# 6. Category breakdown (bar or treemap)
# ------------------------------------------------------------------
    st.subheader("Lost Revenue by Product Category")

    if {"category", "sale_price"}.issubset(lost_df.columns):
        cat_rev = (
            lost_df.groupby("category", dropna=False)["sale_price"]
            .sum()
            .reset_index()
            .sort_values("sale_price", ascending=False)
        )

        view_type = st.radio(
            "Category View",
            options=["Bar Chart", "Treemap"],
            horizontal=True,
        )

        if view_type == "Bar Chart":
            fig_cat = px.bar(
                cat_rev,
                x="category",
                y="sale_price",
                # Optional: Use the same color scale for the bar chart too for consistency
                color="sale_price",
                color_continuous_scale="YlOrRd",
                labels={
                    "category": "Category",
                    "sale_price": "Lost Revenue ($)",
                },
            )
            fig_cat.update_layout(
                xaxis_title="Category",
                yaxis_title="Lost Revenue ($)",
                plot_bgcolor="#FFFFFF",
                paper_bgcolor="#FFFFFF",
            )
            st.plotly_chart(fig_cat, use_container_width=True)
            
        else: # TREEMAP VIEW
            fig_cat = px.treemap(
                cat_rev,
                path=[px.Constant(" "),"category"],
                values="sale_price",
                color="sale_price",              # Must map to a number for continuous scales
                color_continuous_scale="YlOrRd", # The Yellow-Orange-Red palette
                title="Lost Revenue by Product Category (Treemap)",
            )
            fig_cat.update_traces(root_color="rgba(0,0,0,0)")
            fig_cat.update_layout(
                plot_bgcolor="#FFFFFF",
                paper_bgcolor="#FFFFFF",
            )
            st.plotly_chart(fig_cat, use_container_width=True, theme=None)

    else:
        st.info(
            "Missing `category` or `sale_price` – cannot plot category breakdown."
        )

    # ------------------------------------------------------------------
    # 7. Detail Table: Top leaking orders
    # ------------------------------------------------------------------
    st.subheader("Top Leaking Orders (Detail View)")

    detail_cols = [
        col
        for col in [
            "order_id",
            "status",
            "dc_name",
            "category",
            "sale_price",
            "gross_margin",
            "cost",
            "order_date",
        ]
        if col in lost_df.columns
    ]

    detail_df = (
        lost_df[detail_cols]
        .sort_values("sale_price", ascending=False)
        .head(200)
        .reset_index(drop=True)
    )

    st.markdown("Showing up to 200 orders with the highest lost revenue.")
    st.dataframe(detail_df, use_container_width=True)
