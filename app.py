# app.py (Bagian Atas)

import streamlit as st
import pandas as pd
import numpy as np
from datetime import date
import pydeck as pdk

from config import HORIZONTAL_COLS, NAME_MAP
from utils import (
    insert_rainfall_data,
    fetch_rainfall_data_from_db,
    fetch_rainfall_data_timeseries,
    compute_cdd_cwd_timeseries,
    get_latest_db_record_info,
    month_end_day,
    normalize_station_name,
    load_coords_from_repo,
    prepare_station_coordinates,
    compute_cdd_cwd,
    join_names,
    to_csv_bytes,
    fmt_station_list,
    dasarian_windows_to_build,
    build_outputs,
    build_dashboard,
    compute_data_completeness_summary,
    run_quality_control,
)

st.set_page_config(
    page_title="SEGARA: Sistem Ekspor dan Generator Analisis Dasarian",
    layout="wide"
)

st.title("SEGARA: Sistem Ekspor dan Generator Analisis Dasarian")
st.caption(
    "Platform kontrol kualitas dan pemrosesan data pos hujan dasarian BMKG Stasiun Klimatologi Nusa Tenggara Barat: "
    "validasi otomatis, rekapitulasi, analisis indeks iklim, dan visualisasi spasial."
)

# Deskripsi Program & Pembuat
with st.expander("ℹ️ Informasi Program & Pengembang", expanded=False):
    st.markdown(
        """
        **Tentang SEGARA**  
        SEGARA dirancang untuk mengotomatisasi rantai kerja pengawasan mutu (*quality control*), pemantauan kelengkapan data harian/dasarian, 
        perhitungan indeks iklim, hingga pembuatan visualisasi spasial interaktif untuk jaringan pos hujan di Nusa Tenggara Barat.

        **Pengembang**  
        * **Developer:** Cakra Mahasurya Atmojo Pamungkas  
        * **Instansi:** BMKG Stasiun Klimatologi Nusa Tenggara Barat  
        * **Tim:** Tim Analisis
        """
    )

# ============================================================
# Navigation & Session state init
# ============================================================
PAGES = ["Input", "Hasil", "QC", "Tabel", "Grafik", "Peta", "Download"]

st.session_state.setdefault("page", "Input")

def goto(page: str):
    st.session_state["page"] = page if page in PAGES else "Input"

st.session_state.setdefault("outputs", None)
st.session_state.setdefault("meta", None)
st.session_state.setdefault("derived", None)

