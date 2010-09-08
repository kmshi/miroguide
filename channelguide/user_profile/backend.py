from django.contrib.auth import authenticate
from django.contrib.auth.models import User, Group
from django.contrib.auth.backends import ModelBackend
from models import UserProfile

class UserProfileMigrationBackend(ModelBackend):

    def authenticate(self, username=None, password=None):
        try:
            profile = UserProfile.objects.get(user__username=username)
        except UserProfile.DoesNotExist:
            return

        if not profile.check_password(password):
            return

        user = User.objects.get(username=username)

        if profile.role == 'A':
            user.is_superuser = True
            user.save()

        if profile.role in ('A', 'S'):
            user.groups.add(Group.objects.get_or_create(
                    name='cg_supermoderator')[0])

        if profile.role in ('A', 'S', 'M'):
            user.groups.add(
                Group.objects.get_or_create(name='cg_moderator')[0])

        if not user.has_usable_password():
            user.set_password(password)
            user.save()

        return user

class UserEmailLoginBackend(ModelBackend):
    def authenticate(self, username=None, password=None):
        try:
            user = User.objects.get(email=username)
        except User.DoesNotExist:
            try:
                user_profile = UserProfile.objects.get(email=username)
            except UserProfile.DoesNotExist:
                return
            else:
                username = user_profile.user.username
        else:
            username=user.username

        # we've pulled out the real username, now authenticate them
        return authenticate(username=username, password=password)

