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

def setup_client(user_id=None, domain_id=None, keypair=None, multiq=False, callback_obj=None):
    client = bbc_app.BBcAppClient(multiq=multiq)
    client.set_user_id(user_id)
    client.set_domain_id(domain_id)
    client.set_keypair(keypair)
    if callback_obj is not None:
        client.set_callback(callback_obj)
    client.register_to_core()
    return client

def make_transaction(user_id=None, asset_group_id=None, keypair=None):
    txobj = bbclib.make_transaction(relation_num=1, witness=True)
    bbclib.add_relation_asset(txobj, relation_idx=0, 
                            asset_group_id=asset_group_id, user_id=user_id,
                            asset_body=b"asset_body", asset_file=b"asset_file")
    txobj.witness.add_witness(user_id)
    sig = txobj.sign(private_key=keypair.private_key, public_key=keypair.public_key)
    txobj.witness.add_signature(user_id=user_id, signature=sig)
    return txobj

def register_txobj(txobj=None, client=None):
    ret = client.insert_transaction(txobj)
    assert ret

    query_id = client.search_transaction(txobj.transaction_id)
    response_data = client.callback.sync_by_queryid(query_id)
    if response_data[KeyType.status] < ESUCCESS:
        print("ERROR: ", response_data[KeyType.reason].decode())
        assert False
    return response_data

def proc_notify_inserted(dat):
    list_of_asset_group_ids = dat[KeyType.asset_group_ids]
    txid = dat[KeyType.transaction_id]
    print("Inserted transaction %s with asset groups %s" % (txid.hex(), [asgid.hex() for asgid in list_of_asset_group_ids]))

def register_method_of_notify(client=None, asset_group_id=None):
    client.callback.proc_notify_inserted = proc_notify_inserted
    client.request_insert_completion_notification(asset_group_id)

class MessageProcessor(bbc_app.Callback):
    def __init__(self):
        super(MessageProcessor, self).__init__(self)
    
    def proc_user_message(self, dat):
        user_message = dat[KeyType.message]
        print("Received user message: %s" % user_message)

def main():
    # for user1
    keypair = create_keypair()
    client = setup_client(user_id=user_id1, domain_id=domain_id, keypair=keypair, multiq=True)
    register_method_of_notify(client=client, asset_group_id=asset_group_id)
    
    client = setup_client(user_id=user_id1, domain_id=domain_id, keypair=keypair, 
                        multiq=True, callback_obj=MessageProcessor())
    txobj = make_transaction(user_id=user_id1, asset_group_id=asset_group_id, keypair=keypair)
    register_txobj(txobj=txobj, client=client)
    message_to_send1 = {"message": "This is a test message"}
    client.send_message(message_to_send1, user_id1)
 
    # for user2
    keypair = create_keypair()
    client = setup_client(user_id=user_id2, domain_id=domain_id, keypair=keypair, multiq=True)
    # register_method_of_notify(client=client, asset_group_id=asset_group_id) # no need to register again
    
    client = setup_client(user_id=user_id2, domain_id=domain_id, keypair=keypair, 
                        multiq=True, callback_obj=MessageProcessor())
    txobj = make_transaction(user_id=user_id2, asset_group_id=asset_group_id, keypair=keypair)
    register_txobj(txobj=txobj, client=client)
 
    message_to_send2 = "Test message No.2"
    client.send_message(message_to_send2, user_id2)

    import time
    time.sleep(2)

if __name__ == "__main__":
    main()