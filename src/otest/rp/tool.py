import logging
import os

from aatest import exception_trace, ConfigurationError, ConditionError
from aatest import tool
from aatest.check import OK
from aatest.check import State
from aatest.events import EV_CONDITION, EV_REQUEST, EV_PROTOCOL_REQUEST
from aatest.events import EV_RESPONSE
from aatest.result import Result
from aatest.result import safe_path
from aatest.session import Done
from aatest.summation import store_test_state
from aatest.verify import Verify
from future.backports.urllib.parse import parse_qs
from oic.utils.http_util import Redirect
from oic.utils.http_util import Response
from otest.conversation import Conversation

logger = logging.getLogger(__name__)


class WebTester(tool.Tester):
    def __init__(self, *args, **kwargs):
        tool.Tester.__init__(self, *args, **kwargs)
        try:
            self.base_url = self.inut.conf.BASE
        except AttributeError:
            self.base_url = self.kwargs['base']
        self.provider_cls = self.kwargs['provider_cls']
        self.selected = {}

    def fname(self, test_id):
        _pname = '_'.join(self.profile)
        try:
            return safe_path(self.conv.entity_id, _pname, test_id)
        except KeyError:
            return safe_path('dummy', _pname, test_id)

    def match_profile(self, test_id, **kwargs):
        _spec = self.flows[test_id]
        # There must be an intersection between the two profile lists.
        if set(self.profile).intersection(set(_spec["profiles"])):
            return True
        else:
            return False

    def setup(self, test_id, **kw_args):
        if not self.match_profile(test_id):
            return False

        self.sh.session_setup(path=test_id)
        _flow = self.flows[test_id]
        try:
            _cap = kw_args['op_profiles'][self.sh['test_conf']['profile'][0]]
        except KeyError:
            _cap = None
        _ent = self.provider_cls(capabilities=_cap, **kw_args['as_args'])
        _ent.baseurl = os.path.join(_ent.baseurl, kw_args['sid'])
        _ent.jwks_uri = os.path.join(_ent.baseurl,
                                     kw_args['as_args']['jwks_name'])
        _ent.name = _ent.baseurl
        self.conv = Conversation(_flow, _ent,
                                 msg_factory=kw_args["msg_factory"],
                                 trace_cls=self.trace_cls)
        self.conv.sequence = self.sh["sequence"]
        _ent.conv = self.conv
        self.sh["conv"] = self.conv
        return True

    def run(self, test_id, **kw_args):
        if not self.setup(test_id, **kw_args):
            raise ConfigurationError()

        # noinspection PyTypeChecker
        try:
            return self.run_item(test_id, index=0, **kw_args)
        except Exception as err:
            exception_trace("", err, logger)
            return self.inut.err_response("run", err)

    def run_item(self, test_id, index, profiles=None, **kw_args):
        logger.info("<=<=<=<=< %s >=>=>=>=>" % test_id)

        _ss = self.sh
        try:
            _ss["node"].complete = False
        except KeyError:
            pass

        self.conv.test_id = test_id
        res = Result(self.sh, self.kwargs['profile_handler'])

        if index >= len(self.conv.sequence):
            return None

        item = self.conv.sequence[index]

        if isinstance(item, tuple):
            cls, funcs = item
        else:
            cls = item
            funcs = {}

        logger.info("<--<-- {} --- {} -->-->".format(index, cls))
        self.conv.events.store('operation', cls, sender='run_flow')
        try:
            _oper = cls(conv=self.conv, inut=self.inut, sh=self.sh,
                        profile=self.profile, test_id=test_id,
                        funcs=funcs, check_factory=self.chk_factory,
                        cache=self.cache)
            # self.conv.operation = _oper
            if profiles:
                profile_map = profiles.PROFILEMAP
            else:
                profile_map = None
            _oper.setup(profile_map)
            resp = _oper()
        except ConditionError:
            store_test_state(self.sh, self.conv.events)
            res.store_test_info()
            res.print_info(test_id, self.fname(test_id))
            return False
        except Exception as err:
            exception_trace('run_flow', err)
            self.sh["index"] = index
            return self.inut.err_response("run_sequence", err)
        else:
            if isinstance(resp, self.response_cls):
                return resp

            if resp:
                #return self.inut.respond(resp)
                return resp

        # should be done as late as possible, so all processing has been
        # done
        try:
            _oper.post_tests()
        except ConditionError:
            store_test_state(self.sh, self.conv.events)
            res.store_test_info()
            res.print_info(test_id, self.fname(test_id))
            return False

        _ss['index'] = self.conv.index = index + 1

        # try:
        #     if self.conv.flow["assert"]:
        #         _ver = Verify(self.chk_factory, self.conv)
        #         _ver.test_sequence(self.conv.flow["assert"])
        # except KeyError:
        #     pass
        # except Exception as err:
        #     logger.error(err)
        #     raise

        return True

    def display_test_list(self):
        try:
            if self.sh.session_init():
                return self.inut.flow_list()
            else:
                try:
                    resp = Redirect("%s/opresult#%s" % (
                        self.base_url, self.sh["testid"][0]))
                except KeyError:
                    return self.inut.flow_list()
                else:
                    return resp(self.inut.environ, self.inut.start_response)
        except Exception as err:
            exception_trace("display_test_list", err)
            return self.inut.err_response("session_setup", err)

    def handle_request(self, req, path=''):
        self.conv.events.store(EV_REQUEST, req)
        if req:
            func = getattr(self.conv.entity.server,
                           'parse_{}_request'.format(path))

            msg = None
            if req[0] in ['{', '[']:
                msg = func(req, sformat='json')
            else:
                if path in ['authorization', 'check_session']:
                    msg = func(query=req)  # default urlencoded
                elif path in ['token', 'refresh_token']:
                    msg = func(body=req)
                else:
                    msg = func(req)
            if msg:
                self.conv.events.store(EV_PROTOCOL_REQUEST, msg)

    def do_config(self, sid=''):
        resp = Response(mako_template="config.mako",
                        template_lookup=self.kwargs['lookup'], headers=[])

        if sid:
            _url = os.path.join(self.base_url, sid)
        else:
            _url = self.base_url

        kwargs = {
            'start_page': '',
            'params': '',
            'issuer': _url,
            'profiles': self.kwargs['op_profiles'].keys(),
            'selected': self.selected
        }
        return resp(self.inut.environ, self.inut.start_response, **kwargs)

    def do_next(self, req, filename, path='', **kwargs):
        sh = self.sh

        self.conv = sh['conv']
        self.handle_request(req, path)

        store_test_state(sh, sh['conv'].events)
        res = Result(sh, kwargs['profile_handler'])
        res.store_test_info()

        self.conv.index += 1

        try:
            resp = self.run_item(self.conv.test_id, index=self.conv.index,
                                 **kwargs)
        except Exception as err:
            raise

        store_test_state(sh, sh['conv'].events)
        if isinstance(resp, Response):
            res.print_info(path, filename)
            return resp

        _done = False
        for _cond in self.conv.events.get_data(EV_CONDITION):
            if _cond.test_id == 'Done' and _cond.status == OK:
                _done = True
                break

        if not _done:
            self.conv.events.store(EV_CONDITION, State('Done', OK),
                                   sender='do_next')

            if 'assert' in self.conv.flow:
                _ver = Verify(self.chk_factory, self.conv)
                _ver.test_sequence(self.conv.flow["assert"])

            store_test_state(sh, sh['conv'].events)
            res.store_test_info()

        return self.inut.flow_list(filename)

    def get_response(self, resp):
        try:
            loc = resp.headers['location']
        except (AttributeError, KeyError):  # May be a dictionary
            try:
                return resp.response
            except AttributeError:
                try:
                    return resp.text
                except AttributeError:
                    if isinstance(resp, dict):
                        return resp
        else:
            try:
                _resp = dict(
                    [(k, v[0]) for k, v in parse_qs(loc.split('?')[1]).items()])
            except IndexError:
                return loc
            else:
                self.conv.events.store(EV_RESPONSE, _resp)
                return _resp