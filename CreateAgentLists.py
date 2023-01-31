from API_Driven_Migration.QualysCommon.QualysAPI import QualysAPI
from API_Driven_Migration.QualysCloudAgent import CloudAgentListGenerator
import json
import argparse
from sys import exit
from os import path
from getpass import getpass
import glob


def find_activation_key(key_data: list, key_name: str):
    for key in key_data:
        if 'title' not in key['AgentActKey'].keys():
            continue
        if key['AgentActKey']['title'] == key_name:
            return key
    return None


if __name__ == "__main__":
    # Script entry point

    # Help file for configuration file

    # Setup command line arguments
    parser = argparse.ArgumentParser()

    parser.add_argument('-u', '--source_user', help='Username for source subscription')
    parser.add_argument('-p', '--source_password', help='Password for source subscription '
                                                        '(use "-" to enter password interactively)')
    parser.add_argument('-U', '--target_user', help='Username for target subscription')
    parser.add_argument('-P', '--target_password', help='Password for target subscription'
                                                        '(use "-" to enter password interactively)')
    parser.add_argument('--enable_proxy', help='Enable proxy for Qualys Cloud Platform connection')
    parser.add_argument('--proxy_url', help='Proxy URL (e.g. https://10.10.10.10:8080)')
    parser.add_argument('--debug', action='store_true', help='Enable debugging output')
    parser.add_argument('--config_file', help='Configuration file')
    parser.add_argument('--validate_activation_keys', action='store_true', help='Validate target activation '
                                                                                'key is compatible with source '
                                                                                'activation key')

    # Process command line arguments
    args = parser.parse_args()

    # Validate command line arguments
    source_password = ''
    target_password = ''

    if args.source_user is None or args.source_user == '':
        print('ERROR: Source username is required')
        exit(1)

    if args.target_user is None or args.target_user == '':
        print('ERROR: Target username is required')
        exit(1)

    if args.source_password is None or args.source_password == '':
        print('ERROR: Source password is required')
        exit(1)

    if args.target_password is None or args.target_password == '':
        print('ERROR: Target password is required')
        exit(1)

    if args.source_password == '-':
        source_password = getpass('Enter password for source subscription user %s : ' % args.source_user)
    else:
        source_password = args.source_password

    if args.target_password == '-':
        target_password = getpass('Enter password for target subscription user %s : ' % args.target_user)
    else:
        target_password = args.target_password

    if args.enable_proxy and args.proxy_url is None:
        print('ERROR: --enable_proxy also requires --proxy_url')
        exit(1)

    if args.config_file is None or args.config_file == '':
        print('ERROR: No configuration file specified')
        exit(1)

    if not path.exists(args.config_file):
        print('ERROR: Configuration file not found (%s)' % args.config_file)
        exit(1)

    # Read the configuration file
    with open(args.config_file) as f:
        config = json.load(f)

    # Validate that we successfully loaded the configuration
    if config is None:
        print('ERROR: Could not read configuration file (%s)' % args.config_file)
        exit(1)

    # Validate the configuration
    # Check if the api_url exists for both source and target configurations
    if 'api_url' not in config['source'].keys():
        print('CONFIG ERROR: api_url not specified in source configuration')
        exit(2)

    if 'api_url' not in config['target'].keys():
        print('CONFIG ERROR: api_url not specified in target configuration')
        exit(2)

    # Check if the qualys_platform_api is blank
    if config['source']['api_url'] == '':
        print('CONFIG ERROR: api_url is blank in source configuration')
        exit(2)

    if config['target']['api_url'] == '':
        print('CONFIG_ERROR: api_url is blank in target configuration')
        exit(2)

    # Check if target activation keys exist
    if 'keys' not in config['target'].keys():
        print('CONFIG ERROR: keys not specified in target configuration')
        exit(2)

    # Check if target activation key is blank
    if config['target']['keys'] == "" or len(config['target']['keys']) == 0:
        print('CONFIG ERROR: keys is blank in target configuration')
        exit(2)

    # If there is no activation key mapping but multiple target keys, we cannot determine which agents
    # are to be migrated to which key, so exit
    if len(config['target']['keys']) > 1 and ('activation_key_map' not in config.keys() or
                                              len(config['activation_key_map']) == 0):
        print('CONFIG ERROR: Multiple target keys specified but no activation_key_map supplied')
        exit(2)

    # Setup the QualysAPI object which will handle all API requests
    source_api = QualysAPI(svr=config['source']['api_url'], usr=args.source_user, passwd=source_password,
                           debug=args.debug, enableProxy=args.enable_proxy, proxy=args.proxy_url)
    target_api = QualysAPI(svr=config['target']['api_url'], usr=args.target_user, passwd=target_password,
                           debug=args.debug, enableProxy=args.enable_proxy, proxy=args.proxy_url)

    # source_agents will store the agent data for each activation key by the key name
    source_agents = {}

    # target_agents will store the agent data for each target activation key by the key id
    target_agents = {}
    target_keys_data = None
    source_keys_data = None

    # single_target will be True if there is only one target activation key provided, false if multiple
    single_target: bool

    # targets_list will be a dictionary of the target activation key IDs and the assets to migrate to them
    targets_list = {}

    # If there are no source keys listed in the configuration file, we assume that all keys are in scope
    if 'keys' not in config['source'].keys() or len(config['source']['keys']) == 0:
        print('No source key data found, getting all activation keys from source subscription')
        # Get the source key data
        source_keys_data = CloudAgentListGenerator.getActivationKeys(source_api)

        # Build the source_keys with the name and activation key ID from the source data
        config['source']['keys'] = {}
        for key_data in source_keys_data:
            key_title = key_data['AgentActKey']['title']
            key_id = key_data['AgentActKey']['activationKey']
            config['source']['keys'][key_title] = key_id

    if args.validate_activation_keys:
        # Compare source and target activation keys for compatibility
        print('Starting activation key validation')
        print('Getting target activation keys')
        target_keys_data = CloudAgentListGenerator.getActivationKeys(api=target_api)
        if source_keys_data is None:
            print('Getting source activation keys')
            source_keys_data = CloudAgentListGenerator.getActivationKeys(api=source_api)

        # src_key is our source key data, tgt_key is our target key data
        src_key = None
        tgt_key = None

        # If only one target key is supplied, compare all source keys to it
        if len(config['target']['keys']) == 1:
            single_target = True
            print('Single target key detected, checking against all source keys for compatibility')
            target_key_name = config['target']['keys'][0]
            # Get the target key data
            tgt_key = find_activation_key(target_keys_data, target_key_name)

            if tgt_key is None:
                # We were not able to find the target key in the key data downloaded from the target subscription
                print('ERROR: Unable to find key %s in target key data' % target_key_name)
                exit(4)

            for source_key in config['source']['keys'].keys():
                # Obtain activation key data for each source key
                src_key = find_activation_key(source_keys_data, source_key)
                if src_key is None:
                    # We were not able to find the source key in the key data downloaded from the source subscription
                    print('ERROR: Could not find key %s in source key data' % source_key)
                    exit(4)

                # Perform the key comparison
                if not CloudAgentListGenerator.compareActivationKeys(src_key=src_key, tgt_key=tgt_key):
                    print('Target key (%s) does not match source key (%s)' % (target_key_name, source_key))
                    exit(5)
        else:
            single_target = False
            # Multiple target keys supplied, so use the activation_key_map in the configuration
            for source_key in config['activation_key_map'].keys():
                # Check to ensure source and target keys are in the source and target key configurations
                if source_key not in config['source']['keys'].keys():
                    print('KEY MAP ERROR: Source key %s does not exist in source keys configuration' % source_key)
                    exit(4)
                source_key_id = config['source']['keys'][source_key]

                if config['activation_key_map'][source_key] not in config['target']['keys'].keys():
                    print('KEY MAP ERROR: Target key %s does not exist in target keys configuration' %
                          config['activation_key_map'][source_key])
                    exit(4)

            # All is good, proceed with the compatibility check
            src_key = None
            tgt_key = None

            for source_key_name in config['activation_key_map'].keys():
                # Get the source and target key data
                target_key_name = config['activation_key_map'][source_key_name]
                src_key = find_activation_key(source_keys_data, source_key_name)
                if src_key is None:
                    print('ERROR: Unable to find key %s in source key data' % source_key_name)
                    exit(4)

                tgt_key = find_activation_key(target_keys_data, target_key_name)
                if tgt_key is None:
                    print('ERROR: Unable to find key %s in target key data' % target_key_name)
                    exit(4)

                if not CloudAgentListGenerator.compareActivationKeys(src_key=src_key, tgt_key=tgt_key):
                    print('ERROR: Target key (%s) does not match source key (%s)' % (target_key_name, source_key_name))
                    exit(5)

    # To make life easier, we convert the activation_key_map, which contains key names, to activation_id_map,
    # which contains activation key IDs
    activation_id_map = {}
    for source_key_name in config['activation_key_map']:
        target_key_name = config['activation_key_map'][source_key_name]
        src_key_id = config['source']['keys'][source_key_name]
        tgt_key_id = config['target']['keys'][target_key_name]
        activation_id_map[src_key_id] = tgt_key_id

    # Now we can get the assets from the source keys and map them to the target keys
    for source_key_id in activation_id_map.keys():
        assets = CloudAgentListGenerator.getAssets(api=source_api, key=source_key_id)
        if activation_id_map[source_key_id] not in targets_list.keys():
            targets_list[activation_id_map[source_key_id]] = assets
        else:
            targets_list[activation_id_map[source_key_id]].extend(assets)

    # Finally we can write the output files
    for target in targets_list.keys():
        windows_list = []
        linux_list = []
        incompatible_list = []
        platform: str
        for asset in targets_list[target]:
            platform = asset['HostAsset']['agentInfo']['platform']
            if platform.find('LINUX') > -1:
                linux_list.append(asset)
            elif platform.find('Windows') > -1 or platform.find('WINDOWS') > -1:
                windows_list.append(asset)
            else:
                incompatible_list.append(asset)

        CloudAgentListGenerator.outputList(windows_list, '%s_WINDOWS' % target)
        CloudAgentListGenerator.outputList(linux_list, '%s_LINUX' % target)
        CloudAgentListGenerator.outputList(incompatible_list, '%s_INCOMPATIBLE' % target)

