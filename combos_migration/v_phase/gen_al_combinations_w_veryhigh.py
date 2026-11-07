from dynamic_intensive import *
import subprocess
import json
import logging
import time


# Configure the logging module
logging.basicConfig(
    filename='/home/ubuntu/dyn_comb_script.log_old',  # Log file name
    filemode='a',  # Append mode
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.DEBUG  # Set the logging level
)
# Create a logger.info object
logger = logging.getLogger(__name__)

remote_locust_client = "ubuntu@10.0.0.152"


def set_config_file(cpu, memory, disk):
    # use the objects from dynamic_intensive.py to set the configuration file
    # Initialize a json variable to store the configuration file
    config_file = {
        "linux": {
            "resources": {
                "cpu": {},
                "memory": {},
                "blockIO": {}
            }
        }
    }
    # Check the CPU level
    if cpu == "m":
        config_file['linux']['resources']['cpu'] = mid_cpu['resources']['cpu']
    elif cpu == "h":
        config_file['linux']['resources']['cpu'] = high_cpu['resources']['cpu']
    elif cpu == "v":
        config_file['linux']['resources']['cpu'] = veryhigh_cpu['resources']['cpu']
    # Check the memory level
    if memory == "m":
        config_file['linux']['resources']['memory'] = mid_memory['resources']['memory']
    elif memory == "h":
        config_file['linux']['resources']['memory'] = high_memory['resources']['memory']
    if memory == "v":
        config_file['linux']['resources']['memory'] = veryhigh_memory['resources']['memory']
    # Check the disk level
    if disk == "m":
        config_file['linux']['resources']['blockIO'] = mid_disk['blockIO']
    elif disk == "h":
        config_file['linux']['resources']['blockIO'] = high_disk['blockIO']
    elif disk == "v":
        config_file['linux']['resources']['blockIO'] = veryhigh_disk['blockIO']
    logger.info("Resources set as follow: " + str(config_file))
    # Load and modify the existing config.json file
    config_file_path = "/runc/containers/dynintensive/config.json"
    with open(config_file_path, 'r') as file:
        config_json = json.load(file)
    config_json['linux']['resources']['cpu'] = config_file['linux']['resources']['cpu']
    config_json['linux']['resources']['memory'] = config_file['linux']['resources']['memory']
    config_json['linux']['resources']['blockIO'] = config_file['linux']['resources']['blockIO']
    with open(config_file_path, 'w') as file:
        json.dump(config_json, file, indent=2)


def modify_start_script(combination):
    experiment_duration_sec = 180
    modified_script = "#!/bin/bash\n"
    # modify output path based on the combination
    modified_script += "pidstat -u 1 " + str(experiment_duration_sec) + " > /data/"+ combination["cpu"] + combination["memory"] + combination["disk"]+ combination["net"] + "pidstat_u.txt &\n"
    modified_script += "pidstat -r 1 " + str(experiment_duration_sec) + " > /data/"+combination["cpu"] + combination["memory"] + combination["disk"]+ combination["net"] + "pidstat_r.txt &\n"
    modified_script += "pidstat -d 1 " + str(experiment_duration_sec) + " > /data/"+combination["cpu"] + combination["memory"] + combination["disk"]+ combination["net"] + "pidstat_d.txt &\n"
    modified_script += "timeout " + str(experiment_duration_sec) + "s python3 /home/dyn_generator.py /data/db1.db /data/db2.db"
    # overwrite the shell script with the modified script
    start_script_path = "/runc/containers/dynintensive/rootfs/home/start_container.sh"
    with open(start_script_path, 'w') as file:
        file.write(modified_script)

    logger.info("Modified start script as follow: \n" + modified_script)


