import streamlit as st
import pandas as pd
import numpy as np
from datetime import date

# ============================================================
# Page
# ============================================================
st.set_page_config(
    page_title="Pos Hujan Dasarian: Rekap, Indeks, dan QC",
    layout="wide"
)

st.title("Pos Hujan Dasarian: Rekap, Indeks, dan QC")
st.caption("Transpose vertikal → horizontal (urut stasiun fix) + FORMAT BMKG + NUMERIC + QC + Ringkasan + CDD/CWD/CHmax")

with st.expander("Panduan dan syarat file (klik untuk buka)", expanded=False):
    st.markdown(
        """
## Transposer Pos Hujan (Vertikal → Horizontal)

Aplikasi ini digunakan untuk mengubah data curah hujan harian format **vertikal** (baris per stasiun per tanggal)
menjadi format **horizontal** (1 baris per tanggal, kolom per stasiun) dengan urutan kolom **harus persis** mengikuti header yang sudah ditetapkan.

### Input
File CSV vertikal yang minimal memiliki kolom:
- `NAME`
- `DATA TIMESTAMP`
- `RAINFALL DAY MM`

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

### Output yang tersedia
- Tabel **FORMAT BMKG**
- Tabel **NUMERIC**
- QC kelengkapan (per stasiun dan per tanggal)
- QC unmapped names (indikasi masalah penamaan)
- QC stasiun kosong total dan kosong di hari terakhir
- Ringkasan akumulasi dan indeks **CDD/CWD** serta **CH maksimum** pada window dasarian

### Tutorial singkat
1. Upload CSV vertikal (boleh lebih dari 1 file).
2. Pilih **Year**, **Month**, **Dasarian**.
3. Atur threshold bila perlu.
4. Klik **Run**.
5. Gunakan menu “Input / Hasil / QC / Tabel / Download” untuk berpindah halaman tanpa scroll.
"""
    )

# ============================================================
# Navigation: "Tabs" that are truly controllable
# ============================================================
PAGES = ["Input", "Hasil", "QC", "Tabel", "Download"]

if "page" not in st.session_state:
    st.session_state["page"] = "Input"

def goto(page: str):
    if page in PAGES:
        st.session_state["page"] = page

def to_csv_bytes(df: pd.DataFrame) -> bytes:
    return df.to_csv(index=False).encode("utf-8")

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

# ============================================================
# State init
# ============================================================
if "outputs" not in st.session_state:
    st.session_state["outputs"] = None
if "meta" not in st.session_state:
    st.session_state["meta"] = None
if "derived" not in st.session_state:
    st.session_state["derived"] = None

def clear_results():
    st.session_state["outputs"] = None
    st.session_state["meta"] = None
    st.session_state["derived"] = None
    goto("Input")

def require_results():
    if st.session_state.get("outputs") is None or st.session_state.get("meta") is None or st.session_state.get("derived") is None:
        st.info("Belum ada hasil. Silakan proses data di halaman Input.")
        st.stop()

# ============================================================
# Top navigation bar (real navigation)
# ============================================================
nav_cols = st.columns([1, 1, 1, 1, 1, 2])
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
    if st.button("Download", use_container_width=True):
        goto("Download"); st.rerun()
with nav_cols[5]:
    st.write(f"**Halaman aktif:** {st.session_state['page']}")

st.divider()

# ============================================================
# PAGE: Input
# ============================================================
if st.session_state["page"] == "Input":
    st.subheader("Input data")

    up = st.file_uploader(
        "Upload CSV vertikal",
        type=["csv"],
        accept_multiple_files=True,
        key="uploader"
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

    if run:
        if not up:
            st.error("Upload file CSV terlebih dahulu.")
            st.stop()

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
    qc_unmapped = outputs["qc_unmapped"]
    qc_gap = outputs["qc_gap"]
    qc_empty_last_day = outputs["qc_empty_last_day"]

    st.subheader("QC")
    st.write(f"Periode: **{MONTH_STR}** | Dasarian: **{das_n}** | Rentang: **1–{end_day}**")

    total_cells_bmkg = end_day * len(HORIZONTAL_COLS)
    cells_with_row = int((wide_bmkg_out.drop(columns=["TGL"]) != "x").to_numpy().sum())
    coverage_pct = round(cells_with_row / total_cells_bmkg * 100, 2)

    q1, q2, q3 = st.columns(3)
    q1.metric("Coverage record (%)", f"{coverage_pct}%")
    q2.metric("Cells with record", f"{cells_with_row}/{total_cells_bmkg}")
    q3.metric("Stations", f"{len(HORIZONTAL_COLS)}")

    st.markdown("---")
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

    summary_station_name = f"SUMMARY_station_rain_{MONTH_STR}_das{das_n}.csv"
    summary_day_name = f"SUMMARY_day_rain_{MONTH_STR}_das{das_n}.csv"
    summary_cdd_cwd_name = f"SUMMARY_CDD_CWD_CHmax_{MONTH_STR}_das{das_n}.csv"

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


