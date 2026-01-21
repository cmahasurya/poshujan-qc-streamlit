import streamlit as st
import pandas as pd
import numpy as np

st.set_page_config(page_title="Transposer POS HUJAN + QC Dasarian", layout="wide")

st.title("Transposer POS HUJAN (Vertikal → Horizontal) + QC Dasarian")

uploaded = st.file_uploader("Upload CSV format vertikal", type=["csv"])
if uploaded is None:
    st.info("Upload file CSV dulu.")
    st.stop()

# ---- Read CSV
df = pd.read_csv(uploaded)

# ---- Basic checks
required = ["NAME", "DATA TIMESTAMP"]
missing = [c for c in required if c not in df.columns]
if missing:
    st.error(f"Kolom wajib tidak ada: {missing}")
    st.stop()

# ---- Parse datetime safely (avoid the warning you saw)
df["DATA TIMESTAMP"] = pd.to_datetime(df["DATA TIMESTAMP"], errors="coerce", utc=False)

# If you have a rainfall column name, adapt here:
# e.g. "RAINFALL DAY MM" or similar
rain_col = st.selectbox(
    "Pilih kolom curah hujan",
    options=[c for c in df.columns if c not in ["NAME"]],
    index=0
)

# ---- Apply your QC rules
# 9999 as NaN (broken), 8888 -> 0.1, (and maybe 0 rainfall stays 0)
df[rain_col] = pd.to_numeric(df[rain_col], errors="coerce")
df.loc[df[rain_col] == 9999, rain_col] = np.nan
df.loc[df[rain_col] == 8888, rain_col] = 0.1

# ---- Optional: station name mapping (example “Kateng”)
# If your NAME values need standardization, do mapping here:
name_map = {
    "Kateng": "Kateng (lombok Tengah)",
}
df["NAME"] = df["NAME"].replace(name_map)

# ---- Pivot to horizontal
wide = df.pivot_table(
    index=df["DATA TIMESTAMP"].dt.date,
    columns="NAME",
    values=rain_col,
    aggfunc="first"
).reset_index()

wide = wide.rename(columns={"DATA TIMESTAMP": "DATE"})
wide = wide.rename(columns={wide.columns[0]: "DATE"})

st.subheader("Hasil Transpose (Horizontal)")
st.dataframe(wide, use_container_width=True)

# ---- Summary: stations empty on last day
# Define "last day" as max DATE in the dataset
last_day = wide["DATE"].max()
row_last = wide.loc[wide["DATE"] == last_day]

if len(row_last) == 1:
    last_row = row_last.iloc[0]
    empty_stations = []
    for c in wide.columns:
        if c == "DATE":
            continue
        if pd.isna(last_row[c]):
            empty_stations.append(c)

    st.subheader("Summary kosong pada 1 hari terakhir")
    st.write(f"Tanggal terakhir dalam data: **{last_day}**")
    st.write(f"Jumlah pos kosong: **{len(empty_stations)}**")

    if empty_stations:
        st.dataframe(pd.DataFrame({"Pos kosong": empty_stations}))
else:
    st.warning("Tidak bisa menentukan 1 hari terakhir secara unik (cek data tanggal).")

# ---- Download outputs
csv_out = wide.to_csv(index=False).encode("utf-8")
st.download_button(
    "Download CSV (hasil transpose + QC)",
    data=csv_out,
    file_name="poshujan_transpose_qc.csv",
    mime="text/csv"
)
