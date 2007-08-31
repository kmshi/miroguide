from channelguide import util
from channelguide.guide import tables
from sqlhelper.orm import Record
class Rating(Record):
    table = tables.channel_rating

    def get_rating_url(self, rating):
        return '/channels/rating/%s/%s' % (self.channel_id, rating)

    def percentage(self):
        return '%i%%' % (self.rating * 20)

    def a(self, rating):
        try:
            rating_url = self.get_rating_url(rating)
            u = util.make_link_attributes(rating_url, "star%i" % rating,
                title = "%i stars out of 5" % rating,
                onclick="return ajaxLink('%s', 'star-rating')" % rating_url)
            print u
            return u
        except:
            import traceback
            traceback.print_exc()

    def a1(self): return self.a(1)
    def a2(self): return self.a(2)
    def a3(self): return self.a(3)
    def a4(self): return self.a(4)
    def a5(self): return self.a(5)
