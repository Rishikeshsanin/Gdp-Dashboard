"""Interactive World Bank GDP comparison dashboard."""

from pathlib import Path

import altair as alt
import pandas as pd
import streamlit as st


st.set_page_config(
    page_title="GDP Atlas",
    page_icon=":material/public:",
    layout="wide",
)


DATA_FILENAME = Path(__file__).parent / "data" / "gdp_data.csv"
DEFAULT_ECONOMIES = ["DEU", "FRA", "GBR", "BRA", "MEX", "JPN"]
DEFAULT_START_YEAR = 2000
MAX_SELECTIONS = 8
CHART_HEIGHT = 430


@st.cache_data(show_spinner="Loading World Bank GDP data...")
def get_gdp_data() -> pd.DataFrame:
    """Load the source CSV and reshape annual values into tidy rows."""
    raw_gdp_df = pd.read_csv(DATA_FILENAME)
    year_columns = sorted(
        (column for column in raw_gdp_df.columns if column.isdigit()),
        key=int,
    )

    gdp_df = raw_gdp_df.melt(
        id_vars=["Country Name", "Country Code"],
        value_vars=year_columns,
        var_name="Year",
        value_name="GDP",
    )
    gdp_df["Year"] = pd.to_numeric(gdp_df["Year"]).astype(int)
    gdp_df["GDP"] = pd.to_numeric(gdp_df["GDP"], errors="coerce")
    return gdp_df.sort_values(["Country Name", "Year"]).reset_index(drop=True)


def format_currency(value: float | None) -> str | None:
    """Format a GDP value using a readable US-dollar suffix."""
    if value is None or pd.isna(value):
        return None

    absolute_value = abs(value)
    if absolute_value >= 1_000_000_000_000:
        return f"${value / 1_000_000_000_000:,.2f}T"
    if absolute_value >= 1_000_000_000:
        return f"${value / 1_000_000_000:,.1f}B"
    if absolute_value >= 1_000_000:
        return f"${value / 1_000_000:,.1f}M"
    return f"${value:,.0f}"


def growth_rate(start_value: float | None, end_value: float | None) -> float | None:
    """Return percentage growth when both endpoints are comparable."""
    if (
        start_value is None
        or end_value is None
        or pd.isna(start_value)
        or pd.isna(end_value)
        or start_value == 0
    ):
        return None
    return ((end_value / start_value) - 1) * 100


def value_for_year(economy_data: pd.DataFrame, year: int) -> float | None:
    """Return an economy's GDP for an exact year, if reported."""
    values = economy_data.loc[economy_data["Year"] == year, "GDP"]
    if values.empty or pd.isna(values.iloc[0]):
        return None
    return float(values.iloc[0])


def render_trend_chart(chart_data: pd.DataFrame) -> None:
    """Render an interactive multi-economy GDP chart."""
    chart_data = chart_data.assign(
        Economy=chart_data["Country Name"] + " · " + chart_data["Country Code"],
        GDP_trillions=chart_data["GDP"] / 1_000_000_000_000,
    )

    nearest_year = alt.selection_point(
        name="nearest_year",
        fields=["Year"],
        nearest=True,
        on="pointerover",
        empty=False,
    )

    base = alt.Chart(chart_data).encode(
        x=alt.X(
            "Year:Q",
            title=None,
            axis=alt.Axis(format="d", tickCount=10, labelFlush=False),
        ),
        y=alt.Y(
            "GDP_trillions:Q",
            title="GDP (current US$, trillions)",
            axis=alt.Axis(format="$,.1f"),
            scale=alt.Scale(zero=False),
        ),
        color=alt.Color(
            "Economy:N",
            title=None,
            legend=alt.Legend(
                orient="bottom",
                direction="horizontal",
                columns=3,
                symbolType="stroke",
            ),
        ),
    )

    lines = base.mark_line(strokeWidth=2.5)
    points = base.mark_circle(size=80).encode(
        opacity=alt.condition(nearest_year, alt.value(1), alt.value(0)),
        tooltip=[
            alt.Tooltip("Country Name:N", title="Economy"),
            alt.Tooltip("Country Code:N", title="Code"),
            alt.Tooltip("Year:Q", title="Year", format=".0f"),
            alt.Tooltip("GDP:Q", title="GDP", format="$,.3s"),
        ],
    )
    selectors = (
        alt.Chart(chart_data)
        .mark_point(opacity=0)
        .encode(x="Year:Q")
        .add_params(nearest_year)
    )
    rule = (
        alt.Chart(chart_data)
        .mark_rule(strokeDash=[4, 4], opacity=0.35)
        .encode(x="Year:Q")
        .transform_filter(nearest_year)
    )

    chart = (
        (lines + points + selectors + rule)
        .properties(height=CHART_HEIGHT)
        .configure_axis(gridOpacity=0.18, domain=False, tickSize=0, labelPadding=8)
        .configure_view(strokeWidth=0)
        .configure_legend(labelLimit=220, offset=18)
    )
    st.altair_chart(chart, width="stretch", key="gdp_trend_chart")


