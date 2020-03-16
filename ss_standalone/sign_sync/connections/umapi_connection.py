import yaml
import umapi_client


class Umapi:

    def __init__(self, logs=None):

        self.logs = logs

        # read configuration file
        with open("config/connector-umapi.yml", 'r') as stream:
            try:
                self.config = yaml.load(stream, Loader=yaml.FullLoader)
            except yaml.YAMLError as exc:
                print(exc)

        # Create a connection with UMAPI
        self.conn = umapi_client.Connection(ims_host=self.config["server"]['ims_host'],
                                            org_id=self.config["enterprise"]["org_id"],
                                            user_management_endpoint="https://{}/v2/usermanagement".format(
                                                self.config['server']['host']),
                                            auth_dict=self.config["enterprise"])

    def query_users_in_groups(self, groups, account_type):
        """
        This function makes a query for users in a given list of groups.
        :param groups: list[]
        :param account_type: str
        :return: dict()
        """

        user_list = list()

        # Iterate through the group list and make request to get user data within that group
        for product_profile in groups:
            res = umapi_client.UsersQuery(self.conn, in_group=product_profile, direct_only=False)
            users = res.all_results()

            for user in users:
                if account_type == 'all':
                    user['productprofile'] = product_profile
                    user_list.append(user)
                elif user['type'] == account_type:
                    user['productprofile'] = product_profile
                    user_list.append(user)

        return user_list

    def query_product_profile(self):
        """
        This function makes a query to find groups within UMAPI that's a product profile group.
        :return: list[]
        """
        product_profile_list = list()
        groups = umapi_client.GroupsQuery(self.conn)

        for group in groups:
            if group['type'] == 'PRODUCT_PROFILE':
                product_profile_list.append(group['groupName'])

        return product_profile_list

    def query_user_groups(self):
        """
        This function will query UMAPI for group names.
        :return: list[]
        """

        group_list = list()
        user_groups = umapi_client.UserGroupsQuery(self.conn)

        for user_group in user_groups:
            group_list.append(user_group['groupName'])

        return group_list
