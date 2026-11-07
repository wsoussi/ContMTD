from gen_al_combinations_w_veryhigh import set_config_file
import os, sys
import logging
import time
import subprocess


# Configure the logging module
logging.basicConfig(
    filename='/home/ubuntu/dyn_migration_script.log',  # Log file name
    filemode='a',  # Append mode
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.DEBUG  # Set the logging level
)
# Create a logger.info object
logger = logging.getLogger(__name__)

remote_locust_client = "ubuntu@10.0.0.152"
remote_node3 = "ubuntu@10.10.10.9"
ssh_node3 = "ubuntu@10.0.0.31"
gateway_ip = "10.0.0.152"


# 26 valid combinations
valid_combos = [
    "mmmm",
    "vvvl",
    "vvvm",
    "vvvh",
    "vmmh",
    "vmhh",
    "vhvl",
    "vhvm",
    "vhvh",
    "vhhm",
    "vhhh",
    "mmmh",
    "mmhm",
    "mmhh",
    "mhhm",
    "hvv0",
    "hvvl",
    "hmhh",
    "hhv0",
    "hhvl",
    "hhvh"
  ]

real_to_defacto_valid = {
    'vvm0': 'mmm0',
    'vvml': 'mmml',
    'vvh0': 'mhh0',
    'vvhl': 'mhhl',
    'vvhm': 'hhhm',
    'vmhm': 'hmmm',
    'mmml': 'mhvl',
    'mmh0': 'mhv0',
    'mhm0': 'mvv0',
    'mhml': 'mvvl',
    'hvvh': 'hhhh',
    'hvmh': 'hmmh',
    'hhmm': 'hvvm'
}

low_net = 10 # 1 locust user, 97.6 req/s (avg. resp. time 1ms)
mid_net = 100 # 100 locust users, 957 req/s (avg. resp. time 2ms)
high_net = 350 # 350 locust users, 3360 req/s

def net_client_for_migration(combination, intensity, pre, post, count):
    locust_users = 0
    if intensity == "l":
        locust_users = low_net
    elif intensity == "m":
        locust_users = mid_net
    elif intensity == "h":
        locust_users = high_net
    # start the non-blocking locust client with cmd
    command = "locust -f ~/locust_client/simple_locust.py --headless -u " + str(locust_users) + " -r 100 --host http://10.0.8.3:23456 --csv=/home/ubuntu/dyn_logs_migrations/"+ combination + "_locust_log_" + str(pre) + str(post) + str(count)
    try:
        subprocess.check_call(f"ssh {remote_locust_client} \"{command}\" &", stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, shell=True)
        logger.info("Locust client started successfully.")
    except subprocess.CalledProcessError as e:
        logger.error("Error in starting Locust client.")


def stop_net_client():
    command = "killall -9 locust"
    try:
        subprocess.check_call(f"ssh {remote_locust_client} \"{command}\"", shell=True)
        logger.info("Locust client stopped successfully.")
    except subprocess.CalledProcessError as e:
        logger.error("Error in stopping Locust client.")


def start_dynintensive_container():
    cmd = "/home/ubuntu/contMTD/combos_migration/shell_start.sh"
    result = subprocess.run(cmd, stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, shell=True)
    if result.returncode != 0:
        logger.error(f"Error in starting container: {result.stderr}")
        print("Something did not work. Exiting!")
        return False
    msg = "dynintensive container started successfully."
    logger.info(msg)
    return True


# def start_dynintensive_container2():
#     try:
#         subprocess.check_call(
#             "runc run -d --bundle /runc/containers/dynintensive dynintensive &>/dev/null </dev/null", stdin=subprocess.DEVNULL,
#             stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, shell=True)
#         msg = "dynintensive container started successfully."
#         logger.info(msg)
#     except subprocess.CalledProcessError as e:
#         logger.error("Error in starting container.")


