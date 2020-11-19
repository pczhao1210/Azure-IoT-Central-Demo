import base64, hmac, hashlib
from azure.iot.device import ProvisioningDeviceClient

def derive_device_key(device_id, master_symmetric_key):
    message = device_id.encode("utf-8")
    #print(message)
    signing_key = base64.b64decode(master_symmetric_key.encode("utf-8"))
    #print(signing_key)
    signed_hmac = hmac.HMAC(signing_key, message, hashlib.sha256)
    #print(signed_hmac)
    device_key_encoded = base64.b64encode(signed_hmac.digest())
    #print(device_key_encoded)
    #print(device_key_encoded.decode("utf-8"))
    return device_key_encoded.decode("utf-8")

provisioning_host = "global.azure-devices-provisioning.net"
id_scope = "{{Scope ID}}"
registration_id = "{{Device ID}}"
symmetric_key = "{{Master Key or Registration Group}}"

device_key = derive_device_key(registration_id,symmetric_key)

provisioning_device_client = ProvisioningDeviceClient.create_from_symmetric_key(
    provisioning_host=provisioning_host,
    registration_id=registration_id,
    id_scope=id_scope,
    symmetric_key=device_key
)

registration_result = provisioning_device_client.register()

print("The status is :", registration_result.status)
print("The device id is: ", registration_result.registration_state.device_id)
print("The assigned IoT Hub is: ", registration_result.registration_state.assigned_hub)
print("The etag is :", registration_result.registration_state.etag)
print("The Connect Key is :", device_key)