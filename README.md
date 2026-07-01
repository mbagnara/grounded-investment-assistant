spurce# Investment RAG Grounded Synthesis

Project 2: Business Applications with Generative AI: Driving Investment Performance through Grounded Synthesis.

This project builds a retrieval-augmented generation (RAG) workflow for investment intelligence. It combines financial news, stock price summaries, SEC filings, and benchmark questions to produce grounded investment analysis with source-backed answers.

## Structure

```text
project-2/
├── notebooks/
│   └── UTAIGA_Project_2_Full_Code_Notebook.ipynb
├── data/
│   ├── raw/
│   ├── eval/
│   └── processed/
├── src/
│   └── investment_rag_grounded_synthesis/
├── chroma_db/
├── results/
├── requirements.txt
├── .env.example
└── README.md
```

## Setup

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
```

Add your OpenAI API key to `.env`.

## Data

- `data/raw/global_news.csv`: news articles.
- `data/raw/stock_price_details.csv`: stock price summaries.
- `data/raw/sec_filings_10q.pdf`: SEC filing source document.
- `data/eval/golden_benchmark_dataset.csv`: benchmark questions and expected answers.

