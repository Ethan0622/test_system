from rest_framework_jwt.utils import jwt_decode_handler


def jwt_response_payload_handler(token, user=None, unfinished_test=None, request=None):
    """
    自定义jwt认证成功返回数据
    :token  返回的jwt
    :user   当前登录的用户信息[对象]
    :request 当前本次客户端提交过来的数据
    """
    if unfinished_test != None:
        is_unfinished = True
        unfinished_info = {
            key: val
            for key, val in unfinished_test.data.items()
            if key == 'test_id' or key == 'start_time' or key == 'finish_object_test'
        }
    else:
        is_unfinished = False
        unfinished_info = {}

    return {
        "userInfo": {
            'id': user.id,
            'number': user.number,
            'type': user.type,
            'realname': user.realname,
            'token': token,
            'init_ability': user.init_ability
        },
        "unfinishedTest": {
            'isUnfinished': is_unfinished,
            'unfinishedInfo': unfinished_info
        }
    }


def decode_token(req):
    token = req.META.get('HTTP_AUTHORIZATION')[7:]
    return jwt_decode_handler(token)
