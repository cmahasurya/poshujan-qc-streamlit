# utils.py

import pandas as pd
import numpy as np
import streamlit as st
from sqlalchemy import create_engine, text
from config import HORIZONTAL_COLS, NAME_MAP
import streamlit as st
from sqlalchemy import create_engine
import urllib.parse

# ============================================================
# Database Utilities
# ============================================================

@st.cache_resource
def get_db_engine():
    if "connections" in st.secrets and "postgresql" in st.secrets["connections"]:
        pg = st.secrets["connections"]["postgresql"]
        
        # Decode password jika tersimpan sebagai URL-encoded (%40 -> @)
        raw_password = urllib.parse.unquote(pg["password"])
        # Re-encode dengan aman untuk dimasukkan ke URI SQLAlchemy
        clean_password = urllib.parse.quote_plus(raw_password)
        
        db_url = (
            f"postgresql+psycopg2://{pg['username']}:{clean_password}"
            f"@{pg['host']}:{pg['port']}/{pg['database']}?sslmode=require"
        )
    else:
        from config import DB_URL
        db_url = DB_URL

    return create_engine(
        db_url,
        pool_pre_ping=True,
        pool_recycle=300,
        connect_args={"connect_timeout": 10}
    )

engine = get_db_engine()

def get_latest_db_record_info(year: int, month: int):
    """Mengecek info tanggal dan total record terakhir di database untuk bulan terpilih."""
    engine = get_db_engine()
    month_str = f"{year}-{str(month).zfill(2)}"
    
    query = text("""
        SELECT 
            MAX("DATA TIMESTAMP"::text) AS latest_ts,
            COUNT(*) AS total_records,
            COUNT(DISTINCT "NAME") AS total_stations
        FROM rainfall_data 
        WHERE TO_CHAR("DATA TIMESTAMP" AT TIME ZONE 'UTC', 'YYYY-MM') = :month_str;
    """)
    
    with engine.connect() as conn:
        res = conn.execute(query, {"month_str": month_str}).fetchone()
        
    if res and res.latest_ts:
        latest_ts_clean = str(res.latest_ts).split("+")[0].split("Z")[0].strip()
        dt = pd.to_datetime(latest_ts_clean, errors="coerce")
        latest_day = dt.day if pd.notna(dt) else None
        return {
            "latest_ts": latest_ts_clean,
            "latest_day": latest_day,
            "total_records": res.total_records,
            "total_stations": res.total_stations
        }
    return None

@st.cache_data(ttl=300)
def fetch_rainfall_data_from_db(year: int, month: int) -> pd.DataFrame:
    engine = get_db_engine()
    month_str = f"{year}-{str(month).zfill(2)}"
    
    query = text("""
        SELECT 
            "NAME", 
            "DATA TIMESTAMP"::text AS "RAW_TS", 
            "RAINFALL DAY MM"
        FROM rainfall_data 
        WHERE TO_CHAR("DATA TIMESTAMP" AT TIME ZONE 'UTC', 'YYYY-MM') = :month_str 
        ORDER BY "DATA TIMESTAMP" ASC;
    """)
    
    with engine.connect() as conn:
        df = pd.read_sql(query, conn, params={"month_str": month_str})
        
    if df.empty:
        return pd.DataFrame()

    clean_series = (
        df["RAW_TS"]
        .astype(str)
        .str.replace(r'(\+\d{2}(:\d{2})?|Z)$', '', regex=True)
        .str.strip()
    )
    
    df["DATA TIMESTAMP"] = pd.to_datetime(clean_series, format="mixed", errors="coerce")
    df["TGL"] = df["DATA TIMESTAMP"].dt.day
    df["__source_file__"] = "Supabase DB"
    
    return df.drop(columns=["RAW_TS"])

