"""Interactive customer analysis report."""

import numpy as np
import pandas as pd
import plotly.express as px
import streamlit as st

from components.style import setup


setup("Analysis Report")

# ---------------------------------------------------------
# Selected analysis
# ---------------------------------------------------------

selected_analysis = st.session_state.get(
    "selected_analysis"
)

if not selected_analysis:

    st.warning(
        "Please select an analysis from the Analysis Library."
    )

    if st.button("Go to Analysis Library"):
        st.switch_page(
            "pages/8_Analysis_Library.py"
        )

    st.stop()


filename = selected_analysis["report"]
date_submitted = selected_analysis["submitted"]
status = selected_analysis["status"]



# ---------------------------------------------------------
# Navigation
# ---------------------------------------------------------

#st.divider()

back_col, _ = st.columns([1, 5])

with back_col:
    if st.button("← Back to Analysis Library"):
        st.switch_page("pages/8_Analysis_Library.py")

# ---------------------------------------------------------
# Page header
# ---------------------------------------------------------

st.title("Customer Analysis")

st.caption(
    f"{filename}  •  "
    f"Submitted {date_submitted.strftime('%d %b %Y, %I:%M %p')}  •  "
    f"Status: {status}"
)

# ---------------------------------------------------------
# Overview metrics
# ---------------------------------------------------------

st.subheader("Business Overview")

col1, col2, col3, col4 = st.columns(4)

with col1:
    st.metric("Total Customers", "4,372")

with col2:
    st.metric("Total Invoices", "22,190")

with col3:
    st.metric("Total Revenue", "$1.24M")

with col4:
    st.metric("Average Order Value", "$55.89")


# ---------------------------------------------------------
# Sales Over Time
# ---------------------------------------------------------

st.divider()

st.subheader("1. Sales Over Time")

period = st.radio(
    "View sales by",
    ["Daily", "Weekly", "Monthly"],
    horizontal=True,
)

dates = pd.date_range(
    start="2026-01-01",
    periods=180,
    freq="D",
)

rng = np.random.default_rng(42)

sales = rng.integers(
    80,
    450,
    size=len(dates),
)

sales = np.maximum(
    sales + np.linspace(0, 120, len(dates)).astype(int),
    0,
)

sales_df = pd.DataFrame(
    {
        "Date": dates,
        "Sales": sales,
    }
)


if period == "Weekly":

    sales_df = (
        sales_df
        .set_index("Date")
        .resample("W")["Sales"]
        .sum()
        .reset_index()
    )

elif period == "Monthly":

    sales_df = (
        sales_df
        .set_index("Date")
        .resample("ME")["Sales"]
        .sum()
        .reset_index()
    )


fig = px.line(
    sales_df,
    x="Date",
    y="Sales",
    markers=True,
    title=f"{period} Sales",
)

fig.update_layout(
    xaxis_title="Date",
    yaxis_title="Sales",
    hovermode="x unified",
)

st.plotly_chart(
    fig,
    use_container_width=True,
)


# ---------------------------------------------------------
# Top Products
# ---------------------------------------------------------

st.divider()

st.subheader("2. Top Products")

product_view = st.radio(
    "Rank products by",
    ["Quantity Sold", "Revenue"],
    horizontal=True,
)

products = [
    "Product A",
    "Product B",
    "Product C",
    "Product D",
    "Product E",
    "Product F",
    "Product G",
    "Product H",
]

product_df = pd.DataFrame(
    {
        "Product": products,
        "Quantity Sold": [
            820,
            690,
            560,
            510,
            430,
            390,
            340,
            290,
        ],
        "Revenue": [
            18200,
            16500,
            14200,
            11800,
            9700,
            8500,
            7600,
            6100,
        ],
    }
)

product_df = product_df.sort_values(
    product_view,
    ascending=False,
).head(8)


fig = px.bar(
    product_df,
    x=product_view,
    y="Product",
    orientation="h",
    text=product_view,
    title=f"Top Products by {product_view}",
)

fig.update_layout(
    yaxis={"categoryorder": "total ascending"},
    xaxis_title=product_view,
    yaxis_title="Product",
)

st.plotly_chart(
    fig,
    use_container_width=True,
)


# ---------------------------------------------------------
# Revenue Over Time
# ---------------------------------------------------------

st.divider()

st.subheader("3. Revenue Over Time")

revenue_dates = pd.date_range(
    start="2026-01-01",
    periods=12,
    freq="ME",
)

revenue_df = pd.DataFrame(
    {
        "Month": revenue_dates,
        "Revenue": [
            72000,
            81000,
            76000,
            93000,
            88000,
            102000,
            97000,
            108000,
            115000,
            121000,
            134000,
            146000,
        ],
    }
)

fig = px.area(
    revenue_df,
    x="Month",
    y="Revenue",
    markers=True,
    title="Monthly Revenue",
)

fig.update_layout(
    xaxis_title="Month",
    yaxis_title="Revenue",
    hovermode="x unified",
)

st.plotly_chart(
    fig,
    use_container_width=True,
)


# ---------------------------------------------------------
# RFM Analysis
# ---------------------------------------------------------

st.divider()

st.subheader("4. RFM Analysis")

st.write(
    "RFM analysis evaluates customers based on "
    "Recency, Frequency and Monetary value."
)

rfm_col1, rfm_col2, rfm_col3 = st.columns(3)

with rfm_col1:
    st.metric(
        "Average Recency",
        "38 days",
    )

with rfm_col2:
    st.metric(
        "Average Frequency",
        "4.8 orders",
    )

with rfm_col3:
    st.metric(
        "Average Monetary Value",
        "$1,245",
    )


