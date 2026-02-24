import streamlit as st
import pandas as pd
import numpy as np
from datetime import date
import pydeck as pdk

st.set_page_config(
    page_title="SEGARA: Sistem Ekspor dan Generator Analisis Dasarian",
    layout="wide"
)

st.title("SEGARA: Sistem Ekspor dan Generator Analisis Dasarian")
st.caption(
    "Platform operasional untuk pengolahan data pos hujan dasarian: standarisasi format BMKG, kontrol kualitas, "
    "perhitungan ringkasan dan indeks basah-kering, serta visualisasi spasial."
)

with st.expander("Panduan penggunaan SEGARA (klik untuk buka)", expanded=False):
    st.markdown("""
## SEGARA: Sistem Ekspor dan Generator Analisis Dasarian

SEGARA adalah platform operasional untuk **standarisasi, kontrol kualitas, analisis, dan ekspor** data curah hujan dasarian secara terintegrasi.

Aplikasi ini mentransformasi data curah hujan harian berformat **vertikal** (baris per stasiun per tanggal) menjadi format **horizontal** (1 baris per tanggal, kolom per stasiun) dengan urutan kolom **tetap sesuai header baku BMKG**.

---

### Input data curah hujan

File CSV vertikal minimal memiliki kolom berikut:
- `NAME`
- `DATA TIMESTAMP`
- `RAINFALL DAY MM`

---

### Koordinat untuk tab Peta

Aplikasi membaca **coords.csv** dari root repo untuk kebutuhan visualisasi peta dan analisis spasial, dengan kolom:
- `POS HUJAN ID`
- `NAME`
- `CURRENT LATITUDE`
- `CURRENT LONGITUDE`
- `CURRENT ELEVATION M`

---

### Pengaturan periode analisis

- **Year**: tahun data  
- **Month**: bulan data (01–12)  
- **Dasarian**:
  - **Das 1**: tanggal 1–10  
  - **Das 2**: tanggal 11–20  
  - **Das 3**: tanggal 21–akhir bulan  

---

### Aturan nilai format BMKG (tampilan)

- raw = 0 → `-` (tidak hujan teramati)  
- raw = 8888 → `0` (hujan sangat kecil atau trace)  
- raw = 9999 → `x` (tidak ada data atau alat bermasalah)  
- raw kosong atau NaN → `x`  
- tidak ada baris data pada tanggal tersebut → `x`

---

### Aturan nilai numeric (perhitungan)

- raw = 0 → 0.0  
- raw = 8888 → 0.1 mm  
- raw = 9999 → NaN  
- raw kosong atau NaN → NaN  
- tidak ada baris data pada tanggal tersebut → NaN  

---

### Output utama SEGARA

#### Standarisasi dan QC
- Tabel **Format BMKG**
- Tabel **Numeric**
- QC kelengkapan per stasiun
- QC kelengkapan per tanggal
- QC nama tidak dikenali atau tidak sesuai header (indikasi isu penamaan)
- QC stasiun kosong pada seluruh window
- QC stasiun kosong pada hari terakhir window
- QC duplikasi record pada pasangan stasiun dan tanggal (bila ada)

#### Analisis dasarian
- Akumulasi curah hujan per pos pada window dasarian terpilih
- Pos terbasah dan terkering berdasarkan akumulasi dasarian
- CDD dan CWD current (run yang berakhir pada hari terakhir window)
- CDD dan CWD terpanjang dalam window
- Curah hujan maksimum harian dalam window
- Coverage data pada window (berdasarkan ketersediaan record)

#### Visualisasi spasial
- Peta akumulasi hujan
- Peta kelengkapan data
- Peta CDD dan CWD
- Peta curah hujan maksimum harian

#### Ekspor data
- Seluruh tabel dan ringkasan dapat diunduh dalam format CSV.

---

### Alur penggunaan

1. Unggah CSV vertikal (dapat lebih dari satu file).
2. Pilih **Year**, **Month**, dan **Dasarian**.
3. Atur threshold bila diperlukan.
4. Klik **Run** untuk memproses data.
5. Gunakan menu **Input / Hasil / QC / Tabel / Grafik / Peta / Download** untuk berpindah tampilan.

---

### Implementasi operasional

SEGARA digunakan sebagai sistem pendukung pengolahan dan analisis data curah hujan dasarian di **Stasiun Klimatologi Nusa Tenggara Barat** untuk meningkatkan konsistensi format, ketepatan kontrol kualitas, kecepatan analisis, dan kemudahan diseminasi informasi.

---

### Pengembang sistem

**Cakra Mahasurya Atmojo Pamungkas**  
Stasiun Klimatologi Nusa Tenggara Barat  
Badan Meteorologi, Klimatologi, dan Geofisika (BMKG)
""")


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
    
def join_names(names, max_show=8):
    names = [str(x) for x in names if pd.notna(x)]
    if len(names) <= max_show:
        return ", ".join(names)
    return ", ".join(names[:max_show]) + f" (+{len(names)-max_show} lagi)"
    
def to_csv_bytes(df: pd.DataFrame) -> bytes:
    """Convert DataFrame to UTF-8 CSV bytes (Excel-friendly)."""
    if df is None:
        df = pd.DataFrame()
    # utf-8-sig adds BOM so Excel reads it nicely
    return df.to_csv(index=False).encode("utf-8-sig")

def fmt_station_list(df, col_station="station", col_val=None, col_tgl=None):
    # return (names_str, detail_str)
    stn = df[col_station].astype(str).tolist()
    names_str = join_names(stn)
    if col_val and col_tgl and (col_val in df.columns) and (col_tgl in df.columns):
        # show station (TGL x) pairs
        pairs = []
        for _, r in df.iterrows():
            tgl = r[col_tgl]
            tgl_txt = "-" if pd.isna(tgl) else f"TGL {int(tgl)}"
            pairs.append(f"{r[col_station]} ({tgl_txt})")
        detail_str = join_names(pairs, max_show=6)
        return names_str, detail_str
    return names_str, ""

def dasarian_windows_to_build(year: int, month: int, selected_das: int):
    last_day = month_end_day(year, month)

    windows = {}

    # Das 1
    if selected_das >= 1:
        windows["das1"] = (1, 10)

    # Das 2
    if selected_das >= 2:
        windows["das2"] = (11, 20)

    # Das 3
    if selected_das >= 3:
        windows["das3"] = (21, last_day)

    # Monthly always
    windows["monthly"] = (1, last_day)

    return windows

