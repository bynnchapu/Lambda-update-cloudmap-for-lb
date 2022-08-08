import boto3

def get_elb_network_interfaces(lb_name):
    lb_search_condition = 'ELB ' + lb_name
    client = boto3.client('ec2')

    response = client.describe_network_interfaces(
        Filters=[
            {'Name': 'description',
             'Values': [lb_search_condition]}
        ]
    )

    network_interfaces = list()
    for network_interface in response["NetworkInterfaces"]:
        network_interface_info = {
            "NetworkInterfaceId": network_interface["NetworkInterfaceId"],
            "PrivateIpAddress": network_interface["PrivateIpAddress"]
        }
        network_interfaces.append(network_interface_info)

    return network_interfaces


def what_is_update_needed(network_interfaces, service_id):
    client = boto3.client('servicediscovery')

    needed_network_interfaces = list()
    for network_interface_info in network_interfaces:
        try:
            response = client.get_instance(
                ServiceId=service_id,
                InstanceId=network_interface_info["NetworkInterfaceId"],
            )

            if response["Instance"]["Attributes"]["AWS_INSTANCE_IPV4"] \
                != network_interface_info["PrivateIpAddress"]:
                client.deregister_instance(
                    ServiceId=service_id,
                    InstanceId=network_interface_info["NetworkInterfaceId"]
                )
                needed_network_interfaces.append(network_interface_info)
        except:
            needed_network_interfaces.append(network_interface_info)

    return needed_network_interfaces


def set_cloudmap_for_elb_to_elb_private_ip(network_interfaces, service_id):
    client = boto3.client('servicediscovery')
    
    for network_interface in network_interfaces:
        try:
            client.register_instance(
                ServiceId=service_id,
                InstanceId=network_interface["NetworkInterfaceId"],
                Attributes={
                    'AWS_INSTANCE_IPV4': network_interface["PrivateIpAddress"]
                }
            )
        except:
            return False

    return True


def lambda_handler(event, context):
    network_interfaces = get_elb_network_interfaces(event["LBName"])
    update_network_interfaces = what_is_update_needed(
        network_interfaces,
        event["ServiceId"]
    )

    if not update_network_interfaces:
        result = True
        information_message = "No update targets."
    else:
        result = set_cloudmap_for_elb_to_elb_private_ip(
            update_network_interfaces,
            event["ServiceId"]
        )
        if result:
            information_message = "Update successed."
        else:
            information_message = "Failed in update process."

    function_result = {
        'Success': result,
        'Detail': information_message
    }
    print(function_result)
    return function_result
