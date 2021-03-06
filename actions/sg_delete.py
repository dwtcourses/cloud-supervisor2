'''
## sg_delete
What it does: Deletes a security group  
Usage: AUTO: sg_delete  
Limitations: This will fail if there is something still attached to the SG.  
'''

import boto3

### DeleteSecurityGroup ###
def run_action(rule,entity,params):
    text_output = str(entity)
    region = entity['region']
    region = region.replace("_","-")
    sg_id = entity['id']
    
    ec2 = boto3.resource('ec2', region_name=region)
    result = ec2.SecurityGroup(sg_id).delete()

    responseCode = result['ResponseMetadata']['HTTPStatusCode']
    if responseCode >= 400:
        text_output = "Unexpected error: %s \n" % str(result)
    else:
        text_output = "Security Group %s successfully deleted\n" % sg_id

    return text_output 