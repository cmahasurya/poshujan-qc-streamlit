# poshujan-qc-streamlit
Rainfall Transposition, QC, Indices, and Interactive Mapping

This Streamlit application processes daily rainfall station data (POS HUJAN) into BMKG-style horizontal tables, performs quality control (QC), computes dasarian summaries and rainfall indices, and visualizes results using an interactive map.

The app is designed for operational use, with a fixed station order to ensure consistent outputs.

Main Features
1. Data Transposition (BMKG Format)

Input: Vertical daily rainfall data (one row per station per day)

Output: Horizontal table (one row per date, one column per station)

Station order is fixed and predefined

BMKG Display Rules

Raw value	Display	Numeric value
0	-	0.0
8888 (trace)	0	0.1
9999 / empty	x	NaN
No record	x	NaN
2. Quality Control (QC)

Data completeness per station (%)

Data completeness per day

Stations with no data during the dasarian

Stations missing data on the last day

Days since last observation

Unmapped or mismatched station names

3. Dasarian Summary & Indices

Total rainfall per station (dasarian)

Maximum daily rainfall and date

Longest CDD (Consecutive Dry Days)

Longest CWD (Consecutive Wet Days)

Maximum rainfall in the last dasarian

4. Interactive Map

Built with PyDeck (no Mapbox token required)

Scatter map and heatmap modes

Hover tooltips

Dynamic legend

Filters for QC issues

Map coloring by:

Coordinate QC

Data completeness

Rainfall accumulation

CDD / CWD

Maximum rainfall
