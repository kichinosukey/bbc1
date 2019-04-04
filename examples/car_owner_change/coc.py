import argparse
import os
import sys
import datetime
import json
import hashlib
import binascii

from bbc1.core import bbclib
from bbc1.core import bbc_app
from bbc1.core.message_key_types import KeyType
from bbc1.core.bbc_error import *

PRIVATE_KEY = '.private_key'
PUBLIC_KEY = '.public_key'

domain_id = bbclib.get_new_id("car owner change domain", include_timestamp=False)
asset_group_id = bbclib.get_new_id("car owner change asset group", include_timestamp=False)

key_pair = None

def setup_argparse():
    parser = argparse.ArgumentParser()
    subparsers = parser.add_subparsers(dest='command_type', help='command')

    # setup parser
    setup_parser = subparsers.add_parser('setup', help='Setup domain and asset group')

    # apply
    apply_parser = subparsers.add_parser('apply', help='Apply the owner change')
    apply_parser.add_argument('applicant_file', help='The documentation for applicant')
    apply_parser.add_argument('-o', '--username', help='user name')
    apply_parser.add_argument('-d', '--old_owner', help='Old owner name')
    apply_parser.add_argument('-a', '--approver', help='Approver name')

    # wait
    wait_parser = subparsers.add_parser('wait', help='Wait request')
    wait_parser.add_argument('-o', '--username', help='user name')
    wait_parser.add_argument('-r', '--role', help='user name')

    return parser.parse_args()

def create_keypair():
    if os.path.exists(PUBLIC_KEY) or os.path.exists(PRIVATE_KEY):
        print("Keypair already exists.")
        return 0
    keypair = bbclib.KeyPair()
    keypair.generate()
    with open(PRIVATE_KEY, "wb") as fout:
        fout.write(keypair.private_key)
    with open(PUBLIC_KEY, "wb") as fout:
        fout.write(keypair.public_key)
    print("Keypair is created.")
    print("private_key: %s" % binascii.b2a_hex(keypair.private_key).decode())
    print("public_key: %s" % binascii.b2a_hex(keypair.public_key).decode())

def load_keypair():
    if os.path.exists(PUBLIC_KEY) and os.path.exists(PRIVATE_KEY):
        with open(PRIVATE_KEY, "rb") as fin:
            private_key = fin.read()
        with open(PUBLIC_KEY, "rb") as fin:
            public_key = fin.read()
        global key_pair
        key_pair = bbclib.KeyPair(privkey=private_key, pubkey=public_key)
        print("*"*40)
        print(binascii.b2a_hex(key_pair.public_key).decode())
    else:
        print("Keypair was not found.")
        sys.exit(0)
    
def setup_domain():
    client = bbc_app.BBcAppClient()
    client.set_domain_id(domain_id)
    client.register_to_core()
    client.unregister_from_core()
    print("Setup domain done.")

def setup_client(user_id):
    client = bbc_app.BBcAppClient(multiq=True)
    client.set_domain_id(domain_id)
    client.set_user_id(user_id)
    client.set_keypair(key_pair)
    client.set_callback(bbc_app.Callback())
    client.register_to_core()
    return client

def apply_file(filename, user_id, old_owner_id, approver_id):
    if os.path.exists(filename):
        with open(filename, "rb") as fin:
            file_data = fin.read()
    client = setup_client(user_id)

    # create transaction object
    txobj = bbclib.make_transaction(relation_num=1, witness=True)
    bbclib.add_relation_asset(txobj, relation_idx=0, asset_group_id=asset_group_id, 
                            user_id=user_id, asset_body=b'Owner change', asset_file=file_data)
    txobj.witness.add_witness(user_id)
    txobj.witness.add_witness(old_owner_id)
    txobj.witness.add_witness(approver_id)

    # gather signature from old owner
    asset_files = {txobj.relations[0].asset.asset_id: file_data}
    query_id = client.gather_signatures(txobj, destinations=[old_owner_id], asset_files=asset_files)
    assert query_id
    response_data = client.callback.sync_by_queryid(query_id)
    if response_data[KeyType.status] < ESUCCESS:
        print("ERROR: ", response_data[KeyType.reason].decode())
        assert False

    sig = bbclib.BBcSignature()
    sig.unpack(response_data[KeyType.signature]) 
    txobj.witness.add_signature(user_id=response_data[KeyType.source_user_id], signature=sig)

    print("*"*10)
    print(txobj)

    # gather signature from approver
    query_id = client.gather_signatures(txobj, destinations=[approver_id], asset_files=asset_files)
    assert query_id
    response_data = client.callback.sync_by_queryid(query_id)
    if response_data[KeyType.status] < ESUCCESS:
        print("ERROR: ", response_data[KeyType.reason].decode())
        assert False
    sig = bbclib.BBcSignature()
    sig.unpack(response_data[KeyType.signature]) 
    txobj.witness.add_signature(user_id=response_data[KeyType.source_user_id], signature=sig)

    # sign
    sig = txobj.sign(private_key=key_pair.private_key, public_key=key_pair.public_key)
    txobj.witness.add_signature(user_id=user_id, signature=sig)

    # insert transaction
    query_id = client.insert_transaction(txobj)
    assert query_id

    print(txobj)
    print("Applicant is done.")

def wait_request(user_id):
    client = setup_client(user_id)

    # Synchronize to core node
    response_data = client.callback.synchronize()
    if response_data[KeyType.status] < ESUCCESS:
        print("ERROR: ", response_data[KeyType.reason].decode())
        assert False
    query_id_sign_req = response_data[KeyType.query_id]

    # Deserialize transaction data
    txobj, fmt_type = bbclib.deserialize(response_data[KeyType.transaction_data])

    # Sign
    sig = txobj.sign(keypair=key_pair)

    # Sendback sign
    query_id = client.sendback_signature(dest_user_id=response_data[KeyType.source_user_id], 
                                    transaction_id=txobj.transaction_id,
                                    signature=sig, query_id=query_id_sign_req)
    assert query_id
    print("Sendback signature.")

def wait_request_as_approver(user_id):
    client = setup_client(user_id)

    # Synchronize to core node
    response_data = client.callback.synchronize()
    if response_data[KeyType.status] < ESUCCESS:
        print("ERROR: ", response_data[KeyType.reason].decode())
        assert False
    query_id_sign_req = response_data[KeyType.query_id]

    # Deserialize transaction data
    txobj, fmt_type = bbclib.deserialize(response_data[KeyType.transaction_data])

    # Verify sign

    # Sign
    sig = txobj.sign(keypair=key_pair)

    # Sendback sign
    query_id = client.sendback_signature(dest_user_id=response_data[KeyType.source_user_id], 
                                    transaction_id=txobj.transaction_id,
                                    signature=sig, query_id=query_id_sign_req)
    assert query_id
    print("Sendback signature.")

if __name__ == "__main__":
    
    args = setup_argparse()
    if args.command_type == 'setup':
        setup_domain()
        create_keypair()
    else:
        username = args.username
        user_id = bbclib.get_new_id(username, include_timestamp=False)

        load_keypair()
        if args.command_type == 'apply':
            old_owner_name = args.old_owner
            old_owner_id = bbclib.get_new_id(old_owner_name, include_timestamp=False)
            approver_name = args.approver
            approver_id = bbclib.get_new_id(approver_name, include_timestamp=False)
            apply_file(args.applicant_file, user_id, old_owner_id, approver_id)
        elif args.command_type == 'wait':
            if args.role == 'approver':
                wait_request_as_approver(user_id)
            else:
                wait_request(user_id)