import streamlit as st
import pandas as pd
import pydeck as pdk
import plotly.express as px
import plotly.graph_objects as go

def render_tab(df):
    """
    Network Topology Tab
    Purpose: Visualize the warehouse-to-customer delivery flow to identify
    inefficiencies (e.g., distant DCs fulfilling nearby customer orders)

    Key Columns Used:
    - dc_name, dc_lat, dc_long (Distribution Center info)
    - customer_lat, customer_long (Customer delivery location)
    - order_id (To count volume/thickness of flows)
    """

    st.header("Delivery Network Topology")
    st.markdown("""
    **Overview:** This tab visualizes the network of delivery destinations by distribution center.
    """)

    # ============================================================
    # DATA VALIDATION & PREPARATION
    # ============================================================
    required_cols = ['dc_name', 'dc_lat', 'dc_long', 'customer_lat', 'customer_long', 'order_id']
    missing_cols = [col for col in required_cols if col not in df.columns]

    if missing_cols:
        st.error(f"Missing required columns: {missing_cols}")
        st.info("This tab requires: dc_name, dc_lat, dc_long, customer_lat, customer_long, order_id")
        return

    # Filter out rows with missing geo coordinates
    df_clean = df.dropna(subset=['dc_lat', 'dc_long', 'customer_lat', 'customer_long']).copy()

    if df_clean.empty:
        st.warning("No valid geographic data available.")
        return

    # ============================================================
    # FILTERS
    # ============================================================
    with st.expander("Filters", expanded=True):
        
        col1, col2 = st.columns(2)

        # Define dc_options OUTSIDE the column so it's available globally if needed
        dc_options = sorted(df_clean['dc_name'].dropna().unique().tolist())

        with col1:
            # Multiselect Widget
            selected_dcs = st.multiselect(
                "Select Distribution Centers", 
                options=dc_options,
                default=dc_options, 
                key="net_dc_select"
            )

        # --- LOGIC: Filter Dataframe ---
        if selected_dcs:
            df_filtered = df_clean[df_clean['dc_name'].isin(selected_dcs)].copy()
        else:
            df_filtered = df_clean.copy() # Fallback to ALL if empty

        with col2:
            # Safety: Ensure slider doesn't crash if filtered data is very small
            available_rows = len(df_filtered)
            safe_max_value = max(available_rows, 100) 
            
            max_orders = st.slider(
                "Max Orders to Display (Map Only)", # Clarified Label
                min_value=100,
                max_value=safe_max_value,
                value=min(5000, available_rows),
                step=500,
                key="net_slider",
                help="Limits the points on the map for performance. Metrics below still use ALL data."
            )

    # --- LOGIC: Final Slice for Display ---
    # FIX: Use .sample() instead of .head() to randomize the selection.
    # random_state=42 ensures the map doesn't 'flicker' on every interaction.
    if len(df_filtered) > max_orders:
        df_display = df_filtered.sample(n=max_orders, random_state=42).copy()
    else:
        df_display = df_filtered.copy()

    # ============================================================
    # KEY METRICS
    # ============================================================
    col1, col2, col3, col4 = st.columns(4)

    with col1:
        st.metric("Total Orders", f"{len(df_filtered):,}")

    with col2:
        st.metric("Active DCs", df_filtered['dc_name'].nunique())

    with col3:
        avg_distance = calculate_avg_distance(df_filtered)
        st.metric("Avg Shipping Distance", f"{avg_distance:.0f} km")

    with col4:
        unique_customers = df_filtered[['customer_lat', 'customer_long']].drop_duplicates()
        st.metric("Unique Delivery Locations", f"{len(unique_customers):,}")

    # ============================================================
    # MAIN VISUALIZATION: PYDECK MAP
    # ============================================================
    st.divider()   
    st.subheader("Distribution Center to Destination Location Dot Map")

    # Prepare Customer data - each point is an order
    customer_data = df_display[['customer_lat', 'customer_long', 'dc_name', 'order_id']].copy()
    customer_data['color'] = customer_data['dc_name'].apply(lambda x: get_dc_color(x, dc_options))

    # Calculate optimal zoom level and center
    center_lat = customer_data['customer_lat'].mean()
    center_lon = customer_data['customer_long'].mean()

    lat_range = customer_data['customer_lat'].max() - customer_data['customer_lat'].min()
    lon_range = customer_data['customer_long'].max() - customer_data['customer_long'].min()

    # Heuristic: larger range = lower zoom
    if max(lat_range, lon_range) > 100:
        zoom_level = 1
    elif max(lat_range, lon_range) > 50:
        zoom_level = 2
    elif max(lat_range, lon_range) > 20:
        zoom_level = 3
    elif max(lat_range, lon_range) > 10:
        zoom_level = 4
    else:
        zoom_level = 5

    # Create the map view
    view_state = pdk.ViewState(
        latitude=center_lat,
        longitude=center_lon,
        zoom=zoom_level,
        pitch=0,
    )

    # Create separate heatmap layers for each DC (to show density in DC-specific colors)
    heatmap_layers = []
    unique_dcs = customer_data['dc_name'].unique()

    for dc_name in unique_dcs:
        dc_orders = customer_data[customer_data['dc_name'] == dc_name]
        dc_color_rgb = get_dc_color(dc_name, dc_options)

        # Use the DC's actual color for high-density hexagons
        base_color = dc_color_rgb[:3]  # RGB without alpha

        heatmap_layer = pdk.Layer(
            "HexagonLayer",
            data=dc_orders,
            get_position='[customer_long, customer_lat]',
            radius=50000,
            elevation_scale=50,
            elevation_range=[0, 1000],
            pickable=True,
            extruded=False,
            coverage=0.9,
            get_fill_color=base_color,  # Use DC color directly
            get_line_color=[255, 255, 255, 100],
            opacity=0.5,
            colorRange=[
                base_color,  # Low density
                base_color,  # Medium density
                base_color,  # High density
                base_color,  # Higher density
                [max(0, base_color[0] - 50), max(0, base_color[1] - 50), max(0, base_color[2] - 50)],  # Very high density (darker)
                [max(0, base_color[0] - 80), max(0, base_color[1] - 80), max(0, base_color[2] - 80)],  # Highest density (darkest)
            ],
        )
        heatmap_layers.append(heatmap_layer)

    # Layer: Customer Delivery Points (colored by DC)
    customer_layer = pdk.Layer(
        "ScatterplotLayer",
        data=customer_data,
        get_position='[customer_long, customer_lat]',
        get_color='color',
        get_radius=10000,
        pickable=True,
        opacity=0.7,
        filled=True,
    )

    # Create tooltip
    tooltip = {
        "html": "<b>DC:</b> {dc_name}<br/><b>Order ID:</b> {order_id}",
        "style": {"backgroundColor": "steelblue", "color": "white"}
    }

    # Render the map with all layers
    all_layers = heatmap_layers + [customer_layer]

    deck = pdk.Deck(
        layers=all_layers,
        initial_view_state=view_state,
        tooltip=tooltip,
        map_style='mapbox://styles/mapbox/light-v10',
    )

    st.pydeck_chart(deck)

    # Create color legend for DCs grouped by region
    st.markdown("#### Distribution Center Color Legend")

    # Define regional groupings
    regions = {
        'Northeast (Cool Blues/Purples)': [
            'Port Authority of New York/New Jersey NY/NJ',
            'Philadelphia PA',
            'Charleston SC'
        ],
        'Midwest (Green Tones)': [
            'Chicago IL',
            'Memphis TN'
        ],
        'South (Warm Reds/Oranges)': [
            'Houston TX',
            'New Orleans LA',
            'Savannah GA',
            'Mobile AL'
        ],
        'West (Purple/Magenta)': [
            'Los Angeles CA'
        ]
    }

    # Display each region
    for region_name, dcs in regions.items():
        st.markdown(f"**{region_name}**")
        cols = st.columns(len(dcs))

        for idx, dc in enumerate(dcs):
            if dc in df_filtered['dc_name'].unique():
                with cols[idx]:
                    color = get_dc_color(dc, dc_options)
                    color_hex = '#{:02x}{:02x}{:02x}'.format(color[0], color[1], color[2])
                    
                    st.markdown(
                        f'<div style="display:flex; align-items:center; margin-bottom:8px;">'
                        f'<div style="width:30px; height:30px; min-width:30px; flex-shrink:0; ' 
                        f'background-color:{color_hex}; border:2px solid black; margin-right:10px; border-radius:4px;"></div>'
                        f'<span style="font-size:14px; line-height:1.2;">{dc}</span>' # Added line-height for better wrapping text
                        f'</div>',
                        unsafe_allow_html=True
                    )

    st.caption("**Map Guide:** Each dot = Customer order (colored by fulfilling DC). Shaded hexagons = High density areas (darker = more orders). Colors are grouped by geographic region.")

    # ============================================================
    # Prepare DC Performance Data (used by both visualizations)
    # ============================================================
    dc_performance = df_filtered.groupby('dc_name').agg({
        'order_id': 'count',
        'customer_lat': 'count'
    }).rename(columns={
        'order_id': 'Total Orders',
        'customer_lat': 'Deliveries'
    }).reset_index()

    # Calculate average distance per DC (if possible)
    if 'dc_lat' in df_filtered.columns and 'dc_long' in df_filtered.columns:
        dc_performance['Avg Distance (km)'] = df_filtered.groupby('dc_name').apply(
            lambda x: calculate_avg_distance(x)
        ).values

    dc_performance = dc_performance.sort_values('Total Orders', ascending=False)

    # ============================================================
    # VISUALIZATION: Order Volume vs Average Distance
    # ============================================================
    st.divider()   
    st.subheader("Order Volume vs Average Distance by Distribution Center")

    # Create dual-axis chart showing both order volume and average distance
    if 'Avg Distance (km)' in dc_performance.columns:
        # Add DC colors to the performance dataframe
        dc_performance['color'] = dc_performance['dc_name'].apply(
            lambda x: '#{:02x}{:02x}{:02x}'.format(*get_dc_color(x, dc_options)[:3])
        )

        # Create figure with secondary y-axis
        fig = go.Figure()

        # Add bar chart for order volume
        fig.add_trace(go.Bar(
            x=dc_performance['dc_name'],
            y=dc_performance['Total Orders'],
            name='Order Volume',
            marker=dict(
                color=dc_performance['color'],
                line=dict(color='black', width=1)
            ),
            yaxis='y',
            hovertemplate='<b>%{x}</b><br>Orders: %{y:,}<extra></extra>'
        ))

        # Add line chart for average distance
        fig.add_trace(go.Scatter(
            x=dc_performance['dc_name'],
            y=dc_performance['Avg Distance (km)'],
            name='Avg Distance (km)',
            mode='lines+markers',
            line=dict(color='darkred', width=3),
            marker=dict(size=10, color='darkred', symbol='diamond'),
            yaxis='y2',
            hovertemplate='<b>%{x}</b><br>Avg Distance: %{y:,.0f} km<extra></extra>'
        ))

        # Update layout with dual y-axes
        fig.update_layout(
            title=dict(
                text="Order Volume & Average Shipping Distance by Distribution Center",
                font=dict(color='black')
            ),
            xaxis=dict(
                title='Distribution Center',
                tickangle=-45,
                tickfont=dict(size=11, color='black'),
                titlefont=dict(color='black')
            ),
            yaxis=dict(
                title='<b>Order Volume</b>',
                titlefont=dict(color='black'),
                tickfont=dict(color='black'),
                side='left'
            ),
            yaxis2=dict(
                title='<b>Average Distance (km)</b>',
                titlefont=dict(color='black'),
                tickfont=dict(color='black'),
                anchor='x',
                overlaying='y',
                side='right'
            ),
            plot_bgcolor='#FFFFFF',
            paper_bgcolor='#FFFFFF',
            height=500,
            legend=dict(
                orientation='h',
                yanchor='bottom',
                y=1.02,
                xanchor='center',
                x=0.5,
                font=dict(color='black')
            ),
            hovermode='x unified',
            font=dict(color='black')
        )

        st.plotly_chart(fig, use_container_width=True)

        st.caption("**Insight:** Bars show order volume (colored by DC region). Red line shows average shipping distance. High volume + low distance = efficient DC.")

    # ============================================================
    # ANALYSIS: DC Performance Table
    # ============================================================
    st.divider()   
    st.subheader("Distribution Center Performance")
    st.dataframe(dc_performance, use_container_width=True)

    # ============================================================
    # INEFFICIENCY DETECTION (Optional Advanced Feature)
    # ============================================================
    st.divider()   
    with st.expander("**Show Potential Inefficiencies**"):
        st.markdown("""
        **Definition:** This section shows where the shipping distance exceeds the median by 50% or more,
                    and may indicate inefficient DC assignment.
        """)

        df_with_distance = df_filtered.copy()
        df_with_distance['distance_km'] = df_with_distance.apply(
            lambda row: haversine_distance(
                row['dc_lat'], row['dc_long'],
                row['customer_lat'], row['customer_long']
            ), axis=1
        )

        median_distance = df_with_distance['distance_km'].median()
        threshold = median_distance * 1.5

        inefficient_orders = df_with_distance[df_with_distance['distance_km'] > threshold]

        st.metric("Potentially Inefficient Orders", f"{len(inefficient_orders):,}")
        st.metric("Median Shipping Distance", f"{median_distance:.0f} km")
        st.metric("Inefficiency Threshold", f"{threshold:.0f} km")

        if not inefficient_orders.empty:
            st.dataframe(
                inefficient_orders[['order_id', 'dc_name', 'distance_km']].head(20),
                use_container_width=True
            )


