"""
Analytics engine with rule-based recommendations
Generates spending insights and actionable advice in Spanish
"""
from typing import List, Dict, Optional
from datetime import datetime, timedelta
from sqlalchemy.orm import Session
from sqlalchemy import func, extract
from . import models, schemas


def get_analytics(
    db: Session,
    user_id: int,
    period: str = "month",
    is_dollar: bool = False,
    month: Optional[int] = None,
    year: Optional[int] = None
) -> schemas.AnalyticsResponse:
    """
    Generate comprehensive analytics for a user's spending.
    Period can be: month, quarter, year
    is_dollar: filter by currency (True=USD, False=ARS, None=all)
    month/year: filter by specific month and year
    """
    # Build base query
    query = db.query(models.Transaction).filter(
        models.Transaction.user_id == user_id
    )
    
    # Only filter by currency if specified
    if is_dollar is not None:
        query = query.filter(models.Transaction.is_dollar == is_dollar)
    
    # Filter by specific month/year if provided
    if month and year:
        # Join with Statement and filter by statement period
        query = query.join(models.Statement).filter(
            models.Statement.month == month,
            models.Statement.year == year
        )
        period_label = f"{month}/{year}"
    elif year:
        # Join with Statement and filter by statement year
        query = query.join(models.Statement).filter(
            models.Statement.year == year
        )
        period_label = str(year)
    else:

        # Default: Try to find the latest statement
        latest_stmt = db.query(models.Statement).filter(
            models.Statement.user_id == user_id
        ).order_by(
            models.Statement.year.desc(),
            models.Statement.month.desc()
        ).first()

        if latest_stmt:
            # Use latest statement period
            query = query.join(models.Statement).filter(
                models.Statement.id == latest_stmt.id
            )
            period_label = f"Resumen {latest_stmt.month}/{latest_stmt.year}"
        else:
            # Fallback to date-based if no statements exist
            now = datetime.utcnow()
            if period == "month":
                start_date = now - timedelta(days=30)
            elif period == "quarter":
                start_date = now - timedelta(days=90)
            else:  # year
                start_date = now - timedelta(days=365)
            query = query.filter(models.Transaction.date >= start_date)
            period_label = period
    
    transactions = query.all()
    
    # Calculate totals - separate ARS and USD
    total_ars = sum(t.amount for t in transactions if not t.is_dollar)
    total_usd = sum(t.amount for t in transactions if t.is_dollar)
    
    # Get dolar_rate from the relevant statement
    dolar_rate = 0.0
    if transactions and transactions[0].statement:
        dolar_rate = transactions[0].statement.dolar_rate or 0.0
    
    # Calculate unified total (ARS + USD converted to ARS)
    total_unified = total_ars + (total_usd * dolar_rate) if dolar_rate > 0 else total_ars
    
    # Legacy total_spending (sum of all amounts as-is for backwards compatibility)
    total_spending = sum(t.amount for t in transactions)
    transaction_count = len(transactions)
    avg_transaction = total_spending / transaction_count if transaction_count > 0 else 0
    
    # Category breakdown
    category_totals: Dict[int, dict] = {}
    for t in transactions:
        if t.category_id:
            if t.category_id not in category_totals:
                cat = t.category
                category_totals[t.category_id] = {
                    "name": cat.name if cat else "Sin categoría",
                    "icon": cat.icon if cat else "📦",
                    "color": cat.color if cat else "#778899",
                    "total": 0,
                    "count": 0
                }
            category_totals[t.category_id]["total"] += t.amount
            category_totals[t.category_id]["count"] += 1
    
    # Convert to response format with percentages
    category_breakdown = []
    for cat_id, data in category_totals.items():
        percentage = (data["total"] / total_spending * 100) if total_spending > 0 else 0
        category_breakdown.append(schemas.CategorySummary(
            category_id=cat_id,
            category_name=data["name"],
            category_icon=data["icon"],
            category_color=data["color"],
            total=round(data["total"], 2),
            count=data["count"],
            percentage=round(percentage, 1)
        ))
    
    # Sort by total (highest first)
    category_breakdown.sort(key=lambda x: x.total, reverse=True)
    
    # Generate recommendations
    recommendations = generate_recommendations(
        db, user_id, transactions, category_breakdown, total_spending, period, is_dollar
    )
    
    return schemas.AnalyticsResponse(
        total_spending=round(total_spending, 2),
        total_ars=round(total_ars, 2),
        total_usd=round(total_usd, 2),
        total_unified=round(total_unified, 2),
        dolar_rate=dolar_rate,
        transaction_count=transaction_count,
        average_transaction=round(avg_transaction, 2),
        category_breakdown=category_breakdown,
        recommendations=recommendations,
        period=period_label
    )


