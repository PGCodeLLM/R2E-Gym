# editagent_script.py

import openai
import re
import yaml
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any, Dict, List, Optional
from datetime import datetime
import json
import concurrent.futures
import threading
import multiprocessing
from pymongo import MongoClient
import pandas as pd
import traceback
import docker
import pyarrow as pa
import pyarrow.compute as pc
import pyarrow.dataset as pds
from mindforge_harness.utils import (
    consistent_hash,
)


from r2egym.agenthub.runtime.docker import DockerRuntime
from r2egym.agenthub.environment.env import EnvArgs, RepoEnv
from r2egym.agenthub.agent.agent import AgentArgs, Agent

from docker_bash_utils.docker_list_tags import fetch_docker_tags
from r2egym.agenthub.utils.log import get_logger
from r2e_logging import setup_logging, INFO
from r2egym.agenthub.utils.utils import get_parsed_commit

from fire import Fire
from r2egym.agenthub.utils.utils import match_dockerimage_to_repo
from r2egym.agenthub import SUPPORTED_REPOS
from datasets import load_dataset, Dataset
from r2egym.agenthub.trajectory import TrajectoryStep, Trajectory

##############################################################################
# Initialize Logger
##############################################################################
logger = get_logger(__name__)  # Initialize the logger

##############################################################################
# Initialize File Lock for Thread-Safe Writing
##############################################################################
file_lock = threading.Lock()


##############################################################################
# editagent Functions
##############################################################################
def run_agent_with_restarts(
    agent, env, max_steps=40, num_restarts=1, temperature=0.0, top_p=0.0, presence_penalty=0.0, max_steps_absolute=50, use_fn_calling: bool = True
):
    steps_per_agent = max_steps // num_restarts
    logger.warning(f"running {steps_per_agent} steps per agent")

    for idx in range(num_restarts):
        logger.warning(f"running agent at idx: {idx+1}")
        print()
        trajectory = agent.run(
            env,
            max_steps=steps_per_agent,
            temperature=temperature,
            max_steps_absolute=max_steps_absolute,
            use_fn_calling=use_fn_calling,
            top_p=top_p,
            presence_penalty=presence_penalty
        )
        # remove reproduce.py
        # env.runtime.run('rm reproduce_issue.py')
    return trajectory


def runagent(
    ds,
    exp_name: Optional[str] = None,
    max_steps=40,
    num_restarts=1,
    max_steps_absolute=50,
    llm_name="gpt-4o",
    temperature=0,
    top_p=0,
    presence_penalty=0,
    use_fn_calling: bool = False,
    llm_base_url: Optional[str] = None,
    sem = None
) -> Optional[str]:
    """
    Runs the editagent agent on a specified Docker image.

    Args:
        dockerpytest_image: The Docker image to use for the environment.
        traj_dir: Directory to save trajectories.
        jsonl_file: Path to the JSONL file to save results. If not provided, generated using traj_dir and exp_name.
        exp_name: Experiment name. Used if jsonl_file is not provided. If not provided, a unique name is generated.
    """
    print(":3")
    logger = setup_logging(
        name=ds["docker_image"].replace("/", "_"),
        log_file=f"run_logs/{exp_name}/{ds['docker_image'].replace('/', '_')}.log",
        console=True,
        level=INFO,
    )
    logger.info(f"Starting editagent on Docker image: {ds['docker_image']}")
    logger.info(f"Using LLM: {llm_name}")
    logger.info(f"Max Steps: {max_steps}")

    # Generate a unique experiment name if not provided
    if exp_name is None:
        exp_name = datetime.now().strftime("%Y%m%d_%H%M%S")
    
    # Initialize environment arguments
    env_args = EnvArgs(ds=ds)
    # Initialize the RepoEnv
    print("WHY ARE YOU NOT WORKING")
    # print(env_args)
    env = RepoEnv(env_args, logger=logger)
    print("kms")
    # set agent args
    if use_fn_calling:
        print("fml")
        agent_args = AgentArgs.from_yaml(
            Path("./agenthub/config/edit_fn_calling.yaml")
        )
        print("fml")
    else:
        print("fml2")
        agent_args = AgentArgs.from_yaml(
            Path("./agenthub/config/edit_non_fn_calling.yaml")
        )
        print("fml2")
    print(":3333")
    agent_args.llm_name = llm_name
    if llm_base_url:
        agent_args.llm_base_url = llm_base_url

    # Initialize the agent
    agent = Agent(name="EditAgent", args=agent_args, logger=logger, sem=sem)

    # run agent editagent
    print(":33")
    try:
        trajectory = run_agent_with_restarts(
            agent,
            env,
            max_steps=max_steps,
            num_restarts=num_restarts,
            temperature=temperature,
            top_p=top_p,
            presence_penalty=presence_penalty,
            max_steps_absolute=max_steps_absolute,
            use_fn_calling=use_fn_calling,
        )
    except Exception as e:
        logger.error(
            f"Error during agent run for Docker image {ds['docker_image']}: {e}"
        )
        return None
    test_sh_name = f"temp_sh_folder/{ds['instance_id']}.sh"
    with open(test_sh_name, "w") as f:
        # f.write(ds["spec_dict"]["test_cmd"])
        # f.write("QT_QPA_PLATFORM=minimal PYTHONWARNINGS='ignore::UserWarning,ignore::SyntaxWarning' pytest -rA --continue-on-collection-errors")
        test_string = "QT_QPA_PLATFORM=minimal PYTHONWARNINGS='ignore::UserWarning,ignore::SyntaxWarning' pytest -rA --continue-on-collection-errors "
        for f2p in ds["FAIL_TO_PASS"]:
            test_string += " " + f2p.split("::")[0] + " "
        for p2p in ds["PASS_TO_PASS"]:
            test_string += " " + p2p.split("::")[0] + " "
        f.write(test_string)

    env.runtime.copy_to_container(test_sh_name, "/root/run_tests.sh")
    # also get the gt outputs
    reward, test_output = env.runtime._calculate_reward(get_test_output=True)
    # Close the environment and runtime
    env.close()

    # update the trajectory object
    trajectory.reward = reward
    trajectory.test_output = test_output
    trajectory.ds = ds
    trajectory.exp_name = exp_name

    logger.info(f"editagent completed for Docker image: {ds['docker_image']}")
    # close env and docker runtime
    logger.info(f"Closing environment for Docker image: {ds['docker_image']}")
    return trajectory.model_dump_json()


