"""Dashboard Streamlit — Phân tích hành vi & phân khúc khách hàng Olist.

Đọc artifact do notebook phân tích sinh ra (outputs/data/*.parquet,
outputs/figures/*.png). Chạy:
    streamlit run app/streamlit_app.py
Hoặc trỏ thư mục khác qua biến môi trường OLIST_OUTPUTS.
"""
from __future__ import annotations

import os
from pathlib import Path

import pandas as pd
import streamlit as st

try:
    import plotly.express as px
    HAS_PX = True
except Exception:
    HAS_PX = False

# ---- Vị trí dữ liệu ----
OUTROOT = Path(os.environ.get("OLIST_OUTPUTS", "outputs"))
DATA_DIR = OUTROOT / "data"
FIG_DIR = OUTROOT / "figures"

st.set_page_config(page_title="Olist — Phân tích khách hàng", layout="wide")


# --------------------------------------------------------------------------- #
def _read(name: str) -> pd.DataFrame | None:
    p = DATA_DIR / f"{name}.parquet"
    if not p.exists():
        return None
    return pd.read_parquet(p)


@st.cache_data(show_spinner=False)
def load_all() -> dict:
    names = ["orders_view", "customers_view", "order_lines_view", "rfm_features",
             "stat_results", "customer_segments", "segment_profiles",
             "assoc_rules", "model_metrics"]
    return {n: _read(n) for n in names}


def show_fig(name: str, caption: str = "") -> None:
    p = FIG_DIR / f"{name}.png"
    if p.exists():
        st.image(str(p), caption=caption, use_container_width=True)
    else:
        st.info(f"Chưa có biểu đồ `{name}.png` (chạy notebook phân tích để sinh).")


# --------------------------------------------------------------------------- #
def tab_overview(d: dict) -> None:
    st.subheader("Tổng quan")
    ov, cv = d["orders_view"], d["customers_view"]
    if ov is None or cv is None:
        st.warning("Thiếu orders_view / customers_view."); return
    deliv = ov[ov["order_status"] == "delivered"]
    c = st.columns(5)
    c[0].metric("Tổng doanh thu", f"{deliv['order_value'].sum():,.0f}")
    c[1].metric("Số đơn", f"{ov['order_id'].nunique():,}")
    c[2].metric("Số khách", f"{ov['customer_unique_id'].nunique():,}")
    c[3].metric("Đánh giá TB", f"{ov['review_score'].mean():.2f}")
    c[4].metric("Tỉ lệ mua lại", f"{cv['is_repeat_buyer'].mean():.1%}")

    m = (deliv.assign(month=pd.to_datetime(deliv["order_purchase_timestamp"]).dt.to_period("M").dt.to_timestamp())
         .groupby("month").agg(doanh_thu=("order_value", "sum"), so_don=("order_id", "nunique")).reset_index())
    if HAS_PX:
        st.plotly_chart(px.line(m, x="month", y="doanh_thu", markers=True,
                                title="Doanh thu theo tháng"), use_container_width=True)
    else:
        st.line_chart(m.set_index("month")["doanh_thu"])
    show_fig("06_danhmuc_dialy", "Top danh mục & địa lý")


def tab_rfm(d: dict) -> None:
    st.subheader("RFM & Phân khúc khách hàng")
    rfm, seg, prof = d["rfm_features"], d["customer_segments"], d["segment_profiles"]
    if rfm is None:
        st.warning("Thiếu rfm_features."); return
    df = rfm.copy()
    if seg is not None:
        df = df.merge(seg[["customer_unique_id", "persona"]], on="customer_unique_id", how="left")
    states = ["(Tất cả)"] + sorted(df["customer_state"].dropna().unique().tolist())
    pick = st.selectbox("Lọc theo bang", states)
    if pick != "(Tất cả)":
        df = df[df["customer_state"] == pick]
    col1, col2 = st.columns(2)
    with col1:
        vc = df["rfm_segment"].value_counts().reset_index()
        vc.columns = ["phân khúc", "số khách"]
        if HAS_PX:
            st.plotly_chart(px.bar(vc, x="số khách", y="phân khúc", orientation="h",
                                   title="Số khách theo phân khúc RFM"), use_container_width=True)
        else:
            st.bar_chart(vc.set_index("phân khúc"))
    with col2:
        if "persona" in df.columns:
            st.write("**Chân dung (persona) theo cụm K-Means**")
            if prof is not None:
                st.dataframe(prof, use_container_width=True)
    st.write(f"**{len(df):,} khách** — xem trước:")
    st.dataframe(df.head(200), use_container_width=True)
    st.download_button("Tải RFM (CSV)", df.to_csv(index=False).encode("utf-8-sig"),
                       "rfm_filtered.csv", "text/csv")