def container_is_running():
    process = subprocess.Popen("runc list", stdin=subprocess.DEVNULL, stdout=subprocess.PIPE, stderr=subprocess.PIPE, shell=True)
    out, err = process.communicate()
    running = False
    if "running" in str(out):
        logger.info("Container is running")
        running = True
    else:
        logger.error("Container not running.")
    return running

def container_exists():
    process = subprocess.Popen("runc list", stdin=subprocess.DEVNULL, stdout=subprocess.PIPE, stderr=subprocess.PIPE, shell=True)
    out, err = process.communicate()
    if "dynintensive" in str(out):
        return True
    else:
        return False


def container_is_running_remotely():
    command = "sudo runc list"
    running = False
    try:
        process = subprocess.Popen(f"ssh {remote_node3} \"{command}\"", stdin=subprocess.DEVNULL, stdout=subprocess.PIPE, stderr=subprocess.PIPE, shell=True)
        out, err = process.communicate()
        if "running" in str(out):
            running = True
    except subprocess.CalledProcessError as e:
        logger.error("Error: ", str(e))
    return running


def container_exists_remotely():
    command = "sudo runc list"
    running = False
    try:
        process = subprocess.Popen(f"ssh {remote_node3} \"{command}\"", stdin=subprocess.DEVNULL, stdout=subprocess.PIPE, stderr=subprocess.PIPE, shell=True)
        out, err = process.communicate()
        # print(str(out))
        if "dynintensive" in str(out):
            return True
    except subprocess.CalledProcessError as e:
        logger.error("Error: ", str(e))
    return running

def migrate_container(combination, dest="10.10.10.9", pre_dump = False, post_dump = False, with_rootfs = False):
    # cmd = "/home/ubuntu/contMTD/combos_migration/shell_migrate.sh %s %s %s" % (dest, str(pre_dump), str(post_dump))
    try:
        cmd = "/home/ubuntu/contMTD/venv/bin/python /home/ubuntu/contMTD/migrate.py dynintensive %s %s %s %s %s" % (dest, str(pre_dump), str(post_dump), str(with_rootfs), combination)
        process = subprocess.Popen( cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, shell=True)
        msg = "Migration done from node1 to %s for combination %s with pre_dump: %s and post_dump: %s." % (dest, combination, str(pre_dump), str(post_dump))
        logger.info(msg)
        print(msg)
        out, err = process.communicate(timeout=60)
        # id out is empty raise an error
        if not out:
            logger.error("Error in migration process")
            print(("Error in migration process:" + str(err)))
            return False
    except Exception as e:
        logger.error("Error or timeout in migration process: " + str(e))
        return False
    out_per_line = str(out).split("\\n")
    for line in out_per_line:
        logger.info(line)
        print(line)
    # if "restored dynintensive successfully" not in str(out):
    if "Total parallel phase" not in str(out): # this one is less strict (for now)
        return False
    return True


def delete_dynintensive_container():
    try:
        subprocess.check_call('runc kill dynintensive SIGKILL', shell=True)
        logger.info("Dynintensive killed.")
    except subprocess.CalledProcessError as e:
        logger.error("Error in killing container. The container is probably already stopped.")
    for i in range(10):
        running = container_is_running()
        if running:
            time.sleep(0.5)
        else:
            break
    try:
        subprocess.check_call('runc delete dynintensive', shell=True)
        logger.info("Dynintensive removed.")
    except subprocess.CalledProcessError as e:
        logger.error("Error in deleting container. The container is probably already deleted.")
    for i in range(10):
        exist = container_exists()
        if exist:
            time.sleep(0.5)
        else:
            break
    # sometimes the container is not deleted or it is but has residuals. Kill all CRIU processes to avoid this
    try:
        subprocess.check_call("killall -9 criu", shell=True)
        logger.info("CRIU killed in node1.")
    except subprocess.CalledProcessError as e:
        # logger.error("Error in killing CRIU in node1.")
        pass
    # sometimes you need to resume the container and try again
    if container_exists():
        try:
            subprocess.check_call('runc resume dynintensive', shell=True)
            logger.info("Dynintensive resumed to try and remove it.")
        except subprocess.CalledProcessError as e:
            logger.error("Error in resuming container.")
            try:
                subprocess.check_call('runc kill dynintensive SIGKILL', shell=True)
                logger.info("Dynintensive killed.")
            except subprocess.CalledProcessError as e:
                logger.error("Error in killing container. The container is probably already stopped.")
            for i in range(10):
                running = container_is_running()
                if running:
                    time.sleep(0.5)
                else:
                    break
            try:
                subprocess.check_call('runc delete dynintensive', shell=True)
                logger.info("Dynintensive removed.")
            except subprocess.CalledProcessError as e:
                logger.error("Error in deleting container. The container is probably already deleted.")
            for i in range(10):
                exist = container_exists()
                if exist:
                    time.sleep(0.5)
                else:
                    break



