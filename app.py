import streamlit as st
import pandas as pd
import numpy as np
from datetime import date

# ============================================================
# Page
# ============================================================
st.set_page_config(
    page_title="Dashboard POS HUJAN Dasarian",
    layout="wide"
)

st.title("Pos Hujan Dasarian: Rekap, Indeks, dan QC")
st.caption("Transpose vertikal → horizontal (urut stasiun fix) + FORMAT BMKG + NUMERIC + QC + Ringkasan + CDD/CWD/CHmax")

st.markdown(
    """
Aplikasi ini:
- Mengubah data curah hujan harian format vertikal menjadi tabel horizontal (kolom stasiun) dengan urutan kolom mengikuti `HORIZONTAL_COLS`.
- Menyediakan 2 format hasil:
  - **FORMAT BMKG**: `x`, `-`, `0`, atau angka hujan.
  - **NUMERIC**: angka hujan (trace 0.1), missing = NaN.
- Menyediakan QC kelengkapan, nama unmapped, gap, dan stasiun kosong pada hari terakhir.
- Menyediakan dashboard ringkasan akumulasi dan kejadian hujan.
- Menghitung indeks run:
  - **CDD terpanjang**: run terpanjang hari kering (rain = 0.0) dalam window.
  - **CWD terpanjang**: run terpanjang hari hujan (rain >= batas hari hujan) dalam window.
  - **CH maksimum dasarian ini**: maksimum hujan harian per stasiun dalam window.

Syarat file yang di upload:
- Format: CSV (bisa multi upload).
- Minimal memiliki kolom (nama harus persis):
  - `NAME`
  - `DATA TIMESTAMP`
  - `RAINFALL DAY MM`
- `DATA TIMESTAMP` harus bisa diparse (contoh: `2026-01-05 00:00:00`).
- `RAINFALL DAY MM` numerik atau kode:
  - `0` = tidak hujan
  - `8888` = trace
  - `9999` = missing/alat bermasalah
  - kosong/NaN = missing

Tutorial singkat:
1. Upload CSV vertikal start tanggal 1 setiap bulan.
2. Pilih Year, Month, Dasarian.
3. Atur threshold dashboard bila perlu.
4. Klik Run.
5. Lihat dashboard ringkasan, QC, tabel output, dan unduh output yang diperlukan.
"""
)

# ============================================================
# HARD CODE: HORIZONTAL_COLS + NAME_MAP
# ============================================================
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

# ============================================================
# Helpers
# ============================================================
def month_end_day(year: int, month: int) -> int:
    month_start = pd.Timestamp(year=year, month=month, day=1)
    month_end = (month_start + pd.offsets.MonthEnd(1)).normalize()
    return int(month_end.day)

def normalize_station_name(s: pd.Series) -> pd.Series:
    return s.astype(str).str.strip().str.replace(r"\s+", " ", regex=True)

def to_csv_bytes(df: pd.DataFrame) -> bytes:
    return df.to_csv(index=False).encode("utf-8")

def longest_run(series: pd.Series, condition_func):
    """
    Return (max_len, start_day, end_day) for the longest consecutive run
    where condition_func(value) is True.
    Missing (NaN) breaks the run.
    series index assumed to be day numbers (1..end_day).
    """
    max_len = 0
    max_start = None
    max_end = None

    cur_len = 0
    cur_start = None

    for day, val in series.items():
        if pd.isna(val):
            cur_len = 0
            cur_start = None
            continue

        if condition_func(val):
            if cur_len == 0:
                cur_start = int(day)
            cur_len += 1
            if cur_len > max_len:
                max_len = cur_len
                max_start = cur_start
                max_end = int(day)
        else:
            cur_len = 0
            cur_start = None

    return int(max_len), max_start, max_end

