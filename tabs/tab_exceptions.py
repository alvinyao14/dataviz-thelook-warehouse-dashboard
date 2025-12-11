import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import plotly.express as px
from datetime import datetime, timedelta

def render_tab(df):
    """
    Exception Management Tab

    Purpose: Identify orders requiring immediate intervention based on conditional logic.

    Key Rules:
    - Rule A (Processing Lag): Flag if status = 'Processing' AND (Current_Date - created_at) > 3 Days
    - Rule B (Carrier Lag): Flag if status = 'Shipped' AND (Current_Date - created_at) > 7 Days

    Key Columns Used:
    - order_id, created_at, shipped_at, delivered_at, status
    """

    st.header("**Exception Management & Operational Triage**")
    st.markdown("""
        **Overview:** This tab identify orders requiring immediate intervention based on the following metrics:
        - **Processing Lag**: Orders that are stuck in processing for more than 3 days.
        - **Carrier Lag**: Orders that have been shipped but not delivered for more than 7

    """)

    # ============================================================
    # DATA VALIDATION & PREPARATION
    # ============================================================
    required_cols = ['order_id', 'created_at', 'status']
    missing_cols = [col for col in required_cols if col not in df.columns]

    if missing_cols:
        st.error(f"Missing required columns: {missing_cols}")
        st.info("This tab requires: order_id, created_at, status (and optionally: shipped_at, delivered_at)")
        return

    # Convert date columns to datetime
    df_clean = df.copy()

    # Handle created_at
    if 'created_at' in df_clean.columns:
        df_clean['created_at'] = pd.to_datetime(df_clean['created_at'], errors='coerce')
        # Remove timezone info if present
        if df_clean['created_at'].dt.tz is not None:
            df_clean['created_at'] = df_clean['created_at'].dt.tz_localize(None)

    # Handle shipped_at if exists
    if 'shipped_at' in df_clean.columns:
        df_clean['shipped_at'] = pd.to_datetime(df_clean['shipped_at'], errors='coerce')
        # Remove timezone info if present
        if df_clean['shipped_at'].dt.tz is not None:
            df_clean['shipped_at'] = df_clean['shipped_at'].dt.tz_localize(None)

    # Handle delivered_at if exists
    if 'delivered_at' in df_clean.columns:
        df_clean['delivered_at'] = pd.to_datetime(df_clean['delivered_at'], errors='coerce')
        # Remove timezone info if present
        if df_clean['delivered_at'].dt.tz is not None:
            df_clean['delivered_at'] = df_clean['delivered_at'].dt.tz_localize(None)

    # Remove rows without created_at
    df_clean = df_clean.dropna(subset=['created_at'])

    if df_clean.empty:
        st.warning("No valid order data available.")
        return

    # Get current date (timezone-naive to match data)
    current_date = pd.Timestamp.now().tz_localize(None)

    # ============================================================
    # CALCULATE EXCEPTION FLAGS
    # ============================================================

    # Calculate days since order creation
    df_clean['days_since_created'] = (current_date - df_clean['created_at']).dt.days

    # Rule A: Processing Lag (status = 'Processing' AND > 3 days)
    df_clean['flag_processing_lag'] = (
        (df_clean['status'].str.lower() == 'processing') &
        (df_clean['days_since_created'] > 3)
    )

    # Rule B: Carrier Lag (status = 'Shipped' AND > 7 days)
    df_clean['flag_carrier_lag'] = (
        (df_clean['status'].str.lower() == 'shipped') &
        (df_clean['days_since_created'] > 7)
    )

    # Any exception flag
    df_clean['has_exception'] = df_clean['flag_processing_lag'] | df_clean['flag_carrier_lag']

    # Determine exception type for display
    def get_exception_type(row):
        if row['flag_processing_lag']:
            return 'Processing Lag (>3 days)'
        elif row['flag_carrier_lag']:
            return 'Carrier Lag (>7 days)'
        else:
            return 'No Exception'

    df_clean['exception_type'] = df_clean.apply(get_exception_type, axis=1)

    # ============================================================
    # KEY METRICS - RED ALERT COUNTERS
    # ============================================================
    
    st.subheader("Alert Counters")

    # Calculate exception counts
    total_orders = len(df_clean)
    processing_lag_count = df_clean['flag_processing_lag'].sum()
    carrier_lag_count = df_clean['flag_carrier_lag'].sum()
    total_exceptions = df_clean['has_exception'].sum()
    exception_rate = (total_exceptions / total_orders * 100) if total_orders > 0 else 0

    col1, col2, col3, col4 = st.columns(4)

    with col1:
        st.metric(
            "Total Exceptions",
            f"{total_exceptions:,}"

        )
        st.markdown(f"{exception_rate:.1f}% of orders")

    with col2:
        st.metric(
            "Processing Lag",
            f"{processing_lag_count:,}"
        )
        st.markdown("3+ days in processing")

    with col3:
        st.metric(
            "Carrier Lag",
            f"{carrier_lag_count:,}"
        )
        st.markdown("7+ days since creation")

    with col4:
        healthy_orders = total_orders - total_exceptions
        st.metric(
            "Healthy Orders",
            f"{healthy_orders:,}"
        )
        st.markdown(f"{(healthy_orders/total_orders*100):.1f}% of total")

    # ============================================================
    # EXCEPTION TREND OVER TIME
    # ============================================================
    st.divider()
    st.subheader("Exception Trends Over Time")

    # Group by date to show trend
    df_trend = df_clean.copy()
    df_trend['created_date'] = df_trend['created_at'].dt.date

    trend_data = df_trend.groupby('created_date').agg({
        'order_id': 'count',
        'flag_processing_lag': 'sum',
        'flag_carrier_lag': 'sum',
        'has_exception': 'sum'
    }).reset_index()

    trend_data.columns = ['Date', 'Total Orders', 'Processing Lag', 'Carrier Lag', 'Total Exceptions']
    trend_data['Exception Rate (%)'] = (trend_data['Total Exceptions'] / trend_data['Total Orders'] * 100)

    # Sort by date
    trend_data = trend_data.sort_values('Date')

    # Create trend chart
    fig_trend = go.Figure()

    fig_trend.add_trace(go.Scatter(
        x=trend_data['Date'],
        y=trend_data['Processing Lag'],
        name='Processing Lag',
        mode='lines+markers',
        line=dict(color='#FF6B6B', width=2),
        marker=dict(size=6),
        stackgroup='one'
    ))

    fig_trend.add_trace(go.Scatter(
        x=trend_data['Date'],
        y=trend_data['Carrier Lag'],
        name='Carrier Lag',
        mode='lines+markers',
        line=dict(color='#FFA500', width=2),
        marker=dict(size=6),
        stackgroup='one'
    ))

    fig_trend.update_layout(
        title=dict(
            text="Exception Volume Over Time",
            font=dict(color='black')
        ),
        xaxis=dict(
            title='Date',
            tickfont=dict(color='black'),
            titlefont=dict(color='black')
        ),
        yaxis=dict(
            title='Number of Exceptions',
            tickfont=dict(color='black'),
            titlefont=dict(color='black')
        ),
        plot_bgcolor='#FFFFFF',
        paper_bgcolor='#FFFFFF',
        height=400,
        hovermode='x unified',
        font=dict(color='black'),
        legend=dict(
            orientation='h',
            yanchor='bottom',
            y=1.02,
            xanchor='center',
            x=0.5,
            font=dict(color='black')
        )
    )

    st.plotly_chart(fig_trend, use_container_width=True)
    st.caption("**Description:** Track the volume of exceptions over time to identify trends and patterns. The stacked area shows how Processing Lag and Carrier Lag contribute to total exceptions.")

    # ============================================================
    # EXCEPTION RATE OVER TIME
    # ============================================================
    st.subheader("Exception Rate Over Time")

    # Create exception rate chart
    fig_rate = go.Figure()

    fig_rate.add_trace(go.Scatter(
        x=trend_data['Date'],
        y=trend_data['Exception Rate (%)'],
        name='Exception Rate',
        mode='lines+markers',
        line=dict(color='#DC143C', width=3),
        marker=dict(size=8, color='#DC143C'),
        fill='tozeroy',
        fillcolor='rgba(220, 20, 60, 0.2)'
    ))

    # Add reference line at acceptable threshold (e.g., 5%)
    fig_rate.add_hline(
        y=5,
        line_dash="dash",
        line_color="green",
        annotation_text="Target: 5%",
        annotation_position="right"
    )

    fig_rate.update_layout(
        title=dict(
            text="Exception Rate Percentage by Date",
            font=dict(color='black')
        ),
        xaxis=dict(
            title='Date',
            tickfont=dict(color='black'),
            titlefont=dict(color='black')
        ),
        yaxis=dict(
            title='Exception Rate (%)',
            tickfont=dict(color='black'),
            titlefont=dict(color='black')
        ),
        plot_bgcolor='#FFFFFF',
        paper_bgcolor='#FFFFFF',
        height=400,
        hovermode='x unified',
        font=dict(color='black'),
        showlegend=False
    )

    st.plotly_chart(fig_rate, use_container_width=True)
    st.caption("**Description:** Monitor the exception rate percentage to ensure it stays below your target threshold (5%). Spikes indicate periods requiring immediate attention.")

    # ============================================================
    # STATUS DISTRIBUTION
    # ============================================================
    st.divider()
    st.subheader("Order Status Distribution")

    # Status distribution (all orders)
    status_counts = df_clean['status'].value_counts().reset_index()
    status_counts.columns = ['Status', 'Count']

    fig_status = px.bar(
        status_counts,
        x='Status',
        y='Count',
        title='Order Status Distribution (All Orders)',
        labels={'Status': 'Order Status', 'Count': 'Number of Orders'},
        color_discrete_sequence=['#FFA500']
    )

    fig_status.update_layout(
        title=dict(font=dict(color='black')),
        xaxis=dict(
            tickfont=dict(color='black'),
            titlefont=dict(color='black'),
            tickangle=-45,
            title=dict(text='Order Status', font=dict(color='black'))
        ),
        yaxis=dict(
            tickfont=dict(color='black'),
            titlefont=dict(color='black'),
            title=dict(text='Number of Orders', font=dict(color='black'))
        ),
        plot_bgcolor='#FFFFFF',
        paper_bgcolor='#FFFFFF',
        font=dict(color='black'),
        showlegend=False
    )

    # Ensure colorbar text is black
    fig_status.update_coloraxes(colorbar=dict(
        tickfont=dict(color='black'),
        titlefont=dict(color='black')
    ))

    st.plotly_chart(fig_status, use_container_width=True)
    st.caption("**Description:** Understand the distribution of order statuses across your entire order base. This helps identify bottlenecks in the fulfillment pipeline.")

    # ============================================================
    # EXCEPTION SEVERITY HEATMAP
    # ============================================================
    st.divider()    
    st.subheader("Exception Severity Heatmap")

    # Create bins for days since created
    exception_data = df_clean[df_clean['has_exception']].copy()

    if not exception_data.empty:
        # Create bins for severity levels
        exception_data['severity'] = pd.cut(
            exception_data['days_since_created'],
            bins=[0, 7, 14, 30, 60, float('inf')],
            labels=['7 days', '8-14 days', '15-30 days', '31-60 days', '60+ days']
        )

        # Group by date and severity
        heatmap_data = exception_data.groupby([
            exception_data['created_at'].dt.to_period('W').dt.start_time.dt.date,
            'severity'
        ]).size().reset_index(name='count')
        heatmap_data.columns = ['Week', 'Severity', 'Count']

        # Pivot for heatmap
        heatmap_pivot = heatmap_data.pivot(index='Severity', columns='Week', values='Count').fillna(0)

        # Limit to last 12 weeks for readability
        if len(heatmap_pivot.columns) > 12:
            heatmap_pivot = heatmap_pivot.iloc[:, -12:]

        fig_heatmap = go.Figure(data=go.Heatmap(
            z=heatmap_pivot.values,
            x=[str(col) for col in heatmap_pivot.columns],
            y=heatmap_pivot.index.astype(str),
            colorscale='Reds',
            text=heatmap_pivot.values,
            texttemplate='%{text:.0f}',
            textfont={"size": 10},
            colorbar=dict(title="Count", titlefont=dict(color='black'), tickfont=dict(color='black'))
        ))

        fig_heatmap.update_layout(
            title=dict(
                text="Exception Count by Severity & Week",
                font=dict(color='black')
            ),
            xaxis=dict(
                title='Week',
                tickfont=dict(color='black'),
                titlefont=dict(color='black'),
                tickangle=-45
            ),
            yaxis=dict(
                title='Severity (Days Overdue)',
                tickfont=dict(color='black'),
                titlefont=dict(color='black')
            ),
            plot_bgcolor='#FFFFFF',
            paper_bgcolor='#FFFFFF',
            height=400,
            font=dict(color='black')
        )

        st.plotly_chart(fig_heatmap, use_container_width=True)
        st.caption("**Description:** Visualize exception severity patterns over time. Darker red indicates higher exception counts. Use this to identify which severity levels (days overdue) are trending up, helping you prioritize resource allocation.")
    else:
        st.info("No exceptions to display in heatmap")

    # ============================================================
    # TOP PROBLEM ORDERS TABLE
    # ============================================================
    st.divider()    
    st.subheader("Top 10 Most Overdue Orders")

    if not exception_data.empty:
        # Get top 10 most overdue
        top_overdue = exception_data.nlargest(10, 'days_since_created')[
            ['order_id', 'status', 'created_at', 'days_since_created', 'exception_type']
        ].copy()

        top_overdue['created_at'] = top_overdue['created_at'].dt.strftime('%Y-%m-%d')

        st.dataframe(
            top_overdue,
            use_container_width=True,
            hide_index=True
        )
        st.caption("**Description:** Quickly identify the most critical orders that need immediate intervention. These are the orders that have been stuck the longest and represent the highest risk of customer dissatisfaction.")
    else:
        st.success("No overdue orders!")

    # ============================================================
    # DETAILED EXCEPTION ANALYSIS
    # ============================================================
    with st.expander("Show Detailed Exception Analysis"):
        st.markdown("### Processing Lag Analysis (>3 days)")

        processing_lag_orders = df_clean[df_clean['flag_processing_lag']].copy()

        if not processing_lag_orders.empty:
            # Calculate statistics
            avg_lag = processing_lag_orders['days_since_created'].mean()
            max_lag = processing_lag_orders['days_since_created'].max()
            min_lag = processing_lag_orders['days_since_created'].min()

            col1, col2, col3 = st.columns(3)
            with col1:
                st.metric("Average Lag", f"{avg_lag:.1f} days")
            with col2:
                st.metric("Maximum Lag", f"{max_lag:.0f} days")
            with col3:
                st.metric("Minimum Lag", f"{min_lag:.0f} days")

            # Distribution histogram
            fig_hist = px.histogram(
                processing_lag_orders,
                x='days_since_created',
                nbins=20,
                title='Distribution of Processing Lag (days)',
                labels={'days_since_created': 'Days Since Order Created'},
                color_discrete_sequence=['#FF6B6B']
            )

            fig_hist.update_layout(
                title=dict(font=dict(color='black')),
                xaxis=dict(tickfont=dict(color='black'), titlefont=dict(color='black')),
                yaxis=dict(tickfont=dict(color='black'), titlefont=dict(color='black'), title='Count'),
                plot_bgcolor='#F5F5F5',
                paper_bgcolor='#F5F5F5',
                font=dict(color='black')
            )

            st.plotly_chart(fig_hist, use_container_width=True)
        else:
            st.success("No processing lag issues found!")

        st.markdown("---")
        st.markdown("### Carrier Lag Analysis (>7 days)")

        carrier_lag_orders = df_clean[df_clean['flag_carrier_lag']].copy()

        if not carrier_lag_orders.empty:
            # Calculate statistics
            avg_lag = carrier_lag_orders['days_since_created'].mean()
            max_lag = carrier_lag_orders['days_since_created'].max()
            min_lag = carrier_lag_orders['days_since_created'].min()

            col1, col2, col3 = st.columns(3)
            with col1:
                st.metric("Average Lag", f"{avg_lag:.1f} days")
            with col2:
                st.metric("Maximum Lag", f"{max_lag:.0f} days")
            with col3:
                st.metric("Minimum Lag", f"{min_lag:.0f} days")

            # Distribution histogram
            fig_hist = px.histogram(
                carrier_lag_orders,
                x='days_since_created',
                nbins=20,
                title='Distribution of Carrier Lag (days)',
                labels={'days_since_created': 'Days Since Order Created'},
                color_discrete_sequence=['#FFA500']
            )

            fig_hist.update_layout(
                title=dict(font=dict(color='black')),
                xaxis=dict(tickfont=dict(color='black'), titlefont=dict(color='black')),
                yaxis=dict(tickfont=dict(color='black'), titlefont=dict(color='black'), title='Count'),
                plot_bgcolor='#F5F5F5',
                paper_bgcolor='#F5F5F5',
                font=dict(color='black')
            )

            st.plotly_chart(fig_hist, use_container_width=True)
        else:
            st.success("No carrier lag issues found!")

    # ============================================================
    # SUMMARY STATISTICS
    # ============================================================
    st.divider()
    st.subheader("Summary Statistics")

    col1, col2 = st.columns(2)

    with col1:
        st.markdown("**Overall Performance**")
        summary_df = pd.DataFrame({
            'Metric': [
                'Total Orders',
                'Total Exceptions',
                'Exception Rate',
                'Processing Lag Count',
                'Carrier Lag Count'
            ],
            'Value': [
                f"{total_orders:,}",
                f"{total_exceptions:,}",
                f"{exception_rate:.2f}%",
                f"{processing_lag_count:,}",
                f"{carrier_lag_count:,}"
            ]
        })
        st.dataframe(summary_df, use_container_width=True, hide_index=True)

    with col2:
        st.markdown("**Exception Rules**")
        rules_df = pd.DataFrame({
            'Rule': ['Processing Lag', 'Carrier Lag'],
            'Condition': ['Status = Processing', 'Status = Shipped'],
            'Threshold': ['>3 days', '>7 days']
        })
        st.dataframe(rules_df, use_container_width=True, hide_index=True)

    st.caption("**Usage Guide:** This dashboard surfaces orders that need immediate action. Use the Action List to export and assign tasks to your team. Monitor trends to identify systemic issues before they become customer complaints.")
