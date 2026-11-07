#!/usr/bin/python
import socket
import sys
import select
import time
import os
import shutil
import subprocess
import distutils.util
import concurrent.futures
import fcntl
import re
import json
# import logging

# # Configure the logging module
# logging.basicConfig(
#     filename='/home/ubuntu/migrate.log',  # Log file name
#     filemode='a',  # Append mode
#     format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
#     level=logging.DEBUG  # Set the logging level
# )
# # Create a logger.info object
# logger = logging.getLogger(__name__)
json_path = "/home/ubuntu/migration.json"
migration_json_log = {}

runc_base = "/runc/containers/"

lazy = False
pre = False
with_rootfs = False

if len(sys.argv) < 3:
    print("Usage: " + sys.argv[0] + " [container id] [destination] [pre-copy] [post-copy] [with-rootfs]")
    sys.exit(1)

container = sys.argv[1]
migration_json_log["container"] = container
dest = sys.argv[2]
if len(sys.argv) > 3:
    pre = distutils.util.strtobool(sys.argv[3])
if len(sys.argv) > 4:
    lazy = distutils.util.strtobool(sys.argv[4])
if len(sys.argv) > 5:
    with_rootfs = distutils.util.strtobool(sys.argv[5])
if len(sys.argv) > 6:
    combination = sys.argv[6]
    # migration_json_log["cpu"] = combination[0]
    # migration_json_log["ram"] = combination[1]
    # migration_json_log["disk"] = combination[2]
    # migration_json_log["net"] = combination[3]
    migration_json_log["type"] = combination

base_path = runc_base + container
image_path = base_path + "/image"
parent_path = base_path + "/parent"
root_path = base_path + "/rootfs"
gateway_ip = "10.0.0.152"

# create image and parent directories
os.makedirs(image_path, exist_ok=True)
os.makedirs(parent_path, exist_ok=True)


def error():
    print("Something did not work. Exiting!")
    sys.exit(1)

def prepare():
    try:
        shutil.rmtree(image_path)
    except:
        pass
    try:
        shutil.rmtree(parent_path)
    except:
        pass