def delete_dynintensive_remotely():
    remote_command = 'sudo runc kill dynintensive SIGKILL'
    try:
        subprocess.check_call(f"ssh {remote_node3} \"{remote_command}\"", shell=True)
        logger.info("Dynintensive killed in node3.")
    except subprocess.CalledProcessError as e:
        logger.error("Error in killing remote container. The container is probably already stopped.")
    for i in range(10):
        running_remotely = container_is_running_remotely()
        if running_remotely:
            time.sleep(0.5)
        else:
            break
    remote_command = 'sudo runc delete dynintensive'
    try:
        subprocess.check_call(f"ssh {remote_node3} \"{remote_command}\"", shell=True)
        logger.info("Dynintensive removed in node3.")
    except subprocess.CalledProcessError as e:
        logger.error("Error in deleting remote container. The container is probably already deleted.")
    for i in range(10):
        exist = container_exists_remotely()
        if exist:
            time.sleep(0.5)
        else:
            break
    # sometimes the container is not deleted or it is but has residuals. Kill all CRIU processes to avoid this
    remote_cmd = "sudo killall -9 criu"
    try:
        subprocess.check_call(f"ssh {remote_node3} \"{remote_cmd}\"", shell=True)
        logger.info("CRIU killed in node3.")
    except subprocess.CalledProcessError as e:
        # logger.error("Error in killing CRIU in node3.")
        pass


def transfer_ip_back(ip_addr="10.0.8.3"):
    dest_mac_addr = "fa:16:3e:f7:f8:6b" # node1
    cmd = "ssh -i /home/ubuntu/.ssh/id_rsa ubuntu@%s 'sudo arp -s %s %s'" % (gateway_ip, ip_addr, dest_mac_addr)
    ret = os.system(cmd)
    logger.info("IP transfer back to node1")
    if ret != 0:
        print("Something did not work. Exiting!")
        sys.exit(1)


def transfer_config_json():
    cmd = "scp /runc/containers/dynintensive/config.json root@10.10.10.9:/runc/containers/dynintensive/config.json"
    try:
        subprocess.check_call(cmd, shell=True)
    except subprocess.CalledProcessError as e:
        logger.error("Error in copying config.json.")