def build_outputs(df_month_full: pd.DataFrame, month_start: int, month_end: int, win_start: int, win_end: int):
    """
    Build outputs for a given window [win_start..win_end], while keeping the transposed tables
    always covering the full month [month_start..month_end].

    df_month_full must already be filtered to the target month and contain column TGL.
    """

    # full month day axis for transposer tables
    all_days = np.arange(int(month_start), int(month_end) + 1)
    win_days = np.arange(int(win_start), int(win_end) + 1)

    df_month_full = df_month_full.copy()
    df_month_full["NAME"] = normalize_station_name(df_month_full["NAME"])
    df_month_full["NAME_H"] = df_month_full["NAME"].replace(NAME_MAP)

    # raw numeric parsing
    df_month_full["raw"] = pd.to_numeric(df_month_full["RAINFALL DAY MM"], errors="coerce")
    df_month_full["has_row"] = 1

    # =========================
    # QC 0: duplicates inside WINDOW (more actionable)
    # =========================
    df_win = df_month_full[df_month_full["TGL"].between(int(win_start), int(win_end))].copy()

    dup_counts = (
        df_win.groupby(["TGL", "NAME_H"], dropna=False)
              .size()
              .reset_index(name="n_records")
    )
    qc_duplicates = dup_counts[dup_counts["n_records"] > 1].copy()

    if not qc_duplicates.empty:
        src_list = (
            df_win.groupby(["TGL", "NAME_H"])["__source_file__"]
                  .apply(lambda s: ", ".join(sorted(set(map(str, s)))))
                  .reset_index(name="source_files")
        )
        ts_list = (
            df_win.groupby(["TGL", "NAME_H"])["DATA TIMESTAMP"]
                  .apply(lambda s: ", ".join(sorted(set(map(str, s.astype(str).head(6))))))
                  .reset_index(name="timestamps_sample")
        )
        qc_duplicates = (
            qc_duplicates.merge(src_list, on=["TGL", "NAME_H"], how="left")
                         .merge(ts_list, on=["TGL", "NAME_H"], how="left")
                         .sort_values(["n_records", "TGL", "NAME_H"], ascending=[False, True, True])
        )

    # =========================
    # QC 1: unknown raw names (use FULL MONTH to catch all)
    # =========================
    horizontal_set = set(HORIZONTAL_COLS)
    map_keys_set = set(map(str, NAME_MAP.keys()))

    raw_names_set = set(map(str, df_month_full["NAME"].dropna().unique()))
    ok_direct = raw_names_set & horizontal_set
    ok_mappable = raw_names_set & map_keys_set

    unknown_raw = sorted(raw_names_set - ok_direct - ok_mappable)
    qc_unknown_names = (
        df_month_full[df_month_full["NAME"].isin(unknown_raw)][["NAME", "__source_file__"]]
        .assign(n=1)
        .groupby(["NAME"], as_index=False)
        .agg(
            count=("n", "sum"),
            source_files=("__source_file__", lambda s: ", ".join(sorted(set(map(str, s)))))
        )
        .sort_values(["count", "NAME"], ascending=[False, True])
    )

    # =========================
    # NUMERIC mapping (FULL MONTH)
    # =========================
    rain_num = df_month_full["raw"].copy()
    rain_num[df_month_full["raw"].isna()] = np.nan
    rain_num[df_month_full["raw"] == 9999] = np.nan
    rain_num[df_month_full["raw"] == 8888] = 0.1
    rain_num[df_month_full["raw"] == 0] = 0.0
    df_month_full["rain_num"] = rain_num

    # =========================
    # Pivot to wide (FULL MONTH axis 1..last_day)
    # =========================
    wide_raw = (
        df_month_full.pivot_table(index="TGL", columns="NAME_H", values="raw", aggfunc="first")
                    .reindex(index=all_days, columns=HORIZONTAL_COLS)
    )
    wide_num = (
        df_month_full.pivot_table(index="TGL", columns="NAME_H", values="rain_num", aggfunc="first")
                    .reindex(index=all_days, columns=HORIZONTAL_COLS)
    )
    present = (
        df_month_full.pivot_table(index="TGL", columns="NAME_H", values="has_row", aggfunc="first")
                    .reindex(index=all_days, columns=HORIZONTAL_COLS)
    )

    # =========================
    # FORMAT BMKG (FULL MONTH table)
    # =========================
    wide_bmkg = pd.DataFrame("x", index=wide_raw.index, columns=wide_raw.columns)
    row_exists = present.notna()

    wide_bmkg = wide_bmkg.mask(row_exists & (wide_raw == 0), "-")
    wide_bmkg = wide_bmkg.mask(row_exists & (wide_raw == 8888), "0")

    is_pos_measured = row_exists & (wide_raw.notna()) & (wide_raw > 0) & (wide_raw != 8888) & (wide_raw != 9999)
    wide_bmkg = wide_bmkg.mask(is_pos_measured, wide_raw.astype(float))

    wide_bmkg_out = wide_bmkg.copy()
    wide_bmkg_out.insert(0, "TGL", wide_bmkg_out.index.astype(int))

    wide_num_out = wide_num.copy()
    wide_num_out.insert(0, "TGL", wide_num_out.index.astype(int))

    # =========================
    # QC summaries computed on WINDOW only
    # =========================
    present_win = present.loc[win_days].copy()

    station_summary = pd.DataFrame({
        "station": HORIZONTAL_COLS,
        "days_present": present_win.notna().sum(axis=0).astype(int).values,
        "total_days": len(present_win.index),
    })
    station_summary["completeness_pct"] = (station_summary["days_present"] / station_summary["total_days"] * 100).round(1)
    qc_station = station_summary.sort_values(["completeness_pct", "station"], ascending=[True, True])

    day_summary = pd.DataFrame({
        "TGL": present_win.index.astype(int),
        "stations_present": present_win.notna().sum(axis=1).astype(int).values,
        "total_stations": len(HORIZONTAL_COLS),
    })
    day_summary["completeness_pct"] = (day_summary["stations_present"] / day_summary["total_stations"] * 100).round(1)
    qc_day = day_summary

    mapped_not_in_horizontal = sorted(set(map(str, df_month_full["NAME_H"].dropna().unique())) - horizontal_set)
    qc_mapped_not_in_header = (
        df_month_full[df_month_full["NAME_H"].isin(mapped_not_in_horizontal)][["NAME", "NAME_H", "__source_file__"]]
        .drop_duplicates()
        .sort_values(["NAME_H", "NAME"])
    )

    # gaps within window
    last_present_day = present_win.notna().apply(lambda s: s[s].index.max() if s.any() else np.nan)
    gap_days_since_last = (int(win_end) - last_present_day).where(~last_present_day.isna(), np.nan)
    empty_all_window = present_win.notna().sum(axis=0) == 0

    qc_gap = pd.DataFrame({
        "station": HORIZONTAL_COLS,
        "has_any_record_start_to_end": (~empty_all_window).astype(int).values,
        "last_record_day_in_window": last_present_day.reindex(HORIZONTAL_COLS).values,
        "empty_days_since_last_record": gap_days_since_last.reindex(HORIZONTAL_COLS).values
    })

    # empty on last day of window
    last_day_present = present_win.loc[int(win_end)].notna()
    qc_empty_last_day = pd.DataFrame({
        "station": HORIZONTAL_COLS,
        "is_empty_on_last_day": (~last_day_present.reindex(HORIZONTAL_COLS).fillna(False)).astype(int).values,
        "last_record_day_in_window": last_present_day.reindex(HORIZONTAL_COLS).values
    })
    qc_empty_last_day["empty_days_up_to_last_day"] = np.where(
        qc_empty_last_day["last_record_day_in_window"].isna(),
        float(win_end - win_start + 1),
        float(win_end) - qc_empty_last_day["last_record_day_in_window"].astype(float)
    )

    pre_last_any = present_win.loc[present_win.index < int(win_end)].notna().sum(axis=0) > 0
    qc_empty_last_day["was_present_before_last_day"] = pre_last_any.reindex(HORIZONTAL_COLS).fillna(False).astype(int).values

    qc_empty_last_day = qc_empty_last_day[qc_empty_last_day["is_empty_on_last_day"] == 1].copy()
    qc_empty_last_day = qc_empty_last_day.sort_values(["empty_days_up_to_last_day", "station"], ascending=[False, True])

    assert list(wide_bmkg_out.columns[1:]) == HORIZONTAL_COLS, "Urutan kolom output tidak sesuai HORIZONTAL_COLS"

    return {
        # full month transposer tables
        "wide_bmkg_out": wide_bmkg_out,
        "wide_num_out": wide_num_out,

        # window metadata
        "month_start": int(month_start),
        "month_end": int(month_end),
        "win_start": int(win_start),
        "win_end": int(win_end),

        # QC (WINDOW-based)
        "qc_station": qc_station,
        "qc_day": qc_day,
        "qc_gap": qc_gap,
        "qc_empty_last_day": qc_empty_last_day,

        # QC name and duplicates
        "qc_duplicates": qc_duplicates,
        "qc_unknown_names": qc_unknown_names,
        "qc_mapped_not_in_header": qc_mapped_not_in_header,

        # present matrices
        "present_matrix_full": present,
        "present_matrix_win": present_win,
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
# Navigation (single-file multi-view)  <-- MUST BE ABOVE ALL goto() calls
# ============================================================
PAGES = ["Input", "Hasil", "QC", "Tabel", "Grafik", "Peta", "Download"]

st.session_state.setdefault("page", "Input")

def goto(page: str):
    st.session_state["page"] = page if page in PAGES else "Input"


# ============================================================
# Session state init
# ============================================================
st.session_state.setdefault("outputs", None)
st.session_state.setdefault("meta", None)
st.session_state.setdefault("derived", None)

if "coords_final" not in st.session_state:
    coords_repo = load_coords_from_repo("coords.csv")
    st.session_state["coords_final"] = prepare_station_coordinates(coords_repo)


def clear_results():
    st.session_state["outputs"] = None
    st.session_state["meta"] = None
    st.session_state["derived"] = None
    goto("Input")


def require_results():
    if (
        st.session_state.get("outputs") is None
        or st.session_state.get("meta") is None
        or st.session_state.get("derived") is None
        or not st.session_state.get("derived", {}).get("windows")
    ):
        st.info("Belum ada hasil. Silakan proses data di halaman Input.")
        st.stop()

def get_windows():
    d = st.session_state.get("derived", {})
    return d.get("windows", {})

def window_selector_ui():
    windows = get_windows()
    if not windows:
        return None

    # keep stable order
    order = [k for k in ["das1", "das2", "das3", "monthly"] if k in windows]
    labels = {k: windows[k]["label"] for k in order}

    default_key = st.session_state.get("view_window", order[0])
    if default_key not in order:
        default_key = order[0]

    # selector
    sel = st.radio(
        "Pilih periode tampilan",
        options=order,
        format_func=lambda k: labels.get(k, k),
        index=order.index(default_key),
        horizontal=True,
        key="__window_selector__"
    )

    st.session_state["view_window"] = sel
    return sel

def get_active_bundle():
    windows = get_windows()
    key = st.session_state.get("view_window")
    if not windows or key not in windows:
        return None
    return windows[key]

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
    st.write(f"**Halaman aktif:** {st.session_state.get('page', 'Input')}")

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
            format_func=lambda x: (
                "Das 1 (1–10)" if x == "1" else
                ("Das 2 (11–20)" if x == "2" else "Das 3 (21–akhir bulan)")
            ),
            index=0,
            horizontal=True
        )

    st.markdown("**Threshold ringkasan**")
    t1, t2 = st.columns(2)
    with t1:
        rainy_thr = st.number_input(
            "Batas hari hujan untuk CWD dan hitungan hari hujan (mm)",
            min_value=0.0, value=1.0, step=0.1
        )
    with t2:
        heavy_thr = st.number_input("Batas hujan lebat (mm)", min_value=0.0, value=20.0, step=1.0)

    b1, b2, b3 = st.columns([1, 1, 2])
    with b1:
        run = st.button("Run", type="primary", use_container_width=True)
    with b2:
        reset = st.button("Reset hasil", use_container_width=True)
    with b3:
        st.caption("Tip: setelah Run sukses, aplikasi otomatis pindah ke halaman Hasil.")

    if reset:
        clear_results()
        st.success("Hasil direset.")
        st.rerun()

    with st.expander("Status koordinat yang dipakai (coords.csv)", expanded=False):
        coords_final = st.session_state["coords_final"].copy()
        st.write("Koordinat dibaca dari file **coords.csv** di root repo.")
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
        if das_n == 1:
            start_day, end_day = 1, 10
        elif das_n == 2:
            start_day, end_day = 11, 20
        else:
            start_day, end_day = 21, last_day
    
        # -------------------------
        # Read files (robust)
        # -------------------------
        def read_csv_robust(uploaded_file) -> pd.DataFrame:
            attempts = [
                (",", "utf-8"),
                (";", "utf-8"),
                ("\t", "utf-8"),
                (",", "utf-8-sig"),
                (";", "utf-8-sig"),
                (",", "latin1"),
                (";", "latin1"),
                (",", "cp1252"),
                (";", "cp1252"),
            ]
            last_err = None
            for sep, enc in attempts:
                try:
                    uploaded_file.seek(0)
                    df_try = pd.read_csv(uploaded_file, sep=sep, encoding=enc, engine="python")
                    if df_try.shape[1] >= 2:
                        return df_try
                except Exception as e:
                    last_err = e
            raise last_err if last_err else RuntimeError("Unknown read_csv failure")
    
        dfs, bad_files, bad_details = [], [], []
        for f in up_rain:
            try:
                tmp = read_csv_robust(f)
                tmp["__source_file__"] = f.name
                dfs.append(tmp)
            except Exception as e:
                bad_files.append(f.name)
                bad_details.append(f"{f.name}: {type(e).__name__} - {e}")
    
        if bad_files:
            st.warning(f"File gagal dibaca dan diabaikan: {bad_files}")
            with st.expander("Detail error pembacaan file", expanded=False):
                st.code("\n".join(bad_details))
    
        if not dfs:
            st.error("Tidak ada file curah hujan valid untuk diproses.")
            st.stop()
    
        df = pd.concat(dfs, ignore_index=True)
    
        # -------------------------
        # Validate required columns (after read)
        # -------------------------
        required_cols = ["NAME", "DATA TIMESTAMP", "RAINFALL DAY MM"]
        missing_cols = [c for c in required_cols if c not in df.columns]
        if missing_cols:
            st.error(f"Kolom wajib tidak ditemukan: {missing_cols}\nKolom terbaca: {list(df.columns)}")
            st.stop()
    
        # -------------------------
        # Parse datetime FIRST (robust for your export format)
        # -------------------------
        ts = df["DATA TIMESTAMP"].astype(str).str.strip()
    
        # Try strict parse for format like: "2026-01-01 00:00:00.0 +0:00"
        dt = pd.to_datetime(ts, format="%Y-%m-%d %H:%M:%S.%f %z", errors="coerce")
    
        # Fallback: strip trailing ".0 +0:00" then parse without tz
        if dt.isna().mean() > 0.5:
            ts2 = ts.str.replace(r"\.0\s*\+\d{1,2}:\d{2}$", "", regex=True)
            dt = pd.to_datetime(ts2, format="%Y-%m-%d %H:%M:%S", errors="coerce")
    
        df["DATA TIMESTAMP"] = dt
        df = df[df["DATA TIMESTAMP"].notna()].copy()
    
        if df.empty:
            st.error("Semua DATA TIMESTAMP gagal diparse (menjadi NaT). Cek format timestamp pada file.")
            st.stop()
    
        # -------------------------
        # Optional debug (SAFE)
        # -------------------------
        with st.expander("Debug: hasil baca + parse timestamp", expanded=False):
            st.write("Kolom:", list(df.columns))
            st.write("dtype DATA TIMESTAMP:", df["DATA TIMESTAMP"].dtype)
            st.dataframe(df.head(20), use_container_width=True)
    
        # -------------------------
        # Filter month (NOW safe to use .dt)
        # -------------------------
        df_month = df[df["DATA TIMESTAMP"].dt.strftime("%Y-%m") == MONTH_STR].copy()
        if df_month.empty:
            st.error(f"Tidak ada baris untuk {MONTH_STR}. Periksa pilihan bulan atau data.")
            st.stop()
    
        df_month["TGL"] = df_month["DATA TIMESTAMP"].dt.day
    
        # FULL MONTH DATA (source utama semua window)
        df_month_full = df_month[df_month["TGL"].between(1, last_day)].copy()
        if df_month_full.empty:
            st.error(f"Tidak ada baris pada rentang tanggal 1 s.d. {last_day} untuk {MONTH_STR}.")
            st.stop()
    
        # -------------------------
        # Build windows
        # -------------------------
        windows_def = dasarian_windows_to_build(YEAR, int(MM), das_n)
        windows_out = {}
    
        for key, (win_start, win_end) in windows_def.items():
            out = build_outputs(
                df_month_full,
                month_start=1,
                month_end=last_day,
                win_start=win_start,
                win_end=win_end
            )
    
            wide_num_full = out["wide_num_out"].copy()
            wide_num_win = wide_num_full[wide_num_full["TGL"].between(int(win_start), int(win_end))].copy()
    
            dash, daydash, hi = build_dashboard(wide_num_win, rainy_thr, heavy_thr)
            cdd = compute_cdd_cwd(wide_num_win, wet_threshold=rainy_thr)
    
            label = {
                "das1": "Das 1 (TGL 1–10)",
                "das2": "Das 2 (TGL 11–20)",
                "das3": f"Das 3 (TGL 21–{last_day})",
                "monthly": f"Bulanan (TGL 1–{last_day})",
            }[key]
    
            windows_out[key] = {
                "key": key,
                "label": label,
                "start_day": int(win_start),
                "end_day": int(win_end),
                "outputs": out,
                "station_dash": dash,
                "day_dash": daydash,
                "hi": hi,
                "cdd_cwd_df": cdd,
            }
    
        # -------------------------
        # Save session
        # -------------------------
        st.session_state["meta"] = {
            "MONTH_STR": MONTH_STR,
            "YEAR": YEAR,
            "MM": MM,
            "last_day": int(last_day),
            "das_n": int(das_n),
            "rainy_thr": float(rainy_thr),
            "heavy_thr": float(heavy_thr),
        }
    
        st.session_state["derived"] = {"windows": windows_out}
        st.session_state["view_window"] = f"das{das_n}"
        st.session_state["outputs"] = windows_out[f"das{das_n}"]["outputs"]
    
        st.success("Selesai diproses. Membuka halaman Hasil.")
        goto("Hasil")
        st.rerun()

