#!/usr/bin/env python3
"""
Accounts Receivable Automation System
Reads invoice PDFs, extracts data, calculates due dates, sends reminders
"""

import os
import re
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.mime.base import MIMEBase
from email import encoders
from datetime import datetime, timedelta
from fpdf import FPDF

# ============ CONFIGURATION ============
# Defines folder paths where invoices are stored, processed, and reports are saved
# Defines email credentials for sending reminders and reports

INVOICE_FOLDER = "/storage/emulated/0/Invoices/incoming/"
PROCESSED_FOLDER = "/storage/emulated/0/Invoices/processed/"
REPORTS_FOLDER = "/storage/emulated/0/Invoices/reports/"

GMAIL_USER = "your_email@gmail.com"
GMAIL_PASSWORD = "your_app_password"
ALERT_EMAIL = "manager@company.com"

# ============ CORRECTIONS ============
# Fixes common OCR misreads for invoice numbers

INVOICE_CORRECTIONS = {
    "Invoice": "",
    "In voice": "",
    "Invoce": "",
}

# ============ CREATE FOLDERS ============
# Creates all required folders if they don't exist

for folder in [INVOICE_FOLDER, PROCESSED_FOLDER, REPORTS_FOLDER]:
    os.makedirs(folder, exist_ok=True)

# ============ FUNCTION: EXTRACT TEXT FROM PDF ============
# Converts PDF to images, then uses OCR to read text from images
# Returns extracted text or empty string if fails

def extract_text_from_pdf(pdf_path):
    try:
        from pdf2image import convert_from_path
        import pytesseract
        from PIL import Image
        
        print("   OCR processing...")
        images = convert_from_path(pdf_path, dpi=200)
        text = ""
        for img in images:
            text += pytesseract.image_to_string(img)
        return text
    except Exception as e:
        print(f"   OCR error: {e}")
        return ""

# ============ FUNCTION: EXTRACT INVOICE DATA ============
# Extracts invoice number, date, client, email, amount, terms from OCR text
# If invoice number not found, uses filename as fallback

def extract_invoice_data(text, filename):
    data = {
        'invoice_number': '',
        'invoice_date': '',
        'client': '',
        'email': '',
        'amount': 0,
        'terms': 'Net 30'
    }
    
    if not text:
        data['invoice_number'] = filename.replace('.pdf', '')
        return data
    
    # Tries multiple patterns to find invoice number
    invoice_patterns = [
        r'Invoice\s*#?\s*:?\s*([A-Z0-9\-]+)',
        r'Invoice\s*Number\s*:?\s*([A-Z0-9\-]+)',
        r'SVC-2026-\d{4}',
        r'INV-\d{4}',
    ]
    
    for pattern in invoice_patterns:
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            inv_num = match.group(1) if '(' in pattern else match.group(0)
            if inv_num in INVOICE_CORRECTIONS:
                inv_num = ""
            data['invoice_number'] = inv_num
            break
    
    # Fallback: use filename if no invoice number found
    if not data['invoice_number'] or data['invoice_number'] in INVOICE_CORRECTIONS:
        data['invoice_number'] = filename.replace('.pdf', '')
    
    # Extracts invoice date
    match = re.search(r'Invoice Date\s*:?\s*([0-9]{4}-[0-9]{2}-[0-9]{2})', text, re.IGNORECASE)
    if not match:
        match = re.search(r'Invoice\s*Date\s*:?\s*([0-9]{4}-[0-9]{2}-[0-9]{2})', text, re.IGNORECASE)
    if match:
        data['invoice_date'] = match.group(1).strip()
    
    # Extracts client name
    match = re.search(r'Client\s*:?\s*([^\n]+)', text, re.IGNORECASE)
    if match:
        data['client'] = match.group(1).strip()
    
    # Extracts client email with correction
    match = re.search(r'Email\s*:?\s*([a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,})', text, re.IGNORECASE)
    if match:
        email = match.group(1).strip()
        if email in EMAIL_CORRECTIONS:
            email = EMAIL_CORRECTIONS[email]
        data['email'] = email
    
    # Extracts invoice amount
    match = re.search(r'Total\s*:?\s*[$£€]?\s*([0-9,]+\.?[0-9]{0,2})', text, re.IGNORECASE)
    if not match:
        match = re.search(r'Total\s*\n\s*[$£€]?\s*([0-9,]+\.?[0-9]{0,2})', text, re.IGNORECASE)
    if match:
        data['amount'] = float(match.group(1).replace(',', ''))
    
    # Extracts payment terms
    match = re.search(r'Payment Terms\s*:?\s*([^\n]+)', text, re.IGNORECASE)
    if match:
        data['terms'] = match.group(1).strip()
    
    return data

