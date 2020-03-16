import time
import datetime
import json
import os
import sys
import sign_sync.logger
import sign_sync.connections.sign_connection
import sign_sync.connections.umapi_connection
import sign_sync.connections.ldap_connection
import sign_sync.thread_functions
from queue import Queue


LOGGER = sign_sync.logger.Log()


def main():

    data_connector = None
    log_file = LOGGER.get_log()
    
    # Instantiate Sign object & validate
    sign_obj = sign_sync.connections.sign_connection.Sign(log_file)
    sign_obj.validate_integration_key(sign_obj.header, sign_obj.url)
    sign_groups = sign_obj.get_sign_group()
    
    # Get all of the configuration and connector needed to run the application
    if sign_obj.connector == 'ldap':
        data_connector = sign_sync.connections.ldap_connection.LdapConfig()
    elif sign_obj.connector == 'umapi':
        data_connector = sign_sync.connections.umapi_connection.Umapi(log_file)
    
    run(log_file, sign_obj, sign_groups, data_connector)


def run(logs, sign_obj, sign_groups, connector):
    """
    This is the run function of the application.
    :param logs: dict()
    :param sign_obj: dict()
    :param sign_groups: list[]
    :param data_connectors: dict()
    """

    print('-- Time of Sync {} --'.format(datetime.datetime.now().strftime('%m-%d-%Y %H:%M:%S')))
    logs['process'].info('------------------------------- Starting Sign Sync -------------------------------')
    start_time = time.time()

    # Get Users and Groups information from our connector
    group_list, user_list = get_data_from_connector(sign_obj, connector)

    # Format the users and create groups that don't exist in Adobe Sign
    LOGGER.update_progress('Sync Phase', 1 / 4)
    user_that_exist_in_sign = sign_obj.check_user_existence(user_list)
    user_to_be_updated = get_user_to_be_updated_list(sign_obj, user_that_exist_in_sign)
    groups_not_found_in_sign = [group for group in group_list if group not in sign_groups]
    if groups_not_found_in_sign:
        sign_obj.create_sign_group(group_list, LOGGER)

    # Sync users into their groups
    LOGGER.update_progress('Sync Phase', 2 / 4)
    do_threading(user_to_be_updated, sign_obj.process_user)

    # This is when we will start the deactivation phase
    LOGGER.update_progress('Sync Phase', 3 / 4)
    sign_users = sign_obj.get_sign_users()
    active_sign_user_list = do_threading_with_return(sign_users, sign_obj.get_active_user_list)

    deactivate_list = []
    for target_user in active_sign_user_list:
        if not any(user['email'].lower() == target_user['email'].lower() for user in user_that_exist_in_sign):
            deactivate_list.append(target_user)

    if len(deactivate_list) > 0:
        do_threading(deactivate_list, sign_obj.deactivate_users)

    # Save to cache file
    if sign_obj.cache_mode:
        save_cache(sign_obj, user_that_exist_in_sign)

    LOGGER.update_progress('Sync Phase', 4/4)
    print('-- Execution Time: {} --'.format(time.time() - start_time))
    logs['process'].info('------------------------------- Ending Sign Sync ---------------------------------')

def get_data_from_connector(sign_obj, data_connector):
    """
    This function gets user data the main connector
    :param sign_obj: obj
    :param data_connector: dict()
    :return: dict(), dict()
    """

    # Get Users and Groups information from our connector
    if sign_obj.connector == 'umapi':
        group_list = data_connector.query_user_groups()
        user_list = data_connector.query_users_in_groups(sign_obj.get_product_profile(), sign_obj.account_type)
    else:
        group_list = data_connector.get_ldap_groups_query(sign_obj, LOGGER)
        temp_list = data_connector.get_ldap_users_in_groups(group_list, sign_obj, LOGGER)
        user_list = data_connector.ldap_user_mp(temp_list, LOGGER)

    return (group_list, user_list)


def do_threading(user_list, func):
    """
    This function will be start up a threading process.
    :param user_list: list[]
    :param func: FUNCTION
    :return:
    """

    queue = Queue()
    for x in range(200):
        worker = sign_sync.thread_functions.ThreadWorker(queue, func)
        worker.start()

    for user in user_list:
        queue.put(user)

    queue.join()


def do_threading_with_return(user_list, func):
    """
    This function will start up a Thread process and be able to return a list.
    :param user_list: list[]
    :param func: FUNCTION
    :return: list[]
    """

    queue = Queue()
    return_queue = Queue()
    for x in range(200):
        worker = sign_sync.thread_functions.ThreadWithReturnValue(queue, return_queue, func)
        worker.start()

    for user in user_list:
        queue.put(user)

    queue.join()

    return_list = list(return_queue.queue)

    return return_list


def get_user_to_be_updated_list(sign_obj, temp_user_list):
    """
    This function will load the cache file and find the the difference between the current state and the previous
    state of the connector.
    :param sign_obj: dict()
    :param temp_user_list: list[]
    :return: list[]
    """

    file_path = 'cache/user_cache_{}.json'.format(sign_obj.connector)

    if os.path.isfile(file_path) and sign_obj.cache_mode:
        user_to_be_updated = do_threading_with_return(temp_user_list, find_difference)
    else:
        user_to_be_updated = temp_user_list

    return user_to_be_updated


def find_difference(user, difference_list):
    """
    This function will find the difference between the current sync and the previous sync state.
    :param user: dict()
    :param difference_list: list[]
    :return: list[dict()]
    """

    file_path = 'cache/user_cache_ldap.json'

    if os.path.isfile(file_path):
        cache = load_cache(file_path)
    else:
        cache = load_cache('cache/user_cache_umapi.json')

    if user not in cache:
        difference_list.put(user)

    return difference_list


def save_cache(sign_obj, user_list):
    """
    This function will save the cache file.
    :param sign_obj: dict()
    :param user_list: list[]
    """

    file_path = 'cache/user_cache_{}.json'.format(sign_obj.connector)
    with open(file_path, 'w') as file:
        json.dump(user_list, file)


def load_cache(file_path):
    """
    This function will load the cache from the previous sync state.
    :param file_path: str()
    """

    file_path = file_path
    with open(file_path, 'r') as file:
        json_data = json.load(file)

    return json_data


def update_progress(job_title, progress):
    """
    This function will print the progress for each step.
    :param job_title: str()
    :param progress: int
    """

    length = 20
    block = int(round(length*progress))
    msg = "\r{0}: [{1}] {2}%".format(job_title, "#"*block + "-"*(length-block), round(progress*100, 2))
    if progress >= 1:
        msg += " DONE\r\n"
    sys.stdout.write(msg)
    sys.stdout.flush()


if __name__ == '__main__':
    main()