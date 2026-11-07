#!/bin/bash
runc run -d --bundle /runc/containers/dynintensive dynintensive </dev/null &>/dev/null
