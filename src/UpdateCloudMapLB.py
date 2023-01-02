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


def remove_cloudmap_for_elb(service_id):
    client = boto3.client('servicediscovery')

    response = client.list_instances(ServiceId=service_id)
    service_instances = list()
    for service_instance in response['Instances']:
        service_instance_info = {
            'Id': service_instance['Id'],
            'AWS_INSTANCE_IPV4': service_instance['Attributes']['AWS_INSTANCE_IPV4']
        }
        service_instances.append(service_instance_info)

    for service_instance in service_instances:
        try:
            client.deregister_instance(
                ServiceId=service_id,
                InstanceId=service_instances['Id']
            )
        except:
            return False

    return True


def lambda_handler(event, context):
    network_interfaces = get_elb_network_interfaces(event["LBName"])

    if remove_cloudmap_for_elb(event["ServiceId"]):
        if set_cloudmap_for_elb_to_elb_private_ip(network_interfaces, event["ServiceId"]):
            result = True
            information_message = "Succcess updating process."
        else:
            result = False
            information_message = "Failed at updating instances process..."
    else:
        result = False
        information_message = "Failed at removing instances process..."

    function_result = {
        'Success': result,
        'Detail': information_message
    }
    print(function_result)
    return function_result
