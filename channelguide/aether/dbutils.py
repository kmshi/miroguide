# Copyright (c) 2009 Michael C. Urbanski
# See LICENSE for details.

def get_db_lock_for_user (conn, user):
    ret = conn.execute ("SELECT GET_LOCK('user_lock_%s', 30)", user.id)[0][0]
    if not ret:
        raise Exception ()

def release_db_lock_for_user (conn, user):
    conn.execute ("SELECT RELEASE_LOCK('user_lock_%s')", user.id)

def user_lock_required (func):
    def _dec (request, *args, **kwargs):
        conn = request.connection
        user = request.user

        get_db_lock_for_user (conn, user)

        try:
            ret = func (request, *args, **kwargs)
            release_db_lock_for_user (conn, user)
        except:
            release_db_lock_for_user (conn, user)
            raise

        return ret

    return _dec;