def compute_cdd_cwd(wide_num_out: pd.DataFrame, wet_threshold: float = 0.1):
    """
    Compute per-station:
    - Longest CDD: run of rain == 0.0
    - Longest CWD: run of rain >= wet_threshold
    - CH max within window and its day
    Missing breaks runs.
    """
    num = wide_num_out.drop(columns=["TGL"]).apply(pd.to_numeric, errors="coerce")
    num.index = wide_num_out["TGL"].values  # day index

    rows = []
    for station in num.columns:
        s = num[station]

        cdd_len, cdd_start, cdd_end = longest_run(s, lambda x: float(x) == 0.0)
        cwd_len, cwd_start, cwd_end = longest_run(s, lambda x: float(x) >= float(wet_threshold))

        if np.isfinite(s.to_numpy()).any():
            ch_max = float(np.nanmax(s.to_numpy()))
            ch_tgl = int(s.idxmax())
        else:
            ch_max = np.nan
            ch_tgl = np.nan

        rows.append({
            "station": station,
            "CDD_len": cdd_len,
            "CDD_start": cdd_start,
            "CDD_end": cdd_end,
            "CWD_len": cwd_len,
            "CWD_start": cwd_start,
            "CWD_end": cwd_end,
            "CH_max_mm": ch_max,
            "CH_max_TGL": ch_tgl,
        })

    df = pd.DataFrame(rows)
    return df

def build_outputs(df_month: pd.DataFrame, end_day: int):
    all_days = np.arange(1, end_day + 1)

    df_month = df_month.copy()
    df_month["NAME"] = normalize_station_name(df_month["NAME"])
    df_month["NAME_H"] = df_month["NAME"].replace(NAME_MAP)

    df_month["raw"] = pd.to_numeric(df_month["RAINFALL DAY MM"], errors="coerce")
    df_month["has_row"] = 1

    # NUMERIC mapping
    rain_num = df_month["raw"].copy()
    rain_num[df_month["raw"].isna()] = np.nan
    rain_num[df_month["raw"] == 9999] = np.nan
    rain_num[df_month["raw"] == 8888] = 0.1
    rain_num[df_month["raw"] == 0] = 0.0
    df_month["rain_num"] = rain_num

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

    # FORMAT BMKG
    wide_bmkg = pd.DataFrame("x", index=wide_raw.index, columns=wide_raw.columns)
    row_exists = present.notna()
    wide_bmkg = wide_bmkg.mask(row_exists & (wide_raw == 0), "-")
    wide_bmkg = wide_bmkg.mask(row_exists & (wide_raw == 8888), "0")
    is_pos_measured = row_exists & (wide_raw.notna()) & (wide_raw > 0) & (wide_raw != 8888) & (wide_raw != 9999)
    wide_bmkg = wide_bmkg.mask(is_pos_measured, wide_raw.astype(float))

    wide_bmkg_out = wide_bmkg.copy()
    wide_bmkg_out.insert(0, "TGL", wide_bmkg_out.index)

    wide_num_out = wide_num.copy()
    wide_num_out.insert(0, "TGL", wide_num_out.index)

    # QC summaries
    station_summary = pd.DataFrame({
        "station": HORIZONTAL_COLS,
        "days_present": present.notna().sum(axis=0).astype(int).values,
        "total_days": len(present.index),
    })
    station_summary["completeness_pct"] = (station_summary["days_present"] / station_summary["total_days"] * 100).round(1)

    day_summary = pd.DataFrame({
        "TGL": present.index,
        "stations_present": present.notna().sum(axis=1).astype(int).values,
        "total_stations": len(HORIZONTAL_COLS),
    })
    day_summary["completeness_pct"] = (day_summary["stations_present"] / day_summary["total_stations"] * 100).round(1)

    horizontal_set = set(HORIZONTAL_COLS)
    mapped_not_in_horizontal = sorted(set(df_month["NAME_H"].unique()) - horizontal_set)
    qc_unmapped = (
        df_month[df_month["NAME_H"].isin(mapped_not_in_horizontal)][["NAME", "NAME_H", "__source_file__"]]
        .drop_duplicates()
        .sort_values(["NAME_H", "NAME"])
    )

    last_present_day = present.notna().apply(lambda s: s[s].index.max() if s.any() else np.nan)
    gap_days_since_last = (end_day - last_present_day).where(~last_present_day.isna(), np.nan)
    empty_all_window = present.notna().sum(axis=0) == 0

    qc_gap = pd.DataFrame({
        "station": HORIZONTAL_COLS,
        "has_any_record_1_to_end_das": (~empty_all_window).astype(int).values,
        "last_record_day_in_window": last_present_day.reindex(HORIZONTAL_COLS).values,
        "empty_days_since_last_record": gap_days_since_last.reindex(HORIZONTAL_COLS).values
    })

    last_day_present = present.loc[end_day].notna()
    qc_empty_last_day = pd.DataFrame({
        "station": HORIZONTAL_COLS,
        "is_empty_on_last_day": (~last_day_present.reindex(HORIZONTAL_COLS).fillna(False)).astype(int).values,
        "last_record_day_in_window": last_present_day.reindex(HORIZONTAL_COLS).values
    })

    qc_empty_last_day["empty_days_up_to_last_day"] = np.where(
        qc_empty_last_day["last_record_day_in_window"].isna(),
        float(end_day),
        float(end_day) - qc_empty_last_day["last_record_day_in_window"].astype(float)
    )
    qc_empty_last_day = qc_empty_last_day[qc_empty_last_day["is_empty_on_last_day"] == 1].copy()
    qc_empty_last_day = qc_empty_last_day.sort_values(["empty_days_up_to_last_day", "station"], ascending=[False, True])

    assert list(wide_bmkg_out.columns[1:]) == HORIZONTAL_COLS, "Urutan kolom output tidak sesuai HORIZONTAL_COLS"

    return {
        "wide_bmkg_out": wide_bmkg_out,
        "wide_num_out": wide_num_out,
        "qc_station": station_summary.sort_values(["completeness_pct", "station"], ascending=[True, True]),
        "qc_day": day_summary,
        "qc_unmapped": qc_unmapped,
        "qc_gap": qc_gap,
        "qc_empty_last_day": qc_empty_last_day,
    }

