from channelguide import manage, init
init.init_external_libraries()
from channelguide import db
from channelguide.guide.forms import channels
from channelguide.guide.models.user import User, ModeratorAction
from channelguide.guide.models.channel import Channel
from channelguide.guide.models.note import ChannelNote
from channelguide.guide import emailmessages
from django.newforms import ValidationError
from datetime import datetime, timedelta
database = db.connect()
user = User.query(User.c.username=="miroguide").get(database)
checker = channels.RSSFeedField()
checker.connection = database

def sendNote(channel, email):
    note = ChannelNote(user, email.title, email.body,
            ChannelNote.MODERATOR_TO_OWNER)
    note.channel = channel
    note.save(database)
    database.commit()
    channel.join('owner').execute(database)
    if channel.owner.email is not None:
        email.send_email(channel.owner.email)

def scan(query, goodFunc=None, errorFunc=None):
    for channel in query.execute(database):
        try:
            checker.check_missing(channel.url)
        except Exception:
            if errorFunc is not None:
                errorFunc(channel)
        else:
            if goodFunc is not None:
                goodFunc(channel)

def fullScan():
    query = Channel.query_approved()
    def error(channel):
        print channel.id, channel
        channel.change_state(user, Channel.SUSPENDED, database)
        channel.save(database)
        database.commit()
    scan(query, errorFunc=error)

def dailyScan():
    query = Channel.query(Channel.c.state==Channel.SUSPENDED)
    def error(channel):
        lastMA = ModeratorAction.query(ModeratorAction.c.channel_id==channel.id,
                ModeratorAction.c.user_id==user.id).order_by('timestamp', desc=True).limit(1).get(database)
        print lastMA.channel_id, lastMA.timestamp
        if datetime.now() - timedelta(5) < lastMA.timestamp < datetime.now() - timedelta(days=4):
            print 'sending broken notice for', channel
            email = emailmessages.SuspendedChannelEmail(channel)
            sendNote(channel, email)
            print 'e-mail sent'
        elif lastMA.timestamp < datetime.now() - timedelta(weeks=2):
            print 'sending rejection e-mail for', channel
            email = emailmessages.RejectedChannelEmail(channel)
            sendNote(channel, email)
            print 'e-mail sent'
            channel.change_state(user, Channel.REJECTED, database)
            channel.save(database)
            database.commit()
    def good(channel):
        channel.change_state(user, Channel.APPROVED, database)
        channel.save(database)
        database.commit()
    scan(query, good, error)

if __name__ == "__main__":
    import sys
    if len(sys.argv) > 1 and sys.argv[1] == 'full':
        print 'full scan'
        fullScan()
    else:
        print 'daily scan'
        dailyScan()
