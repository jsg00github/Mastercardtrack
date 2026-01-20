"""
SQLAlchemy models for CardTrack
"""
from sqlalchemy import Column, Integer, String, Float, DateTime, Date, ForeignKey, Boolean
from sqlalchemy.orm import relationship
from datetime import datetime
from .database import Base


class User(Base):
    """User model with authentication"""
    __tablename__ = "users"
    
    id = Column(Integer, primary_key=True, index=True)
    email = Column(String(255), unique=True, index=True, nullable=False)
    username = Column(String(100), unique=True, index=True, nullable=False)
    hashed_password = Column(String(255), nullable=False)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # Relationships
    transactions = relationship("Transaction", back_populates="user", cascade="all, delete-orphan")
    categories = relationship("Category", back_populates="user", cascade="all, delete-orphan")
    statements = relationship("Statement", back_populates="user", cascade="all, delete-orphan")


class Category(Base):
    """Expense category - editable by user"""
    __tablename__ = "categories"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    name = Column(String(100), nullable=False)
    icon = Column(String(10), default="📦")  # Emoji icon
    color = Column(String(7), default="#778899")  # Hex color
    is_default = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # Relationships
    user = relationship("User", back_populates="categories")
    transactions = relationship("Transaction", back_populates="category")


class Statement(Base):
    """Credit card statement (resumen) - groups transactions by month/PDF"""
    __tablename__ = "statements"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    filename = Column(String(255), nullable=False)
    month = Column(Integer, nullable=False)  # 1-12
    year = Column(Integer, nullable=False)   # 2025, 2026, etc
    
    # Totals
    total_pesos = Column(Float, default=0.0)
    total_dollars = Column(Float, default=0.0)
    transaction_count = Column(Integer, default=0)
    dolar_rate = Column(Float, default=0.0)  # Dólar tarjeta rate (official + 30%)
    
    # Important dates from PDF
    statement_date = Column(Date, nullable=True)  # ESTADO DE CUENTA AL
    proximo_cierre = Column(Date, nullable=True)  # PROXIMO CIERRE
    proximo_vencimiento = Column(Date, nullable=True)  # PROXIMO VENCIMIENTO
    
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # Relationships
    user = relationship("User", back_populates="statements")
    transactions = relationship("Transaction", back_populates="statement", cascade="all, delete-orphan")


class Transaction(Base):
    """Individual expense transaction"""
    __tablename__ = "transactions"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    statement_id = Column(Integer, ForeignKey("statements.id"), nullable=True)  # Links to Statement
    category_id = Column(Integer, ForeignKey("categories.id"), nullable=True)
    merchant = Column(String(255), nullable=False)
    amount = Column(Float, nullable=False)
    is_dollar = Column(Boolean, default=False)  # True if amount is in USD
    date = Column(DateTime, nullable=False)
    description = Column(String(500), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # Relationships
    user = relationship("User", back_populates="transactions")
    statement = relationship("Statement", back_populates="transactions")
    category = relationship("Category", back_populates="transactions")


# Default categories in Spanish (Argentinian)
DEFAULT_CATEGORIES = [
    {"name": "Comida y Restaurantes", "icon": "🍔", "color": "#ff6b6b"},
    {"name": "Compras", "icon": "🛍️", "color": "#ffd93d"},
    {"name": "Transporte", "icon": "🚗", "color": "#6bcb77"},
    {"name": "Entretenimiento", "icon": "🎬", "color": "#4d96ff"},
    {"name": "Servicios", "icon": "💡", "color": "#ff9f43"},
    {"name": "Salud", "icon": "🏥", "color": "#a66cff"},
    {"name": "Suscripciones", "icon": "📱", "color": "#00d4ff"},
    {"name": "Otros", "icon": "📦", "color": "#778899"},
]

