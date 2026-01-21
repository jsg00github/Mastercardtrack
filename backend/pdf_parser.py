"""
PDF Parser for Mastercard Argentina Credit Card Statements
Extracts transactions, balances, and calculates taxes from PDF statements
"""
import re
from datetime import datetime
from typing import List, Optional, Tuple
from dataclasses import dataclass
import pdfplumber


@dataclass
class Transaction:
    """Represents a single transaction from the statement"""
    date: datetime
    merchant: str
    coupon_number: str
    amount_pesos: float
    amount_dollars: float
    is_dollar: bool = False


@dataclass
class StatementData:
    """Parsed statement data"""
    saldo_actual_pesos: float
    saldo_actual_dolares: float
    transactions: List[Transaction]
    impuestos_pesos: float
    impuestos_dolares: float
    total_transactions_pesos: float
    total_transactions_dolares: float
    # Saldo Pendiente (previous month balance)
    saldo_pendiente_pesos: float = 0.0
    saldo_pendiente_dolares: float = 0.0
    # New fields for Statement model
    month: int = 0
    year: int = 0
    statement_date: Optional[datetime] = None
    proximo_cierre: Optional[datetime] = None
    proximo_vencimiento: Optional[datetime] = None


def parse_amount(text: str) -> float:
    """Parse an amount string to float, handling Argentine format (comma as decimal)"""
    if not text or text.strip() == '':
        return 0.0
    
    text = text.strip()
    is_negative = text.startswith('-') or text.startswith('(')
    text = text.replace('(', '').replace(')', '').replace('-', '').strip()
    
    # Handle Argentine format: 1.234,56 -> 1234.56
    if ',' in text and '.' in text:
        text = text.replace('.', '').replace(',', '.')
    elif ',' in text:
        text = text.replace(',', '.')
    
    try:
        value = float(text)
        return -value if is_negative else value
    except ValueError:
        return 0.0


def parse_date(text: str) -> Optional[datetime]:
    """Parse date in format DD-Mmm-YY (e.g., 26-Nov-25)"""
    months = {
        'ene': 1, 'feb': 2, 'mar': 3, 'abr': 4, 'may': 5, 'jun': 6,
        'jul': 7, 'ago': 8, 'sep': 9, 'oct': 10, 'nov': 11, 'dic': 12
    }
    
    try:
        match = re.match(r'(\d{1,2})-([A-Za-z]{3})-(\d{2})', text.strip())
        if match:
            day = int(match.group(1))
            month_str = match.group(2).lower()
            year = int(match.group(3)) + 2000
            month = months.get(month_str, 1)
            return datetime(year, month, day)
    except Exception:
        pass
    
    return None


def is_subtotal_row(text: str) -> bool:
    """Check if a row is a subtotal row that should be skipped"""
    text_lower = text.lower()
    skip_patterns = [
        'total titular',
        'total adicional',
        'saldo actual',
        'pago minimo',
        'detalle del mes',
        'su pago',  # Payment line
        'transfer financ',  # Transfer line
    ]
    return any(pattern in text_lower for pattern in skip_patterns)


def extract_saldo_actual(text: str) -> Tuple[float, float]:
    """Extract SALDO ACTUAL values (pesos and dollars) from text"""
    saldo_pesos = 0.0
    saldo_dolares = 0.0
    
    # Pattern: SALDO ACTUAL $ 3051644,80 U$S 488,62
    match = re.search(r'SALDO ACTUAL\s*\$?\s*([\d.,]+)\s*U\$S\s*([\d.,]+)', text, re.IGNORECASE)
    if match:
        saldo_pesos = parse_amount(match.group(1))
        saldo_dolares = parse_amount(match.group(2))
    
    return saldo_pesos, saldo_dolares


def extract_saldo_pendiente(text: str) -> Tuple[float, float]:
    """
    Extract SALDO PENDIENTE values (previous month's balance)
    Example line: "SALDO PENDIENTE     160594,67      0,00"
    """
    saldo_pesos = 0.0
    saldo_dolares = 0.0
    
    # Pattern: SALDO PENDIENTE followed by two numbers (pesos and dollars)
    match = re.search(r'SALDO PENDIENTE\s+([\d.,]+)\s+([\d.,]+)', text, re.IGNORECASE)
    if match:
        saldo_pesos = parse_amount(match.group(1))
        saldo_dolares = parse_amount(match.group(2))
    
    return saldo_pesos, saldo_dolares


def extract_statement_date(text: str) -> Tuple[Optional[datetime], int, int]:
    """
    Extract ESTADO DE CUENTA AL date and return (date, month, year)
    Example: "ESTADO DE CUENTA AL: 31-Dic-25"
    """
    # Pattern: ESTADO DE CUENTA AL: DD-Mmm-YY
    match = re.search(r'ESTADO DE CUENTA AL:\s*(\d{1,2})-([A-Za-z]{3})-(\d{2})', text, re.IGNORECASE)
    if match:
        date_obj = parse_date(f"{match.group(1)}-{match.group(2)}-{match.group(3)}")
        if date_obj:
            return date_obj, date_obj.month, date_obj.year
    
    return None, 0, 0


