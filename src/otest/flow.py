import json
import os
import re
from otest import Unknown
from otest.func import factory as ofactory

PAT = re.compile('\${([A-Z_0-9]*)}')

ABBR = {
    "code": 'C',
    "id_token": 'I',
    "id_token token": 'IT',
    "code id_token": 'CI',
    "code token": 'CT',
    "code id_token token": 'CIT',
    "dynamic": 'DYN',
    "configuration": 'CNF'
}

EXP = dict([(v, k) for k, v in ABBR.items()])

GRPS = [
    "Discovery", "Dynamic Client Registration",
    "Response Type and Response Mode", "claims Request Parameter",
    "request_uri Request Parameter", "scope Request Parameter",
    "nonce Request Parameter", "Client Authentication",
    "ID Token", "Key Rotation", "Claims Types", "UserInfo Endpoint"
]


def replace_with_url(txt, links):
    for m in PAT.findall(txt):
        try:
            _url = links['URL'][m]
        except KeyError:
            pass
        else:
            txt = txt.replace('${%s}' % m, _url)

    return txt


def replace_with_link(txt, links):
    for m in PAT.findall(txt):
        try:
            _url, tag = links['LINK'][m]
        except KeyError:
            pass
        else:
            _li = replace_with_url(_url, links)
            _href = '<a href="{}">{}</a>'.format(_li, tag)
            txt = txt.replace('${%s}' % m, _href)
    return txt


class Flow(object):
    def __init__(self, fdir):
        self.fdir = fdir

    def __getitem__(self, tid):
        """
        Get the flow description given a test ID

        :param tid: The test ID
        :return: A dictionary representation of the description
        """

        fname = os.path.join(self.fdir, tid + '.json')
        fp = open(fname, 'r')
        try:
            _info = json.load(fp)
        except Exception:
            raise KeyError(tid)
        finally:
            fp.close()

        return _info

    def items(self):
        """
        Return all flow descriptions.
        It is assumed that all files with names that has the postfix '.json'
        prepresents flow descriptions.

        :return:
        """
        for fn in os.listdir(self.fdir):
            if fn.endswith('.json'):
                sfn = fn[:-5]
                yield((sfn, self[sfn]))

    def keys(self):
        """
        Return all Test IDs
        :return: list of test IDs
        """
        for fn in os.listdir(self.fdir):
            if fn.endswith('.json'):
                yield(fn[:-5])

    def pick(self, key, value):
        tids = []
        for tid, spec in self.items():
            try:
                _val = spec[key]
            except KeyError:
                pass
            else:
                if value == _val:
                    tids.append(tid)
        return tids

# ==============================================================================


def _get_cls(name, factories, use=''):
    if use:
        try:
            cls = factories[use](name)
        except Unknown:
            pass
        else:
            return cls

    try:
        cls = factories[''](name)
    except Unknown:
        raise Exception("Unknown Class: '{}'".format(name))

    return cls


def _get_func(dic, func_factory):
    """
    Convert function names into function references

    :param dic: A key, value dictionary where keys are function names
    :param func_factory: Factory function used to find functions
    :return: A dictionary with the keys replace with references to functions
    """
    res = {}
    for fname, val in dic.items():
        func = func_factory(fname)
        if func is None:
            func = ofactory(fname)

        if func is None:
            raise Exception("Unknown function: '{}'".format(fname))
        res[func] = val

    return res


class RPFlow(Flow):
    def __init__(self, fdir, cls_factories, func_factory, use=''):
        Flow.__init__(self, fdir)
        self.cls_factories = cls_factories
        self.func_factory = func_factory
        self.use = use

    def expanded_conf(self, tid):
        """

        :param test_id:
        :return:
        """
        spec = self[tid]
        seq = []
        for oper in spec["sequence"]:
            if isinstance(oper, dict):  # Must be only one key, value item
                if len(oper) > 1:
                    raise SyntaxError(tid)
                key, val = list(oper.items())[0]
                try:
                    seq.append((_get_cls(key, self.cls_factories, self.use),
                                _get_func(val, self.func_factory)))
                except Exception:
                    print('tid:{}'.format(tid))
                    raise
            else:
                try:
                    seq.append(_get_cls(oper, self.cls_factories, self.use))
                except Exception:
                    print('tid:{}'.format(tid))
                    raise
        spec["sequence"] = seq

        return spec


def match_usage(spec, **kwargs):
    try:
        _usage = spec['usage']
    except KeyError:
        return True
    else:
        for key, val in kwargs.items():
            try:
                allowed = _usage[key]
            except KeyError:
                continue
            else:
                if val not in allowed:
                    return False
    return True