def insert_rainfall_data(df: pd.DataFrame):
    """
    Memasukkan DataFrame curah hujan (format vertikal/raw) ke tabel 'rainfall_data' di Supabase.
    Mendukung Upsert / Handling duplikasi berdasarkan constraint skema database.
    """
    engine = get_db_engine()
    df_to_insert = df.copy()

    # 1. Standarisasi Nama Kolom Wajib
    required_cols = ["NAME", "DATA TIMESTAMP", "RAINFALL DAY MM"]
    for col in required_cols:
        if col not in df_to_insert.columns:
            raise ValueError(f"Kolom wajib '{col}' tidak ditemukan dalam DataFrame yang akan di-insert.")

    # 2. Penanganan & Pembersihan Format Timestamp
    ts_clean = (
        df_to_insert["DATA TIMESTAMP"]
        .astype(str)
        .str.replace(r'(\+\d{2}(:\d{2})?|Z)$', '', regex=True)
        .str.strip()
    )
    df_to_insert["DATA TIMESTAMP"] = pd.to_datetime(ts_clean, format="mixed", errors="coerce")
    
    # Hapus baris dengan timestamp invalid
    df_to_insert = df_to_insert[df_to_insert["DATA TIMESTAMP"].notna()].copy()

    # 3. Filtering Kolom Sesuai Skema Tabel Supabase
    cols_to_keep = [c for c in ["POS HUJAN ID", "NAME", "DATA TIMESTAMP", "RAINFALL DAY MM"] if c in df_to_insert.columns]
    df_to_insert = df_to_insert[cols_to_keep]

    # 4. Eksplisit Penanganan Tipe Data
    df_to_insert["RAINFALL DAY MM"] = pd.to_numeric(df_to_insert["RAINFALL DAY MM"], errors="coerce")

    # 5. Eksekusi Batch Ingestion ke Database
    with engine.begin() as conn:
        df_to_insert.to_sql(
            "rainfall_data",
            con=conn,
            if_exists="append",
            index=False,
            method="multi",
            chunksize=1000
        )
    return len(df_to_insert)

def insert_rainfall_data(df: pd.DataFrame) -> int:
    """
    Memasukkan DataFrame curah hujan (format vertikal/raw) ke tabel 'rainfall_data' di Supabase.
    Membersihkan timestamp dan kolom agar sesuai dengan skema tabel.
    """
    engine = get_db_engine()
    df_to_insert = df.copy()

    # 1. Validasi kolom wajib
    required_cols = ["NAME", "DATA TIMESTAMP", "RAINFALL DAY MM"]
    missing = [c for c in required_cols if c not in df_to_insert.columns]
    if missing:
        raise ValueError(f"Kolom wajib tidak ditemukan dalam DataFrame: {missing}")

    # 2. Sanitasi Timestamp
    ts_clean = (
        df_to_insert["DATA TIMESTAMP"]
        .astype(str)
        .str.replace(r'(\+\d{2}(:\d{2})?|Z)$', '', regex=True)
        .str.strip()
    )
    df_to_insert["DATA TIMESTAMP"] = pd.to_datetime(ts_clean, format="mixed", errors="coerce")
    df_to_insert = df_to_insert[df_to_insert["DATA TIMESTAMP"].notna()].copy()

    # 3. Filter Kolom Sesuai Skema Database
    cols_to_keep = [c for c in ["POS HUJAN ID", "NAME", "DATA TIMESTAMP", "RAINFALL DAY MM"] if c in df_to_insert.columns]
    df_to_insert = df_to_insert[cols_to_keep]

    # 4. Pastikan Tipe Data Numerik
    df_to_insert["RAINFALL DAY MM"] = pd.to_numeric(df_to_insert["RAINFALL DAY MM"], errors="coerce")

    if df_to_insert.empty:
        return 0

    # 5. Insert Batch ke Supabase
    with engine.begin() as conn:
        df_to_insert.to_sql(
            "rainfall_data",
            con=conn,
            if_exists="append",
            index=False,
            method="multi",
            chunksize=1000
        )
    return len(df_to_insert)

