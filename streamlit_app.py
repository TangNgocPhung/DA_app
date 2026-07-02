"""Dashboard — Phân tích hành vi & phân khúc khách hàng Olist.

Đọc artifact (outputs/data/*.parquet, outputs/figures/*.png) do notebook phân
tích sinh ra. Tự dò thư mục outputs/; có thể nhập tay ở sidebar hoặc đặt biến
môi trường OLIST_OUTPUTS.
"""
from __future__ import annotations

import os
from pathlib import Path

import pandas as pd
import streamlit as st

try:
    import plotly.express as px
    import plotly.graph_objects as go
    HAS_PX = True
except Exception:
    HAS_PX = False

try:
    from streamlit_option_menu import option_menu
    HAS_MENU = True
except Exception:
    HAS_MENU = False

# ---- Cấu hình chung ----
ARTIFACTS = ["orders_view", "customers_view", "order_lines_view", "rfm_features",
             "stat_results", "customer_segments", "segment_profiles",
             "assoc_rules", "model_metrics"]
SCRIPT_DIR = Path(__file__).resolve().parent
FIG_DIR: Path | None = None

PRIMARY = "#059669"
ACCENT = "#0F766E"
PALETTE = ["#059669", "#0F766E", "#10B981", "#F59E0B", "#0EA5E9",
           "#34D399", "#EF4444", "#14B8A6"]

st.set_page_config(page_title="Olist · Phân tích khách hàng",
                   page_icon="🛒", layout="wide", initial_sidebar_state="expanded")

# --------------------------------------------------------------------------- #
# CSS
# --------------------------------------------------------------------------- #
CSS = """
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&family=Poppins:wght@600;700;800&display=swap');

html, body, [class*="css"] { font-family: 'Inter', sans-serif; }
.block-container { padding-top: 1.4rem; padding-bottom: 2rem; max-width: 1250px; }
#MainMenu, footer { visibility: hidden; }
header[data-testid="stHeader"] { background: transparent; }
[data-testid="stAppViewContainer"] { background: #F1F5F9; }

/* Header bar (gọn, kiểu BI) */
.topbar { background:#fff; border:1px solid #E5E9EF; border-left:5px solid #059669;
  border-radius:12px; padding:18px 22px; margin-bottom:20px;
  display:flex; justify-content:space-between; align-items:flex-start; gap:18px; }
.tb-title { font-size:1.3rem; font-weight:800; color:#0F172A; letter-spacing:-.01em; }
.tb-sub { color:#64748B; font-size:.9rem; margin-top:5px; max-width:780px; line-height:1.45; }
.tb-meta { color:#059669; font-size:.78rem; font-weight:600; background:#ECFDF5;
  border:1px solid #A7F3D0; padding:6px 12px; border-radius:8px; white-space:nowrap; }

/* KPI cards (phẳng, kiểu báo cáo) */
.kpi { background:#fff; border:1px solid #E5E9EF; border-top:3px solid #059669;
  border-radius:12px; padding:15px 18px; height:100%; }
.kpi .lab { font-size:.72rem; font-weight:600; letter-spacing:.04em;
  text-transform:uppercase; color:#94A3B8; }
.kpi .val { font-weight:700; font-size:1.55rem; color:#0F172A; margin-top:6px;
  line-height:1.1; white-space:nowrap; }

/* Section heading */
.sec { border-left:3px solid #059669; padding-left:12px; margin:10px 0 6px; }
.sec h3 { font-weight:700; font-size:1.12rem; color:#0F172A; margin:0; }
.sec p { color:#94A3B8; font-size:.86rem; margin:2px 0 0 0; }

/* Tabs */
.stTabs [data-baseweb="tab-list"] { gap: 4px; border-bottom:1px solid #EEF0F5; }
.stTabs [data-baseweb="tab"] { font-weight:600; font-size:.95rem; padding:8px 16px;
  border-radius:10px 10px 0 0; }
.stTabs [aria-selected="true"] { color:#059669 !important; background:#ECFDF5; }

/* Cards for dataframes/plots */
[data-testid="stDataFrame"] { border:1px solid #E5E9EF; border-radius:10px; }
section[data-testid="stSidebar"] { background:#FFFFFF; border-right:1px solid #E5E9EF; }
.small-note { color:#94A3B8; font-size:.82rem; }
hr { margin: 0.8rem 0; border-color:#E5E9EF; }
</style>
"""