def build_dashboard(wide_num_out: pd.DataFrame, rainy_threshold: float, heavy_threshold: float):
    num = wide_num_out.drop(columns=["TGL"]).apply(pd.to_numeric, errors="coerce")

    # Station aggregates
    station_total = num.sum(axis=0, skipna=True)
    station_valid_days = num.notna().sum(axis=0)
    station_rainy_days = (num >= rainy_threshold).sum(axis=0, skipna=True)
    station_heavy_days = (num >= heavy_threshold).sum(axis=0, skipna=True)
    station_max = num.max(axis=0, skipna=True)
    station_tgl_max = num.idxmax(axis=0, skipna=True).astype("Int64")  # idx is row number, not TGL

    # Fix tgl_max with actual day numbers
    num_idx = wide_num_out["TGL"].values
    # idxmax returns positional index (0..n-1) when index is default, so ensure index = TGL
    num2 = num.copy()
    num2.index = num_idx
    station_tgl_max = num2.idxmax(axis=0, skipna=True).astype("Int64")

    station_dash = pd.DataFrame({
        "station": num.columns,
        "total_mm": station_total.values,
        "valid_days": station_valid_days.values,
        "rainy_days_ge_thr": station_rainy_days.values,
        "heavy_days_ge_thr": station_heavy_days.values,
        "max_mm": station_max.values,
        "tgl_max": station_tgl_max.values,
    }).sort_values(["total_mm", "station"], ascending=[False, True])

    # Day aggregates
    day_total = num.sum(axis=1, skipna=True)
    day_mean = num.mean(axis=1, skipna=True)
    day_valid_stations = num.notna().sum(axis=1)
    day_rainy_stations = (num >= rainy_threshold).sum(axis=1, skipna=True)
    day_heavy_stations = (num >= heavy_threshold).sum(axis=1, skipna=True)

    day_dash = pd.DataFrame({
        "TGL": wide_num_out["TGL"].values,
        "total_mm_all_stations": day_total.values,
        "mean_mm_across_stations": day_mean.values,
        "stations_valid": day_valid_stations.values,
        "stations_rainy_ge_thr": day_rainy_stations.values,
        "stations_heavy_ge_thr": day_heavy_stations.values,
    }).sort_values("TGL")

    # Global highlights
    total_mm_all_cells = float(np.nansum(num.to_numpy()))
    total_valid_cells = int(np.isfinite(num.to_numpy()).sum())
    total_cells = int(num.size)
    coverage_pct_numeric = round(total_valid_cells / total_cells * 100, 2)

    wettest_station = station_dash.iloc[0][["station", "total_mm"]].to_dict() if len(station_dash) else {}
    wettest_day_idx = day_dash["total_mm_all_stations"].idxmax() if len(day_dash) else None
    wettest_day = day_dash.loc[wettest_day_idx, ["TGL", "total_mm_all_stations"]].to_dict() if wettest_day_idx is not None else {}

    return station_dash, day_dash, {
        "total_mm_all_cells": total_mm_all_cells,
        "coverage_pct_numeric": coverage_pct_numeric,
        "wettest_station": wettest_station,
        "wettest_day": wettest_day
    }

