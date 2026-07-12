# Accounts Receivable Automation

Automated AR system that reads scanned invoice PDFs using OCR, sends payment reminders to clients, and generates AR reports.

## Features

- Reads scanned invoice PDFs using OCR (Tesseract)
- Extracts invoice data: number, date, client, email, amount, terms
- Calculates due dates automatically (Net 30)
- Sends professional email reminders:
  - **Due Today** reminders
  - **Overdue** reminders (with days overdue)
- Attaches invoice PDF to reminder emails
- Generates PDF report with AR summary
- Sends report to finance team
- Auto-corrects common OCR misreads

## How It Works

```

1. Invoices placed in /storage/emulated/0/Invoices/incoming/
2. Script reads each PDF using OCR
3. Extracts invoice data (number, date, client, email, amount)
4. Calculates due date (Invoice Date + Net 30)
5. Compares with today's date
6. Sends reminders for Due Today and Overdue invoices
7. Moves processed invoices to /processed/
8. Generates PDF report
9. Emails report to finance team

```

## Invoice Format (USA Standard)

```

INVOICE
========================================
Invoice #: SVC-2026-1020
Invoice Date: 2026-06-12
Payment Terms: Net 30

Client: Test Client One
Email: client@email.com

Services:

---

Professional Consulting Services    $1,500.00

Total: $1,500.00
========================================

```

## Requirements

- Termux / Python 3
- Tesseract OCR
- Poppler
- Python libraries: pdf2image, pytesseract, pillow, fpdf

## Installation

### In Termux:
```bash
pkg install tesseract poppler
python -m pip install pdf2image pytesseract pillow fpdf
```

Configuration

Edit these variables in the script:

```python
INVOICE_FOLDER = "/storage/emulated/0/Invoices/incoming/"
PROCESSED_FOLDER = "/storage/emulated/0/Invoices/processed/"
REPORTS_FOLDER = "/storage/emulated/0/Invoices/reports/"

GMAIL_USER = "your_email@gmail.com"
GMAIL_PASSWORD = "your_app_password"
ALERT_EMAIL = "finance@company.com"
```

Folder Structure

```
/storage/emulated/0/Invoices/
├── incoming/      # Place invoices here
├── processed/     # Processed invoices moved here
└── reports/       # AR reports saved here
```

Running the Script

```bash
python ar_automation.py
```

Email Example

Due Today Reminder:

```
Subject: REMINDER: Payment Due Today - SVC-2026-1020

Dear Test Client One,

This is a friendly reminder that invoice SVC-2026-1020 for $1,500.00 is due today.

[Professional email body with company details]
```

Overdue Reminder:

```
Subject: URGENT: Invoice SVC-2026-1035 is 8 Days Overdue

Dear Test Client Two,

Invoice SVC-2026-1035 for $2,200.00 is now 8 days overdue.

[Professional email body with escalation notice]
```

Report Output

· Email: Summary + PDF attachment
· PDF: AR report with summary table and invoices needing action

Technologies

· Python 3
· Tesseract OCR (for scanned PDFs)
· pdf2image (PDF to image conversion)
· fpdf (PDF report generation)
· Gmail SMTP (Email)

# Author

Shezad Dev

· GitHub: shezad-dev

License

MIT

```
