import streamlit as st
import pandas as pd
import numpy as np
from datetime import date

st.set_page_config(
    page_title="Transposer POS HUJAN + QC Dasarian",
    layout="wide"
)

st.title("Transposer POS HUJAN (Vertikal → Horizontal) + QC Dasarian")

st.markdown(
    """
Notebook ini diubah menjadi aplikasi Streamlit untuk:
- Transpose data curah hujan harian format vertikal menjadi horizontal (kolom stasiun).
- QC kelengkapan per stasiun dan per hari.
- Ringkasan stasiun kosong pada hari terakhir dalam jendela dasarian.
- Output tersedia dalam format DISPLAY dan NUMERIC.

Aturan nilai DISPLAY:
- raw = 0 → "-"
- raw = 8888 → "0"
- raw = 9999 atau NaN atau tidak ada baris → "x"
- raw > 0 dan bukan 8888/9999 → angka hujan

Aturan nilai NUMERIC:
- raw = 0 → 0.0
- raw = 8888 → 0.1
- raw = 9999 atau NaN atau tidak ada baris → NaN
"""
)

# ----------------------------
# HARD CODE: HORIZONTAL_COLS + NAME_MAP
# ----------------------------
HORIZONTAL_COLS = [
    "Ampenan","Cakranegara","Majeluk","Selaparang","Batu Layar","Buwun Mas",
    "Banter Gerung / Banyu Urip","Gerung","Gunung Sari","Labuapi","Lembar",
    "Narmada","Pelangan","Rumak","Sekotong/Cendimanik","Sigerongan",
    "Stasiun Klimatologi Kediri","Bayan","BBI Santong","Gangga","Pemenang",
    "Pemenang Timur","Sambik Bangkol","Senaru","Tanjung","Batukliang Utara",
    "Batu Nyala/lajut","Darek","Janapria","Kopang","Mantang/Batukliang",
    "Mertak","Mujur","Mujur 2","Praya /Aikmual","Praya Barat /Penujak",
    "Pringgarata","Pujut","Puyung /Jonggat","Selong Belanak","STAMET BIL",
    "Aikmel","Jerowaru / Sepapan","karang baru timur/Wanasaba","Keruak",
    "Kokok Putih Sembalun","Kotaraja /montong gading","Labuhan Haji",
    "Labuhan Pandan","Lenek Duren","Masbagik","Montong Baan / Sikur",
    "Perigi","Pringgabaya","Pringgasela","Rarang Selatan",
    "Rensing Sakra Barat","Sambelia","Sembalun",
    "Sukamulia /Dasan Lekong","Swela","Terara","Brang Ene","Brang rea",
    "Maluk","Tano","Tapir /Seteluk","Jereweh","Taliwang","Sekongkang",
    "Alas","Alas Barat","Batulanteh / Semongkat","Buer","Diperta SBW",
    "Empang","Lab. Badas","Lape","Lenangguar","Lunyuk (Lunyuk Ode)",
    "Moyo Hilir","Moyo Hulu","Orong Telu","Plampang","Rhee",
    "Sebewe Moyo Utara","Stasiun Meteorologi Sumbawa","Sukadamai/Labangka",
    "Tarano","Utan","Dompu","Huu","Kilo","Manggalewa","Pajo",
    "Pekat/Calabai","Saneo Woja","Bolo","Donggo (Oo)","Lambu","Madapangga",
    "Madapangga 2","Monta","Palibelo Panda","Palibelo (Teke)","Sanggar",
    "Sape","Sape2","Soromandi","Stamet Bima","Wawo","Wera","Woha",
    "Asakota","Kolo","Raba","Rasanae Timur","Kempo (Dompu)",
    "Tambora (Bima)","Unter Iwes (Sumbawa)","Donggo Ndano (Bima)",
    "Langgudu Doro Oo (Bima)","Belo (Bima)","Parado (Bima)",
    "Lambitu (Bima)","Kateng (lombok Tengah)",
    "Pandan wangi (Lotim)","Selong (Lotim)"
]

