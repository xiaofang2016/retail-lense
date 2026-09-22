"""Reference analysis: a pre-generated demo report, rendered without any backend calls."""
 
import json
from pathlib import Path
 
import streamlit as st
 
from components.report_view import render_report
from components.style import setup
 
setup("Reference")
 
st.title("Reference analysis")
st.caption("A sample retail analysis that shows what our analysis process would provide for your uploaded data. ")
 
_REPORT_PATH = Path(__file__).resolve().parent.parent / "data" / "reference_report.json"
 
report = json.loads(_REPORT_PATH.read_text())
render_report(report)