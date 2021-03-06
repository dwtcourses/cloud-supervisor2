import re
import boto3
import importlib 
from botocore.exceptions import ClientError

def handle_event(message,text_output_array):
    post_to_sns = True
    #Break out the values from the JSON payload from Dome9
    rule_name = message['rule']['name']
    status = message['status']
    entity_id = message['entity']['id']
    entity_name = message['entity']['name']

    #Make sure that the event that's being referenced is for the account this function is running in.
    event_account_id = message['account']['id']
    try:
        #get the accountID
        sts = boto3.client("sts")
        lambda_account_id = sts.get_caller_identity()["Account"]
    except ClientError as e:
        text_output_array.append("Unexpected STS error: %s \n"  % e)

    if lambda_account_id != event_account_id:
        text_output_array.append("Error: This finding was found in account id %s. The Lambda function is running in account id: %s. Remediations need to be ran from the account there is the issue in.\n" % (event_account_id, lambda_account_id))
        post_to_sns = False
        return text_output_array,post_to_sns
            
    #All of the remediation values are coming in on the compliance tags and they're pipe delimited
    compliance_tags = message['rule']['complianceTags'].split("|")

    #evaluate the event and tags and decide is there's something to do with them. 
    if status == "Passed":
        text_output_array.append("Previously failing rule has been resolved: %s \n ID: %s \nName: %s \n" % (rule_name, entity_id, entity_name))
        post_to_sns = False
        return text_output_array,post_to_sns

    #Check if any of the tags have AUTO: in them. If there's nothing to do at all, skip it. 
    auto_pattern = re.compile("AUTO:")
    if not auto_pattern.search(message['rule']['complianceTags']):
        text_output_array.append("Rule %s \n Doesn't have any 'AUTO:' tags. \nSkipping.\n" % rule_name)
        post_to_sns = False
        return text_output_array,post_to_sns

    for tag in compliance_tags:
        tag = tag.strip() #Sometimes the tags come through with trailing or leading spaces. 

        #Check the tag to see if we have AUTO: in it
        pattern = re.compile("^AUTO:\s.+")
        if pattern.match(tag):
            text_output_array.append("Rule violation found: %s \nID: %s | Name: %s \nRemediation Action: %s \n" % (rule_name, entity_id, entity_name, tag))

            # Pull out only the action verb to run as a function
            # The format is AUTO: action_name param1 param2
            arr = tag.split(' ')
            if len(arr) < 2:
                err_msg = "Empty AUTO: tag. No action was specified"
                print(err_msg)
                text_output_array.append(err_msg)
                continue
            
            action = arr[1]
            params = arr[2:]

            try:
                action_module = importlib.import_module('actions.' + action, package=None)
            except:
                print("Error: could not find action: " + action)
                text_output_array.append("Action: %s is not a known action. Skipping.\n" % action)
                continue
            
            print("Found action '%s', about to invoke it" % action)
            action_msg = ""
            try:
                action_msg = action_module.run_action(message['rule'],message['entity'], params)
            except Exception as e: 
                action_msg = "Error while executing function '%s'.\n Error: %s \n" % (action,e)
                print(action_msg)
            finally:
                text_output_array.append(action_msg)

    #After the remediation functions finish, send the notification out. 
    return text_output_array,post_to_sns
