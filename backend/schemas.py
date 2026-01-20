"""
Pydantic schemas for API request/response validation
"""
from pydantic import BaseModel, EmailStr
from typing import Optional, List
from datetime import datetime, date


# ============ User Schemas ============

class UserCreate(BaseModel):
    email: EmailStr
    username: str
    password: str


class UserLogin(BaseModel):
    username: str
    password: str


class UserResponse(BaseModel):
    id: int
    email: str
    username: str
    is_active: bool
    created_at: datetime
    
    class Config:
        from_attributes = True


class Token(BaseModel):
    access_token: str
    token_type: str
    user: UserResponse


# ============ Category Schemas ============

class CategoryBase(BaseModel):
    name: str
    icon: str = "📦"
    color: str = "#778899"


class CategoryCreate(CategoryBase):
    pass


class CategoryUpdate(BaseModel):
    name: Optional[str] = None
    icon: Optional[str] = None
    color: Optional[str] = None


class CategoryResponse(CategoryBase):
    id: int
    user_id: int
    is_default: bool
    created_at: datetime
    
    class Config:
        from_attributes = True


# ============ Statement Schemas (Base) ============

class StatementResponse(BaseModel):
    id: int
    user_id: int
    filename: str
    month: int
    year: int
    total_pesos: float
    total_dollars: float
    transaction_count: int
    dolar_rate: float = 0.0
    statement_date: Optional[date] = None
    proximo_cierre: Optional[date] = None
    proximo_vencimiento: Optional[date] = None
    created_at: datetime
    
    class Config:
        from_attributes = True


# ============ Transaction Schemas ============

class TransactionBase(BaseModel):
    merchant: str
    amount: float
    date: datetime
    description: Optional[str] = None


class TransactionCreate(TransactionBase):
    category_id: Optional[int] = None


class TransactionUpdate(BaseModel):
    merchant: Optional[str] = None
    amount: Optional[float] = None
    date: Optional[datetime] = None
    category_id: Optional[int] = None
    description: Optional[str] = None


class TransactionResponse(TransactionBase):
    id: int
    user_id: int
    statement_id: Optional[int] = None
    statement: Optional[StatementResponse] = None
    category_id: Optional[int]
    category: Optional[CategoryResponse] = None
    is_dollar: bool = False
    created_at: datetime
    
    class Config:
        from_attributes = True


# ============ Statement Schemas ============

class StatementWithTransactions(StatementResponse):
    transactions: List[TransactionResponse] = []


class LatestStatementDates(BaseModel):
    """Dates from the most recent statement for the banner"""
    proximo_cierre: Optional[date] = None
    proximo_vencimiento: Optional[date] = None
    month: int = 0
    year: int = 0


# ============ Analytics Schemas ============

class CategorySummary(BaseModel):
    category_id: int
    category_name: str
    category_icon: str
    category_color: str
    total: float
    count: int
    percentage: float


class Recommendation(BaseModel):
    type: str  # warning, tip, success, info
    icon: str
    message: str


class AnalyticsResponse(BaseModel):
    total_spending: float
    total_ars: float = 0.0  # Total in ARS only
    total_usd: float = 0.0  # Total in USD only
    total_unified: float = 0.0  # ARS + (USD × dolar_rate)
    dolar_rate: float = 0.0  # The dolar tarjeta rate used
    transaction_count: int
    average_transaction: float
    category_breakdown: List[CategorySummary]
    recommendations: List[Recommendation]
    period: str


# ============ Upload Schemas ============

class UploadResponse(BaseModel):
    filename: str
    transactions_imported: int
    total_amount: float
    statement_id: Optional[int] = None

