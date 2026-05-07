def user_role(request):
    """
    모든 템플릿에 user_role 변수를 주입한다.
    - 'guest'  : 로그인한 손님
    - 'owner'  : 사장님
    - 'admin'  : 관리자
    - ''       : 비로그인
    """
    if not request.user.is_authenticated:
        return {'user_role': ''}

    try:
        role = request.user.profile.role
    except Exception:
        role = 'guest'

    return {'user_role': role}
