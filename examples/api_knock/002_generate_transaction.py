from bbc1.core import bbclib
from bbc1.core import bbc_app

def setup_appclient(user_id=None, domain_id=None, multiq=False, keypair=None):
    client = bbc_app.BBcAppClient(multiq=multiq)
    client.set_domain_id(domain_id)
    client.set_user_id(user_id)
    client.set_keypair(keypair)
    client.register_to_core()
    return client

def main():
    user_id = bbclib.get_new_id("user_id for testing", include_timestamp=False)
    domain_id = bbclib.get_new_id("domain_id for testing", include_timestamp=False)
    asset_group_id = bbclib.get_new_id("asset_group_id for testing", include_timestamp=False)
    keypair = bbclib.KeyPair()
    keypair.generate()

    client = setup_appclient(user_id=user_id, domain_id=domain_id, keypair=keypair)

    txobj = bbclib.make_transaction(relation_num=1, witness=True)
    bbclib.add_relation_asset(txobj, relation_idx=0, asset_group_id=asset_group_id, user_id=user_id,
                            asset_file=b"test file", asset_body=b"test asset")
    txobj.witness.add_witness(user_id)
    sig = txobj.sign(key_type=bbclib.KeyType.ECDSA_SECP256k1,
                    private_key=keypair.private_key, public_key=keypair.public_key)
    txobj.witness.add_signature(user_id=user_id, signature=sig)
    print(txobj)

if __name__ == "__main__":
    main()