NAME_MAP = {
    "Batulayar": "Batu Layar",
    "Banyu Urip/Banter": "Banter Gerung / Banyu Urip",
    "Sekotong": "Sekotong/Cendimanik",
    "Staklim Lobar": "Stasiun Klimatologi Kediri",
    "Stamet BIL": "STAMET BIL",
    "Praya": "Praya /Aikmual",
    "Puyung": "Puyung /Jonggat",
    "Mantang": "Mantang/Batukliang",
    "Batu Nyala": "Batu Nyala/lajut",
    "Mujur2/Bilelando": "Mujur 2",
    "Kr Baru Timur/Wanasaba": "karang baru timur/Wanasaba",
    "Kotaraja/Montong Gading": "Kotaraja /montong gading",
    "Jerowaru/Sepapan": "Jerowaru / Sepapan",
    "Kokok Putih/Sembalun": "Kokok Putih Sembalun",
    "Pandan Wangi": "Pandan wangi (Lotim)",
    "Selong": "Selong (Lotim)",
    "Semongkat": "Batulanteh / Semongkat",
    "Diperta Sumbawa": "Diperta SBW",
    "Sebewe/Moyo Utara": "Sebewe Moyo Utara",
    "Stamet Sumbawa": "Stasiun Meteorologi Sumbawa",
    "Unter Iwes": "Unter Iwes (Sumbawa)",
    "Lunyuk": "Lunyuk (Lunyuk Ode)",
    "Kempo": "Kempo (Dompu)",
    "Tambora": "Tambora (Bima)",
    "Donggo2/Ndano": "Donggo Ndano (Bima)",
    "Doro O'o": "Langgudu Doro Oo (Bima)",
    "Belo": "Belo (Bima)",
    "Parado": "Parado (Bima)",
    "Lambitu": "Lambitu (Bima)",
    "Palibelo Teke": "Palibelo (Teke)",
    "Sape 2": "Sape2",
    "Asakota/Jatiwangi": "Asakota",
    "Asakota/Kolo": "Kolo",
    "Santong": "BBI Santong",
    "Moyo hilir": "Moyo Hilir",
    "Moyo hulu": "Moyo Hulu",
    "Brang Rea": "Brang rea",
    "Donggo": "Donggo (Oo)",
    "Penujak": "Praya Barat /Penujak",
    "Sikur": "Montong Baan / Sikur",
    "Sukamulia/Dasan Lekong": "Sukamulia /Dasan Lekong",
    "Tapir/Seteluk": "Tapir /Seteluk",
    "Kateng": "Kateng (lombok Tengah)",
}

# ----------------------------
# Helpers
# ----------------------------
def month_end_day(year: int, month: int) -> int:
    month_start = pd.Timestamp(year=year, month=month, day=1)
    month_end = (month_start + pd.offsets.MonthEnd(1)).normalize()
    return int(month_end.day)

def normalize_station_name(s: pd.Series) -> pd.Series:
    return (
        s.astype(str)
        .str.strip()
        .str.replace(r"\s+", " ", regex=True)
    )

def to_csv_bytes(df: pd.DataFrame) -> bytes:
    return df.to_csv(index=False).encode("utf-8")

