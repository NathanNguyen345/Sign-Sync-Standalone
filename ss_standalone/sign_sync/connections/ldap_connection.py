import ldap
import ldap.controls.libldap
import yaml
import itertools
import multiprocessing


class LdapConfig:

    def __init__(self, logs=None):

        self.logs = logs

        # create config file
        with open("config/connector-ldap.yml") as stream:
            try:
                self.ldap_config_yml = yaml.load(stream, Loader=yaml.FullLoader)
            except yaml.YAMLError as exc:
                print(exc)

        # read ldap server settings
        self.address = self.ldap_config_yml["host"]
        self.base_dn = self.ldap_config_yml['base_dn']

        # read ldap credential
        self.username = self.ldap_config_yml["username"]
        self.password = self.ldap_config_yml["password"]

        # connection
        self.conn = self.authenticate()

    def get_conn(self):
        """
        This function gets the connection for LDAP
        :return: LDAP connection
        """

        return self.conn

    def authenticate(self):
        """
        This function will authenticate a connection with the LDAP server.
        :return:
        """

        # set options for LDAP connection
        self.conn = ldap.initialize('{}'.format(self.address))
        self.conn.protocol_version = 3
        self.conn.set_option(ldap.OPT_REFERRALS, 0)

        # attempt to connect to the LDAP server
        try:
            self.conn.simple_bind_s(self.username, self.password)
            return self.conn
        except ldap.INVALID_CREDENTIALS:
            self.logs['error'].error("Invalid LDAP Credentials...")
        except ldap.SERVER_DOWN:
            self.logs['error'].error("Server Is Down...")

    def disconnect(self):
        """
        This function will disconnect the application from the LDAP server
        :return:
        """

        try:
            self.conn.unbind_s()
        except Exception:
            self.logs['error'].error("Failed to unbind from LDAP server...")

    def get_base_dn_setting(self):
        """
        This function will return the base dn for the ldap.
        :return: str
        """

        return self.base_dn

    def get_ldap_groups_query(self, sign_obj, sys_log=None):
        """
        This function will perform a query to the ldap to find all groups.
        :param sign_obj: dict()
        :param sys_log: LOGGER
        :return: list[]
        """

        new_base_dn = 'OU={}, {}'.format(sign_obj.get_adobe_ou(), self.base_dn)
        ignore_groups = ['SIGN_GROUP_ADMIN', 'SIGN_ACCOUNT_ADMIN']
        group_list = list()

        # Query for a list and decode each group to a str
        group_query = self.get_ldap_query_paged(new_base_dn)

        for count, group in enumerate(group_query):
            sys_log.update_progress('Group Query', count / len(group_query))
            if group[1]['name'][0].decode('utf-8') not in ignore_groups and 'cn' in group[1]:
                group_list.append(group[1]['cn'][0].decode('utf-8'))
        sys_log.update_progress('Group Query', 1)

        return group_list

    def get_ldap_users_in_groups(self, groups, sign_obj, sys_log=None):
        """
        This function will return a list of users within all targeted groups.
        :param groups: list[]
        :param sign_obj: dict()
        :param sys_log: LOGGER
        :return: list[]
        """

        new_base_dn = 'OU={}, {}'.format(sign_obj.get_adobe_ou(), self.base_dn)
        user_list = []
        temp_name = ""

        # Query each group to find the users in each group
        for i, group in enumerate(groups):
            sys_log.update_progress('User Query', i / len(groups))
            user_in_group = self.conn.search_s(new_base_dn, ldap.SCOPE_SUBTREE, "(CN={})".format(group),
                                               attrlist=['member'])
            group_dn = user_in_group[0][0]
            user_in_group = user_in_group[0][1]

            # This is the option if there's 1500+ users in a group
            if len(user_in_group) == 2:
                for attr_name in user_in_group:
                    if ';range=' in attr_name:
                        actual_attr_name, range_stmt = attr_name.split(';')
                        bound_lower, bound_upper = [
                            int(x) for x in range_stmt.split('=')[1].split('-')
                        ]

                        step = bound_upper - bound_lower + 1

                        while True:
                            attr_next = '%s;range=%d-%d' % (
                                actual_attr_name, bound_lower, bound_upper
                            )
                            temp_dict = self.conn.search_s(group_dn, ldap.SCOPE_SUBTREE, attrlist=[attr_next])
                            temp_dict = temp_dict[0][1]

                            for temp_attr in temp_dict:
                                temp_name = temp_attr
                                user_list.append(temp_dict[temp_name])

                            if temp_name.endswith('-*'):
                                break

                            bound_lower = bound_upper + 1
                            bound_upper += step
            elif not user_in_group:
                pass
            else:
                user_list.append(user_in_group['member'])

        sys_log.update_progress('User Query', 1)
        flatten_user_list = self.flatten_list(user_list)

        return flatten_user_list

    def get_ldap_query_paged(self, base_dn, target_object=None):
        """
        This method will perform LDAP query in pages. The size limit can be set in the ldap.yml file.
        :param base_dn: str()
        :param target_object: str()
        :return: list[]
        """

        connection = self.get_conn()
        search_page_size = self.ldap_config_yml['search_page_size']
        query_list = []

        if target_object is None:
            target_object = '*'

        msgid = None
        try:
            lc = ldap.controls.libldap.SimplePagedResultsControl(True, size=search_page_size, cookie='')

            has_next_page = True
            while has_next_page:
                if msgid is not None:
                    result_type, response_data, _rmsgid, serverctrls = connection.result3(msgid)
                    query_list.append(response_data)
                    msgid = None
                    pctrls = [c for c in serverctrls
                              if c.controlType == ldap.controls.libldap.SimplePagedResultsControl.controlType]
                    if not pctrls:
                        self.logs['process'].error("Server ignored RFC 2696 control...")
                        has_next_page = False
                    else:
                        lc.cookie = cookie = pctrls[0].cookie
                        if not cookie:
                            has_next_page = False
                if has_next_page:
                    msgid = connection.search_ext(base_dn, ldap.SCOPE_SUBTREE, serverctrls=[lc])

            merged_list = list(itertools.chain(*query_list))

            return merged_list

        except GeneratorExit:
            if msgid is not None:
                connection.abandon(msgid)
            raise

    def ldap_user_mp(self, user_list, group_map, sys_log=None):
        """
        This function is the multiprocessor for getting batch users from LDAP. This is performed if you're trying to
        query more than 1500+ users. LDAP has user query limitation.
        :param user_list: list[dict()]
        :param group_map: list()
        :param sys_log: LOGGER
        :return: list[dict()]
        """

        batch_size = 225

        # Setting up mp manager for return
        manager = multiprocessing.Manager()

        temp_user_list = []
        filters = ['memberOf', 'mail', 'givenName', 'sn']

        test_list = list(self.chunks(user_list, batch_size))

        for count, user_group in enumerate(test_list):
            sys_log.update_progress('Formatting Users', count / len(test_list))
            return_dict = manager.dict()

            for process_number, user in enumerate(user_group):
                user_info_decoded = user.decode('utf-8')
                user_info = self.conn.search_s(user_info_decoded, ldap.SCOPE_SUBTREE, attrlist=filters)[0][1]

                self.create_user_json(user_info, group_map, process_number, return_dict)

            temp_user_list.append(return_dict.values())
        temp_user_list = self.flatten_list(temp_user_list)
        sys_log.update_progress('Formatting Users', 1)

        return temp_user_list

    @staticmethod
    def chunks(user_list, batch):
        """
        This function will split an array of dicts into manageable chunk size.
        :param user_list: list[dict()]
        :param batch: int
        :return:
        """

        for i in range(0, len(user_list), batch):
            yield user_list[i:i + batch]

    @staticmethod
    def create_user_json(user_info, group_map, process_number, return_dict):
        """
        This function will format the ldap information into a json format similar to the one we get
        from UMAPI.
        :param user_info: dict()
        :param group_map: list()
        :param process_number: int
        :param return_dict: dict()
        :return: dict()
        """

        group_list = list()

        # Split the user's group into a list and decode it
        for group in user_info['memberOf']:
            group_list.append(group.decode('utf-8').split(',')[0][3:])

        # Group mapping
        if group_map:
            temp_group_list = list()
            for group in group_list:
                if group == "SIGN_ACCOUNT_ADMIN" or group == "SIGN_GROUP_ADMIN":
                    temp_group_list.append(group)
                elif group in group_map:
                    temp_group_list.append(group_map[group])
            group_list = temp_group_list

        # Format it to an a standardize json format
        data = {
            "email": user_info['mail'][0].decode('utf-8'),
            "firstname": user_info['givenName'][0].decode('utf-8'),
            "groups": group_list,
            "lastname": user_info['sn'][0].decode('utf-8'),
            "username": user_info['mail'][0].decode('utf-8'),
            }

        return_dict[process_number] = data

    def get_extra_ldap_attribute(self, user_name):
        """
        This function will get extra ldap information if requested
        :param user_name: str
        :return: dict()
        """

        base_dn = "CN=Users, {}".format(self.base_dn)
        base_dn_result = self.conn.search_s(base_dn, ldap.SCOPE_SUBTREE, "(CN={})".format(user_name))
        user_data = base_dn_result[0][1]

        temp_user_info = dict()
        if 'company' in user_data:
            temp_user_info['company'] = user_data['company'][0].decode("utf-8")
        if 'title' in user_data:
            temp_user_info['title'] = user_data['title'][0].decode("utf-8")

        return temp_user_info

    @staticmethod
    def flatten_list(target_list):
        """
        This function will flatten a list of dict into a single list of dict elements
        :param target_list: list[dict()]
        :return: list[]
        """
        flatten_list = [item for sublist in target_list for item in sublist]

        return flatten_list

    @staticmethod
    def check_group_mapping(group_list, group_map):
        """
        This function checks to see if group mapping is enabled. If so, it will replace all the mappings prior to group
        creation.
        :param group_list: list()
        :param group_map: dict()
        :return: list()
        """

        if group_map:

            temp_list = list()

            for group_name in group_list:
                if group_name in group_map:
                    temp_list.append(group_map[group_name])

            return temp_list
        else:
            return group_list