# ============================================================
# Sidebar controls
# ============================================================
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
        format_func=lambda x: "Das 1 (1-10)" if x == "1" else ("Das 2 (1-20)" if x == "2" else "Das 3 (Full month)" ),
        index=0
    )

    st.divider()
    st.subheader("Dashboard thresholds")
    rainy_thr = st.number_input("Batas hari hujan untuk CWD dan hitungan hari hujan (mm)", min_value=0.0, value=0.1, step=0.1)
    heavy_thr = st.number_input("Batas hujan lebat (mm)", min_value=0.0, value=20.0, step=1.0)

    st.divider()
    run = st.button("Run transpose + QC", type="primary", use_container_width=True)
    reset = st.button("Reset hasil", use_container_width=True)

# ============================================================
# Session state init
# ============================================================
if "outputs" not in st.session_state:
    st.session_state["outputs"] = None
if "meta" not in st.session_state:
    st.session_state["meta"] = None

if reset:
    st.session_state["outputs"] = None
    st.session_state["meta"] = None
    st.rerun()

if not up:
    st.info("Upload file, pilih Year, Month, Dasarian, lalu klik Run transpose + QC.")
    st.stop()

# ============================================================
# Process when Run clicked
# ============================================================
if run:
    YEAR = int(year)
    MM = str(month)
    MONTH_STR = f"{YEAR}-{MM}"
    das_n = int(dasarian)

    last_day = month_end_day(YEAR, int(MM))
    end_day = 10 if das_n == 1 else (20 if das_n == 2 else last_day)

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

    outputs = build_outputs(df_month, end_day)

    st.session_state["outputs"] = outputs
    st.session_state["meta"] = {
        "MONTH_STR": MONTH_STR,
        "das_n": das_n,
        "end_day": end_day,
        "YEAR": YEAR,
        "MM": MM,
    }

if st.session_state["outputs"] is None:
    st.warning("Klik Run transpose + QC untuk memproses data.")
    st.stop()

# ============================================================
# Use stored outputs
# ============================================================
outputs = st.session_state["outputs"]
meta = st.session_state["meta"]

MONTH_STR = meta["MONTH_STR"]
das_n = meta["das_n"]
end_day = meta["end_day"]

wide_bmkg_out = outputs["wide_bmkg_out"]
wide_num_out = outputs["wide_num_out"]
qc_station = outputs["qc_station"]
qc_day = outputs["qc_day"]
qc_unmapped = outputs["qc_unmapped"]
qc_gap = outputs["qc_gap"]
qc_empty_last_day = outputs["qc_empty_last_day"]

# ============================================================
# Dashboard summaries
# ============================================================
station_dash, day_dash, hi = build_dashboard(wide_num_out, rainy_thr, heavy_thr)
cdd_cwd_df = compute_cdd_cwd(wide_num_out, wet_threshold=rainy_thr)

top_cdd = cdd_cwd_df.sort_values(["CDD_len", "station"], ascending=[False, True]).head(15)
top_cwd = cdd_cwd_df.sort_values(["CWD_len", "station"], ascending=[False, True]).head(15)

