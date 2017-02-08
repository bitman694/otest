from otest.aus.preproc import PMAP


def op_choice(base, flows):
    """
    Creates a list of test flows
    """
    _grp = "_"
    color = ['<img src="/static/black.png" alt="Black">',  # INFORMATION
             '<img src="/static/green.png" alt="Green">',  # OK
             '<img src="/static/yellow.png" alt="Yellow">',  # WARNING
             '<img src="/static/red.png" alt="Red">',  # ERROR
             '<img src="/static/red.png" alt="Red">',  # CRITICAL
             '<img src="/static/qmark.jpg" alt="QuestionMark">',  # INTERACTION
             '<img src="/static/qmark.jpg" alt="QuestionMark">',  # INCOMPLETE
             '<img src="/static/greybutton" alt="Grey">',  # NOT_APPLICABLE
             ]
    line = [
        '<table>',
        '<tr><th>Status</th><th>Description</th><th>Info</th></tr>']

    for grp, state, desc, tid in flows:
        b = tid.split("-", 2)[1]
        if not grp == _grp:
            _grp = grp
            _item = '<td colspan="3" class="center"><b>{}</b></td>'.format(_grp)
            line.append(
                '<tr id="{}">{}</tr>'.format(b, _item))

        if state:
            _info = "<a href='{}test_info/{}'><img " \
                    "src='/static/info32.png'></a>".format(
                base, tid)
        else:
            _info = ''

        _stat = "<a href='{}{}'>{}</a>".format(base, tid, color[state])
        line.append(
            '<tr><td>{}</td><td>{} ({})</td><td>{}</td></tr>'.format(
                _stat, desc, tid, _info))
    line.append('</table>')

    return "\n".join(line)


ICONS = [
    ('<img src="/static/black.png" alt="Black">', "The test has not be run"),
    ('<img src="/static/green.png" alt="Green">', "Success"),
    ('<img src="/static/yellow.png" alt="Yellow">',
     "Warning, something was not as expected"),
    ('<img src="/static/red.png" alt="Red">', "Failed"),
    ('<img src="/static/qmark.jpg" alt="QuestionMark">',
     "The test flow wasn't completed. This may have been expected or not"),
    ('<img src="/static/info32.png">',
     "Signals the fact that there are trace information available for the "
     "test"),
]


def legends():
    element = ["<table border='1' id='legends'>"]
    for icon, txt in ICONS:
        element.append("<tr><td>%s</td><td>%s</td></tr>" % (icon, txt))
    element.append('</table>')
    return "\n".join(element)


L2I = {"webfinger": 1, "discovery": 2, "registration": 3}
CM = {"n": "none", "s": "sign", "e": "encrypt"}


def display_profile(spec):
    el = ["<p><ul>"]
    p = spec.split('.')
    el.append("<li> %s" % PMAP[p[0]])
    for mode in ["webfinger", "discovery", "registration"]:
        if p[L2I[mode]] == "T":
            el.append("<li> Dynamic %s" % mode)
        else:
            el.append("<li> Static %s" % mode)
    if len(p) > 4:
        if p[4]:
            el.append("<li> crypto support %s" % [CM[x] for x in p[4]])
    if len(p) == 6:
        if p[5] == '+':
            el.append("<li> extra tests")
    el.append("</ul></p>")

    return "\n".join(el)