rfm_df = pd.DataFrame(
    {
        "RFM Segment": [
            "High Value",
            "Loyal",
            "Potential Loyal",
            "At Risk",
            "Lost",
        ],
        "Customers": [
            520,
            980,
            760,
            610,
            430,
        ],
    }
)

fig = px.bar(
    rfm_df,
    x="RFM Segment",
    y="Customers",
    text="Customers",
    title="Customer Distribution by RFM Segment",
)

fig.update_layout(
    xaxis_title="RFM Segment",
    yaxis_title="Customers",
)

st.plotly_chart(
    fig,
    use_container_width=True,
)

# ---------------------------------------------------------
# Customer Segmentation
# ---------------------------------------------------------

st.divider()

st.subheader("5. Customer Segmentation")

st.write(
    "Explore customer segments identified through "
    "RFM analysis and K-Means clustering."
)


# ---------------------------------------------------------
# Mock customer-level data
# ---------------------------------------------------------

customer_df = pd.DataFrame(
    {
        "Customer ID": [
            "1234567",
            "2345678",
            "3456789",
            "4567890",
            "5678901",
            "6789012",
            "7890123",
            "8901234",
        ],
        "Segment": [
            "Top Customers",
            "Top Customers",
            "Loyal Customers",
            "Loyal Customers",
            "At Risk",
            "At Risk",
            "Last Active",
            "Last Active",
        ],
        "Recency": [
            12,
            15,
            20,
            24,
            95,
            110,
            7,
            5,
        ],
        "Frequency": [
            18,
            14,
            10,
            8,
            3,
            2,
            1,
            1,
        ],
        "Monetary": [
            3240,
            2890,
            1450,
            1280,
            420,
            310,
            180,
            150,
        ],
        "RFM Score": [
            555,
            555,
            454,
            443,
            212,
            211,
            321,
            322,
        ],
        "Last Purchase Date": [
            "2026-08-14",
            "2026-08-10",
            "2026-08-05",
            "2026-08-01",
            "2026-05-15",
            "2026-04-28",
            "2026-08-25",
            "2026-08-26",
        ],
    }
)


# ---------------------------------------------------------
# Segment summary
# ---------------------------------------------------------

segment_summary_df = (
    customer_df
    .groupby("Segment")
    .agg(
        Customers=("Customer ID", "count"),
        Average_Recency=("Recency", "mean"),
        Average_Frequency=("Frequency", "mean"),
        Average_Monetary=("Monetary", "mean"),
    )
    .reset_index()
)


# ---------------------------------------------------------
# Segment selector
# ---------------------------------------------------------

selected_segment = st.selectbox(
    "Explore segment",
    [
        "All Customers",
        "Top Customers",
        "Loyal Customers",
        "At Risk",
        "Last Active",
    ],
)


# ---------------------------------------------------------
# Segment distribution
# ---------------------------------------------------------

fig = px.bar(
    segment_summary_df,
    x="Segment",
    y="Customers",
    text="Customers",
    title="Customer Segment Distribution",
)

fig.update_layout(
    xaxis_title="Customer Segment",
    yaxis_title="Number of Customers",
)

st.plotly_chart(
    fig,
    use_container_width=True,
)


# ---------------------------------------------------------
# Selected segment summary
# ---------------------------------------------------------

if selected_segment == "All Customers":

    selected_data = customer_df

else:

    selected_data = customer_df[
        customer_df["Segment"] == selected_segment
    ]


customer_count = len(selected_data)

average_recency = selected_data["Recency"].mean()

average_frequency = selected_data["Frequency"].mean()

average_monetary = selected_data["Monetary"].mean()


st.markdown(
    f"### {selected_segment}"
)


col1, col2, col3, col4 = st.columns(4)

with col1:
    st.metric(
        "Customers",
        f"{customer_count:,}",
    )

with col2:
    st.metric(
        "Avg. Recency",
        f"{average_recency:.0f} days",
    )

with col3:
    st.metric(
        "Avg. Frequency",
        f"{average_frequency:.1f}",
    )

with col4:
    st.metric(
        "Avg. Monetary",
        f"${average_monetary:,.2f}",
    )


# ---------------------------------------------------------
# Download detailed customer data
# ---------------------------------------------------------

st.write("")

download_df = selected_data[
    [
        "Customer ID",
        "Segment",
        "Recency",
        "Frequency",
        "Monetary",
        "RFM Score",
        "Last Purchase Date",
    ]
].copy()


csv_data = download_df.to_csv(
    index=False
).encode("utf-8")


file_name = (
    selected_segment
    .lower()
    .replace(" ", "_")
    .replace("-", "_")
)


st.download_button(
    label="📥 Download Customer Details",
    data=csv_data,
    file_name=f"{file_name}_customer_details.csv",
    mime="text/csv",
    use_container_width=True,
    help=(
        "Download the detailed customer list "
        "for the selected segment."
    ),
)

# ---------------------------------------------------------
# Business Decisions
# ---------------------------------------------------------

st.divider()

st.subheader("6. Business Decisions & Recommendations")

st.markdown("### Key Insights")

st.info(
    """
    • Revenue shows an overall upward trend.

    • A small group of customers contributes a significant
      proportion of total revenue.

    • Loyal customers demonstrate consistent purchasing
      behaviour.

    • At-risk customers may require targeted
      re-engagement campaigns.
    """
)


st.markdown("### Recommendations")

recommendation_col1, recommendation_col2 = st.columns(2)

with recommendation_col1:

    st.markdown("#### 🎯 Retain High-Value Customers")

    st.write(
        "Develop loyalty rewards and personalised offers "
        "for customers with high monetary value."
    )

with recommendation_col2:

    st.markdown("#### 🔄 Re-engage At-Risk Customers")

    st.write(
        "Use targeted promotions and personalised "
        "communication to encourage repeat purchases."
    )

