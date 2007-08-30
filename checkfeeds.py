from channelguide import manage, init
init.init_external_libraries()
from channelguide import db
from channelguide.guide.forms import channels
from channelguide.guide.models.user import User
from channelguide.guide.models.channel import Channel
from django.newforms import ValidationError
database = db.connect()
user = User.query(User.c.username=="miroguide").get(database)
checker = channels.RSSFeedField()
checker.connection = database

#print checker.check_missing("http://mediamatters.org/tools/syndication/latest.rss")

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
        if ModeratorAction.query(ModeratorAction.c.channel_id==channel.id,
                ModeratorAction.c.user_id==user.id).order_by('timestamp', desc=True).limit(1).get(database).timestamp > time.now() + 60*60*24*14:
            # two weeks old
            note = make_rejection_note(channel, user, "BROKEN")
            note.save(database)
            note.send_email(database)
            channel.change_state(user, Channel.REJECTED, database).save(database)
            database.commit()
    def good(channel):
        channel.change_state(user, Channel.APPROVED, database).save(database)
        database.commit()
    scan(query, good, error)

if __name__ == "__main__":
    import sys
    if len(sys.argv) > 1 and sys.argv[1] == 'full':
        fullScan()
    else:
        dailyScan()
