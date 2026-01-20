"""
CardTrack - Main FastAPI Application
Full-stack expense tracking with authentication, categories, and analytics
"""
import os
import random
from datetime import datetime, timedelta
from typing import List, Optional
from fastapi import FastAPI, Depends, HTTPException, status, UploadFile, File, Query, Form
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session

from . import models, schemas, auth, analytics
from .database import get_db, init_db, engine

# Create FastAPI app
app = FastAPI(
    title="CardTrack API",
    description="API para tracking de gastos de tarjeta de crédito",
    version="1.0.0"
)

# CORS middleware for frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, specify your domain
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize database on startup
@app.on_event("startup")
def startup_event():
    init_db()


# ============ Static Files & Frontend ============

# Mount static files (frontend)
frontend_path = os.path.join(os.path.dirname(os.path.dirname(__file__)))
if os.path.exists(os.path.join(frontend_path, "index.html")):
    app.mount("/static", StaticFiles(directory=frontend_path), name="static")


@app.get("/", include_in_schema=False)
async def root():
    """Serve the frontend"""
    index_path = os.path.join(frontend_path, "index.html")
    if os.path.exists(index_path):
        return FileResponse(index_path)
    return {"message": "CardTrack API", "docs": "/docs"}

@app.get("/styles.css", include_in_schema=False)
async def styles():
    return FileResponse(os.path.join(frontend_path, "styles.css"))

@app.get("/app.js", include_in_schema=False)
async def app_js():
    return FileResponse(os.path.join(frontend_path, "app.js"))



# ============ Health Check ============

@app.get("/api/health")
async def health_check():
    """Health check endpoint for Railway"""
    return {"status": "healthy", "timestamp": datetime.utcnow().isoformat()}


# ============ Authentication Endpoints ============

@app.post("/api/auth/register", response_model=schemas.Token)
async def register(user_data: schemas.UserCreate, db: Session = Depends(get_db)):
    """Register a new user"""
    user = auth.register_user(db, user_data)
    return auth.create_user_token(user)


@app.post("/api/auth/login", response_model=schemas.Token)
async def login(credentials: schemas.UserLogin, db: Session = Depends(get_db)):
    """Login and get access token"""
    user = auth.authenticate_user(db, credentials.username, credentials.password)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Usuario o contraseña incorrectos"
        )
    return auth.create_user_token(user)


@app.get("/api/auth/me", response_model=schemas.UserResponse)
async def get_current_user_info(
    current_user: models.User = Depends(auth.get_current_user)
):
    """Get current user info"""
    return current_user


# ============ Category Endpoints ============

@app.get("/api/categories", response_model=List[schemas.CategoryResponse])
async def get_categories(
    current_user: models.User = Depends(auth.get_current_user),
    db: Session = Depends(get_db)
):
    """Get all categories for the current user"""
    categories = db.query(models.Category).filter(
        models.Category.user_id == current_user.id
    ).order_by(models.Category.name).all()
    return categories


@app.post("/api/categories", response_model=schemas.CategoryResponse)
async def create_category(
    category_data: schemas.CategoryCreate,
    current_user: models.User = Depends(auth.get_current_user),
    db: Session = Depends(get_db)
):
    """Create a new category"""
    category = models.Category(
        user_id=current_user.id,
        name=category_data.name,
        icon=category_data.icon,
        color=category_data.color,
        is_default=False
    )
    db.add(category)
    db.commit()
    db.refresh(category)
    return category


@app.put("/api/categories/{category_id}", response_model=schemas.CategoryResponse)
async def update_category(
    category_id: int,
    category_data: schemas.CategoryUpdate,
    current_user: models.User = Depends(auth.get_current_user),
    db: Session = Depends(get_db)
):
    """Update a category"""
    category = db.query(models.Category).filter(
        models.Category.id == category_id,
        models.Category.user_id == current_user.id
    ).first()
    
    if not category:
        raise HTTPException(status_code=404, detail="Categoría no encontrada")
    
    if category_data.name is not None:
        category.name = category_data.name
    if category_data.icon is not None:
        category.icon = category_data.icon
    if category_data.color is not None:
        category.color = category_data.color
    
    db.commit()
    db.refresh(category)
    return category


@app.delete("/api/categories/{category_id}")
async def delete_category(
    category_id: int,
    current_user: models.User = Depends(auth.get_current_user),
    db: Session = Depends(get_db)
):
    """Delete a category (transactions will have null category)"""
    category = db.query(models.Category).filter(
        models.Category.id == category_id,
        models.Category.user_id == current_user.id
    ).first()
    
    if not category:
        raise HTTPException(status_code=404, detail="Categoría no encontrada")
    
    # Set transactions to null category
    db.query(models.Transaction).filter(
        models.Transaction.category_id == category_id
    ).update({"category_id": None})
    
    db.delete(category)
    db.commit()
    return {"message": "Categoría eliminada"}