# ============ FUNCTION: CALCULATE DUE DATE ============
# Calculates due date by adding Net 30 days to invoice date
# Extracts number from "Net 30" or defaults to 30 days

def calculate_due_date(invoice_date, terms):
    try:
        date_obj = datetime.strptime(invoice_date, "%Y-%m-%d")
        match = re.search(r'Net\s*(\d+)', terms, re.IGNORECASE)
        if match:
            days = int(match.group(1))
        else:
            days = 30
        due_date = date_obj + timedelta(days=days)
        return due_date.strftime("%Y-%m-%d")
    except:
        return invoice_date

# ============ FUNCTION: SEND REMINDER EMAIL ============
# Sends professional email with invoice PDF attached
# Uses different templates for "Due Today" vs "Overdue"

def send_reminder(invoice_data, due_date, days, pdf_path):
    try:
        company_name = "Shezad Consulting Group"
        company_phone = "+1-800-555-0199"
        company_email = "ar@shezadconsulting.com"
        
        if days == 0:
            subject = f"REMINDER: Payment Due Today - {invoice_data['invoice_number']}"
            body = f"""
Dear {invoice_data['client']},

This is a friendly reminder that invoice {invoice_data['invoice_number']} for ${invoice_data['amount']:.2f} is due today, {due_date}.

Please arrange payment at your earliest convenience.

Should you have any questions, contact {company_email} or call {company_phone}.

Thank you for your business.

Yours sincerely,
Accounts Receivable Department
{company_name}
"""
        else:
            subject = f"URGENT: Invoice {invoice_data['invoice_number']} is {abs(days)} Days Overdue"
            body = f"""
Dear {invoice_data['client']},

Invoice {invoice_data['invoice_number']} for ${invoice_data['amount']:.2f} is now {abs(days)} days overdue. The due date was {due_date}.

Please arrange immediate payment. If already paid, disregard this notice.

Contact {company_email} or call {company_phone} with any questions.

Yours sincerely,
Accounts Receivable Department
{company_name}
"""
        
        msg = MIMEMultipart()
        msg['From'] = GMAIL_USER
        msg['To'] = invoice_data['email']
        msg['Subject'] = subject
        msg.attach(MIMEText(body, 'plain'))
        
        # Attaches the invoice PDF
        if os.path.exists(pdf_path):
            with open(pdf_path, 'rb') as f:
                part = MIMEBase('application', 'pdf')
                part.set_payload(f.read())
                encoders.encode_base64(part)
                part.add_header('Content-Disposition', f'attachment; filename={os.path.basename(pdf_path)}')
                msg.attach(part)
        
        # Connects to Gmail and sends email
        server = smtplib.SMTP('smtp.gmail.com', 587)
        server.starttls()
        server.login(GMAIL_USER, GMAIL_PASSWORD)
        server.send_message(msg)
        server.quit()
        
        print(f"   ✅ Email sent to: {invoice_data['email']}")
        return True
    except Exception as e:
        print(f"   ❌ Email failed: {e}")
        return False

# ============ FUNCTION: GENERATE PDF REPORT ============
# Creates a PDF report with summary table and invoices needing action

