## taken from http://ppa.sourceforge.net/#ip2cc
#!/usr/bin/env python
# $Id: ip2cc.py,v 1.4 2005/02/19 17:19:26 ods Exp $
__version__ = '0.3'

import re, struct


is_IP = re.compile('^%s$' % r'\.'.join([r'(?:(?:2[0-4]|1\d|[1-9])?\d|25[0-5])']*4)).match


class CountryByIP:

    def __init__(self, filename):
        self.fp = open(filename, 'rb')

    def __getitem__(self, ip):
        offset = 0
        fp = self.fp
        for part in ip.split('.'):
            start = offset+int(part)*4
            fp.seek(start)
            value = fp.read(4)
            assert len(value)==4
            if value[:2]=='\xFF\xFF':
                if value[2:]=='\x00\x00':
                    raise KeyError(ip)
                else:
                    return value[2:]
            offset = struct.unpack('!I', value)[0]
        raise RuntimeError('ip2cc database is briken') # must never reach here

    
# ISO 3166-1 A2 codes (latest change: Wednesday 10 October 2003)
cc2name = {
    'AD': 'ANDORRA',
    'AE': 'UNITED ARAB EMIRATES',
    'AF': 'AFGHANISTAN',
    'AG': 'ANTIGUA AND BARBUDA',
    'AI': 'ANGUILLA',
    'AL': 'ALBANIA',
    'AM': 'ARMENIA',
    'AN': 'NETHERLANDS ANTILLES',
    'AO': 'ANGOLA',
    'AQ': 'ANTARCTICA',
    'AR': 'ARGENTINA',
    'AS': 'AMERICAN SAMOA',
    'AT': 'AUSTRIA',
    'AU': 'AUSTRALIA',
    'AW': 'ARUBA',
    'AZ': 'AZERBAIJAN',
    'BA': 'BOSNIA AND HERZEGOVINA',
    'BB': 'BARBADOS',
    'BD': 'BANGLADESH',
    'BE': 'BELGIUM',
    'BF': 'BURKINA FASO',
    'BG': 'BULGARIA',
    'BH': 'BAHRAIN',
    'BI': 'BURUNDI',
    'BJ': 'BENIN',
    'BM': 'BERMUDA',
    'BN': 'BRUNEI DARUSSALAM',
    'BO': 'BOLIVIA',
    'BR': 'BRAZIL',
    'BS': 'BAHAMAS',
    'BT': 'BHUTAN',
    'BV': 'BOUVET ISLAND',
    'BW': 'BOTSWANA',
    'BY': 'BELARUS',
    'BZ': 'BELIZE',
    'CA': 'CANADA',
    'CC': 'COCOS (KEELING) ISLANDS',
    'CD': 'CONGO, THE DEMOCRATIC REPUBLIC OF THE',
    'CF': 'CENTRAL AFRICAN REPUBLIC',
    'CG': 'CONGO',
    'CH': 'SWITZERLAND',
    'CI': "COTE D'IVOIRE",
    'CK': 'COOK ISLANDS',
    'CL': 'CHILE',
    'CM': 'CAMEROON',
    'CN': 'CHINA',
    'CO': 'COLOMBIA',
    'CR': 'COSTA RICA',
    'CS': 'SERBIA AND MONTENEGRO',
    'CU': 'CUBA',
    'CV': 'CAPE VERDE',
    'CX': 'CHRISTMAS ISLAND',
    'CY': 'CYPRUS',
    'CZ': 'CZECH REPUBLIC',
    'DE': 'GERMANY',
    'DJ': 'DJIBOUTI',
    'DK': 'DENMARK',
    'DM': 'DOMINICA',
    'DO': 'DOMINICAN REPUBLIC',
    'DZ': 'ALGERIA',
    'EC': 'ECUADOR',
    'EE': 'ESTONIA',
    'EG': 'EGYPT',
    'EH': 'WESTERN SAHARA',
    'ER': 'ERITREA',
    'ES': 'SPAIN',
    'ET': 'ETHIOPIA',
    'FI': 'FINLAND',
    'FJ': 'FIJI',
    'FK': 'FALKLAND ISLANDS (MALVINAS)',
    'FM': 'MICRONESIA, FEDERATED STATES OF',
    'FO': 'FAROE ISLANDS',
    'FR': 'FRANCE',
    'GA': 'GABON',
    'GB': 'UNITED KINGDOM',
    'GD': 'GRENADA',
    'GE': 'GEORGIA',
    'GF': 'FRENCH GUIANA',
    'GH': 'GHANA',
    'GI': 'GIBRALTAR',
    'GL': 'GREENLAND',
    'GM': 'GAMBIA',
    'GN': 'GUINEA',
    'GP': 'GUADELOUPE',
    'GQ': 'EQUATORIAL GUINEA',
    'GR': 'GREECE',
    'GS': 'SOUTH GEORGIA AND THE SOUTH SANDWICH ISLANDS',
    'GT': 'GUATEMALA',
    'GU': 'GUAM',
    'GW': 'GUINEA-BISSAU',
    'GY': 'GUYANA',
    'HK': 'HONG KONG',
    'HM': 'HEARD ISLAND AND MCDONALD ISLANDS',
    'HN': 'HONDURAS',
    'HR': 'CROATIA',
    'HT': 'HAITI',
    'HU': 'HUNGARY',
    'ID': 'INDONESIA',
    'IE': 'IRELAND',
    'IL': 'ISRAEL',
    'IN': 'INDIA',
    'IO': 'BRITISH INDIAN OCEAN TERRITORY',
    'IQ': 'IRAQ',
    'IR': 'IRAN, ISLAMIC REPUBLIC OF',
    'IS': 'ICELAND',
    'IT': 'ITALY',
    'JM': 'JAMAICA',
    'JO': 'JORDAN',
    'JP': 'JAPAN',
    'KE': 'KENYA',
    'KG': 'KYRGYZSTAN',
    'KH': 'CAMBODIA',
    'KI': 'KIRIBATI',
    'KM': 'COMOROS',
    'KN': 'SAINT KITTS AND NEVIS',
    'KP': "KOREA, DEMOCRATIC PEOPLE'S REPUBLIC OF",
    'KR': 'KOREA, REPUBLIC OF',
    'KW': 'KUWAIT',
    'KY': 'CAYMAN ISLANDS',
    'KZ': 'KAZAKHSTAN',
    'LA': "LAO PEOPLE'S DEMOCRATIC REPUBLIC",
    'LB': 'LEBANON',
    'LC': 'SAINT LUCIA',
    'LI': 'LIECHTENSTEIN',
    'LK': 'SRI LANKA',
    'LR': 'LIBERIA',
    'LS': 'LESOTHO',
    'LT': 'LITHUANIA',
    'LU': 'LUXEMBOURG',
    'LV': 'LATVIA',
    'LY': 'LIBYAN ARAB JAMAHIRIYA',
    'MA': 'MOROCCO',
    'MC': 'MONACO',
    'MD': 'MOLDOVA, REPUBLIC OF',
    'MG': 'MADAGASCAR',
    'MH': 'MARSHALL ISLANDS',
    'MK': 'MACEDONIA, THE FORMER YUGOSLAV REPUBLIC OF',
    'ML': 'MALI',
    'MM': 'MYANMAR',
    'MN': 'MONGOLIA',
    'MO': 'MACAO',
    'MP': 'NORTHERN MARIANA ISLANDS',
    'MQ': 'MARTINIQUE',
    'MR': 'MAURITANIA',
    'MS': 'MONTSERRAT',
    'MT': 'MALTA',
    'MU': 'MAURITIUS',
    'MV': 'MALDIVES',
    'MW': 'MALAWI',
    'MX': 'MEXICO',
    'MY': 'MALAYSIA',
    'MZ': 'MOZAMBIQUE',
    'NA': 'NAMIBIA',
    'NC': 'NEW CALEDONIA',
    'NE': 'NIGER',
    'NF': 'NORFOLK ISLAND',
    'NG': 'NIGERIA',
    'NI': 'NICARAGUA',
    'NL': 'NETHERLANDS',
    'NO': 'NORWAY',
    'NP': 'NEPAL',
    'NR': 'NAURU',
    'NU': 'NIUE',
    'NZ': 'NEW ZEALAND',
    'OM': 'OMAN',
    'PA': 'PANAMA',
    'PE': 'PERU',
    'PF': 'FRENCH POLYNESIA',
    'PG': 'PAPUA NEW GUINEA',
    'PH': 'PHILIPPINES',
    'PK': 'PAKISTAN',
    'PL': 'POLAND',
    'PM': 'SAINT PIERRE AND MIQUELON',
    'PN': 'PITCAIRN',
    'PR': 'PUERTO RICO',
    'PS': 'PALESTINIAN TERRITORY, OCCUPIED',
    'PT': 'PORTUGAL',
    'PW': 'PALAU',
    'PY': 'PARAGUAY',
    'QA': 'QATAR',
    'RE': 'REUNION',
    'RO': 'ROMANIA',
    'RU': 'RUSSIAN FEDERATION',
    'RW': 'RWANDA',
    'SA': 'SAUDI ARABIA',
    'SB': 'SOLOMON ISLANDS',
    'SC': 'SEYCHELLES',
    'SD': 'SUDAN',
    'SE': 'SWEDEN',
    'SG': 'SINGAPORE',
    'SH': 'SAINT HELENA',
    'SI': 'SLOVENIA',
    'SJ': 'SVALBARD AND JAN MAYEN',
    'SK': 'SLOVAKIA',
    'SL': 'SIERRA LEONE',
    'SM': 'SAN MARINO',
    'SN': 'SENEGAL',
    'SO': 'SOMALIA',
    'SR': 'SURINAME',
    'ST': 'SAO TOME AND PRINCIPE',
    'SV': 'EL SALVADOR',
    'SY': 'SYRIAN ARAB REPUBLIC',
    'SZ': 'SWAZILAND',
    'TC': 'TURKS AND CAICOS ISLANDS',
    'TD': 'CHAD',
    'TF': 'FRENCH SOUTHERN TERRITORIES',
    'TG': 'TOGO',
    'TH': 'THAILAND',
    'TJ': 'TAJIKISTAN',
    'TK': 'TOKELAU',
    'TL': 'TIMOR-LESTE',
    'TM': 'TURKMENISTAN',
    'TN': 'TUNISIA',
    'TO': 'TONGA',
    'TR': 'TURKEY',
    'TT': 'TRINIDAD AND TOBAGO',
    'TV': 'TUVALU',
    'TW': 'TAIWAN, PROVINCE OF CHINA',
    'TZ': 'TANZANIA, UNITED REPUBLIC OF',
    'UA': 'UKRAINE',
    'UG': 'UGANDA',
    'UM': 'UNITED STATES MINOR OUTLYING ISLANDS',
    'US': 'UNITED STATES',
    'UY': 'URUGUAY',
    'UZ': 'UZBEKISTAN',
    'VA': 'HOLY SEE (VATICAN CITY STATE)',
    'VC': 'SAINT VINCENT AND THE GRENADINES',
    'VE': 'VENEZUELA',
    'VG': 'VIRGIN ISLANDS, BRITISH',
    'VI': 'VIRGIN ISLANDS, U.S.',
    'VN': 'VIET NAM',
    'VU': 'VANUATU',
    'WF': 'WALLIS AND FUTUNA',
    'WS': 'SAMOA',
    'YE': 'YEMEN',
    'YT': 'MAYOTTE',
    'ZA': 'SOUTH AFRICA',
    'ZM': 'ZAMBIA',
    'ZW': 'ZIMBABWE'
}

