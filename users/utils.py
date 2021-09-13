from rest_framework_jwt.utils import jwt_decode_handler

def jwt_response_payload_handler(token, user=None, request=None):
    """
    自定义jwt认证成功返回数据
    :token  返回的jwt
    :user   当前登录的用户信息[对象]
    :request 当前本次客户端提交过来的数据
    """
    return {
        'id': user.id,
        'number': user.number,
        'type':user.type,
        'realname':user.realname,
        'token': token,
    }

def decodeToken(req):
    token = req.META.get('HTTP_AUTHORIZATION')[7:]
    return jwt_decode_handler(token)