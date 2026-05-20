from django import forms


class ReviewWithRatingForm(forms.Form):
    score = forms.IntegerField(
        widget=forms.HiddenInput(),
        min_value=1,
        max_value=5,
        error_messages={"required": "별점을 선택해주세요."},
    )
    content = forms.CharField(
        widget=forms.Textarea(attrs={
            "rows": 4,
            "placeholder": "이 가게에 대한 솔직한 리뷰를 남겨주세요.",
        }),
        label="리뷰",
    )
