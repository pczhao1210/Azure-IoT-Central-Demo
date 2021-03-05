import asyncio
import threading
import datetime
import time
import json
import random
import uuid
from functions import derive_device_key
from six.moves import input
from azure.iot.device import MethodResponse, Message
from azure.iot.device.aio import IoTHubDeviceClient, ProvisioningDeviceClient

fw_info = 1.0
telemetry_interval = 10
send_data = True

location = {"Geo_Info":{"value":{"lon": 116.3, "lat": 39.9}}} #Beijing, China
device_property = {
    'Manufacturer': 'Microsoft',
    'Model': 'Azure_Demo_Device',
    'OS_Info': 'Azure_RTOS',
    'Disk_Info': '256',
    'RAM_Info': "2",
    'Firmware_Info': fw_info,
    "Telemetry_Interval": telemetry_interval,
    'Telemetry_Switch': send_data,
    'Device_City': 'Beijing',
    'Device_Country': 'P.R. China'
}

provisioning_host = "global.azure-devices-provisioning.net"
id_scope = "{Scope Here}"
registration_id = "{Device Name Here}"
symmetric_key = "{Master Key Here}"

async def main():
    
    # Connect using Device Provisioning Service (DPS)
    device_key = derive_device_key(registration_id,symmetric_key) #Convert from original symmetric key to device key for further enrollment
    #print(device_key)
    provisioning_device_client = ProvisioningDeviceClient.create_from_symmetric_key(
        provisioning_host=provisioning_host,
        registration_id=registration_id,
        id_scope=id_scope,
        symmetric_key=device_key
    )
    registration_result = await provisioning_device_client.register()
    print("The Provision Status is :", registration_result.status)
    print("The Provisioned ID is: ", registration_result.registration_state.device_id)
    print("The Assigned IoT Hub is: ", registration_result.registration_state.assigned_hub)
    print("The eTag is :", registration_result.registration_state.etag)

    if registration_result.status == "assigned":
        print("Provisioning Sucessfully, will send telemetry from the provisioned device now!")
        device_client = IoTHubDeviceClient.create_from_symmetric_key(
            symmetric_key=device_key,
            hostname=registration_result.registration_state.assigned_hub,
            device_id=registration_result.registration_state.device_id,
        )

        # Connect the client.
        await device_client.connect()

    # Update Device Information on Start
    await device_client.patch_twin_reported_properties(device_property)
    await device_client.patch_twin_reported_properties(location)


    # define method handler
    async def method_request_handler(method_request):
        if method_request.name == "SetTelementryInternal":
            global telemetry_interval
            print(str(datetime.datetime.now()), "Recevied Request \"SetTelementryInternal\", Setting Interval to: " + str(telemetry_interval))
            telemetry_interval = method_request.payload["Telemetry_Interval"]
            # set response payload
            payload = {"Time": str(datetime.datetime.now()), 
                        "CallbackStatus": "200 OK", 
                        "CallbackPayload": "The Interval is now: " + str(telemetry_interval)
                        }
            status = 200  # set return status code
            print(str(datetime.datetime.now()), "Processing Request \"SetTelementryInternal\" and Report, The Interval is now: " + str(telemetry_interval))
            method_response = MethodResponse.create_from_method_request(
                method_request, status, payload
            )
            # send response
            await device_client.send_method_response(method_response)

            device_property_new_interval = {
                    'Telemetry_Interval': telemetry_interval
                }
            await device_client.patch_twin_reported_properties(device_property_new_interval)

        elif method_request.name == "SetTelemetrySwitch":
            global send_data
            print(str(datetime.datetime.now()), "Recevied Request \"SetTelemetrySwitch\", Setting Send_Data Switch to: " + str(send_data))
            send_data = method_request.payload
            payload = {"Time": str(datetime.datetime.now()),
                        "CommandStatus": "200 OK",
                        "CommandCallback": "The Send Data Status is: " + str(send_data)}
            status = 200  # set return status code
            print(str(datetime.datetime.now()), "Processing Request \"SetTelemetrySwitch\" and Report, The Send_Data Status is " + str(send_data))
            method_response = MethodResponse.create_from_method_request(
                method_request, status, payload
            )
            # send response
            await device_client.send_method_response(method_response)

            device_property_new_switch = {
                    'Telemetry_Switch': send_data
                }
            await device_client.patch_twin_reported_properties(device_property_new_switch)

        else:
            # set response payload
            payload = {"result": False, "data": "Unrecognized Method"}
            status = 400  # set return status code
            print(str(datetime.datetime.now()), "Receiving Unknown Method: " + method_request.name)
            method_response = MethodResponse.create_from_method_request(
                method_request, status, payload
            )
            # send response
            await device_client.send_method_response(method_response)

    async def twin_patch_handler(data):
        global fw_info
        fw_info_new = data["Firmware_Info"]["value"]
        print(str(datetime.datetime.now()), "Received Firmware Upgrade Request: Version " +
                str(fw_info_new)+ ", Initialiazing...")
        time.sleep(2)
        if fw_info >= fw_info_new:
            print(str(datetime.datetime.now()), "The Firmware Version is Latest, Firmware Upgrade Cancelled")

        if fw_info < fw_info_new:
            print(str(datetime.datetime.now()), "Step 1: New Firmware Version " + str(fw_info_new),
                    "is Set, Firmware Downloading...")
            time.sleep(2)
            print(str(datetime.datetime.now()), "Step 2: Downloading Success, Validation Firmware file...")
            time.sleep(2)
            print(str(datetime.datetime.now()), "Step 3: Firmware Validation Passed, Start Firmware Upgrading...")
            time.sleep(2)
            print(str(datetime.datetime.now()), "Step 4: Upgrading Sucessful, Rebooting Device...")
            time.sleep(2)
            print(str(datetime.datetime.now()), "Step 5: Device Successful Reconnected !!!")
            fw_info = fw_info_new

            device_property_new_fw = {
                'Firmware_Info': fw_info
            }
            await device_client.patch_twin_reported_properties(device_property_new_fw)

    # define behavior for receiving a message
    async def message_receive_handler(device_client):
        while True:
            message = device_client.receive_message()  # blocking call
            print(str(datetime.datetime.now()), "Received Message:")
            print(message.data.decode())
            if len(message.custom_properties) > 0:
                print(str(datetime.datetime.now()), "With Custom Properties:")
                print(message.custom_properties)

    # define send message to iot hub
    async def send_telemetry(device_client):
        global telemetry_interval, send_data
        telemetry_data_raw = '{{"voltage": {voltage},"ampere": {ampere},"walt": {walt}}}'
        temp_telemetry_raw = '{{"Temperature": {temp},"Humidity": {humi}}}'
        while True:
            time.sleep(telemetry_interval)
            if send_data == True:
                voltageset = 220 + (random.random() * 10)
                ampereset = 10 + random.random()
                waltset = (voltageset * ampereset) / 1000
                device_telemetry_data_formatted = telemetry_data_raw.format(
                    voltage=voltageset, ampere=ampereset, walt=waltset)     
                device_telemetry_data = Message(device_telemetry_data_formatted)
                print(str(datetime.datetime.now()),
                        "Sending Telemetry: ", device_telemetry_data)

                
                Temperatureset = 20 + (random.random()*3)
                Humidityset = 50 + (random.random()*6)
                temp_telemetry_data_formatted = temp_telemetry_raw.format(
                    temp=Temperatureset, humi=Humidityset)
                temp_telemetry_data = Message(temp_telemetry_data_formatted)
                print(str(datetime.datetime.now()),
                        "Sending Telemetry: ", temp_telemetry_data)

                if waltset > 2.5:
                    alert_info = "Capacity Over 90%"
                    alert_msg_raw = '{{"Alert": "{alert}"}}'
                    alert_msg = Message(alert_msg_raw.format(alert = alert_info), content_encoding= "utf-8", content_type="application/json")
                    alert_msg.custom_properties["Alert"] = "Capacity Over 90%"
                    alert_msg.message_id = uuid.uuid4()
                    await device_client.send_message(alert_msg)
                    print(str(datetime.datetime.now()), "Sending Telemetry: ", alert_msg)

                await device_client.send_message(device_telemetry_data)
                await device_client.send_message(temp_telemetry_data)

                
    def send_telemetry_sync(device_client):
        loop = asyncio.new_event_loop()
        loop.run_until_complete(send_telemetry(device_client))

    def stdin_listener():
        while True:
            selection = input("Press Q to quit\n")
            if selection == "Q" or selection == "q":
                print("Quitting...")
                break

    # Set handlers to the client
    device_client.on_method_request_received = method_request_handler
    device_client.on_twin_desired_properties_patch_received = twin_patch_handler
    device_client.on_message_received = message_receive_handler
    
    send_telemetry_Thread = threading.Thread(target=send_telemetry_sync, args=(device_client,))
    send_telemetry_Thread.daemon = True
    send_telemetry_Thread.start()

    # Run the stdin listener in the event loop
    loop = asyncio.get_event_loop()
    user_finished = loop.run_in_executor(None, stdin_listener)

    # Wait for user to indicate they are done listening for method calls
    await user_finished

    # Finally, disconnect
    await device_client.disconnect()


if __name__ == "__main__":
    asyncio.run(main())

