import requests
import json
import yaml

LOGGER = None


class Sign:

    def __init__(self, logs=None):

        self.logs = logs
        global LOGGER
        LOGGER = self.logs

        try:
            with open("config/connector-sign-sync.yml") as stream:
                try:
                    self.sign_config_yml = yaml.load(stream, Loader=yaml.FullLoader)
                except yaml.YAMLError as exc:
                    print(exc)
        except IOError:
            self.logs['error'].error('** Failed To Open Connector-Sign-Sync.yml **')
            exit(1)

        # Read server parameters
        self.host = self.sign_config_yml['server']['host']
        self.endpoint = self.sign_config_yml['server']['endpoint_v5']

        # Read condition parameters
        self.version = self.sign_config_yml['sign_sync']['version']
        self.connector = self.sign_config_yml['sign_sync']['connector']
        self.account_type = self.sign_config_yml['umapi_conditions']['target_account_type']
        self.cache_mode = self.sign_config_yml['sign_sync']['cache_mode']

        # Read enterprise parameters
        self.integration = self.sign_config_yml['enterprise']['integration']
        self.email = self.sign_config_yml['enterprise']['email']

        if self.connector == 'umapi':
            self.product_profile = self.sign_config_yml['umapi_conditions']['product_profile']
        else:
            self.product_profile = []
            self.account_admin = None

        # Read provisioning rules
        self.auto_provision = self.sign_config_yml['sign_sync']['provisioning']['auto_provisioning']
        self.auto_password = self.sign_config_yml['sign_sync']['provisioning']['email_suppression']['password']

        self.url = self.get_sign_url()
        self.header = self.get_sign_header()
        self.temp_header = self.get_temp_header()

        self.sign_users = self.get_sign_users()
        self.default_group = self.get_sign_group()['Default Group']


    class SignDecorators:
        @classmethod
        def exception_catcher(cls, func):
            def wrapper(*args, **kwargs):
                try:
                    res = func(*args, **kwargs)
                    return res
                except requests.exceptions.HTTPError as http_error:
                    LOGGER['error'].error("-- HTTP ERROR: {} --".format(http_error))
                    exit()
                except requests.exceptions.ConnectionError as conn_error:
                    LOGGER['error'].error("-- ERROR CONNECTING -- {}".format(conn_error))
                    exit()
                except requests.exceptions.Timeout as timeout_error:
                    LOGGER['error'].error("-- TIMEOUT ERROR: {} --".format(timeout_error))
                    exit()
                except requests.exceptions.RequestException as error:
                    LOGGER['error'].error("-- ERROR: {} --".format(error))
                    exit()

            return wrapper

    @SignDecorators.exception_catcher
    def validate_integration_key(self, headers, url):
        """
        This function validates that the SIGN integration key is valid.
        :param headers: dict()
        :param url: str
        :return: dict()
        """

        if self.version == "v5":
            res = requests.get(url + "base_uris", headers=self.header)
        else:
            res = requests.get(url + "baseUris", headers=headers)

        return res

    @SignDecorators.exception_catcher
    def api_get_group_request(self):
        """
        API request to get group information
        :return: dict()
        """

        res = requests.get(self.url + 'groups', headers=self.header)

        return res

    @SignDecorators.exception_catcher
    def api_get_users_request(self):
        """
        API request to get user information from SIGN.
        :return: dict()
        """

        res = requests.get(self.url + 'users', headers=self.header)

        return res

    @SignDecorators.exception_catcher
    def api_post_group_request(self, data):
        """
        API request to post new group in SIGN.
        :param data: list[]
        :return: dict[]
        """

        res = requests.post(self.url + 'groups', headers=self.temp_header, data=json.dumps(data))

        return res

    @SignDecorators.exception_catcher
    def api_put_user_request(self, sign_user_id, data):
        """
        API request to change user group information into SIGN.
        :param sign_user_id: str
        :param data: dict()
        :return: dict()
        """

        res = requests.put(self.url + 'users/' + sign_user_id, headers=self.temp_header, data=json.dumps(data))

        return res

    @SignDecorators.exception_catcher
    def api_get_user_by_id_request(self, user_id):
        """
        API request to get user by ID
        :param user_id:  str
        :return: dict()
        """

        res = requests.get(self.url + 'users/' + user_id, headers=self.header)

        return res

    @SignDecorators.exception_catcher
    def api_put_user_status_request(self, user_id, payload):
        """
        API request to change user status.
        :param user_id: str
        :param payload: dict()
        :return: dict()
        """

        res = requests.put(self.url + 'users/' + user_id + '/status',
                           headers=self.header, data=json.dumps(payload))

        return res

    @SignDecorators.exception_catcher
    def api_post_user_request(self, payload):
        """
        API request to post new user in SIGN.
        :param payload: dict()
        :return: dict()
        """

        res = requests.post(self.url + 'users',
                            headers=self.header, data=json.dumps(payload))

        return res

    def get_sign_url(self, ver=None):
        """
        This function returns the SIGN url.
        :param ver: str
        :return: str
        """

        if ver is None:
            return "https://" + self.host + self.endpoint + "/"
        else:
            return "https://" + self.host + "/" + ver + "/"

    def get_sign_header(self, ver=None):
        """
        This function returns the SIGN header
        :param ver: str
        :return: dict()
        """

        headers = {}

        if ver == 'v6':
            headers = {
                "Authorization": "Bearer {}".format(self.integration)
            }
        elif self.version == 'v5' or ver == 'v5':
            headers = {
                "Access-Token": self.integration
            }

        return headers

    def get_adobe_ou(self):
        """
        This function will return the LDAP OU destination from the yml.
        :return: str
        """

        return self.sign_config_yml['ldap_conditions']['adobe_sign_ou']

    def get_sign_group(self):
        """
        This function creates a list of groups that's in Adobe Sign Groups.
        :return: list[]
        """

        temp_list = {}

        res = self.api_get_group_request()

        if res.status_code == 200:
            sign_groups = res.json()
            for group in sign_groups['groupInfoList']:
                temp_list[group['groupName']] = group['groupId']

        return temp_list

    def get_product_profile(self):
        """
        This function returns the product profile
        :return: list[]
        """

        return self.product_profile

    def get_sign_users(self):
        """
        This function will create a list of all users in SIGN.
        :return: list[dict()]
        """

        user_list = []
        res = self.api_get_users_request()

        if res.status_code == 200:
            user_list.append(res.json()['userInfoList'])

        return user_list[0]

    def create_sign_group(self, group_list, sys_log):
        """
        This function will create a group in Adobe SIGN if the group doesn't already exist.
        :param group_list: list[]
        :param sys_log: LOGGER
        :return:
        """

        sign_group = self.get_sign_group()

        for count, group_name in enumerate(group_list):
            sys_log.update_progress('Creating Groups', count / len(group_list))
            data = {
                "groupName": group_name
            }

            # SIGN API to get existing groups
            res = self.api_post_group_request(data)

            if res.status_code == 201:
                self.logs['process'].info('{} Group Created...'.format(group_name))
                res_data = res.json()
                sign_group[group_name] = res_data['groupId']
            else:
                self.logs['error'].error("!! {}: Creating group error !! {}".format(group_name, res.text))
                self.logs['error'].error('!! Reason !! {}'.format(res.reason))

        sys_log.update_progress('Creating Groups', 1)

    def create_user_account(self, user):
        """
        This function will route the application to either provisioning a user with email verification, email
        suppression or auto provisioning turned off.
        :param user: dict[]
        :return:
        """

        if self.auto_provision and self.auto_password:
            self.auto_provision_email_suppression(user)
        elif self.auto_provision and not self.auto_password:
            self.auto_provision_email_verification(user)
        else:
            self.logs['process'].info('-- Auto provisioning turned off -- {} '.format(user['email']))

    def auto_provision_email_verification(self, user):
        """
        This function will provision a user, but the user account will need to be manually activated in order to user
        Adobe Sign. User will be moved to corresponding groups regardless if they've been activated.
        :param user: dict()
        :return:
        """

        payload = {
            "email": user['email'],
            "firstName": user['firstname'],
            "lastName": user['lastname']
        }

        res = self.api_post_user_request(payload)

        if res.status_code == 200:
            self.logs['process'].info('-- Account Email Activation Required -- {}'.format(user['email']))
        else:
            self.logs['error'].error("!! Account Creation Error !! {}".format(user['email']))
            self.logs['error'].error('!! Reason !! {}'.format(res.reason))

    def auto_provision_email_suppression(self, user):
        """
        This function will provision users with email activation suppression. However, a tech ops and support ticket
        will need to be created to edit backend settings. Please view user documentation for this information.
        :param user: dict[]
        :return: None
        """

        company = None
        phone = None
        title = None

        if "company" in user:
            company = user['company']

        if "mobile" in user:
            phone = user['mobile']

        if 'title' in user:
            title = user['title']

        payload = {
            "email": user['email'],
            "firstName": user['firstname'],
            "lastName": user['lastname'],
            "company": company,
            "password": self.auto_password,
            "phone": phone,
            "title": title
        }

        res = self.api_post_user_request(payload)

        if res.status_code == 200:
            self.logs['process'].info('-- Account Created/Activated -- {}'.format(user['email']))
        else:
            self.logs['error'].error("!! Account Creation Error !! {}".format(user['email']))
            self.logs['error'].error('!! Reason !! {}'.format(res.reason))

    def get_temp_header(self):
        """
        This function creates a temp header to push json payloads
        :return: dict()
        """

        temp_header = self.header
        temp_header['Content-Type'] = 'application/json'
        temp_header['Accept'] = 'application/json'

        return temp_header

    def get_user_info(self, user_info, group_id, group=None):
        """
        Retrieve user's information
        :param user_info: dict()
        :param group_id: str
        :param group: list[]
        :return: dict()
        """

        if self.connector == 'umapi':
            privileges = self.check_umapi_privileges(group, user_info)
        else:
            privileges = self.check_ldap_privileges(user_info)

        data = {
            "email": user_info['username'],
            "firstName": user_info['firstname'],
            "groupId": group_id,
            "lastName": user_info['lastname'],
            "roles": privileges
        }

        return data

    def get_user_status(self, user):
        """
        This function will get a list of all active users in Adobe Sign
        :return: list[]
        """
        res = requests.get(self.url + 'users/' + user['userId'], headers=self.header)
        user_data = res.json()

        if user_data['userStatus'] == 'ACTIVE':
            user_data['userId'] = user['userId']
            return user_data

        return None

    def get_active_user_list(self, user, queue):
        """
        This function will grab a list of active users in Adobe Sign.
        :param user: dict[]
        :param queue: Queue
        :return:
        """

        if user['email'].lower() != self.email.lower():
            res = self.api_get_user_by_id_request(user['userId'])
            user_data = res.json()

            if user_data['userStatus'] == 'ACTIVE':
                user_data['userId'] = user['userId']
                queue.put(user_data)

    def reactivate_account(self, user_id, email):
        """
        This function will reactivate a user account that's been inactive
        :param user_id: str
        :param email: str
        :return:
        """

        data = {}

        # SIGN API call to get user by ID
        res = self.api_get_user_by_id_request(user_id)
        if res.status_code == 200:
            data = res.json()

        if data['userStatus'] == "INACTIVE":
            payload = {"userStatus": "ACTIVE"}

            # SIGN API call to reactivate user account
            res = self.api_put_user_status_request(user_id, payload)
            if res.status_code == 200:
                self.logs['process'].info('-- Account: Reactivation -- {}'.format(email))
                self.logs['process'].info('-- Account: Reactivation -- {}'.format(email))
            else:
                self.logs['error'].error('!! Reactivation Error !! {}'.format(email))
                self.logs['error'].error('!! Reason !! {}'.format(res.reason))

    def deactivate_users(self, user):
        """
        This function will deactivate users if using LDAP as a connector.
        :param user: dict()
        :return:
        """

        # Create temp header and assign the payload
        data = {"userStatus": 'INACTIVE'}
        self.remove_user_privileges(user)
        res = self.api_put_user_status_request(user['userId'], data)
        if res.status_code == 200:
            self.logs['process'].info('-- Account Deactivated -- {}'.format(user['email']))
        else:
            self.logs['error'].error('!! Deactivation Error !! {}'.format(user['email']))
            self.logs['error'].error('!! Reason !! {}'.format(res.reason))

    def remove_user_privileges(self, user_info):
        """
        This function will remove all user privileges in order to be able to deactivate the user.
        :param user_info: dict()
        :return:
        """

        data = {
            "email": user_info['email'],
            "firstName": user_info['firstName'],
            "groupId": self.default_group,
            "lastName": user_info['lastName'],
            "roles": ['NORMAL_USER']
        }

        res = self.api_put_user_request(user_info['userId'], data)
        if res.status_code == 200:
            self.logs['process'].info('-- Privileges Removed -- {}'.format(user_info['email']))
        else:
            self.logs['error'].error('!! Privileges Removed Failed !! {}'.format(user_info['email']))
            self.logs['error'].error('!! Reason !! {}'.format(res.reason))

    @staticmethod
    def check_umapi_privileges(group, umapi_user_info):
        """
        This function will look through the configuration settings and give access privileges access to each user.
        :param group: list[]
        :param umapi_user_info: dict()
        :return:
        """

        # Set initial flags
        privileges = ["NORMAL_USER"]
        acc_admin_flag = False
        group_admin_flag = False

        for user_group in umapi_user_info['groups']:

            # Check to see if groups are part of an admin groups
            if len(user_group) >= 7 and '_admin_' in user_group[:7]:
                if user_group[7:] in umapi_user_info['productprofile']:
                    acc_admin_flag = True
                if user_group[7:] == group:
                    group_admin_flag = True

            # Determine the correct privileges to assign to the user
            if acc_admin_flag and group_admin_flag:
                privileges = ["ACCOUNT_ADMIN", "GROUP_ADMIN"]
            elif acc_admin_flag and not group_admin_flag:
                privileges = ["ACCOUNT_ADMIN"]
            elif not acc_admin_flag and group_admin_flag:
                privileges = ["GROUP_ADMIN"]
            else:
                privileges = ["NORMAL_USER"]

        return privileges

    @staticmethod
    def check_ldap_privileges(user_info):
        """
        This function will look through each user's membership profile to determine what admin rights they will have.
        :param user_info: dict()
        :return: list[]
        """

        # Filter out the user groups leaving just the admin right groups.
        group_list = user_info['groups']
        admin_rights = ['SIGN_GROUP_ADMIN', 'SIGN_ACCOUNT_ADMIN']
        admin_group_list = [group for group in group_list if any(word in group for word in admin_rights)]

        # Condition to check which privileges we should assign
        if 'SIGN_GROUP_ADMIN' in admin_group_list and 'SIGN_ACCOUNT_ADMIN' in admin_group_list:
            privileges = ["ACCOUNT_ADMIN", "GROUP_ADMIN"]
        elif 'SIGN_GROUP_ADMIN' in admin_group_list:
            privileges = ["GROUP_ADMIN"]
        elif 'SIGN_ACCOUNT_ADMIN' in admin_group_list:
            privileges = ["ACCOUNT_ADMIN"]
        else:
            privileges = ["NORMAL_USER"]

        return privileges

    def check_user_existence(self, user_list):
        """
        This function checks to see if the user exist in SIGN.
        :param user_list: list[dict()]
        :return: list[dict()]
        """

        sign_users = self.get_sign_users()
        updated_user_list = []

        for user in user_list:
            # If user email exist in SIGN we will skip the user
            if any(target_user['email'].lower() == user['email'].lower() for target_user in sign_users):
                pass
            else:
                self.create_user_account(user)

            for sign_user in sign_users:
                if user['email'].lower() in sign_user['email'].lower():
                    user['userId'] = sign_user['userId']
                    updated_user_list.append(user)
                else:
                    pass

        return updated_user_list

    def process_user(self, user):
        """
        This function will process each user and assign them to their Sign groups
        :param user: dict()
        :return:
        """
        temp_group = self.get_sign_group()

        # Sort the groups and assign the user to first group
        # Sign doesn't support multi group assignment at this time
        for group in sorted(user['groups']):
            group_id = temp_group.get(group)
            if group_id is not None:
                temp_payload = self.get_user_info(user, group_id, group)
                #     # temp_payload.update(ldap_connector.get_extra_ldap_attribute(name))
                self.reactivate_account(user['userId'], user['email'])
                res = self.api_put_user_request(user['userId'], temp_payload)
                if res.status_code == 200:
                    self.logs['process'].info('<< Information Updated >> {}'.format(user['email']))

                else:
                    self.logs['error'].error("!! Adding User To Group Error !! {} \n{}".format(user['email'], res.text))
                    self.logs['error'].error('!! Reason !! {}'.format(res.reason))
            break
