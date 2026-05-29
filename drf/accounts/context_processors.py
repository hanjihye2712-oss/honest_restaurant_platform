def user_role(request):
    """
    모든 템플릿에 user_role, owned_restaurant_name 변수를 주입한다.
    - 'guest'  : 로그인한 손님
    - 'owner'  : 사장님
    - 'admin'  : 관리자
    - ''       : 비로그인
    """
    if not request.user.is_authenticated:
        return {'user_role': '', 'owned_restaurant_name': ''}

    try:
        role = request.user.profile.role
    except Exception:
        role = 'guest'

    owner_display = ''
    if role == 'owner':
        try:
            # 닉네임(first_name) 우선, 없으면 가게 이름
            name = request.user.first_name or request.user.owned_restaurant.name
            owner_display = f"{name} 사장님"
        except Exception:
            pass

    return {
        'user_role': role,
        'owner_display': owner_display,
    }
