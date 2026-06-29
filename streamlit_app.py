"""Dashboard Streamlit — Phân tích hành vi & phân khúc khách hàng Olist.

Đọc artifact do notebook phân tích sinh ra (outputs/data/*.parquet,
outputs/figures/*.png). Tự dò thư mục outputs/ ở nhiều vị trí; có thể nhập tay
đường dẫn ở sidebar hoặc đặt biến môi trường OLIST_OUTPUTS.

Chạy:  streamlit run app/streamlit_app.py
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

ARTIFACTS = ["orders_view", "customers_view", "order_lines_view", "rfm_features",
             "stat_results", "customer_segments", "segment_profiles",
             "assoc_rules", "model_metrics"]
SCRIPT_DIR = Path(__file__).resolve().parent
FIG_DIR: Path | None = None  # gán trong main()

st.set_page_config(page_title="Olist — Phân tích khách hàng", layout="wide")


# --------------------------------------------------------------------------- #
def candidate_roots() -> list[Path]:
    """Các vị trí có thể chứa thư mục outputs/ (ưu tiên env)."""
    cands = []
    if os.environ.get("OLIST_OUTPUTS"):
        cands.append(Path(os.environ["OLIST_OUTPUTS"]))
    cands += [Path.cwd() / "outputs", SCRIPT_DIR / "outputs",
              SCRIPT_DIR.parent / "outputs", Path.cwd()]
    return cands


def has_data(root: Path) -> bool:
    dd = root / "data"
    return dd.exists() and any(dd.glob("*.parquet"))


def auto_root() -> Path | None:
    for p in candidate_roots():
        if has_data(p):
            return p.resolve()
    return None


@st.cache_data(show_spinner=False)
def load_all(data_dir: str) -> dict:
    dd = Path(data_dir)
    out = {}
    for n in ARTIFACTS:
        p = dd / f"{n}.parquet"
        out[n] = pd.read_parquet(p) if p.exists() else None
    return out


def show_fig(name: str, caption: str = "") -> None:
    p = (FIG_DIR / f"{name}.png") if FIG_DIR else None
    if p and p.exists():
        st.image(str(p), caption=caption, use_container_width=True)
    else:
        st.info(f"Chưa có biểu đồ `{name}.png`.")


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
         .groupby("month").agg(doanh_thu=("order_value", "sum")).reset_index())
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
        if prof is not None:
            st.write("**Chân dung (persona) theo cụm K-Means**")
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
    global FIG_DIR
    st.title("🛒 Olist — Phân tích hành vi & phân khúc khách hàng")

    st.sidebar.header("⚙️ Dữ liệu")
    detected = auto_root()
    default = str(detected) if detected else "outputs"
    root_str = st.sidebar.text_input("Thư mục outputs", value=default,
                                     help="Thư mục chứa data/ và figures/")
    root = Path(root_str)
    FIG_DIR = root / "figures"
    data_dir = root / "data"

    if not has_data(root):
        st.error(f"Không thấy dữ liệu parquet trong `{(root/'data')}`.")
        st.markdown("**Cách khắc phục:**")
        st.markdown(
            "1. Chạy notebook phân tích (`Olist_Phan_Tich.ipynb`) để sinh `outputs/`, "
            "tải về `olist_outputs.zip` rồi **giải nén** sao cho có `outputs/data/*.parquet`.\n"
            "2. Nhập đúng đường dẫn thư mục `outputs` vào ô bên trái (sidebar), hoặc đặt "
            "biến môi trường `OLIST_OUTPUTS`.\n"
            "3. Nếu chạy local, mở terminal tại thư mục dự án rồi: "
            "`streamlit run app/streamlit_app.py`")
        st.markdown("**Đã thử các vị trí sau:**")
        st.code("\n".join(str(p / "data") for p in candidate_roots()))
        return

    st.sidebar.success(f"Đang đọc: {data_dir}")
    d = load_all(str(data_dir))
    found = [k for k, v in d.items() if v is not None]
    st.sidebar.caption(f"Đã nạp {len(found)}/{len(ARTIFACTS)} bảng.")

    tabs = st.tabs(["Tổng quan", "RFM & Phân khúc", "Thống kê", "Cohort/Thời gian",
                    "Luật kết hợp", "Mô hình", "Tra cứu KH"])
    for t, fn in zip(tabs, [tab_overview, tab_rfm, tab_stats, tab_cohort,
                            tab_assoc, tab_models, tab_lookup]):
        with t:
            fn(d)


if __name__ == "__main__":
    main()