# Global bests
best_cdd = cdd_cwd_df.loc[cdd_cwd_df["CDD_len"].idxmax()] if len(cdd_cwd_df) else None
best_cwd = cdd_cwd_df.loc[cdd_cwd_df["CWD_len"].idxmax()] if len(cdd_cwd_df) else None
best_ch = cdd_cwd_df.loc[cdd_cwd_df["CH_max_mm"].idxmax()] if cdd_cwd_df["CH_max_mm"].notna().any() else None

# ============================================================
# Dashboard section
# ============================================================
st.header("Dashboard Ringkasan")

m1, m2, m3, m4 = st.columns(4)
m1.metric("Total hujan (mm) semua stasiun", f"{hi['total_mm_all_cells']:.1f}")
m2.metric("Coverage numeric (%)", f"{hi['coverage_pct_numeric']:.2f}")
if hi["wettest_station"]:
    m3.metric("Stasiun terbasah (akumulasi)", f"{hi['wettest_station']['station']}", f"{hi['wettest_station']['total_mm']:.1f} mm")
else:
    m3.metric("Stasiun terbasah (akumulasi)", "-")
if hi["wettest_day"]:
    m4.metric("Hari terbasah (akumulasi)", f"TGL {int(hi['wettest_day']['TGL'])}", f"{hi['wettest_day']['total_mm_all_stations']:.1f} mm")
else:
    m4.metric("Hari terbasah (akumulasi)", "-")

st.subheader("Indeks Dasarian: CDD / CWD terpanjang + CH maksimum (dasarian ini)")
d1, d2, d3 = st.columns(3)

if best_cdd is not None:
    d1.metric(
        "CDD terpanjang (stasiun terbaik)",
        f"{best_cdd['station']}",
        f"{int(best_cdd['CDD_len'])} hari (TGL {best_cdd['CDD_start']}–{best_cdd['CDD_end']})"
    )
else:
    d1.metric("CDD terpanjang (stasiun terbaik)", "-")

if best_cwd is not None:
    d2.metric(
        "CWD terpanjang (stasiun terbaik)",
        f"{best_cwd['station']}",
        f"{int(best_cwd['CWD_len'])} hari (TGL {best_cwd['CWD_start']}–{best_cwd['CWD_end']})"
    )
else:
    d2.metric("CWD terpanjang (stasiun terbaik)", "-")

if best_ch is not None and pd.notna(best_ch["CH_max_mm"]):
    d3.metric(
        "CH maksimum (dasarian ini)",
        f"{best_ch['station']}",
        f"{best_ch['CH_max_mm']:.1f} mm (TGL {int(best_ch['CH_max_TGL'])})"
    )
else:
    d3.metric("CH maksimum (dasarian ini)", "-")

cL, cR = st.columns([1.1, 0.9])

with cL:
    st.subheader("Total hujan harian (semua stasiun)")
    chart_df = day_dash[["TGL", "total_mm_all_stations"]].set_index("TGL")
    st.line_chart(chart_df)

    st.subheader("Jumlah stasiun hujan per hari")
    chart2_df = day_dash[["TGL", "stations_rainy_ge_thr"]].set_index("TGL")
    st.line_chart(chart2_df)

with cR:
    st.subheader("Top 15 stasiun berdasarkan akumulasi")
    st.dataframe(station_dash.head(15), use_container_width=True)

    st.subheader("Top 10 stasiun hari hujan")
    top_rainy = station_dash.sort_values(["rainy_days_ge_thr", "station"], ascending=[False, True]).head(10)
    st.dataframe(top_rainy[["station", "rainy_days_ge_thr", "total_mm", "max_mm", "tgl_max"]], use_container_width=True)

st.subheader("Top 15 CDD dan CWD terpanjang")
cc1, cc2 = st.columns(2)
with cc1:
    st.markdown("**Top 15 CDD terpanjang (per stasiun)**")
    st.dataframe(top_cdd[["station","CDD_len","CDD_start","CDD_end","CH_max_mm","CH_max_TGL"]], use_container_width=True)
with cc2:
    st.markdown("**Top 15 CWD terpanjang (per stasiun)**")
    st.dataframe(top_cwd[["station","CWD_len","CWD_start","CWD_end","CH_max_mm","CH_max_TGL"]], use_container_width=True)

st.divider()

