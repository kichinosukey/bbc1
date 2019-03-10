import sys
import time

from bbc1.core import bbclib
from bbc1.core import bbc_app
from bbc1.core.message_key_types import KeyType
from bbc1.core.bbc_error import *

user_id1 = bbclib.get_new_id("user_id1 for testing", include_timestamp=False)
user_id2 = bbclib.get_new_id("user_id2 for testing", include_timestamp=False)
domain_id = bbclib.get_new_id("domain_id for testing", include_timestamp=False)
asset_group_id = bbclib.get_new_id("asset_group_id for testing", include_timestamp=False)

def create_keypair():
    keypair = bbclib.KeyPair()
    keypair.generate()
    return keypair

def setup_client(user_id=None, domain_id=None, keypair=None, callback_obj=None, multiq=True, multicast=False, client=None):
    if client is None:
        client = bbc_app.BBcAppClient(multiq=multiq)
        client.set_domain_id(domain_id)
        client.set_keypair(keypair)
    client.set_user_id(user_id)
    if callback_obj is not None:
        client.set_callback(callback_obj)
    client.register_to_core(on_multiple_nodes=multicast)
    return client

def make_transaction(user_id=None, asset_group_id=None, keypair=None):
    txobj = bbclib.make_transaction(relation_num=1, witness=True)
    bbclib.add_relation_asset(txobj, relation_idx=0,
                        user_id=user_id, asset_group_id=asset_group_id,
                        asset_body=b"test body", asset_file=b"test asset")
    txobj.witness.add_witness(user_id)
    sig = txobj.sign(private_key=keypair.private_key, public_key=keypair.public_key)
    txobj.witness.add_signature(user_id=user_id, signature=sig)
    return txobj

def register_txobj(txobj=None, client=None):
    ret = client.insert_transaction(txobj)
    assert ret
    query_id = client.search_transaction(txobj.transaction_id)
    response_data = client.callback.sync_queryid(query_id)
    if response_data[KeyType.status] < ESUCCESS:
        print("ERROR: ", response_data[KeyType.reason].decode())
        assert False
    return response_data

class MessageProcessor(bbc_app.Callback):
    def __init__(self):
        super(MessageProcessor, self).__init__(self)
    
    def proc_user_message(self, dat):
        user_message = dat[KeyType.message]
        print("Received user message: %s" % user_message)

def main(user_id=None, anycast_receiver_id_list=None, message=None):
    keypair = create_keypair()
    client = setup_client(user_id=user_id, domain_id=domain_id, keypair=keypair,
                        callback_obj=MessageProcessor(), multiq=True, multicast=False)

    for anycast_receiver_id in anycast_receiver_id_list:
        client.set_user_id(anycast_receiver_id)
        client.register_to_core(on_multiple_nodes=True)
        client.send_message(message, anycast_receiver_id, is_anycast=True)

if __name__ == "__main__":
    args = sys.argv
    if args[1] == "user1":
        main(user_id=user_id1, anycast_receiver_id_list=[user_id2], message=args[2])
    
    elif args[1] == "user2":
        keypair = create_keypair()
        client = setup_client(user_id=user_id2, domain_id=domain_id, keypair=keypair, 
                            callback_obj=MessageProcessor(), multiq=True, multicast=True)
    
    time.sleep(10)
    