def build_outputs(df_month: pd.DataFrame, end_day: int):
    all_days = np.arange(1, end_day + 1)

    df_month = df_month.copy()
    df_month["NAME"] = normalize_station_name(df_month["NAME"])
    df_month["NAME_H"] = df_month["NAME"].replace(NAME_MAP)

    df_month["raw"] = pd.to_numeric(df_month["RAINFALL DAY MM"], errors="coerce")
    df_month["has_row"] = 1

    # Numeric mapping
    rain_num = df_month["raw"].copy()
    rain_num[df_month["raw"].isna()] = np.nan
    rain_num[df_month["raw"] == 9999] = np.nan
    rain_num[df_month["raw"] == 8888] = 0.1
    rain_num[df_month["raw"] == 0] = 0.0
    df_month["rain_num"] = rain_num

    # Wide tables with required order
    wide_raw = (
        df_month.pivot_table(index="TGL", columns="NAME_H", values="raw", aggfunc="first")
        .reindex(index=all_days, columns=HORIZONTAL_COLS)
    )
    wide_num = (
        df_month.pivot_table(index="TGL", columns="NAME_H", values="rain_num", aggfunc="first")
        .reindex(index=all_days, columns=HORIZONTAL_COLS)
    )
    present = (
        df_month.pivot_table(index="TGL", columns="NAME_H", values="has_row", aggfunc="first")
        .reindex(index=all_days, columns=HORIZONTAL_COLS)
    )

    # DISPLAY rules
    wide_display = pd.DataFrame("x", index=wide_raw.index, columns=wide_raw.columns)
    row_exists = present.notna()

    wide_display = wide_display.mask(row_exists & (wide_raw == 0), "-")
    wide_display = wide_display.mask(row_exists & (wide_raw == 8888), "0")

    is_pos_measured = row_exists & (wide_raw.notna()) & (wide_raw > 0) & (wide_raw != 8888) & (wide_raw != 9999)
    wide_display = wide_display.mask(is_pos_measured, wide_raw.astype(float))

    wide_display_out = wide_display.copy()
    wide_display_out.insert(0, "TGL", wide_display_out.index)

    wide_num_out = wide_num.copy()
    wide_num_out.insert(0, "TGL", wide_num_out.index)

    # QC station completeness
    station_summary = pd.DataFrame({
        "station": HORIZONTAL_COLS,
        "days_present": present.notna().sum(axis=0).astype(int).values,
        "total_days": len(present.index),
    })
    station_summary["completeness_pct"] = (station_summary["days_present"] / station_summary["total_days"] * 100).round(1)

    # QC day completeness
    day_summary = pd.DataFrame({
        "TGL": present.index,
        "stations_present": present.notna().sum(axis=1).astype(int).values,
        "total_stations": len(HORIZONTAL_COLS),
    })
    day_summary["completeness_pct"] = (day_summary["stations_present"] / day_summary["total_stations"] * 100).round(1)

    # QC unmapped
    horizontal_set = set(HORIZONTAL_COLS)
    mapped_not_in_horizontal = sorted(set(df_month["NAME_H"].unique()) - horizontal_set)
    qc_unmapped = (
        df_month[df_month["NAME_H"].isin(mapped_not_in_horizontal)][["NAME", "NAME_H"]]
        .drop_duplicates()
        .sort_values(["NAME_H", "NAME"])
    )

    # QC gap summary
    last_present_day = present.notna().apply(lambda s: s[s].index.max() if s.any() else np.nan)
    gap_days_since_last = (end_day - last_present_day).where(~last_present_day.isna(), np.nan)
    empty_all_window = present.notna().sum(axis=0) == 0

    empty_gap_summary = pd.DataFrame({
        "station": HORIZONTAL_COLS,
        "has_any_record_1_to_end_das": (~empty_all_window).astype(int).values,
        "last_record_day_in_window": last_present_day.reindex(HORIZONTAL_COLS).values,
        "empty_days_since_last_record": gap_days_since_last.reindex(HORIZONTAL_COLS).values
    })

    # QC empty on last day
    last_day_present = present.loc[end_day].notna()
    empty_last_day_df = pd.DataFrame({
        "station": HORIZONTAL_COLS,
        "is_empty_on_last_day": (~last_day_present.reindex(HORIZONTAL_COLS).fillna(False)).astype(int).values,
        "last_record_day_in_window": last_present_day.reindex(HORIZONTAL_COLS).values
    })

    empty_last_day_df["empty_days_up_to_last_day"] = np.where(
        empty_last_day_df["last_record_day_in_window"].isna(),
        float(end_day),
        float(end_day) - empty_last_day_df["last_record_day_in_window"].astype(float)
    )

    empty_last_day_df = empty_last_day_df[empty_last_day_df["is_empty_on_last_day"] == 1].copy()
    empty_last_day_df = empty_last_day_df.sort_values(
        ["empty_days_up_to_last_day", "station"],
        ascending=[False, True]
    )

    # Strict order assertion
    assert list(wide_display_out.columns[1:]) == HORIZONTAL_COLS, "Urutan kolom output tidak sesuai HORIZONTAL_COLS"

    return {
        "wide_display_out": wide_display_out,
        "wide_num_out": wide_num_out,
        "qc_station": station_summary.sort_values(["completeness_pct", "station"], ascending=[True, True]),
        "qc_day": day_summary,
        "qc_unmapped": qc_unmapped,
        "qc_gap": empty_gap_summary,
        "qc_empty_last_day": empty_last_day_df
    }

