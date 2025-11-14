# 🦆 DuckIQ – Commercial Analytics Hub

**Data Health • Promotions • Promo Trends • Pricing Index**

A unified analytics solution combining:

✅ **A Streamlit dashboard** for interactive commercial analytics  
✅ **A FastAPI backend** exposing clean JSON endpoints  
✅ **DuckDB** as an embedded analytical engine

---

## 1. 🧠 Project Summary

This project implements a **lightweight commercial analytics platform** focused on four core retail insights:

1. **Data Health Monitoring**
2. **Promotions Performance**
3. **Promo Trends Over Time**
4. **Price Index & Competitor Price Comparison**

It satisfies the interview requirement by providing **both**:

* **(2A)** A simple, clean **Streamlit dashboard**
* **(2B)** A simple **FastAPI service** exposing JSON endpoints

The system uses:

* **DuckDB** for fast local OLAP-style querying
* **FastAPI** for structured JSON APIs
* **Streamlit** for interactive analysis
* **ETL logic inside the `app/` folder** to compute metrics

---

## 2. 🚀 Getting Started

Clone the repository:

```bash
git clone https://github.com/KinyuaMwathi/DuckIQ.git
cd DuckIQ
```

Create and activate a virtual environment:

```bash
python -m venv venv
source venv/bin/activate   # Mac/Linux
venv\Scripts\activate      # Windows
```

Install dependencies:

```bash
pip install -r requirements.txt
```

---

## 2A. 📊 Running the Streamlit Dashboard

Launch the analytics dashboard:

```bash
streamlit run streamlit_app/app.py
```

This loads a **4-tab unified UI**:

* **Data Health**
* **Promotions**
* **Promo Trends**
* **Pricing Index**

All computations pull from the latest **`data/duckiq.duckdb`** database.

---

## 2B. 🌐 Running the FastAPI JSON Backend

Start the API (note the correct module import):

```bash
uvicorn app.main:app --reload
```

The API will run at:

```
http://127.0.0.1:8000
```

Swagger docs available at:

```
http://127.0.0.1:8000/docs
```

### Available Endpoints

| Endpoint                            | Description                                             |
| ----------------------------------- | ------------------------------------------------------- |
| `/data_quality`                     | Computes & returns store health metrics                 |
| `/promo_summary`                    | Computes uplift, coverage, price impact for promotions  |
| `/price_index`                      | Computes Bidco price index vs competitor pricing        |

Every endpoint writes its results into DuckDB so that both **Streamlit** and **FastAPI** share the same analytic layer.

---

## 3. 🧱 Architecture Overview

```
                          ┌────────────────────────┐
                          │        Streamlit        │
                          │  (Frontend Dashboard)   │
                          └─────────────┬───────────┘
                                        │
                                        ▼
                              Shared Analytical Layer
                                        │
                                        ▼
┌────────────────────────┐     ┌────────────────────────┐
│        FastAPI         │     │         ETL/Engines     │
│  (/data_quality etc.)  │◄──► │ health_engine, promo,   │
└─────────────┬──────────┘     │ price_index calculations│
              │                └─────────────┬───────────┘
              ▼                              │
                           ┌────────────────────────┐
                           │         DuckDB          │
                           │  (data/duckiq.duckdb)   │
                           └────────────────────────┘
```

### Why this design?

* **Single source of truth** → Streamlit and FastAPI both read from DuckDB
* **Portable & reproducible** → DuckDB requires no server
* **Fast queries** → OLAP-optimized columnar engine
* **Testable** → FastAPI endpoints can be tested independently

---

## 4. 🧪 Approach, Assumptions & Reasoning

### ✔ Commercial Focus

Brand decisions come from:

* **Healthy retail data**
* **Strong promo execution**
* **Competitive pricing insights**

This guided all the metrics chosen.

### ✔ Data Health Logic

Assumptions:

* Missing RRP, extreme prices, negative quantities all reduce trust
* A 0–100 "health score" makes performance comparable
* Supplier drift flags highlight upstream issues

### ✔ Promotions Logic

Assumptions:

* Uplift = (Promo Volume – Baseline Volume) / Baseline
* Coverage = % stores participating
* Price impact = difference between promo and baseline price

Brands learn:

* Which SKUs are working
* Whether promos are deep enough
* Whether participation is wide across stores

### ✔ Price Index Logic

Assumptions:

* Bidco = base brand
* Competitor index = competitor price / Bidco price × 100
* Over 105 = premium; 95–105 = near-market; <95 = discounted

Brands learn:

* Are they competitively priced?
* Where are they overpriced by store/sub-dept?

---

## 5. 📂 Folder Structure

```
DuckIQ/
│
├── app/                     # FastAPI backend engines & routes
│   ├── main.py
│   ├── routes_*.py
│   ├── *_engine.py
│   └── db.py
│
├── streamlit_app/           # Unified UI
│   ├── app.py
│   ├── data_health_dashboard.py
│   ├── promo_dashboard.py
│   ├── promo_trends_dashboard.py
│   └── price_index_dashboard.py
│
├── data/
│   └── duckiq.duckdb        # Shared analytics DB
│
├── requirements.txt
└── README.md
```

---

## 6. 🔍 What a Brand Can Learn

### 📈 From Data Health

* Gaps in RRP, suppliers, pricing
* Stores or suppliers with low data integrity
* Alerts on supplier drift

### 🏷️ From Promotions

* Which SKUs give highest uplift
* Whether promos are deep enough
* Whether they're reaching enough stores

### 📊 From Promo Trends

* Multi-run view of uplift, coverage, price impact
* Supplier comparisons

### 💰 From Price Index

* How competitively Bidco is priced
* Store-level gaps
* Competitor undercutting

---

## 7. 📬 Contact

Prepared by **Charles Mwathi**  

---