# ============ Transaction Endpoints ============

@app.get("/api/transactions", response_model=List[schemas.TransactionResponse])
async def get_transactions(
    current_user: models.User = Depends(auth.get_current_user),
    db: Session = Depends(get_db),
    category_id: Optional[int] = Query(None),
    search: Optional[str] = Query(None),
    is_dollar: Optional[bool] = Query(None, description="Filter by currency"),
    month: Optional[int] = Query(None, ge=1, le=12),
    year: Optional[int] = Query(None, ge=2020, le=2030),
    limit: int = Query(100, le=500),
    offset: int = Query(0)
):
    """Get transactions with optional filters"""
    query = db.query(models.Transaction).filter(
        models.Transaction.user_id == current_user.id
    )
    
    if category_id:
        query = query.filter(models.Transaction.category_id == category_id)
    
    if search:
        query = query.filter(models.Transaction.merchant.ilike(f"%{search}%"))
    
    if is_dollar is not None:
        query = query.filter(models.Transaction.is_dollar == is_dollar)
    
    if month and year:
        query = query.join(models.Statement).filter(
            models.Statement.month == month,
            models.Statement.year == year
        )
    elif year:
        query = query.join(models.Statement).filter(
            models.Statement.year == year
        )
    
    transactions = query.order_by(
        models.Transaction.date.desc()
    ).offset(offset).limit(limit).all()
    
    return transactions


@app.post("/api/transactions", response_model=schemas.TransactionResponse)
async def create_transaction(
    transaction_data: schemas.TransactionCreate,
    current_user: models.User = Depends(auth.get_current_user),
    db: Session = Depends(get_db)
):
    """Create a new transaction"""
    transaction = models.Transaction(
        user_id=current_user.id,
        category_id=transaction_data.category_id,
        merchant=transaction_data.merchant,
        amount=transaction_data.amount,
        date=transaction_data.date,
        description=transaction_data.description
    )
    db.add(transaction)
    db.commit()
    db.refresh(transaction)
    return transaction


@app.put("/api/transactions/{transaction_id}", response_model=schemas.TransactionResponse)
async def update_transaction(
    transaction_id: int,
    transaction_data: schemas.TransactionUpdate,
    current_user: models.User = Depends(auth.get_current_user),
    db: Session = Depends(get_db)
):
    """Update a transaction"""
    transaction = db.query(models.Transaction).filter(
        models.Transaction.id == transaction_id,
        models.Transaction.user_id == current_user.id
    ).first()
    
    if not transaction:
        raise HTTPException(status_code=404, detail="Transacción no encontrada")
    
    if transaction_data.merchant is not None:
        transaction.merchant = transaction_data.merchant
    if transaction_data.amount is not None:
        transaction.amount = transaction_data.amount
    if transaction_data.date is not None:
        transaction.date = transaction_data.date
    if transaction_data.category_id is not None:
        transaction.category_id = transaction_data.category_id
    if transaction_data.description is not None:
        transaction.description = transaction_data.description
    
    db.commit()
    db.refresh(transaction)
    return transaction


@app.delete("/api/transactions/{transaction_id}")
async def delete_transaction(
    transaction_id: int,
    current_user: models.User = Depends(auth.get_current_user),
    db: Session = Depends(get_db)
):
    """Delete a transaction"""
    transaction = db.query(models.Transaction).filter(
        models.Transaction.id == transaction_id,
        models.Transaction.user_id == current_user.id
    ).first()
    
    if not transaction:
        raise HTTPException(status_code=404, detail="Transacción no encontrada")
    
    db.delete(transaction)
    db.commit()
    return {"message": "Transacción eliminada"}


# ============ Analytics Endpoints ============

@app.get("/api/analytics", response_model=schemas.AnalyticsResponse)
async def get_analytics_data(
    current_user: models.User = Depends(auth.get_current_user),
    db: Session = Depends(get_db),
    period: str = Query("month", pattern="^(month|quarter|year)$"),
    is_dollar: Optional[bool] = Query(None, description="True for USD, False for ARS, None for all"),
    month: Optional[int] = Query(None, ge=1, le=12, description="Filter by month (1-12)"),
    year: Optional[int] = Query(None, ge=2020, le=2030, description="Filter by year")
):
    """Get analytics and recommendations with currency and period filters"""
    return analytics.get_analytics(db, current_user.id, period, is_dollar, month, year)


