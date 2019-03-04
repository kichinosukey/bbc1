from bbc1.core import bbclib
from bbc1.core import bbc_app

def main():
    user_id = bbclib.get_new_id("user_id for testing", include_timestamp=False)
    domain_id = bbclib.get_new_id("domain_id for testing", include_timestamp=False)
    keypair = bbclib.KeyPair()
    keypair.generate()

    client = bbc_app.BBcAppClient(port=9000, multiq=False, loglevel='all')
    client.set_domain_id(domain_id)
    client.set_user_id(user_id)
    client.set_keypair(keypair)

    client.register_to_core()
    print("Done!")

if __name__ == "__main__":
    main()