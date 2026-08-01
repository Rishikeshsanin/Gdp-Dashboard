# GDP Atlas

GDP Atlas is an interactive Streamlit dashboard for comparing the scale and
trajectory of economies using World Bank GDP data.

## Highlights

- Compare up to eight economies across any year range from 1960 to 2022.
- Search using full economy names or three-letter codes.
- Explore combined GDP, coverage, growth, rankings, and individual trends.
- Inspect exact values through interactive chart tooltips and a comparison table.
- Switch between purpose-built light and dark themes.
- See missing observations clearly without interpolation.

## Run locally

```bash
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
streamlit run streamlit_app.py
```

On macOS or Linux, activate the environment with `source .venv/bin/activate`.

## Data source

The included dataset uses the World Bank indicator
[`NY.GDP.MKTP.CD`](https://data.worldbank.org/indicator/NY.GDP.MKTP.CD), GDP
in current US dollars. It contains countries, territories, and World Bank
aggregate groups, with some missing annual observations.

## Contributors

- [Mukund](https://github.com/mukundfeb) — original project and baseline implementation
- [Rishikesh Sanin](https://github.com/Rishikeshsanin) — GDP Atlas redesign

This project is based on Streamlit's GDP dashboard template and retains its
Apache 2.0 license.
