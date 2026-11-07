# low cpu doesn't go beyond 40% usage
low_cpu =     {"resources": {
        "cpu": {
            "quota": 40000,
            "period": 100000
        }
    }}

# mid cpu doesn't go beyond 65% usage
mid_cpu =    {"resources": {
        "cpu": {
            "quota": 65000,
            "period": 100000
        }
    }}

# high cpu doesn't go beyond 100% usage
high_cpu =   {"resources": {
        "cpu": {
            "quota": 100000,
            "period": 100000
        }
    }}

veryhigh_cpu =   {"resources": {
        "cpu": {
            "quota": 250000,
            "period": 100000
        }
    }}


# low memory doesn't go beyond 30000 memory pages
low_memory = {"resources": {
        "memory": {
            "limit": 150760000 # ~150MB
        }
    }}

# mid memory doesn't go beyond 60000 memory pages
mid_memory = {"resources": {
        "memory": {
            "limit": 240760000 # ~240MB
        }
    }}

# high memory doesn't go beyond 200000 memory pages
high_memory = {"resources": {
        "memory": {
            "limit": 1250760000 # ~1.25 GB
        }
    }}

veryhigh_memory = {"resources": {
        "memory": {
            "limit": 2000760000 # ~2 GB
        }
    }}


# low disk doesn't go beyond 10MB read/write operation
low_disk = {"blockIO": {
            "throttleReadBpsDevice": [
                {
                    "major": 252,
                    "minor": 0,
                    "rate": 10485760  # 10 MB/s read limit
                }
            ],
            "throttleWriteBpsDevice": [
                {
                    "major": 252,
                    "minor": 0,
                    "rate": 10485760  # 10 MB/s write limit
                }
            ],
            "throttleReadIOPSDevice": [
                {
                    "major": 252,
                    "minor": 0,
                    "rate": 200  # 100 read IOPS
                }
            ],
            "throttleWriteIOPSDevice": [
                {
                    "major": 252,
                    "minor": 0,
                    "rate": 200  # 100 write IOPS
                }
            ]
        }}

mid_disk = {"blockIO": {
                "throttleReadBpsDevice": [
                    {
                        "major": 252,
                        "minor": 0,
                        "rate": 50485760  # 50 MB/s read limit
                    }
                ],
                "throttleWriteBpsDevice": [
                    {
                        "major": 252,
                        "minor": 0,
                        "rate": 50485760  # 50 MB/s write limit
                    }
                ],
                "throttleReadIOPSDevice": [
                    {
                        "major": 252,
                        "minor": 0,
                        "rate": 500  # 500 read IOPS
                    }
                ],
                "throttleWriteIOPSDevice": [
                    {
                        "major": 252,
                        "minor": 0,
                        "rate": 500  # 500 write IOPS
                    }
                ]
            }}

high_disk = {"blockIO": {
                "throttleReadBpsDevice": [
                    {
                        "major": 252,
                        "minor": 0,
                        "rate": 150485760  # 150 MB/s read limit
                    }
                ],
                "throttleWriteBpsDevice": [
                    {
                        "major": 252,
                        "minor": 0,
                        "rate": 150485760  # 150 MB/s write limit
                    }
                ],
                "throttleReadIOPSDevice": [
                    {
                        "major": 252,
                        "minor": 0,
                        "rate": 1500  # 1500 read IOPS
                    }
                ],
                "throttleWriteIOPSDevice": [
                    {
                        "major": 252,
                        "minor": 0,
                        "rate": 1500  # 1500 write IOPS
                    }
                ]
            }}

veryhigh_disk = {"blockIO": {
                "throttleReadBpsDevice": [
                    {
                        "major": 252,
                        "minor": 0,
                        "rate": 300485760  # 300 MB/s read limit
                    }
                ],
                "throttleWriteBpsDevice": [
                    {
                        "major": 252,
                        "minor": 0,
                        "rate": 300485760  # 300 MB/s write limit
                    }
                ],
                "throttleReadIOPSDevice": [
                    {
                        "major": 252,
                        "minor": 0,
                        "rate": 3000  # 3000 read IOPS
                    }
                ],
                "throttleWriteIOPSDevice": [
                    {
                        "major": 252,
                        "minor": 0,
                        "rate": 3000  # 3000 write IOPS
                    }
                ]
            }}


low_net = 10 # 1 locust user, 97.6 req/s (avg. resp. time 1ms)
mid_net = 100 # 100 locust users, 957 req/s (avg. resp. time 2ms)
high_net = 500 # 500 locust users, 3360 req/s (avg. resp. time 33ms)


# thresholds fixed based on graphics from dynintensive logs
net_thresholds = [100, 955]
cpu_thresholds = [40, 65]
memory_thresholds = [39000, 62000]
disk_thresholds = [100000, 210000]
thresholds = {"cpu": cpu_thresholds, "memory": memory_thresholds, "disk": disk_thresholds, "net": net_thresholds }