def generate_recommendations(
    db: Session,
    user_id: int,
    transactions: List[models.Transaction],
    category_breakdown: List[schemas.CategorySummary],
    total_spending: float,
    period: str,
    is_dollar: bool = False
) -> List[schemas.Recommendation]:
    """
    Generate actionable recommendations based on spending patterns.
    Rules-based system with Argentinian Spanish messages.
    """
    recommendations = []
    currency = "USD" if is_dollar else "ARS"
    
    if not transactions:
        recommendations.append(schemas.Recommendation(
            type="info",
            icon="📊",
            message=f"Todavía no tenés transacciones en {currency} en este período. ¡Subí tu resumen para empezar a analizar!"
        ))
        return recommendations
    
    # Calculate previous period for comparison
    now = datetime.utcnow()
    if period == "month":
        prev_start = now - timedelta(days=60)
        prev_end = now - timedelta(days=30)
    else:
        prev_start = now - timedelta(days=180)
        prev_end = now - timedelta(days=90)
    
    prev_transactions = db.query(models.Transaction).filter(
        models.Transaction.user_id == user_id,
        models.Transaction.is_dollar == is_dollar,
        models.Transaction.date >= prev_start,
        models.Transaction.date < prev_end
    ).all()
    prev_total = sum(t.amount for t in prev_transactions)
    
    # Rule 1: Compare to previous period
    if prev_total > 0:
        change_percent = ((total_spending - prev_total) / prev_total) * 100
        if change_percent > 20:
            recommendations.append(schemas.Recommendation(
                type="warning",
                icon="📈",
                message=f"¡Ojo! Gastaste {abs(change_percent):.0f}% más que el período anterior en {currency}."
            ))
        elif change_percent < -10:
            recommendations.append(schemas.Recommendation(
                type="success",
                icon="🎉",
                message=f"¡Muy bien! Redujiste tus gastos un {abs(change_percent):.0f}% en {currency}."
            ))
    
    # Rule 2: Top category analysis
    if category_breakdown:
        top_cat = category_breakdown[0]
        if top_cat.percentage > 40:
            recommendations.append(schemas.Recommendation(
                type="warning",
                icon="⚠️",
                message=f"Tu categoría top '{top_cat.category_name}' representa el {top_cat.percentage:.0f}% de tus gastos."
            ))
        elif top_cat.percentage > 25:
            recommendations.append(schemas.Recommendation(
                type="info",
                icon="📍",
                message=f"La mayor parte de tus gastos ({top_cat.percentage:.0f}%) va a '{top_cat.category_name}'."
            ))
    
    # USD-specific recommendations
    if is_dollar:
        # Rule: Subscription count for USD
        if len(transactions) >= 3:
            recommendations.append(schemas.Recommendation(
                type="tip",
                icon="💳",
                message=f"Tenés {len(transactions)} suscripciones en USD (${total_spending:.2f}). ¿Las usás todas?"
            ))
    else:
        # ARS-specific rules
        # Rule 3: Food/delivery spending
        food_cats = [c for c in category_breakdown if "comida" in c.category_name.lower() or "restaurant" in c.category_name.lower()]
        if food_cats:
            food_total = sum(c.total for c in food_cats)
            food_percent = (food_total / total_spending * 100) if total_spending > 0 else 0
            if food_percent > 30:
                recommendations.append(schemas.Recommendation(
                    type="tip",
                    icon="🍳",
                    message=f"Gastás {food_percent:.0f}% en comida. Cocinar más en casa podría ahorrarte bastante."
                ))
        
        # Rule 4: Small purchases add up
        small_purchases = [t for t in transactions if t.amount < 500]
        if len(small_purchases) > 10:
            small_total = sum(t.amount for t in small_purchases)
            recommendations.append(schemas.Recommendation(
                type="info",
                icon="💸",
                message=f"Tenés {len(small_purchases)} compras chicas que suman ${small_total:.0f}."
            ))
    
    # Ensure we always have at least one recommendation
    if not recommendations:
        recommendations.append(schemas.Recommendation(
            type="success",
            icon="✅",
            message=f"¡Tus gastos en {currency} se ven bien balanceados!"
        ))
    
    # Limit to 5 recommendations
    return recommendations[:5]