# ============================================================
# PAGE: Hasil  (FULL REWRITE: window-aware + safe + backward compatible)
# ============================================================
elif st.session_state["page"] == "Hasil":
    require_results()

    meta = st.session_state.get("meta", {}) or {}

    # Window selector + active bundle
    window_selector_ui()
    bundle = get_active_bundle()
    if bundle is None:
        st.info("Window belum tersedia. Silakan Run ulang.")
        st.stop()

    # Meta
    MONTH_STR = str(meta.get("MONTH_STR", "UNKNOWN"))
    last_day = int(meta.get("last_day", 0) or 0)
    rainy_thr = float(meta.get("rainy_thr", 1.0))
    heavy_thr = float(meta.get("heavy_thr", 20.0))

    # Window
    win_label = str(bundle.get("label", "Window"))
    start_day = int(bundle.get("start_day", 1))
    end_day = int(bundle.get("end_day", start_day))

    # Payloads (safe defaults)
    outputs = bundle.get("outputs", {}) or {}
    station_dash = bundle.get("station_dash", pd.DataFrame())
    day_dash = bundle.get("day_dash", pd.DataFrame())
    hi = bundle.get("hi", {}) or {}
    cdd_cwd_df = bundle.get("cdd_cwd_df", pd.DataFrame())

    # -------------------------
    # Header
    # -------------------------
    st.subheader("Hasil")
    st.write(
        f"Periode: **{MONTH_STR}** | Tampilan: **{win_label}** | Rentang analisis: **TGL {start_day}–{end_day}**"
    )
    st.write(
        f"Threshold CWD dan hari hujan: **{rainy_thr} mm** | Threshold hujan lebat: **{heavy_thr} mm**"
    )

    # -------------------------
    # Helpers (local to this page)
    # -------------------------
    def _num(s):
        return pd.to_numeric(s, errors="coerce")

    def _safe_df(x):
        return x if isinstance(x, pd.DataFrame) else pd.DataFrame()

    station_dash = _safe_df(station_dash)
    day_dash = _safe_df(day_dash)
    cdd_cwd_df = _safe_df(cdd_cwd_df)

    # ============================================================
    # A) CURRENT RUN highlights (ending at end_day) (tie safe)
    # ============================================================
    cdd_cur_best_len, cdd_cur_names, cdd_cur_start_min, cdd_cur_end = 0, "", None, None
    cwd_cur_best_len, cwd_cur_names, cwd_cur_start_min, cwd_cur_end = 0, "", None, None

    if not cdd_cwd_df.empty:
        tmp_all = cdd_cwd_df.copy()

        # CDD current
        if "CDD_cur_len" in tmp_all.columns:
            tmp = tmp_all.copy()
            tmp["CDD_cur_len"] = _num(tmp["CDD_cur_len"]).fillna(0).astype(int)
            best_len = int(tmp["CDD_cur_len"].max()) if len(tmp) else 0
            if best_len > 0:
                best = tmp[tmp["CDD_cur_len"] == best_len].copy().sort_values("station")
                cdd_cur_best_len = best_len
                cdd_cur_names = join_names(best["station"].tolist())
                if ("CDD_cur_start" in best.columns) and ("CDD_cur_end" in best.columns):
                    starts = _num(best["CDD_cur_start"])
                    ends = _num(best["CDD_cur_end"])
                    cdd_cur_start_min = int(np.nanmin(starts)) if starts.notna().any() else None
                    cdd_cur_end = int(np.nanmax(ends)) if ends.notna().any() else end_day

        # CWD current
        if "CWD_cur_len" in tmp_all.columns:
            tmp = tmp_all.copy()
            tmp["CWD_cur_len"] = _num(tmp["CWD_cur_len"]).fillna(0).astype(int)
            best_len = int(tmp["CWD_cur_len"].max()) if len(tmp) else 0
            if best_len > 0:
                best = tmp[tmp["CWD_cur_len"] == best_len].copy().sort_values("station")
                cwd_cur_best_len = best_len
                cwd_cur_names = join_names(best["station"].tolist())
                if ("CWD_cur_start" in best.columns) and ("CWD_cur_end" in best.columns):
                    starts = _num(best["CWD_cur_start"])
                    ends = _num(best["CWD_cur_end"])
                    cwd_cur_start_min = int(np.nanmin(starts)) if starts.notna().any() else None
                    cwd_cur_end = int(np.nanmax(ends)) if ends.notna().any() else end_day

    # ============================================================
    # B) Wettest + driest station accumulation in window (tie safe)
    # ============================================================
    wet_total, wet_names, wet_n = np.nan, "", 0
    dry_total, dry_names, dry_n = np.nan, "", 0
    ch_min_wet_val, ch_min_wet_names, ch_min_wet_n = np.nan, "", 0

    if (not station_dash.empty) and ("total_mm" in station_dash.columns):
        sd = station_dash.copy()
        sd["total_mm"] = _num(sd["total_mm"])
        sd2 = sd[np.isfinite(sd["total_mm"])].copy()

        if not sd2.empty:
            wet_total = float(sd2["total_mm"].max())
            dry_total = float(sd2["total_mm"].min())

            wet_df = sd2[sd2["total_mm"] == wet_total].copy().sort_values("station")
            dry_df = sd2[sd2["total_mm"] == dry_total].copy().sort_values("station")

            wet_n = int(len(wet_df))
            dry_n = int(len(dry_df))

            wet_names = join_names(wet_df["station"].tolist())
            dry_names = join_names(dry_df["station"].tolist())

            sd_wetonly = sd2[sd2["total_mm"] > 0].copy()
            if not sd_wetonly.empty:
                ch_min_wet_val = float(sd_wetonly["total_mm"].min())
                minwet_df = sd_wetonly[sd_wetonly["total_mm"] == ch_min_wet_val].copy().sort_values("station")
                ch_min_wet_n = int(len(minwet_df))
                ch_min_wet_names = join_names(minwet_df["station"].tolist())

    # ============================================================
    # C) CH max (daily maximum inside window) (tie safe, show TGL)
    # ============================================================
    ch_max_val, ch_max_names, ch_max_detail = np.nan, "", ""

    if (not cdd_cwd_df.empty) and ("CH_max_mm" in cdd_cwd_df.columns):
        tmp = cdd_cwd_df.copy()
        tmp["CH_max_mm"] = _num(tmp["CH_max_mm"])
        if tmp["CH_max_mm"].notna().any():
            ch_max_val = float(tmp["CH_max_mm"].max())
            top = tmp[tmp["CH_max_mm"] == ch_max_val].copy().sort_values("station")
            ch_max_names, ch_max_detail = fmt_station_list(
                top, col_station="station", col_val="CH_max_mm", col_tgl="CH_max_TGL"
            )

    # ============================================================
    # Render grouped metrics (Basah vs Kering)
    # ============================================================
    basah_col, kering_col = st.columns(2)

    with basah_col:
        st.markdown("### Basah")
        b1, b2, b3 = st.columns(3)

        if cwd_cur_best_len > 0 and cwd_cur_names:
            rng = f"{cwd_cur_best_len} hari"
            if cwd_cur_start_min is not None and cwd_cur_end is not None:
                rng += f" (TGL {cwd_cur_start_min}–{cwd_cur_end})"
            b1.metric("CWD current terpanjang", cwd_cur_names, rng)
        else:
            b1.metric("CWD current terpanjang", "-")

        if np.isfinite(wet_total) and wet_names:
            label = "Akumulasi CH tertinggi" if wet_n <= 1 else f"Akumulasi CH tertinggi ({wet_n} pos)"
            b2.metric(label, wet_names, f"{wet_total:.1f} mm")
        else:
            b2.metric("Akumulasi CH tertinggi", "-")

        if np.isfinite(ch_max_val) and ch_max_names:
            b3.metric("CH maksimum (harian)", ch_max_names, f"{ch_max_val:.1f} mm")
        else:
            b3.metric("CH maksimum (harian)", "-")

        with st.expander("Detail Basah", expanded=False):
            st.markdown(
                f"Akumulasi CH = jumlah curah hujan harian pada rentang **TGL {start_day}–{end_day}** untuk setiap pos."
            )

            st.markdown("#### Akumulasi CH tertinggi (window)")
            if not station_dash.empty:
                cols_rank = [c for c in ["station", "total_mm", "valid_days", "max_mm", "tgl_max"] if c in station_dash.columns]
                st.dataframe(
                    station_dash.sort_values(["total_mm", "station"], ascending=[False, True])[cols_rank].head(30),
                    use_container_width=True,
                    height=520
                )
            else:
                st.write("Ringkasan pos belum tersedia.")

            st.markdown("---")
            st.markdown("#### CH maksimum harian (tie safe)")
            if np.isfinite(ch_max_val) and ch_max_detail:
                st.write(f"Nilai maksimum: **{ch_max_val:.1f} mm**")
                st.write(ch_max_detail)
            else:
                st.write("Tidak ada CH maksimum yang valid.")

            st.markdown("---")
            st.markdown(f"#### CWD current (run harus berakhir di TGL {end_day})")
            if (not cdd_cwd_df.empty) and ("CWD_cur_len" in cdd_cwd_df.columns):
                tmp = cdd_cwd_df.copy()
                tmp["CWD_cur_len"] = _num(tmp["CWD_cur_len"]).fillna(0).astype(int)
                best_len = int(tmp["CWD_cur_len"].max()) if len(tmp) else 0
                if best_len > 0:
                    best = tmp[tmp["CWD_cur_len"] == best_len].copy().sort_values("station")
                    cols3 = [c for c in ["station", "CWD_cur_len", "CWD_cur_start", "CWD_cur_end"] if c in best.columns]
                    st.dataframe(best[cols3], use_container_width=True, height=360)
                else:
                    st.write("Tidak ada CWD current (len > 0) pada hari terakhir.")
            else:
                st.write("Kolom CWD_cur_len tidak tersedia.")

    with kering_col:
        st.markdown("### Kering")
        k1, k2, k3 = st.columns(3)

        if cdd_cur_best_len > 0 and cdd_cur_names:
            rng = f"{cdd_cur_best_len} hari"
            if cdd_cur_start_min is not None and cdd_cur_end is not None:
                rng += f" (TGL {cdd_cur_start_min}–{cdd_cur_end})"
            k1.metric("CDD current terpanjang", cdd_cur_names, rng)
        else:
            k1.metric("CDD current terpanjang", "-")

        if np.isfinite(dry_total) and dry_names:
            label = "Akumulasi CH terendah" if dry_n <= 1 else f"Akumulasi CH terendah ({dry_n} pos)"
            k2.metric(label, dry_names, f"{dry_total:.1f} mm")
        else:
            k2.metric("Akumulasi CH terendah", "-")

        if np.isfinite(ch_min_wet_val) and ch_min_wet_names:
            label = "CH minimum (ada hujan)" if ch_min_wet_n <= 1 else f"CH minimum (ada hujan) ({ch_min_wet_n} pos)"
            k3.metric(label, ch_min_wet_names, f"{ch_min_wet_val:.1f} mm")
        else:
            k3.metric("CH minimum (ada hujan)", "-")

        with st.expander("Detail Kering", expanded=False):
            st.markdown(
                f"Akumulasi CH = jumlah curah hujan harian pada rentang **TGL {start_day}–{end_day}** untuk setiap pos."
            )
            st.markdown(f"#### CDD current (run harus berakhir di TGL {end_day})")
            if (not cdd_cwd_df.empty) and ("CDD_cur_len" in cdd_cwd_df.columns):
                tmp = cdd_cwd_df.copy()
                tmp["CDD_cur_len"] = _num(tmp["CDD_cur_len"]).fillna(0).astype(int)
                best_len = int(tmp["CDD_cur_len"].max()) if len(tmp) else 0
                if best_len > 0:
                    best = tmp[tmp["CDD_cur_len"] == best_len].copy().sort_values("station")
                    cols = [c for c in ["station", "CDD_cur_len", "CDD_cur_start", "CDD_cur_end"] if c in best.columns]
                    st.dataframe(best[cols], use_container_width=True, height=360)
                else:
                    st.write("Tidak ada CDD current (len > 0) pada hari terakhir.")
            else:
                st.write("Kolom CDD_cur_len tidak tersedia.")

    st.caption("Jika nilai sama, semua nama pos ditampilkan (dipotong bila terlalu panjang).")

    # ============================================================
    # Ringkasan agregat (window)
    # ============================================================
    st.markdown("---")
    st.subheader("Ringkasan (agregat)")

    m1, m2, m3, m4 = st.columns(4)
    if isinstance(hi, dict) and hi:
        v_total = hi.get("total_mm_all_cells", np.nan)
        v_cov = hi.get("coverage_pct_numeric", np.nan)
        m1.metric("Total hujan (mm) semua pos", f"{float(v_total):.1f}" if np.isfinite(v_total) else "-")
        m2.metric("Coverage numeric (%)", f"{float(v_cov):.2f}" if np.isfinite(v_cov) else "-")

        ws = hi.get("wettest_station", {}) or {}
        wd = hi.get("wettest_day", {}) or {}
        m3.metric(
            "Pos terbasah (akumulasi)",
            ws.get("station", "-"),
            f"{float(ws.get('total_mm', np.nan)):.1f} mm" if ws else "-"
        )
        m4.metric(
            "Hari terbasah (akumulasi)",
            f"TGL {int(wd.get('TGL', end_day))}" if ("TGL" in wd and pd.notna(wd.get("TGL"))) else "-",
            f"{float(wd.get('total_mm_all_stations', np.nan)):.1f} mm" if wd else "-"
        )
    else:
        m1.metric("Total hujan (mm) semua pos", "-")
        m2.metric("Coverage numeric (%)", "-")
        m3.metric("Pos terbasah (akumulasi)", "-")
        m4.metric("Hari terbasah (akumulasi)", "-")

    # ============================================================
    # Kondisi terkini (Top 15)
    # ============================================================
    st.markdown("---")
    st.subheader("Kondisi terkini (run harus berakhir pada hari terakhir window)")

    if not cdd_cwd_df.empty:
        tmp_cur = cdd_cwd_df.copy()

        tmp_cur["CDD_cur_len"] = _num(tmp_cur.get("CDD_cur_len", 0)).fillna(0).astype(int)
        tmp_cur["CWD_cur_len"] = _num(tmp_cur.get("CWD_cur_len", 0)).fillna(0).astype(int)

        tmp_cdd_cur = (
            tmp_cur[tmp_cur["CDD_cur_len"] > 0]
            .sort_values(["CDD_cur_len", "station"], ascending=[False, True])
            .head(15)
            .copy()
        )
        tmp_cwd_cur = (
            tmp_cur[tmp_cur["CWD_cur_len"] > 0]
            .sort_values(["CWD_cur_len", "station"], ascending=[False, True])
            .head(15)
            .copy()
        )

        x1, x2 = st.columns(2)
        with x1:
            st.caption(f"Top 15 CDD current (ending TGL {end_day})")
            cols = [c for c in ["station", "CDD_cur_len", "CDD_cur_start", "CDD_cur_end", "CH_max_mm", "CH_max_TGL"] if c in tmp_cdd_cur.columns]
            st.dataframe(tmp_cdd_cur[cols], use_container_width=True, height=420)

        with x2:
            st.caption(f"Top 15 CWD current (ending TGL {end_day})")
            cols = [c for c in ["station", "CWD_cur_len", "CWD_cur_start", "CWD_cur_end", "CH_max_mm", "CH_max_TGL"] if c in tmp_cwd_cur.columns]
            st.dataframe(tmp_cwd_cur[cols], use_container_width=True, height=420)
    else:
        st.info("Tabel CDD/CWD belum tersedia. Silakan Run dari halaman Input.")

    # ============================================================
    # Grafik ringkas (window)
    # ============================================================
    st.markdown("---")
    gL, gR = st.columns([1.1, 0.9])

    with gL:
        if (not day_dash.empty) and ("TGL" in day_dash.columns):
            st.subheader("Total hujan harian (semua pos)")
            if "total_mm_all_stations" in day_dash.columns:
                st.line_chart(day_dash[["TGL", "total_mm_all_stations"]].set_index("TGL"))
            else:
                st.caption("Kolom total_mm_all_stations tidak tersedia pada day_dash.")

            st.subheader("Jumlah pos hujan per hari")
            if "stations_rainy_ge_thr" in day_dash.columns:
                st.line_chart(day_dash[["TGL", "stations_rainy_ge_thr"]].set_index("TGL"))
            else:
                st.caption("Kolom stations_rainy_ge_thr tidak tersedia pada day_dash.")
        else:
            st.info("Ringkasan harian belum tersedia.")

    with gR:
        st.subheader("Top 15 pos berdasarkan akumulasi window")
        if not station_dash.empty:
            st.dataframe(station_dash.head(15), use_container_width=True, height=520)
        else:
            st.info("Ringkasan pos belum tersedia.")

    # ============================================================
    # Indeks terpanjang (sekunder)  <-- FIXED: define top_cdd/top_cwd
    # ============================================================
    st.markdown("---")
    st.subheader("Indeks terpanjang (sekunder)")

    top_cdd = pd.DataFrame()
    top_cwd = pd.DataFrame()

    if not cdd_cwd_df.empty:
        tmp = cdd_cwd_df.copy()
        if "CDD_len" in tmp.columns:
            tmp["CDD_len"] = _num(tmp["CDD_len"])
            top_cdd = (
                tmp[tmp["CDD_len"].notna()]
                .sort_values(["CDD_len", "station"], ascending=[False, True])
                .head(15)
                .copy()
            )
        if "CWD_len" in tmp.columns:
            tmp["CWD_len"] = _num(tmp["CWD_len"])
            top_cwd = (
                tmp[tmp["CWD_len"].notna()]
                .sort_values(["CWD_len", "station"], ascending=[False, True])
                .head(15)
                .copy()
            )

    d1, d2 = st.columns(2)

    with d1:
        st.caption("Top 15 CDD terpanjang (per pos)")
        if not top_cdd.empty:
            cols = [c for c in ["station", "CDD_len", "CDD_start", "CDD_end", "CH_max_mm", "CH_max_TGL"] if c in top_cdd.columns]
            st.dataframe(top_cdd[cols], use_container_width=True, height=520)
        else:
            st.write("Tidak ada")

    with d2:
        st.caption("Top 15 CWD terpanjang (per pos)")
        if not top_cwd.empty:
            cols = [c for c in ["station", "CWD_len", "CWD_start", "CWD_end", "CH_max_mm", "CH_max_TGL"] if c in top_cwd.columns]
            st.dataframe(top_cwd[cols], use_container_width=True, height=520)
        else:
            st.write("Tidak ada")

    with st.expander("Tabel lengkap CDD/CWD/CHmax (semua pos)", expanded=False):
        if not cdd_cwd_df.empty:
            st.dataframe(cdd_cwd_df, use_container_width=True, height=520)
        else:
            st.write("Tidak ada")

    # ============================================================
    # Insight bulanan (sekunder)  [window-aware + backward compatible]
    # ============================================================
    st.markdown("---")
    st.subheader("Insight bulanan (sekunder)")

    windows = st.session_state.get("derived", {}).get("windows", {}) or {}
    monthly_bundle = windows.get("monthly")
    legacy_monthly = st.session_state.get("derived", {}).get("monthly", {}) or {}

    if monthly_bundle is not None:
        hi_m = monthly_bundle.get("hi", {}) or {}
        station_dash_m = monthly_bundle.get("station_dash", pd.DataFrame())
        day_dash_m = monthly_bundle.get("day_dash", pd.DataFrame())
        last_day_m = int(st.session_state.get("meta", {}).get("last_day", last_day) or last_day)
    else:
        hi_m = legacy_monthly.get("hi", {}) or {}
        station_dash_m = legacy_monthly.get("station_dash", pd.DataFrame())
        day_dash_m = legacy_monthly.get("day_dash", pd.DataFrame())
        last_day_m = last_day

    station_dash_m = _safe_df(station_dash_m)
    day_dash_m = _safe_df(day_dash_m)

    no_monthly = (not hi_m) and station_dash_m.empty and day_dash_m.empty
    if no_monthly:
        st.info("Insight bulanan belum tersedia. Pastikan window **Bulanan (TGL 1–akhir bulan)** terbentuk saat Run.")
    else:
        st.write(f"Periode bulanan: **{MONTH_STR}** | Rentang: **TGL 1–{last_day_m}**")

        mm1, mm2, mm3, mm4 = st.columns(4)

        v_total_m = hi_m.get("total_mm_all_cells", np.nan)
        v_cov_m = hi_m.get("coverage_pct_numeric", np.nan)
        ws_m = hi_m.get("wettest_station", {}) or {}
        wd_m = hi_m.get("wettest_day", {}) or {}

        mm1.metric("Total hujan bulanan (mm) semua pos", f"{float(v_total_m):.1f}" if np.isfinite(v_total_m) else "-")
        mm2.metric("Coverage numeric bulanan (%)", f"{float(v_cov_m):.2f}" if np.isfinite(v_cov_m) else "-")
        mm3.metric(
            "Pos terbasah bulanan (akumulasi)",
            ws_m.get("station", "-"),
            f"{float(ws_m.get('total_mm', np.nan)):.1f} mm" if ws_m else "-"
        )
        mm4.metric(
            "Hari terbasah bulanan (akumulasi)",
            f"TGL {int(wd_m.get('TGL', last_day_m))}" if ("TGL" in wd_m and pd.notna(wd_m.get("TGL"))) else "-",
            f"{float(wd_m.get('total_mm_all_stations', np.nan)):.1f} mm" if wd_m else "-"
        )

        with st.expander("Detail insight bulanan", expanded=False):
            if not station_dash_m.empty:
                st.dataframe(station_dash_m.head(30), use_container_width=True, height=520)
            else:
                st.caption("Ringkasan pos bulanan belum tersedia.")

            if (not day_dash_m.empty) and ("TGL" in day_dash_m.columns) and ("total_mm_all_stations" in day_dash_m.columns):
                st.line_chart(day_dash_m[["TGL", "total_mm_all_stations"]].set_index("TGL"))
            else:
                st.caption("Ringkasan harian bulanan belum tersedia atau kolom total_mm_all_stations tidak ada.")
                