# ----------------------------
# Sidebar controls
# ----------------------------
with st.sidebar:
    st.header("Input")

    up = st.file_uploader(
        "Upload CSV vertikal",
        type=["csv"],
        accept_multiple_files=True
    )

    today = date.today()
    year = st.number_input("Year", min_value=2000, max_value=2100, value=int(today.year), step=1)
    month = st.selectbox("Month", options=[f"{i:02d}" for i in range(1, 13)], index=int(today.month) - 1)

    dasarian = st.radio(
        "Dasarian",
        options=["1", "2", "3"],
        format_func=lambda x: "Das 1 (1-10)" if x == "1" else ("Das 2 (1-20)" if x == "2" else "Das 3 (Full month)"),
        index=0
    )

    run = st.button("Run transpose + QC", type="primary", use_container_width=True)

# ----------------------------
# Main run
# ----------------------------
if not run:
    st.info("Upload file, pilih Year, Month, Dasarian, lalu klik Run transpose + QC.")
    st.stop()

if not up:
    st.error("Belum ada file yang diupload.")
    st.stop()

YEAR = int(year)
MM = str(month)
MONTH_STR = f"{YEAR}-{MM}"
das_n = int(dasarian)

last_day = month_end_day(YEAR, int(MM))
end_day = 10 if das_n == 1 else (20 if das_n == 2 else last_day)

st.subheader("Parameter")
st.write(f"Periode: **{MONTH_STR}**")
st.write(f"Dasarian: **{das_n}** | Rentang tanggal: **1 s.d. {end_day}**")
st.write(f"Total stasiun (kolom output): **{len(HORIZONTAL_COLS)}**")

# Read and concat uploads
dfs = []
bad_files = []
for f in up:
    try:
        tmp = pd.read_csv(f)
        tmp["__source_file__"] = f.name
        dfs.append(tmp)
    except Exception:
        bad_files.append(f.name)

if bad_files:
    st.warning(f"File gagal dibaca dan diabaikan: {bad_files}")

if not dfs:
    st.error("Tidak ada file valid untuk diproses.")
    st.stop()

df = pd.concat(dfs, ignore_index=True)

required_cols = ["NAME", "DATA TIMESTAMP", "RAINFALL DAY MM"]
missing_cols = [c for c in required_cols if c not in df.columns]
if missing_cols:
    st.error(f"Kolom wajib tidak ditemukan: {missing_cols}")
    st.stop()

# Parse datetime safely
df["DATA TIMESTAMP"] = pd.to_datetime(df["DATA TIMESTAMP"], errors="coerce")
df = df[df["DATA TIMESTAMP"].notna()].copy()

df_month = df[df["DATA TIMESTAMP"].dt.strftime("%Y-%m") == MONTH_STR].copy()
if df_month.empty:
    st.error(f"Tidak ada baris untuk {MONTH_STR}. Periksa pilihan bulan atau data.")
    st.stop()

df_month["TGL"] = df_month["DATA TIMESTAMP"].dt.day
df_month = df_month[df_month["TGL"].between(1, end_day)].copy()
if df_month.empty:
    st.error(f"Tidak ada baris pada rentang tanggal 1 s.d. {end_day} untuk {MONTH_STR}.")
    st.stop()

# Build outputs
outputs = build_outputs(df_month, end_day)