# try all combinations of CPU, memory, disk and network resources, each resource have 3 levels
def gen_all_combinations():
    # Define the levels for each resource
    cpu_levels = ["m", "h", "v"]
    memory_levels = ["m", "h", "v"]
    disk_levels = ["m", "h", "v"]
    net_levels = ["l", "m", "h"]
    # Initialize a variable to store the combinations
    combinations = []
    # Iterate over all combinations of CPU, memory, disk, and network resources
    for cpu in cpu_levels:
        for memory in memory_levels:
            for disk in disk_levels:
                for net in net_levels:
                    # Create a dictionary representing the combination
                    combination = {
                        "cpu": cpu,
                        "memory": memory,
                        "disk": disk,
                        "net": net
                    }
                    # Append the combination to the list of combinations
                    combinations.append(combination)
    # Return the list of combinations
    return combinations


def delete_dynintensive_container():
    # delete any old dynintensive container with  'sudo runc kill dynintensive SIGKILL && sudo runc delete dynintensive' and read its output
    try:
        subprocess.check_call('sudo runc kill dynintensive SIGKILL', shell=True)
    except subprocess.CalledProcessError as e:
        logger.error("Error in killing container. The container is probably already stopped.")
    time.sleep(2)
    try:
        subprocess.check_call('sudo runc delete dynintensive', shell=True)
    except subprocess.CalledProcessError as e:
        logger.error("Error in deleting container. The container is probably already deleted.")
    logger.info("Container removed.")


def net_client(combination, intensity, time=180):
    locust_users = 0
    if intensity == "l":
        locust_users = low_net
    elif intensity == "m":
        locust_users = mid_net
    elif intensity == "h":
        locust_users = high_net
    # start the non-blocking locust client with cmd
    command = "locust -f ~/locust_client/simple_locust.py --headless -u " + str(locust_users) + " -r 100 --host http://10.0.8.3:23456 --run-time "+str(time)+"s --csv=/home/ubuntu/dyn_logs/"+ combination["cpu"] + combination["memory"] + combination["disk"] + combination["net"] + "_locust_log"
    process = subprocess.Popen(f"ssh {remote_locust_client} \"{command}\"", shell=True)


def container_exists():
    process = subprocess.Popen("runc list", stdin=subprocess.DEVNULL, stdout=subprocess.PIPE, stderr=subprocess.PIPE, shell=True)
    out, err = process.communicate()
    if "dynintensive" in str(out):
        return True
    else:
        return False


if __name__ == "__main__":
    # Generate all combinations of resources
    combinations = gen_all_combinations()

    for combination in combinations:
        if "v" in combination["cpu"] or "v" in combination["memory"] or "v" in combination["disk"]:
            print("Combination: ", combination)
            # Delete the old dynintensive container
            if container_exists():
                delete_dynintensive_container()
                time.sleep(1)
            # start container with new combination
            logger.info("-------------------------------------------------")
            logger.info("Modified config.json for combination:" + str(combination))
            # Set the runc configuration file based on the combination
            set_config_file(combination["cpu"], combination["memory"], combination["disk"])
            # Modify the start script based on the combination
            modify_start_script(combination)
            # run the container
            try:
                subprocess.check_call("sudo runc run -d --bundle /runc/containers/dynintensive dynintensive & > /home/ubuntu/dyn_logs/"+ combination["cpu"] + combination["memory"] + combination["disk"] + combination["net"] + "file.out < /dev/null", shell=True)
            except subprocess.CalledProcessError as e:
                logger.error("Error in starting container.")
                continue
            # check from sudo runc list that the container is running
            time.sleep(5)
            logger.info("Container started.")
            process = subprocess.Popen("sudo runc list", stdout=subprocess.PIPE, stderr=subprocess.PIPE, shell=True)
            out, err = process.communicate()
            running = False
            if "running" in str(out):
                logger.info("Container is running")
                running = True
            else:
                logger.error("Container not running. Next combination.")
            if running:
                # start the network intensive client
                net_client(combination, combination["net"], 179)
                logger.info("sleeping")
                time.sleep(181)