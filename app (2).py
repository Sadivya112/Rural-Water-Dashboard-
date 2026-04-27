import streamlit as st
import pandas as pd
import plotly.express as px
import os

st.set_page_config(
    page_title="Drinking Water Access Dashboard",
    layout="wide"
) 

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

@st.cache_data
def load_data():
    df = pd.read_csv(os.path.join(BASE_DIR, "API_SH.H2O.SMDW.ZS_DS2_en_csv_v2_3203.csv"), skiprows=4)
    meta = pd.read_csv(os.path.join(BASE_DIR, "Metadata_Country_API_SH.H2O.SMDW.ZS_DS2_en_csv_v2_3203.csv"))

    df = df.merge(meta[["Country Code", "Region", "IncomeGroup"]], on="Country Code", how="left")
    df = df[df["Region"].notna()].copy()
    df = df.drop(columns=["Unnamed: 70", "Indicator Name", "Indicator Code"], errors="ignore")

    year_cols = [str(y) for y in range(2000, 2023)]
    long = df.melt(
        id_vars=["Country Name", "Country Code", "Region", "IncomeGroup"],
        value_vars=year_cols,
        var_name="Year",
        value_name="Access"
    )
    long = long.dropna(subset=["Access"])
    long["Year"] = long["Year"].astype(int)
    long["Access"] = long["Access"].astype(float)
    return long

data = load_data()

st.title("SAFELY MANAGED DRINKING WATER ACCESS")
st.caption("Percentage of population using safely managed drinking water services · Source: World Bank — WHO/UNICEF Joint Monitoring Programme")
st.divider()

st.sidebar.header("Filters")

all_regions = sorted(data["Region"].unique())
selected_regions = st.sidebar.multiselect("Region", all_regions, default=all_regions)

all_income = sorted(data["IncomeGroup"].dropna().unique())
selected_income = st.sidebar.multiselect("Income Group", all_income, default=all_income)

year_range = st.sidebar.slider("Year Range", 2000, 2022, (2000, 2022))

filtered = data[
    (data["Region"].isin(selected_regions)) &
    (data["IncomeGroup"].isin(selected_income)) &
    (data["Year"] >= year_range[0]) &
    (data["Year"] <= year_range[1])
]

if filtered.empty:
    st.warning("No data matches the current filters. Adjust the sidebar filters.")
    st.stop()

latest_year = filtered["Year"].max()
earliest_year = filtered["Year"].min()
latest = filtered[filtered["Year"] == latest_year]
earliest = filtered[filtered["Year"] == earliest_year]

col1, col2, col3, col4 = st.columns(4)
with col1:
    st.metric("Countries", latest["Country Name"].nunique())
with col2:
    avg_latest = latest["Access"].mean()
    st.metric(f"Avg Access ({latest_year})", f"{avg_latest:.1f}%")
with col3:
    avg_earliest = earliest["Access"].mean()
    change = avg_latest - avg_earliest
    st.metric(f"Change ({earliest_year}–{latest_year})", f"{change:+.1f}%")
with col4:
    below_50 = (latest["Access"] < 50).sum()
    st.metric("Countries Below 50%", below_50)

st.divider()

tab1, tab2, tab3, tab4, tab5 = st.tabs(["Global Map", "Trends", "Comparison", "Analysis", "Data"])

with tab1:
    available_years = sorted(filtered["Year"].unique())
    map_year = st.selectbox("Select year", available_years, index=len(available_years)-1)
    map_data = filtered[filtered["Year"] == map_year]
    fig_map = px.choropleth(
        map_data,
        locations="Country Code",
        color="Access",
        hover_name="Country Name",
        hover_data={"Region": True, "IncomeGroup": True, "Access": ":.1f", "Country Code": False},
        color_continuous_scale="RdYlGn",
        range_color=[0, 100],
        labels={"Access": "Access (%)", "IncomeGroup": "Income Group"}
    )
    fig_map.update_layout(
        height=550,
        geo=dict(showframe=False, projection_type="natural earth", showcoastlines=True, coastlinecolor="lightgray"),
        margin=dict(l=0, r=0, t=30, b=0),
        coloraxis_colorbar=dict(title="Access (%)", ticksuffix="%")
    )
    st.plotly_chart(fig_map, use_container_width=True)

    top_col, bottom_col = st.columns(2)
    with top_col:
        st.markdown(f"**Top 10 Countries ({map_year})**")
        top10 = map_data.nlargest(10, "Access")[["Country Name", "Access", "Region"]].reset_index(drop=True)
        top10.index = top10.index + 1
        top10["Access"] = top10["Access"].round(1).astype(str) + "%"
        st.dataframe(top10, use_container_width=True)
    with bottom_col:
        st.markdown(f"**Bottom 10 Countries ({map_year})**")
        bottom10 = map_data.nsmallest(10, "Access")[["Country Name", "Access", "Region"]].reset_index(drop=True)
        bottom10.index = bottom10.index + 1
        bottom10["Access"] = bottom10["Access"].round(1).astype(str) + "%"
        st.dataframe(bottom10, use_container_width=True)