def extract_proximo_cierre(text: str) -> Optional[datetime]:
    """
    Extract PROXIMO CIERRE date
    Example: "PROXIMO CIERRE: 29-Ene-26"
    """
    match = re.search(r'PROXIMO\s*CIERRE:\s*(\d{1,2})-([A-Za-z]{3})-(\d{2})', text, re.IGNORECASE)
    if match:
        return parse_date(f"{match.group(1)}-{match.group(2)}-{match.group(3)}")
    return None


def extract_proximo_vencimiento(text: str) -> Optional[datetime]:
    """
    Extract PROXIMO VENCIMIENTO date
    Example: "PROXIMO VENCIMIENTO: 11-Feb-26"
    """
    match = re.search(r'PROXIMO\s*VENCIMIENTO:\s*(\d{1,2})-([A-Za-z]{3})-(\d{2})', text, re.IGNORECASE)
    if match:
        return parse_date(f"{match.group(1)}-{match.group(2)}-{match.group(3)}")
    return None


def parse_transaction_line(line: str) -> Optional[Transaction]:
    """
    Parse a single transaction line.
    
    Format examples:
    - 26-Nov-25 GOOGLE *YouTube (USA,ARS, 600,00) 00761 0,41      <- USD
    - 30-Nov-25 PUPPIS 02842 46500,00                             <- PESOS
    - 13-Dic-25 NETFLIX.COM (USA,ARS, 25398,00) 00779 17,63      <- USD
    """
    # Skip subtotal rows
    if is_subtotal_row(line):
        return None
    
    # Pattern: DATE MERCHANT COUPON AMOUNT
    # Date is at the start: DD-Mmm-YY
    date_match = re.match(r'^(\d{1,2}-[A-Za-z]{3}-\d{2})\s+(.+)', line.strip())
    if not date_match:
        return None
    
    date = parse_date(date_match.group(1))
    if not date:
        return None
    
    rest = date_match.group(2).strip()
    
    # Check if it's a USD transaction (contains USA,USD or USA,ARS in description)
    is_dollar = 'USA,' in rest.upper()
    
    # Extract the amount at the END of the line (last number)
    # Pattern: find the last number in the line
    numbers = re.findall(r'-?[\d]+[.,][\d]+', rest)
    
    if not numbers:
        return None
    
    # Last number is the transaction amount
    amount_str = numbers[-1]
    amount = parse_amount(amount_str)
    
    # Find coupon number (5 digits before the amount)
    coupon_match = re.search(r'\s(\d{5})\s+' + re.escape(amount_str.replace('.', r'\.').replace(',', r'\,')), rest)
    coupon = coupon_match.group(1) if coupon_match else ""
    
    # Get merchant name (everything before the coupon or amount)
    if coupon:
        merchant = rest.split(coupon)[0].strip()
    else:
        # Just take everything before the last number
        last_num_pos = rest.rfind(amount_str)
        merchant = rest[:last_num_pos].strip()
    
    # Clean up merchant name
    merchant = re.sub(r'\s+', ' ', merchant).strip()
    
    # Remove trailing numbers that might be coupon
    merchant = re.sub(r'\s+\d{5}$', '', merchant)
    
    # Assign to correct column based on transaction type
    if is_dollar:
        return Transaction(
            date=date,
            merchant=merchant,
            coupon_number=coupon,
            amount_pesos=0.0,
            amount_dollars=amount,
            is_dollar=True
        )
    else:
        return Transaction(
            date=date,
            merchant=merchant,
            coupon_number=coupon,
            amount_pesos=amount,
            amount_dollars=0.0,
            is_dollar=False
        )