# Additional codes used by registrars
cc2name.update({
    'UK': cc2name['GB'],
    'EU': 'EUROPEAN UNION',
    'AP': 'ASSIGNED PORTABLE',
    'YU': 'FORMER YUGOSLAVIA',
})


if __name__=='__main__':
    import sys, os
    db_file = os.path.splitext(sys.argv[0])[0]+'.db'
    if os.environ.get('REQUEST_URI'):
        import cgi
        form = cgi.FieldStorage()
        try:
            addr = form['addr'].value
        except (KeyError, AttributeError):
            addr = ''
        msg = ''

        if addr:
            if not is_IP(addr):
                msg = '%s is not valid IP address' % cgi.escape(addr)
            else:
                db = CountryByIP(db_file)
                try:
                    cc = db[addr]
                except KeyError:
                    msg = 'Information for %s not found' % cgi.escape(addr)
                else:
                    msg = '%s is located in %s' % (cgi.escape(addr),
                                                   cc2name.get(cc, cc))
        script_name = os.environ['SCRIPT_NAME']
        print '''\
Content-Type: text/html

<html>
<head><title>Country By IP</title></head>
<body>
<h1>Country By IP</h1>
<form action="%(script_name)s">
<input type="text" name="addr" value="%(addr)s">
</form>
%(msg)s
<hr>
<a href="http://ppa.sf.net/#ip2cc">ip2cc %(__version__)s</a>
</body>
</html>''' % vars()

    elif len(sys.argv)==2:
        addr = sys.argv[1]
        if is_IP(addr):
            ip = addr_str = addr
        else:
            from socket import gethostbyname, gaierror
            try:
                ip = gethostbyname(addr)
            except gaierror, exc:
                sys.exit(exc)
            else:
                addr_str = '%s (%s)' % (addr, ip)
        try:
            db = CountryByIP(db_file)
        except IOError, exc:
            import errno
            if exc.errno==errno.ENOENT:
                sys.exit('Database not found. Run update.py to create it.')
            else:
                sys.exit('Cannot open database: %s' % exc)
        try:
            cc = db[ip]
        except KeyError:
            sys.exit('Information for %s not found' % addr)
        else:
            print '%s is located in %s' % (addr_str, cc2name.get(cc, cc))
    else:
        sys.exit('Usage:\n\t%s <address>' % sys.argv[0])