def get_spending_trend(
    db: Session,
    user_id: int,
    period: str = "month",
    is_dollar: Optional[bool] = None,
    month: Optional[int] = None,
    year: Optional[int] = None
) -> List[dict]:
    """
    Get spending trend based on period:
    - month: daily data for 30 days
    - quarter: weekly data for 12 weeks
    - year: monthly data for 12 months
    is_dollar: None = all currencies
    """
    now = datetime.utcnow()
    
    # Build base query filter
    base_filter = [
        models.Transaction.user_id == user_id
    ]
    
    # Only filter by currency if specified
    if is_dollar is not None:
        base_filter.append(models.Transaction.is_dollar == is_dollar)
    
    if period == "month":
        # Daily data
        if month and year:
            # JOIN with Statement for filtering
            # But group by DATE for trend visualization
            
            # Re-build query since we accept filters above but here we need aggregate
            query = db.query(
                func.date(models.Transaction.date).label("date"),
                func.sum(models.Transaction.amount).label("total")
            ).join(models.Statement).filter(
                models.Statement.month == month,
                models.Statement.year == year,
                models.Transaction.user_id == user_id
            )
            
            if is_dollar is not None:
                query = query.filter(models.Transaction.is_dollar == is_dollar)
                
            results = query.group_by(func.date(models.Transaction.date)).order_by(func.date(models.Transaction.date)).all()
            
        else:
            # Default: Try to use Latest Statement if available
            latest_stmt = db.query(models.Statement).filter(
                models.Statement.user_id == user_id
            ).order_by(
                models.Statement.year.desc(),
                models.Statement.month.desc()
            ).first()

            if latest_stmt:
                 # Filter by Latest Statement
                query = db.query(
                    func.date(models.Transaction.date).label("date"),
                    func.sum(models.Transaction.amount).label("total")
                ).join(models.Statement).filter(
                    models.Statement.id == latest_stmt.id,
                    models.Statement.user_id == user_id
                )
                
                if is_dollar is not None:
                    query = query.filter(models.Transaction.is_dollar == is_dollar)
                    
                results = query.group_by(func.date(models.Transaction.date)).order_by(func.date(models.Transaction.date)).all()
            else:
                # Fallback to last 30 days
                start_date = now - timedelta(days=30)
                end_date = now
                
                base_filter.append(models.Transaction.date >= start_date)
                base_filter.append(models.Transaction.date < end_date)
                
                results = db.query(
                    func.date(models.Transaction.date).label("date"),
                    func.sum(models.Transaction.amount).label("total")
                ).filter(*base_filter).group_by(
                    func.date(models.Transaction.date)
                ).order_by(
                    func.date(models.Transaction.date)
                ).all()

        return [{"date": str(r.date), "total": float(r.total)} for r in results]
    
    elif period == "quarter":
        # Weekly data for 12 weeks
        start_date = now - timedelta(weeks=12)
        base_filter.append(models.Transaction.date >= start_date)
        
        # Group by week
        results = db.query(
            func.strftime('%Y-%W', models.Transaction.date).label("week"),
            func.sum(models.Transaction.amount).label("total")
        ).filter(*base_filter).group_by(
            func.strftime('%Y-%W', models.Transaction.date)
        ).order_by(
            func.strftime('%Y-%W', models.Transaction.date)
        ).all()
        
        return [{"date": f"Semana {r.week.split('-')[1]}", "total": float(r.total)} for r in results]
    
    else:  # year
        # Monthly data for 12 months
        if year:
            base_filter.append(extract('year', models.Transaction.date) == year)
        else:
            start_date = now - timedelta(days=365)
            base_filter.append(models.Transaction.date >= start_date)
        
        # Group by month
        results = db.query(
            func.strftime('%Y-%m', models.Transaction.date).label("month"),
            func.sum(models.Transaction.amount).label("total")
        ).filter(*base_filter).group_by(
            func.strftime('%Y-%m', models.Transaction.date)
        ).order_by(
            func.strftime('%Y-%m', models.Transaction.date)
        ).all()
        
        month_names = ['Ene', 'Feb', 'Mar', 'Abr', 'May', 'Jun', 'Jul', 'Ago', 'Sep', 'Oct', 'Nov', 'Dic']
        return [{"date": month_names[int(r.month.split('-')[1]) - 1], "total": float(r.total)} for r in results]


def get_available_periods(db: Session, user_id: int) -> dict:
    """Get available months and years that have transaction data"""
    # Get distinct months/years from statements
    statements = db.query(
        models.Statement.month,
        models.Statement.year
    ).filter(
        models.Statement.user_id == user_id
    ).distinct().order_by(
        models.Statement.year.desc(),
        models.Statement.month.desc()
    ).all()
    
    months = [{"month": s.month, "year": s.year} for s in statements]
    years = list(set(s.year for s in statements))
    years.sort(reverse=True)
    
    return {"months": months, "years": years}