# ============================================================
# QC section
# ============================================================
st.header("QC")

st.subheader("Parameter")
st.write(f"Periode: **{MONTH_STR}**")
st.write(f"Dasarian: **{das_n}** | Rentang tanggal: **1 s.d. {end_day}**")
st.write(f"Total stasiun (kolom output): **{len(HORIZONTAL_COLS)}**")

st.subheader("Ringkasan QC (kelengkapan record, berbasis FORMAT BMKG)")
total_cells_bmkg = end_day * len(HORIZONTAL_COLS)
cells_with_row = int((wide_bmkg_out.drop(columns=["TGL"]) != "x").to_numpy().sum())
coverage_pct = round(cells_with_row / total_cells_bmkg * 100, 2)

q1, q2, q3 = st.columns(3)
q1.metric("Coverage record (%)", f"{coverage_pct}%")
q2.metric("Cells with record", f"{cells_with_row}/{total_cells_bmkg}")
q3.metric("Stations", f"{len(HORIZONTAL_COLS)}")

with st.expander("Stasiun kosong total pada jendela dasarian"):
    empty_all_stations = qc_gap[qc_gap["has_any_record_1_to_end_das"] == 0]["station"].tolist()
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

st.divider()

# ============================================================
# Tables
# ============================================================
st.header("Tabel Output")

view_choice = st.radio(
    "Pilih tampilan",
    options=["FORMAT BMKG (x / - / 0 / angka)", "NUMERIC (NaN / 0.1 / angka)"],
    index=0,
    horizontal=True
)

if view_choice.startswith("FORMAT BMKG"):
    st.dataframe(wide_bmkg_out, use_container_width=True, height=420)
else:
    st.dataframe(wide_num_out, use_container_width=True, height=420)

st.divider()

# ============================================================
# Downloads
# ============================================================
st.header("Download")

summary_station_name = f"SUMMARY_station_rain_{MONTH_STR}_das{das_n}.csv"
summary_day_name = f"SUMMARY_day_rain_{MONTH_STR}_das{das_n}.csv"
summary_cdd_cwd_name = f"SUMMARY_CDD_CWD_CHmax_{MONTH_STR}_das{das_n}.csv"

download_choice = st.selectbox(
    "Pilih file yang ingin di-download",
    [
        f"rain_horizontal_{MONTH_STR}_das{das_n}_format_bmkg.csv",
        f"rain_horizontal_{MONTH_STR}_das{das_n}_numeric.csv",
        f"QC_station_completeness_{MONTH_STR}_das{das_n}.csv",
        f"QC_day_completeness_{MONTH_STR}_das{das_n}.csv",
        f"QC_unmapped_names_{MONTH_STR}_das{das_n}.csv",
        f"QC_station_empty_gap_{MONTH_STR}_das{das_n}.csv",
        f"QC_empty_last_day_{MONTH_STR}_das{das_n}.csv",
        summary_station_name,
        summary_day_name,
        summary_cdd_cwd_name,
    ],
    index=0
)

download_map = {
    f"rain_horizontal_{MONTH_STR}_das{das_n}_format_bmkg.csv": wide_bmkg_out,
    f"rain_horizontal_{MONTH_STR}_das{das_n}_numeric.csv": wide_num_out,
    f"QC_station_completeness_{MONTH_STR}_das{das_n}.csv": qc_station,
    f"QC_day_completeness_{MONTH_STR}_das{das_n}.csv": qc_day,
    f"QC_unmapped_names_{MONTH_STR}_das{das_n}.csv": qc_unmapped,
    f"QC_station_empty_gap_{MONTH_STR}_das{das_n}.csv": qc_gap,
    f"QC_empty_last_day_{MONTH_STR}_das{das_n}.csv": qc_empty_last_day,
    summary_station_name: station_dash,
    summary_day_name: day_dash,
    summary_cdd_cwd_name: cdd_cwd_df,
}

df_dl = download_map[download_choice]
st.download_button(
    label=f"Download: {download_choice}",
    data=to_csv_bytes(df_dl),
    file_name=download_choice,
    mime="text/csv",
    use_container_width=True
)