@st.cache_data(ttl=300)
def fetch_rainfall_data_timeseries(year: int, month: int, lookback_days: int = 60) -> pd.DataFrame:
    """
    Mengambil data curah hujan dari database Supabase termasuk periode lookback (hari-hari sebelumnya)
    agar perhitungan CDD/CWD berkesinambungan lintas bulan (real continuous timeseries).
    """
    engine = get_db_engine()
    
    # Tanggal akhir bulan target
    target_end_dt = pd.Timestamp(year=year, month=month, day=month_end_day(year, month))
    # Tanggal awal batas lookback ke belakang
    start_dt = target_end_dt - pd.Timedelta(days=lookback_days)
    
    start_str = start_dt.strftime("%Y-%m-%d")
    end_str = target_end_dt.strftime("%Y-%m-%d")

    query = text("""
        SELECT 
            "NAME", 
            "DATA TIMESTAMP"::text AS "RAW_TS", 
            "RAINFALL DAY MM"
        FROM rainfall_data 
        WHERE ("DATA TIMESTAMP" AT TIME ZONE 'UTC')::date BETWEEN :start_str AND :end_str
        ORDER BY "DATA TIMESTAMP" ASC;
    """)
    
    with engine.connect() as conn:
        df = pd.read_sql(query, conn, params={"start_str": start_str, "end_str": end_str})
        
    if df.empty:
        return pd.DataFrame()

    clean_series = (
        df["RAW_TS"]
        .astype(str)
        .str.replace(r'(\+\d{2}(:\d{2})?|Z)$', '', regex=True)
        .str.strip()
    )
    
    df["DATA TIMESTAMP"] = pd.to_datetime(clean_series, format="mixed", errors="coerce")
    df["DATE"] = df["DATA TIMESTAMP"].dt.date
    df["__source_file__"] = "Supabase DB"
    
    return df.drop(columns=["RAW_TS"])

import pandas as pd
import io

def read_csv_robust(uploaded_file):
    """
    Fungsi kustom untuk membaca file CSV dengan penanganan otomatis 
    encoding (utf-8 / latin-1) dan auto-detect separator (, atau ;).
    """
    if uploaded_file is None:
        return None

    # Baca byte data dari Streamlit UploadedFile
    bytes_data = uploaded_file.getvalue()

    # Coba dekode encoding
    try:
        decoded_data = bytes_data.decode("utf-8")
    except UnicodeDecodeError:
        decoded_data = bytes_data.decode("latin-1")

    # Gunakan python engine dengan sep=None untuk mendeteksi delimiter secara otomatis
    df = pd.read_csv(
        io.StringIO(decoded_data),
        sep=None,
        engine="python"
    )
    
    return df

# ============================================================
# Helper Utilities
# ============================================================

def month_end_day(year: int, month: int) -> int:
    month_start = pd.Timestamp(year=year, month=month, day=1)
    month_end = (month_start + pd.offsets.MonthEnd(1)).normalize()
    return int(month_end.day)

def normalize_station_name(s: pd.Series) -> pd.Series:
    return s.astype(str).str.strip().str.replace(r"\s+", " ", regex=True)

@st.cache_data
def load_coords_from_repo(path: str = "coords.csv") -> pd.DataFrame:
    try:
        coord_raw = pd.read_csv(path)
        return prepare_station_coordinates(coord_raw)
    except Exception as e:
        raise RuntimeError(
            f"Gagal membaca '{path}'. Pastikan file ada di root repo dan formatnya CSV. Detail: {e}"
        )

def prepare_station_coordinates(coord_raw: pd.DataFrame) -> pd.DataFrame:
    c = coord_raw.copy()
    req = ["POS HUJAN ID", "NAME", "CURRENT LATITUDE", "CURRENT LONGITUDE", "CURRENT ELEVATION M"]
    missing = [x for x in req if x not in c.columns]
    if missing:
        raise ValueError(f"Kolom wajib pada coords.csv tidak ditemukan: {missing}")

    c = c.rename(columns={
        "POS HUJAN ID": "pos_id",
        "NAME": "name_raw",
        "CURRENT LATITUDE": "lat_raw",
        "CURRENT LONGITUDE": "lon_raw",
        "CURRENT ELEVATION M": "elev_m",
    })

    c["name_raw"] = normalize_station_name(c["name_raw"])
    c["station"] = c["name_raw"].replace(NAME_MAP)
    
    c["lat"] = pd.to_numeric(c["lat_raw"], errors="coerce")
    c["lon"] = pd.to_numeric(c["lon_raw"], errors="coerce")
    c["elev_m"] = pd.to_numeric(c["elev_m"], errors="coerce")

    c["qc_coord_ok"] = c["lat"].notna() & c["lon"].notna()
    c["qc_in_bounds_ntb"] = c["lat"].between(-11.5, -7.0) & c["lon"].between(115.0, 119.5)

    dup_key = c[["lat", "lon"]].round(5).astype(str).agg(",".join, axis=1)
    c["qc_dup_latlon"] = dup_key.duplicated(keep=False) & c["qc_coord_ok"]

    base = pd.DataFrame({"station": HORIZONTAL_COLS})
    out = base.merge(
        c[["station", "pos_id", "lat", "lon", "elev_m", "name_raw", "qc_coord_ok", "qc_in_bounds_ntb", "qc_dup_latlon"]],
        on="station",
        how="left"
    )

    out["qc_flag"] = np.where(out["lat"].notna() & out["lon"].notna(), "OK", "MISSING_COORD")
    out.loc[(out["qc_flag"] == "OK") & (out["qc_in_bounds_ntb"] == False), "qc_flag"] = "OUT_OF_BOUNDS"
    out.loc[(out["qc_flag"] == "OK") & (out["qc_dup_latlon"] == True), "qc_flag"] = "DUP_LATLON"

    return out

