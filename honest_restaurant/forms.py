from django import forms
from .models import ReceiptVerification, RestaurantMedia


class RestaurantMediaForm(forms.Form):
    file = forms.FileField(
        label="",
        widget=forms.FileInput(attrs={"accept": "image/*,video/*"}),
    )


class ReceiptVerificationForm(forms.ModelForm):
    class Meta:
        model = ReceiptVerification
        fields = ["receipt_image", "comment"]
        widgets = {
            "comment": forms.Textarea(attrs={
                "rows": 3,
                "placeholder": "가격·음식·분위기 한 줄 후기 (선택)",
            }),
        }
        labels = {
            "receipt_image": "",
            "comment": "",
        }
