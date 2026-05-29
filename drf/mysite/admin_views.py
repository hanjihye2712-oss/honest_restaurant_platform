"""
mysite.admin_views
==================
운영 관리 뷰는 management 앱으로 이전됨.
이 파일에는 mysite 전용 소규모 뷰만 남긴다.
"""
from django.shortcuts import redirect
from django.views import View
from django.http import HttpResponse
from django.template.loader import render_to_string


class DesignPreviewView(View):
    """GET /management/design-preview/ — 대시보드 디자인 후보 미리보기 (관리자 전용)"""

    def dispatch(self, request, *args, **kwargs):
        try:
            role = request.user.profile.role
        except Exception:
            role = ''
        if role != 'admin':
            return redirect('/')
        return super().dispatch(request, *args, **kwargs)

    def get(self, request):
        html = render_to_string('admin_panel/design_preview.html')
        return HttpResponse(html)
