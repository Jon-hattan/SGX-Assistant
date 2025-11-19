# SGX REIT Analysis Assistant (Keppel DC REIT – Pilot)

This project is an end-to-end SGX announcements assistant that automates data collection from [SGX announcements](https://www.sgx.com/securities/company-announcements) and builds a RAG system on top of the documents using Google Gemini’s File Search API. It is currently tested on Keppel DC REIT (2021–2025).

---

## Features

### 1. Automated SGX Scraper (Selenium)
- Scrapes SGX company announcements from 2021–2025
- Downloads PDFs for:
  - Quarterly and annual financial statements
  - Investor presentations
  - Business updates
  - Other REIT-related announcements

### 2. RAG System with Gemini File Search
- Uploads scraped PDFs into a persistent Gemini File Search Store
- Enables natural-language querying directly over REIT filings
- Retrieves relevant sections before answering (grounded responses)
- Example queries:
  - "Summarize the 2023 Q4 results."
  - "What did Keppel DC REIT say about data centre acquisitions?"
  - "What changed between Q1 and Q2 in 2024?"

---

## Tech Stack

- Python
- Selenium (web automation and SGX scraping)
- Google Gemini API (File Search and RAG)

---


