import streamlit as st
import pandas as pd
import numpy as np
from datetime import date
import pydeck as pdk

# ============================================================
# Page
# ============================================================
st.set_page_config(
    page_title="Pos Hujan Dasarian: Rekap, Indeks, QC, dan Peta",
    layout="wide"
)

st.title("Pos Hujan Dasarian: Rekap, Indeks, QC, dan Peta")
st.caption(
    "Transpose vertikal → horizontal (urut stasiun fix) + FORMAT BMKG + NUMERIC + QC + Ringkasan + "
    "CDD/CWD/CHmax + Peta (lat lon dari coords.csv di repo)"
)

# ============================================================
# Navigation (single-file multi-view; controllable like tabs)
# ============================================================
PAGES = ["Input", "Hasil", "QC", "Tabel", "Grafik", "Peta", "Download"]


if "page" not in st.session_state:
    st.session_state["page"] = "Input"

def goto(page: str):
    if page in PAGES:
        st.session_state["page"] = page

def to_csv_bytes(df: pd.DataFrame) -> bytes:
    return df.to_csv(index=False).encode("utf-8")

# ============================================================
# Panduan (collapsible, default closed)
# ============================================================
with st.expander("Panduan dan syarat file (klik untuk buka)", expanded=False):
    st.markdown(
        """
## Transposer Pos Hujan (Vertikal → Horizontal) + QC Dasarian + Peta

Aplikasi ini digunakan untuk mengubah data curah hujan harian format **vertikal** (baris per stasiun per tanggal)
menjadi format **horizontal** (1 baris per tanggal, kolom per stasiun) dengan urutan kolom **harus persis** mengikuti header yang sudah ditetapkan.

### Input Curah Hujan
File CSV vertikal yang minimal memiliki kolom:
- `NAME`
- `DATA TIMESTAMP`
- `RAINFALL DAY MM`

### Koordinat untuk Tab Peta (dibaca dari repo)
Aplikasi otomatis membaca **coords.csv** dari root repo (Opsi A) dengan kolom:
- `POS HUJAN ID`
- `NAME`
- `CURRENT LATITUDE`
- `CURRENT LONGITUDE`
- `CURRENT ELEVATION M`

### Pilihan di aplikasi
- **Year**: Tahun data (misal 2026)
- **Month**: Bulan data (01–12)
- **Dasarian**:
  - **Das 1**: tanggal 1–10
  - **Das 2**: tanggal 1–20
  - **Das 3**: satu bulan penuh

### Aturan nilai (FORMAT BMKG)
- `raw = 0` → tampil `-` (tidak hujan teramati)
- `raw = 8888` → tampil `0` (hujan sangat kecil/trace)
- `raw = 9999` → tampil `x` (tidak ada data/alat bermasalah)
- `raw kosong/NaN` → tampil `x`
- **Tidak ada baris** untuk stasiun pada tanggal tersebut → tampil `x`

### Aturan nilai (NUMERIC untuk perhitungan)
- `raw = 0` → `0.0`
- `raw = 8888` → `0.1` (trace dianggap 0.1 mm)
- `raw = 9999` → `NaN`
- `raw kosong/NaN` → `NaN`
- **Tidak ada baris** → `NaN`

### Output utama
- Tabel **FORMAT BMKG**
- Tabel **NUMERIC**
- QC kelengkapan (per stasiun dan per tanggal)
- QC unmapped names (indikasi masalah penamaan)
- QC stasiun kosong total dan kosong di hari terakhir
- Ringkasan akumulasi
- Indeks **CDD/CWD terpanjang** serta **CH maksimum** pada window dasarian
- Peta titik (lat lon) untuk visual QC, akumulasi, completeness, CDD/CWD, CH max

### Tutorial singkat
1. Upload CSV vertikal (boleh lebih dari 1 file).
2. Pilih **Year**, **Month**, **Dasarian**.
3. Atur threshold bila perlu.
4. Klik **Run**.
5. Gunakan menu “Input / Hasil / QC / Tabel / Peta / Download” untuk berpindah tampilan tanpa scroll.
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
    "Sape 2": "Sape2",
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

def load_coords_from_repo(path: str = "coords.csv") -> pd.DataFrame:
    """
    Membaca coords.csv dari root repo (Opsi A).
    Wajib punya kolom:
    POS HUJAN ID, NAME, CURRENT LATITUDE, CURRENT LONGITUDE, CURRENT ELEVATION M
    """
    try:
        return pd.read_csv(path)
    except Exception as e:
        raise RuntimeError(
            f"Gagal membaca '{path}'. Pastikan file ada di root repo dan formatnya CSV. Detail: {e}"
        )

def prepare_station_coordinates(coord_raw: pd.DataFrame) -> pd.DataFrame:
    """
    coord_raw wajib punya kolom Opsi A:
    - POS HUJAN ID
    - NAME
    - CURRENT LATITUDE
    - CURRENT LONGITUDE
    - CURRENT ELEVATION M
    """
    c = coord_raw.copy()

    # validate presence
    req = ["POS HUJAN ID", "NAME", "CURRENT LATITUDE", "CURRENT LONGITUDE", "CURRENT ELEVATION M"]
    missing = [x for x in req if x not in c.columns]
    if missing:
        raise ValueError(f"Kolom wajib pada coords.csv tidak ditemukan: {missing}")

    # rename kolom agar nyaman
    c = c.rename(columns={
        "POS HUJAN ID": "pos_id",
        "NAME": "name_raw",
        "CURRENT LATITUDE": "lat_raw",
        "CURRENT LONGITUDE": "lon_raw",
        "CURRENT ELEVATION M": "elev_m",
    })

    # normalisasi nama + mapping mengikuti NAME_MAP
    c["name_raw"] = normalize_station_name(c["name_raw"])
    c["station"] = c["name_raw"].replace(NAME_MAP)

    # parse numeric
    c["lat"] = pd.to_numeric(c["lat_raw"], errors="coerce")
    c["lon"] = pd.to_numeric(c["lon_raw"], errors="coerce")
    c["elev_m"] = pd.to_numeric(c["elev_m"], errors="coerce")

    # QC koordinat
    c["qc_coord_ok"] = c["lat"].notna() & c["lon"].notna()
    c["qc_in_bounds_ntb"] = c["lat"].between(-11.5, -7.0) & c["lon"].between(115.0, 119.5)

    dup_key = c[["lat", "lon"]].round(5).astype(str).agg(",".join, axis=1)
    c["qc_dup_latlon"] = dup_key.duplicated(keep=False) & c["qc_coord_ok"]

    # left join ke daftar resmi HORIZONTAL_COLS
    base = pd.DataFrame({"station": HORIZONTAL_COLS})
    out = base.merge(
        c[["station", "pos_id", "lat", "lon", "elev_m", "name_raw", "qc_coord_ok", "qc_in_bounds_ntb", "qc_dup_latlon"]],
        on="station",
        how="left"
    )

    out["qc_flag"] = np.where(
        out["lat"].notna() & out["lon"].notna(),
        "OK",
        "MISSING_COORD"
    )
    out.loc[(out["qc_flag"] == "OK") & (out["qc_in_bounds_ntb"] == False), "qc_flag"] = "OUT_OF_BOUNDS"
    out.loc[(out["qc_flag"] == "OK") & (out["qc_dup_latlon"] == True), "qc_flag"] = "DUP_LATLON"

    return out

def longest_run(series: pd.Series, condition_func):
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
    num = wide_num_out.drop(columns=["TGL"]).apply(pd.to_numeric, errors="coerce")
    num.index = wide_num_out["TGL"].values

    last_day = int(wide_num_out["TGL"].max())

    rows = []
    for station in num.columns:
        s = num[station]

        # longest
        cdd_len, cdd_start, cdd_end = longest_run(s, lambda x: float(x) == 0.0)
        cwd_len, cwd_start, cwd_end = longest_run(s, lambda x: float(x) >= float(wet_threshold))

        # current (ending at last_day)
        cdd_cur_len, cdd_cur_start, cdd_cur_end = current_run_ending_at_last(
            s, lambda x: float(x) == 0.0, last_day
        )
        cwd_cur_len, cwd_cur_start, cwd_cur_end = current_run_ending_at_last(
            s, lambda x: float(x) >= float(wet_threshold), last_day
        )

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

            # NEW: current condition at last day
            "CDD_cur_len": cdd_cur_len,
            "CDD_cur_start": cdd_cur_start,
            "CDD_cur_end": cdd_cur_end,

            "CWD_cur_len": cwd_cur_len,
            "CWD_cur_start": cwd_cur_start,
            "CWD_cur_end": cwd_cur_end,

            "CH_max_mm": ch_max,
            "CH_max_TGL": ch_tgl,
        })

    return pd.DataFrame(rows)

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
    qc_station = station_summary.sort_values(["completeness_pct", "station"], ascending=[True, True])

    day_summary = pd.DataFrame({
        "TGL": present.index,
        "stations_present": present.notna().sum(axis=1).astype(int).values,
        "total_stations": len(HORIZONTAL_COLS),
    })
    day_summary["completeness_pct"] = (day_summary["stations_present"] / day_summary["total_stations"] * 100).round(1)
    qc_day = day_summary

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
        "qc_station": qc_station,
        "qc_day": qc_day,
        "qc_unmapped": qc_unmapped,
        "qc_gap": qc_gap,
        "qc_empty_last_day": qc_empty_last_day,
    }

def build_dashboard(wide_num_out: pd.DataFrame, rainy_threshold: float, heavy_threshold: float):
    num = wide_num_out.drop(columns=["TGL"]).apply(pd.to_numeric, errors="coerce")
    num2 = num.copy()
    num2.index = wide_num_out["TGL"].values

    station_total = num.sum(axis=0, skipna=True)
    station_valid_days = num.notna().sum(axis=0)
    station_rainy_days = (num >= rainy_threshold).sum(axis=0, skipna=True)
    station_heavy_days = (num >= heavy_threshold).sum(axis=0, skipna=True)
    station_max = num.max(axis=0, skipna=True)
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

def current_run_ending_at_last(series: pd.Series, condition_func, last_day: int):
    """
    Hitung panjang run yang sedang berlangsung dan HARUS berakhir di last_day.
    - series: indexed by day number (int)
    - NaN memutus run
    Return: (len_run, start_day, end_day) or (0, None, None)
    """
    if last_day not in series.index:
        return 0, None, None

    v_last = series.loc[last_day]
    if pd.isna(v_last) or (not condition_func(v_last)):
        return 0, None, None

    cur_len = 0
    cur_start = last_day
    d = last_day
    while d in series.index:
        v = series.loc[d]
        if pd.isna(v) or (not condition_func(v)):
            break
        cur_len += 1
        cur_start = d
        d -= 1

    return int(cur_len), int(cur_start), int(last_day)


# ============================================================
# Session state init
# ============================================================
if "outputs" not in st.session_state:
    st.session_state["outputs"] = None
if "meta" not in st.session_state:
    st.session_state["meta"] = None
if "derived" not in st.session_state:
    st.session_state["derived"] = None
if "coords_final" not in st.session_state:
    coords_repo = load_coords_from_repo("coords.csv")
    st.session_state["coords_final"] = prepare_station_coordinates(coords_repo)

def clear_results():
    st.session_state["outputs"] = None
    st.session_state["meta"] = None
    st.session_state["derived"] = None
    goto("Input")

def require_results():
    if st.session_state.get("outputs") is None or st.session_state.get("meta") is None or st.session_state.get("derived") is None:
        st.info("Belum ada hasil. Silakan proses data di halaman Input.")
        st.stop()
def legend_qc_block():
    # Warna harus konsisten dengan qc_to_rgb
    items = [
        ("OK", (30, 160, 60)),
        ("MISSING_COORD", (180, 180, 180)),
        ("OUT_OF_BOUNDS", (255, 140, 0)),
        ("DUP_LATLON", (220, 60, 60)),
    ]
    st.markdown("**Legend (QC)**")
    for label, (r, g, b) in items:
        st.markdown(
            f"""
<div style="display:flex;align-items:center;margin-bottom:6px;">
  <div style="width:14px;height:14px;background:rgb({r},{g},{b});border:1px solid #999;margin-right:8px;"></div>
  <div style="font-size:13px;">{label}</div>
</div>
""",
            unsafe_allow_html=True
        )

def legend_continuous_block(series: pd.Series, title: str):
    s = pd.to_numeric(series, errors="coerce")
    s = s[np.isfinite(s)]
    st.markdown(f"**Legend ({title})**")

    if s.empty:
        st.caption("Tidak ada nilai untuk dibuat legend.")
        return

    q0 = float(np.nanmin(s))
    q25 = float(np.nanpercentile(s, 25))
    q50 = float(np.nanpercentile(s, 50))
    q75 = float(np.nanpercentile(s, 75))
    q100 = float(np.nanmax(s))

    # Bar sederhana (low -> high)
    st.markdown(
        """
<div style="height:12px;border-radius:6px;border:1px solid #bbb;
background: linear-gradient(90deg, rgb(60,80,220), rgb(240,80,40));">
</div>
""",
        unsafe_allow_html=True
    )

    st.write(
        pd.DataFrame(
            {
                "min": [q0],
                "p25": [q25],
                "median": [q50],
                "p75": [q75],
                "max": [q100],
            }
        )
    )


# ============================================================
# Top navigation bar
# ============================================================
nav_cols = st.columns([1, 1, 1, 1, 1, 1, 1, 2])

with nav_cols[0]:
    if st.button("Input", use_container_width=True):
        goto("Input"); st.rerun()
with nav_cols[1]:
    if st.button("Hasil", use_container_width=True):
        goto("Hasil"); st.rerun()
with nav_cols[2]:
    if st.button("QC", use_container_width=True):
        goto("QC"); st.rerun()
with nav_cols[3]:
    if st.button("Tabel", use_container_width=True):
        goto("Tabel"); st.rerun()
with nav_cols[4]:
    if st.button("Grafik", use_container_width=True):
        goto("Grafik"); st.rerun()
with nav_cols[5]:
    if st.button("Peta", use_container_width=True):
        goto("Peta"); st.rerun()
with nav_cols[6]:
    if st.button("Download", use_container_width=True):
        goto("Download"); st.rerun()
with nav_cols[7]:
    st.write(f"**Halaman aktif:** {st.session_state['page']}")

st.divider()

# ============================================================
# PAGE: Input
# ============================================================
if st.session_state["page"] == "Input":
    st.subheader("Input data")

    up_rain = st.file_uploader(
        "Upload CSV vertikal (curah hujan)",
        type=["csv"],
        accept_multiple_files=True,
        key="uploader_rain"
    )

    cA, cB, cC = st.columns([1, 1, 1.2])
    today = date.today()
    with cA:
        year = st.number_input("Year", min_value=2000, max_value=2100, value=int(today.year), step=1)
    with cB:
        month = st.selectbox("Month", options=[f"{i:02d}" for i in range(1, 13)], index=int(today.month) - 1)
    with cC:
        dasarian = st.radio(
            "Dasarian",
            options=["1", "2", "3"],
            format_func=lambda x: "Das 1 (1-10)" if x == "1" else ("Das 2 (1-20)" if x == "2" else "Das 3 (Full month)"),
            index=0,
            horizontal=True
        )

    st.markdown("**Threshold ringkasan**")
    t1, t2 = st.columns(2)
    with t1:
        rainy_thr = st.number_input("Batas hari hujan untuk CWD dan hitungan hari hujan (mm)", min_value=0.0, value=0.1, step=0.1)
    with t2:
        heavy_thr = st.number_input("Batas hujan lebat (mm)", min_value=0.0, value=20.0, step=1.0)

    b1, b2, b3 = st.columns([1, 1, 2])
    with b1:
        run = st.button("Run", type="primary", use_container_width=True)
    with b2:
        reset = st.button("Reset hasil", use_container_width=True)
    with b3:
        st.caption("Tip: setelah Run sukses, app otomatis pindah ke halaman Hasil.")

    if reset:
        clear_results()
        st.success("Hasil direset.")
        st.rerun()

    with st.expander("Status koordinat yang dipakai (coords.csv)", expanded=False):
        coords_final = st.session_state["coords_final"].copy()
        st.write("Default koordinat dibaca dari file **coords.csv** di root repo.")
        st.write(f"Jumlah stasiun pada HORIZONTAL_COLS: **{len(HORIZONTAL_COLS)}**")
        st.write(f"Koordinat OK: **{int((coords_final['qc_flag'] == 'OK').sum())}**")
        st.write(f"Tanpa koordinat: **{int((coords_final['qc_flag'] == 'MISSING_COORD').sum())}**")
        st.write(f"Out of bounds: **{int((coords_final['qc_flag'] == 'OUT_OF_BOUNDS').sum())}**")
        st.write(f"Duplikat lat lon: **{int((coords_final['qc_flag'] == 'DUP_LATLON').sum())}**")
        st.dataframe(coords_final.head(60), use_container_width=True, height=420)

    if run:
        if not up_rain:
            st.error("Upload file CSV vertikal curah hujan terlebih dahulu.")
            st.stop()

        YEAR = int(year)
        MM = str(month)
        MONTH_STR = f"{YEAR}-{MM}"
        das_n = int(dasarian)

        last_day = month_end_day(YEAR, int(MM))
        end_day = 10 if das_n == 1 else (20 if das_n == 2 else last_day)

        dfs = []
        bad_files = []
        for f in up_rain:
            try:
                tmp = pd.read_csv(f)
                tmp["__source_file__"] = f.name
                dfs.append(tmp)
            except Exception:
                bad_files.append(f.name)

        if bad_files:
            st.warning(f"File gagal dibaca dan diabaikan: {bad_files}")
        if not dfs:
            st.error("Tidak ada file curah hujan valid untuk diproses.")
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
        station_dash, day_dash, hi = build_dashboard(outputs["wide_num_out"], rainy_thr, heavy_thr)
        cdd_cwd_df = compute_cdd_cwd(outputs["wide_num_out"], wet_threshold=rainy_thr)

        top_cdd = cdd_cwd_df.sort_values(["CDD_len", "station"], ascending=[False, True]).head(15)
        top_cwd = cdd_cwd_df.sort_values(["CWD_len", "station"], ascending=[False, True]).head(15)

        best_cdd = cdd_cwd_df.loc[cdd_cwd_df["CDD_len"].idxmax()] if len(cdd_cwd_df) else None
        best_cwd = cdd_cwd_df.loc[cdd_cwd_df["CWD_len"].idxmax()] if len(cdd_cwd_df) else None
        best_ch = cdd_cwd_df.loc[cdd_cwd_df["CH_max_mm"].idxmax()] if cdd_cwd_df["CH_max_mm"].notna().any() else None

        st.session_state["outputs"] = outputs
        st.session_state["meta"] = {
            "MONTH_STR": MONTH_STR,
            "das_n": das_n,
            "end_day": end_day,
            "YEAR": YEAR,
            "MM": MM,
            "rainy_thr": float(rainy_thr),
            "heavy_thr": float(heavy_thr),
        }
        st.session_state["derived"] = {
            "station_dash": station_dash,
            "day_dash": day_dash,
            "hi": hi,
            "cdd_cwd_df": cdd_cwd_df,
            "top_cdd": top_cdd,
            "top_cwd": top_cwd,
            "best_cdd": best_cdd,
            "best_cwd": best_cwd,
            "best_ch": best_ch,
        }

        st.success("Selesai diproses. Membuka halaman Hasil.")
        goto("Hasil")
        st.rerun()

# ============================================================
# PAGE: Hasil
# ============================================================
elif st.session_state["page"] == "Hasil":
    require_results()

    meta = st.session_state["meta"]
    derived = st.session_state["derived"]

    MONTH_STR = meta["MONTH_STR"]
    das_n = meta["das_n"]
    end_day = meta["end_day"]
    rainy_thr = meta["rainy_thr"]
    heavy_thr = meta["heavy_thr"]

    station_dash = derived["station_dash"]
    day_dash = derived["day_dash"]
    hi = derived["hi"]
    cdd_cwd_df = derived["cdd_cwd_df"]
    top_cdd = derived["top_cdd"]
    top_cwd = derived["top_cwd"]
    best_cdd = derived["best_cdd"]
    best_cwd = derived["best_cwd"]
    best_ch = derived["best_ch"]

    st.subheader("Parameter")
    st.write(f"Periode: **{MONTH_STR}**")
    st.write(f"Dasarian: **{das_n}** | Rentang tanggal: **1 s.d. {end_day}**")
    st.write(f"Threshold hari hujan (CWD): **{rainy_thr} mm** | Threshold lebat: **{heavy_thr} mm**")

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

    st.markdown("---")
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
        st.line_chart(day_dash[["TGL", "total_mm_all_stations"]].set_index("TGL"))

        st.subheader("Jumlah stasiun hujan per hari")
        st.line_chart(day_dash[["TGL", "stations_rainy_ge_thr"]].set_index("TGL"))

    with cR:
        st.subheader("Top 15 stasiun berdasarkan akumulasi")
        st.dataframe(station_dash.head(15), use_container_width=True, height=520)

    st.markdown("---")
    cc1, cc2 = st.columns(2)
    with cc1:
        st.subheader("Top 15 CDD terpanjang (per stasiun)")
        st.dataframe(top_cdd[["station","CDD_len","CDD_start","CDD_end","CH_max_mm","CH_max_TGL"]], use_container_width=True, height=520)
    with cc2:
        st.subheader("Top 15 CWD terpanjang (per stasiun)")
        st.dataframe(top_cwd[["station","CWD_len","CWD_start","CWD_end","CH_max_mm","CH_max_TGL"]], use_container_width=True, height=520)

    with st.expander("Tabel lengkap CDD/CWD/CHmax (semua stasiun)"):
        st.dataframe(cdd_cwd_df, use_container_width=True, height=520)

    st.markdown("---")
    st.subheader("Kondisi terkini (run yang sedang berlangsung di hari terakhir window)")
    
    last_day = end_day  # same for your window
    tmp_cur = cdd_cwd_df.copy()
    
    # show only stations where current run exists
    tmp_cdd_cur = tmp_cur[tmp_cur["CDD_cur_len"] > 0].sort_values(["CDD_cur_len","station"], ascending=[False, True]).head(15)
    tmp_cwd_cur = tmp_cur[tmp_cur["CWD_cur_len"] > 0].sort_values(["CWD_cur_len","station"], ascending=[False, True]).head(15)
    
    x1, x2 = st.columns(2)
    with x1:
        st.caption(f"Top 15 CDD current (ending TGL {last_day})")
        st.dataframe(tmp_cdd_cur[["station","CDD_cur_len","CDD_cur_start","CDD_cur_end"]], use_container_width=True, height=420)
    with x2:
        st.caption(f"Top 15 CWD current (ending TGL {last_day})")
        st.dataframe(tmp_cwd_cur[["station","CWD_cur_len","CWD_cur_start","CWD_cur_end"]], use_container_width=True, height=420)


# ============================================================
# PAGE: QC
# ============================================================
elif st.session_state["page"] == "QC":
    require_results()

    outputs = st.session_state["outputs"]
    meta = st.session_state["meta"]

    MONTH_STR = meta["MONTH_STR"]
    das_n = meta["das_n"]
    end_day = meta["end_day"]

    wide_bmkg_out = outputs["wide_bmkg_out"]
    qc_station = outputs["qc_station"]
    qc_unmapped = outputs["qc_unmapped"]
    qc_gap = outputs["qc_gap"]
    qc_empty_last_day = outputs["qc_empty_last_day"]

    st.subheader("QC")
    st.write(f"Periode: **{MONTH_STR}** | Dasarian: **{das_n}** | Rentang: **1–{end_day}**")
    st.write(f"Total stasiun: **{len(HORIZONTAL_COLS)}**")

    total_cells_bmkg = end_day * len(HORIZONTAL_COLS)
    cells_with_row = int((wide_bmkg_out.drop(columns=["TGL"]) != "x").to_numpy().sum())
    coverage_pct = round(cells_with_row / total_cells_bmkg * 100, 2)

    q1, q2, q3 = st.columns(3)
    q1.metric("Coverage record (%)", f"{coverage_pct}%")
    q2.metric("Cells with record", f"{cells_with_row}/{total_cells_bmkg}")
    q3.metric("Stations", f"{len(HORIZONTAL_COLS)}")

    st.markdown("---")
    with st.expander("QC kelengkapan per stasiun"):
        st.dataframe(qc_station, use_container_width=True, height=520)

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

# ============================================================
# PAGE: Tabel
# ============================================================
elif st.session_state["page"] == "Tabel":
    require_results()

    outputs = st.session_state["outputs"]
    wide_bmkg_out = outputs["wide_bmkg_out"]
    wide_num_out = outputs["wide_num_out"]

    st.subheader("Tabel Output")

    view_choice = st.radio(
        "Pilih tampilan",
        options=["FORMAT BMKG (x / - / 0 / angka)", "NUMERIC (NaN / 0.1 / angka)"],
        index=0,
        horizontal=True,
        key="view_choice"
    )

    if view_choice.startswith("FORMAT BMKG"):
        st.dataframe(wide_bmkg_out, use_container_width=True, height=720)
    else:
        st.dataframe(wide_num_out, use_container_width=True, height=720)

# ============================================================
# PAGE: Grafik
# ============================================================
elif st.session_state["page"] == "Grafik":
    require_results()

    outputs = st.session_state["outputs"]
    meta = st.session_state["meta"]

    wide_num_out = outputs["wide_num_out"].copy()

    st.subheader("Grafik curah hujan harian per pos (pilih satu atau banyak)")

    # station selector
    selected = st.multiselect(
        "Pilih Pos Hujan",
        options=HORIZONTAL_COLS,
        default=["Sembalun"] if "Sembalun" in HORIZONTAL_COLS else [],
        help="Bisa pilih lebih dari satu untuk dibandingkan"
    )

    if not selected:
        st.info("Pilih minimal 1 pos hujan.")
        st.stop()

    # prepare long format
    dfp = wide_num_out[["TGL"] + selected].copy()
    dfp_long = dfp.melt(id_vars=["TGL"], var_name="station", value_name="rain_mm")
    dfp_long["rain_mm"] = pd.to_numeric(dfp_long["rain_mm"], errors="coerce")

    # optional: display last day conditions for selected stations
    cdd_cwd_df = st.session_state["derived"]["cdd_cwd_df"].copy()
    cur_sel = cdd_cwd_df[cdd_cwd_df["station"].isin(selected)][
        ["station","CDD_cur_len","CDD_cur_start","CWD_cur_len","CWD_cur_start"]
    ].copy()

    st.markdown("### Kondisi terkini di hari terakhir window")
    st.dataframe(cur_sel.sort_values("station"), use_container_width=True, height=240)

    st.markdown("### Time series")
    # Streamlit can plot multi-line if you pivot to wide with TGL index
    chart_df = dfp.set_index("TGL")
    st.line_chart(chart_df)

    st.markdown("### Tabel nilai")
    st.dataframe(dfp, use_container_width=True, height=520)


# ============================================================
# PAGE: Peta
# ============================================================
elif st.session_state["page"] == "Peta":
    st.subheader("Peta interaktif stasiun (hover untuk tooltip)")

    coords_final = st.session_state["coords_final"].copy()

    # -----------------------------
    # Join hasil jika tersedia
    # -----------------------------
    if st.session_state.get("outputs") is not None:
        outputs = st.session_state["outputs"]
        derived = st.session_state["derived"]

        qc_station = outputs["qc_station"][["station", "completeness_pct"]].copy()
        station_dash = derived["station_dash"][["station", "total_mm", "max_mm", "tgl_max"]].copy()
        cdd_cwd_df = derived["cdd_cwd_df"][[
            "station",
            "CDD_len", "CWD_len",
            "CDD_cur_len", "CWD_cur_len",
            "CH_max_mm", "CH_max_TGL"
        ]].copy()


        map_df = (
            coords_final.merge(qc_station, on="station", how="left")
                       .merge(station_dash, on="station", how="left")
                       .merge(cdd_cwd_df, on="station", how="left")
        )
        st.caption("Peta sudah digabung dengan hasil curah hujan, QC, dan indeks.")
    else:
        map_df = coords_final.copy()
        st.info("Hasil curah hujan belum diproses. Peta hanya menampilkan koordinat dan QC koordinat.")

    # -----------------------------
    # Controls
    # -----------------------------
    c1, c2, c3, c4 = st.columns([1, 1, 1.1, 1.2])
    with c1:
        hide_missing = st.checkbox("Sembunyikan stasiun tanpa koordinat", value=True)
    with c2:
        show_only_bad = st.checkbox("Hanya QC koordinat bermasalah", value=False)
    with c3:
        point_size = st.slider("Ukuran titik", min_value=3, max_value=18, value=9, step=1)
    with c4:
        mode = st.radio(
            "Mode peta",
            options=["Titik (Scatter)", "Heatmap (nilai layer)"],
            index=0,
            horizontal=True
        )

    plot_df = map_df.copy()
    if hide_missing:
        plot_df = plot_df[plot_df["lat"].notna() & plot_df["lon"].notna()].copy()
    if show_only_bad:
        plot_df = plot_df[plot_df["qc_flag"].isin(["MISSING_COORD", "OUT_OF_BOUNDS", "DUP_LATLON"])].copy()

    if plot_df.empty:
        st.warning("Tidak ada titik yang bisa ditampilkan (cek filter atau data koordinat).")
        st.stop()

    layer = st.selectbox(
        "Warna atau bobot berdasarkan",
        options=[
            "QC Koordinat (flag)",
            "Kelengkapan data (completeness_pct)",
            "Akumulasi dasarian (total_mm)",
            "CDD terpanjang (CDD_len)",
            "CWD terpanjang (CWD_len)",
            "CDD terkini (CDD_cur_len)",
            "CWD terkini (CWD_cur_len)",
            "CH maksimum (CH_max_mm)"
        ],
    )

    left, right = st.columns([4.2, 1.3])

    with left:
        st.markdown("### Map")
    with right:
        st.markdown("### Legend")

    # -----------------------------
    # Color + legend helpers
    # -----------------------------
    def clamp01(x: float) -> float:
        return max(0.0, min(1.0, x))

    def value_to_rgb(v, vmin, vmax):
        # gradient: rendah -> biru, tinggi -> merah
        if pd.isna(v) or pd.isna(vmin) or pd.isna(vmax) or vmax == vmin:
            return [160, 160, 160, 180]
        t = clamp01((float(v) - float(vmin)) / (float(vmax) - float(vmin)))
        r = int(60 + 180 * t)
        g = int(80 + 60 * (1 - t))
        b = int(220 - 180 * t)
        return [r, g, b, 190]

    def qc_to_rgb(flag: str):
        m = {
            "OK": [30, 160, 60, 190],
            "MISSING_COORD": [180, 180, 180, 160],
            "OUT_OF_BOUNDS": [255, 140, 0, 190],
            "DUP_LATLON": [220, 60, 60, 190],
        }
        return m.get(str(flag), [140, 140, 140, 170])

    def render_qc_legend(container):
        items = [
            ("OK", (30, 160, 60)),
            ("MISSING_COORD", (180, 180, 180)),
            ("OUT_OF_BOUNDS", (255, 140, 0)),
            ("DUP_LATLON", (220, 60, 60)),
        ]
        with container:
            for label, (r, g, b) in items:
                st.markdown(
                    f"""
<div style="display:flex;align-items:center;margin-bottom:6px;">
  <div style="width:14px;height:14px;background:rgb({r},{g},{b});
              border:1px solid #999;margin-right:8px;"></div>
  <div style="font-size:13px;">{label}</div>
</div>
""",
                    unsafe_allow_html=True
                )

    def render_continuous_legend(container, series: pd.Series, title: str):
        s = pd.to_numeric(series, errors="coerce")
        s = s[np.isfinite(s)]
        with container:
            st.caption(title)
            if s.empty:
                st.caption("Tidak ada nilai.")
                return

            q0 = float(np.nanmin(s))
            q25 = float(np.nanpercentile(s, 25))
            q50 = float(np.nanpercentile(s, 50))
            q75 = float(np.nanpercentile(s, 75))
            q100 = float(np.nanmax(s))

            st.markdown(
                """
<div style="height:12px;border-radius:6px;border:1px solid #bbb;
background: linear-gradient(90deg, rgb(60,80,220), rgb(240,80,40));">
</div>
""",
                unsafe_allow_html=True
            )
            st.write(
                pd.DataFrame(
                    {
                        "min": [q0],
                        "p25": [q25],
                        "median": [q50],
                        "p75": [q75],
                        "max": [q100],
                    }
                )
            )

    # -----------------------------
    # Tentukan metric column + label
    # -----------------------------
    metric_col = None
    metric_label = None

    if layer == "QC Koordinat (flag)":
        metric_col = "qc_flag"
        metric_label = "QC"
    elif layer == "Kelengkapan data (completeness_pct)":
        metric_col = "completeness_pct"
        metric_label = "Completeness (%)"
    elif layer == "Akumulasi dasarian (total_mm)":
        metric_col = "total_mm"
        metric_label = "Total (mm)"
    elif layer == "CDD terpanjang (CDD_len)":
        metric_col = "CDD_len"
        metric_label = "CDD (hari)"
    elif layer == "CWD terpanjang (CWD_len)":
        metric_col = "CWD_len"
        metric_label = "CWD (hari)"
    elif layer == "CH maksimum (CH_max_mm)":
        metric_col = "CH_max_mm"
        metric_label = "CH max (mm)"
    elif layer == "CDD terkini (CDD_cur_len)":
        metric_col = "CDD_cur_len"
        metric_label = "CDD current (hari)"
    elif layer == "CWD terkini (CWD_cur_len)":
        metric_col = "CWD_cur_len"
        metric_label = "CWD current (hari)"


    # -----------------------------
    # Prepare colors for Scatter
    # -----------------------------
    if metric_col == "qc_flag":
        plot_df["__color__"] = plot_df["qc_flag"].apply(qc_to_rgb)
    else:
        # make sure numeric
        plot_df[metric_col] = pd.to_numeric(plot_df.get(metric_col), errors="coerce")
        vmin, vmax = plot_df[metric_col].min(skipna=True), plot_df[metric_col].max(skipna=True)
        plot_df["__color__"] = plot_df[metric_col].apply(lambda v: value_to_rgb(v, vmin, vmax))

    # -----------------------------
    # Render Legend (right column)
    # -----------------------------
    if metric_col == "qc_flag":
        render_qc_legend(right)
    else:
        render_continuous_legend(right, plot_df[metric_col], metric_label)

    # -----------------------------
    # Tooltip (hover)
    # -----------------------------
    tooltip_html = (
        "<b>{station}</b><br/>"
        "POS: {pos_id}<br/>"
        "Lat/Lon: {lat}, {lon}<br/>"
        "QC: {qc_flag}<br/>"
    )
    if metric_col is not None:
        tooltip_html += f"{metric_label}: " + "{" + metric_col + "}<br/>"

    tooltip = {
        "html": tooltip_html,
        "style": {"backgroundColor": "white", "color": "black"}
    }

    # -----------------------------
    # View state
    # -----------------------------
    center_lat = float(plot_df["lat"].median())
    center_lon = float(plot_df["lon"].median())
    view_state = pdk.ViewState(
        latitude=center_lat,
        longitude=center_lon,
        zoom=8.2,
        pitch=0
    )

    # -----------------------------
    # Layers
    # -----------------------------
    layers = []

    if mode.startswith("Titik"):
        layer_scatter = pdk.Layer(
            "ScatterplotLayer",
            data=plot_df,
            get_position=["lon", "lat"],
            get_fill_color="__color__",
            get_radius=point_size * 120,
            pickable=True,
            auto_highlight=True,
        )
        layers.append(layer_scatter)

    else:
        # Heatmap only for numeric layers
        if metric_col == "qc_flag":
            with left:
                st.warning("Heatmap hanya tersedia untuk layer numerik (bukan QC kategori). Gunakan mode Titik.")
        else:
            hm_df = plot_df.copy()
            hm_df[metric_col] = pd.to_numeric(hm_df[metric_col], errors="coerce")
            hm_df = hm_df[np.isfinite(hm_df[metric_col])].copy()

            if hm_df.empty:
                with left:
                    st.warning("Tidak ada nilai numerik untuk dibuat heatmap.")
            else:
                with left:
                    hm_intensity = st.slider("Heatmap intensity", 0.5, 5.0, 1.2, 0.1)
                    hm_radius = st.slider("Heatmap radius (meter)", 5000, 60000, 25000, 1000)

                layer_heat = pdk.Layer(
                    "HeatmapLayer",
                    data=hm_df,
                    get_position=["lon", "lat"],
                    get_weight=metric_col,
                    radius=hm_radius,
                    intensity=hm_intensity,
                    threshold=0.02
                )
                layers.append(layer_heat)

    # -----------------------------
    # Render Map (left column)
    # -----------------------------
    with left:
        st.pydeck_chart(
            pdk.Deck(
                layers=layers,
                initial_view_state=view_state,
                tooltip=tooltip,
                map_style=None
            )
        )

    # -----------------------------
    # Tabel ringkasan
    # -----------------------------
    st.markdown("### Tabel ringkasan (sesuai layer)")
    cols_show = ["station", "pos_id", "lat", "lon", "elev_m", "qc_flag"]
    if metric_col and metric_col in plot_df.columns and metric_col not in cols_show:
        cols_show.append(metric_col)
    st.dataframe(plot_df[cols_show], use_container_width=True, height=620)


# ============================================================
# PAGE: Download
# ============================================================
elif st.session_state["page"] == "Download":
    require_results()

    outputs = st.session_state["outputs"]
    meta = st.session_state["meta"]
    derived = st.session_state["derived"]

    MONTH_STR = meta["MONTH_STR"]
    das_n = meta["das_n"]

    wide_bmkg_out = outputs["wide_bmkg_out"]
    wide_num_out = outputs["wide_num_out"]
    qc_station = outputs["qc_station"]
    qc_day = outputs["qc_day"]
    qc_unmapped = outputs["qc_unmapped"]
    qc_gap = outputs["qc_gap"]
    qc_empty_last_day = outputs["qc_empty_last_day"]

    station_dash = derived["station_dash"]
    day_dash = derived["day_dash"]
    cdd_cwd_df = derived["cdd_cwd_df"]

    coords_final = st.session_state["coords_final"].copy()

    summary_station_name = f"SUMMARY_station_rain_{MONTH_STR}_das{das_n}.csv"
    summary_day_name = f"SUMMARY_day_rain_{MONTH_STR}_das{das_n}.csv"
    summary_cdd_cwd_name = f"SUMMARY_CDD_CWD_CHmax_{MONTH_STR}_das{das_n}.csv"
    coords_name = "STATION_COORDS_MAPPED.csv"

    st.subheader("Download")

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
            coords_name,
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
        coords_name: coords_final,
    }

    df_dl = download_map[download_choice]
    st.download_button(
        label=f"Download: {download_choice}",
        data=to_csv_bytes(df_dl),
        file_name=download_choice,
        mime="text/csv",
        use_container_width=True
    )