# ============================================================
# HELPER FUNCTIONS
# ============================================================

def get_dc_color(dc_name, dc_options):
    """
    Assign a unique color to each DC for visual consistency.
    Colors are logically assigned based on geographic/regional grouping.
    Returns RGBA color array with distinct, vibrant colors.
    """
    # Define color mapping for specific DCs with logical regional grouping
    color_map = {
        # Northeast (Cool colors - Blues/Purples)
        'Port Authority of New York/New Jersey NY/NJ': [0, 100, 255, 220],      # Royal Blue
        'Philadelphia PA': [138, 43, 226, 220],                                   # Blue Violet
        'Charleston SC': [70, 130, 180, 220],                                     # Steel Blue

        # Midwest (Green tones)
        'Chicago IL': [34, 139, 34, 220],                                         # Forest Green
        'Memphis TN': [50, 205, 50, 220],                                         # Lime Green

        # South (Warm colors - Reds/Oranges)
        'Houston TX': [255, 69, 0, 220],                                          # Red-Orange
        'New Orleans LA': [255, 140, 0, 220],                                     # Dark Orange
        'Savannah GA': [220, 20, 60, 220],                                        # Crimson
        'Mobile AL': [255, 165, 0, 220],                                          # Orange

        # West (Purple/Magenta)
        'Los Angeles CA': [199, 21, 133, 220],                                    # Medium Violet Red
    }

    # If DC has a predefined color, use it
    if dc_name in color_map:
        return color_map[dc_name]

    # Fallback colors for any additional DCs
    fallback_colors = [
        [0, 255, 255, 220],      # Cyan
        [255, 215, 0, 220],      # Gold
        [255, 105, 180, 220],    # Hot Pink
        [64, 224, 208, 220],     # Turquoise
    ]

    try:
        idx = dc_options.index(dc_name) % len(fallback_colors)
        return fallback_colors[idx]
    except (ValueError, AttributeError):
        return [128, 128, 128, 200]  # Gray default


def haversine_distance(lat1, lon1, lat2, lon2):
    """
    Calculate the great circle distance between two points
    on the earth (specified in decimal degrees).
    Returns distance in kilometers.
    """
    from math import radians, cos, sin, asin, sqrt

    # Convert decimal degrees to radians
    lon1, lat1, lon2, lat2 = map(radians, [lon1, lat1, lon2, lat2])

    # Haversine formula
    dlon = lon2 - lon1
    dlat = lat2 - lat1
    a = sin(dlat/2)**2 + cos(lat1) * cos(lat2) * sin(dlon/2)**2
    c = 2 * asin(sqrt(a))
    r = 6371  # Radius of earth in kilometers

    return c * r


def calculate_avg_distance(df_subset):
    """
    Calculate average shipping distance for a subset of orders.
    """
    if df_subset.empty:
        return 0

    distances = df_subset.apply(
        lambda row: haversine_distance(
            row['dc_lat'], row['dc_long'],
            row['customer_lat'], row['customer_long']
        ), axis=1
    )

    return distances.mean()