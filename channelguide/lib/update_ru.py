#!/usr/bin/env python
# -*- coding: utf-8 -*-

from update import IPTree
from iso3166_2_ru import cc2name
import codecs, logging, os, sys
from urllib2 import urlopen
from cStringIO import StringIO
from zipfile import ZipFile

logger = logging.getLogger(__name__)


class RussiaRegionByIP(IPTree):

    value_length = 3
    url = 'http://ipgeobase.ru/files/db/Main/db_files.zip'
    
    def fetch(self):
        logger.info('Fetching from %r', self.url)
        zip_content = urlopen(self.url).read()
        zip = ZipFile(StringIO(zip_content))
        data = zip.read('cidr_ru_block.txt')
        zip.close()
        self.parse(StringIO(data))

    def parse(self, file):
        if isinstance(file, basestring):
            file = open(file, 'rb')
        fp = codecs.getreader('windows-1251')(file)
        region2code = dict((name, code) for code, name in cc2name.items())
        prev_start = 0
        prev_end = 0
        for line in fp:
            parts = line.strip().split('\t')
            # start, end, ip_range, cc, city, region, area, status, address
            assert parts[0]>=prev_start, ((prev_start, prev_end), (parts[0], parts[1]))
            #assert parts[0]>prev_end or parts[1]<=prev_end, ((prev_start, prev_end), (parts[0], parts[1]))
            prev_start = parts[0]
            prev_end = parts[1]
            first, last = parts[2].split(' - ')
            if parts[5] in [u'Иностранные блоки']:
                continue
            try:
                code = region2code[parts[5]]
            except KeyError:
                print parts[5], parts[7]
                break
            self.add(first, last, code)


if __name__=='__main__':
    logging.basicConfig(level=logging.INFO)
    tree = RussiaRegionByIP()
    tree.fetch()
    tree.optimize()
    db_file = os.path.join(os.path.dirname(sys.argv[0]), 'ip2ru.db')
    db = open(db_file+'.new', 'wb')
    db.write(tree.dump())
    db.close()
    os.rename(db_file+'.new', db_file)
