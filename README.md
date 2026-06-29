# 🛒 Phân tích hành vi mua sắm & phân khúc khách hàng TMĐT (Olist)

Dashboard **Streamlit** trực quan hóa kết quả đề tài *Phân tích hành vi mua sắm và
phân khúc khách hàng trên nền tảng thương mại điện tử*, dùng bộ dữ liệu
**Brazilian E-Commerce Public Dataset by Olist** (~100.000 đơn hàng, 2016–2018).

> Đây là phần trình bày (nhóm sản phẩm đầu ra thứ 7). Toàn bộ phân tích (ETL → RFM →
> thống kê suy diễn → phân cụm → luật kết hợp → mô hình ML/DL) được thực hiện trong
> notebook `Olist_Phan_Tich.ipynb`; dashboard này chỉ **đọc kết quả** đã sinh trong `outputs/`.

---

## ✨ Tính năng dashboard
| Tab | Nội dung |
|-----|----------|
| **Tổng quan** | KPI (doanh thu, số đơn, số khách, đánh giá TB, tỉ lệ mua lại) + doanh thu theo tháng |
| **RFM & Phân khúc** | Bảng RFM, phân khúc, chân dung (persona) theo cụm K-Means, lọc theo bang, tải CSV |
| **Thống kê** | Kết quả 8 giả thuyết (chi-square / ANOVA / t-test) kèm p-value + effect size |
| **Cohort / Thời gian** | Biểu đồ cohort retention & chuỗi thời gian |
| **Luật kết hợp** | Bảng luật (support / confidence / lift) + lọc tương tác |
| **Mô hình** | So sánh 4 mô hình ML + SHAP + Deep Learning (đường ROC/PR, feature importance) |
| **Tra cứu KH** | Tìm 1 khách hàng theo `customer_unique_id` |

---

## 🚀 Chạy thử

### Cách 1 — Streamlit Community Cloud (khuyến nghị)
1. Vào [share.streamlit.io](https://share.streamlit.io) → **New app**.
2. Chọn repo này, branch `master`, **Main file path:** `streamlit_app.py`.
3. **Deploy** → app tự đọc dữ liệu trong `outputs/data`.

### Cách 2 — Chạy local
```bash
pip install -r requirements.txt
streamlit run streamlit_app.py
```
Mở trình duyệt tại `http://localhost:8501`.

> App tự dò thư mục `outputs/` (cạnh file app / thư mục cha / cwd). Có thể nhập tay
> đường dẫn ở sidebar hoặc đặt biến môi trường `OLIST_OUTPUTS`.

---

## 📂 Cấu trúc repo
```
streamlit_app.py        # ứng dụng Streamlit (7 tab)
requirements.txt        # thư viện cần cài
outputs/
├── data/               # bảng kết quả (.parquet): RFM, segments, stat_results, ...
├── figures/            # biểu đồ (.png)
└── tables/             # bảng kết quả (.csv)
```

---

## 🧰 Công nghệ
`Python` · `Streamlit` · `pandas` · `pyarrow` · `plotly` · (phân tích: `scikit-learn`,
`statsmodels`, `mlxtend`, `xgboost`, `lightgbm`, `shap`, `tensorflow`)

## 📊 Dữ liệu
Brazilian E-Commerce Public Dataset by Olist — [Kaggle](https://www.kaggle.com/datasets/olistbr/brazilian-ecommerce)
(giấy phép CC BY-NC-SA 4.0, dùng cho mục đích học thuật).

## 👤 Tác giả
**Trường Đại học Sư phạm Thành Phố Hồ Chí Minh**

**Tăng Ngọc Phụng - KHMT836027** — Học viên cao học Khoa học máy tính (hướng ứng dụng) ·

**Hoàng Châu Ngọc Phương - KHMT836028** — Học viên cao học Khoa học máy tính (hướng ứng dụng) ·

**Lê Thị Mai Len - KHMT836015** — Học viên cao học Khoa học máy tính (hướng ứng dụng) ·

**GVHD: ** TS. Nguyễn Tấn Trung

Đồ án môn Phân tích dữ liệu.
