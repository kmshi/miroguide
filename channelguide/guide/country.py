import os.path
import ip2cc

def country_code(request):
    ip = request.META.get('REMOTE_ADDR')
    if ip == '127.0.0.1':
        ip = request.META.get('HTTP_X_FORWARDED_FOR')
    if not ip:
        return
    try:
        return CountryDict[ip]
    except KeyError:
        return

CountryDict = ip2cc.CountryByIP(os.path.join(
    os.path.dirname(ip2cc.__file__), 'ip2cc', 'ip2cc.db'))
