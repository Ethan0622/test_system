import random

from .models import MyClass


def generate_invitation_code():
    while (1):
        randomCodeList = random.sample(
            "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789", 8)
        code = ''
        code = code.join(randomCodeList)
        checkClass = MyClass.objects.filter(invitation_code=code)
        if not checkClass:
            return code