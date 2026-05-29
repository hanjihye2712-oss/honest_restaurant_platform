from django import forms
from django.conf import settings
from .models import PublicRestaurantData, ReceiptVerification, RestaurantMedia, RestaurantMenuItem

_IMAGE_TYPES = {'image/jpeg', 'image/png', 'image/webp', 'image/gif'}
_VIDEO_TYPES = {'video/mp4', 'video/quicktime', 'video/x-msvideo', 'video/webm'}
_MAX_IMAGE_MB = getattr(settings, 'MAX_UPLOAD_SIZE_IMAGE_MB', 10)
_MAX_VIDEO_MB = getattr(settings, 'MAX_UPLOAD_SIZE_VIDEO_MB', 100)


class RestaurantMediaForm(forms.Form):
    file = forms.FileField(
        label="",
        widget=forms.FileInput(attrs={"accept": "image/*,video/*"}),
    )

    def clean_file(self):
        f = self.cleaned_data['file']
        content_type = getattr(f, 'content_type', '')
        is_video = content_type in _VIDEO_TYPES
        is_image = content_type in _IMAGE_TYPES
        if not (is_image or is_video):
            raise forms.ValidationError("JPG·PNG·MP4 등 이미지/동영상 파일만 업로드할 수 있습니다.")
        limit_mb = _MAX_VIDEO_MB if is_video else _MAX_IMAGE_MB
        if f.size > limit_mb * 1024 * 1024:
            raise forms.ValidationError(f"파일 크기는 {limit_mb}MB 이하여야 합니다.")
        return f


class MenuItemForm(forms.ModelForm):
    class Meta:
        model  = RestaurantMenuItem
        fields = ["name", "price"]
        labels = {"name": "메뉴명", "price": "가격(원)"}
        widgets = {
            "name":  forms.TextInput(attrs={"placeholder": "예: 김밥"}),
            "price": forms.NumberInput(attrs={"placeholder": "예: 3000", "min": 0}),
        }


class RestaurantInfoForm(forms.ModelForm):
    class Meta:
        model  = PublicRestaurantData
        fields = ["address_road", "address_jibun", "phone"]


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

    def clean_receipt_image(self):
        f = self.cleaned_data.get('receipt_image')
        if f:
            content_type = getattr(f, 'content_type', '')
            if content_type not in _IMAGE_TYPES:
                raise forms.ValidationError("JPG·PNG 등 이미지 파일만 업로드할 수 있습니다.")
            if f.size > _MAX_IMAGE_MB * 1024 * 1024:
                raise forms.ValidationError(f"파일 크기는 {_MAX_IMAGE_MB}MB 이하여야 합니다.")
        return f
