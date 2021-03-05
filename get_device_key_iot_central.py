import base64, hmac, hashlib
import asyncio
from azure.iot.device.aio import ProvisioningDeviceClient

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

async def main():
    provisioning_host = "global.azure-devices-provisioning.net"
    id_scope = "{Scope Here}"
    registration_id = "{Device Name Here}"
    symmetric_key = "{Master Key Here}"

    device_key = derive_device_key(registration_id,symmetric_key)

    provisioning_device_client = ProvisioningDeviceClient.create_from_symmetric_key(
        provisioning_host=provisioning_host,
        registration_id=registration_id,
        id_scope=id_scope,
        symmetric_key=device_key
    )

    registration_result = await provisioning_device_client.register()

    #print(registration_result)

    print("The Provision Status is :", registration_result.status)
    print("The Provisioned ID is: ", registration_result.registration_state.device_id)
    iot_hub_name = registration_result.registration_state.assigned_hub
    print("The Assigned IoT Hub is: ", registration_result.registration_state.assigned_hub)
    print("The eTag is :", registration_result.registration_state.etag)

    connectiont_String_raw = "HostName={iot_hub_name}.azure-devices.net;DeviceId={registration_id};SharedAccessKey={device_key}"
    connectiont_String = connectiont_String_raw.format(iot_hub_name = iot_hub_name, registration_id = registration_id, device_key = device_key)
    print("The Connection String is :", connectiont_String)


if __name__ == "__main__":
    asyncio.run(main())

