import streamlit as st
import pandas as pd
import altair as alt

df = pd.DataFrame({"name": ["A", "B", "C"], "val": [1, 2, 3]})

if "table_sel" not in st.session_state:
    st.session_state.table_sel = {"rows": []}

selection = alt.selection_point(name="Select", fields=['name'])
chart = alt.Chart(df).mark_bar().encode(
    x="name:N",
    y="val:Q",
    opacity=alt.condition(selection, alt.value(1.0), alt.value(0.3))
).add_params(selection)

event = st.altair_chart(chart, on_select="rerun", key="chart_sel")
st.write(event)

# Attempt to sync table selection based on chart selection
if event.selection.get("Select"):
    selected_names = [item["name"] for item in event.selection.get("Select")]
    selected_indices = df[df["name"].isin(selected_names)].index.tolist()
    st.session_state.table_sel["rows"] = selected_indices

df_event = st.dataframe(df, on_select="rerun", selection_mode="multi-row", key="table_sel")
st.write(df_event)
