from adal import AuthenticationContext
import requests
import yaml


class Azure:

    def __init__(self, logs=None):

        self.logs = logs

        # create config file
        with open("config/connector-azure.yml") as stream:
            try:
                self.azure_config_yml = yaml.load(stream, Loader=yaml.FullLoader)
            except yaml.YAMLError as exc:
                print(exc)

        self.tenant = self.azure_config_yml['tenant']
        self.client_id = self.azure_config_yml['client_id']
        self.client_secret = self.azure_config_yml['client_secret']

        self.token = self.authenticate_device_code()

        self.header = {
            'User-Agent': 'python_test',
            'Authorization': 'Bearer {0}'.format(self.token),
            'Accept': 'application/json',
            'Content-Type': 'application/json'
        }

    def authenticate_device_code(self):
        """
        Authenticate the end-user using device auth.
        """

        tenant = self.tenant
        client_id = self.client_id
        client_secret = self.client_secret

        authority = "https://login.microsoftonline.com/" + tenant
        resource = "https://graph.microsoft.com"

        context = AuthenticationContext(authority)
        token = context.acquire_token_with_client_credentials(resource, client_id, client_secret)

        return token["accessToken"]

    def get_azure_users(self, sys_log=None):
        """
        This function will get all user IDs within the directory targeting Adobe Sign Groups

        https://docs.microsoft.com/en-us/graph/api/user-list?view=graph-rest-1.0&tabs=http

        :return:
        """

        req = requests.get("https://graph.microsoft.com/v1.0/users", headers=self.header)

        data = req.json()

        sys_log.update_progress('User Query', 1)

        return data

    def get_azure_groups(self):
        """
        This function will get all groups within the directory/

        https://docs.microsoft.com/en-us/graph/api/group-list?view=graph-rest-1.0&tabs=http

        :return: Object{}
        """

        req = requests.get("https://graph.microsoft.com/v1.0/groups", headers=self.header)

        data = req.json()

        return data

    def get_azure_groups_formatted(self, group_mapping, sys_log=None):
        """
        This function will the format the group into a list.
        :return: list[]
        """

        group_list = []

        data = self.get_azure_groups()

        for count, group in enumerate(data['value']):
            sys_log.update_progress('Group Query', count / len(data['value']))
            if group['displayName'] == "SIGN_ACCOUNT_ADMIN" or group['displayName'] == "SIGN_GROUP_ADMIN":
                pass
            else:
                if group_mapping:
                    if group['displayName'] in group_mapping:
                        group_list.append(group_mapping[group['displayName']])
                else:
                    group_list.append(group['displayName'])
        sys_log.update_progress('Group Query', 1)

        return group_list

    def create_user_json(self, sign_account_email, group_mapping, sys_log=None):
        """
        This function creates the user JSON matching the schmea with the other connectors.

        :return: Object{}
        """

        data = self.get_azure_users(sys_log)

        user_json = []

        for count, user in enumerate(data['value']):
            sys_log.update_progress('Formatting Users', count / len(data['value']))
            if user['userPrincipalName'] == sign_account_email:
                pass
            else:
                # Format it to an a standardize json format
                temp = {
                    "email": user['mail'],
                    "firstname": user['givenName'],
                    "groups": self.check_group_mapping(user['id'], group_mapping),
                    "lastname": user['surname'],
                    "username": user['mail'],
                }

                user_json.append(temp)
        sys_log.update_progress('Formatting Users', 1)

        return user_json

    def check_group_mapping(self, user_id, group_mapping):
        """
        This function checks to see if group mapping is enabled.
        :param user_id: string
        :param group_mapping: list()
        :return:
        """

        temp_groups = self.get_user_member_of(user_id)
        group_list = list()

        if group_mapping:
            for group_name in temp_groups:
                if group_name == "SIGN_ACCOUNT_ADMIN" or group_name == "SIGN_GROUP_ADMIN":
                    group_list.append(group_name)
                elif group_name in group_mapping:
                    group_list.append(group_mapping[group_name])
        else:
            group_list = temp_groups

        return group_list

    def get_user_member_of(self, user_id):
        """
        This function will get all user IDs member of information within the directory targeting Adobe Sign Groups
        :return:
        """

        group_list = []

        req = requests.get("https://graph.microsoft.com/v1.0/users/{}/memberOf".format(user_id), headers=self.header)

        data = req.json()

        for group in data['value']:
            group_list.append(group['displayName'])

        # TODO check for multiple groups
        return group_list