# ============================================================
# Indices & Continuous Run Calculations
# ============================================================

def current_run_ending_at_last(series: pd.Series, condition_func, last_day: int):
    """Menghitung run berkesinambungan melintasi dasarian hingga last_day."""
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

def compute_cdd_cwd(wide_num_full: pd.DataFrame, wet_threshold: float = 0.1, dynamic_last_day: int = None):
    """
    Menerima matriks bulanan penuh agar CDD/CWD Current bisa dihitung lintas dasarian.
    """
    num = wide_num_full.drop(columns=["TGL"]).apply(pd.to_numeric, errors="coerce")
    num.index = wide_num_full["TGL"].values
    
    if dynamic_last_day is not None and dynamic_last_day in num.index:
        eval_last_day = int(dynamic_last_day)
    else:
        eval_last_day = int(wide_num_full["TGL"].max())

    rows = []
    for station in num.columns:
        s = num[station]

        cdd_len, cdd_start, cdd_end = longest_run(s, lambda x: float(x) == 0.0)
        cwd_len, cwd_start, cwd_end = longest_run(s, lambda x: float(x) >= float(wet_threshold))

        # Hitung run lintas dasarian yang berakhir di eval_last_day
        cdd_cur_len, cdd_cur_start, cdd_cur_end = current_run_ending_at_last(
            s, lambda x: float(x) == 0.0, eval_last_day
        )
        cwd_cur_len, cwd_cur_start, cwd_cur_end = current_run_ending_at_last(
            s, lambda x: float(x) >= float(wet_threshold), eval_last_day
        )

        if np.isfinite(s.to_numpy()).any():
            ch_max = float(np.nanmax(s.to_numpy()))
            ch_tgl = int(s.idxmax())
        else:
            ch_max = np.nan
            ch_tgl = np.nan

        rows.append({
            "station": station,
            "CDD_len": cdd_len, "CDD_start": cdd_start, "CDD_end": cdd_end,
            "CWD_len": cwd_len, "CWD_start": cwd_start, "CWD_end": cwd_end,
            "CDD_cur_len": cdd_cur_len, "CDD_cur_start": cdd_cur_start, "CDD_cur_end": cdd_cur_end,
            "CWD_cur_len": cwd_cur_len, "CWD_cur_start": cwd_cur_start, "CWD_cur_end": cwd_cur_end,
            "CH_max_mm": ch_max, "CH_max_TGL": ch_tgl,
            "eval_last_day": eval_last_day
        })

    return pd.DataFrame(rows)

def join_names(names, max_show=8):
    names = [str(x) for x in names if pd.notna(x)]
    if len(names) <= max_show:
        return ", ".join(names)
    return ", ".join(names[:max_show]) + f" (+{len(names)-max_show} lagi)"

def to_csv_bytes(df: pd.DataFrame) -> bytes:
    if df is None:
        df = pd.DataFrame()
    return df.to_csv(index=False).encode("utf-8-sig")

def fmt_station_list(df, col_station="station", col_val=None, col_tgl=None):
    stn = df[col_station].astype(str).tolist()
    names_str = join_names(stn)
    if col_val and col_tgl and (col_val in df.columns) and (col_tgl in df.columns):
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
    if selected_das >= 1:
        windows["das1"] = (1, 10)
    if selected_das >= 2:
        windows["das2"] = (11, 20)
    if selected_das >= 3:
        windows["das3"] = (21, last_day)
    windows["monthly"] = (1, last_day)
    return windows

# ============================================================
# Core Standardization & Output Generators
# ============================================================

