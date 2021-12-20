import asyncio
import threading
import datetime
import time
import json
import random
import uuid
from functions import derive_device_key
from six.moves import input
from azure.iot.device.aio import IoTHubDeviceClient, ProvisioningDeviceClient
from azure.iot.device import MethodResponse, Message

fw_info = 1.0
telemetry_interval = 10
send_data = True
overload_value = 2.45

location = {"Geo_Info":{"value":{"lon": 116.3, "lat": 39.9}}}
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


# Using this for Connecting through Device Provisioning Service (DPS) - "Group Enrollment"
# When provision through "Individual Enrollment", USE SYMMETRIC KEY DIRECTLY
provisioning_host = "global.azure-devices-provisioning.net"
id_scope = "{DPS Scope ID}"
registration_id = "{Your Device ID}"
symmetric_key = "{Your DPS Group Registration Key}"


async def main():
    #'''
    # Connect using Device Provisioning Service (DPS)
    device_key = derive_device_key(registration_id,symmetric_key) #Convert from original symmetric key to device key for further enrollment
    provisioning_device_client = ProvisioningDeviceClient.create_from_symmetric_key(
        provisioning_host=provisioning_host,
        registration_id=registration_id,
        id_scope=id_scope,
        symmetric_key=device_key
    )
    registration_result = await provisioning_device_client.register()

    print("The status is :", registration_result.status)
    print("The device id is: ", registration_result.registration_state.device_id)
    print("The assigned IoT Hub is: ", registration_result.registration_state.assigned_hub)
    print("The etag is :", registration_result.registration_state.etag)

    if registration_result.status == "assigned":
        print("Provisioning Sucessfully, will send telemetry from the provisioned device")
        device_client = IoTHubDeviceClient.create_from_symmetric_key(
            symmetric_key=device_key,
            hostname=registration_result.registration_state.assigned_hub,
            device_id=registration_result.registration_state.device_id,
        )
    
        # connect the client
        await device_client.connect()

    # define method handlers
    async def method_request_handler(method_request):
        if method_request.name == "Get_FW_info":
            # set response payload
            payload = {"result": True,
                        "data": "The Firmware version now is " + str(fw_info)}
            status = 200  # set return status code
            print(str(datetime.datetime.now()), "Processing Request \"Get_FW_info\" and Report, The Firmware version now is " + str(fw_info))
            method_response = MethodResponse.create_from_method_request(
                method_request, status, payload
            )
            # send response
            await device_client.send_method_response(method_response)
        
        elif method_request.name =="SetTelementryInternal":
            global telemetry_interval
            telemetry_interval_tobe = method_request.payload["Telemetry_Interval"]
            telemetry_interval = telemetry_interval_tobe
            #print(send_data)
            # set response payload
            payload = {"result": telemetry_interval,
                        "data": "The Send Data Status is " + str(telemetry_interval)}
            status = 200  # set return status code
            print(str(datetime.datetime.now()), "Processing Request \"SetTelemetryInterval\" and Report, The Telemetry Interval is now " + str(telemetry_interval))
            method_response = MethodResponse.create_from_method_request(
                method_request, status, payload
            )
            # send response
            await device_client.send_method_response(method_response)

        elif method_request.name =="SetTelemetrySwitch":
            global send_data
            data = await device_client.get_twin()  # blocking call
            #print(data)
            send_data_now = send_data
            send_data_tobe = method_request.payload
            send_data = send_data_tobe
            #print(send_data)
            # set response payload
            payload = {"result": send_data,
                        "data": "The Send Data Status is " + str(send_data)}
            status = 200  # set return status code
            print(str(datetime.datetime.now()), "Processing Request \"SetTelemetrySwitch\" and Report, The Send_Data Status is now " + str(send_data))
            method_response = MethodResponse.create_from_method_request(
                method_request, status, payload
            )
            # send response
            await device_client.send_method_response(method_response)

        elif method_request.name == "FW_Update":
            fw_info_from_method = method_request.payload
            print(str(datetime.datetime.now()), "Received Firmware Upgrade Request: Version " +
                    str(fw_info_from_method)+ ", Initialiazing...")
            time.sleep(2)
            if fw_info >= fw_info_from_method:
                payload = {"result": False,
                        "data": ("The Firmware Version Now is " + str(fw_info) + ", Update Cancelled")}
                status = 403  # set return status code
                print(str(datetime.datetime.now()), "The Firmware Version is Latest, Firmware Upgrade Cancelled")
                method_response = MethodResponse.create_from_method_request(
                    method_request, status, payload
                )
                # send response
                await device_client.send_method_response(method_response)
            if fw_info < fw_info_from_method:
                payload = {"result": True,
                    "data": ("The Firmware Version Now is " + str(fw_info)+ ", Update Task Now Begin...")}
                status = 200  # set return status code
                method_response = MethodResponse.create_from_method_request(
                    method_request, status, payload
                )
                # send response
                await device_client.send_method_response(method_response)
                print(str(datetime.datetime.now()), "Step 1: New Firmware Version " + str(fw_info_from_method),
                        "is Set, Firmware Downloading...")
                time.sleep(2)
                print(str(datetime.datetime.now()), "Step 2: Downloading Success, Validation Firmware file...")
                time.sleep(2)
                print(str(datetime.datetime.now()), "Step 3: Firmware Validation Passed, Start Firmware Upgrading...")
                time.sleep(2)
                print(str(datetime.datetime.now()), "Step 4: Upgrading Sucessful, Rebooting Device...")
                time.sleep(2)
                print(str(datetime.datetime.now()), "Step 5: Device Successful Reconnected !!!")
        
        else:
            # set response payload
            payload = {"result": False, "data": "Unrecognized Method"}
            status = 400  # set return status code
            print(str(datetime.datetime.now()), "Receiving Unknown Method: " + method_request.name)
            print(method_request.payload)
            method_response = MethodResponse.create_from_method_request(
                method_request, status, payload
            )
            # send response
            await device_client.send_method_response(method_response)

    # define behavior for receiving a message
    async def message_receive_handler(message):
        print(str(datetime.datetime.now()), "Received Message:")
        print(message.data.decode())
        if len(message.custom_properties) > 0:
            print("With Custom Properties:")
            print(message.custom_properties)

    # Twin Listener
    async def twin_patch_handler(data):
        global telemetry_interval, send_data
        #data = patch  # blocking call
        if "Telemetry_Interval" in data:
            telemetry_interval = data["Telemetry_Interval"]
            print(str(datetime.datetime.now()), "Telemetry Interval has set to", telemetry_interval)
        if "Send_Data" in data:
            send_data = data["Send_Data"]
            if send_data == True:
                print(str(datetime.datetime.now()), "Send Data has set to " + str(send_data) +
                    ", Continue Sending Data...")
            else:
                print(str(datetime.datetime.now()), "Send Data has set to " + str(send_data) +
                    ", Please update \"Send_Data\" to \"True\" in device-twin to restart!")
        reported_properties = {
            "Telemetry_Interval": telemetry_interval,
            "Send_Data": send_data
        }
        await device_client.patch_twin_reported_properties(reported_properties)
   
    # define send message to iot hub
    async def send_telemetry(device_client):
        global telemetry_interval, send_data, overload_value
        telemetry_data_raw = '{{"voltage": {voltage},"ampere": {ampere},"walt": {walt}}}'
        temp_telemetry_raw = '{{"Temperature": {temp},"Humidity": {humi}}}'
        alert_data_raw = '{{"Alert": "{alert_text}"}}'

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

                time.sleep(1)
                Temperatureset = 20 + (random.random()*3)
                Humidityset = 50 + (random.random()*6)
                temp_telemetry_data_formatted = temp_telemetry_raw.format(
                    temp=Temperatureset, humi=Humidityset)
                temp_telemetry_data = Message(temp_telemetry_data_formatted)
                print(str(datetime.datetime.now()),
                        "Sending Telemetry: ", temp_telemetry_data)

                if waltset >= overload_value:
                    alert_info = "Overload"
                    alertdata_formatted = alert_data_raw.format(alert_text = alert_info)
                    alert_data = Message(alertdata_formatted, content_type="application/json", content_encoding="utf-8")
                    temp_telemetry_data.custom_properties["Overload"] = "Yes"
                    print(str(datetime.datetime.now()),
                        "Sending Telemetry: ", alert_data)
                    await device_client.send_message(alert_data)

                await device_client.send_message(device_telemetry_data)
                await device_client.send_message(temp_telemetry_data)
                

    async def property_patcher(device_client):
        print("Updating Device Information on Start !!!")
        reported_property1 = location
        reported_property2 = device_property
        await device_client.patch_twin_reported_properties(reported_property1)
        await device_client.patch_twin_reported_properties(reported_property2)

    def send_telemetry_sync(device_client):
        loop = asyncio.new_event_loop()
        loop.run_until_complete(send_telemetry(device_client))

    def twin_patch_sync(device_client):
        loop = asyncio.new_event_loop()
        loop.run_until_complete(property_patcher(device_client))

    def stdin_listener():
        while True:
            selection = input("Press Q to quit\n")
            if selection == "Q" or selection == "q":
                print("Quitting...")
                break

    # Set handlers to the client
    device_client.on_method_request_received = method_request_handler
    device_client.on_message_received = message_receive_handler
    device_client.on_twin_desired_properties_patch_received = twin_patch_handler
    
    send_telemetry_Thread = threading.Thread(target=send_telemetry_sync, args=(device_client,))
    send_telemetry_Thread.daemon = True
    send_telemetry_Thread.start()

    send_telemetry_Thread = threading.Thread(target=twin_patch_sync, args=(device_client,))
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


    # If using Python 3.6 or below, use the following code instead of asyncio.run(main()):
    # loop = asyncio.get_event_loop()
    # loop.run_until_complete(main())
    # loop.close()