gdp_df = get_gdp_data()
economy_lookup = (
    gdp_df[["Country Code", "Country Name"]]
    .drop_duplicates()
    .set_index("Country Code")["Country Name"]
    .to_dict()
)
economy_codes = sorted(economy_lookup, key=lambda code: economy_lookup[code])
min_year = int(gdp_df["Year"].min())
max_year = int(gdp_df["Year"].max())
default_economies = [code for code in DEFAULT_ECONOMIES if code in economy_lookup]


with st.sidebar:
    st.markdown("## :material/public: GDP Atlas")
    st.caption("A focused view of the world economy across six decades.")

    st.space("small")
    st.markdown("**Build your comparison**")
    selected_economies = st.multiselect(
        "Economies",
        options=economy_codes,
        default=default_economies,
        format_func=lambda code: f"{economy_lookup[code]} · {code}",
        max_selections=MAX_SELECTIONS,
        placeholder="Search by economy or code",
        key="selected_economies",
        help=f"Select up to {MAX_SELECTIONS} countries, territories, or World Bank groups.",
    )
    from_year, to_year = st.slider(
        "Year range",
        min_value=min_year,
        max_value=max_year,
        value=(max(min_year, DEFAULT_START_YEAR), max_year),
        key="year_range",
    )
    st.caption(
        f"{len(selected_economies)} selected · {to_year - from_year + 1} annual periods"
    )

    st.space("medium")
    st.markdown("**About the data**")
    st.caption(
        "GDP is reported in current US dollars. Missing observations are left "
        "unfilled so the dashboard never invents values."
    )
    st.link_button(
        "Open World Bank source",
        "https://data.worldbank.org/indicator/NY.GDP.MKTP.CD",
        icon=":material/open_in_new:",
        type="tertiary",
    )


st.markdown("# :material/public: GDP Atlas")
st.caption(
    "Compare the scale and trajectory of economies with World Bank GDP data."
)
st.markdown(
    f":blue-badge[:material/database: World Bank] "
    f":gray-badge[{min_year}–{max_year}] "
    ":green-badge[Current US$]"
)
st.space("small")


if not selected_economies:
    st.warning(
        "Choose at least one economy from the sidebar to begin comparing GDP.",
        icon=":material/tune:",
    )
    st.stop()


filtered_gdp_df = gdp_df[
    gdp_df["Country Code"].isin(selected_economies)
    & gdp_df["Year"].between(from_year, to_year)
].copy()
reported_gdp_df = filtered_gdp_df.dropna(subset=["GDP"])

expected_observations = len(selected_economies) * (to_year - from_year + 1)
coverage = (
    len(reported_gdp_df) / expected_observations * 100
    if expected_observations
    else 0
)

start_values = filtered_gdp_df[filtered_gdp_df["Year"] == from_year].set_index(
    "Country Code"
)["GDP"]
end_values = filtered_gdp_df[filtered_gdp_df["Year"] == to_year].set_index(
    "Country Code"
)["GDP"]
comparable_codes = [
    code
    for code in selected_economies
    if code in start_values
    and code in end_values
    and pd.notna(start_values[code])
    and pd.notna(end_values[code])
    and start_values[code] != 0
]

combined_latest = end_values.dropna().sum(min_count=1)
combined_growth = None
if comparable_codes:
    comparable_start = float(start_values.loc[comparable_codes].sum())
    comparable_end = float(end_values.loc[comparable_codes].sum())
    combined_growth = growth_rate(comparable_start, comparable_end)

latest_ranked = (
    filtered_gdp_df[filtered_gdp_df["Year"] == to_year]
    .dropna(subset=["GDP"])
    .sort_values("GDP", ascending=False)
)

summary_columns = st.columns(4)
with summary_columns[0]:
    st.metric(
        "Selected economies",
        len(selected_economies),
        delta=f"Up to {MAX_SELECTIONS}",
        delta_color="off",
        delta_arrow="off",
        border=True,
    )
with summary_columns[1]:
    st.metric(
        "Data coverage",
        f"{coverage:.0f}%",
        delta=f"{len(reported_gdp_df):,} reported values",
        delta_color="off",
        delta_arrow="off",
        border=True,
        help="Share of selected economy-year observations with a reported GDP value.",
    )
