import streamlit as st
import pandas as pd
df = pd.DataFrame({"name": ["A", "B", "C"], "val": [1, 2, 3]})
st.session_state["my_table"] = {"selection": {"rows": [0, 1]}}
try:
    st.dataframe(df, on_select="rerun", selection_mode="multi-row", key="my_table")
    print("session_state override is supported")
except Exception as e:
    print(f"Other error: {e}")
