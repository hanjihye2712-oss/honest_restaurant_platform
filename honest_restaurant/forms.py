from django import forms
from .models import Review, ReceiptVerification, RestaurantMedia


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


class ReviewForm(forms.ModelForm):
    class Meta:
        model = Review
        fields = ["rating", "content"]
        widgets = {
            "rating": forms.RadioSelect(),
            "content": forms.Textarea(attrs={
                "rows": 4,
                "placeholder": "이 가게에 대한 솔직한 리뷰를 남겨주세요.",
            }),
        }
        labels = {
            "rating": "별점",
            "content": "리뷰",
        }