def migration_experiment_per_combo(i, combination, dest="10.10.10.9", last_type=""):
    # Set the runc config.json configuration file based on the combination
    set_config_file(combination[0], combination[1], combination[2])
    time.sleep(2)
    # transfer the config.json to destination node
    transfer_config_json()
    for pre in [False, True]:
        for post in [False, True]:
            if last_type:
                if last_type == "cold":
                    if not pre and not post:
                        continue
                if last_type == "post":
                    if not pre and not post:
                        continue
                    elif not pre and post:
                        continue
                if last_type == "pre":
                    if pre and not post:
                        continue
                    elif not pre and post:
                        continue
                    elif not pre and not post:
                        continue
            fail_count = 0
            with_rootfs = False
            migrated = False
            while fail_count < 10 and not migrated:  # try up to 10 times if migration fails
                # Delete the old dynintensive container if any remains
                if container_exists():
                    delete_dynintensive_container()
                    time.sleep(1)
                # transfer the IP back to node1
                transfer_ip_back()
                # run the container and wait for it to start
                started = start_dynintensive_container()
                time.sleep(5)
                # check from runc list that the container is running
                if started and container_is_running():
                    # start the locust client
                    if combination[3] != "0":
                        net_client_for_migration(combination, combination[3], pre, post, i)
                        time.sleep(6)  # wait until container runtime stabilizes with requests
                    # if fail_count is a multiple of 4 (fifth iteration) transfer the rootfs
                    if fail_count % 3 == 0:
                        with_rootfs = True
                    # perform the migration
                    migrated = migrate_container(combination, dest, pre, post, with_rootfs)
                    with_rootfs = False
                    time.sleep(3)
                    if container_is_running_remotely():
                        logger.info("Container is running remotely")
                        time.sleep(5)  # wait for locust requests stats to stabilize
                    else:
                        fail_count += 1
                        migrated = False
                    # stop the locust client
                    if combination[3] != "0":
                        stop_net_client()
                    # stop remote container
                    delete_dynintensive_remotely()
                    time.sleep(3)
                else:
                    logger.error("Container not running. Next combination.")

def get_last_iter_and_comb():
    #get the last iteration and combination
    cmd = 'cat /home/ubuntu/dyn_comb_script.log_old | grep "Modified config.json for combination:mmmm" | wc -l'
    # run the command
    process = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, shell=True)
    out, err = process.communicate()
    last_iter = int(out)

    with open("/home/ubuntu/migration.json", "r") as f:
        lines = f.readlines()
        # read lines from the last one to the first one
        for line in reversed(lines):
            # if line contains "}," and the following line contains "{"
            if '"migration":' in line:
                migration = line.split(": ")[1].strip()
                migration = migration.replace(',', '')
                migration = migration.replace('"', '')
            elif '"net":' in line:
                netval = line.split(": ")[1].strip()
                netval = netval.replace(',', '')
                netval = netval.replace('"', '')
            elif '"disk":' in line:
                diskval = line.split(": ")[1].strip()
                diskval = diskval.replace(',', '')
                diskval = diskval.replace('"', '')
            elif '"ram":' in line:
                ramval = line.split(": ")[1].strip()
                ramval = ramval.replace(',', '')
                ramval = ramval.replace('"', '')
            elif '"cpu":' in line:
                cpuval = line.split(": ")[1].strip()
                cpuval = cpuval.replace(',', '')
                cpuval = cpuval.replace('"', '')
                break
    last_comb = cpuval + ramval + diskval + netval
    return last_iter, last_comb, migration

def reboot():
    # reboot the remote node3 and wait execution to finish
    try:
        subprocess.check_call(f"ssh {remote_node3} 'sudo reboot'", shell=True)
    except subprocess.CalledProcessError as e:
        logger.error("Exit status -1 in rebooting remote node3 but the node is probably rebooted.")
    time.sleep(2)
    # reboot the local node1
    subprocess.Popen("sudo reboot", shell=True)


def reset_net():
    # set down the network interface ens8 then up again
    try:
        subprocess.check_call("ifconfig ens8 down", shell=True)
        subprocess.check_call("ifconfig ens7 down", shell=True)
        time.sleep(2)
        subprocess.check_call("ip addr flush dev ens8", shell=True)
        subprocess.check_call("ip addr flush dev ens7", shell=True)
        time.sleep(2)
        subprocess.check_call("ifconfig ens8 up", shell=True)
        subprocess.check_call("ifconfig ens7 up", shell=True)
        time.sleep(2)
    except subprocess.CalledProcessError as e:
        logger.error("Error in resetting network interface.")
        print("Error in resetting network interface.")
    # do the same for the remote node3
    try:
        subprocess.check_call(f"ssh {remote_node3} 'sudo ifconfig ens4 down'", shell=True)
        time.sleep(2)
        subprocess.check_call(f"ssh {remote_node3} 'sudo ifconfig ens8 down'", shell=True)
        time.sleep(3)
        subprocess.check_call(f"ssh {remote_node3} 'sudo ip addr flush dev ens4'", shell=True)
        time.sleep(2)
        subprocess.check_call(f"ssh {remote_node3} 'sudo ip addr flush dev ens8'", shell=True)
        time.sleep(3)
        subprocess.check_call(f"ssh ubuntu@10.0.0.31 'sudo ifconfig ens4 up'", shell=True)
        time.sleep(2)
        subprocess.check_call(f"ssh ubuntu@10.0.0.31 'sudo ifconfig ens8 up'", shell=True)
        time.sleep(3)
        logger.info("Interfaces reset in remote node3.")
    except subprocess.CalledProcessError as e:
        logger.error("Error in resetting network interface in remote node3.")
        print("Error in resetting network interface in remote node3.")



