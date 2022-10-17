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
    response = client.list_instances(
        ServiceId=service_id
    )

    service_instances = list()
    for service_instance in response['Instances']:
        service_instance_info = {
            'Id': service_instance['Id'],
            'AWS_INSTANCE_IPV4': service_instance['Attributes']['AWS_INSTANCE_IPV4']
        }
        service_instances.append(service_instance_info)

    update_needed_netowrk_interfaces = list()
    used_network_interfaces = list()
    for network_interface in network_interfaces:
        add_flag = True
        for service_instance in service_instances:
            if network_interface['PrivateIpAddress'] == service_instance['AWS_INSTANCE_IPV4']:
                add_flag = False
                used_network_interfaces.append(network_interface)
                break
        if add_flag:
            update_needed_netowrk_interfaces.append(network_interface)

    remove_needed_service_interfaces = list()
    for service_instance in service_instances:
        add_flag = True
        for used_network_interface in used_network_interfaces:
            if service_instance['Id'] == used_network_interface['NetworkInterfaceId']:
                add_flag = False
                break
        if add_flag:
            remove_needed_service_interfaces.append(service_instance)

    return_info = {
        'update_needed_netowrk_interfaces': update_needed_netowrk_interfaces,
        'remove_needed_service_interfaces': remove_needed_service_interfaces
    }

    return return_info 


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


def remove_cloudmap_for_elb(service_instances, service_id):
    client = boto3.client('servicediscovery')

    for service_instance in service_instances:
        try:
            client.deregister_instance(
                ServiceId=service_id,
                InstanceId=service_id['Id']
            )
        except:
            return False

    return True


def lambda_handler(event, context):
    network_interfaces = get_elb_network_interfaces(event["LBName"])
    update_info = what_is_update_needed(
        network_interfaces,
        event["ServiceId"]
    )

    if not update_info['update_needed_netowrk_interfaces'] and :
        result = True
        information_message = "No update targets."
    else:
        result = set_cloudmap_for_elb_to_elb_private_ip(
            update_info['update_needed_netowrk_interfaces'],
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
