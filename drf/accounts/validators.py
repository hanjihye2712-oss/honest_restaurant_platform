import re
from django.core.exceptions import ValidationError


class SpecialCharValidator:
    def validate(self, password, user=None):
        if not re.search(r'[!@#$%^&*()\-_=+\[\]{};:\'",.<>/?`~\\|]', password):
            raise ValidationError(
                "비밀번호에 특수문자(!@#$%^&* 등)를 하나 이상 포함해야 합니다.",
                code="no_special_char",
            )

    def get_help_text(self):
        return "비밀번호에 특수문자를 하나 이상 포함하세요."