def check_remote_runs():
    # check if the remote node3 by using whoami command
    cmd = "whoami"
    accessible = False
    while not accessible:
        try:
            process = subprocess.Popen(f"ssh {remote_node3} \"{cmd}\"", stdout=subprocess.PIPE, stderr=subprocess.PIPE, shell=True)
            out, err = process.communicate()
            if "ubuntu" not in str(out) and "root" not in str(out):
                logger.error("Remote node3 is not accessible.")
                print("Remote node3 is not accessible. Exiting!")
            else:
                accessible = True
        except subprocess.CalledProcessError as e:
            logger.error("Error in checking remote node3. Retrying.")
            time.sleep(2)
    logger.info("node3 accessible")


if __name__ == '__main__':
    nodes = {"node1": "10.0.0.19", "node3": "10.10.10.9"}
    # always start migration from node1
    source = nodes["node1"]
    dest = nodes["node3"]
    last_iter, last_comb, last_type = get_last_iter_and_comb()
    last_iter += 10
    # run migration 20 times for each optimization with the same config
    reboot_iter = 0
    check_remote_runs()
    for i in range(20, 100):
        # get the last iteration and combination
        if i >= last_iter:
            # for each combination run the correspondent dynintensive container
            for combination in valid_combos:
                if i == last_iter and last_comb not in valid_combos:
                    # skip the whole iteration as the last combo is in the next dictionary
                    break
                if i == last_iter and valid_combos.index(combination) < valid_combos.index(last_comb):
                    continue
                if i == last_iter and valid_combos.index(combination) == valid_combos.index(last_comb):
                    if last_type == "hybrid":
                        continue
                    else: # complete the partial combo iteration
                        migration_experiment_per_combo( i, combination, dest, last_type)
                        reboot_iter += 1
                        continue
                # continue with the rest of the combinations
                logger.info("-------------------------------------------------")
                logger.info("Modified config.json for combination:" + str(combination) + ";")
                migration_experiment_per_combo(i, combination, dest)
                reboot_iter += 1
                if reboot_iter % 3 == 0:
                    reboot()

            for combination in real_to_defacto_valid.keys():
                if i == last_iter and last_comb in real_to_defacto_valid.keys():
                    if i == last_iter and list(real_to_defacto_valid.keys()).index(combination) < list(real_to_defacto_valid.keys()).index(last_comb):
                        continue
                    if i == last_iter and list(real_to_defacto_valid.keys()).index(combination) == list(real_to_defacto_valid.keys()).index(last_comb):
                        if last_type == "hybrid":
                            continue
                        else: # complete the partial combo iteration
                            reboot_iter += 1
                            migration_experiment_per_combo(i, combination, dest, last_type)
                            continue
                # for the defacto combos use the defacto config (key) but classify as value combo
                logger.info("-------------------------------------------------")
                logger.info("Modified config.json for combination " + real_to_defacto_valid[combination] + "; real defacto combination:" + str(combination))
                migration_experiment_per_combo(i, combination, dest)
                reboot_iter += 1
                if reboot_iter % 3 == 0:
                    reboot()