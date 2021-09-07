from django.db import models
from django.contrib.auth.models import (BaseUserManager, AbstractBaseUser)
from django.core.validators import (MinValueValidator, MaxValueValidator)


class MyUserManager(BaseUserManager):
    def create_user(self, number, type, password=None):
        if not number:
            raise ValueError('Users must have an school number ID')

        user = self.model(
            number=number,
            type=type,
        )

        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_superuser(self, number, type, password=None):
        user = self.create_user(
            number,
            password=password,
            type=type,
        )
        user.is_admin = True
        user.save(using=self._db)
        return user


class MyUser(AbstractBaseUser):
    number = models.CharField(verbose_name='student-ID/employee-ID',
                              max_length=60,
                              unique=True)
    type = models.IntegerField(
        verbose_name='user-type; 0=student; 1=teacher',
        default=0,
        validators=[MinValueValidator(0),
                    MaxValueValidator(1)])
    realname = models.CharField(verbose_name='user-real-name',
                                default='',
                                max_length=100)
    email = models.EmailField(verbose_name='user-email',
                              max_length=255,
                              default='')
    is_active = models.BooleanField(default=True)
    is_admin = models.BooleanField(default=False)

    objects = MyUserManager()

    USERNAME_FIELD = 'number'
    REQUIRED_FIELDS = ['type']

    def __str__(self):
        return self.number

    def has_perm(self, perm, obj=None):
        "Does the user have a specific permission?"
        # Simplest possible answer: Yes, always
        return True

    def has_module_perms(self, app_label):
        "Does the user have permissions to view the app `app_label`?"
        # Simplest possible answer: Yes, always
        return True

    @property
    def is_staff(self):
        "Is the user a member of staff?"
        # Simplest possible answer: All admins are staff
        return self.is_admin