def tab_stats(d: dict) -> None:
    st.subheader("Kiểm định thống kê (8 giả thuyết)")
    sr = d["stat_results"]
    if sr is None:
        st.warning("Thiếu stat_results."); return
    st.dataframe(sr, use_container_width=True)
    st.caption("p_param: kiểm định tham số (ANOVA/t-test/Chi-square). "
               "p_nonparam: phi-tham số. p_holm < 0.05 ⇒ có ý nghĩa thống kê.")
    show_fig("07_tuong_quan", "Ma trận tương quan")


def tab_cohort(d: dict) -> None:
    st.subheader("Cohort & Chuỗi thời gian")
    show_fig("02_xu_huong_thang", "Số đơn & doanh thu theo tháng")
    show_fig("10_cohort", "Cohort retention")


def tab_assoc(d: dict) -> None:
    st.subheader("Luật kết hợp giữa các danh mục")
    ar = d["assoc_rules"]
    if ar is None or ar.empty:
        st.warning("Chưa có luật (giỏ Olist rất thưa — đây cũng là một phát hiện).")
        return
    c = st.columns(2)
    min_lift = c[0].slider("Lift tối thiểu", 1.0, float(max(2.0, ar["lift"].max())), 1.0, 0.1)
    min_conf = c[1].slider("Confidence tối thiểu", 0.0, 1.0, 0.0, 0.05)
    f = ar[(ar["lift"] >= min_lift) & (ar["confidence"] >= min_conf)].sort_values("lift", ascending=False)
    st.write(f"**{len(f)} luật**")
    st.dataframe(f, use_container_width=True)
    if HAS_PX and len(f):
        st.plotly_chart(px.scatter(f, x="support", y="confidence", size="lift",
                                   hover_data=["antecedents", "consequents"],
                                   title="Support – Confidence – Lift"), use_container_width=True)


def tab_models(d: dict) -> None:
    st.subheader("Mô hình dự đoán")
    mm = d["model_metrics"]
    if mm is not None:
        st.write("**So sánh chỉ số các mô hình** (PR-AUC quan trọng vì dữ liệu mất cân bằng)")
        st.dataframe(mm, use_container_width=True)
    col1, col2 = st.columns(2)
    with col1:
        show_fig("13_ml_hailong", "ROC & PR — Hài lòng")
        show_fig("14_feature_importance", "Mức ảnh hưởng đặc trưng (SHAP)")
    with col2:
        show_fig("13_ml_mualai", "ROC & PR — Mua lại")
        show_fig("15_dl_duong_hoc", "Deep Learning — đường học")
    show_fig("16_so_sanh_mo_hinh", "So sánh ML vs Deep Learning")


def tab_lookup(d: dict) -> None:
    st.subheader("Tra cứu khách hàng")
    rfm, seg = d["rfm_features"], d["customer_segments"]
    if rfm is None:
        st.warning("Thiếu rfm_features."); return
    cid = st.text_input("Nhập customer_unique_id")
    if cid:
        row = rfm[rfm["customer_unique_id"] == cid]
        if row.empty:
            st.error("Không tìm thấy khách hàng.")
        else:
            st.dataframe(row.T, use_container_width=True)
            if seg is not None:
                s = seg[seg["customer_unique_id"] == cid]
                if not s.empty:
                    st.success(f"Phân khúc: {s.iloc[0].get('persona','?')} "
                               f"(cụm {s.iloc[0].get('cluster','?')})")


def main() -> None:
    st.title("🛒 Olist — Phân tích hành vi & phân khúc khách hàng")
    if not DATA_DIR.exists():
        st.error(f"Không thấy thư mục dữ liệu: `{DATA_DIR}`.\n\n"
                 "Hãy chạy notebook phân tích trước để sinh `outputs/`, "
                 "hoặc đặt biến môi trường `OLIST_OUTPUTS` trỏ tới thư mục chứa `data/`.")
        return
    d = load_all()
    tabs = st.tabs(["Tổng quan", "RFM & Phân khúc", "Thống kê", "Cohort/Thời gian",
                    "Luật kết hợp", "Mô hình", "Tra cứu KH"])
    for t, fn in zip(tabs, [tab_overview, tab_rfm, tab_stats, tab_cohort,
                            tab_assoc, tab_models, tab_lookup]):
        with t:
            fn(d)


if __name__ == "__main__":
    main()