# ============================================================
# PAGE: QC
# ============================================================
elif st.session_state["page"] == "QC":
    require_results()

    meta = st.session_state["meta"]

    # choose which window to show (das1/das2/das3/monthly)
    window_selector_ui()
    bundle = get_active_bundle()
    if bundle is None:
        st.info("Window belum tersedia. Silakan Run ulang di halaman Input.")
        st.stop()

    MONTH_STR = str(meta.get("MONTH_STR", "UNKNOWN"))
    win_label = str(bundle.get("label", "Window"))
    start_day = int(bundle.get("start_day", 1))
    end_day = int(bundle.get("end_day", start_day))

    outputs = bundle.get("outputs", {})
    if not outputs:
        st.info("Output window kosong. Silakan Run ulang di halaman Input.")
        st.stop()

    # -------------------------
    # QC tables (window-based)
    # -------------------------
    qc_station = outputs.get("qc_station", pd.DataFrame())
    qc_day = outputs.get("qc_day", pd.DataFrame())
    qc_gap = outputs.get("qc_gap", pd.DataFrame())
    qc_empty_last_day = outputs.get("qc_empty_last_day", pd.DataFrame())

    qc_duplicates = outputs.get("qc_duplicates", pd.DataFrame())
    qc_unknown_names = outputs.get("qc_unknown_names", pd.DataFrame())
    qc_mapped_not_in_header = outputs.get("qc_mapped_not_in_header", pd.DataFrame())

    # window presence matrix (preferred)
    present_win = outputs.get("present_matrix_win", None)
    days_in_window = int(end_day - start_day + 1)

    # -------------------------
    # Coverage calculations
    # -------------------------
    record_cells = 0
    total_cells = int(days_in_window * len(HORIZONTAL_COLS))
    coverage_record_pct = 0.0

    if isinstance(present_win, pd.DataFrame) and (not present_win.empty):
        record_cells = int(present_win.notna().to_numpy().sum())
        total_cells = int(present_win.size)
        coverage_record_pct = round(record_cells / total_cells * 100, 2) if total_cells > 0 else 0.0
    else:
        # fallback: compute using FULL MONTH bmkg table but restrict rows to window days
        wide_bmkg_out = outputs.get("wide_bmkg_out", pd.DataFrame())
        if isinstance(wide_bmkg_out, pd.DataFrame) and (not wide_bmkg_out.empty) and ("TGL" in wide_bmkg_out.columns):
            tmp = wide_bmkg_out[wide_bmkg_out["TGL"].between(start_day, end_day)].copy()
            if not tmp.empty:
                record_cells = int((tmp.drop(columns=["TGL"]) != "x").to_numpy().sum())
                total_cells = int(days_in_window * len(HORIZONTAL_COLS))
                coverage_record_pct = round(record_cells / total_cells * 100, 2) if total_cells > 0 else 0.0

    # complete stations (must have record every day in window)
    n_complete = 0
    pct_complete = 0.0
    if isinstance(present_win, pd.DataFrame) and (not present_win.empty):
        stn_days_present = (
            present_win.notna()
                       .sum(axis=0)
                       .reindex(HORIZONTAL_COLS)
                       .fillna(0)
                       .astype(int)
        )
        n_complete = int((stn_days_present == days_in_window).sum())
        pct_complete = round(n_complete / len(HORIZONTAL_COLS) * 100, 2) if len(HORIZONTAL_COLS) else 0.0

    # -------------------------
    # Header
    # -------------------------
    st.subheader("QC")
    st.write(f"Periode: **{MONTH_STR}** | Tampilan: **{win_label}** | Rentang: **TGL {start_day}–{end_day}**")
    st.write(f"Total stasiun: **{len(HORIZONTAL_COLS)}**")

    a1, a2 = st.columns([1, 3])
    a1.metric("Pos lengkap (full)", f"{n_complete}/{len(HORIZONTAL_COLS)}", f"{pct_complete:.2f}%")
    a2.caption("Pos lengkap = jumlah pos yang punya record pada semua hari dalam window aktif.")

    q1, q2, q3, q4 = st.columns(4)
    q1.metric("Coverage record (%)", f"{coverage_record_pct}%")
    q2.metric("Cells with record", f"{record_cells}/{total_cells}")
    q3.metric("Stations", f"{len(HORIZONTAL_COLS)}")
    q4.metric("Duplicate station day", f"{0 if qc_duplicates.empty else len(qc_duplicates)}")

    st.markdown("---")

    # -------------------------
    # Tables
    # -------------------------
    with st.expander("QC kelengkapan per stasiun"):
        st.dataframe(qc_station, use_container_width=True, height=520)

    with st.expander("QC kelengkapan per hari"):
        st.dataframe(qc_day, use_container_width=True, height=520)

    with st.expander("Duplicate records per station day (perlu dicek sebelum pivot)"):
        if qc_duplicates.empty:
            st.write("Tidak ada duplicate record pada pasangan TGL dan station.")
        else:
            st.dataframe(qc_duplicates, use_container_width=True, height=520)
            st.caption("Pivot memakai first, sehingga duplicate akan memilih salah satu baris. Tabel ini menunjukkan pasangan yang perlu dibersihkan.")

    with st.expander("Nama tidak dikenali (tidak masuk mapping dan tidak ada di header resmi)"):
        if qc_unknown_names.empty:
            st.write("Tidak ada nama raw yang tidak dikenali.")
        else:
            st.dataframe(qc_unknown_names, use_container_width=True, height=520)

    with st.expander("Nama hasil mapping tidak ada di header resmi"):
        if qc_mapped_not_in_header.empty:
            st.write("Tidak ada.")
        else:
            st.dataframe(qc_mapped_not_in_header, use_container_width=True, height=520)

    with st.expander("Stasiun kosong total pada window aktif"):
        if qc_gap.empty:
            st.write("Tidak ada.")
        else:
            empty_all_stations = qc_gap[qc_gap["has_any_record_start_to_end"] == 0]["station"].astype(str).tolist()
            if empty_all_stations:
                st.dataframe(pd.DataFrame({"station": empty_all_stations}), use_container_width=True)
            else:
                st.write("Tidak ada")

    with st.expander(f"Stasiun kosong pada hari terakhir window (TGL={end_day})"):
        if qc_empty_last_day.empty:
            st.write("Tidak ada")
        else:
            st.dataframe(qc_empty_last_day, use_container_width=True)
            st.caption("was_present_before_last_day = 1 berarti pernah melapor pada hari sebelumnya, lalu berhenti menjelang hari terakhir window.")

