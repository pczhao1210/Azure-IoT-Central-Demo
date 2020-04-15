import asyncio
import threading
import datetime
import time
import json
import random
import uuid
from functions import derive_device_key
from six.moves import input
from azure.iot.device import MethodResponse, Message, IoTHubDeviceClient, ProvisioningDeviceClient

fw_info = 1.0
telemetry_interval = 1
send_data = False

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
registration_result = provisioning_device_client.register()

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

    # Connect the client.
    device_client.connect()


# define method listeners
def Telemetry_Interval_Listerner(device_client):
    global telemetry_interval
    while True:
        # Wait for method calls
        method_request = device_client.receive_method_request("SetTelementryInternal")
        #print(type(method_request.payload))
        telemetry_interval = method_request.payload["Telemetry_Interval"]
        # set response payload
        payload = {"CallbackStatus": "200 OK",
                    "CallbackPayload": "The Interval is now: " + str(telemetry_interval)
                    }
        status = 200  # set return status code
        print(str(datetime.datetime.now()), "Processing Request \"SetTelementryInternal\" and Report, TThe Interval is now: " + str(telemetry_interval))
        method_response = MethodResponse.create_from_method_request(
            method_request, status, payload
        )
        # send response
        device_client.send_method_response(method_response)

        device_property_new_interval = {
                'Telemetry_Interval': telemetry_interval
            }
        device_client.patch_twin_reported_properties(device_property_new_interval)

def Get_Send_Data_info_listener(device_client):
    global send_data
    while True:
        # Wait for method calls
        method_request = device_client.receive_method_request("SetTelemetrySwitch")
        print(method_request.payload)
        send_data = method_request.payload
        payload = {"CommandStatus": "200 OK",
                    "CommandCallback": "The Send Data Status is: " + str(send_data)}
        status = 200  # set return status code
        print(str(datetime.datetime.now()), "Processing Request \"SetTelemetrySwitch\" and Report, The Send_Data Status is " + str(send_data))
        method_response = MethodResponse.create_from_method_request(
            method_request, status, payload
        )
        # send response
        device_client.send_method_response(method_response)

        device_property_new_switch = {
                'Telemetry_Switch': send_data
            }
        device_client.patch_twin_reported_properties(device_property_new_switch)

def FW_updater_listener(device_client):
    global fw_info
    while True:
        data = device_client.receive_twin_desired_properties_patch()
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
            device_client.patch_twin_reported_properties(device_property_new_fw)

def generic_method_listener(device_client):
    while True:
        method_request = (
            device_client.receive_method_request()
        )  # Wait for unknown method calls
        # set response payload
        payload = {"result": False, "data": "Unrecognized Method"}
        status = 400  # set return status code
        print(str(datetime.datetime.now()), "Receiving Unknown Method: " + method_request.name)
        method_response = MethodResponse.create_from_method_request(
            method_request, status, payload
        )
        # send response
        device_client.send_method_response(method_response)

# define behavior for receiving a message
def message_listener(device_client):
    while True:
        message = device_client.receive_message()  # blocking call
        print(str(datetime.datetime.now()), "Received Message:")
        print(message.data.decode())
        if len(message.custom_properties) > 0:
            print(str(datetime.datetime.now()), "With Custom Properties:")
            print(message.custom_properties)

# define send message to iot hub
def send_telemetry(device_client):
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

            device_client.send_message(device_telemetry_data)
            device_client.send_message(temp_telemetry_data)

def property_patcher(device_client):
    print("Updating Device Information on Start !!!")
    reported_property1 = location
    reported_property2 = device_property
    device_client.patch_twin_reported_properties(reported_property1)
    device_client.patch_twin_reported_properties(reported_property2)



# Schedule tasks for Listener
Get_FW_info_listener_Thread = threading.Thread(target=Telemetry_Interval_Listerner, args=(device_client,))
Get_FW_info_listener_Thread.daemon = True
Get_FW_info_listener_Thread.start()

Get_Send_Data_info_listener_Thread = threading.Thread(target=Get_Send_Data_info_listener, args=(device_client,))
Get_Send_Data_info_listener_Thread.daemon = True
Get_Send_Data_info_listener_Thread.start()

FW_updater_listener_Thread = threading.Thread(target=FW_updater_listener, args=(device_client,))
FW_updater_listener_Thread.daemon = True
FW_updater_listener_Thread.start()

generic_method_listener_Thread = threading.Thread(target=generic_method_listener, args=(device_client,))
generic_method_listener_Thread.daemon = True
generic_method_listener_Thread.start()

message_listener_Thread = threading.Thread(target=message_listener, args=(device_client,))
message_listener_Thread.daemon = True
message_listener_Thread.start()

send_telemetry_Thread = threading.Thread(target=send_telemetry, args=(device_client,))
send_telemetry_Thread.daemon = True
send_telemetry_Thread.start()

send_telemetry_Thread = threading.Thread(target=property_patcher, args=(device_client,))
send_telemetry_Thread.daemon = True
send_telemetry_Thread.start()

# Wait for user to indicate they are done listening for messages
while True:
    selection = input("Press Q to quit\n")
    if selection == "Q" or selection == "q":
        print("Quitting...")
        break

# Finally, disconnect
device_client.disconnect()