def generate_report(invoices_data):
    pdf = FPDF()
    pdf.add_page()
    
    # Adds title
    pdf.set_font("Helvetica", "B", 18)
    pdf.cell(200, 12, "ACCOUNTS RECEIVABLE REPORT", ln=True, align="C")
    pdf.ln(4)
    
    # Adds timestamp
    pdf.set_font("Helvetica", "", 10)
    pdf.cell(200, 8, f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}", ln=True, align="C")
    pdf.ln(8)
    
    pdf.line(20, pdf.get_y(), 190, pdf.get_y())
    pdf.ln(6)
    
    # Adds SUMMARY table
    pdf.set_font("Helvetica", "B", 14)
    pdf.cell(200, 10, "SUMMARY", ln=True)
    pdf.ln(4)
    
    pdf.set_font("Helvetica", "B", 11)
    pdf.set_fill_color(200, 200, 200)
    pdf.cell(70, 10, "Category", border=1, fill=True)
    pdf.cell(50, 10, "Count", border=1, fill=True, ln=True)
    
    pdf.set_font("Helvetica", "", 11)
    rows = [
        ("Total Invoices", len(invoices_data)),
        ("Overdue", len([i for i in invoices_data if i.get('status') == 'Overdue'])),
        ("Due Today", len([i for i in invoices_data if i.get('status') == 'Due Today'])),
        ("Upcoming (1-7 days)", len([i for i in invoices_data if i.get('status') == 'Upcoming'])),
        ("Future (8+ days)", len([i for i in invoices_data if i.get('status') == 'Future']))
    ]
    
    for label, value in rows:
        pdf.cell(70, 8, label, border=1)
        pdf.cell(50, 8, str(value), border=1, ln=True)
    
    pdf.ln(8)
    pdf.line(20, pdf.get_y(), 190, pdf.get_y())
    pdf.ln(6)
    
    # Adds INVOICES NEEDING ACTION table
    action_invoices = [i for i in invoices_data if i.get('status') in ['Overdue', 'Due Today']]
    if action_invoices:
        pdf.set_font("Helvetica", "B", 14)
        pdf.cell(200, 10, "INVOICES NEEDING ACTION", ln=True)
        pdf.ln(4)
        
        pdf.set_font("Helvetica", "B", 9)
        pdf.set_fill_color(200, 200, 200)
        pdf.cell(35, 8, "Invoice #", border=1, fill=True)
        pdf.cell(45, 8, "Client", border=1, fill=True)
        pdf.cell(30, 8, "Amount", border=1, fill=True)
        pdf.cell(30, 8, "Status", border=1, fill=True)
        pdf.cell(40, 8, "Email", border=1, fill=True, ln=True)
        
        pdf.set_font("Helvetica", "", 8)
        for inv in action_invoices:
            pdf.cell(35, 6, inv['invoice_number'], border=1)
            pdf.cell(45, 6, inv['client'][:20], border=1)
            pdf.cell(30, 6, f"${inv['amount']:.2f}", border=1)
            pdf.cell(30, 6, inv['status'], border=1)
            pdf.cell(40, 6, inv['email'][:25], border=1, ln=True)
        
        pdf.ln(4)
    
    # Adds footer
    pdf.set_y(-20)
    pdf.set_font("Helvetica", "I", 8)
    pdf.line(20, pdf.get_y(), 190, pdf.get_y())
    pdf.ln(2)
    pdf.cell(200, 8, "This is an automated AR report.", align="C")
    
    # Saves PDF
    pdf_filename = f"{REPORTS_FOLDER}ar_report_{datetime.now().strftime('%Y%m%d')}.pdf"
    pdf.output(pdf_filename)
    return pdf_filename

# ============ FUNCTION: SEND REPORT EMAIL ============
# Sends the AR report PDF to the finance team email address

def send_report_email(pdf_path, invoices_data):
    try:
        action_invoices = [i for i in invoices_data if i.get('status') in ['Overdue', 'Due Today']]
        
        body = f"""
ACCOUNTS RECEIVABLE REPORT
==================================================
Date: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

SUMMARY
--------------------------------------------------
Total Invoices: {len(invoices_data)}
Overdue: {len([i for i in invoices_data if i.get('status') == 'Overdue'])}
Due Today: {len([i for i in invoices_data if i.get('status') == 'Due Today'])}
Upcoming: {len([i for i in invoices_data if i.get('status') == 'Upcoming'])}
Future: {len([i for i in invoices_data if i.get('status') == 'Future'])}

"""
        
        if action_invoices:
            body += "INVOICES NEEDING ACTION\n"
            body += "--------------------------------------------------\n"
            for inv in action_invoices:
                body += f"Invoice #: {inv['invoice_number']}\n"
                body += f"Client: {inv['client']}\n"
                body += f"Email: {inv['email']}\n"
                body += f"Amount: ${inv['amount']:.2f}\n"
                body += f"Status: {inv['status']}\n"
                body += "--------------------------------------------------\n"
        
        body += "\nPDF report attached.\n"
        
        msg = MIMEMultipart()
        msg['From'] = GMAIL_USER
        msg['To'] = ALERT_EMAIL
        msg['Subject'] = f"AR Report - {datetime.now().strftime('%Y-%m-%d')}"
        msg.attach(MIMEText(body, 'plain'))
        
        # Attaches PDF
        with open(pdf_path, 'rb') as f:
            part = MIMEBase('application', 'pdf')
            part.set_payload(f.read())
            encoders.encode_base64(part)
            part.add_header('Content-Disposition', f'attachment; filename={os.path.basename(pdf_path)}')
            msg.attach(part)
        
        server = smtplib.SMTP('smtp.gmail.com', 587)
        server.starttls()
        server.login(GMAIL_USER, GMAIL_PASSWORD)
        server.send_message(msg)
        server.quit()
        print(f"✅ Report emailed to {ALERT_EMAIL}")
        return True
    except Exception as e:
        print(f"❌ Report email failed: {e}")
        return False

