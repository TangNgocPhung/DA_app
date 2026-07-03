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

PRIMARY = "#2FA36B"   # emerald tươi (biểu đồ đơn sắc)
ACCENT = "#EF5B4C"    # coral (nhấn)
PALETTE = ["#EF5B4C", "#2FA36B", "#E0A73E", "#2C8C99", "#7C5CFC",
           "#F2789F", "#38B6A0", "#FF9F45"]

# Mã bang Brazil (UF) -> tên đầy đủ
UF_NAMES = {
    "AC": "Acre", "AL": "Alagoas", "AP": "Amapá", "AM": "Amazonas", "BA": "Bahia",
    "CE": "Ceará", "DF": "Distrito Federal", "ES": "Espírito Santo", "GO": "Goiás",
    "MA": "Maranhão", "MT": "Mato Grosso", "MS": "Mato Grosso do Sul",
    "MG": "Minas Gerais", "PA": "Pará", "PB": "Paraíba", "PR": "Paraná",
    "PE": "Pernambuco", "PI": "Piauí", "RJ": "Rio de Janeiro",
    "RN": "Rio Grande do Norte", "RS": "Rio Grande do Sul", "RO": "Rondônia",
    "RR": "Roraima", "SC": "Santa Catarina", "SP": "São Paulo", "SE": "Sergipe",
    "TO": "Tocantins",
}

# Ý nghĩa các phân khúc RFM
SEGMENT_DESC = {
    "Champions": "Mua gần đây, thường xuyên và chi nhiều — khách tốt nhất; ưu đãi đặc quyền, giữ chân.",
    "Loyal Customers": "Mua khá gần đây, tần suất khá — trung thành; có thể upsell/bán chéo.",
    "Potential Loyalist": "Mới mua, có dấu hiệu tích cực — tiềm năng thành khách trung thành.",
    "New / Promising": "Khách mới, mua gần đây nhưng mới một lần — nuôi dưỡng để mua lại.",
    "At Risk": "Từng mua nhiều nhưng lâu chưa quay lại — nguy cơ rời bỏ; chiến dịch win-back.",
    "Hibernating": "Lâu không mua, tần suất & chi tiêu thấp — đang 'ngủ đông'.",
    "Lost": "Rất lâu không mua — gần như đã mất; chi phí kích hoạt lại cao.",
}

REGIONS = ["Norte", "Nordeste", "Centro-Oeste", "Sudeste", "Sul"]

# Tọa độ tâm (lat, lon) các bang Brazil — cho bản đồ bong bóng
STATE_CENTROIDS = {
    "AC": (-9.0, -70.5), "AL": (-9.6, -36.6), "AP": (1.4, -51.8), "AM": (-3.9, -63.0),
    "BA": (-12.5, -41.7), "CE": (-5.2, -39.6), "DF": (-15.8, -47.9), "ES": (-19.6, -40.3),
    "GO": (-15.9, -49.6), "MA": (-5.0, -45.3), "MT": (-12.6, -55.9), "MS": (-20.5, -54.5),
    "MG": (-18.5, -44.5), "PA": (-4.0, -52.9), "PB": (-7.1, -36.7), "PR": (-24.8, -51.5),
    "PE": (-8.4, -37.9), "PI": (-7.7, -42.7), "RJ": (-22.2, -42.7), "RN": (-5.8, -36.6),
    "RS": (-30.0, -53.5), "RO": (-10.8, -63.3), "RR": (2.1, -61.4), "SC": (-27.3, -50.4),
    "SP": (-22.2, -48.6), "SE": (-10.6, -37.4), "TO": (-10.2, -48.3),
}

st.set_page_config(page_title="Olist · Phân tích khách hàng",
                   page_icon="🛒", layout="wide", initial_sidebar_state="expanded")