with tab2:
    view_by = st.radio("View trends by", ["Region", "Income Group"], horizontal=True)

    if view_by == "Region":
        trend_data = filtered.groupby(["Year", "Region"])["Access"].mean().reset_index()
        fig_trend = px.line(
            trend_data, x="Year", y="Access", color="Region",
            labels={"Access": "Access (%)", "Year": "Year"},
            markers=True
        )
    else:
        trend_data = filtered.groupby(["Year", "IncomeGroup"])["Access"].mean().reset_index()
        fig_trend = px.line(
            trend_data, x="Year", y="Access", color="IncomeGroup",
            labels={"Access": "Access (%)", "IncomeGroup": "Income Group"},
            markers=True
        )

    fig_trend.update_layout(height=500, legend=dict(orientation="h", y=-0.15))
    fig_trend.update_traces(line=dict(width=2.5))
    st.plotly_chart(fig_trend, use_container_width=True)

    st.subheader("Global Average Over Time")
    global_avg = filtered.groupby("Year")["Access"].mean().reset_index()
    fig_global = px.area(
        global_avg, x="Year", y="Access",
        labels={"Access": "Access (%)", "Year": "Year"}
    )
    fig_global.update_layout(height=350)
    fig_global.update_traces(line=dict(color="#2196F3", width=2.5), fillcolor="rgba(33,150,243,0.15)")
    st.plotly_chart(fig_global, use_container_width=True)

with tab3:
    available_countries = sorted(filtered["Country Name"].unique())
    selected_countries = st.multiselect(
        "Select countries to compare (max 10)",
        available_countries,
        default=available_countries[:3] if len(available_countries) >= 3 else available_countries,
        max_selections=10
    )

    if selected_countries:
        country_data = filtered[filtered["Country Name"].isin(selected_countries)]
        fig_compare = px.line(
            country_data, x="Year", y="Access", color="Country Name",
            labels={"Access": "Access (%)", "Country Name": "Country"},
            markers=True
        )
        fig_compare.update_layout(height=500, legend=dict(orientation="h", y=-0.15))
        st.plotly_chart(fig_compare, use_container_width=True)

        st.subheader("Country Summary")
        summary_data = country_data.groupby("Country Name").agg(
            Latest=("Access", "last"),
            Earliest=("Access", "first"),
            Average=("Access", "mean")
        ).reset_index()
        summary_data["Change"] = summary_data["Latest"] - summary_data["Earliest"]
        summary_data = summary_data.round(1)
        summary_data.index = summary_data.index + 1
        st.dataframe(summary_data, use_container_width=True)

with tab4:
available_years_analysis = sorted(filtered["Year"].unique())
analysis_year = st.selectbox("Select year", available_years_analysis, index=len(available_years_analysis)-1, key="analysis_year")
analysis_data = filtered[filtered["Year"] == analysis_year]

    col_left, col_right = st.columns(2)

    with col_left:
        st.subheader("Distribution of Access")
        fig_hist = px.histogram(
            analysis_data, x="Access", nbins=15,
            labels={"Access": "Access (%)", "count": "Number of Countries"},
            color_discrete_sequence=["#2196F3"]
        )
        fig_hist.update_layout(height=400, bargap=0.05)
        st.plotly_chart(fig_hist, use_container_width=True)

    with col_right:
        st.subheader("Access by Region")
        fig_box = px.box(
            analysis_data, x="Region", y="Access",
            labels={"Access": "Access (%)", "Region": ""},
            color="Region"
        )
        fig_box.update_layout(height=400, showlegend=False, xaxis_tickangle=-30)
        st.plotly_chart(fig_box, use_container_width=True)

    st.subheader("Access by Income Group")
    fig_bar = px.bar(
        analysis_data.groupby("IncomeGroup")["Access"].mean().reset_index().sort_values("Access"),
        x="Access", y="IncomeGroup",
        orientation="h",
        labels={"Access": "Average Access (%)", "IncomeGroup": "Income Group"},
        color="Access",
        color_continuous_scale="RdYlGn",
        range_color=[0, 100]
    )
    fig_bar.update_layout(height=300, showlegend=False, coloraxis_showscale=False)
    st.plotly_chart(fig_bar, use_container_width=True)

with tab5:
    st.subheader("Filtered Data")
    display_data = filtered[["Country Name", "Country Code", "Region", "IncomeGroup", "Year", "Access"]].copy()
    display_data["Access"] = display_data["Access"].round(2)
    display_data = display_data.sort_values(["Country Name", "Year"]).reset_index(drop=True)

    search = st.text_input("Search by country name")
    if search:
        display_data = display_data[display_data["Country Name"].str.contains(search, case=False)]

    st.dataframe(display_data, use_container_width=True, height=500)
    st.download_button(
        "Download filtered data as CSV",
        display_data.to_csv(index=False),
        "filtered_data.csv",
        "text/csv"
    )