@app.get("/api/analytics/trend")
async def get_spending_trend(
    current_user: models.User = Depends(auth.get_current_user),
    db: Session = Depends(get_db),
    period: str = Query("month", pattern="^(month|quarter|year)$"),
    is_dollar: Optional[bool] = Query(None, description="True for USD, False for ARS, None for all"),
    month: Optional[int] = Query(None, ge=1, le=12),
    year: Optional[int] = Query(None, ge=2020, le=2030)
):
    """Get spending trend based on period (month=daily, quarter=weekly, year=monthly)"""
    return analytics.get_spending_trend(db, current_user.id, period, is_dollar, month, year)


@app.get("/api/available-periods")
async def get_available_periods(
    current_user: models.User = Depends(auth.get_current_user),
    db: Session = Depends(get_db)
):
    """Get available months and years that have statement data"""
    return analytics.get_available_periods(db, current_user.id)


# ============ File Upload Endpoint ============

# Merchant name patterns for auto-categorization
CATEGORY_KEYWORDS = {
    "Comida y Restaurantes": ["restaurant", "cafe", "coffee", "food", "pizza", "burger", "sushi", "starbucks", "mcdonalds", "uber eats", "pedidosya", "rappi", "supermercado", "carrefour", "coto", "dia"],
    "Compras": ["amazon", "mercadolibre", "store", "shop", "mall", "clothing", "fashion", "nike", "adidas", "zara", "tienda"],
    "Transporte": ["uber", "cabify", "taxi", "subte", "sube", "ypf", "shell", "axion", "estacionamiento", "peaje"],
    "Entretenimiento": ["netflix", "spotify", "hulu", "disney", "cine", "cinema", "concert", "ticket", "steam", "playstation", "xbox"],
    "Servicios": ["edenor", "edesur", "metrogas", "aysa", "telecom", "personal", "movistar", "claro", "fibertel"],
    "Salud": ["farmacia", "farmacity", "doctor", "hospital", "clinica", "gym", "gimnasio", "megatlon"],
    "Suscripciones": ["subscription", "mensual", "apple", "google", "microsoft", "adobe", "amazon prime"]
}


def auto_categorize(merchant: str, categories: List[models.Category]) -> Optional[int]:
    """Auto-categorize a transaction based on merchant name"""
    merchant_lower = merchant.lower()
    
    for cat in categories:
        cat_name = cat.name
        if cat_name in CATEGORY_KEYWORDS:
            keywords = CATEGORY_KEYWORDS[cat_name]
            if any(keyword in merchant_lower for keyword in keywords):
                return cat.id
    
    # Default to "Otros" if exists
    otros = next((c for c in categories if "otro" in c.name.lower()), None)
    return otros.id if otros else None


