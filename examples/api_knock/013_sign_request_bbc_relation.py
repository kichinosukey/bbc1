import sys
import time
import binascii

from bbc1.core import bbclib
from bbc1.core import bbc_app
from bbc1.core.message_key_types import KeyType
from bbc1.core.bbclib import MsgType
from bbc1.core.bbc_error import *

user_id1 = bbclib.get_new_id("user_id1 for testing", include_timestamp=False)
user_id2 = bbclib.get_new_id("user_id2 for testing", include_timestamp=False) # as approver
user_id3 = bbclib.get_new_id("user_id3 for testing", include_timestamp=False) # as approver
domain_id = bbclib.get_new_id("domain_id for testing", include_timestamp=False)
asset_group_id = bbclib.get_new_id("asset_group_id for testing", include_timestamp=False)

def create_keypair():
    keypair = bbclib.KeyPair()
    keypair.generate()
    return keypair

def setup_client(client=None, user_id=None, domain_id=None, callback_obj=None, keypair=None, multiq=True, multicast=False):
    if client is None:
        client = bbc_app.BBcAppClient(multiq=multiq)
        client.set_domain_id(domain_id)
    client.set_user_id(user_id)
    client.set_keypair(keypair)
    if callback_obj is not None:
        client.set_callback(callback_obj)
    client.register_to_core(on_multiple_nodes=multicast)
    return client

def register_txobj(txobj=None, client=None):
    ret = client.insert_transaction(txobj)
    assert ret
    query_id = client.search_transaction(txobj.transaction_id)
    response_data = client.callback.sync_by_queryid(query_id)
    if response_data[KeyType.status] < ESUCCESS:
        print("ERROR: ", response_data[KeyType.reason].decode())
        assert False
    return response_data

class MessageProcessor(bbc_app.Callback):
    def __init__(self):
        super(MessageProcessor, self).__init__(self)

    def proc_cmd_sign_request(self, dat):
        dst_user_id = dat[KeyType.source_user_id]
        query_id = dat[KeyType.query_id]
        transaction_data = dat[KeyType.transaction_data]
        if KeyType.transaction_data not in dat:
            print("Invalid message")
            self.client.sendback_denial_of_sign(dest_user_id=dst_user_id,
                                            transaction_id=transaction_id, reason_text="Invalid request",
                                            query_id=query_id)
            return None
        txobj_received, fmt_type = bbclib.deserialize(dat[KeyType.transaction_data])
        sig = txobj_received.sign(keypair=self.client.keypair)
        self.client.sendback_signature(dest_user_id=dst_user_id, 
            transaction_id=txobj_received.transaction_id, signature=sig, query_id=query_id)

def main_01():
    keypair = create_keypair()
    user_id = user_id1
    destinations = [user_id2]

    client = setup_client(user_id=user_id, domain_id=domain_id, 
                callback_obj=MessageProcessor(), keypair=keypair, multiq=True)
    txobj = bbclib.make_transaction(relation_num=1, witness=True)
    bbclib.add_relation_asset(txobj, relation_idx=0,
                            user_id=user_id, asset_group_id=asset_group_id,
                            asset_body=b"test body", asset_file=b"test file")
    txobj.witness.add_witness(user_id)
    txobj.witness.add_witness(user_id2)
    txobj.digest()
    
    asset_files = {}
    asset_files[txobj.relations[0].asset.asset_id] = txobj.relations[0].asset.asset_file
    query_id = client.gather_signatures(txobj, asset_files=asset_files, destinations=destinations)
    
    recv_msg = client.callback.sync_by_queryid(query_id, no_delete_q=True)
    if recv_msg[KeyType.status] < ESUCCESS:
        print("Error", recv_msg[KeyType.reason].decode())
        assert False

    sig_received = bbclib.BBcSignature()
    sig_received.unpack(recv_msg[KeyType.signature])
    txobj.witness.add_signature(user_id=destinations[0], signature=sig_received)
    sig = txobj.sign(keypair=keypair)
    txobj.witness.add_signature(user_id=user_id, signature=sig)
    
    register_txobj(txobj=txobj, client=client)

def main_02(user_id):
    keypair = create_keypair()
    client = setup_client(user_id=user_id, domain_id=domain_id, keypair=keypair, 
                    callback_obj=MessageProcessor(), multiq=True)


if __name__ == "__main__":
    args = sys.argv
    if args[1] == "user1":
        main_01()
    if args[1] == "user2":
        main_02(user_id2)
    if args[1] == "user3":
        main_02(user_id3)
    time.sleep(10)