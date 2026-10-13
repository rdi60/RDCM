"""
Shared stock-movement logic used by both the transfer and consumption
views: staff think in terms of "move 50 gloves", not batch numbers, so
both pick batches to fulfil a requested quantity oldest-expiry-first
(falling back to oldest-received-first for batches with no expiry date).
"""
from datetime import date

from .models import StockBatch


def available_batches(item, location):
    """[(batch, quantity_available_here), ...] for batches with stock > 0
    at this location, soonest-to-expire first."""
    batch_ids = (
        item.batches.filter(transactions__location=location)
        .values_list("id", flat=True)
        .distinct()
    )
    rows = []
    for batch in StockBatch.objects.filter(id__in=batch_ids):
        qty = batch.quantity_at(location)
        if qty > 0:
            rows.append((batch, qty))
    rows.sort(key=lambda row: (row[0].expiry_date or date.max, row[0].created_at))
    return rows


def total_available(item, location):
    return sum(qty for _, qty in available_batches(item, location))