@app.post("/api/upload", response_model=schemas.UploadResponse)
async def upload_statement(
    file: UploadFile = File(...),
    dolar_rate: float = Form(0.0, description="Cotización dólar tarjeta (oficial + 30%)"),
    current_user: models.User = Depends(auth.get_current_user),
    db: Session = Depends(get_db)
):
    """
    Upload and process a credit card statement (PDF).
    Parses Mastercard Argentina statements and extracts real transactions.
    """
    import tempfile
    import shutil
    from .pdf_parser import parse_mastercard_pdf, get_category_for_merchant
    
    # Get user's categories
    categories = db.query(models.Category).filter(
        models.Category.user_id == current_user.id
    ).all()
    
    # Create a category lookup dict
    category_lookup = {c.name.lower(): c for c in categories}
    
    # Check if it's a PDF
    if not file.filename.lower().endswith('.pdf'):
        # For non-PDF files, use the old mock behavior for now
        transactions = []
        now = datetime.utcnow()
        total_amount = 0
        
        sample_merchants = [
            ("Demo Transaction", "Otros"),
        ]
        
        num_transactions = random.randint(5, 10)
        for i in range(num_transactions):
            merchant, cat_name = random.choice(sample_merchants)
            category = next((c for c in categories if cat_name.lower() in c.name.lower()), None)
            amount = round(random.uniform(1000, 10000), 2)
            total_amount += amount
            
            transaction = models.Transaction(
                user_id=current_user.id,
                category_id=category.id if category else None,
                merchant=f"{merchant} {i+1}",
                amount=amount,
                date=now - timedelta(days=random.randint(0, 30))
            )
            db.add(transaction)
            transactions.append(transaction)
        
        db.commit()
        
        return schemas.UploadResponse(
            filename=file.filename,
            transactions_imported=len(transactions),
            total_amount=round(total_amount, 2)
        )
    
    # Save PDF to temp file
    try:
        with tempfile.NamedTemporaryFile(delete=False, suffix='.pdf') as tmp:
            shutil.copyfileobj(file.file, tmp)
            tmp_path = tmp.name
        
        print(f"[Upload] Saved PDF to: {tmp_path}")
        
        # Parse the PDF
        statement_data = parse_mastercard_pdf(tmp_path)
        
        # Create Statement record
        statement = models.Statement(
            user_id=current_user.id,
            filename=file.filename,
            month=statement_data.month or datetime.utcnow().month,
            year=statement_data.year or datetime.utcnow().year,
            total_pesos=statement_data.saldo_actual_pesos,
            total_dollars=statement_data.saldo_actual_dolares,
            dolar_rate=dolar_rate,
            statement_date=statement_data.statement_date.date() if statement_data.statement_date else None,
            proximo_cierre=statement_data.proximo_cierre.date() if statement_data.proximo_cierre else None,
            proximo_vencimiento=statement_data.proximo_vencimiento.date() if statement_data.proximo_vencimiento else None,
        )
        db.add(statement)
        db.flush()  # Get the statement ID
        
        # Create transactions from parsed data
        transactions_created = []
        total_pesos = 0
        total_dollars = 0
        
        for t in statement_data.transactions:
            # Get or create category based on merchant name
            cat_name = get_category_for_merchant(t.merchant)
            category = category_lookup.get(cat_name.lower())
            
            if not category:
                category = next(
                    (c for c in categories if cat_name.lower() in c.name.lower()),
                    next((c for c in categories if "otro" in c.name.lower()), None)
                )
            
            # Import both PESOS and USD transactions
            if t.amount_pesos != 0:
                total_pesos += t.amount_pesos
                transaction = models.Transaction(
                    user_id=current_user.id,
                    statement_id=statement.id,
                    category_id=category.id if category else None,
                    merchant=t.merchant,
                    amount=abs(t.amount_pesos),
                    is_dollar=False,
                    date=t.date,
                    description=f"Cupón: {t.coupon_number}" if t.coupon_number else None
                )
                db.add(transaction)
                transactions_created.append(transaction)
            
            if t.amount_dollars != 0:
                total_dollars += t.amount_dollars
                # Categorize USD transactions as Suscripciones by default
                usd_category = next(
                    (c for c in categories if "suscripcion" in c.name.lower()),
                    category
                )
                transaction = models.Transaction(
                    user_id=current_user.id,
                    statement_id=statement.id,
                    category_id=usd_category.id if usd_category else None,
                    merchant=t.merchant,
                    amount=abs(t.amount_dollars),
                    is_dollar=True,
                    date=t.date,
                    description=f"Cupón: {t.coupon_number}" if t.coupon_number else None
                )
                db.add(transaction)
                transactions_created.append(transaction)
        
        # Add impuestos as a separate transaction if significant
        if abs(statement_data.impuestos_pesos) > 100:
            impuestos_category = next(
                (c for c in categories if "impuesto" in c.name.lower() or "servicio" in c.name.lower()),
                next((c for c in categories if "otro" in c.name.lower()), None)
            )
            
            impuestos_transaction = models.Transaction(
                user_id=current_user.id,
                statement_id=statement.id,
                category_id=impuestos_category.id if impuestos_category else None,
                merchant="Impuestos y Cargos del Resumen",
                amount=abs(statement_data.impuestos_pesos),
                is_dollar=False,
                date=statement_data.statement_date or datetime.utcnow(),
                description="Calculado automáticamente (diferencia entre saldo y transacciones)"
            )
            db.add(impuestos_transaction)
            transactions_created.append(impuestos_transaction)
            total_pesos += abs(statement_data.impuestos_pesos)
        
        # Update statement transaction count
        statement.transaction_count = len(transactions_created)
        
        db.commit()
        
        # Clean up temp file
        import os
        try:
            os.unlink(tmp_path)
        except:
            pass
        
        print(f"[Upload] Created statement ID {statement.id} with {len(transactions_created)} transactions")
        print(f"[Upload] Total PESOS: ${total_pesos:,.2f}, Total USD: ${total_dollars:.2f}")
        
        return schemas.UploadResponse(
            filename=file.filename,
            transactions_imported=len(transactions_created),
            total_amount=round(statement_data.saldo_actual_pesos, 2),
            statement_id=statement.id
        )
        
    except HTTPException:
        raise
    except Exception as e:
        print(f"[Upload Error] {str(e)}")
        import traceback
        traceback.print_exc()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error procesando PDF: {str(e)}"
        )