# ============ MAIN FUNCTION ============
# Orchestrates the entire AR process:
# 1. Reads all PDFs from incoming folder
# 2. Extracts data using OCR
# 3. Calculates due dates
# 4. Sends reminders for overdue/due today invoices
# 5. Moves processed invoices
# 6. Generates and sends AR report

def main():
    print("\n" + "="*60)
    print("  ACCOUNTS RECEIVABLE AUTOMATION")
    print(f"  {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("="*60 + "\n")
    
    # Creates folders if they don't exist
    for folder in [INVOICE_FOLDER, PROCESSED_FOLDER, REPORTS_FOLDER]:
        os.makedirs(folder, exist_ok=True)
    
    # Gets list of PDF files in incoming folder
    files = os.listdir(INVOICE_FOLDER)
    invoice_files = [f for f in files if f.lower().endswith('.pdf')]
    
    if not invoice_files:
        print("No invoices found.")
        return
    
    print(f"{len(invoice_files)} invoices found\n")
    
    today = datetime.now().date()
    invoices_data = []
    emails_sent = 0
    
    # Processes each invoice one by one
    for filename in invoice_files:
        filepath = os.path.join(INVOICE_FOLDER, filename)
        print(f"Processing: {filename}")
        
        text = extract_text_from_pdf(filepath)
        if not text:
            print("   ❌ No text extracted")
            os.rename(filepath, os.path.join(PROCESSED_FOLDER, filename))
            continue
        
        invoice_data = extract_invoice_data(text, filename)
        print(f"   Invoice: {invoice_data['invoice_number']}")
        print(f"   Date: {invoice_data['invoice_date']}")
        print(f"   Client: {invoice_data['client']}")
        print(f"   Email: {invoice_data['email']}")
        print(f"   Amount: ${invoice_data['amount']:.2f}")
        
        # Calculates due date
        if invoice_data['invoice_date']:
            due_date_str = calculate_due_date(invoice_data['invoice_date'], invoice_data['terms'])
            due_date = datetime.strptime(due_date_str, "%Y-%m-%d").date()
            days_left = (due_date - today).days
        else:
            days_left = None
            due_date_str = ""
        
        # Determines status
        if days_left is None:
            status = "Unknown"
        elif days_left < 0:
            status = "Overdue"
        elif days_left == 0:
            status = "Due Today"
        elif days_left <= 7:
            status = "Upcoming"
        else:
            status = "Future"
        
        invoice_data['status'] = status
        invoice_data['due_date'] = due_date_str
        invoice_data['days_left'] = days_left if days_left is not None else 0
        invoices_data.append(invoice_data)
        
        print(f"   Status: {status} ({days_left if days_left is not None else 'N/A'} days)")
        
        # Sends reminder if needed
        if status == "Due Today" or status == "Overdue":
            if invoice_data['email']:
                print(f"   📧 Sending reminder to: {invoice_data['email']}")
                send_reminder(invoice_data, due_date_str, days_left, filepath)
                emails_sent += 1
            else:
                print(f"   ⚠️ No email address found")
        
        # Moves processed file
        os.rename(filepath, os.path.join(PROCESSED_FOLDER, filename))
        print()
    
    # Generates and sends report
    print("Generating report...")
    pdf_path = generate_report(invoices_data)
    send_report_email(pdf_path, invoices_data)
    
    print("\n" + "="*60)
    print("SUMMARY")
    print("="*60)
    print(f"Total Invoices: {len(invoices_data)}")
    print(f"Reminders Sent: {emails_sent}")
    print(f"Overdue: {len([i for i in invoices_data if i.get('status') == 'Overdue'])}")
    print(f"Due Today: {len([i for i in invoices_data if i.get('status') == 'Due Today'])}")
    print("="*60 + "\n")
    print("✅ Done.")

if __name__ == "__main__":
    main()
