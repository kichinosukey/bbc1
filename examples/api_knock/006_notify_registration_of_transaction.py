from bbc1.core import bbclib
from bbc1.core import bbc_app
from bbc1.core.message_key_types import KeyType
from bbc1.core.bbc_error import *

user_id = bbclib.get_new_id("user_id for testing", include_timestamp=False)
domain_id = bbclib.get_new_id("domain_id for testing", include_timestamp=False)
asset_group_id = bbclib.get_new_id("asset_group_id for testing", include_timestamp=False)

keypair = bbclib.KeyPair()
keypair.generate()

def setup_client(user_id=None, domain_id=None, keypair=None, multiq=False):
    client = bbc_app.BBcAppClient(multiq=multiq)
    client.set_domain_id(domain_id)
    client.set_user_id(user_id)
    client.set_keypair(keypair)
    client.register_to_core()
    return client

def make_transaction(user_id=None, domain_id=None, asset_group_id=None, keypair=None):
    txobj = bbclib.make_transaction(relation_num=1, witness=True)
    bbclib.add_relation_asset(txobj, relation_idx=0,
                            asset_group_id=asset_group_id, user_id=user_id,
                            asset_body=b'test body', asset_file=b'test file')
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
    list_of_asset_gropu_ids = dat[KeyType.asset_group_ids]
    txid = dat[KeyType.transaction_id]
    print("Inserted transaction %s with asset_groups %s" % (txid.hex(), [asgid.hex() for asgid in list_of_asset_gropu_ids]))

def main():
    # register callback method
    client = setup_client(user_id=user_id, domain_id=domain_id, keypair=keypair, multiq=True)
    client.callback.proc_notify_inserted = proc_notify_inserted
    query_id = client.request_insert_completion_notification(asset_group_id)

    # register transaction to core node
    client = setup_client(user_id=user_id, domain_id=domain_id, keypair=keypair, multiq=True)
    txobj = make_transaction(user_id=user_id, domain_id=domain_id, asset_group_id=asset_group_id, keypair=keypair)
    response_data = register_txobj(txobj=txobj, client=client)

if __name__ == "__main__":
    main()