# ============ Statement Endpoints ============

@app.get("/api/statements", response_model=List[schemas.StatementResponse])
async def get_statements(
    current_user: models.User = Depends(auth.get_current_user),
    db: Session = Depends(get_db)
):
    """Get all statements for current user, ordered by date descending"""
    statements = db.query(models.Statement).filter(
        models.Statement.user_id == current_user.id
    ).order_by(models.Statement.year.desc(), models.Statement.month.desc()).all()
    
    return statements


@app.get("/api/statements/latest-dates", response_model=schemas.LatestStatementDates)
async def get_latest_statement_dates(
    current_user: models.User = Depends(auth.get_current_user),
    db: Session = Depends(get_db)
):
    """Get próximo cierre and vencimiento from the most recent statement"""
    statement = db.query(models.Statement).filter(
        models.Statement.user_id == current_user.id
    ).order_by(models.Statement.year.desc(), models.Statement.month.desc()).first()
    
    if not statement:
        return schemas.LatestStatementDates()
    
    return schemas.LatestStatementDates(
        proximo_cierre=statement.proximo_cierre,
        proximo_vencimiento=statement.proximo_vencimiento,
        month=statement.month,
        year=statement.year
    )


@app.get("/api/statements/{statement_id}", response_model=schemas.StatementWithTransactions)
async def get_statement(
    statement_id: int,
    current_user: models.User = Depends(auth.get_current_user),
    db: Session = Depends(get_db)
):
    """Get a specific statement with its transactions"""
    statement = db.query(models.Statement).filter(
        models.Statement.id == statement_id,
        models.Statement.user_id == current_user.id
    ).first()
    
    if not statement:
        raise HTTPException(status_code=404, detail="Resumen no encontrado")
    
    return statement


@app.delete("/api/statements/{statement_id}")
async def delete_statement(
    statement_id: int,
    current_user: models.User = Depends(auth.get_current_user),
    db: Session = Depends(get_db)
):
    """Delete a statement and all its transactions"""
    statement = db.query(models.Statement).filter(
        models.Statement.id == statement_id,
        models.Statement.user_id == current_user.id
    ).first()
    
    if not statement:
        raise HTTPException(status_code=404, detail="Resumen no encontrado")
    
    # Delete the statement (transactions will cascade delete)
    db.delete(statement)
    db.commit()
    
    return {"message": f"Resumen de {statement.month}/{statement.year} eliminado con {statement.transaction_count} transacciones"}


@app.get("/api/transactions/by-statement/{statement_id}", response_model=List[schemas.TransactionResponse])
async def get_transactions_by_statement(
    statement_id: int,
    is_dollar: Optional[bool] = Query(None, description="Filter by currency"),
    current_user: models.User = Depends(auth.get_current_user),
    db: Session = Depends(get_db)
):
    """Get transactions for a specific statement, optionally filtered by currency"""
    query = db.query(models.Transaction).filter(
        models.Transaction.statement_id == statement_id,
        models.Transaction.user_id == current_user.id
    )
    
    if is_dollar is not None:
        query = query.filter(models.Transaction.is_dollar == is_dollar)
    
    return query.order_by(models.Transaction.date.desc()).all()


@app.patch("/api/transactions/{transaction_id}", response_model=schemas.TransactionResponse)
async def update_transaction(
    transaction_id: int,
    transaction_update: schemas.TransactionUpdate,
    current_user: models.User = Depends(auth.get_current_user),
    db: Session = Depends(get_db)
):
    """Update a transaction (e.g. modify category)"""
    transaction = db.query(models.Transaction).filter(
        models.Transaction.id == transaction_id,
        models.Transaction.user_id == current_user.id
    ).first()
    
    if not transaction:
        raise HTTPException(status_code=404, detail="Transacción no encontrada")
    
    # Update fields
    update_data = transaction_update.dict(exclude_unset=True)
    
    # Validate category if changing
    if "category_id" in update_data and update_data["category_id"] is not None:
        category = db.query(models.Category).filter(
            models.Category.id == update_data["category_id"],
            models.Category.user_id == current_user.id
        ).first()
        if not category:
            raise HTTPException(status_code=404, detail="Categoría no encontrada")
            
    for key, value in update_data.items():
        setattr(transaction, key, value)
        
    db.commit()
    db.refresh(transaction)
    return transaction


@app.get("/api/available-periods")
async def get_available_periods_endpoint(
    current_user: models.User = Depends(auth.get_current_user),
    db: Session = Depends(get_db)
):
    """Get available months and years from statements"""
    return analytics.get_available_periods(db, current_user.id)
