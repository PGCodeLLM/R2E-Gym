import os, sys
import json
from time import sleep
import time
import uuid
import tempfile
import docker
from docker.models.containers import Container

from r2egym.repo_analysis.execution_log_parser import parse_log_pytest, decolor_dict_keys
from r2egym.agenthub.runtime.base import (
    ExecutionEnvironment,
)
import base64
import subprocess
import datetime
import hashlib
import shutil

import docker
import tarfile
import io
import os
from r2egym.agenthub.utils.log import get_logger
import re
from r2egym.agenthub.utils.utils import match_dockerimage_to_repo
from r2egym.agenthub import SUPPORTED_REPOS, SKIP_FILES, SKIP_FILES_NEW, CMD_TIMEOUT
import concurrent.futures


def _calculate_reward_r2e() -> float:
    # calculate reward based for r2e-edit dockers
    with open("/shared_workspace/alex/tracegen/R2E-Gym/src/r2egym/test_out.txt", "r") as f:
        output = f.read()
    # print(output)x
    
    
    parse = parse_log_pytest(output)
    print("PARSING 2...")
    print(parse)
    parse = decolor_dict_keys(parse)
    print("PARSING 3..")
    print(parse)
    print("DONE PARSING...")
    with open("/shared_workspace/alex/tracegen/R2E-Gym/src/r2egym/test_expected.json", "r") as f:
        expected_json = f.read()

    expected: dict = json.loads(expected_json)
    expected = decolor_dict_keys(expected)
    parse = {k.split(" - ")[0]: parse[k] for k in sorted(parse.keys())}
    expected = {k.split(" - ")[0]: expected[k] for k in sorted(expected.keys())}
    print(f"EXPECTED IS {expected} with len {len(expected)} compared to parsed {parse} with len {len(parse)}")
    # Compare
    # if len(parse) != len(expected):
    #     reward = 0.0
    # else:
        # If ANY mismatch, reward = 0.0, else = 1.0
    match = True
    if len(parse) < 1:
        reason = "PARSE IS EMPTY, BREAKING..."
        print(reason)
        
        match = False
    else:
        for k in expected.keys():
            reason = ":3"
            if k not in parse:
                match = False
                reason = f"K {k} NOT IN PARSED, BREAKING..."
                print(reason)
                break
            if expected[k] != parse[k]:
                match = False
                reason = f"K {k} IN PARSE OF RESULT {parse[k]} NOT EQUAL TO EXPECTED {expected[k]}, BREAKING..."
                print(reason)
                break
    reward = 1.0 if match else 0.0
    print(f"REWARD IS {reward}")
    kms = {
        "expected": expected,
        "expected_len": len(expected),
        "parsed": parse,
        "parsed_len": len(parse),
        "reward": reward
    }
    print("WRITING OUTPUT...")
    print(kms)
    with open ("/shared_workspace/alex/tracegen/R2E-Gym/src/r2egym/ahhhhhhhhhhhhhhhhhhhhhh.jsonl", "a") as wtf:
        wtf.write(json.dumps(kms) + "\n")
    print("DONE WRITING OUTPUT")
    
    # If the caller wants the test output as well, return (reward, output)
    print(f"REWARD IS STILL {reward}")
    
_calculate_reward_r2e()