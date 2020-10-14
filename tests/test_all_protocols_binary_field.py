from __future__ import absolute_import

import time
import traceback
from multiprocessing import Process

import pytest

import thriftpy2
from tests.test_apache_json import recursive_vars
from thriftpy2._compat import PYPY
from thriftpy2.http import make_server as make_http_server, \
    make_client as make_http_client
from thriftpy2.protocol import (
    TApacheJSONProtocolFactory,
    TJSONProtocolFactory,
    TCompactProtocolFactory,
    TMultiplexedProtocolFactory
)
from thriftpy2.protocol.binary import TBinaryProtocolFactory
from thriftpy2.protocol.cybin import TCyBinaryProtocolFactory
from thriftpy2.rpc import make_server as make_rpc_server, \
    make_client as make_rpc_client
from thriftpy2.transport.buffered import TBufferedTransportFactory

protocols = [TApacheJSONProtocolFactory,
             TJSONProtocolFactory,
             TBinaryProtocolFactory,
             # TMultiplexedProtocolFactory,
             TCompactProtocolFactory]

if not PYPY:
    protocols.append(TCyBinaryProtocolFactory)


@pytest.mark.parametrize('server_func',
                         [(make_rpc_server, make_rpc_client),
                          (make_http_server, make_http_client)])
@pytest.mark.parametrize('tlist', [[], ['a', 'b', 'c']])
@pytest.mark.parametrize('binary', [b'', b'\x01\x03test binary\x03\xff'])
@pytest.mark.parametrize('proto_factory', protocols)
def test_protocols(proto_factory, binary, tlist, server_func):
    test_thrift = thriftpy2.load(
        "apache_json_test.thrift",
        module_name="test_thrift"
    )
    Foo = test_thrift.Foo

    class Handler:
        @staticmethod
        def test(t):
            return t

    trans_factory = TBufferedTransportFactory

    def run_server():
        server = server_func[0](
            test_thrift.TestService,
            handler=Handler(),
            host='localhost',
            port=9090,
            proto_factory=proto_factory(),
            trans_factory=trans_factory(),
        )
        server.serve()

    proc = Process(target=run_server)
    proc.start()
    time.sleep(0.1)
    err = None
    try:
        test_object = test_thrift.Test(
            tdouble=12.3456,
            tint=567,
            tstr='A test \'{["string',
            tbinary=binary,
            tlist_of_strings=tlist,
            tbool=False,
            tbyte=16,
            tlong=123123123,
            tshort=123,
            tsetofints={1, 2, 3, 4, 5},
            tmap_of_int2str={
                1: "one",
                2: "two",
                3: "three"
            },
            tmap_of_str2foo={'first': Foo("first"), "2nd": Foo("baz")},
            tmap_of_str2foolist={
                'test': [Foo("test list entry")]
            },
            tmap_of_str2mapofstring2foo={
                "first": {
                    "second": Foo("testing")
                }
            },
            tmap_of_str2stringlist={
                "words": ["dog", "cat", "pie"],
                "other": ["test", "foo", "bar", "baz", "quux"]
            },
            tfoo=Foo("test food"),
            tlist_of_foo=[Foo("1"), Foo("2"), Foo("3")],
            tlist_of_maps2int=[
                {"one": 1, "two": 2, "three": 3}
            ],
            tmap_of_int2foo={
                1: Foo("One"),
                2: Foo("Two"),
                5: Foo("Five")
            },
        )

        client = server_func[1](
            test_thrift.TestService,
            host='localhost',
            port=9090,
            proto_factory=proto_factory(),
            trans_factory=trans_factory(),
        )
        res = client.test(test_object)
        assert recursive_vars(res) == recursive_vars(test_object)
    except Exception as e:
        err = e
    finally:
        proc.terminate()
    if err:
        traceback.format_exc()
        raise err
