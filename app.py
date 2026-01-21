import streamlit as st
import pandas as pd
import numpy as np

# ----------------------------
# HARD CODE: station order + mapping
# ----------------------------
HORIZONTAL_COLS = [ ... ]   # paste your full list
NAME_MAP = { ... }          # paste your full dict

def build_outputs(df_month: pd.DataFrame, end_day: int):
    all_days = np.arange(1, end_day + 1)

    df_month = df_month.copy()
    df_month["NAME"] = (
        df_month["NAME"].astype(str).str.strip().str.replace(r"\s+", " ", regex=True)
    )
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

    # Wide tables in REQUIRED order
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

    # DISPLAY rules (x default)
    wide_display = pd.DataFrame("x", index=wide_raw.index, columns=wide_raw.columns)
    row_exists = present.notna()

    wide_display = wide_display.mask(row_exists & (wide_raw == 0), "-")
    wide_display = wide_display.mask(row_exists & (wide_raw == 8888), "0")

    is_pos_measured = row_exists & (wide_raw.notna()) & (wide_raw > 0) & (wide_raw != 8888) & (wide_raw != 9999)
    wide_display = wide_display.mask(is_pos_measured, wide_raw.astype(float))

    # Add TGL col
    wide_display_out = wide_display.copy()
    wide_display_out.insert(0, "TGL", wide_display_out.index)

    wide_num_out = wide_num.copy()
    wide_num_out.insert(0, "TGL", wide_num_out.index)

    # QC: completeness
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

    # QC: unmapped
    horizontal_set = set(HORIZONTAL_COLS)
    mapped_not_in_horizontal = sorted(set(df_month["NAME_H"].unique()) - horizontal_set)
    qc_unmapped = df_month[df_month["NAME_H"].isin(mapped_not_in_horizontal)][["NAME", "NAME_H"]].drop_duplicates()

    # QC: empty last day
    last_present_day = present.notna().apply(lambda s: s[s].index.max() if s.any() else np.nan)
    last_day_present = present.loc[end_day].notna()
    empty_last_day_df = pd.DataFrame({
        "station": HORIZONTAL_COLS,
        "is_empty_on_last_day": (~last_day_present.reindex(HORIZONTAL_COLS).fillna(False)).astype(int).values,
        "last_record_day_in_window": last_present_day.reindex(HORIZONTAL_COLS).values,
    })
    empty_last_day_df["empty_days_up_to_last_day"] = np.where(
        empty_last_day_df["last_record_day_in_window"].isna(),
        float(end_day),
        float(end_day) - empty_last_day_df["last_record_day_in_window"].astype(float),
    )
    empty_last_day_df = empty_last_day_df[empty_last_day_df["is_empty_on_last_day"] == 1].copy()
    empty_last_day_df = empty_last_day_df.sort_values(
        ["empty_days_up_to_last_day", "station"], ascending=[False, True]
    )

    # Assert strict order
    assert list(wide_display_out.columns[1:]) == HORIZONTAL_COLS

    return wide_display_out, wide_num_out, station_summary, day_summary, qc_unmapped, empty_last_day_df


# ----------------------------
# In your Streamlit main flow AFTER df_month prepared:
# ----------------------------
st.subheader("Output view")
view_choice = st.radio(
    "Tampilan tabel",
    options=["DISPLAY (x / - / 0 / angka)", "NUMERIC (NaN / 0.1 / angka)"],
    index=0
)

download_choice = st.selectbox(
    "Pilih file yang ingin di-download",
    [
        "rain_horizontal_display.csv",
        "rain_horizontal_numeric.csv",
        "QC_station_completeness.csv",
        "QC_day_completeness.csv",
        "QC_unmapped_names.csv",
        "QC_empty_last_day.csv",
    ],
    index=0
)

wide_display_out, wide_num_out, qc_station, qc_day, qc_unmapped, qc_last_day = build_outputs(df_month, end_day)

# Show table (default display)
if view_choice.startswith("DISPLAY"):
    st.dataframe(wide_display_out, use_container_width=True)
else:
    st.dataframe(wide_num_out, use_container_width=True)

# Prepare downloads
def to_csv_bytes(dfx: pd.DataFrame) -> bytes:
    return dfx.to_csv(index=False).encode("utf-8")

download_map = {
    "rain_horizontal_display.csv": (wide_display_out, "text/csv"),
    "rain_horizontal_numeric.csv": (wide_num_out, "text/csv"),
    "QC_station_completeness.csv": (qc_station, "text/csv"),
    "QC_day_completeness.csv": (qc_day, "text/csv"),
    "QC_unmapped_names.csv": (qc_unmapped, "text/csv"),
    "QC_empty_last_day.csv": (qc_last_day, "text/csv"),
}

df_to_dl, mime = download_map[download_choice]
st.download_button(
    label=f"Download: {download_choice}",
    data=to_csv_bytes(df_to_dl),
    file_name=download_choice,
    mime=mime
)
