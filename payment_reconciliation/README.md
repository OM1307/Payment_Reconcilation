# Reconcilify: Intelligent Payment Reconciliation Engine

An end-to-end payment reconciliation platform built to automatically identify discrepancies between platform transaction logs and bank settlement records. The system utilizes a high-performance Python (Pandas) backend to run complex aggregation logic and a beautiful, modern React frontend to visualize the results.

## ✨ Features

- **Automated Discrepancy Detection**: The Pandas-driven engine identifies 6 specific types of financial edge cases:
  - **Cross-Month Settlements**: Transactions made at the end of a month but settled by the bank in the following month.
  - **Rounding Differences**: Minor fractional differences that only become apparent when the bank groups multiple transactions into a single settlement batch.
  - **Duplicate Entries**: Accidental double-records in either the bank or platform datasets.
  - **Unmatched Refunds**: Refunds issued on the platform without a corresponding bank deduction.
  - **Missing in Bank**: Platform sales that the bank failed to settle.
  - **Missing in Platform**: Unrecognized bank settlements with no originating platform transaction.
- **Interactive Dashboard**: A responsive, glassmorphism-styled UI featuring an interactive Pie Chart (via Recharts) and dynamic, global search filtering to easily sort through thousands of rows of discrepancies.
- **Synthetic Test Data Generator**: A built-in robust Python generator that creates rigorous test datasets (in INR) containing hundreds of normal transactions interspersed with explicitly planted edge-case discrepancies for thorough testing.

## 🛠️ Technology Stack

- **Backend**: Python 3.12+, FastAPI, Uvicorn, Pandas, NumPy
- **Frontend**: React 19, Vite, Recharts, Lucide React, Vanilla CSS (Glassmorphism aesthetics)

## 📁 Project Structure

```
payment_reconciliation/
├── backend/
│   ├── data/
│   │   └── generator.py        # Generates synthetic CSVs with planted discrepancies
│   ├── model/
│   │   └── reconciliation.py   # Core Pandas logic for merging and calculating gaps
│   ├── main.py                 # FastAPI server and endpoint definitions
│   └── requirements.txt        # Backend dependencies
├── frontend/
│   ├── src/
│   │   ├── App.jsx             # Main dashboard UI, charts, and API integrations
│   │   └── index.css           # Glassmorphism styling and animations
│   ├── package.json            # Frontend dependencies
│   └── vite.config.js
└── generated/                  # Output directory for test CSVs
```

## 🚀 Getting Started

### 1. Start the Backend (FastAPI)

Open a terminal and navigate to the `backend` directory:

```bash
cd backend
# Create and activate a virtual environment (Windows)
python -m venv venv
.\venv\Scripts\activate

# Install dependencies (ensure fastapi, uvicorn, pandas, python-multipart are installed)
pip install fastapi uvicorn pandas python-multipart

# Start the server
uvicorn main:app --reload
```
The backend will run on `http://localhost:8000`.

### 2. Start the Frontend (React + Vite)

Open a **second** terminal and navigate to the `frontend` directory:

```bash
cd frontend

# Install Node dependencies
npm install

# Start the development server
npm run dev
```
The frontend will run on `http://localhost:5173`.

## 📖 How to Use

1. **Access the Dashboard**: Open your browser to `http://localhost:5173`.
2. **Generate Test Data**: Click the **"Generate Test Data"** button on the UI. This will ask the backend to generate highly specific `platform_data.csv` and `bank_data.csv` files with planted errors and automatically download them to your computer.
3. **Upload & Reconcile**: Drag and drop (or select) the two downloaded CSV files into their respective upload zones.
4. **Analyze**: Click **"Run Reconciliation"**. Explore the visual match rate, the discrepancy breakdown pie chart, and utilize the global search bar to investigate specific transaction IDs or amounts across the tables.
