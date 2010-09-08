# Copyright (c) 2008 Participatory Culture Foundation
# See LICENSE for details.

from django.contrib.auth import decorators

admin_required = decorators.user_passes_test(lambda u: u.is_superuser)