# --------------------------------------------------------------------------- #
# Tiện ích
# --------------------------------------------------------------------------- #
def candidate_roots() -> list[Path]:
    c = []
    if os.environ.get("OLIST_OUTPUTS"):
        c.append(Path(os.environ["OLIST_OUTPUTS"]))
    c += [Path.cwd() / "outputs", SCRIPT_DIR / "outputs",
          SCRIPT_DIR.parent / "outputs", Path.cwd()]
    return c


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
    return {n: (pd.read_parquet(dd / f"{n}.parquet")
                if (dd / f"{n}.parquet").exists() else None) for n in ARTIFACTS}


def fmt_int(x) -> str:
    try:
        return f"{int(x):,}".replace(",", ".")
    except Exception:
        return str(x)


def fmt_money(x) -> str:
    x = float(x)
    if x >= 1e9:
        return f"R$ {x/1e9:.1f}tỷ"
    if x >= 1e6:
        return f"R$ {x/1e6:.1f}tr"
    if x >= 1e3:
        return f"R$ {x/1e3:.0f}k"
    return f"R$ {x:.0f}"


def kpi(col, icon, label, value, tint):
    col.markdown(
        f'<div class="kpi" style="border-top-color:{tint}">'
        f'<div class="lab">{label}</div><div class="val">{value}</div></div>',
        unsafe_allow_html=True)


def section(title, sub=""):
    st.markdown(f'<div class="sec"><h3>{title}</h3>'
                + (f'<p>{sub}</p>' if sub else "") + '</div>', unsafe_allow_html=True)


def style_fig(fig, h=360):
    fig.update_layout(
        template="plotly_white", height=h, font_family="Inter",
        margin=dict(l=10, r=10, t=54, b=10), colorway=PALETTE,
        plot_bgcolor="rgba(0,0,0,0)", paper_bgcolor="rgba(0,0,0,0)",
        title_font=dict(family="Poppins", size=16, color="#1E2130"),
        legend=dict(orientation="h", yanchor="bottom", y=1.02, x=0),
    )
    return fig


def show_fig(name, caption=""):
    p = (FIG_DIR / f"{name}.png") if FIG_DIR else None
    if p and p.exists():
        st.image(str(p), caption=caption, use_container_width=True)
    else:
        st.caption(f"— (chưa có biểu đồ {name})")


# --------------------------------------------------------------------------- #
# Tabs
# --------------------------------------------------------------------------- #
def tab_overview(d):
    ov, cv = d["orders_view"], d["customers_view"]
    if ov is None or cv is None:
        st.warning("Thiếu orders_view / customers_view."); return
    deliv = ov[ov["order_status"] == "delivered"]
    section("Bức tranh tổng quan", "Các chỉ số chính của toàn bộ giao dịch trên Olist")
    cols = st.columns(5)
    kpi(cols[0], "💰", "Tổng doanh thu", fmt_money(deliv["order_value"].sum()), "#059669")
    kpi(cols[1], "🧾", "Số đơn hàng", fmt_int(ov["order_id"].nunique()), "#0F766E")
    kpi(cols[2], "👥", "Số khách hàng", fmt_int(ov["customer_unique_id"].nunique()), "#0EA5E9")
    kpi(cols[3], "⭐", "Đánh giá TB", f'{ov["review_score"].mean():.2f}', "#F59E0B")
    kpi(cols[4], "🔁", "Tỉ lệ mua lại", f'{cv["is_repeat_buyer"].mean():.1%}', "#EF4444")

    st.write("")
    c1, c2 = st.columns((3, 2))
    with c1:
        m = (deliv.assign(month=pd.to_datetime(deliv["order_purchase_timestamp"])
                          .dt.to_period("M").dt.to_timestamp())
             .groupby("month").agg(doanh_thu=("order_value", "sum")).reset_index())
        if HAS_PX:
            fig = px.area(m, x="month", y="doanh_thu", title="Doanh thu theo tháng")
            fig.update_traces(line_color=PRIMARY, fillcolor="rgba(5,150,105,.12)")
            st.plotly_chart(style_fig(fig), use_container_width=True)
    with c2:
        top = (deliv.groupby("customer_state")["order_value"].sum()
               .sort_values(ascending=False).head(8).reset_index())
        if HAS_PX:
            fig = px.bar(top, x="order_value", y="customer_state", orientation="h",
                         title="Top bang theo doanh thu", color="order_value",
                         color_continuous_scale=["#D1FAE5", PRIMARY])
            fig.update_layout(coloraxis_showscale=False, yaxis=dict(autorange="reversed"))
            st.plotly_chart(style_fig(fig), use_container_width=True)


