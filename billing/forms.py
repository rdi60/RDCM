from django import forms

from clinic.models import Treatment

from .models import Invoice, InvoiceLineItem, Payment


class InvoiceForm(forms.ModelForm):
    class Meta:
        model = Invoice
        fields = ["patient", "discount", "tax_percent", "notes"]
        widgets = {"notes": forms.Textarea(attrs={"rows": 2})}


class LineItemForm(forms.ModelForm):
    class Meta:
        model = InvoiceLineItem
        fields = ["treatment", "description", "quantity", "unit_price"]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["treatment"].required = False
        self.fields["treatment"].queryset = Treatment.objects.filter(is_active=True)


class PaymentForm(forms.ModelForm):
    class Meta:
        model = Payment
        fields = ["amount", "mode", "notes"]
