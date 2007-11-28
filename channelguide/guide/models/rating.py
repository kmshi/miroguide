from channelguide import util
from channelguide.guide import tables
from sqlhelper.orm import Record
from sqlhelper.orm.columns import Subquery
class Rating(Record):
    table = tables.channel_rating

    @classmethod
    def update_rating(cls, connection, channel, user, rating):
        try:
            dbRating = cls.query(cls.c.user_id==user.id,
                cls.c.channel_id==channel.id).get(connection)
        except Exception:
            dbRating = cls()
            dbRating.channel_id = channel.id
            dbRating.user_id = user.id
            dbRating.rating = None
        if rating not in range(6):
            raise ValueError('bad rating: %s' % rating)
        try:
            gen_rating = GeneratedRatings().query().get(connection, channel.id)
        except:
            gen_rating = GeneratedRatings()
            gen_rating.channel_id = channel.id
            gen_rating.count = gen_rating.average = gen_rating.total = 0
        if dbRating.rating:
            gen_rating.count -= 1
            gen_rating.total -= dbRating.rating
        dbRating.rating = int(rating)
        if dbRating.rating == 0:
            dbRating.rating = None
        elif user.approved:
            gen_rating.count += 1
            gen_rating.total += dbRating.rating
            gen_rating.average = float(gen_rating.total) / gen_rating.count
            gen_rating.save(connection)
        dbRating.save(connection)


class GeneratedRatings(Record):
    table = tables.generated_ratings
