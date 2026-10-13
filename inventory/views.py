from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.exceptions import ValidationError
from django.db.models import Sum
from django.shortcuts import get_object_or_404, redirect, render

from . import services
from .forms import ConsumptionForm, PurchaseOrderForm, PurchaseOrderLineForm, ReceiveLineForm, TransferRequestForm
from .models import (
    GoodsReceiptLine,
    GoodsReceiptNote,
    Item,
    PurchaseOrder,
    PurchaseOrderLine,
    StockBatch,
    StockTransaction,
    StockTransfer,
)


@login_required
def po_list(request):
    orders = PurchaseOrder.objects.select_related("supplier")
    return render(request, "inventory/po_list.html", {"orders": orders[:200]})


@login_required
def po_create(request):
    if request.method == "POST":
        form = PurchaseOrderForm(request.POST)
        if form.is_valid():
            po = form.save(commit=False)
            po.created_by = request.user
            po.save()
            messages.success(request, f"Created draft {po.po_number}.")
            return redirect("po_detail", pk=po.pk)
    else:
        form = PurchaseOrderForm()
    return render(request, "inventory/po_form.html", {"form": form})


@login_required
def po_detail(request, pk):
    po = get_object_or_404(PurchaseOrder.objects.select_related("supplier"), pk=pk)
    line_form = PurchaseOrderLineForm()

    if request.method == "POST":
        action = request.POST.get("action")

        if action == "add_line" and po.status == PurchaseOrder.Status.DRAFT:
            line_form = PurchaseOrderLineForm(request.POST)
            if line_form.is_valid():
                line = line_form.save(commit=False)
                line.purchase_order = po
                line.save()
                messages.success(request, "Line added.")
                return redirect("po_detail", pk=po.pk)

        elif action == "send":
            try:
                po.send()
                messages.success(request, f"{po.po_number} sent to {po.supplier}.")
            except ValidationError as e:
                messages.error(request, "; ".join(e.messages))
            return redirect("po_detail", pk=po.pk)

        elif action == "cancel":
            try:
                po.cancel()
                messages.success(request, f"{po.po_number} cancelled.")
            except ValidationError as e:
                messages.error(request, "; ".join(e.messages))
            return redirect("po_detail", pk=po.pk)

        elif action == "receive_line":
            po_line = get_object_or_404(PurchaseOrderLine, pk=request.POST.get("po_line_id"), purchase_order=po)
            if po.status not in (PurchaseOrder.Status.SENT, PurchaseOrder.Status.PARTIALLY_RECEIVED):
                messages.error(request, "This purchase order isn't open for receiving.")
            else:
                receive_form = ReceiveLineForm(request.POST, po_line=po_line)
                if receive_form.is_valid():
                    grn = GoodsReceiptNote.objects.create(
                        purchase_order=po,
                        location=receive_form.cleaned_data["location"],
                        received_by=request.user,
                    )
                    GoodsReceiptLine.objects.create(
                        grn=grn,
                        po_line=po_line,
                        batch_number=receive_form.cleaned_data["batch_number"],
                        expiry_date=receive_form.cleaned_data["expiry_date"],
                        quantity_received=receive_form.cleaned_data["quantity"],
                        unit_cost=receive_form.cleaned_data["unit_cost"],
                    )
                    messages.success(
                        request,
                        f"Received {receive_form.cleaned_data['quantity']} x {po_line.item} ({grn.grn_number}).",
                    )
                else:
                    messages.error(request, "Couldn't record that receipt — check the values.")
            return redirect("po_detail", pk=po.pk)

    receive_rows = []
    if po.status in (PurchaseOrder.Status.SENT, PurchaseOrder.Status.PARTIALLY_RECEIVED):
        for line in po.lines.all():
            if line.quantity_pending > 0:
                receive_rows.append({"line": line, "form": ReceiveLineForm(po_line=line)})

    return render(
        request,
        "inventory/po_detail.html",
        {"po": po, "line_form": line_form, "receive_rows": receive_rows},
    )


@login_required
def transfer_create(request):
    form = TransferRequestForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        item = form.cleaned_data["item"]
        from_location = form.cleaned_data["from_location"]
        to_location = form.cleaned_data["to_location"]
        quantity = form.cleaned_data["quantity"]

        if from_location == to_location:
            form.add_error(None, "Source and destination must be different.")
        else:
            available = services.total_available(item, from_location)
            if quantity > available:
                form.add_error(None, f"Only {available} {item.unit} available at {from_location}.")
            else:
                _fulfil_from_batches(
                    item, from_location, quantity,
                    on_batch=lambda batch, take: _create_transfer(
                        batch, from_location, to_location, take, request.user, form.cleaned_data["notes"]
                    ),
                )
                messages.success(request, f"Transferred {quantity} {item.unit} of {item.name} to {to_location}.")
                return redirect("stock_levels")

    return render(request, "inventory/transfer_form.html", {"form": form})


@login_required
def consumption_create(request):
    form = ConsumptionForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        item = form.cleaned_data["item"]
        location = form.cleaned_data["location"]
        quantity = form.cleaned_data["quantity"]

        available = services.total_available(item, location)
        if quantity > available:
            form.add_error(None, f"Only {available} {item.unit} available at {location}.")
        else:
            _fulfil_from_batches(
                item, location, quantity,
                on_batch=lambda batch, take: StockTransaction.objects.create(
                    item=item,
                    batch=batch,
                    location=location,
                    quantity=-take,
                    tx_type=StockTransaction.TxType.CONSUMPTION,
                    appointment=form.cleaned_data["appointment"],
                    created_by=request.user,
                    notes=form.cleaned_data["notes"],
                ),
            )
            messages.success(request, f"Recorded use of {quantity} {item.unit} of {item.name}.")
            return redirect("stock_levels")

    return render(request, "inventory/consumption_form.html", {"form": form})


def _fulfil_from_batches(item, location, quantity, on_batch):
    remaining = quantity
    for batch, available in services.available_batches(item, location):
        if remaining <= 0:
            break
        take = min(available, remaining)
        on_batch(batch, take)
        remaining -= take


def _create_transfer(batch, from_location, to_location, quantity, user, notes):
    StockTransfer.objects.create(
        batch=batch,
        from_location=from_location,
        to_location=to_location,
        quantity=quantity,
        transferred_by=user,
        notes=notes,
    )


@login_required
def stock_levels(request):
    grouped = (
        StockTransaction.objects.values("item_id", "item__name", "item__unit", "location_id", "location__name")
        .annotate(qty=Sum("quantity"))
        .filter(qty__gt=0)
        .order_by("item__name", "location__name")
    )
    return render(request, "inventory/stock_levels.html", {"rows": grouped})


@login_required
def alerts(request):
    low_stock = [item for item in Item.objects.filter(is_active=True, reorder_level__gt=0) if item.is_low_stock]

    expiring = [
        batch
        for batch in StockBatch.objects.filter(expiry_date__isnull=False).select_related("item")
        if batch.quantity_remaining > 0 and batch.is_expiring_soon
    ]
    expiring.sort(key=lambda b: b.expiry_date)

    return render(request, "inventory/alerts.html", {"low_stock": low_stock, "expiring": expiring})
