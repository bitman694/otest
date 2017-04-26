from otest.aus.preproc import PMAP
from otest.prof_util import CRYPTO, EMAP, EXTRAS

PMAPL = list(PMAP.keys())
PMAPL.sort()

L2I = {"discovery": 1, "registration": 2}
LONG_NAMES = {"none": "none", "sig": "signing", "enc": "encryption"}

RADIO = '<input type="radio" name="{}" value="{}">{}<br>'
RADIO_C = '<input type="radio" name="{}" value="{}" checked>{}<br>'
CHECK = '<input type="checkbox" name="{}">{}<br>'
CHECK_C = '<input type="checkbox" name="{}" checked>{}<br>'

def profile_form(prof):
    p = prof.split(".")
    el = []
    for key in PMAPL:
        txt = PMAP[key]
        if key == p[0]:
            el.append(RADIO_C.format('return_type', key, txt))
        else:
            el.append(RADIO.format('return_type', key, txt))
    el.append("<br>")
    el.append("These you can't change here:")
    el.append("<ul>")
    for mode in ["discovery", "registration"]:
        if p[L2I[mode]] == "T":
            el.append("<li>Dynamic %s" % mode)
        else:
            el.append("<li>Static %s" % mode)
    el.append("</ul><p>Cryptographic support:<br>")
    if len(p) > CRYPTO:
        vs = p[CRYPTO]
    else:
        vs = ''

    for code, attr in EMAP.items():
        if code in vs:
            el.append(CHECK_C.format(attr, LONG_NAMES[attr]))
        else:
            el.append(CHECK.format(attr, LONG_NAMES[attr]))
    el.append("</p>")

    el.append(
        '</ul><p>Check this if you want extra tests (not needed for any '
        'certification profiles): ')
    if len(p) > EXTRAS and p[EXTRAS] == "+":
        el.append(CHECK_C.format('extra',''))
    else:
        el.append(CHECK.format('extra',''))
    el.append('</p>')
    return "\n".join(el)