def runagent_multiple(
    k: int = 1,
    traj_dir: str = "./traj",
    exp_name: Optional[str] = None,
    start_idx=0,
    max_steps=40,
    num_restarts=1,
    max_steps_absolute=50,
    max_workers: Optional[int] = None,
    llm_name="gpt-4o",
    use_existing: bool = False,
    skip_existing: bool = True,
    temperature: float = 0,
    top_p: float = 0.8,
    presence_penalty: float = 1.5,
    use_fn_calling: bool = True,
    llm_base_urls: Optional[str] = None,
    max_semaphores: Optional[int] = 1
):
    """
    Runs the editagent agent on the first k Docker images.

    Args:
        k: The number of Docker images to process.
        traj_dir: Directory to save trajectories.
        exp_name: Experiment name for the JSONL file. If not provided, a unique name is generated.
        start_idx: The starting index in the Docker images list.
        max_steps: Maximum steps for the agent run.
        max_workers: Maximum number of threads to use.
    """
    # Load the dataset
    mongo_uri = "mongodb://bmc:GwvDjDyUnm1GpRT6sMAq7rUo44EDmzuv02Tn9n5mmqvZyn3Zvsee4ozdCGFN57qXRqKEYethBPQfErCGE4oAr3feVuqjpcBuF2em@10.10.100.43:26969/"
    db_name="swe_gym_plus"
    collection_name="r2e_instances"
    mongo_client = MongoClient(mongo_uri)
    db = mongo_client[db_name]
    collection = db[collection_name]
    cursor = collection.find({"verified": True}, {
        "_id": 0,
        "last_modified": 0,
        "issue_numbers": 0,
        "created_at": 0,
        "patch_file_contents": 0,
        "test_patch_file_contents": 0
    })
    documents = list(cursor)
    df = pd.DataFrame(documents)
    print(df)
    temp_client = docker.from_env()
    image_list = temp_client.images.list(
        all=True
    )
    image_label_list = [im.attrs["RepoTags"][0][:-7] for im in image_list if len(im.attrs["RepoTags"])>0 and im.attrs["RepoTags"][0].startswith("eval-")]
    print(len(image_label_list))
    print(image_label_list)
    def add_image_name(entry):
        hash = consistent_hash(entry["spec_dict"])
        image_name = f"eval-{entry['repo'].replace('/','-').lower()}-{hash[0:8]}"
        # print(image_name)
        if image_name in image_label_list:
            # logger.info(image_name)
            return image_name
        return ""
    df["docker_image"] = df.apply(add_image_name, axis=1)
    df = df[df["docker_image"] != ""]
    def add_image_commit(entry):
        return entry["base_commit"]
    df["commit_hash"] = df.apply(add_image_commit, axis=1)
    def stringify_commit(entry):
        entry["parsed_commit_content"]["commit_date"] = entry["parsed_commit_content"]["commit_date"].timestamp()
        return json.dumps(entry["parsed_commit_content"])
    df["parsed_commit_content"] = df.apply(stringify_commit, axis=1)
    print(df)
    ds = Dataset.from_pandas(df)
    # print(ds[0])
    
    print(image_list[0])
    print(image_list[0].attrs["RepoTags"][0])
    logger.info(f"{len(ds)}, {k}, {start_idx}")
    # shuffle the dataset
    ds = ds.shuffle(seed=42)
    # get selected idxs
    selected_idx = range(start_idx, start_idx + k)
    ds_selected = [ds[i] for i in selected_idx]
    llm_base_urls = llm_base_urls.split(',')
    num_base = len(llm_base_urls)
    # print ds_selected stats
    logger.info(
        f"Num_total: {len(ds)}, Start Index: {start_idx}, k: {k}"
    )
    logger.info(f"Starting editagent on {len(ds_selected)} Docker images.")

    # Generate a unique experiment name if not provided
    if exp_name is None:
        exp_name = datetime.now().strftime("%Y%m%d_%H%M%S")

    # Ensure traj_dir exists
    traj_dir_path = Path(traj_dir)
    traj_dir_path.mkdir(parents=True, exist_ok=True)

    # Generate a filename for the JSONL file
    jsonl_file = traj_dir_path / f"{exp_name}.jsonl"

    assert not use_existing
    if use_existing:
        if jsonl_file.exists():
            with open(jsonl_file) as f:
                existing_dockers = []
                for line in f.readlines():
                    try:
                        existing_dockers.append(
                            Trajectory.load_from_model_dump_json(line).ds[
                                "docker_image"
                            ]
                        )
                    except:
                        print("error in jsonl file")

            ds_selected = [
                ds_entry
                for ds_entry in ds_selected
                if ds_entry["docker_image"] not in existing_dockers
            ]
    assert skip_existing
    if skip_existing:
        old_jsonl_files_glob = f"{exp_name[:-1]}*"
        for old_jsonl_file in traj_dir_path.glob(old_jsonl_files_glob):
            with open(old_jsonl_file) as f:
                existing_dockers = [
                    loadline["ds"]["docker_image"]
                    for line in f
                    for loadline in [json.loads(line)]
                    if loadline["reward"] == 1
                ]
            ds_selected = [
                ds_entry
                for ds_entry in ds_selected
                if ds_entry["docker_image"] not in existing_dockers
            ]
        # frog.write(f"existing_dockers {len(existing_dockers)}\n")
        # frog.write(f"selected {len(ds_selected)}")

    logger.info(
        f"Starting editagent on {len(ds_selected)} Docker images after filtering."
    )
    # trackfile = open("trackfile.jsonl", "a")
    # for seleected in ds_selected:
    #     trackfile.write(
    #         json.dumps(seleected)
    #         + "\n"
    #     )
    # return
    # with concurrent.futures.ThreadPoolExecutor(max_workers=max_workers) as executor:
    with multiprocessing.Manager() as manager:
        semaphores = {}
        for url in llm_base_urls:
            semaphores[url] = manager.Semaphore(max_semaphores)
        with concurrent.futures.ProcessPoolExecutor(max_workers=max_workers) as executor:
            # Submit all tasks to the executor using keyword arguments
            future_to_image = {
                executor.submit(
                    runagent,
                    ds=ds_entry,
                    exp_name=exp_name,
                    max_steps=max_steps,
                    num_restarts=num_restarts,
                    max_steps_absolute=max_steps_absolute,
                    llm_name=llm_name,
                    temperature=temperature,
                    top_p=top_p,
                    presence_penalty=presence_penalty,
                    use_fn_calling=use_fn_calling,
                    llm_base_url=llm_base_urls[idx%num_base],
                    sem=semaphores[llm_base_urls[idx%num_base]]
                ): ds_entry[
                    "docker_image"
                ]  # <-- store the docker_image from ds_entry here
                for idx,ds_entry in enumerate(ds_selected)
            }

            with open(jsonl_file, "a") as f:
                for future in concurrent.futures.as_completed(future_to_image):
                    docker_image = future_to_image[
                        future
                    ]  # <-- retrieve that stored docker_image
                    try:
                        result = future.result()
                        if result is not None:
                            with file_lock:
                                f.write(result + "\n")
                    except Exception:
                        # Use docker_image from above when logging
                        logger.error(f"Exception for Docker image {docker_image}")
                        logger.error(traceback.format_exc())
        logger.info(f"editagent completed on {len(ds_selected)} Docker images.")


if __name__ == "__main__":
    # Expose functions via Fire
    Fire(
        {
            "runagent": runagent,
            "runagent_multiple": runagent_multiple,
        }
    )