def build_outputs(df_month_full: pd.DataFrame, month_start: int, month_end: int, win_start: int, win_end: int):
    all_days = np.arange(int(month_start), int(month_end) + 1)
    win_days = np.arange(int(win_start), int(win_end) + 1)

    df_month_full = df_month_full.copy()
    df_month_full["NAME"] = normalize_station_name(df_month_full["NAME"])
    df_month_full["NAME_H"] = df_month_full["NAME"].replace(NAME_MAP)
    
    df_month_full["raw"] = pd.to_numeric(df_month_full["RAINFALL DAY MM"], errors="coerce")
    df_month_full["has_row"] = 1

    df_win = df_month_full[df_month_full["TGL"].between(int(win_start), int(win_end))].copy()

    dup_counts = df_win.groupby(["TGL", "NAME_H"], dropna=False).size().reset_index(name="n_records")
    qc_duplicates = dup_counts[dup_counts["n_records"] > 1].copy()

    if not qc_duplicates.empty:
        src_list = df_win.groupby(["TGL", "NAME_H"])["__source_file__"].apply(lambda s: ", ".join(sorted(set(map(str, s))))).reset_index(name="source_files")
        raw_name_list = df_win.groupby(["TGL", "NAME_H"])["NAME"].apply(lambda s: ", ".join(sorted(set(map(str, s))))).reset_index(name="raw_names")
        ts_list = df_win.groupby(["TGL", "NAME_H"])["DATA TIMESTAMP"].apply(lambda s: ", ".join(sorted(set(map(str, s.astype(str).head(6)))))).reset_index(name="timestamps_sample")
        
        qc_duplicates = (
            qc_duplicates
            .merge(raw_name_list, on=["TGL", "NAME_H"], how="left")
            .merge(src_list, on=["TGL", "NAME_H"], how="left")
            .merge(ts_list, on=["TGL", "NAME_H"], how="left")
            .sort_values(["n_records", "TGL", "NAME_H"], ascending=[False, True, True])
        )

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
        .agg(count=("n", "sum"), source_files=("__source_file__", lambda s: ", ".join(sorted(set(map(str, s))))))
        .sort_values(["count", "NAME"], ascending=[False, True])
    )

    rain_num = df_month_full["raw"].copy()
    rain_num[df_month_full["raw"].isna()] = np.nan
    rain_num[df_month_full["raw"] == 9999] = np.nan
    rain_num[df_month_full["raw"] == 8888] = 0.1
    rain_num[df_month_full["raw"] == 0] = 0.0
    df_month_full["rain_num"] = rain_num

    wide_raw = df_month_full.pivot_table(index="TGL", columns="NAME_H", values="raw", aggfunc="first").reindex(index=all_days, columns=HORIZONTAL_COLS)
    wide_num = df_month_full.pivot_table(index="TGL", columns="NAME_H", values="rain_num", aggfunc="first").reindex(index=all_days, columns=HORIZONTAL_COLS)
    present = df_month_full.pivot_table(index="TGL", columns="NAME_H", values="has_row", aggfunc="first").reindex(index=all_days, columns=HORIZONTAL_COLS)

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
    qc_mapped_not_in_header = df_month_full[df_month_full["NAME_H"].isin(mapped_not_in_horizontal)][["NAME", "NAME_H", "__source_file__"]].drop_duplicates().sort_values(["NAME_H", "NAME"])

    last_present_day = present_win.notna().apply(lambda s: s[s].index.max() if s.any() else np.nan)
    gap_days_since_last = (int(win_end) - last_present_day).where(~last_present_day.isna(), np.nan)
    empty_all_window = present_win.notna().sum(axis=0) == 0

    qc_gap = pd.DataFrame({
        "station": HORIZONTAL_COLS,
        "has_any_record_start_to_end": (~empty_all_window).astype(int).values,
        "last_record_day_in_window": last_present_day.reindex(HORIZONTAL_COLS).values,
        "empty_days_since_last_record": gap_days_since_last.reindex(HORIZONTAL_COLS).values
    })

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
    qc_empty_last_day = qc_empty_last_day[qc_empty_last_day["is_empty_on_last_day"] == 1].copy().sort_values(["empty_days_up_to_last_day", "station"], ascending=[False, True])

    return {
        "wide_bmkg_out": wide_bmkg_out, "wide_num_out": wide_num_out,
        "month_start": int(month_start), "month_end": int(month_end),
        "win_start": int(win_start), "win_end": int(win_end),
        "qc_station": qc_station, "qc_day": qc_day, "qc_gap": qc_gap, "qc_empty_last_day": qc_empty_last_day,
        "qc_duplicates": qc_duplicates, "qc_unknown_names": qc_unknown_names, "qc_mapped_not_in_header": qc_mapped_not_in_header,
        "present_matrix_full": present, "present_matrix_win": present_win,
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
    station_tgl_max = num2.apply(lambda col: col.idxmax() if col.notna().any() else pd.NA).astype("Int64")

    station_dash = (
        pd.DataFrame({
            "station": num.columns,
            "total_mm": station_total.values,
            "valid_days": station_valid_days.values,
            "rainy_days_ge_thr": station_rainy_days.values,
            "heavy_days_ge_thr": station_heavy_days.values,
            "max_mm": station_max.values,
            "tgl_max": station_tgl_max.values,
        })
        .sort_values(["total_mm", "station"], ascending=[False, True])
        .reset_index(drop=True)
    )

    day_total = num.sum(axis=1, skipna=True)
    day_mean = num.mean(axis=1, skipna=True)
    day_valid_stations = num.notna().sum(axis=1)
    day_rainy_stations = (num >= rainy_threshold).sum(axis=1, skipna=True)
    day_heavy_stations = (num >= heavy_threshold).sum(axis=1, skipna=True)

    day_dash = (
        pd.DataFrame({
            "TGL": wide_num_out["TGL"].values,
            "total_mm_all_stations": day_total.values,
            "mean_mm_across_stations": day_mean.values,
            "stations_valid": day_valid_stations.values,
            "stations_rainy_ge_thr": day_rainy_stations.values,
            "stations_heavy_ge_thr": day_heavy_stations.values,
        })
        .sort_values("TGL")
        .reset_index(drop=True)
    )

    arr = num.to_numpy()
    total_mm_all_cells = float(np.nan_to_num(np.nansum(arr)))
    total_valid_cells = int(np.isfinite(arr).sum())
    total_cells = int(arr.size)
    coverage_pct_numeric = round((total_valid_cells / total_cells * 100) if total_cells > 0 else 0, 2)

    wettest_station = station_dash.iloc[0][["station", "total_mm"]].to_dict() if not station_dash.empty else {}
    wettest_day_idx = day_dash["total_mm_all_stations"].idxmax() if not day_dash.empty and day_dash["total_mm_all_stations"].notna().any() else None
    wettest_day = day_dash.loc[wettest_day_idx, ["TGL", "total_mm_all_stations"]].to_dict() if wettest_day_idx is not None else {}

    return station_dash, day_dash, {
        "total_mm_all_cells": total_mm_all_cells,
        "coverage_pct_numeric": coverage_pct_numeric,
        "wettest_station": wettest_station,
        "wettest_day": wettest_day,
    }

# utils.py

@st.cache_data(ttl=300)
def fetch_rainfall_data_timeseries(year: int, month: int, lookback_days: int = 365) -> pd.DataFrame:
    """
    Mengambil data curah hujan dari database Supabase dengan window lookback 365 hari ke belakang
    agar streak CDD/CWD ekstrim (hingga >60-200 hari) dapat dihitung dengan presisi.
    """
    engine = get_db_engine()
    
    # Tanggal akhir bulan target
    target_end_dt = pd.Timestamp(year=year, month=month, day=month_end_day(year, month))
    # Tanggal awal batas lookback (365 hari ke belakang)
    start_dt = target_end_dt - pd.Timedelta(days=lookback_days)
    
    start_str = start_dt.strftime("%Y-%m-%d")
    end_str = target_end_dt.strftime("%Y-%m-%d")

    query = text("""
        SELECT 
            "NAME", 
            "DATA TIMESTAMP"::text AS "RAW_TS", 
            "RAINFALL DAY MM"
        FROM rainfall_data 
        WHERE ("DATA TIMESTAMP" AT TIME ZONE 'UTC')::date BETWEEN :start_str AND :end_str
        ORDER BY "DATA TIMESTAMP" ASC;
    """)
    
    with engine.connect() as conn:
        df = pd.read_sql(query, conn, params={"start_str": start_str, "end_str": end_str})
        
    if df.empty:
        return pd.DataFrame()

    clean_series = (
        df["RAW_TS"]
        .astype(str)
        .str.replace(r'(\+\d{2}(:\d{2})?|Z)$', '', regex=True)
        .str.strip()
    )
    
    df["DATA TIMESTAMP"] = pd.to_datetime(clean_series, format="mixed", errors="coerce")
    df["DATE"] = df["DATA TIMESTAMP"].dt.date
    df["__source_file__"] = "Supabase DB"
    
    return df.drop(columns=["RAW_TS"])

def compute_cdd_cwd_timeseries(df_timeseries: pd.DataFrame, target_year: int, target_month: int, wet_threshold: float = 1.0, eval_until_date=None):
    """
    Menghitung CDD dan CWD secara riil (lintas bulan) menggunakan timeseries harian berlanjut.
    """
    if df_timeseries.empty:
        return pd.DataFrame()

    # Preprocessing & Normalisasi Nama Pos Hujan
    df = df_timeseries.copy()
    df["NAME_H"] = normalize_station_name(df["NAME"]).replace(NAME_MAP)
    
    rain_num = pd.to_numeric(df["RAINFALL DAY MM"], errors="coerce")
    df["rain_num"] = np.where(rain_num == 9999, np.nan, np.where(rain_num == 8888, 0.1, rain_num))

    # Pivot Table dengan Index Tanggal Riil (YYYY-MM-DD)
    pivot_num = df.pivot_table(index="DATE", columns="NAME_H", values="rain_num", aggfunc="first").reindex(columns=HORIZONTAL_COLS)
    pivot_num.index = pd.to_datetime(pivot_num.index)
    pivot_num = pivot_num.sort_index()

    # Tentukan tanggal evaluasi akhir
    if eval_until_date is None:
        eval_until_date = pivot_num.index.max()
    else:
        eval_until_date = pd.to_datetime(eval_until_date)

    # Filter matriks hingga tanggal evaluasi
    pivot_eval = pivot_num.loc[pivot_num.index <= eval_until_date]

    rows = []
    for station in HORIZONTAL_COLS:
        if station not in pivot_eval.columns:
            continue
            
        s = pivot_eval[station]

        # 1. CDD Current Lintas Bulan (Hitung mundur dari eval_until_date)
        cdd_cur_len, cdd_cur_start, cdd_cur_end = 0, None, None
        if not s.empty and eval_until_date in s.index:
            v_last = s.loc[eval_until_date]
            if pd.notna(v_last) and float(v_last) < float(wet_threshold):
                cdd_cur_end = eval_until_date
                cur_dt = eval_until_date
                while cur_dt in s.index:
                    val = s.loc[cur_dt]
                    if pd.isna(val) or float(val) >= float(wet_threshold):
                        break
                    cdd_cur_len += 1
                    cdd_cur_start = cur_dt
                    cur_dt -= pd.Timedelta(days=1)

        # 2. CWD Current Lintas Bulan (Hitung mundur dari eval_until_date)
        cwd_cur_len, cwd_cur_start, cwd_cur_end = 0, None, None
        if not s.empty and eval_until_date in s.index:
            v_last = s.loc[eval_until_date]
            if pd.notna(v_last) and float(v_last) >= float(wet_threshold):
                cwd_cur_end = eval_until_date
                cur_dt = eval_until_date
                while cur_dt in s.index:
                    val = s.loc[cur_dt]
                    if pd.isna(val) or float(val) < float(wet_threshold):
                        break
                    cwd_cur_len += 1
                    cwd_cur_start = cur_dt
                    cur_dt -= pd.Timedelta(days=1)

        # Filter periode khusus bulan target untuk CH Max harian
        target_mask = (s.index.year == target_year) & (s.index.month == target_month)
        s_target = s[target_mask]

        if not s_target.empty and np.isfinite(s_target.to_numpy()).any():
            ch_max = float(np.nanmax(s_target.to_numpy()))
            ch_max_dt = s_target.idxmax()
            ch_tgl = ch_max_dt.day if pd.notna(ch_max_dt) else np.nan
        else:
            ch_max, ch_tgl = np.nan, np.nan

        rows.append({
            "station": station,
            "CDD_cur_len": cdd_cur_len,
            "CDD_cur_start_date": cdd_cur_start.strftime("%d %b %Y") if cdd_cur_start else "-",
            "CWD_cur_len": cwd_cur_len,
            "CWD_cur_start_date": cwd_cur_start.strftime("%d %b %Y") if cwd_cur_start else "-",
            "eval_date": eval_until_date.strftime("%d %b %Y"),
            "CH_max_mm": ch_max,
            "CH_max_TGL": ch_tgl,
        })

    return pd.DataFrame(rows)

def run_quality_control(df_month_win: pd.DataFrame, rainy_thr: float = 1.0, heavy_thr: float = 200.0) -> pd.DataFrame:
    """
    Memeriksa kontrol kualitas data curah hujan:
    1. Data Kosong / Missing Data (NaN, None, 9999)
    2. Nilai Ekstrim / Anomali (> heavy_thr / 200mm)
    3. Nilai Negatif (< 0)
    """
    if df_month_win.empty:
        return pd.DataFrame()

    qc_records = []

    # Iterasi setiap tanggal dan pos hujan
    for idx, row in df_month_win.iterrows():
        tgl = row.get("TGL", np.nan)
        for col in HORIZONTAL_COLS:
            if col not in df_month_win.columns:
                continue
            
            val = row[col]
            
            # --- CEK 1: Data Kosong (Missing Data) ---
            if pd.isna(val) or val == 9999 or str(val).strip() == "":
                qc_records.append({
                    "TGL": tgl,
                    "Station": col,
                    "Nilai": "KOSONG / 9999",
                    "FLAG": "MISSING_DATA",
                    "Keterangan": "Data harian tidak terisi / hilang (Missing Value)"
                })
            else:
                try:
                    num_val = float(val)
                    # --- CEK 2: Nilai Ekstrim ---
                    if num_val > heavy_thr:
                        qc_records.append({
                            "TGL": tgl,
                            "Station": col,
                            "Nilai": num_val,
                            "FLAG": "EXTREME_VALUE",
                            "Keterangan": f"Curah hujan sangat tinggi (> {heavy_thr} mm)"
                        })
                    # --- CEK 3: Nilai Negatif ---
                    elif num_val < 0:
                        qc_records.append({
                            "TGL": tgl,
                            "Station": col,
                            "Nilai": num_val,
                            "FLAG": "INVALID_NEGATIVE",
                            "Keterangan": "Nilai curah hujan negatif"
                        })
                except ValueError:
                    qc_records.append({
                        "TGL": tgl,
                        "Station": col,
                        "Nilai": str(val),
                        "FLAG": "INVALID_FORMAT",
                        "Keterangan": "Format karakter tidak valid"
                    })

    return pd.DataFrame(qc_records)

def compute_data_completeness_summary(wide_num_win: pd.DataFrame) -> dict:
    """
    Menghitung agregasi kelengkapan data nasional/provinsi dan status Pos Completed.
    """
    if wide_num_win.empty:
        return {
            "total_stations": 0,
            "completed_stations_count": 0,
            "incomplete_stations_count": 0,
            "total_expected_records": 0,
            "total_real_records": 0,
            "overall_completeness_pct": 0.0,
            "station_breakdown": pd.DataFrame()
        }

    stations = [c for c in HORIZONTAL_COLS if c in wide_num_win.columns]
    num_days = len(wide_num_win)  # Total hari dalam window
    
    rows = []
    completed_count = 0

    for stn in stations:
        s = wide_num_win[stn]
        
        # Count NaN, empty string, atau kode sandi BMKG 9999
        missing_cnt = int(s.isna().sum() + (s == 9999).sum())
        real_cnt = num_days - missing_cnt
        pct = round((real_cnt / num_days * 100), 1) if num_days > 0 else 0.0
        
        is_completed = (missing_cnt == 0)
        if is_completed:
            completed_count += 1

        rows.append({
            "Station": stn,
            "Expected": num_days,
            "Real": real_cnt,
            "Missing": missing_cnt,
            "Completeness_Pct": pct,
            "Status": "COMPLETED" if is_completed else "INCOMPLETE"
        })

    df_summary = pd.DataFrame(rows)
    
    tot_exp = len(stations) * num_days
    tot_real = int(df_summary["Real"].sum()) if not df_summary.empty else 0
    overall_pct = round((tot_real / tot_exp * 100), 1) if tot_exp > 0 else 0.0

    return {
        "total_stations": len(stations),
        "completed_stations_count": completed_count,
        "incomplete_stations_count": len(stations) - completed_count,
        "total_expected_records": tot_exp,
        "total_real_records": tot_real,
        "overall_completeness_pct": overall_pct,
        "station_breakdown": df_summary
    }