with summary_columns[2]:
    st.metric(
        f"Combined GDP · {to_year}",
        format_currency(float(combined_latest))
        if pd.notna(combined_latest)
        else None,
        delta=f"{combined_growth:+.1f}%" if combined_growth is not None else None,
        delta_description=f"vs. {from_year}",
        border=True,
        help="Sum of selected economies that report GDP in the ending year.",
    )
with summary_columns[3]:
    if latest_ranked.empty:
        st.metric(
            f"Largest · {to_year}",
            None,
            delta="No reported values",
            delta_color="off",
            delta_arrow="off",
            border=True,
        )
    else:
        largest = latest_ranked.iloc[0]
        st.metric(
            f"Largest · {to_year}",
            format_currency(float(largest["GDP"])),
            delta=str(largest["Country Name"]),
            delta_color="off",
            delta_arrow="off",
            border=True,
        )


st.space("small")
with st.container(border=True):
    st.markdown("### GDP over time")
    st.caption(
        f"Annual GDP from {from_year} to {to_year}. Hover over the chart for exact values."
    )
    if reported_gdp_df.empty:
        st.warning(
            "No GDP observations are available for this selection and period.",
            icon=":material/data_alert:",
        )
    else:
        render_trend_chart(reported_gdp_df)


st.space("small")
st.markdown(f"### Economy snapshot · {to_year}")
st.caption(
    "Each card compares the exact start and end years. Missing endpoints are shown explicitly."
)

for row_start in range(0, len(selected_economies), 3):
    row_codes = selected_economies[row_start : row_start + 3]
    columns = st.columns(3)

    for column, code in zip(columns, row_codes):
        economy_data = filtered_gdp_df[
            filtered_gdp_df["Country Code"] == code
        ].sort_values("Year")
        start_value = value_for_year(economy_data, from_year)
        end_value = value_for_year(economy_data, to_year)
        economy_growth = growth_rate(start_value, end_value)
        sparkline = economy_data["GDP"].dropna().tolist()

        with column:
            st.metric(
                f"{economy_lookup[code]} · {code}",
                format_currency(end_value),
                delta=f"{economy_growth:+.1f}%" if economy_growth is not None else None,
                delta_description=(
                    f"{from_year} to {to_year}"
                    if economy_growth is not None
                    else f"Missing endpoint for {from_year} or {to_year}"
                ),
                delta_color="normal" if economy_growth is not None else "off",
                delta_arrow="auto" if economy_growth is not None else "off",
                chart_data=sparkline or None,
                chart_type="line",
                border=True,
            )


with st.expander(
    "Explore the comparison table",
    icon=":material/table_chart:",
):
    summary_rows = []
    for code in selected_economies:
        economy_data = filtered_gdp_df[
            filtered_gdp_df["Country Code"] == code
        ].sort_values("Year")
        start_value = value_for_year(economy_data, from_year)
        end_value = value_for_year(economy_data, to_year)
        summary_rows.append(
            {
                "Economy": economy_lookup[code],
                "Code": code,
                f"GDP {to_year} (US$T)": (
                    end_value / 1_000_000_000_000
                    if end_value is not None
                    else None
                ),
                "Period change": (
                    growth_rate(start_value, end_value) / 100
                    if growth_rate(start_value, end_value) is not None
                    else None
                ),
                "Reported years": int(economy_data["GDP"].notna().sum()),
                "Trend": economy_data["GDP"].dropna().tolist(),
            }
        )

    summary_df = pd.DataFrame(summary_rows).sort_values(
        f"GDP {to_year} (US$T)", ascending=False, na_position="last"
    )
    st.dataframe(
        summary_df,
        hide_index=True,
        column_config={
            "Economy": st.column_config.TextColumn("Economy", pinned=True),
            "Code": st.column_config.TextColumn("Code", width="small"),
            f"GDP {to_year} (US$T)": st.column_config.NumberColumn(
                f"GDP {to_year}", format="$%.2fT"
            ),
            "Period change": st.column_config.NumberColumn(
                f"Change since {from_year}", format="percent"
            ),
            "Reported years": st.column_config.NumberColumn(
                "Reported years", format="%d"
            ),
            "Trend": st.column_config.LineChartColumn(
                "Trend", width="medium"
            ),
        },
        key="economy_summary_table",
    )


st.caption(
    "Source: World Bank Open Data · Indicator NY.GDP.MKTP.CD · "
    "Dataset includes countries, territories, and World Bank aggregate groups."
)
st.caption(
    "Original project by [Mukund](https://github.com/mukundfeb) · "
    "Redesigned as GDP Atlas."
)
