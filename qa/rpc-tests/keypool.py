#!/usr/bin/env python3
# Copyright (c) 2014-2016 The Bitcoin Core developers
# Distributed under the MIT software license, see the accompanying
# file COPYING or http://www.opensource.org/licenses/mit-license.php.

# Exercise the wallet keypool, and interaction with wallet encryption/locking

from test_framework.test_framework import BitcoinTestFramework
from test_framework.util import *
from test_framework import auxpow

class KeyPoolTest(BitcoinTestFramework):

    def run_test(self):
        nodes = self.nodes
        # Encrypt wallet and wait to terminate
        nodes[0].encryptwallet('test')
        bitcoind_processes[0].wait()
        # Restart node 0
        nodes[0] = start_node(0, self.options.tmpdir)
        # Keep creating keys
        addr = nodes[0].getnewaddress()
        try:
            addr = nodes[0].getnewaddress()
            raise AssertionError('Keypool should be exhausted after one address')
        except JSONRPCException as e:
            assert(e.error['code']==-12)

        # put three new keys in the keypool
        nodes[0].walletpassphrase('test', 12000)
        nodes[0].keypoolrefill(3)
        nodes[0].walletlock()

        # drain the keys
        addr = set()
        addr.add(nodes[0].getrawchangeaddress())
        addr.add(nodes[0].getrawchangeaddress())
        addr.add(nodes[0].getrawchangeaddress())
        addr.add(nodes[0].getrawchangeaddress())
        # assert that four unique addresses were returned
        assert(len(addr) == 4)
        # the next one should fail
        try:
            addr = nodes[0].getrawchangeaddress()
            raise AssertionError('Keypool should be exhausted after three addresses')
        except JSONRPCException as e:
            assert(e.error['code']==-12)

        # refill keypool with three new addresses
        nodes[0].walletpassphrase('test', 1)
        nodes[0].keypoolrefill(3)
        # test walletpassphrase timeout
        time.sleep(1.1)
        assert_equal(nodes[0].getwalletinfo()["unlocked_until"], 0)

        # drain them by mining
        nodes[0].generate(1)
        nodes[0].generate(1)
        nodes[0].generate(1)
        nodes[0].generate(1)
        try:
            nodes[0].generate(1)
            raise AssertionError('Keypool should be exhausted after three addesses')
        except JSONRPCException as e:
            assert(e.error['code']==-12)

        # test draining with getauxblock
        test_auxpow(nodes)

    def __init__(self):
        super().__init__()
        self.setup_clean_chain = False
        self.num_nodes = 1

    def setup_network(self):
        self.nodes = self.setup_nodes()

def test_auxpow(nodes):
    """
    Test behaviour of getauxpow.  Calling getauxpow should reserve
    a key from the pool, but it should be released again if the
    created block is not actually used.  On the other hand, if the
    auxpow is submitted and turned into a block, the keypool should
    be drained.
    """

    nodes[0].walletpassphrase('test', 12000)
    nodes[0].keypoolrefill(1)
    nodes[0].walletlock()
    assert_equal (nodes[0].getwalletinfo()['keypoolsize'], 2)

    nodes[0].getauxblock()
    assert_equal (nodes[0].getwalletinfo()['keypoolsize'], 2)
    nodes[0].generate(1)
    assert_equal (nodes[0].getwalletinfo()['keypoolsize'], 1)
    auxblock = nodes[0].getauxblock()
    assert_equal (nodes[0].getwalletinfo()['keypoolsize'], 1)

    target = auxpow.reverseHex(auxblock['_target'])
    solved = auxpow.computeAuxpow(auxblock['hash'], target, True)
    res = nodes[0].getauxblock(auxblock['hash'], solved)
    assert res
    assert_equal(nodes[0].getwalletinfo()['keypoolsize'], 0)

    try:
        nodes[0].getauxblock()
        raise AssertionError('Keypool should be exhausted by getauxblock')
    except JSONRPCException as e:
        assert(e.error['code']==-12)

if __name__ == '__main__':
    KeyPoolTest().main()