if "coords_final" not in st.session_state:
    st.session_state["coords_final"] = load_coords_from_repo("coords.csv")

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

    order = [k for k in ["das1", "das2", "das3", "monthly"] if k in windows]
    labels = {k: windows[k]["label"] for k in order}

    default_key = st.session_state.get("view_window", order[0])
    if default_key not in order:
        default_key = order[0]

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

    data_source = st.radio(
        "Pilih Sumber Data:",
        options=["Database Supabase (Online)", "Upload File CSV Vertikal"],
        horizontal=True,
        key="data_source_mode"
    )

    cA, cB, cC = st.columns([1, 1, 1.2])
    today = date.today()
    with cA:
        year = st.number_input("Year", min_value=2000, max_value=2100, value=int(today.year), step=1)
    with cB:
        month = st.selectbox("Month", options=[f"{i:02d}" for i in range(1, 13)], index=int(today.month) - 1)
    
    # INFO STATUS DATA BASE SEBELUM RUN
    if data_source == "Database Supabase (Online)":
        db_info = get_latest_db_record_info(int(year), int(month))
        if db_info:
            st.success(
                f"📊 **Status Database Saat Ini ({year}-{month})**: "
                f"Data Terakhir = **{db_info['latest_ts']} (TGL {db_info['latest_day']})** | "
                f"Total Records = **{db_info['total_records']}** | "
                f"Jumlah Stasiun = **{db_info['total_stations']}**"
            )
            # Auto select dasarian default based on DB last record
            default_das_idx = 0 if db_info['latest_day'] <= 10 else (1 if db_info['latest_day'] <= 20 else 2)
        else:
            st.warning(f"⚠️ Belum ada data di database Supabase untuk periode {year}-{month}.")
            default_das_idx = 0
    else:
        default_das_idx = 0

    up_rain = None
    if data_source == "Upload File CSV Vertikal":
        up_rain = st.file_uploader(
            "Upload CSV vertikal (curah hujan)",
            type=["csv"],
            accept_multiple_files=True,
            key="uploader_rain"
        )
        
        # Fitur Push/Insert ke Supabase jika file diupload
        if up_rain and st.button("💾 Push / Save Uploaded CSV to Supabase DB", type="secondary"):
            with st.spinner("Memproses dan menyimpan data ke Supabase PostgreSQL..."):
                try:
                    # Gabungkan file jika multi upload
                    dfs_to_push = [read_csv_robust(f) for f in up_rain]
                    df_push = pd.concat(dfs_to_push, ignore_index=True)
                    rows_added = insert_rainfall_data(df_push)
                    st.success(f"Berhasil menambahkan {rows_added} baris data baru ke database Supabase!")
                except Exception as e:
                    st.error(f"Gagal melakukan simpan ke database: {e}")

    with cC:
        dasarian = st.radio(
            "Dasarian Target Analysis",
            options=["1", "2", "3"],
            format_func=lambda x: (
                "Das 1 (1–10)" if x == "1" else
                ("Das 2 (11–20)" if x == "2" else "Das 3 (21–akhir bulan)")
            ),
            index=default_das_idx,
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

    if run:
        YEAR = int(year)
        MM = str(month)
        MONTH_INT = int(MM)
        MONTH_STR = f"{YEAR}-{MM}"
        das_n = int(dasarian)

        # ------------------------------------------------------------
        # 1. Pengambilan Data dari Supabase (Online) atau CSV Upload
        # ------------------------------------------------------------
        # app.py (di dalam blok if run:)

        if data_source == "Database Supabase (Online)":
            with st.spinner("Mengambil data timeseries 365 hari ke belakang dari Supabase..."):
                try:
                    # Tarik data dengan lookback 365 hari
                    df_ts = fetch_rainfall_data_timeseries(YEAR, MONTH_INT, lookback_days=365)
                    df = fetch_rainfall_data_from_db(YEAR, MONTH_INT)
                except Exception as e:
                    st.error(f"Gagal mengambil data dari Supabase: {e}")
                    st.stop()
                
                if df.empty:
                    st.error(f"Tidak ada data tersimpan di Supabase untuk periode {MONTH_STR}.")
                    st.stop()
        else:
            if not up_rain:
                st.error("Upload file CSV vertikal curah hujan terlebih dahulu.")
                st.stop()

            def read_csv_robust(uploaded_file) -> pd.DataFrame:
                attempts = [
                    (",", "utf-8"), (";", "utf-8"), ("\t", "utf-8"),
                    (",", "utf-8-sig"), (";", "utf-8-sig"), (",", "latin1")
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

            dfs, bad_files = [], []
            for f in up_rain:
                try:
                    tmp = read_csv_robust(f)
                    tmp["__source_file__"] = f.name
                    dfs.append(tmp)
                except Exception as e:
                    bad_files.append(f.name)

            if not dfs:
                st.error("Tidak ada file curah hujan valid untuk diproses.")
                st.stop()

            df = pd.concat(dfs, ignore_index=True)
            df_ts = df.copy()

        # ------------------------------------------------------------
        # 2. Validasi & Sanitasi Data Bulan Target
        # ------------------------------------------------------------
        required_cols = ["NAME", "DATA TIMESTAMP", "RAINFALL DAY MM"]
        missing_cols = [c for c in required_cols if c not in df.columns]
        if missing_cols:
            st.error(f"Kolom wajib tidak ditemukan: {missing_cols}")
            st.stop()
    
        ts_clean = (
            df["DATA TIMESTAMP"]
            .astype(str)
            .str.replace(r'(\+\d{2}(:\d{2})?|Z)$', '', regex=True)
            .str.strip()
        )
        df["DATA TIMESTAMP"] = pd.to_datetime(ts_clean, format="mixed", errors="coerce")
        df = df[df["DATA TIMESTAMP"].notna()].copy()
    
        df_month = df[df["DATA TIMESTAMP"].dt.strftime("%Y-%m") == MONTH_STR].copy()
        if df_month.empty:
            st.error(f"Tidak ada baris untuk {MONTH_STR}. Periksa pilihan bulan atau data.")
            st.stop()
    
        df_month["TGL"] = df_month["DATA TIMESTAMP"].dt.day
        last_day = month_end_day(YEAR, MONTH_INT)
        df_month_full = df_month[df_month["TGL"].between(1, last_day)].copy()

        # Deteksi tanggal data TERAKHIR yang ada di database untuk bulan ini
        latest_db_day = int(df_month_full["TGL"].max())

        # ------------------------------------------------------------
        # 3. Kalkulasi Window Dasarian & Continuous Index Lintas Bulan
        # ------------------------------------------------------------
        windows_def = dasarian_windows_to_build(YEAR, MONTH_INT, das_n)
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
            
            # Hitung CDD/CWD Lintas Bulan secara Real Continuous Timeseries
            if data_source == "Database Supabase (Online)":
                if key == "monthly":
                    eval_day = min(latest_db_day, last_day)
                else:
                    eval_day = min(int(win_end), latest_db_day)
                    
                eval_dt = pd.Timestamp(year=YEAR, month=MONTH_INT, day=eval_day)
                
                cdd = compute_cdd_cwd_timeseries(
                    df_ts, 
                    target_year=YEAR, 
                    target_month=MONTH_INT, 
                    wet_threshold=rainy_thr, 
                    eval_until_date=eval_dt
                )
            else:
                cdd = compute_cdd_cwd(wide_num_full, wet_threshold=rainy_thr, dynamic_last_day=latest_db_day)
    
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
    
        # ------------------------------------------------------------
        # 4. Update Session State & Transisi Halaman
        # ------------------------------------------------------------
        st.session_state["meta"] = {
            "MONTH_STR": MONTH_STR,
            "YEAR": YEAR,
            "MM": MM,
            "last_day": int(last_day),
            "latest_db_day": int(latest_db_day),
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
# PAGE: Hasil
# ============================================================
elif st.session_state["page"] == "Hasil":
    require_results()

    meta = st.session_state.get("meta", {}) or {}
    window_selector_ui()
    bundle = get_active_bundle()
    if bundle is None:
        st.info("Window belum tersedia. Silakan Run ulang.")
        st.stop()

    MONTH_STR = str(meta.get("MONTH_STR", "UNKNOWN"))
    last_day = int(meta.get("last_day", 0) or 0)
    latest_db_day = int(meta.get("latest_db_day", last_day))
    rainy_thr = float(meta.get("rainy_thr", 1.0))
    heavy_thr = float(meta.get("heavy_thr", 20.0))

    win_label = str(bundle.get("label", "Window"))
    start_day = int(bundle.get("start_day", 1))
    end_day = int(bundle.get("end_day", start_day))

    outputs = bundle.get("outputs", {}) or {}
    station_dash = bundle.get("station_dash", pd.DataFrame())
    day_dash = bundle.get("day_dash", pd.DataFrame())
    hi = bundle.get("hi", {}) or {}
    cdd_cwd_df = bundle.get("cdd_cwd_df", pd.DataFrame())

    st.subheader("Dashboard Analisis Operasional SEGARA")
    
    # KOTAK STATUS UTAMA
    st.markdown(
        f"""
        <div style="background-color: #f0f2f6; padding: 12px 18px; border-radius: 8px; margin-bottom: 15px;">
            <span style="font-size: 16px;"><b>Periode:</b> {MONTH_STR} | <b>Tampilan Window:</b> {win_label} | <b>Data Terakhir Evaluasi:</b> TGL {latest_db_day}</span><br/>
            <span style="font-size: 13px; color: #555;">💡 <i><b>CDD/CWD Current:</b> Menghitung durasi berurutan yang benar-benar berlanjut melintasi batas dasarian dan bulan hingga data posisi terakhir.</i></span>
        </div>
        """, 
        unsafe_allow_html=True
    )

    def _num(s):
        return pd.to_numeric(s, errors="coerce")

    def _safe_df(x):
        return x if isinstance(x, pd.DataFrame) else pd.DataFrame()

    station_dash = _safe_df(station_dash)
    day_dash = _safe_df(day_dash)
    cdd_cwd_df = _safe_df(cdd_cwd_df)

    cdd_cur_best_len, cdd_cur_names, cdd_cur_rng = 0, "", ""
    cwd_cur_best_len, cwd_cur_names, cwd_cur_rng = 0, "", ""

    if not cdd_cwd_df.empty:
        tmp_all = cdd_cwd_df.copy()

        # ------------------------------------------------------------
        # 1. CDD Current (Hari Kering Berlanjut Lintas Bulan)
        # ------------------------------------------------------------
        if "CDD_cur_len" in tmp_all.columns:
            tmp = tmp_all.copy()
            tmp["CDD_cur_len"] = _num(tmp["CDD_cur_len"]).fillna(0).astype(int)
            best_len = int(tmp["CDD_cur_len"].max()) if len(tmp) else 0
            if best_len > 0:
                best = tmp[tmp["CDD_cur_len"] == best_len].copy().sort_values("station")
                cdd_cur_best_len = best_len
                cdd_cur_names = join_names(best["station"].tolist())
                
                # Format Tanggal: Prioritaskan Format Lintas Bulan (CDD_cur_start_date)
                if "CDD_cur_start_date" in best.columns and best["CDD_cur_start_date"].notna().any():
                    first_start = str(best["CDD_cur_start_date"].iloc[0])
                    cdd_cur_rng = f"{cdd_cur_best_len} hari (sejak {first_start})"
                else:
                    starts = _num(best.get("CDD_cur_start", pd.Series()))
                    cdd_start_min = int(np.nanmin(starts)) if starts.notna().any() else 1
                    cdd_cur_rng = f"{cdd_cur_best_len} hari (TGL {cdd_start_min}–{latest_db_day})"

        # ------------------------------------------------------------
        # 2. CWD Current (Hari Basah Berlanjut Lintas Bulan)
        # ------------------------------------------------------------
        if "CWD_cur_len" in tmp_all.columns:
            tmp = tmp_all.copy()
            tmp["CWD_cur_len"] = _num(tmp["CWD_cur_len"]).fillna(0).astype(int)
            best_len = int(tmp["CWD_cur_len"].max()) if len(tmp) else 0
            if best_len > 0:
                best = tmp[tmp["CWD_cur_len"] == best_len].copy().sort_values("station")
                cwd_cur_best_len = best_len
                cwd_cur_names = join_names(best["station"].tolist())
                
                # Format Tanggal: Prioritaskan Format Lintas Bulan (CWD_cur_start_date)
                if "CWD_cur_start_date" in best.columns and best["CWD_cur_start_date"].notna().any():
                    first_start = str(best["CWD_cur_start_date"].iloc[0])
                    cwd_cur_rng = f"{cwd_cur_best_len} hari (sejak {first_start})"
                else:
                    starts = _num(best.get("CWD_cur_start", pd.Series()))
                    cwd_start_min = int(np.nanmin(starts)) if starts.notna().any() else 1
                    cwd_cur_rng = f"{cwd_cur_best_len} hari (TGL {cwd_start_min}–{latest_db_day})"

    # ------------------------------------------------------------
    # 3. Pos Terbasah & Pos Terkering dalam Window Tampilan
    # ------------------------------------------------------------
    wet_total, wet_names, wet_n = np.nan, "", 0
    dry_total, dry_names, dry_n = np.nan, "", 0

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

    ch_max_val, ch_max_names = np.nan, ""
    if (not cdd_cwd_df.empty) and ("CH_max_mm" in cdd_cwd_df.columns):
        tmp = cdd_cwd_df.copy()
        tmp["CH_max_mm"] = _num(tmp["CH_max_mm"])
        if tmp["CH_max_mm"].notna().any():
            ch_max_val = float(tmp["CH_max_mm"].max())
            top = tmp[tmp["CH_max_mm"] == ch_max_val].copy().sort_values("station")
            ch_max_names, _ = fmt_station_list(top, col_station="station", col_val="CH_max_mm", col_tgl="CH_max_TGL")

    # ------------------------------------------------------------
    # 4. Panel Metrik Kondisi Terkini
    # ------------------------------------------------------------
    st.markdown("### 📌 Summary & Kondisi Terkini")
    m1, m2, m3, m4 = st.columns(4)
    
    m1.metric(
        label="CWD Current Terpanjang",
        value=cwd_cur_names if cwd_cur_names else "-",
        delta=cwd_cur_rng if cwd_cur_rng else "0 hari"
    )
    
    m2.metric(
        label="CDD Current Terpanjang",
        value=cdd_cur_names if cdd_cur_names else "-",
        delta=cdd_cur_rng if cdd_cur_rng else "0 hari",
        delta_color="inverse"
    )

    m3.metric(
        label=f"Pos Terbasah ({win_label})",
        value=wet_names if wet_names else "-",
        delta=f"{wet_total:.1f} mm" if np.isfinite(wet_total) else "0 mm"
    )

    m4.metric(
        label=f"CH Max Harian ({win_label})",
        value=ch_max_names if ch_max_names else "-",
        delta=f"{ch_max_val:.1f} mm" if np.isfinite(ch_max_val) else "0 mm"
    )

    st.markdown("---")

    # ------------------------------------------------------------
    # 5. Tabel Detail Kondisi Terkini Lintas Bulan / Dasarian
    # ------------------------------------------------------------
    st.subheader(f"⚡ Detail Kondisi Terkini (Evaluasi s.d. TGL {latest_db_day})")
    
    if not cdd_cwd_df.empty:
        tmp_cur = cdd_cwd_df.copy()
        tmp_cur["CDD_cur_len"] = _num(tmp_cur.get("CDD_cur_len", 0)).fillna(0).astype(int)
        tmp_cur["CWD_cur_len"] = _num(tmp_cur.get("CWD_cur_len", 0)).fillna(0).astype(int)

        tmp_cdd_cur = tmp_cur[tmp_cur["CDD_cur_len"] > 0].sort_values(["CDD_cur_len", "station"], ascending=[False, True]).head(15).copy()
        tmp_cwd_cur = tmp_cur[tmp_cur["CWD_cur_len"] > 0].sort_values(["CWD_cur_len", "station"], ascending=[False, True]).head(15).copy()

        c1, c2 = st.columns(2)
        with c1:
            st.caption(f"🔥 Top 15 Wet Spells (CWD Current Berlanjut s.d. TGL {latest_db_day})")
            cols_cwd = [c for c in ["station", "CWD_cur_len", "CWD_cur_start_date", "CWD_cur_start", "CWD_cur_end", "CH_max_mm"] if c in tmp_cwd_cur.columns]
            st.dataframe(tmp_cwd_cur[cols_cwd], use_container_width=True, height=380)

        with c2:
            st.caption(f"☀️ Top 15 Dry Spells (CDD Current Berlanjut s.d. TGL {latest_db_day})")
            cols_cdd = [c for c in ["station", "CDD_cur_len", "CDD_cur_start_date", "CDD_cur_start", "CDD_cur_end", "CH_max_mm"] if c in tmp_cdd_cur.columns]
            st.dataframe(tmp_cdd_cur[cols_cdd], use_container_width=True, height=380)

    st.markdown("---")

    # ------------------------------------------------------------
    # 6. Grafik Tren & Akumulasi Harian
    # ------------------------------------------------------------
    gL, gR = st.columns([1.2, 0.8])

    with gL:
        if (not day_dash.empty) and ("TGL" in day_dash.columns):
            st.subheader(f"📈 Tren Harian ({win_label})")
            if "total_mm_all_stations" in day_dash.columns:
                st.line_chart(day_dash[["TGL", "total_mm_all_stations"]].set_index("TGL"))

    with gR:
        st.subheader(f"🏆 Akumulasi Pos ({win_label})")
        if not station_dash.empty:
            st.dataframe(station_dash[["station", "total_mm", "valid_days"]].head(15), use_container_width=True, height=380)

# ============================================================
# PAGE: QC
# ============================================================
elif st.session_state["page"] == "QC":
    require_results()

    meta = st.session_state.get("meta", {}) or {}
    window_selector_ui()
    bundle = get_active_bundle()
    if bundle is None:
        st.info("Window belum tersedia. Silakan Run ulang dari menu Input.")
        st.stop()

    win_label = str(bundle.get("label", "Window"))
    outputs = bundle.get("outputs", {}) or {}
    
    # Ambil wide numeric matrix untuk perhitungan completeness
    wide_num_win = outputs.get("wide_num_out", pd.DataFrame())

    # Ambil dataframe QC dari outputs (dengan fallback key lookup)
    qc_df = outputs.get("qc_df")
    if qc_df is None:
        qc_df = outputs.get("qc_report")
    if qc_df is None:
        qc_df = outputs.get("qc", pd.DataFrame())

    st.subheader(f"🔍 Kontrol Kualitas Data (Quality Control) - {win_label}")

    # ------------------------------------------------------------
    # 1. METRIK UTAMA & HASIL TEMUAN QC ANOMALI
    # ------------------------------------------------------------
    if isinstance(qc_df, pd.DataFrame) and not qc_df.empty:
        total_anomali = len(qc_df)
        
        # Hitung spesifik temuan Data Kosong vs Ekstrim
        missing_count = len(qc_df[qc_df["FLAG"] == "MISSING_DATA"]) if "FLAG" in qc_df.columns else 0
        extreme_count = len(qc_df[qc_df["FLAG"] == "EXTREME_VALUE"]) if "FLAG" in qc_df.columns else 0

        # Dashboard Card Ringkasan Temuan Anomali
        k1, k2, k3 = st.columns(3)
        k1.metric("Total Temuan QC", f"{total_anomali} Catatan")
        k2.metric(
            "Data Kosong / Missing (9999)", 
            f"{missing_count} Pos-Hari", 
            delta="Perlu Diisi/Interpolasi" if missing_count > 0 else "Lengkap", 
            delta_color="inverse"
        )
        k3.metric(
            "Nilai Ekstrim (>200mm)", 
            f"{extreme_count} Pos-Hari", 
            delta="Verifikasi Manual" if extreme_count > 0 else "Normal", 
            delta_color="off"
        )

        st.markdown("---")

        # Tampilkan Breakdown per Jenis FLAG
        if "FLAG" in qc_df.columns:
            flag_counts = qc_df["FLAG"].value_counts().reset_index()
            flag_counts.columns = ["Jenis Anomali / Flag", "Jumlah Incident"]
            
            q1, q2 = st.columns([1, 2])
            with q1:
                st.caption("📊 Distribution QC Flags")
                st.dataframe(flag_counts, use_container_width=True)
            with q2:
                st.caption("📋 Detail Riwayat Anomali QC")
                st.dataframe(qc_df, use_container_width=True, height=350)
        else:
            st.dataframe(qc_df, use_container_width=True, height=350)

        # Download Report
        csv_qc = to_csv_bytes(qc_df)
        st.download_button(
            label="📥 Download Laporan Anomali QC (CSV)",
            data=csv_qc,
            file_name=f"Laporan_QC_SEGARA_{meta.get('MONTH_STR', 'periode')}.csv",
            mime="text/csv"
        )
    else:
        st.success("🎉 Tidak ditemukan data anomali atau nilai ekstrim (Data Passed Anomaly Checks).")

    st.markdown("---")

    # ------------------------------------------------------------
    # 2. ANALISIS KELENGKAPAN DATA (DATA COMPLETENESS & POS COMPLETED)
    # ------------------------------------------------------------
    st.subheader(f"📊 Quality Control & Data Completeness - {win_label}")
    
    comp_summary = compute_data_completeness_summary(wide_num_win)

    # Panel Card KPI Completeness
    k1, k2, k3, k4 = st.columns(4)

    k1.metric(
        label="Data Completeness Rate",
        value=f"{comp_summary['overall_completeness_pct']}%",
        delta=f"{comp_summary['total_real_records']} / {comp_summary['total_expected_records']} Record",
        delta_color="normal" if comp_summary['overall_completeness_pct'] >= 90 else "inverse"
    )

    k2.metric(
        label="Pos Completed (100%)",
        value=f"{comp_summary['completed_stations_count']} Pos",
        delta=f"Dari total {comp_summary['total_stations']} pos",
        delta_color="normal"
    )

    k3.metric(
        label="Pos Incomplete (<100%)",
        value=f"{comp_summary['incomplete_stations_count']} Pos",
        delta="Perlu Pengisian" if comp_summary['incomplete_stations_count'] > 0 else "Lengkap",
        delta_color="inverse" if comp_summary['incomplete_stations_count'] > 0 else "normal"
    )

    k4.metric(
        label="Total Record Missing",
        value=f"{comp_summary['total_expected_records'] - comp_summary['total_real_records']}",
        delta="Missing / 9999",
        delta_color="off"
    )

    st.markdown("<br/>", unsafe_allow_html=True)

    # Filter Tab: All vs Incomplete vs Completed
    tab_all, tab_incomplete, tab_completed = st.tabs(["🌐 Semua Pos Hujan", "⚠️ Pos Incomplete", "✅ Pos Completed"])

    df_breakdown = comp_summary.get("station_breakdown", pd.DataFrame())

    if not df_breakdown.empty:
        with tab_all:
            st.dataframe(df_breakdown, use_container_width=True, height=350)

        with tab_incomplete:
            df_inc = df_breakdown[df_breakdown["Status"] == "INCOMPLETE"].sort_values("Completeness_Pct")
            if not df_inc.empty:
                st.dataframe(df_inc, use_container_width=True, height=350)
            else:
                st.success("🎉 Seluruh pos hujan telah COMPLETED 100%.")

        with tab_completed:
            df_comp = df_breakdown[df_breakdown["Status"] == "COMPLETED"]
            st.dataframe(df_comp, use_container_width=True, height=350)
    else:
        st.info("Data breakdown pos hujan belum tersedia.")

# ============================================================
# PAGE: Tabel
# ============================================================
elif st.session_state["page"] == "Tabel":
    require_results()

    meta = st.session_state["meta"]
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
        options=["FORMAT BMKG (x / - / 0 / angka)", "NUMERIC (NaN / 0.1 / angka)"],
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

    cdd_cwd_df = bundle.get("cdd_cwd_df")
    if cdd_cwd_df is None:
        cdd_cwd_df = st.session_state.get("derived", {}).get("cdd_cwd_df", pd.DataFrame())

    st.subheader("Grafik curah hujan harian per pos")
    st.write(f"Periode: **{MONTH_STR}** | Tampilan: **{win_label}** | Rentang: **TGL {start_day}–{end_day}**")

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

    dfp = wide_num_out[["TGL"] + selected].copy()
    for c in selected:
        dfp[c] = pd.to_numeric(dfp[c], errors="coerce")

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
# PAGE: Peta
# ============================================================
elif st.session_state["page"] == "Peta":
    st.subheader("Peta interaktif stasiun (hover untuk tooltip)")

    coords_final = st.session_state["coords_final"].copy()

    if st.session_state.get("outputs") is not None:
        window_selector_ui()
        bundle = get_active_bundle()
    else:
        bundle = None

    if bundle is not None:
        outputs = bundle.get("outputs", {})
        station_dash = bundle.get("station_dash", pd.DataFrame())
        cdd_cwd_df = bundle.get("cdd_cwd_df", pd.DataFrame())

        qc_station = outputs.get("qc_station", pd.DataFrame())
        if isinstance(qc_station, pd.DataFrame) and (not qc_station.empty) and ("station" in qc_station.columns):
            qc_station = qc_station[["station", "completeness_pct"]].copy() if "completeness_pct" in qc_station.columns else qc_station[["station"]].copy()
        else:
            qc_station = pd.DataFrame(columns=["station", "completeness_pct"])

        if not (isinstance(station_dash, pd.DataFrame) and (not station_dash.empty)):
            station_dash = pd.DataFrame(columns=["station", "total_mm", "max_mm", "tgl_max"])
        else:
            keep_sd = [c for c in ["station", "total_mm", "max_mm", "tgl_max"] if c in station_dash.columns]
            station_dash = station_dash[keep_sd].copy()

        if not (isinstance(cdd_cwd_df, pd.DataFrame) and (not cdd_cwd_df.empty)):
            cdd_cwd_df = pd.DataFrame(columns=[
                "station", "CDD_len", "CWD_len", "CDD_cur_len", "CWD_cur_len", "CH_max_mm", "CH_max_TGL"
            ])
        else:
            keep_idx = [c for c in [
                "station", "CDD_len", "CWD_len", "CDD_cur_len", "CWD_cur_len", "CH_max_mm", "CH_max_TGL"
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

    c1, c2, c3, c4 = st.columns([1, 1, 1.1, 1.2])
    with c1:
        hide_missing = st.checkbox("Sembunyikan stasiun tanpa koordinat", value=True, key="map_hide_missing")
    with c2:
        show_only_bad = st.checkbox("Hanya QC koordinat bermasalah", value=False, key="map_show_only_bad")
    with c3:
        point_size = st.slider("Ukuran titik", min_value=3, max_value=18, value=9, step=1, key="map_point_size")
    with c4:
        mode = st.radio("Mode peta", options=["Titik (Scatter)", "Heatmap (nilai layer)"], index=0, horizontal=True, key="map_mode")

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
            "QC Koordinat (flag)", "Kelengkapan data (completeness_pct)",
            "Akumulasi window (total_mm)", "CDD terpanjang (CDD_len)",
            "CWD terpanjang (CWD_len)", "CDD terkini (CDD_cur_len)",
            "CWD terkini (CWD_cur_len)", "CH maksimum (CH_max_mm)"
        ],
        key="map_layer"
    )

    left, right = st.columns([4.2, 1.3])
    with left:
        st.markdown("### Map")
    with right:
        st.markdown("### Legend")

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

            q0, q25, q50, q75, q100 = float(np.nanmin(s)), float(np.nanpercentile(s, 25)), float(np.nanpercentile(s, 50)), float(np.nanpercentile(s, 75)), float(np.nanmax(s))

            st.markdown(
                """
<div style="height:12px;border-radius:6px;border:1px solid #bbb;
background: linear-gradient(90deg, rgb(60,80,220), rgb(240,80,40));">
</div>
""",
                unsafe_allow_html=True
            )
            st.write(pd.DataFrame({"min": [q0], "p25": [q25], "median": [q50], "p75": [q75], "max": [q100]}))

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

    if metric_col == "qc_flag":
        plot_df["__color__"] = plot_df["qc_flag"].apply(qc_to_rgb)
    else:
        plot_df[metric_col] = pd.to_numeric(plot_df.get(metric_col), errors="coerce")
        vmin, vmax = plot_df[metric_col].min(skipna=True), plot_df[metric_col].max(skipna=True)
        plot_df["__color__"] = plot_df[metric_col].apply(lambda v: value_to_rgb(v, vmin, vmax))

    if metric_col == "qc_flag":
        render_qc_legend(right)
    else:
        render_continuous_legend(right, plot_df[metric_col], metric_label)

    tooltip_html = (
        "<b>{station}</b><br/>"
        "POS: {pos_id}<br/>"
        "Lat/Lon: {lat}, {lon}<br/>"
        "QC: {qc_flag}<br/>"
    )
    if metric_col is not None:
        tooltip_html += f"{metric_label}: " + "{" + metric_col + "}<br/>"

    tooltip = {"html": tooltip_html, "style": {"backgroundColor": "white", "color": "black"}}

    center_lat = float(plot_df["lat"].median())
    center_lon = float(plot_df["lon"].median())
    view_state = pdk.ViewState(latitude=center_lat, longitude=center_lon, zoom=8.2, pitch=0)

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

    with left:
        st.pydeck_chart(pdk.Deck(layers=layers, initial_view_state=view_state, tooltip=tooltip, map_style=None))

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

    meta = st.session_state.get("meta", {}) or {}

    st.subheader("Download")
    window_selector_ui()
    bundle = get_active_bundle()
    if bundle is None:
        st.info("Bundle window tidak ditemukan. Silakan Run ulang di halaman Input.")
        st.stop()

    win_label = str(bundle.get("label", "Window"))
    start_day = int(bundle.get("start_day", 1))
    end_day = int(bundle.get("end_day", start_day))

    outputs = bundle.get("outputs", {}) or {}
    station_dash = bundle.get("station_dash", pd.DataFrame())
    day_dash = bundle.get("day_dash", pd.DataFrame())
    cdd_cwd_df = bundle.get("cdd_cwd_df", pd.DataFrame())

    wide_bmkg_out = outputs.get("wide_bmkg_out")
    wide_num_out = outputs.get("wide_num_out")
    if wide_bmkg_out is None or wide_num_out is None:
        st.warning("Output utama tidak ditemukan pada window ini. Silakan Run ulang di halaman Input.")
        st.stop()

    qc_station = outputs.get("qc_station", pd.DataFrame())
    qc_day = outputs.get("qc_day", pd.DataFrame())
    qc_gap = outputs.get("qc_gap", pd.DataFrame())
    qc_empty_last_day = outputs.get("qc_empty_last_day", pd.DataFrame())

    qc_duplicates = outputs.get("qc_duplicates", pd.DataFrame())
    qc_unknown_names = outputs.get("qc_unknown_names", pd.DataFrame())
    qc_mapped_not_in_header = outputs.get("qc_mapped_not_in_header", pd.DataFrame())

    qc_unmapped = outputs.get("qc_unmapped", qc_mapped_not_in_header)

    coords_final = st.session_state.get("coords_final")
    coords_final = coords_final.copy() if isinstance(coords_final, pd.DataFrame) else pd.DataFrame()

    MONTH_STR = str(meta.get("MONTH_STR", "UNKNOWN"))
    view_key = str(st.session_state.get("view_window", "window")).lower()

    st.caption(f"Window aktif: **{win_label}** (TGL {start_day}–{end_day}) | Periode: **{MONTH_STR}**")

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

    download_choice = st.selectbox(
        "Pilih file yang ingin di-download",
        [
            fname_bmkg, fname_num, "— QC —", fname_qc_station,
            fname_qc_day, fname_qc_unmapped, fname_qc_gap, fname_qc_empty_last,
            fname_qc_duplicates, fname_qc_unknown, "— Ringkasan —",
            summary_station_name, summary_day_name, summary_cdd_cwd_name,
            "— Referensi —", coords_name,
        ],
        index=0
    )

    if str(download_choice).startswith("—"):
        st.info("Pilih item file (bukan header pemisah).")
        st.stop()

    download_map = {
        fname_bmkg: wide_bmkg_out, fname_num: wide_num_out,
        fname_qc_station: qc_station, fname_qc_day: qc_day,
        fname_qc_unmapped: qc_unmapped, fname_qc_gap: qc_gap,
        fname_qc_empty_last: qc_empty_last_day, fname_qc_duplicates: qc_duplicates,
        fname_qc_unknown: qc_unknown_names, summary_station_name: station_dash,
        summary_day_name: day_dash, summary_cdd_cwd_name: cdd_cwd_df,
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

    st.download_button(
        label=f"Download: {download_choice}",
        data=to_csv_bytes(df_dl),
        file_name=download_choice,
        mime="text/csv",
        use_container_width=True
    )

    with st.expander("Preview (10 baris pertama)", expanded=False):
        st.dataframe(df_dl.head(10), use_container_width=True, height=320)