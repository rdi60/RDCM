from decimal import Decimal

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.exceptions import ValidationError
from django.db.models import Q
from django.shortcuts import get_object_or_404, redirect, render

from scheduling.models import Appointment

from .forms import InvoiceForm, LineItemForm, PaymentForm
from .models import Invoice, InvoiceLineItem, Payment


@login_required
def invoice_list(request):
    query = request.GET.get("q", "").strip()
    status = request.GET.get("status", "")
    invoices = Invoice.objects.select_related("patient")
    if query:
        invoices = invoices.filter(
            Q(invoice_number__icontains=query)
            | Q(patient__full_name__icontains=query)
            | Q(patient__uhid__icontains=query)
        )
    if status:
        invoices = invoices.filter(status=status)
    return render(
        request,
        "billing/invoice_list.html",
        {"invoices": invoices[:200], "query": query, "status": status, "statuses": Invoice.Status.choices},
    )


@login_required
def invoice_create(request):
    appointment_id = request.GET.get("appointment")
    appointment = None
    initial = {}
    if appointment_id:
        appointment = get_object_or_404(Appointment, pk=appointment_id)
        initial["patient"] = appointment.patient_id

    if request.method == "POST":
        form = InvoiceForm(request.POST)
        if form.is_valid():
            invoice = form.save(commit=False)
            invoice.created_by = request.user
            if appointment_id:
                invoice.appointment_id = appointment_id
            invoice.save()
            if appointment and appointment.treatment:
                InvoiceLineItem.objects.create(
                    invoice=invoice,
                    treatment=appointment.treatment,
                    description=appointment.treatment.name,
                    quantity=1,
                    unit_price=appointment.treatment.price,
                )
            messages.success(request, f"Created draft invoice {invoice.invoice_number}.")
            return redirect("invoice_detail", pk=invoice.pk)
    else:
        form = InvoiceForm(initial=initial)

    return render(request, "billing/invoice_form.html", {"form": form, "appointment": appointment})


@login_required
def invoice_detail(request, pk):
    invoice = get_object_or_404(Invoice.objects.select_related("patient", "appointment"), pk=pk)
    line_item_form = LineItemForm()
    payment_form = PaymentForm()

    if request.method == "POST":
        action = request.POST.get("action")

        if action == "add_item" and invoice.status == Invoice.Status.DRAFT:
            line_item_form = LineItemForm(request.POST)
            if line_item_form.is_valid():
                item = line_item_form.save(commit=False)
                item.invoice = invoice
                if not item.description and item.treatment:
                    item.description = item.treatment.name
                item.save()
                messages.success(request, "Line item added.")
                return redirect("invoice_detail", pk=invoice.pk)

        elif action == "record_payment" and invoice.status in (
            Invoice.Status.ISSUED,
            Invoice.Status.PARTIALLY_PAID,
        ):
            payment_form = PaymentForm(request.POST)
            if payment_form.is_valid():
                payment = payment_form.save(commit=False)
                payment.invoice = invoice
                payment.received_by = request.user
                try:
                    payment.full_clean()
                    payment.save()
                    messages.success(request, f"Recorded payment {payment.receipt_number}.")
                    return redirect("invoice_detail", pk=invoice.pk)
                except ValidationError as e:
                    payment_form.add_error(None, e)

        elif action == "issue":
            try:
                invoice.issue()
                messages.success(request, f"Invoice {invoice.invoice_number} issued.")
            except ValidationError as e:
                messages.error(request, "; ".join(e.messages))
            return redirect("invoice_detail", pk=invoice.pk)

        elif action == "void":
            try:
                invoice.void()
                messages.success(request, f"Invoice {invoice.invoice_number} voided.")
            except ValidationError as e:
                messages.error(request, "; ".join(e.messages))
            return redirect("invoice_detail", pk=invoice.pk)

    return render(
        request,
        "billing/invoice_detail.html",
        {"invoice": invoice, "line_item_form": line_item_form, "payment_form": payment_form},
    )


@login_required
def invoice_remove_item(request, pk, item_pk):
    invoice = get_object_or_404(Invoice, pk=pk)
    if request.method == "POST" and invoice.status == Invoice.Status.DRAFT:
        InvoiceLineItem.objects.filter(pk=item_pk, invoice=invoice).delete()
        messages.success(request, "Line item removed.")
    return redirect("invoice_detail", pk=pk)


@login_required
def invoice_print(request, pk):
    invoice = get_object_or_404(Invoice.objects.select_related("patient"), pk=pk)
    return render(request, "billing/invoice_print.html", {"invoice": invoice})


@login_required
def payment_print(request, pk):
    payment = get_object_or_404(Payment.objects.select_related("invoice", "invoice__patient"), pk=pk)
    return render(request, "billing/receipt_print.html", {"payment": payment})


@login_required
def dues_list(request):
    invoices = Invoice.objects.filter(
        status__in=[Invoice.Status.ISSUED, Invoice.Status.PARTIALLY_PAID]
    ).select_related("patient")
    rows = []
    total_due = Decimal("0.00")
    for inv in invoices:
        due = inv.balance_due
        if due > 0:
            rows.append({"invoice": inv, "due": due})
            total_due += due
    rows.sort(key=lambda r: r["due"], reverse=True)
    return render(request, "billing/dues_list.html", {"rows": rows, "total_due": total_due})