def freeze_cgroup():
    cgroup_freezer_path = "/sys/fs/cgroup/user.slice/user-1000.slice/"+str(container)+"/cgroup.freeze"
    freeze_cmd = "echo 1 > " + cgroup_freezer_path
    unfreeze_cmd = "echo 1 > " + cgroup_freezer_path
    paused = False
    start = time.time()
    while not paused:
        os.system(freeze_cmd)
        tries = 0
        cmd = "runc list"
        timeout_exceeded = False
        while tries < 10 and not paused:
            # run cmd with a timeout of 1 second
            try:
                p = subprocess.Popen(cmd, shell=True, stdin=subprocess.DEVNULL, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
                out, err = p.communicate(timeout=1)
            except subprocess.TimeoutExpired as e:
                # not freeze yet
                timeout_exceeded = True
                tries += 1
            if not timeout_exceeded and "paused" in str(out):
                paused = True
            timeout_exceeded = False
        if not paused:
            os.system(unfreeze_cmd)
            time.sleep(0.1)
    end = time.time()
    elapsed = end - start
    print("container freezed in " + str(elapsed) + " s")
    return elapsed


def unfreeze_cgroup():
    cgroup_freezer_path = "/sys/fs/cgroup/user.slice/user-1000.slice/"+str(container)+"/cgroup.freeze"
    unfreeze_cmd = "echo 0 > " + cgroup_freezer_path
    os.system(unfreeze_cmd)
    print("container unfreezed")


def pre_dump():
    old_cwd = os.getcwd()
    os.chdir(base_path)
    freeze_time = freeze_cgroup()
    migration_json_log["predump_freeze_time"] = freeze_time
    cmd = 'runc checkpoint --pre-dump --image-path parent --manage-cgroups-mode ignore --tcp-established --ext-unix-sk --shell-job --file-locks --auto-dedup'
    cmd += ' ' + container
    start = time.time()
    ret = os.system(cmd)
    end = time.time()
    unfreeze_cgroup()
    elapsed = end - start
    print("%s finished after %.2f second(s) with %d" % (cmd, elapsed, ret))
    os.chdir(old_cwd)
    if ret != 0:
        error()
    return elapsed


def real_dump(precopy, postcopy):
    old_cwd = os.getcwd()
    os.chdir(base_path)
    cmd = "runc checkpoint --image-path image --manage-cgroups-mode ignore --tcp-established --ext-unix-sk --shell-job --file-locks --auto-dedup"
    if precopy:
        cmd += ' --parent-path ../parent'
    if postcopy:
        cmd += ' --lazy-pages'
        cmd += ' --page-server localhost:27'
        # unamed pipe to get the status of the criu lazy-page server
        read_fd, write_fd = os.pipe()
        cmd += f' --status-fd {write_fd}'
    cmd += ' ' + container
    start = time.time()
    if postcopy:
        subprocess.Popen(cmd.split(" "), pass_fds=(write_fd,))
        os.close(write_fd)
        print("Waiting for lazy page transfer to start")
        # Set the file descriptor to blocking read mode
        flags = fcntl.fcntl(read_fd, fcntl.F_GETFL)
        fcntl.fcntl(read_fd, fcntl.F_SETFL, flags & ~os.O_NONBLOCK)
        # read from the unnamed pipe
        with os.fdopen(read_fd, 'rb') as read_pipe:
            ret = read_pipe.read(1)
            if ret == b'\0':
                print("Ready for lazy page transfer")
            else:
                print("Unexpected data received from pipe:", ret)
            ret = 0
    else:
        migration_json_log["dump_freeze"] = freeze_cgroup()
        p = subprocess.Popen(cmd, shell=True)
        ret = p.wait()

    end = time.time()
    elapsed = end - start
    print("%s finished after %.2f second(s) with %d" % (cmd, elapsed, ret))
    os.chdir(old_cwd)
    if ret != 0:
        error()
    return elapsed


def get_file_size(file_path):
    cmd = 'du -hs %s' % file_path
    process = subprocess.Popen(cmd, stdin=subprocess.DEVNULL, stdout=subprocess.PIPE, stderr=subprocess.PIPE, shell=True)
    out, err = process.communicate()
    pattern = r"b'(.*?)\\t"
    matches = re.findall(pattern, str(out))
    if len(matches) > 0:
        return matches[0]
    else:
        return "0M"


def size_in_mb(str_size):
    # convert the size to KB if str_size ends with K and MB if str_size ends with M and GB if it ends with G
    if str_size.endswith('K'):
        size = float(str_size[:-1]) / 1024
    elif str_size.endswith('M'):
        size = float(str_size[:-1])
    elif str_size.endswith('G'):
        size = float(str_size[:-1]) * 1024
    else:
        size = 0
    return size


def parse_transferred_size(output):
    match = re.search(r'Literal data: (.*?) bytes', output)
    if match:
        size = match.group(1)
        size = size.replace(',', '')
        return int(size)
    return 0


def xfer_pre_dump():
    pre_dump_size = get_file_size(parent_path)
    print('PRE-DUMP size: ', pre_dump_size)
    pre_dump_size = size_in_mb(pre_dump_size)
    cmd = 'rsync -a --delete --inplace --stats %s %s:%s/' % (parent_path, dest, base_path)
    # print("Transferring PRE-DUMP to %s" % dest)
    start = time.time()
    process = subprocess.Popen(cmd, stdin=subprocess.DEVNULL, stdout=subprocess.PIPE, stderr=subprocess.PIPE, shell=True)
    out, err = process.communicate()
    end = time.time()
    elapsed = end - start
    print("PRE-DUMP transfer time %s seconds" % elapsed)
    ret = process.returncode
    if ret:
        print(str(err))
        error()
    # Parse rsync output to find the transferred data and speed
    out_str = out.decode('utf-8')
    # Parse the output to find the transferred data and speed
    transferred_data_size_mb = parse_transferred_size(out_str) / (1024 * 1024)
    # manually calculate the speed based on time and data transferred
    transfer_speed = transferred_data_size_mb / elapsed
    return pre_dump_size, transferred_data_size_mb, elapsed, transfer_speed


def xfer_final():
    dump_size = get_file_size(image_path)
    print('DUMP size: ', dump_size)
    dump_size = size_in_mb(dump_size)
    cmd = 'rsync -a --delete --inplace %s %s:%s/' % (image_path, dest, base_path)
    # print("Transferring DUMP to %s" % dest)
    start = time.time()
    process = subprocess.Popen(cmd, stdin=subprocess.DEVNULL, stdout=subprocess.PIPE, stderr=subprocess.PIPE, shell=True)
    out, err = process.communicate()
    end = time.time()
    elapsed = end - start
    print("DUMP transfer time %s seconds" % (end - start))
    ret = process.returncode
    if ret:
        print(str(err))
        error()
    # Parse rsync output to find the transferred data and speed
    out_str = out.decode('utf-8')
    # Parse the output to find the transferred data and speed
    transferred_data_size_mb = parse_transferred_size(out_str) / (1024 * 1024)
    # manually calculate the speed based on time and data transferred
    transfer_speed = transferred_data_size_mb / elapsed
    return dump_size, transferred_data_size_mb, elapsed, transfer_speed


def xfer_rootfs():
    rootfs_size = get_file_size(root_path)
    print('Rootfs size: ', rootfs_size)
    rootfs_size = size_in_mb(rootfs_size)
    cmd = 'rsync -a --delete --inplace %s %s:%s/' % (root_path, dest, base_path)
    # print("Transferring RootFS to %s" % dest)
    start = time.time()
    process = subprocess.Popen(cmd, stdin=subprocess.DEVNULL, stdout=subprocess.PIPE, stderr=subprocess.PIPE, shell=True)
    out, err = process.communicate()
    end = time.time()
    elapsed = end - start
    print("Rootfs transfer time %s seconds" % (end - start))
    ret = process.returncode
    if ret:
        print(str(err))
        error()
    # Parse rsync output to find the transferred data and speed
    out_str = out.decode('utf-8')
    # Parse the output to find the transferred data and speed
    transferred_data_size_mb = parse_transferred_size(out_str) / (1024 * 1024)
    # manually calculate the speed based on time and data transferred
    transfer_speed = transferred_data_size_mb / elapsed
    return rootfs_size, transferred_data_size_mb, elapsed, transfer_speed


def xfer_disk_data(container_type, pre_copy = False):
    disk_data_path = "/host/" + container_type
    disk_data_dest_path = "/host/"
    # get rootfs size
    disk_size = get_file_size(disk_data_path)
    print('DISK size: ', disk_size)
    disk_size = size_in_mb(disk_size)
    # Transfer the rootfs
    if pre_copy:
        cmd = 'rsync -a --delete-during --inplace --ignore-errors --ignore-missing-args --partial %s %s:%s/' % (disk_data_path, dest, disk_data_dest_path)
    else:
        cmd = 'rsync -a --delete --inplace %s %s:%s/' % (disk_data_path, dest, disk_data_dest_path)
    # print("Transferring disk data to %s" % dest)
    start = time.time()
    process = subprocess.Popen(cmd, stdin=subprocess.DEVNULL, stdout=subprocess.PIPE, stderr=subprocess.PIPE, shell=True)
    out, err = process.communicate()
    end = time.time()
    elapsed = end - start
    print("Disk data transfer time %s seconds" % (end - start))
    ret = process.returncode
    if ret:
        print(str(err))
        error()
    # Parse rsync output to find the transferred data and speed
    out_str = out.decode('utf-8')
    # Parse the output to find the transferred data and speed
    transferred_data_size_mb = parse_transferred_size(out_str) / (1024 * 1024)
    # manually calculate the speed based on time and data transferred
    transfer_speed = transferred_data_size_mb / elapsed
    return disk_size, transferred_data_size_mb, elapsed, transfer_speed


def transfer_ip(ip_addr):
    start = time.time()
    if dest == "10.0.0.19":
        dest_mac_addr = "fa:16:3e:f7:f8:6b" # node1
    else:
        dest_mac_addr = "fa:16:3e:e5:eb:03" # node3
    cmd = "ssh -i /home/ubuntu/.ssh/id_rsa ubuntu@%s 'sudo arp -s %s %s'" % (gateway_ip, ip_addr, dest_mac_addr)
    try:
        subprocess.check_call(cmd, shell=True)
    except subprocess.CalledProcessError as e:
        print("Error in transfering IP to node3.")
        error()
    end = time.time()
    elapsed = end - start
    print("IP transfer time %s seconds" % elapsed)
    return elapsed



def touch(fname):
    open(fname, 'a').close()


prepare()

if pre and lazy:
    migration_json_log["migration"] = "hybrid"
elif pre:
    migration_json_log["migration"] = "pre"
elif lazy:
    migration_json_log["migration"] = "post"
else:
    migration_json_log["migration"] = "cold"

if pre:
    pre_dump_elapsed_time = pre_dump()
    migration_json_log["pre_dump_time"] = pre_dump_elapsed_time
    migration_json_log["pre_dump_transfer"] = {}
    (migration_json_log["pre_dump_transfer"]["size"],
     migration_json_log["pre_dump_transfer"]["transferred_mb"],
     migration_json_log["pre_dump_transfer"]["transf_time"],
     migration_json_log["pre_dump_transfer"]["transf_speed"])  = xfer_pre_dump()

dump_elapsed_time = real_dump(pre, lazy)
migration_json_log["dump_time"] = dump_elapsed_time

# do the transfer in parallel
with concurrent.futures.ThreadPoolExecutor() as executor:
    future_to_task = {}
    start = time.time()
    # transfer the IP from source node to destination node
    future_to_task[executor.submit(transfer_ip, "10.0.8.3")] = "transfer_ip"

    # transfer the final dump
    future_to_task[executor.submit(xfer_final)] = "xfer_final"

    # transfer the rootfs
    if with_rootfs:
        future_to_task[executor.submit(xfer_rootfs)] = "xfer_rootfs"

    # transfer the disk data
    future_to_task[executor.submit(xfer_disk_data, str(container))] = "xfer_disk_data"

    # concurrent.futures.wait(futures)
    for future in concurrent.futures.as_completed(future_to_task):
        task_name = future_to_task[future]
        if task_name == "xfer_final":
            migration_json_log["dump_transfer"] = {}
            (migration_json_log["dump_transfer"]["size"],
             migration_json_log["dump_transfer"]["transferred_mb"],
             migration_json_log["dump_transfer"]["transf_time"],
             migration_json_log["dump_transfer"]["transf_speed"]) = future.result()
        elif task_name == "xfer_rootfs":
            migration_json_log["rootfs_transfer"] = {}
            (migration_json_log["rootfs_transfer"]["size"],
             migration_json_log["rootfs_transfer"]["transferred_mb"],
             migration_json_log["rootfs_transfer"]["transf_time"],
             migration_json_log["rootfs_transfer"]["transf_speed"]) = future.result()
        elif task_name == "xfer_disk_data":
            migration_json_log["disk_data_transfer"] = {}
            (migration_json_log["disk_data_transfer"]["size"],
             migration_json_log["disk_data_transfer"]["transferred_mb"],
             migration_json_log["disk_data_transfer"]["transf_time"],
             migration_json_log["disk_data_transfer"]["transf_speed"]) = future.result()
        elif task_name == "transfer_ip":
            migration_json_log["ip_transfer_time"] = future.result()

end = time.time()
executor.shutdown()
parallel_phase_time = end - start
print("Total parallel phase %s seconds" % (end - start))
migration_json_log["parallel_phase_time"] = parallel_phase_time

# Connect to the server to request the restore
cs = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
cs.connect((dest, 8887))
input = [cs, sys.stdin]

cs_content = '{ "restore" : { "path" : "' + base_path + '", "name" : "' + container + '" , "image_path" : "' + image_path + '" , "lazy" : "' + str(lazy) + '" } }'
cs.send(cs_content.encode())

while True:
    inputready, outputready, exceptready = select.select(input,[],[], 5)

    if not inputready:
        break

    for s in inputready:
        if s == cs:
            print("Reading from socket")
            answer = cs.recv(1024)
            restore_msg = answer.decode()
            print(restore_msg)
            migration_json_log["restore_time"] = float(re.search(r"sudo runc restored "+re.escape(str(container))+" successfully in (.*?) s", restore_msg).group(1))
            json_string = json.dumps(migration_json_log, indent=4)
            json_string += ',\n'
            with open(json_path, 'a') as file:
                file.write(json_string)