def parse_mastercard_pdf(file_path: str) -> StatementData:
    """
    Parse a Mastercard Argentina PDF statement
    """
    transactions: List[Transaction] = []
    saldo_pesos = 0.0
    saldo_dolares = 0.0
    saldo_pendiente_pesos = 0.0
    saldo_pendiente_dolares = 0.0
    statement_date = None
    month = 0
    year = 0
    proximo_cierre = None
    proximo_vencimiento = None
    
    print(f"[PDF Parser] Opening file: {file_path}")
    
    with pdfplumber.open(file_path) as pdf:
        full_text = ""
        
        for page_num, page in enumerate(pdf.pages):
            page_text = page.extract_text() or ""
            full_text += page_text + "\n"
            
            print(f"[PDF Parser] Processing page {page_num + 1}")
            
            # Extract header info from first page
            if page_num == 0:
                saldo_pesos, saldo_dolares = extract_saldo_actual(page_text)
                saldo_pendiente_pesos, saldo_pendiente_dolares = extract_saldo_pendiente(page_text)
                print(f"[PDF Parser] SALDO ACTUAL: ${saldo_pesos:,.2f} pesos, ${saldo_dolares:,.2f} USD")
                print(f"[PDF Parser] SALDO PENDIENTE: ${saldo_pendiente_pesos:,.2f} pesos, ${saldo_pendiente_dolares:,.2f} USD")
                
                # Extract dates
                statement_date, month, year = extract_statement_date(page_text)
                proximo_cierre = extract_proximo_cierre(page_text)
                proximo_vencimiento = extract_proximo_vencimiento(page_text)
                
                if statement_date:
                    print(f"[PDF Parser] ESTADO DE CUENTA AL: {statement_date.strftime('%d-%b-%Y')}")
                if proximo_cierre:
                    print(f"[PDF Parser] PROXIMO CIERRE: {proximo_cierre.strftime('%d-%b-%Y')}")
                if proximo_vencimiento:
                    print(f"[PDF Parser] PROXIMO VENCIMIENTO: {proximo_vencimiento.strftime('%d-%b-%Y')}")
        
        # Parse all lines for transactions
        lines = full_text.split('\n')
        for line in lines:
            line = line.strip()
            if not line:
                continue
            
            # Check if line starts with date
            if re.match(r'^\d{1,2}-[A-Za-z]{3}-\d{2}\s', line):
                transaction = parse_transaction_line(line)
                if transaction:
                    transactions.append(transaction)
                    pesos_str = f"${transaction.amount_pesos:,.2f}" if transaction.amount_pesos else ""
                    usd_str = f"U${transaction.amount_dollars:.2f}" if transaction.amount_dollars else ""
                    print(f"[PDF Parser] {transaction.date.strftime('%d-%b-%y')} | {transaction.merchant[:35]:35} | {pesos_str:>15} | {usd_str:>10}")
    
    # Calculate totals
    total_pesos = sum(t.amount_pesos for t in transactions)
    total_dolares = sum(t.amount_dollars for t in transactions)
    
    # Calculate taxes (difference between SALDO ACTUAL and sum of transactions, minus saldo pendiente)
    # Impuestos = Saldo Actual - Total Consumos - Saldo Pendiente
    impuestos_pesos = saldo_pesos - total_pesos - saldo_pendiente_pesos
    impuestos_dolares = saldo_dolares - total_dolares - saldo_pendiente_dolares
    
    print(f"[PDF Parser] Total transactions: {len(transactions)}")
    print(f"[PDF Parser] Sum of transactions: ${total_pesos:,.2f} pesos, ${total_dolares:,.2f} USD")
    print(f"[PDF Parser] SALDO ACTUAL: ${saldo_pesos:,.2f} pesos, ${saldo_dolares:,.2f} USD")
    print(f"[PDF Parser] SALDO PENDIENTE: ${saldo_pendiente_pesos:,.2f} pesos, ${saldo_pendiente_dolares:,.2f} USD")
    print(f"[PDF Parser] Impuestos calculated: ${impuestos_pesos:,.2f} pesos, ${impuestos_dolares:,.2f} USD")
    
    return StatementData(
        saldo_actual_pesos=saldo_pesos,
        saldo_actual_dolares=saldo_dolares,
        transactions=transactions,
        impuestos_pesos=impuestos_pesos,
        impuestos_dolares=impuestos_dolares,
        total_transactions_pesos=total_pesos,
        total_transactions_dolares=total_dolares,
        saldo_pendiente_pesos=saldo_pendiente_pesos,
        saldo_pendiente_dolares=saldo_pendiente_dolares,
        month=month,
        year=year,
        statement_date=statement_date,
        proximo_cierre=proximo_cierre,
        proximo_vencimiento=proximo_vencimiento
    )


def get_category_for_merchant(merchant: str) -> str:
    """Auto-categorize merchant based on name patterns"""
    merchant_lower = merchant.lower()
    
    categories = {
        "Entretenimiento": ["google", "youtube", "netflix", "spotify", "steam", "playstation", "xbox", "hoyts", "cinema", "cine"],
        "Educación": ["udemy", "coursera", "skillshare", "domestika", "platzi", "healingmind", "skills to", "timsykes", "traders agency"],
        "Compras": ["mercadolibre", "amazon", "alibaba", "zara", "nike", "adidas", "jumbo", "carrefour", "coto", "dia tienda", "gift card"],
        "Comida y Restaurantes": ["rappi", "pedidosya", "uber eats", "mcdonalds", "starbucks", "cafe", "restaurant", "panera", "cayena"],
        "Tecnología": ["openai", "chatgpt", "github", "microsoft", "adobe", "dropbox"],
        "Transporte": ["uber", "cabify", "ypf", "shell", "axion", "deheza", "autop"],
        "Servicios": ["edenor", "edesur", "metrogas", "aysa", "telecom", "personal", "movistar", "claro", "naturgy", "arba", "zurich", "global z", "municipalidad"],
        "Salud": ["farmacia", "farmacity", "osde", "swiss medical", "galeno"],
        "Mascotas": ["puppis", "pet"],
        "Pagos Digitales": ["merpago", "mercadopago", "paypal", "dlo*"],
    }
    
    for category, keywords in categories.items():
        if any(kw in merchant_lower for kw in keywords):
            return category
    
    return "Otros"
