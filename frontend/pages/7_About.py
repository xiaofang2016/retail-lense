"""Public About page."""
 
import streamlit as st
 
from components.style import setup
 
 
setup("About")
 
 
# ---------------------------------------------------------
# Page-local styling (team avatars, tech chips)
# ---------------------------------------------------------
 
st.markdown(
    """
    <style>
    .team-card {
        text-align: center;
        padding: 1.75rem 1rem 1.25rem;
    }
    .team-avatar {
        width: 64px;
        height: 64px;
        margin: 0 auto 0.9rem;
        border-radius: 50%;
        display: flex;
        align-items: center;
        justify-content: center;
        color: #fff;
        font-weight: 600;
        font-size: 1.05rem;
        letter-spacing: 0.02em;
    }
    .team-name {
        font-weight: 600;
        font-size: 1rem;
        margin-bottom: 0.15rem;
        color: #1a1a1a;
    }
    .team-role {
        font-size: 0.85rem;
        color: #6b7280;
    }
    .tech-card-title {
        font-weight: 600;
        font-size: 0.95rem;
        margin-bottom: 0.75rem;
        color: #1a1a1a;
    }
    .tech-chip-row {
        display: flex;
        flex-wrap: wrap;
        gap: 0.4rem;
        padding-bottom: 0.75rem;
    }
    .tech-chip {
        display: inline-block;
        padding: 0.3rem 0.75rem;
        border-radius: 999px;
        border: 1px solid #e0e0e0;
        background: #fafafa;
        font-size: 0.82rem;
        color: #333;
    }
    </style>
    """,
    unsafe_allow_html=True,
)
 
 
# ---------------------------------------------------------
# Page header
# ---------------------------------------------------------
 
st.title("About Retail Lense")
 
st.write(
    "Retail Lense is a customer analytics platform designed "
    "to help small and medium retail businesses better "
    "understand their transaction data."
)
 
 
# ---------------------------------------------------------
# Our Purpose
# ---------------------------------------------------------
 
st.divider()
 
st.subheader("Our Purpose")
 
st.write(
    "Retail businesses generate valuable information through "
    "everyday transactions, but raw transaction data can be "
    "difficult to interpret and use for decision-making."
)
 
st.write(
    "Retail Lense brings data analysis, customer segmentation, "
    "and AI-powered advice together to help businesses turn "
    "transaction data into meaningful insights."
)
 
 
# ---------------------------------------------------------
# Our Approach
# ---------------------------------------------------------
 
st.subheader("Our Approach")
 
st.write(
    "Retail Lense combines business analytics, statistical "
    "analysis, machine learning, and artificial intelligence "
    "to understand customer behaviour and business performance."
)
 
col1, col2 = st.columns(2)
 
with col1:
 
    st.markdown("### Data & Machine Learning")
 
    st.write(
        "Transaction data is processed through a structured "
        "analysis pipeline. RFM analysis and K-Means clustering "
        "are used to identify meaningful customer segments."
    )
 
 
with col2:
 
    st.markdown("### AI-Powered Advice")
 
    st.write(
        "Key analytical results and numerical insights are used "
        "to generate written business advice through a "
        "Language Model."
    )
 
 
# ---------------------------------------------------------
# What is RFM?
# ---------------------------------------------------------
 
st.divider()
 
st.subheader("What is RFM Analysis?")
 
st.write(
    "RFM stands for **Recency, Frequency, and Monetary value** — three "
    "simple numbers calculated for every customer directly from their "
    "purchase history. Together they turn a raw transaction log into a "
    "picture of how engaged and valuable each customer actually is."
)
 
_RFM_METRICS = [
    {
        "letter": "R",
        "title": "Recency",
        "question": "How recently did they buy?",
        "measured_as": "Days since their last purchase.",
        "interpret": "Lower is better — a small number means they bought recently and are still engaged.",
        "color": "#3B6E68",
    },
    {
        "letter": "F",
        "title": "Frequency",
        "question": "How often do they buy?",
        "measured_as": "Number of separate orders placed.",
        "interpret": "Higher is better — frequent orders signal a loyal, repeat customer.",
        "color": "#4C5B7A",
    },
    {
        "letter": "M",
        "title": "Monetary",
        "question": "How much do they spend?",
        "measured_as": "Total amount spent across all orders.",
        "interpret": "Higher is better — it shows how much revenue this customer contributes.",
        "color": "#7A5C3E",
    },
]
 
rfm_cols = st.columns(3)
 
for i, metric in enumerate(_RFM_METRICS):
    with rfm_cols[i]:
        with st.container(border=True):
            st.markdown(
                f"""
                <div class="team-card">
                    <div class="team-avatar" style="background:{metric['color']}">
                        {metric['letter']}
                    </div>
                    <div class="team-name">{metric['title']}</div>
                    <div class="team-role" style="margin-bottom:0.6rem;">{metric['question']}</div>
                    <div style="font-size:0.85rem; color:#444; text-align:left;">
                        <b>Measured as:</b> {metric['measured_as']}<br>
                        <b>Reading it:</b> {metric['interpret']}
                    </div>
                </div>
                """,
                unsafe_allow_html=True,
            )
 
