from django.db import models
from django.db.models.deletion import CASCADE


class MyClass(models.Model):
    class_name = models.CharField(max_length=255, null=False)
    create_time = models.DateField(null=False, auto_now_add=True)
    invitation_code = models.CharField(max_length=30, unique=True, null=False)
    teacher_id = models.ForeignKey(to="users.MyUser", on_delete=CASCADE, null=False)
    # students = models.ManyToManyField(MyUser, through='Classroom')


# class Classroom(models.Model):
#     theclass = models.ForeignKey(MyClass, on_delete=CASCADE)
#     thestudent = models.ForeignKey(MyUser, on_delete=CASCADE)
#     date_joined = models.DateField(auto_now_add=True)
