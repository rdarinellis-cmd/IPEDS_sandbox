import streamlit as st
import pandas as pd
import altair as alt

df = pd.DataFrame({"name": ["A", "B", "C"], "val": [1, 2, 3]})

# We use a central state to store the "true" selection
if "selected_names" not in st.session_state:
    st.session_state.selected_names = set()

# Determine selection state for Altair
click_selection = alt.selection_point(name="Select", fields=['name'])

# Python override for opacity
if st.session_state.selected_names:
    python_selection = alt.FieldOneOfPredicate(field='name', oneOf=list(st.session_state.selected_names))
    opacity_cond = alt.condition(click_selection | python_selection, alt.value(1.0), alt.value(0.3))
else:
    opacity_cond = alt.condition(click_selection, alt.value(1.0), alt.value(0.3))

chart = alt.Chart(df).mark_bar().encode(
    x="name:N",
    y="val:Q",
    opacity=opacity_cond
).add_params(click_selection)

chart_event = st.altair_chart(chart, on_select="rerun", key="chart_key")

# We want to know if the chart changed
chart_names = set()
if chart_event and chart_event.selection.get("Select"):
    chart_names = {item["name"] for item in chart_event.selection.get("Select")}

# We also want to know if the table changed
# But we can't know until we render it.