st.write(
    "Scoring every customer on all three values at once is what makes RFM useful. A customer who spent a "
    "lot two years ago and a customer who spends a little every week "
    "can look identical on a simple revenue report, but RFM tells them "
    "apart immediately."
)
 
st.markdown("#### Why it matters for the business")
 
st.write(
    "RFM scores are what Retail Lense's K-Means clustering groups "
    "customers by, producing the segments a business can actually act "
    "on:"
)
 
st.markdown(
    "- **High Value / Loyal customers** (recent, frequent, high spend) — worth "
    "retention perks, loyalty programs, and early access, since losing them "
    "costs the most revenue.\n"
    "- **At Risk customers** (used to buy often, haven't lately) — the best "
    "candidates for a win-back campaign, before they lapse further.\n"
    "- **Lost customers** (long inactive, rarely purchased) — usually not worth "
    "further marketing spend, so budget can be redirected elsewhere.\n\n"
    "In short, RFM turns \"here's our transaction history\" into \"here's who to "
    "reward, who to win back, and where to stop spending\" — the exact decisions "
    "a retailer needs to make with a limited marketing budget."
)
 
 
# ---------------------------------------------------------
# Our Team
# ---------------------------------------------------------
 
st.divider()
 
st.subheader("Our Team")
 
st.write(
    "Retail Lense is developed by a multidisciplinary team "
    "covering infrastructure, security, machine learning, "
    "backend, and frontend development."
)
 
 
_TEAM = [
    {"name": "Xiao Yuqun", "role": "Infrastructure", "color": "#3B6E68"},
    {"name": "SM Farhan", "role": "Infrastructure Security", "color": "#4C5B7A"},
    {"name": "Tahreem Tahir", "role": "Backend Developer (ML)", "color": "#7A5C3E"},
    {"name": "Arya Dhuri", "role": "Backend Developer (LLM)", "color": "#6E5A8C"},
    {"name": "Ei Thae Thae Naing", "role": "Frontend Developer", "color": "#8C5A4E"},
]
 
 
def _initials(name: str) -> str:
    parts = name.split()
    return (parts[0][0] + parts[-1][0]).upper()
 
 
team_cols = st.columns(3)
 
for i, member in enumerate(_TEAM):
    with team_cols[i % 3]:
        with st.container(border=True):
            st.markdown(
                f"""
                <div class="team-card">
                    <div class="team-avatar" style="background:{member['color']}">
                        {_initials(member['name'])}
                    </div>
                    <div class="team-name">{member['name']}</div>
                    <div class="team-role">{member['role']}</div>
                </div>
                """,
                unsafe_allow_html=True,
            )
 
 
# ---------------------------------------------------------
# Technology
# ---------------------------------------------------------
 
st.divider()
 
st.subheader("Technology")
 
st.write(
    "Retail Lense combines web development, data analytics, "
    "machine learning, cloud infrastructure, and artificial "
    "intelligence technologies."
)
 
 
_TECH_GROUPS = [
    {
        "title": "Application",
        "items": ["Python", "Streamlit", "FastAPI", "Redis", "Docker"],
    },
    {
        "title": "Data & AI",
        "items": [
            "pandas",
            "scikit-learn",
            "RFM Analysis",
            "K-Means Clustering",
            "Plotly",
            "OpenAI API",
        ],
    },
    {
        "title": "AWS Cloud Infrastructure",
        "items": [
            "EC2",
            "S3",
            "SQS",
            "Lambda",
            "DynamoDB",
            "Secrets Manager",
            "SNS",
            "CloudWatch",
            "Application Load Balancer",
        ],
    },
]
 
tech_cols = st.columns(3)
 
for i, group in enumerate(_TECH_GROUPS):
    with tech_cols[i]:
        with st.container(border=True):
            chips = "".join(f'<span class="tech-chip">{item}</span>' for item in group["items"])
            st.markdown(
                f"""
                <div class="tech-card-title">{group['title']}</div>
                <div class="tech-chip-row">{chips}</div>
                """,
                unsafe_allow_html=True,
            )
 
st.caption("CI/CD via GitHub Actions, deploying to AWS over an IAM-authorized EC2 Instance Connect tunnel.")
 
 
# ---------------------------------------------------------
# Privacy
# ---------------------------------------------------------
 
st.divider()
 
st.subheader("Privacy")
 
st.write(
    "Retail Lense is designed with privacy and responsible "
    "handling of user information in mind."
)
 
if st.button(
    "View Data Privacy Policy",
    use_container_width=True,
):
 
    st.switch_page(
        "pages/10_Data_Privacy.py"
    )
 
 
# ---------------------------------------------------------
# Project
# ---------------------------------------------------------
 
st.divider()
 
st.subheader("About This Project")
 
st.write(
    "Retail Lense is developed as a cloud-hosted group "
    "software project combining web development, data "
    "analytics, machine learning, artificial intelligence, "
    "and cloud technologies."
)
 
 
# ---------------------------------------------------------
# Footer
# ---------------------------------------------------------
 
st.divider()
 
st.caption(
    "Retail Lense — Turning transaction data into meaningful insights."
)