wide_display_out = outputs["wide_display_out"]
wide_num_out = outputs["wide_num_out"]
qc_station = outputs["qc_station"]
qc_day = outputs["qc_day"]
qc_unmapped = outputs["qc_unmapped"]
qc_gap = outputs["qc_gap"]
qc_empty_last_day = outputs["qc_empty_last_day"]

# ----------------------------
# Highlights
# ----------------------------
st.subheader("Ringkasan QC")

total_cells = (end_day) * len(HORIZONTAL_COLS)
cells_with_row = int((wide_display_out.drop(columns=["TGL"]) != "x").to_numpy().sum())
coverage_pct = round(cells_with_row / total_cells * 100, 2)

c1, c2, c3 = st.columns(3)
c1.metric("Coverage", f"{coverage_pct}%")
c2.metric("Cells with record", f"{cells_with_row}/{total_cells}")
c3.metric("Stations", f"{len(HORIZONTAL_COLS)}")

empty_all_stations = qc_gap[qc_gap["has_any_record_1_to_end_das"] == 0]["station"].tolist()
with st.expander("Stasiun kosong total pada jendela dasarian"):
    if empty_all_stations:
        st.dataframe(pd.DataFrame({"station": empty_all_stations}), use_container_width=True)
    else:
        st.write("Tidak ada")

with st.expander(f"Stasiun kosong pada hari terakhir (TGL={end_day})"):
    if qc_empty_last_day.empty:
        st.write("Tidak ada")
    else:
        st.dataframe(qc_empty_last_day, use_container_width=True)

if not qc_unmapped.empty:
    with st.expander("Nama hasil mapping yang tidak ada di header horizontal"):
        st.dataframe(qc_unmapped, use_container_width=True)

# ----------------------------
# View choice
# ----------------------------
st.subheader("Tampilan tabel")
view_choice = st.radio(
    "Pilih tampilan",
    options=["DISPLAY (x / - / 0 / angka)", "NUMERIC (NaN / 0.1 / angka)"],
    index=0,
    horizontal=True
)

if view_choice.startswith("DISPLAY"):
    st.dataframe(wide_display_out, use_container_width=True)
else:
    st.dataframe(wide_num_out, use_container_width=True)

# ----------------------------
# Downloads
# ----------------------------
st.subheader("Download")

download_choice = st.selectbox(
    "Pilih file yang ingin di-download",
    [
        f"rain_horizontal_{MONTH_STR}_das{das_n}_display.csv",
        f"rain_horizontal_{MONTH_STR}_das{das_n}_numeric.csv",
        f"QC_station_completeness_{MONTH_STR}_das{das_n}.csv",
        f"QC_day_completeness_{MONTH_STR}_das{das_n}.csv",
        f"QC_unmapped_names_{MONTH_STR}_das{das_n}.csv",
        f"QC_station_empty_gap_{MONTH_STR}_das{das_n}.csv",
        f"QC_empty_last_day_{MONTH_STR}_das{das_n}.csv",
    ],
    index=0
)

download_map = {
    f"rain_horizontal_{MONTH_STR}_das{das_n}_display.csv": wide_display_out,
    f"rain_horizontal_{MONTH_STR}_das{das_n}_numeric.csv": wide_num_out,
    f"QC_station_completeness_{MONTH_STR}_das{das_n}.csv": qc_station,
    f"QC_day_completeness_{MONTH_STR}_das{das_n}.csv": qc_day,
    f"QC_unmapped_names_{MONTH_STR}_das{das_n}.csv": qc_unmapped,
    f"QC_station_empty_gap_{MONTH_STR}_das{das_n}.csv": qc_gap,
    f"QC_empty_last_day_{MONTH_STR}_das{das_n}.csv": qc_empty_last_day,
}

df_dl = download_map[download_choice]
st.download_button(
    label=f"Download: {download_choice}",
    data=to_csv_bytes(df_dl),
    file_name=download_choice,
    mime="text/csv",
    use_container_width=True
)