# ============================================================
# PAGE: Tabel
# ============================================================
elif st.session_state["page"] == "Tabel":
    require_results()

    meta = st.session_state["meta"]

    # choose which window to show
    window_selector_ui()
    bundle = get_active_bundle()
    if bundle is None:
        st.info("Window belum tersedia. Silakan Run ulang di halaman Input.")
        st.stop()

    MONTH_STR = str(meta.get("MONTH_STR", "UNKNOWN"))
    win_label = str(bundle.get("label", "Window"))
    start_day = int(bundle.get("start_day", 1))
    end_day = int(bundle.get("end_day", start_day))

    outputs = bundle.get("outputs", {})
    if not outputs:
        st.info("Output window kosong. Silakan Run ulang di halaman Input.")
        st.stop()

    wide_bmkg_out = outputs.get("wide_bmkg_out", pd.DataFrame())
    wide_num_out = outputs.get("wide_num_out", pd.DataFrame())

    if wide_bmkg_out.empty or wide_num_out.empty:
        st.warning("Tabel output tidak ditemukan untuk window ini. Silakan Run ulang di halaman Input.")
        st.stop()

    st.subheader("Tabel Output")
    st.write(f"Periode: **{MONTH_STR}** | Tampilan: **{win_label}** | Rentang: **TGL {start_day}–{end_day}**")

    view_choice = st.radio(
        "Pilih tampilan",
        options=[
            "FORMAT BMKG (x / - / 0 / angka)",
            "NUMERIC (NaN / 0.1 / angka)"
        ],
        index=0,
        horizontal=True,
        key="table_view_choice"
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

    meta = st.session_state["meta"]

    # choose which window to show
    window_selector_ui()
    bundle = get_active_bundle()
    if bundle is None:
        st.stop()

    MONTH_STR = str(meta.get("MONTH_STR", "UNKNOWN"))
    win_label = str(bundle.get("label", "Window"))
    start_day = int(bundle.get("start_day", 1))
    end_day = int(bundle.get("end_day", start_day))

    outputs = bundle.get("outputs", {})
    if not outputs:
        st.info("Output window kosong. Silakan Run ulang di halaman Input.")
        st.stop()

    wide_num_out = outputs.get("wide_num_out")
    if wide_num_out is None or wide_num_out.empty:
        st.warning("Tabel NUMERIC tidak tersedia untuk window ini.")
        st.stop()

    # CDD/CWD bundle (prefer per-window if available, fallback to old derived)
    cdd_cwd_df = bundle.get("cdd_cwd_df")
    if cdd_cwd_df is None:
        cdd_cwd_df = st.session_state.get("derived", {}).get("cdd_cwd_df", pd.DataFrame())

    st.subheader("Grafik curah hujan harian per pos")
    st.write(f"Periode: **{MONTH_STR}** | Tampilan: **{win_label}** | Rentang: **TGL {start_day}–{end_day}**")

    # station selector
    default_station = "Stasiun Klimatologi Kediri"
    selected = st.multiselect(
        "Pilih Pos Hujan",
        options=HORIZONTAL_COLS,
        default=[default_station] if default_station in HORIZONTAL_COLS else [],
        help="Bisa pilih lebih dari satu untuk dibandingkan",
        key="chart_station_multiselect"
    )

    if not selected:
        st.info("Pilih minimal 1 pos hujan.")
        st.stop()

    # prepare data (wide for plotting)
    dfp = wide_num_out[["TGL"] + selected].copy()
    for c in selected:
        dfp[c] = pd.to_numeric(dfp[c], errors="coerce")

    # optional: show current run (ending at last day of this window)
    st.markdown("### Kondisi terkini di hari terakhir window")
    if isinstance(cdd_cwd_df, pd.DataFrame) and (not cdd_cwd_df.empty):
        cols_want = [c for c in ["station", "CDD_cur_len", "CDD_cur_start", "CDD_cur_end",
                                 "CWD_cur_len", "CWD_cur_start", "CWD_cur_end",
                                 "CH_max_mm", "CH_max_TGL"] if c in cdd_cwd_df.columns]
        cur_sel = cdd_cwd_df[cdd_cwd_df["station"].isin(selected)][cols_want].copy()
        if cur_sel.empty:
            st.caption("Tidak ada ringkasan indeks untuk pos yang dipilih.")
        else:
            st.dataframe(cur_sel.sort_values("station"), use_container_width=True, height=260)
    else:
        st.caption("Ringkasan indeks belum tersedia untuk window ini.")

    st.markdown("### Time series")
    chart_df = dfp.set_index("TGL")
    st.line_chart(chart_df)

    st.markdown("### Tabel nilai")
    st.dataframe(dfp, use_container_width=True, height=520)


# ============================================================
# PAGE: Peta  (window-aware: das1/das2/das3/monthly)
# ============================================================
elif st.session_state["page"] == "Peta":
    st.subheader("Peta interaktif stasiun (hover untuk tooltip)")

    coords_final = st.session_state["coords_final"].copy()

    # ---------------------------------
    # Window selector (das1/das2/das3/monthly)
    # ---------------------------------
    if st.session_state.get("outputs") is not None:
        # show selector only if results exist
        window_selector_ui()
        bundle = get_active_bundle()
    else:
        bundle = None

    # ---------------------------------
    # Join results (if available)
    # ---------------------------------
    if bundle is not None:
        outputs = bundle.get("outputs", {})
        station_dash = bundle.get("station_dash", pd.DataFrame())
        cdd_cwd_df = bundle.get("cdd_cwd_df", pd.DataFrame())

        # QC completeness from window output
        qc_station = outputs.get("qc_station", pd.DataFrame())
        if isinstance(qc_station, pd.DataFrame) and (not qc_station.empty) and ("station" in qc_station.columns):
            qc_station = qc_station[["station", "completeness_pct"]].copy() if "completeness_pct" in qc_station.columns else qc_station[["station"]].copy()
        else:
            qc_station = pd.DataFrame(columns=["station", "completeness_pct"])

        # station dashboard (total, max, tgl_max)
        if not (isinstance(station_dash, pd.DataFrame) and (not station_dash.empty)):
            station_dash = pd.DataFrame(columns=["station", "total_mm", "max_mm", "tgl_max"])
        else:
            keep_sd = [c for c in ["station", "total_mm", "max_mm", "tgl_max"] if c in station_dash.columns]
            station_dash = station_dash[keep_sd].copy()

        # cdd/cwd table
        if not (isinstance(cdd_cwd_df, pd.DataFrame) and (not cdd_cwd_df.empty)):
            cdd_cwd_df = pd.DataFrame(columns=[
                "station", "CDD_len", "CWD_len", "CDD_cur_len", "CWD_cur_len", "CH_max_mm", "CH_max_TGL"
            ])
        else:
            keep_idx = [c for c in [
                "station",
                "CDD_len", "CWD_len",
                "CDD_cur_len", "CWD_cur_len",
                "CH_max_mm", "CH_max_TGL"
            ] if c in cdd_cwd_df.columns]
            cdd_cwd_df = cdd_cwd_df[keep_idx].copy()

        map_df = (
            coords_final.merge(qc_station, on="station", how="left")
                       .merge(station_dash, on="station", how="left")
                       .merge(cdd_cwd_df, on="station", how="left")
        )

        win_label = str(bundle.get("label", "Window"))
        start_day = int(bundle.get("start_day", 1))
        end_day = int(bundle.get("end_day", start_day))
        st.caption(f"Peta digabung dengan hasil: **{win_label}** (TGL {start_day}–{end_day}).")
    else:
        map_df = coords_final.copy()
        st.info("Hasil curah hujan belum diproses. Peta hanya menampilkan koordinat dan QC koordinat.")

    # -----------------------------
    # Controls
    # -----------------------------
    c1, c2, c3, c4 = st.columns([1, 1, 1.1, 1.2])
    with c1:
        hide_missing = st.checkbox("Sembunyikan stasiun tanpa koordinat", value=True, key="map_hide_missing")
    with c2:
        show_only_bad = st.checkbox("Hanya QC koordinat bermasalah", value=False, key="map_show_only_bad")
    with c3:
        point_size = st.slider("Ukuran titik", min_value=3, max_value=18, value=9, step=1, key="map_point_size")
    with c4:
        mode = st.radio(
            "Mode peta",
            options=["Titik (Scatter)", "Heatmap (nilai layer)"],
            index=0,
            horizontal=True,
            key="map_mode"
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
            "Akumulasi window (total_mm)",
            "CDD terpanjang (CDD_len)",
            "CWD terpanjang (CWD_len)",
            "CDD terkini (CDD_cur_len)",
            "CWD terkini (CWD_cur_len)",
            "CH maksimum (CH_max_mm)"
        ],
        key="map_layer"
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
            st.write(pd.DataFrame({"min": [q0], "p25": [q25], "median": [q50], "p75": [q75], "max": [q100]}))

    # -----------------------------
    # Metric column + label
    # -----------------------------
    metric_col, metric_label = None, None
    if layer == "QC Koordinat (flag)":
        metric_col, metric_label = "qc_flag", "QC"
    elif layer == "Kelengkapan data (completeness_pct)":
        metric_col, metric_label = "completeness_pct", "Completeness (%)"
    elif layer == "Akumulasi window (total_mm)":
        metric_col, metric_label = "total_mm", "Total (mm)"
    elif layer == "CDD terpanjang (CDD_len)":
        metric_col, metric_label = "CDD_len", "CDD (hari)"
    elif layer == "CWD terpanjang (CWD_len)":
        metric_col, metric_label = "CWD_len", "CWD (hari)"
    elif layer == "CH maksimum (CH_max_mm)":
        metric_col, metric_label = "CH_max_mm", "CH max (mm)"
    elif layer == "CDD terkini (CDD_cur_len)":
        metric_col, metric_label = "CDD_cur_len", "CDD current (hari)"
    elif layer == "CWD terkini (CWD_cur_len)":
        metric_col, metric_label = "CWD_cur_len", "CWD current (hari)"

    # -----------------------------
    # Prepare colors
    # -----------------------------
    if metric_col == "qc_flag":
        plot_df["__color__"] = plot_df["qc_flag"].apply(qc_to_rgb)
    else:
        plot_df[metric_col] = pd.to_numeric(plot_df.get(metric_col), errors="coerce")
        vmin, vmax = plot_df[metric_col].min(skipna=True), plot_df[metric_col].max(skipna=True)
        plot_df["__color__"] = plot_df[metric_col].apply(lambda v: value_to_rgb(v, vmin, vmax))

    # -----------------------------
    # Render legend
    # -----------------------------
    if metric_col == "qc_flag":
        render_qc_legend(right)
    else:
        render_continuous_legend(right, plot_df[metric_col], metric_label)

    # -----------------------------
    # Tooltip
    # -----------------------------
    tooltip_html = (
        "<b>{station}</b><br/>"
        "POS: {pos_id}<br/>"
        "Lat/Lon: {lat}, {lon}<br/>"
        "QC: {qc_flag}<br/>"
    )
    if metric_col is not None:
        tooltip_html += f"{metric_label}: " + "{" + metric_col + "}<br/>"

    tooltip = {"html": tooltip_html, "style": {"backgroundColor": "white", "color": "black"}}

    # -----------------------------
    # View state
    # -----------------------------
    center_lat = float(plot_df["lat"].median())
    center_lon = float(plot_df["lon"].median())
    view_state = pdk.ViewState(latitude=center_lat, longitude=center_lon, zoom=8.2, pitch=0)

    # -----------------------------
    # Layers
    # -----------------------------
    layers = []

    if mode.startswith("Titik"):
        layers.append(
            pdk.Layer(
                "ScatterplotLayer",
                data=plot_df,
                get_position=["lon", "lat"],
                get_fill_color="__color__",
                get_radius=point_size * 120,
                pickable=True,
                auto_highlight=True,
            )
        )
    else:
        # Heatmap only for numeric layers
        if metric_col == "qc_flag":
            with left:
                st.warning("Heatmap hanya untuk layer numerik. Gunakan mode Titik untuk QC kategori.")
        else:
            hm_df = plot_df.copy()
            hm_df[metric_col] = pd.to_numeric(hm_df[metric_col], errors="coerce")
            hm_df = hm_df[np.isfinite(hm_df[metric_col])].copy()

            if hm_df.empty:
                with left:
                    st.warning("Tidak ada nilai numerik untuk dibuat heatmap.")
            else:
                with left:
                    hm_intensity = st.slider("Heatmap intensity", 0.5, 5.0, 1.2, 0.1, key="hm_intensity")
                    hm_radius = st.slider("Heatmap radius (meter)", 5000, 60000, 25000, 1000, key="hm_radius")

                layers.append(
                    pdk.Layer(
                        "HeatmapLayer",
                        data=hm_df,
                        get_position=["lon", "lat"],
                        get_weight=metric_col,
                        radius=hm_radius,
                        intensity=hm_intensity,
                        threshold=0.02
                    )
                )

    # -----------------------------
    # Render map
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
    # Summary table
    # -----------------------------
    st.markdown("### Tabel ringkasan (sesuai layer)")
    cols_show = ["station", "pos_id", "lat", "lon", "elev_m", "qc_flag"]
    if metric_col and metric_col in plot_df.columns and metric_col not in cols_show:
        cols_show.append(metric_col)
    st.dataframe(plot_df[cols_show], use_container_width=True, height=620)


# ============================================================
# PAGE: Download (window-aware: das1/das2/das3/monthly)
# ============================================================
elif st.session_state["page"] == "Download":
    require_results()

    # results may be in "derived['windows']" (new) or legacy single-window (old)
    meta = st.session_state.get("meta", {}) or {}

    st.subheader("Download")

    # ---------- Window selector ----------
    window_selector_ui()
    bundle = get_active_bundle()
    if bundle is None:
        st.info("Bundle window tidak ditemukan. Silakan Run ulang di halaman Input.")
        st.stop()

    win_label = str(bundle.get("label", "Window"))
    start_day = int(bundle.get("start_day", 1))
    end_day = int(bundle.get("end_day", start_day))

    # ---------- Pull outputs from active window ----------
    outputs = bundle.get("outputs", {}) or {}
    station_dash = bundle.get("station_dash", pd.DataFrame())
    day_dash = bundle.get("day_dash", pd.DataFrame())
    cdd_cwd_df = bundle.get("cdd_cwd_df", pd.DataFrame())

    # ---------- Core outputs (must exist) ----------
    wide_bmkg_out = outputs.get("wide_bmkg_out")
    wide_num_out = outputs.get("wide_num_out")
    if wide_bmkg_out is None or wide_num_out is None:
        st.warning("Output utama tidak ditemukan pada window ini. Silakan Run ulang di halaman Input.")
        st.stop()

    # ---------- QC outputs (safe defaults) ----------
    qc_station = outputs.get("qc_station", pd.DataFrame())
    qc_day = outputs.get("qc_day", pd.DataFrame())
    qc_gap = outputs.get("qc_gap", pd.DataFrame())
    qc_empty_last_day = outputs.get("qc_empty_last_day", pd.DataFrame())

    qc_duplicates = outputs.get("qc_duplicates", pd.DataFrame())
    qc_unknown_names = outputs.get("qc_unknown_names", pd.DataFrame())
    qc_mapped_not_in_header = outputs.get("qc_mapped_not_in_header", pd.DataFrame())

    # compatibility alias (old name)
    qc_unmapped = outputs.get("qc_unmapped", qc_mapped_not_in_header)

    # ---------- Coords ----------
    coords_final = st.session_state.get("coords_final")
    coords_final = coords_final.copy() if isinstance(coords_final, pd.DataFrame) else pd.DataFrame()

    # ---------- File prefix ----------
    MONTH_STR = str(meta.get("MONTH_STR", "UNKNOWN"))
    # stable key for filenames
    view_key = str(st.session_state.get("view_window", "window")).lower()  # e.g. das1/das2/das3/monthly

    st.caption(f"Window aktif: **{win_label}** (TGL {start_day}–{end_day}) | Periode: **{MONTH_STR}**")

    # ---------- Filenames ----------
    fname_bmkg = f"rain_horizontal_{MONTH_STR}_{view_key}_format_bmkg.csv"
    fname_num = f"rain_horizontal_{MONTH_STR}_{view_key}_numeric.csv"

    fname_qc_station = f"QC_station_completeness_{MONTH_STR}_{view_key}.csv"
    fname_qc_day = f"QC_day_completeness_{MONTH_STR}_{view_key}.csv"
    fname_qc_unmapped = f"QC_unmapped_names_{MONTH_STR}_{view_key}.csv"
    fname_qc_gap = f"QC_station_empty_gap_{MONTH_STR}_{view_key}.csv"
    fname_qc_empty_last = f"QC_empty_last_day_{MONTH_STR}_{view_key}.csv"

    fname_qc_duplicates = f"QC_duplicates_station_day_{MONTH_STR}_{view_key}.csv"
    fname_qc_unknown = f"QC_unknown_raw_names_{MONTH_STR}_{view_key}.csv"

    summary_station_name = f"SUMMARY_station_rain_{MONTH_STR}_{view_key}.csv"
    summary_day_name = f"SUMMARY_day_rain_{MONTH_STR}_{view_key}.csv"
    summary_cdd_cwd_name = f"SUMMARY_CDD_CWD_CHmax_{MONTH_STR}_{view_key}.csv"

    coords_name = "STATION_COORDS_MAPPED.csv"

    # ---------- Choice UI ----------
    download_choice = st.selectbox(
        "Pilih file yang ingin di-download",
        [
            fname_bmkg,
            fname_num,
            "— QC —",
            fname_qc_station,
            fname_qc_day,
            fname_qc_unmapped,
            fname_qc_gap,
            fname_qc_empty_last,
            fname_qc_duplicates,
            fname_qc_unknown,
            "— Ringkasan —",
            summary_station_name,
            summary_day_name,
            summary_cdd_cwd_name,
            "— Referensi —",
            coords_name,
        ],
        index=0
    )

    if str(download_choice).startswith("—"):
        st.info("Pilih item file (bukan header pemisah).")
        st.stop()

    # ---------- Map file -> dataframe ----------
    download_map = {
        fname_bmkg: wide_bmkg_out,
        fname_num: wide_num_out,

        fname_qc_station: qc_station,
        fname_qc_day: qc_day,
        fname_qc_unmapped: qc_unmapped,
        fname_qc_gap: qc_gap,
        fname_qc_empty_last: qc_empty_last_day,
        fname_qc_duplicates: qc_duplicates,
        fname_qc_unknown: qc_unknown_names,

        summary_station_name: station_dash,
        summary_day_name: day_dash,
        summary_cdd_cwd_name: cdd_cwd_df,

        coords_name: coords_final,
    }

    df_dl = download_map.get(download_choice)
    if df_dl is None:
        st.error("Pilihan file tidak dikenali. Silakan pilih ulang.")
        st.stop()

    if not isinstance(df_dl, pd.DataFrame):
        try:
            df_dl = pd.DataFrame(df_dl)
        except Exception:
            st.error("Data tidak bisa dikonversi ke DataFrame untuk di-download.")
            st.stop()

    # ---------- Download ----------
    st.download_button(
        label=f"Download: {download_choice}",
        data=to_csv_bytes(df_dl),
        file_name=download_choice,
        mime="text/csv",
        use_container_width=True
    )

    # Optional: quick preview
    with st.expander("Preview (10 baris pertama)", expanded=False):
        st.dataframe(df_dl.head(10), use_container_width=True, height=320)























