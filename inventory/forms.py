from django import forms
from django.utils import timezone

from scheduling.models import Appointment

from .models import Item, PurchaseOrder, PurchaseOrderLine, StockLocation


class PurchaseOrderForm(forms.ModelForm):
    class Meta:
        model = PurchaseOrder
        fields = ["supplier", "notes"]
        widgets = {"notes": forms.Textarea(attrs={"rows": 2})}


class PurchaseOrderLineForm(forms.ModelForm):
    class Meta:
        model = PurchaseOrderLine
        fields = ["item", "quantity_ordered", "unit_cost"]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["item"].queryset = Item.objects.filter(is_active=True)


class ReceiveLineForm(forms.Form):
    location = forms.ModelChoiceField(queryset=StockLocation.objects.filter(type=StockLocation.LocationType.STORE))
    quantity = forms.IntegerField(min_value=1)
    batch_number = forms.CharField(required=False, max_length=50)
    expiry_date = forms.DateField(required=False, widget=forms.DateInput(attrs={"type": "date"}))
    unit_cost = forms.DecimalField(min_value=0, decimal_places=2, max_digits=10)

    def __init__(self, *args, po_line=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.po_line = po_line
        if po_line and not self.is_bound:
            self.fields["unit_cost"].initial = po_line.unit_cost
            self.fields["quantity"].initial = po_line.quantity_pending

    def clean_quantity(self):
        quantity = self.cleaned_data["quantity"]
        if self.po_line and quantity > self.po_line.quantity_pending:
            raise forms.ValidationError(
                f"Only {self.po_line.quantity_pending} still pending on this line."
            )
        return quantity


class TransferRequestForm(forms.Form):
    item = forms.ModelChoiceField(queryset=Item.objects.filter(is_active=True))
    from_location = forms.ModelChoiceField(queryset=StockLocation.objects.filter(is_active=True))
    to_location = forms.ModelChoiceField(queryset=StockLocation.objects.filter(is_active=True))
    quantity = forms.IntegerField(min_value=1)
    notes = forms.CharField(required=False, max_length=255)


class ConsumptionForm(forms.Form):
    item = forms.ModelChoiceField(queryset=Item.objects.filter(is_active=True))
    location = forms.ModelChoiceField(
        queryset=StockLocation.objects.filter(is_active=True, type=StockLocation.LocationType.ROOM)
    )
    quantity = forms.IntegerField(min_value=1)
    appointment = forms.ModelChoiceField(queryset=Appointment.objects.none(), required=False)
    notes = forms.CharField(required=False, max_length=255)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Only today's appointments are realistic candidates to tie a
        # consumption entry to; narrows a dropdown that would otherwise
        # grow without bound.
        self.fields["appointment"].queryset = Appointment.objects.filter(
            start_time__date=timezone.localdate()
        ).select_related("patient", "doctor")