def tab_rfm(d):
    rfm, seg, prof = d["rfm_features"], d["customer_segments"], d["segment_profiles"]
    if rfm is None:
        st.warning("Thiếu rfm_features."); return
    section("RFM & Phân khúc khách hàng",
            "Chấm điểm RFM, phân cụm K-Means và chân dung từng nhóm")
    df = rfm.copy()
    if seg is not None:
        df = df.merge(seg[["customer_unique_id", "persona"]], on="customer_unique_id", how="left")
    pick = st.selectbox("Lọc theo bang",
                        ["(Tất cả)"] + sorted(df["customer_state"].dropna().unique().tolist()))
    if pick != "(Tất cả)":
        df = df[df["customer_state"] == pick]
    c1, c2 = st.columns(2)
    with c1:
        vc = df["rfm_segment"].value_counts().reset_index()
        vc.columns = ["phân khúc", "số khách"]
        if HAS_PX:
            fig = px.bar(vc.sort_values("số khách"), x="số khách", y="phân khúc",
                         orientation="h", title="Số khách theo phân khúc RFM",
                         color="phân khúc", color_discrete_sequence=PALETTE)
            fig.update_layout(showlegend=False)
            st.plotly_chart(style_fig(fig), use_container_width=True)
    with c2:
        if HAS_PX and "monetary" in df.columns:
            fig = px.scatter(df.sample(min(4000, len(df)), random_state=42),
                             x="recency_days", y="monetary", color="rfm_segment",
                             title="Recency vs Monetary theo phân khúc",
                             color_discrete_sequence=PALETTE, opacity=0.6)
            fig.update_yaxes(type="log")
            st.plotly_chart(style_fig(fig), use_container_width=True)
    if prof is not None:
        section("Chân dung phân khúc (K-Means)")
        st.dataframe(prof, use_container_width=True, hide_index=True)
    st.download_button("⬇️ Tải RFM (CSV)", df.to_csv(index=False).encode("utf-8-sig"),
                       "rfm_filtered.csv", "text/csv")


def tab_stats(d):
    sr = d["stat_results"]
    if sr is None:
        st.warning("Thiếu stat_results."); return
    section("Kiểm định thống kê — 8 giả thuyết",
            "Mỗi giả thuyết dùng kiểm định tham số (ANOVA/t-test/Chi-square) và phi-tham số")
    st.dataframe(sr, use_container_width=True, hide_index=True)
    st.markdown('<span class="small-note">p_holm &lt; 0.05 ⇒ có ý nghĩa thống kê. '
                'effect size cho biết độ mạnh của mối liên hệ.</span>', unsafe_allow_html=True)
    st.write("")
    show_fig("07_tuong_quan", "Ma trận tương quan giữa các biến số")


def tab_cohort(d):
    section("Cohort & Chuỗi thời gian", "Xu hướng doanh thu và tỉ lệ giữ chân khách")
    c1, c2 = st.columns(2)
    with c1:
        show_fig("02_xu_huong_thang", "Số đơn & doanh thu theo tháng")
    with c2:
        show_fig("10_cohort", "Cohort retention")


def tab_assoc(d):
    ar = d["assoc_rules"]
    section("Luật kết hợp giữa các danh mục", "Gợi ý bán chéo dựa trên hành vi mua kèm")
    if ar is None or ar.empty:
        st.info("Giỏ hàng Olist rất thưa (đa số 1 danh mục/đơn) nên ít luật — "
                "đây cũng là một phát hiện đáng chú ý.")
        return
    c = st.columns(2)
    lift = c[0].slider("Lift tối thiểu", 1.0, float(max(2.0, ar["lift"].max())), 1.0, 0.1)
    conf = c[1].slider("Confidence tối thiểu", 0.0, 1.0, 0.0, 0.05)
    f = ar[(ar["lift"] >= lift) & (ar["confidence"] >= conf)].sort_values("lift", ascending=False)
    st.dataframe(f, use_container_width=True, hide_index=True)
    if HAS_PX and len(f):
        fig = px.scatter(f, x="support", y="confidence", size="lift", color="lift",
                         hover_data=["antecedents", "consequents"],
                         title="Support – Confidence – Lift",
                         color_continuous_scale=["#D1FAE5", PRIMARY])
        st.plotly_chart(style_fig(fig), use_container_width=True)


def tab_models(d):
    mm = d["model_metrics"]
    section("Mô hình dự đoán", "Machine Learning (4 mô hình) + Deep Learning; nhấn PR-AUC")
    if mm is not None:
        st.dataframe(mm, use_container_width=True, hide_index=True)
    c1, c2 = st.columns(2)
    with c1:
        show_fig("13_ml_hailong", "ROC & PR — Dự đoán hài lòng")
        show_fig("14_feature_importance", "Mức ảnh hưởng đặc trưng (SHAP)")
    with c2:
        show_fig("13_ml_mualai", "ROC & PR — Dự đoán mua lại")
        show_fig("15_dl_duong_hoc", "Deep Learning — đường học")
    show_fig("16_so_sanh_mo_hinh", "So sánh ML vs Deep Learning")


