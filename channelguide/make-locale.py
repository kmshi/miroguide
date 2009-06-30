#!/usr/bin/env python
import os
import tarfile

poMapping = {
    'django.po': 'miro-guide',
    'djangojs.po': 'javascript',
}

localeDir = os.path.join(os.path.dirname(__file__), 'guide', 'locale')
languages = os.listdir(localeDir)

tempTGZFile = file('/tmp/miro-guide-po.tgz', 'wb')
tempTGZ = tarfile.open(tempTGZFile.name, 'w|gz')

tarInfo = tarfile.TarInfo()
tarInfo.name = 'po'
tarInfo.type = tarfile.DIRTYPE
tempTGZ.addfile(tarInfo)

for dirName in poMapping.values():
    tarInfo.name = 'po/%s' % dirName
    tempTGZ.addfile(tarInfo)

for language in languages:
    languageDir = os.path.join(localeDir, language, 'LC_MESSAGES')
    for name in os.listdir(languageDir):
        if name in poMapping:
            dataFile = file(os.path.join(languageDir, name))
            dataStat = os.stat(dataFile.name)
            tarInfo.name = 'po/%s/%s.po' % (poMapping[name],
                                            language)
            tarInfo.type = tarfile.REGTYPE
            tarInfo.mtime = dataStat.st_mtime
            tarInfo.size = dataStat.st_size
            tempTGZ.addfile(tarInfo, dataFile)
            if language == 'en': # use english as the template
                tarInfo.name = 'po/%s/%st' % (poMapping[name],
                                              name)
                dataFile.seek(0)
                tempTGZ.addfile(tarInfo, dataFile)
            dataFile.close()
tempTGZ.close()
tempTGZFile.close()

print 'wrote translations file to /tmp/miro-guide-po.tgz'