# --------------------------------------------------------------------------- #
# CSS
# --------------------------------------------------------------------------- #
CSS = """
<style>
@import url('https://fonts.googleapis.com/css2?family=Playfair+Display:wght@700;800;900&family=IBM+Plex+Mono:wght@400;500;600&family=Inter:wght@400;500;600;700&display=swap');

html, body, [class*="css"] { font-family:'Inter', sans-serif; color:#1B3A4B; }
[data-testid="stAppViewContainer"] { background:#FBF7F0; }
.block-container { padding-top:1rem; padding-bottom:2.4rem; max-width:1290px; }
#MainMenu, footer { visibility:hidden; }
header[data-testid="stHeader"] { background:transparent; }

/* ===== Masthead (tạp chí) ===== */
.mast { border-top:3px solid #1B3A4B; border-bottom:3px solid #1B3A4B;
  padding:12px 0 14px; margin-bottom:22px; }
.mast-strip { display:flex; justify-content:space-between; gap:14px; padding:0 2px;
  font-family:'IBM Plex Mono',monospace; text-transform:uppercase; letter-spacing:.14em;
  font-size:.66rem; color:#6C7A72; }
.mast-title { font-family:'Playfair Display',serif; font-weight:900; text-align:center;
  font-size:3.1rem; line-height:1; color:#1B3A4B; margin:12px 0 8px; }
.mast-title .ac { color:#EF5B4C; }
.mast-sub { text-align:center; font-family:'IBM Plex Mono',monospace; text-transform:uppercase;
  letter-spacing:.16em; font-size:.72rem; color:#6C7A72; }
.mast-rule { height:4px; background:#E0A73E; margin:14px 0 12px; position:relative; border-radius:2px; }
.mast-rule i { position:absolute; top:0; left:0; bottom:0; width:62%; background:#EF5B4C; border-radius:2px; }

/* ===== KPI (số serif lớn) ===== */
.kpi { border-top:2px solid #E4DCC9; padding:12px 2px 4px; background:transparent; height:100%; }
.kpi .val { font-family:'Playfair Display',serif; font-weight:800; font-size:1.95rem; line-height:1; }
.kpi .lab { font-family:'IBM Plex Mono',monospace; text-transform:uppercase; letter-spacing:.09em;
  font-size:.66rem; color:#6C7A72; margin-top:9px; }

/* ===== Section ===== */
.sec { border-top:2px solid #1B3A4B; padding-top:8px; margin:22px 0 8px; }
.sec h3 { font-family:'IBM Plex Mono',monospace; text-transform:uppercase; letter-spacing:.12em;
  font-size:.92rem; font-weight:600; color:#1B3A4B; margin:0; }
.sec p { color:#9A8C74; font-size:.84rem; margin:4px 0 0; }

/* ===== Sidebar teal, chữ kem ===== */
section[data-testid="stSidebar"] { background:#0E6E63; border-right:none; }
section[data-testid="stSidebar"] .stMarkdown, section[data-testid="stSidebar"] label,
section[data-testid="stSidebar"] p, section[data-testid="stSidebar"] h1,
section[data-testid="stSidebar"] h2, section[data-testid="stSidebar"] h3,
section[data-testid="stSidebar"] [data-testid="stCaptionContainer"] { color:#FBF7F0 !important; }
.brand { font-family:'Playfair Display',serif; font-weight:900; font-size:1.75rem; color:#FBF7F0; }
.brand .ac { color:#EF5B4C; }
.nav-lbl { font-family:'IBM Plex Mono',monospace; text-transform:uppercase; letter-spacing:.18em;
  font-size:.62rem; color:#9FD3CB; margin:8px 0 2px; }

/* ===== Insight / pipe / dataframe ===== */
[data-testid="stDataFrame"] { border:1px solid #E4DCC9; border-radius:8px; }
.small-note { color:#9A8C74; font-size:.82rem; }
hr { border-color:#E4DCC9; }
.pipe { background:#FFFDF7; border:1px solid #E4DCC9; color:#1B3A4B; font-family:'IBM Plex Mono',monospace;
  font-size:.78rem; letter-spacing:.03em; padding:10px 14px; border-radius:8px; margin:4px 0 14px; line-height:1.9; }
.insight { background:#FFFDF7; border:1px solid #E4DCC9; border-left:3px solid #EF5B4C;
  border-radius:8px; padding:12px 16px; margin:14px 0 4px; color:#3A4A52; font-size:.9rem; }
.insight .ins-title { font-family:'IBM Plex Mono',monospace; text-transform:uppercase; letter-spacing:.08em;
  font-weight:600; color:#1B3A4B; margin-bottom:6px; font-size:.76rem; }
.insight ul { margin:0; padding-left:18px; } .insight li { margin:4px 0; line-height:1.55; }

/* ===== Thông tin nhóm (trên nền teal) ===== */
.credit { font-size:.8rem; color:#DCEFEA; line-height:1.5; }
.credit .c-school { font-family:'Playfair Display',serif; font-weight:700; font-size:1.05rem; color:#FBF7F0; }
.credit .c-dept, .credit .c-meta { color:#BFE0D8; }
.credit .c-role { font-family:'IBM Plex Mono',monospace; text-transform:uppercase; letter-spacing:.1em;
  font-weight:600; color:#E0A73E; margin-top:10px; font-size:.66rem; }
.credit ol.c-list { margin:4px 0 0; padding-left:18px; }
.credit ol.c-list li { margin:2px 0; color:#EAF5F1; }
.credit .c-gv { font-weight:700; color:#FBF7F0; }
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
        f'<div class="kpi"><div class="val" style="color:{tint}">{value}</div>'
        f'<div class="lab">{label}</div></div>', unsafe_allow_html=True)


def section(title, sub=""):
    st.markdown(f'<div class="sec"><h3>{title}</h3>'
                + (f'<p>{sub}</p>' if sub else "") + '</div>', unsafe_allow_html=True)


def note(lines):
    """Hộp nhận xét (danh sách gạch đầu dòng, cho phép thẻ <b>)."""
    items = "".join(f"<li>{x}</li>" for x in lines)
    st.markdown(f'<div class="insight"><div class="ins-title">📝 Nhận xét</div>'
                f'<ul>{items}</ul></div>', unsafe_allow_html=True)


def style_fig(fig, h=360):
    fig.update_layout(
        template="plotly_white", height=h, font_family="Inter",
        margin=dict(l=10, r=10, t=54, b=10), colorway=PALETTE,
        plot_bgcolor="rgba(0,0,0,0)", paper_bgcolor="rgba(0,0,0,0)",
        title_font=dict(family="Playfair Display", size=17, color="#1B3A4B"),
        legend=dict(orientation="v", yanchor="top", y=1, x=1.02, font=dict(size=11),
                    title_text=""),
        title=dict(x=0, xanchor="left", pad=dict(b=10)),
    )
    return fig


def show_fig(name, caption=""):
    p = (FIG_DIR / f"{name}.png") if FIG_DIR else None
    if p and p.exists():
        st.image(str(p), caption=caption, use_container_width=True)
    else:
        st.caption(f"— (chưa có biểu đồ {name})")


def apply_filters(d, regions, dr):
    """Lọc theo vùng miền + khoảng thời gian qua orders_view rồi lan sang các bảng."""
    ov = d.get("orders_view")
    if ov is None:
        return d
    m = pd.Series(True, index=ov.index)
    if regions:
        m &= ov["region"].isin(regions)
    if dr and len(dr) == 2 and dr[0] and dr[1]:
        ts = pd.to_datetime(ov["order_purchase_timestamp"]).dt.date
        m &= (ts >= dr[0]) & (ts <= dr[1])
    ovf = ov[m]
    if len(ovf) == 0 or len(ovf) == len(ov):
        return d  # rỗng hoặc không thay đổi -> giữ nguyên
    out = dict(d)
    out["orders_view"] = ovf
    oids, cids = set(ovf["order_id"]), set(ovf["customer_unique_id"])
    ol = d.get("order_lines_view")
    if ol is not None:
        out["order_lines_view"] = ol[ol["order_id"].isin(oids)]
    for k in ("customers_view", "rfm_features"):
        t = d.get(k)
        if t is not None and "customer_unique_id" in t.columns:
            out[k] = t[t["customer_unique_id"].isin(cids)]
    return out


# --------------------------------------------------------------------------- #
# Tabs
# --------------------------------------------------------------------------- #
def tab_intro(d):
    section("Giới thiệu bộ dữ liệu Olist",
            "Brazilian E-Commerce Public Dataset by Olist — dữ liệu TMĐT thực tế tại Brazil")
    ov = d.get("orders_view")
    n_orders = (f"{ov['order_id'].nunique():,}".replace(",", ".")
                if ov is not None else "~100.000")
    cols = st.columns(4)
    kpi(cols[0], "", "Nguồn", "Kaggle · Olist", "#059669")
    kpi(cols[1], "", "Số đơn hàng", n_orders, "#0F766E")
    kpi(cols[2], "", "Giai đoạn", "2016 – 2018", "#0EA5E9")
    kpi(cols[3], "", "Số bảng", "9 bảng", "#F59E0B")
    st.markdown("<div style='height:14px'></div>", unsafe_allow_html=True)

    st.markdown(
        "Dữ liệu thương mại **thực tế, đã ẩn danh** của **Olist** (Brazil) — ~**100.000 "
        "đơn hàng** giai đoạn 09/2016–10/2018, gồm **9 bảng quan hệ** liên kết qua khóa "
        "ngoại. Nguồn: [Kaggle](https://www.kaggle.com/datasets/olistbr/brazilian-ecommerce) "
        "· giấy phép CC BY-NC-SA 4.0.")

    ol = d.get("order_lines_view")
    if HAS_PX and ov is not None:
        r1c1, r1c2 = st.columns(2)
        with r1c1:
            s = ov["order_status"].value_counts().reset_index()
            s.columns = ["trạng thái", "số đơn"]
            fig = px.bar(s.sort_values("số đơn"), x="số đơn", y="trạng thái",
                         orientation="h", title="Trạng thái đơn hàng (thang log)",
                         text="số đơn", color="trạng thái",
                         color_discrete_sequence=PALETTE)
            fig.update_xaxes(type="log")
            fig.update_traces(textposition="outside", cliponaxis=False)
            fig.update_layout(showlegend=False)
            st.plotly_chart(style_fig(fig, 300), use_container_width=True)
        with r1c2:
            rv = ov["review_score"].dropna().astype(int).value_counts().sort_index().reset_index()
            rv.columns = ["điểm", "số lượng"]
            rv["điểm"] = rv["điểm"].astype(str)
            fig = px.bar(rv, x="điểm", y="số lượng", title="Phân bố điểm đánh giá (1–5)",
                         color="điểm", color_discrete_map={
                             "1": "#EF4444", "2": "#F97316", "3": "#F59E0B",
                             "4": "#34D399", "5": "#059669"})
            fig.update_layout(showlegend=False)
            st.plotly_chart(style_fig(fig, 300), use_container_width=True)
        r2c1, r2c2 = st.columns(2)
        with r2c1:
            pt = ov["payment_type_primary"].value_counts().reset_index()
            pt.columns = ["phương thức", "số đơn"]
            fig = px.bar(pt, x="số đơn", y="phương thức", orientation="h",
                         title="Phương thức thanh toán", color="phương thức",
                         color_discrete_sequence=PALETTE)
            fig.update_layout(yaxis=dict(autorange="reversed"), showlegend=False)
            st.plotly_chart(style_fig(fig, 300), use_container_width=True)
        with r2c2:
            if ol is not None:
                tc = ol["category"].value_counts().head(10).reset_index()
                tc.columns = ["danh mục", "số dòng"]
                fig = px.bar(tc.sort_values("số dòng"), x="số dòng", y="danh mục",
                             orientation="h", title="Top 10 danh mục sản phẩm",
                             color="danh mục", color_discrete_sequence=PALETTE)
                fig.update_layout(showlegend=False)
                st.plotly_chart(style_fig(fig, 300), use_container_width=True)

    section("Cấu trúc 9 bảng dữ liệu")
    tables = pd.DataFrame([
        ("olist_customers_dataset", "Khách hàng", "customer_id, customer_unique_id, mã bưu chính, thành phố, bang"),
        ("olist_orders_dataset", "Đơn hàng", "trạng thái đơn + mốc thời gian (đặt, duyệt, giao, dự kiến)"),
        ("olist_order_items_dataset", "Dòng đơn", "sản phẩm, người bán, giá bán, phí vận chuyển"),
        ("olist_products_dataset", "Sản phẩm", "danh mục, kích thước, trọng lượng, số ảnh"),
        ("olist_sellers_dataset", "Người bán", "mã bưu chính, thành phố, bang"),
        ("olist_order_payments_dataset", "Thanh toán", "phương thức, số kỳ trả góp, giá trị"),
        ("olist_order_reviews_dataset", "Đánh giá", "điểm 1–5, tiêu đề/bình luận, thời gian"),
        ("olist_geolocation_dataset", "Tọa độ địa lý", "vĩ độ/kinh độ theo tiền tố mã bưu chính"),
        ("product_category_name_translation", "Dịch danh mục", "tên danh mục: Bồ Đào Nha → tiếng Anh"),
    ], columns=["Bảng (CSV)", "Nội dung", "Cột chính"])
    st.dataframe(tables, hide_index=True, use_container_width=True)

    section("Phương pháp & thuật toán phân tích",
            "Quy trình xử lý và kỹ thuật áp dụng cho từng bước")
    st.markdown('<div class="pipe">ETL → RFM → Thống kê suy diễn → Phân cụm → '
                'Luật kết hợp → Machine Learning → Deep Learning → Dashboard</div>',
                unsafe_allow_html=True)
    methods = pd.DataFrame([
        ("1. Làm sạch & hợp nhất (ETL)", "Chuẩn hóa kiểu, khử trùng lặp, gộp đa bảng theo khóa ngoại; tạo 3 view (khách hàng/đơn/dòng đơn)", "pandas, pyarrow"),
        ("2. Đặc trưng RFM", "Recency – Frequency – Monetary + đặc trưng mở rộng; chấm điểm ngũ phân vị & gán nhãn phân khúc", "pandas, numpy"),
        ("3. Thống kê suy diễn", "Chi-square, ANOVA, t-test (+ Kruskal-Wallis, Mann-Whitney, Spearman); effect size + hiệu chỉnh Holm", "scipy, statsmodels"),
        ("4. Phân khúc khách hàng", "Phân cụm K-Means; chọn k bằng Silhouette / Davies-Bouldin / Calinski-Harabasz; trực quan PCA", "scikit-learn"),
        ("5. Luật kết hợp", "Khai phá luật kết hợp FP-Growth (support – confidence – lift)", "mlxtend"),
        ("6. Machine Learning", "Logistic Regression, Random Forest, XGBoost, LightGBM; đánh giá ROC-AUC / PR-AUC / F1; giải thích SHAP", "scikit-learn, xgboost, lightgbm, shap"),
        ("7. Deep Learning", "Mạng nơ-ron nhiều lớp (MLP) dự đoán mức độ hài lòng", "TensorFlow / Keras"),
        ("8. Trực quan hóa", "Dashboard tương tác trình bày toàn bộ kết quả", "streamlit, plotly"),
    ], columns=["Bước", "Kỹ thuật / Thuật toán", "Thư viện"])
    st.dataframe(methods, hide_index=True, use_container_width=True)


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
            fig = px.area(m, x="month", y="doanh_thu", markers=True,
                          title="Doanh thu theo tháng",
                          labels={"month": "Tháng", "doanh_thu": "Doanh thu (R$)"})
            fig.update_traces(line_color="#0EA5E9", fillcolor="rgba(14,165,233,.14)")
            st.plotly_chart(style_fig(fig), use_container_width=True)
    with c2:
        top = (deliv.groupby("customer_state")["order_value"].sum()
               .sort_values(ascending=False).head(8).reset_index())
        top.columns = ["Bang", "Doanh thu"]
        if HAS_PX:
            fig = px.bar(top, x="Doanh thu", y="Bang", orientation="h",
                         title="Top bang theo doanh thu", color="Bang",
                         color_discrete_sequence=PALETTE)
            fig.update_layout(showlegend=False, yaxis=dict(autorange="reversed"))
            st.plotly_chart(style_fig(fig), use_container_width=True)

    tot = deliv["order_value"].sum()
    bs = deliv.groupby("customer_state")["order_value"].sum().sort_values(ascending=False)
    note([
        f"<b>{bs.index[0]}</b> (São Paulo) dẫn đầu tuyệt đối với khoảng "
        f"<b>{bs.iloc[0]/tot:.0%}</b> tổng doanh thu, bỏ xa các bang còn lại.",
        f"Top 3 bang (<b>{', '.join(bs.head(3).index)}</b>) chiếm tới "
        f"<b>{bs.head(3).sum()/tot:.0%}</b> doanh thu → thị trường tập trung mạnh ở vùng "
        f"Đông Nam Brazil.",
        "Doanh thu <b>tăng trưởng mạnh từ đầu 2017</b>, đạt đỉnh ~1,1–1,2 triệu R$/tháng "
        "giai đoạn cuối 2017–2018; năm 2016 gần như bằng 0 (dữ liệu mới bắt đầu) và tháng "
        "cuối chuỗi sụt giảm do dữ liệu chưa đầy đủ.",
        f"Tỉ lệ mua lại chỉ <b>{cv['is_repeat_buyer'].mean():.1%}</b> — khách chủ yếu mua "
        "một lần, gợi ý dư địa lớn cho chương trình giữ chân (loyalty).",
    ])


def tab_rfm(d):
    rfm, seg, prof = d["rfm_features"], d["customer_segments"], d["segment_profiles"]
    if rfm is None:
        st.warning("Thiếu rfm_features."); return
    section("RFM & Phân khúc khách hàng",
            "Chấm điểm RFM, phân cụm K-Means và chân dung từng nhóm")
    df = rfm.copy()
    if seg is not None:
        df = df.merge(seg[["customer_unique_id", "persona"]], on="customer_unique_id", how="left")
    states = ["(Tất cả)"] + sorted(df["customer_state"].dropna().unique().tolist())
    pick = st.selectbox(
        "Lọc theo bang (mã bang của Brazil — UF)", states,
        format_func=lambda s: s if s == "(Tất cả)" else f"{s} — {UF_NAMES.get(s, s)}")
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
                             title="Recency vs Monetary theo phân khúc", opacity=0.6,
                             color_discrete_sequence=PALETTE,
                             labels={"recency_days": "Recency – ngày từ lần mua cuối",
                                     "monetary": "Monetary – tổng chi tiêu (R$)",
                                     "rfm_segment": "Phân khúc"})
            fig.update_yaxes(type="log")
            st.plotly_chart(style_fig(fig), use_container_width=True)

    note([
        "<b>Biểu đồ trái</b> (số khách theo phân khúc): phần lớn khách rơi vào "
        "<b>New/Promising</b> (mới mua, một lần) cùng các nhóm giá trị thấp (Hibernating, "
        "Lost, Potential Loyalist); nhóm <b>Champions/Loyal Customers rất ít</b> — phản ánh "
        "đặc thù Olist khách chủ yếu mua một lần.",
        "<b>Biểu đồ phải</b>: trục X = <b>Recency</b> (số ngày từ lần mua cuối, càng nhỏ càng "
        "gần đây), trục Y = <b>Monetary</b> (tổng chi tiêu, thang log), màu = phân khúc. Các "
        "nhóm tách rõ theo recency (New/Promising bên trái, Lost bên phải) còn chi tiêu trải "
        "đều → <b>recency là yếu tố phân biệt chính</b>.",
    ])

    section("Ý nghĩa các phân khúc RFM",
            "RFM = Recency (gần đây) – Frequency (tần suất) – Monetary (chi tiêu)")
    order = ["Champions", "Loyal Customers", "Potential Loyalist", "New / Promising",
             "At Risk", "Hibernating", "Lost"]
    gloss = pd.DataFrame([(s, SEGMENT_DESC[s]) for s in order],
                         columns=["Phân khúc", "Ý nghĩa & gợi ý hành động"])
    st.dataframe(gloss, hide_index=True, use_container_width=True)

    if prof is not None:
        section("Chân dung phân khúc (K-Means)",
                "Phân cụm khách theo đặc trưng RFM; mỗi cụm là một 'chân dung'")
        st.dataframe(prof, use_container_width=True, hide_index=True)
        if HAS_PX:
            pf = prof.copy()
            pf["Cụm"] = "Cụm " + pf["cluster"].astype(str)
            fig = px.scatter(pf, x="recency", y="monetary", size="n", color="Cụm",
                             text="persona", size_max=60, color_discrete_sequence=PALETTE,
                             title="Bản đồ phân khúc K-Means (kích thước bong bóng = số khách)",
                             labels={"recency": "Recency TB (ngày)",
                                     "monetary": "Chi tiêu TB (R$)"})
            fig.update_traces(textposition="top center")
            st.plotly_chart(style_fig(fig), use_container_width=True)
        big = prof.loc[prof["n"].idxmax()]
        vip = prof.loc[prof["monetary"].idxmax()]
        low = prof.loc[prof["review"].idxmin()]
        note([
            f"K-Means chia khách thành <b>{len(prof)} cụm</b>. Cụm đông nhất khoảng "
            f"<b>{fmt_int(big['n'])}</b> khách (chân dung: {big['persona']}).",
            f"Cụm chi tiêu cao nhất (~<b>{vip['monetary']:.0f} R$</b>) là nhóm giá trị nhất — "
            "ưu tiên giữ chân & bán chéo.",
            f"Cụm có điểm đánh giá thấp nhất (~<b>{low['review']:.1f}/5</b>) là nhóm khách kém "
            "hài lòng — cần cải thiện giao hàng/chất lượng để tránh rời bỏ.",
            "Tần suất mua gần như bằng <b>1</b> ở hầu hết cụm → các cụm khác nhau chủ yếu ở "
            "<b>mức chi tiêu</b> và <b>độ hài lòng</b>, đúng đặc thù mua một lần của Olist.",
        ])

    st.download_button("⬇️ Tải RFM (CSV)", df.to_csv(index=False).encode("utf-8-sig"),
                       "rfm_filtered.csv", "text/csv")


def tab_stats(d):
    sr = d["stat_results"]
    if sr is None:
        st.warning("Thiếu stat_results."); return
    section("Kiểm định thống kê — 8 giả thuyết",
            "Mỗi giả thuyết dùng kiểm định tham số (ANOVA/t-test/Chi-square) và phi-tham số")

    def fp(p):
        p = pd.to_numeric(p, errors="coerce")
        if pd.isna(p):
            return ""
        return "< 0.0001" if p < 1e-4 else f"{p:.4f}"

    disp = sr.copy()
    for c in ["p_param", "p_nonparam", "p_holm", "levene_p"]:
        if c in disp:
            disp[c] = disp[c].map(fp)
    for c in ["es_param", "es_nonparam"]:
        if c in disp:
            disp[c] = pd.to_numeric(disp[c], errors="coerce").round(3)
    st.dataframe(disp, use_container_width=True, hide_index=True)
    st.markdown('<span class="small-note">p_holm &lt; 0.05 ⇒ có ý nghĩa thống kê. '
                'effect size cho biết độ mạnh mối liên hệ (không phụ thuộc cỡ mẫu).</span>',
                unsafe_allow_html=True)

    # Biểu đồ độ mạnh effect size
    eff = sr.copy()
    eff["effect"] = pd.to_numeric(eff["es_nonparam"], errors="coerce")
    eff["effect"] = eff["effect"].fillna(pd.to_numeric(eff["es_param"], errors="coerce")).abs()
    eff["Ý nghĩa"] = (pd.to_numeric(eff["p_holm"], errors="coerce") < 0.05).map(
        {True: "Có ý nghĩa", False: "Không"})
    if HAS_PX:
        fig = px.bar(eff.sort_values("effect"), x="effect", y="id", orientation="h",
                     color="Ý nghĩa", text="effect", hover_data=["giả thuyết"],
                     color_discrete_map={"Có ý nghĩa": "#059669", "Không": "#94A3B8"},
                     title="Độ mạnh mối liên hệ (effect size) theo giả thuyết",
                     labels={"effect": "Effect size (|giá trị|)", "id": "Giả thuyết"})
        fig.update_traces(texttemplate="%{text:.3f}", textposition="outside", cliponaxis=False)
        st.plotly_chart(style_fig(fig), use_container_width=True)

    n_sig = int((pd.to_numeric(sr["p_holm"], errors="coerce") < 0.05).sum())
    strong = eff.loc[eff["effect"].idxmax()]
    note([
        f"<b>{n_sig}/{len(sr)}</b> giả thuyết có ý nghĩa thống kê (p_holm &lt; 0.05). Do cỡ mẫu "
        "rất lớn (~100K), gần như mọi p-value đều cực nhỏ ⇒ <b>phải đọc effect size</b> để biết "
        "mối liên hệ mạnh hay yếu, không chỉ nhìn p-value.",
        f"Mối liên hệ <b>mạnh nhất</b>: <b>{strong['id']} — {strong['giả thuyết']}</b> "
        f"(effect size ≈ {strong['effect']:.3f}).",
        "Phần lớn effect size ở mức <b>nhỏ</b> → có khác biệt thật nhưng độ lớn khiêm tốn; "
        "cần thận trọng khi suy ra hành động nghiệp vụ.",
    ])

    section("Tương quan giữa các biến số")
    show_fig("07_tuong_quan", "Ma trận tương quan (đơn đã giao)")
    note([
        "<b>order_value ≈ items_price_total</b> (hệ số 1.00): doanh thu đơn = giá hàng + phí "
        "ship nên hai biến gần như trùng nhau (đa cộng tuyến — tránh dùng đồng thời trong mô "
        "hình tuyến tính).",
        "<b>Thời gian giao (delivery_days) tương quan ÂM với điểm đánh giá (−0.33)</b> — rõ "
        "nhất: <b>giao càng lâu, khách đánh giá càng thấp</b>; đây là đòn bẩy quan trọng để "
        "tăng mức độ hài lòng.",
        "Đơn nhiều mặt hàng gắn với đánh giá thấp hơn một chút (−0.12); các biến còn lại tương "
        "quan yếu với điểm đánh giá.",
    ])


def tab_cohort(d):
    section("Cohort & Chuỗi thời gian", "Xu hướng theo tháng và tỉ lệ giữ chân khách")
    ov = d.get("orders_view")
    if ov is not None and HAS_PX:
        deliv = ov[ov["order_status"] == "delivered"]
        m = (deliv.assign(month=pd.to_datetime(deliv["order_purchase_timestamp"])
                          .dt.to_period("M").dt.to_timestamp())
             .groupby("month").agg(so_don=("order_id", "nunique")).reset_index())
        fig = px.bar(m, x="month", y="so_don", title="Số đơn theo tháng",
                     labels={"month": "Tháng", "so_don": "Số đơn"},
                     color_discrete_sequence=[PRIMARY])
        st.plotly_chart(style_fig(fig), use_container_width=True)
    c1, c2 = st.columns(2)
    with c1:
        show_fig("02_xu_huong_thang", "Số đơn & doanh thu theo tháng")
    with c2:
        show_fig("10_cohort", "Cohort retention (tỉ lệ quay lại theo tháng)")
    note([
        "Lượng đơn <b>tăng nhanh từ 2017</b> và duy trì mức cao trong 2018 — giai đoạn Olist "
        "mở rộng mạnh.",
        "Ma trận cohort cho thấy <b>tỉ lệ quay lại rất thấp</b> (các ô sau tháng 0 gần như trống) "
        "→ khách gần như chỉ mua một lần; giữ chân là bài toán trọng tâm.",
        "Gợi ý: email/ưu đãi sau mua lần đầu và chương trình loyalty để kéo cohort quay lại.",
    ])


def tab_assoc(d):
    ar = d["assoc_rules"]
    section("Luật kết hợp giữa các danh mục", "Gợi ý bán chéo dựa trên hành vi mua kèm")
    st.markdown('<span class="small-note"><b>Support</b>: tỉ lệ giỏ chứa cả A và B · '
                '<b>Confidence</b>: xác suất mua B khi đã mua A · '
                '<b>Lift &gt; 1</b>: A và B đi cùng nhau nhiều hơn ngẫu nhiên.</span>',
                unsafe_allow_html=True)
    if ar is None or ar.empty:
        st.info("Giỏ hàng Olist rất thưa (đa số 1 danh mục/đơn) nên ít/không có luật — "
                "bản thân điều này là một phát hiện: khách ít mua kèm chéo danh mục.")
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
    lines = [
        f"Tìm được <b>{len(ar)}</b> luật có lift &gt; 1 — số lượng ít, đúng đặc thù giỏ hàng "
        "Olist rất thưa.",
        "Cặp có <b>lift cao</b> là ứng viên <b>bán chéo</b>: khi khách mua nhóm A, gợi ý kèm nhóm B.",
        "Đây là quan hệ <b>tương quan</b>, không phải nhân quả — nên A/B test trước khi triển khai.",
    ]
    if len(f):
        top = f.iloc[0]
        lines.insert(1, f"Luật mạnh nhất: <b>{top['antecedents']} → {top['consequents']}</b> "
                        f"(lift ≈ {top['lift']:.2f}).")
    note(lines)


def tab_models(d):
    mm = d["model_metrics"]
    section("Mô hình dự đoán", "Machine Learning (4 mô hình) + Deep Learning; nhấn PR-AUC")
    if mm is not None:
        st.dataframe(mm, use_container_width=True, hide_index=True)
        if HAS_PX and {"level_0", "level_1", "PR_AUC"}.issubset(mm.columns):
            fig = px.bar(mm, x="level_1", y="PR_AUC", color="level_0", barmode="group",
                         title="PR-AUC theo mô hình & bài toán",
                         color_discrete_sequence=PALETTE,
                         labels={"level_1": "Mô hình", "PR_AUC": "PR-AUC",
                                 "level_0": "Bài toán"})
            st.plotly_chart(style_fig(fig), use_container_width=True)
    c1, c2 = st.columns(2)
    with c1:
        show_fig("13_ml_hailong", "ROC & PR — Dự đoán hài lòng")
        show_fig("14_feature_importance", "Mức ảnh hưởng đặc trưng (SHAP)")
    with c2:
        show_fig("13_ml_mualai", "ROC & PR — Dự đoán mua lại")
        show_fig("15_dl_duong_hoc", "Deep Learning — đường học")
    show_fig("16_so_sanh_mo_hinh", "So sánh ML vs Deep Learning")
    note([
        "<b>Dự đoán hài lòng</b> đạt PR-AUC cao (~0.85–0.9) — dự báo tốt khách hài lòng "
        "(lớp dương ~78%); yếu tố quan trọng nhất là <b>thời gian giao & giao trễ</b> (xem SHAP).",
        "<b>Dự đoán mua lại</b> rất khó: PR-AUC thấp (~0.02–0.03) do <b>mất cân bằng nặng</b> "
        "(~3% mua lại) và tín hiệu yếu từ đơn đầu — khớp kết luận 'khách mua một lần'.",
        "Gradient boosting (LightGBM/XGBoost) và mạng nơ-ron cho kết quả tương đương; với dữ "
        "liệu bảng cỡ này, <b>boosting là lựa chọn hợp lý</b> (nhanh, dễ giải thích bằng SHAP).",
    ])


def tab_geo(d):
    section("Bản đồ địa lý theo bang",
            "Doanh thu (kích thước bong bóng) & mức hài lòng (màu) theo bang Brazil")
    ov = d.get("orders_view")
    if ov is None:
        st.warning("Thiếu orders_view."); return
    deliv = ov[ov["order_status"] == "delivered"]
    g = deliv.groupby("customer_state").agg(
        doanh_thu=("order_value", "sum"), so_don=("order_id", "nunique"),
        danh_gia=("review_score", "mean")).reset_index()
    g["lat"] = g["customer_state"].map(lambda s: STATE_CENTROIDS.get(s, (None, None))[0])
    g["lon"] = g["customer_state"].map(lambda s: STATE_CENTROIDS.get(s, (None, None))[1])
    g["Bang"] = g["customer_state"].map(lambda s: f"{s} — {UF_NAMES.get(s, s)}")
    g = g.dropna(subset=["lat", "lon"])
    if HAS_PX and len(g):
        fig = px.scatter_geo(
            g, lat="lat", lon="lon", size="doanh_thu", color="danh_gia",
            hover_name="Bang", size_max=45, color_continuous_scale="RdYlGn",
            hover_data={"doanh_thu": ":,.0f", "so_don": ":,", "danh_gia": ":.2f",
                        "lat": False, "lon": False},
            title="Doanh thu & điểm đánh giá TB theo bang")
        fig.update_geos(scope="south america", showcountries=True,
                        landcolor="#EFE7D5", bgcolor="rgba(0,0,0,0)",
                        fitbounds="locations")
        st.plotly_chart(style_fig(fig, 480), use_container_width=True)
    tbl = g[["Bang", "doanh_thu", "so_don", "danh_gia"]].sort_values(
        "doanh_thu", ascending=False).round({"danh_gia": 2})
    st.dataframe(tbl, hide_index=True, use_container_width=True)
    tot = g["doanh_thu"].sum()
    note([
        f"<b>{g.sort_values('doanh_thu', ascending=False).iloc[0]['Bang']}</b> đóng góp lớn "
        f"nhất (~{g['doanh_thu'].max()/tot:.0%} doanh thu) — thị trường tập trung ở vùng "
        "Đông Nam (SP, RJ, MG).",
        "Các bang phía Bắc/Đông Bắc có doanh thu thấp và thường <b>điểm đánh giá thấp hơn</b> "
        "(màu ngả đỏ) — có thể do khoảng cách giao hàng xa hơn.",
        "Gợi ý: tối ưu logistics cho vùng xa để cải thiện hài lòng & mở rộng thị phần.",
    ])


def tab_conclusion(d):
    section("Kết luận & Khuyến nghị", "Tổng hợp phát hiện chính và đề xuất hành động")
    ov, cv = d.get("orders_view"), d.get("customers_view")
    repeat = f"{cv['is_repeat_buyer'].mean():.1%}" if cv is not None else "~3%"
    st.markdown("#### 🔑 Kết luận chính")
    note([
        "Olist <b>tăng trưởng mạnh</b> 2017–2018 nhưng doanh thu tập trung ở vùng <b>Đông Nam "
        "Brazil</b> (SP dẫn đầu áp đảo).",
        f"Khách <b>chủ yếu mua một lần</b> (tỉ lệ mua lại chỉ {repeat}) — cơ hội lớn cho giữ chân.",
        "<b>Thời gian giao hàng</b> là yếu tố ảnh hưởng mạnh nhất tới mức hài lòng "
        "(tương quan −0.33; nổi bật trong SHAP) → đòn bẩy chính để tăng đánh giá.",
        "Giỏ hàng thưa → ít mua kèm chéo; mô hình dự đoán hài lòng tốt, dự đoán mua lại khó "
        "do mất cân bằng nặng.",
    ])

    section("Khuyến nghị theo phân khúc khách hàng")
    rec = pd.DataFrame([
        ("Champions / VIP", "Ưu đãi đặc quyền, chăm sóc riêng, giữ chân & bán chéo cao cấp."),
        ("Loyal / Potential Loyalist", "Chương trình tích điểm, upsell theo sở thích."),
        ("New / Promising", "Email chào mừng + ưu đãi lần mua thứ 2, cá nhân hóa gợi ý."),
        ("At Risk / Hibernating", "Chiến dịch win-back: voucher, nhắc nhở, sản phẩm phù hợp."),
        ("Lost", "Kích hoạt lại có chọn lọc (chi phí thấp) hoặc chấp nhận rời bỏ."),
    ], columns=["Phân khúc", "Đề xuất hành động"])
    st.dataframe(rec, hide_index=True, use_container_width=True)

    section("Khuyến nghị vận hành & kinh doanh")
    note([
        "<b>Cải thiện logistics</b> (rút ngắn thời gian giao, giảm giao trễ) — tác động lớn "
        "nhất tới hài lòng, đặc biệt ở vùng xa.",
        "<b>Bán chéo</b> theo các luật kết hợp có lift cao; thử nghiệm gợi ý sản phẩm kèm.",
        "<b>Giữ chân</b>: xây chương trình loyalty & tự động hóa email sau mua để tăng mua lại.",
        "Tập trung nguồn lực marketing ở Đông Nam nhưng <b>mở rộng có chọn lọc</b> sang vùng "
        "tiềm năng khác.",
    ])

    section("Hạn chế & hướng phát triển")
    note([
        "Dữ liệu một thị trường (Brazil) và một giai đoạn (2016–2018); tỉ lệ mua lại thấp gây "
        "khó cho mô hình repurchase.",
        "Hướng phát triển: thêm dữ liệu hành vi duyệt web, mô hình CLV/churn, hệ gợi ý sản phẩm, "
        "và cập nhật dữ liệu theo thời gian thực.",
    ])


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
NAV = [("00 · Giới thiệu", "info-circle-fill", tab_intro),
       ("01 · Tổng quan", "bar-chart-fill", tab_overview),
       ("02 · RFM & Phân khúc", "people-fill", tab_rfm),
       ("03 · Thống kê", "clipboard-data", tab_stats),
       ("04 · Cohort/Thời gian", "graph-up", tab_cohort),
       ("05 · Địa lý", "geo-alt-fill", tab_geo),
       ("06 · Luật kết hợp", "link-45deg", tab_assoc),
       ("07 · Mô hình", "cpu-fill", tab_models),
       ("08 · Tra cứu KH", "search", tab_lookup),
       ("09 · Kết luận", "clipboard-check-fill", tab_conclusion)]

MENU_STYLES = {
    "container": {"padding": "4px 0", "background-color": "#0E6E63"},
    "icon": {"color": "#F1B24A", "font-size": "14px"},
    "nav-link": {"font-family": "'IBM Plex Mono', monospace", "font-size": "12.5px",
                 "font-weight": "600", "text-transform": "uppercase",
                 "letter-spacing": "0.07em", "color": "#F3EFE6", "text-align": "left",
                 "margin": "2px 0", "border-radius": "6px", "--hover-color": "#0B5A52"},
    "nav-link-selected": {"background-color": "#EF5B4C", "color": "#FFFFFF",
                          "font-weight": "700"},
}

HERO = """<div class="mast">
<div class="mast-strip"><span>Khai thác dữ liệu &amp; ứng dụng · ĐHSP TP.HCM · 2026</span>
<span>Customer Analytics &amp; Segmentation</span></div>
<div class="mast-title">Olist <span class="ac">Analytics</span></div>
<div class="mast-sub">Phân tích hành vi &amp; phân khúc khách hàng · Customer Behavior Intelligence</div>
<div class="mast-rule"><i></i></div>
<div class="mast-strip"><span>GVHD: TS. Nguyễn Tấn Trung · Đồ án Phân tích dữ liệu</span>
<span>Olist · ~100K khách hàng · 8 giả thuyết · ML + Deep Learning</span></div></div>"""

SIDEBAR_INFO = """<div class="credit">
<div class="c-school">Trường Đại học Sư phạm<br>Thành phố Hồ Chí Minh</div>
<div class="c-dept">Khoa Công nghệ thông tin</div>
<div class="c-meta">Môn <b>Phân tích dữ liệu</b><br>Khóa 36 (2025–2027)</div>
<div class="c-meta"> <b> Năm học</b> 2025–2026  </div>
<div class="c-role">Học viên thực hiện</div>
<ol class="c-list">
<li>Tăng Ngọc Phụng — KHMT836027</li>
<li>Hoàng Châu Ngọc Phương — KHMT836028</li>
<li>Lê Thị Mai Len — KHMT836015</li>
</ol>
<div class="c-role">Giảng viên hướng dẫn</div>
<div class="c-gv">TS. Nguyễn Tấn Trung</div>
</div>"""


def main():
    global FIG_DIR
    st.markdown(CSS, unsafe_allow_html=True)
    labels = [n[0] for n in NAV]

    with st.sidebar:
        st.markdown('<div class="brand">Olist <span class="ac">Analytics</span></div>'
                    '<div class="nav-lbl">Navigation</div>', unsafe_allow_html=True)
        if HAS_MENU:
            choice = option_menu(None, labels, icons=[n[1] for n in NAV],
                                 default_index=0, styles=MENU_STYLES)
        else:
            choice = st.radio("Điều hướng", labels, label_visibility="collapsed")

    detected = auto_root()
    root = detected if detected else Path("outputs")
    FIG_DIR = root / "figures"

    st.markdown(HERO, unsafe_allow_html=True)

    if not has_data(root):
        st.error(f"Không thấy dữ liệu parquet trong `{root/'data'}`.")
        st.markdown("Chạy notebook phân tích để sinh thư mục `outputs/`, hoặc đặt biến "
                    "môi trường `OLIST_OUTPUTS`. Đã thử các vị trí:")
        st.code("\n".join(str(p / "data") for p in candidate_roots()))
        return

    d0 = load_all(str(root / "data"))

    # --- Bộ lọc toàn cục ---
    regions, dr = [], None
    ov0 = d0.get("orders_view")
    with st.sidebar:
        st.markdown("---")
        st.markdown("##### 🔎 Bộ lọc")
        regions = st.multiselect("Vùng miền", REGIONS, placeholder="Tất cả vùng")
        if ov0 is not None:
            ts = pd.to_datetime(ov0["order_purchase_timestamp"]).dt.date.dropna()
            dmin, dmax = ts.min(), ts.max()
            dr = st.date_input("Khoảng thời gian", (dmin, dmax),
                               min_value=dmin, max_value=dmax)
        st.caption("Áp cho: Tổng quan · RFM · Địa lý · Cohort · Tra cứu. "
                   "Thống kê / Luật kết hợp / Mô hình dùng dữ liệu toàn bộ.")
        st.markdown("---")
        st.markdown(SIDEBAR_INFO, unsafe_allow_html=True)

    d = apply_filters(d0, regions, dr)
    fn = {n[0]: n[2] for n in NAV}[choice]
    fn(d)


if __name__ == "__main__":
    main()