def tab_lookup(d):
    rfm, seg = d["rfm_features"], d["customer_segments"]
    section("Tra cứu khách hàng", "Nhập mã khách để xem hồ sơ & phân khúc")
    if rfm is None:
        st.warning("Thiếu rfm_features."); return
    cid = st.text_input("customer_unique_id", placeholder="vd: 0000366f3b9a7992bf8c76cfdf3221e2")
    if cid:
        row = rfm[rfm["customer_unique_id"] == cid]
        if row.empty:
            st.error("Không tìm thấy khách hàng.")
        else:
            r = row.iloc[0]
            cols = st.columns(4)
            kpi(cols[0], "🕒", "Recency (ngày)", fmt_int(r.get("recency_days", 0)), "#059669")
            kpi(cols[1], "🔁", "Frequency", fmt_int(r.get("frequency", 0)), "#0F766E")
            kpi(cols[2], "💰", "Monetary", fmt_money(r.get("monetary", 0)), "#0EA5E9")
            kpi(cols[3], "⭐", "Đánh giá TB", f'{r.get("avg_review_score", float("nan")):.1f}', "#F59E0B")
            if seg is not None:
                s = seg[seg["customer_unique_id"] == cid]
                if not s.empty:
                    st.success(f"**Phân khúc:** {s.iloc[0].get('persona','?')}  ·  "
                               f"RFM: {r.get('rfm_segment','?')}")
            st.dataframe(row.T, use_container_width=True)


# --------------------------------------------------------------------------- #
NAV = [("Tổng quan", "bar-chart-fill", tab_overview),
       ("RFM & Phân khúc", "people-fill", tab_rfm),
       ("Thống kê", "clipboard-data", tab_stats),
       ("Cohort/Thời gian", "graph-up", tab_cohort),
       ("Luật kết hợp", "link-45deg", tab_assoc),
       ("Mô hình", "cpu-fill", tab_models),
       ("Tra cứu KH", "search", tab_lookup)]

MENU_STYLES = {
    "container": {"padding": "0", "background-color": "transparent"},
    "icon": {"color": "#0F766E", "font-size": "15px"},
    "nav-link": {"font-size": "14px", "font-weight": "600", "color": "#334155",
                 "text-align": "left", "margin": "3px 0", "border-radius": "10px",
                 "--hover-color": "#ECFDF5"},
    "nav-link-selected": {"background-color": "#059669", "color": "white",
                          "font-weight": "700"},
}

HERO = """<div class="topbar">
<div><div class="tb-title">Olist · Phân tích hành vi &amp; phân khúc khách hàng</div>
<div class="tb-sub">Khai phá hành vi mua sắm và xây dựng chân dung khách hàng trên nền tảng
thương mại điện tử — RFM, thống kê suy diễn, phân cụm, luật kết hợp và mô hình dự đoán.</div></div>
<div class="tb-meta">Bộ dữ liệu Olist · 2016–2018 · ~100K đơn</div></div>"""


def main():
    global FIG_DIR
    st.markdown(CSS, unsafe_allow_html=True)
    labels = [n[0] for n in NAV]

    with st.sidebar:
        st.markdown("## 🛒 Olist Analytics")
        if HAS_MENU:
            choice = option_menu(None, labels, icons=[n[1] for n in NAV],
                                 default_index=0, styles=MENU_STYLES)
        else:
            choice = st.radio("Điều hướng", labels, label_visibility="collapsed")
        st.markdown("---")
        st.markdown("##### ⚙️ Nguồn dữ liệu")
        detected = auto_root()
        root = Path(st.text_input("Thư mục outputs",
                    value=str(detected) if detected else "outputs",
                    label_visibility="collapsed"))
        FIG_DIR = root / "figures"

    st.markdown(HERO, unsafe_allow_html=True)

    if not has_data(root):
        st.error(f"Không thấy dữ liệu parquet trong `{root/'data'}`.")
        st.markdown("Nhập đúng đường dẫn thư mục `outputs` ở sidebar, hoặc chạy notebook "
                    "phân tích để sinh dữ liệu. Đã thử:")
        st.code("\n".join(str(p / "data") for p in candidate_roots()))
        return

    d = load_all(str(root / "data"))
    n = sum(v is not None for v in d.values())
    with st.sidebar:
        st.success(f"✅ Đã nạp {n}/{len(ARTIFACTS)} bảng")
        st.caption(f"Đang đọc: {root/'data'}")
        st.markdown("---")
        st.markdown("**Đồ án Phân tích dữ liệu**  \nĐH Sư phạm TP.HCM")

    fn = {n[0]: n[2] for n in NAV}[choice]
    fn(d)


if __name__ == "__main__":
    main()
