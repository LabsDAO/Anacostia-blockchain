from logging import Logger
import os
import time
import logging
import shutil
from typing import List
import json
import requests
import time
from web3 import Web3
from dotenv import load_dotenv

from anacostia_pipeline.engine.base import BaseNode, BaseActionNode, BaseMetadataStoreNode
from anacostia_pipeline.engine.pipeline import Pipeline
from anacostia_pipeline.dashboard.webserver import run_background_webserver

from anacostia_pipeline.resources.filesystem_store import FilesystemStoreNode
from anacostia_pipeline.metadata.sql_metadata_store import SqliteMetadataStore

from utils import *

# Make sure that the .env file is in the same directory as this Python script
load_dotenv()


class MetadataStore(SqliteMetadataStore):
    def __init__(
        self, name: str, uri: str, temp_dir: str, loggers: Logger | List[Logger] = None
    ) -> None:
        super().__init__(name, uri, loggers)
        self.temp_dir = temp_dir
        os.makedirs(self.temp_dir)

    def get_runs_json(self, path: str):
        runs = self.get_runs()
        runs = [run.as_dict() for run in runs]

        for run in runs:
            run["start_time"] = str(run["start_time"])
            if run["end_time"] != None:
                run["end_time"] = str(run["end_time"])

        with open(path, "w") as f:
            json.dump(runs, f, ensure_ascii=False, indent=4) 

    def get_metrics_json(self, path: str):
        metrics = self.get_metrics()
        with open(path, "w") as f:
            json.dump(metrics, f, ensure_ascii=False, indent=4)  

    def get_params_json(self, path: str):
        params = self.get_params()
        with open(path, "w") as f:
            json.dump(params, f, ensure_ascii=False, indent=4)  

    def get_tags_json(self, path: str):
        tags = self.get_tags()
        with open(path, "w") as f:
            json.dump(tags, f, ensure_ascii=False, indent=4)  



class MonitoringDataStoreNode(FilesystemStoreNode):
    def __init__(
        self, name: str, resource_path: str, metadata_store: BaseMetadataStoreNode, 
        init_state: str = "new", max_old_samples: int = None
    ) -> None:
        super().__init__(name, resource_path, metadata_store, init_state, max_old_samples)
    
    def trigger_condition(self) -> bool:
        num_new = self.get_num_artifacts("new")
        return num_new >= 1


class ModelRegistryNode(FilesystemStoreNode):
    def __init__(self, name: str, resource_path: str, metadata_store: BaseMetadataStoreNode, ) -> None:
        super().__init__(name, resource_path, metadata_store, init_state="new", max_old_samples=None, monitoring=False)
    
    def create_filename(self) -> str:
        return f"processed_data_file{self.get_num_artifacts('all')}.txt"

    def save_artifact(self, content: str) -> None:
        filename = self.create_filename()
        filepath = os.path.join(self.path, filename)

        # note: for monitoring-enabled resource nodes, record_artifact should be called before create_file;
        # that way, the Observer can see the file is already logged and ignore it
        self.record_current(filepath)
        with open(filepath, 'w') as f:
            f.write(content)
        self.log(f"Saved preprocessed {filepath}", level="INFO")


class PlotsStoreNode(FilesystemStoreNode):
    def __init__(self, name: str, resource_path: str, metadata_store: BaseMetadataStoreNode, ) -> None:
        super().__init__(name, resource_path, metadata_store, init_state="new", max_old_samples=None, monitoring=False)
    

class ModelRetrainingNode(BaseActionNode):
    def __init__(
        self, name: str, 
        data_store: MonitoringDataStoreNode, plots_store: PlotsStoreNode,
        model_registry: ModelRegistryNode, metadata_store: BaseMetadataStoreNode
    ) -> None:
        self.data_store = data_store
        self.model_registry = model_registry
        self.plots_store = plots_store
        self.metadata_store = metadata_store
        super().__init__(name, predecessors=[data_store, plots_store, model_registry])
    
    def execute(self, *args, **kwargs) -> bool:
        self.log(f"Executing node '{self.name}'", level="INFO")

        for filepath in self.data_store.list_artifacts("current"):
            with open(filepath, 'r') as f:
                self.log(f"Trained on {filepath}", level="INFO")
        
        for filepath in self.data_store.list_artifacts("old"):
            self.log(f"Already trained on {filepath}", level="INFO")
        
        self.metadata_store.log_metrics(acc=1.00)
        
        self.metadata_store.log_params(
            batch_size = 64, # how many independent sequences will we process in parallel?
            block_size = 256, # what is the maximum context length for predictions?
            max_iters = 2500,
            eval_interval = 500,
            learning_rate = 3e-4,
            eval_iters = 200,
            n_embd = 384,
            n_head = 6,
            n_layer = 6,
            dropout = 0.2,
            seed = 1337,
            split = 0.9    # first 90% will be train, rest val
        )

        self.metadata_store.set_tags(test_name="Karpathy LLM test")

        self.log(f"Node '{self.name}' executed successfully.", level="INFO")
        return True


class ShakespeareEvalNode(BaseActionNode):
    def __init__(
        self, name: str, predecessors: List[BaseNode], 
        metadata_store: BaseMetadataStoreNode, loggers: Logger | List[Logger] = None
    ) -> None:
        self.metadata_store = metadata_store
        super().__init__(name, predecessors, loggers)
    
    def execute(self, *args, **kwargs) -> bool:
        self.log("Evaluating LLM on Shakespeare validation dataset", level="INFO")
        self.metadata_store.log_metrics(shakespeare_test_loss=1.47)
        return True

class HaikuEvalNode(BaseActionNode):
    def __init__(
        self, name: str, predecessors: List[BaseNode], 
        metadata_store: BaseMetadataStoreNode, loggers: Logger | List[Logger] = None
    ) -> None:
        self.metadata_store = metadata_store
        super().__init__(name, predecessors, loggers)
    
    def execute(self, *args, **kwargs) -> bool:
        self.log("Evaluating LLM on Haiku validation dataset", level="INFO")
        self.metadata_store.log_metrics(haiku_test_loss=2.43)
        return True
class BlockchainNode(BaseActionNode):
    def __init__(
        self, name: str, predecessors: List[BaseNode], metadata_store: MetadataStore,
        contract_address: str, contract_abi: list, web3_provider: str,
        account_address: str, private_key: str, loggers: Logger | List[Logger] = None
    ) -> None:
        super().__init__(name, predecessors, loggers)
        self.metadata_store = metadata_store
        self.temp_dir = self.metadata_store.temp_dir
        self.web3 = Web3(Web3.HTTPProvider(web3_provider))
        self.account_address = account_address
        self.private_key = private_key
        self.contract = self.web3.eth.contract(address=contract_address, abi=contract_abi)
        self.api_key = 'QN_f3860eefca4341f1a71e1cc7ee2c2604'  # Replace with your actual QuickNode API key

    def execute(self, *args, **kwargs) -> bool:
        url = 'https://api.quicknode.com/ipfs/rest/v1/s3/put-object'
        filename = 'filename1.json'
        file_path = f"{self.temp_dir}/{filename}"
        content_type = 'application/json'

        if not self.api_key:
            raise Exception("QuickNode API key is not set.")

        # Uploading metadata to IPFS
        self.metadata_store.get_runs_json(path=file_path)
        time.sleep(1)

        payload = {'Key': filename, 'ContentType': content_type}
        files = [('Body', (filename, open(file_path, 'rb'), content_type))]
        headers = {'x-api-key': self.api_key}

        response = requests.request("POST", url, headers=headers, data=payload, files=files)

        if response.status_code == 200:
            ipfs_hash = response.json()['ipfs_hash']
            print(f'File uploaded to QuickNode IPFS with hash: {ipfs_hash}')
            
            # Minting NFT with the received IPFS hash
            token_id = 1  # Assuming you want to mint MLOPs_NFT1; change as needed
            mint_amount = 1  # Change as needed
            nonce = self.web3.eth.getTransactionCount(self.account_address)
            txn = self.contract.functions.mint(
                self.account_address, token_id, mint_amount
            ).buildTransaction({
                'chainId': 137,  # For Polygon Mainnet; change according to your target network
                'gas': 2000000,
                'gasPrice': self.web3.toWei('50', 'gwei'),
                'nonce': nonce,
                'value': self.web3.toWei(0.006, 'ether')  # Mint price per NFT
            })
            signed_txn = self.web3.eth.account.signTransaction(txn, private_key=self.private_key)
            txn_hash = self.web3.eth.sendRawTransaction(signed_txn.rawTransaction)
            txn_receipt = self.web3.eth.waitForTransactionReceipt(txn_hash)
            print(f'NFT minted successfully with transaction hash: {txn_receipt.transactionHash.hex()}')
            return True
        else:
            print(f'Error uploading file: {response.text}')
            return False




web_tests_path = "./testing_artifacts/frontend"
if os.path.exists(web_tests_path) is True:
    shutil.rmtree(web_tests_path)
os.makedirs(web_tests_path)

log_path = f"{web_tests_path}/anacostia.log"
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(levelname)s - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S',
    filename=log_path,
    filemode='a'
)
logger = logging.getLogger(__name__)


path = f"{web_tests_path}/webserver_test"
metadata_store_path = f"{path}/metadata_store"
haiku_data_store_path = f"{path}/haiku"
model_registry_path = f"{path}/model_registry"
plots_path = f"{path}/plots"
json_dir = f'{path}/ipfsjson'  # Adjust the file path if necessary

metadata_store = MetadataStore(
    name="metadata_store", 
     uri=f"sqlite:///{metadata_store_path}/metadata.db",
    temp_dir=json_dir
)
model_registry = ModelRegistryNode(
    "model_registry", 
    model_registry_path, 
    metadata_store
)
plots_store = PlotsStoreNode("plots_store", plots_path, metadata_store)
haiku_data_store = MonitoringDataStoreNode("haiku_data_store", haiku_data_store_path, metadata_store)
retraining = ModelRetrainingNode("retraining", haiku_data_store, plots_store, model_registry, metadata_store)
shakespeare_eval = ShakespeareEvalNode("shakespeare_eval", predecessors=[retraining], metadata_store=metadata_store)
haiku_eval = HaikuEvalNode("haiku_eval", predecessors=[retraining], metadata_store=metadata_store)

# Blockchain node variables
contract_address = os.getenv("CONTRACT_ADDRESS")  # Replace ... with the actual value of contract_address
contract_abi = os.getenv("CONTRACT_ABI")  # Replace ... with the actual value of contract_abi
web3_provider = os.getenv("WEB3_PROVIDER_URI_MUMBAI")  # Replace with the actual web3 provider URL
account_address = os.getenv("ACCOUNT_ADDRESS")  # Replace with the actual account address
private_key= os.getenv("PRIVATE_KEY")  # Replace with the actual private key

# Load the contract ABI
with open('../artifacts/contracts/MLOpsNFT.sol/MLOpsNFT.json', 'r') as abi_file:
    contract_abi = json.load(abi_file)["abi"]

blockchain_node = BlockchainNode(
    "blockchain_node",
    predecessors=[haiku_eval, shakespeare_eval],
    metadata_store=metadata_store,
    contract_address=contract_address,
    contract_abi=contract_abi,
    web3_provider=web3_provider,
    account_address=account_address,
    private_key=private_key
)

pipeline = Pipeline(
    nodes=[metadata_store, haiku_data_store, model_registry, plots_store, shakespeare_eval, haiku_eval, retraining,blockchain_node],
    loggers=logger
)



if __name__ == "__main__":
    run_background_webserver(pipeline, host="127.0.0.1", port=8000)

    time.sleep(6)
    for i in range(10):
        create_file(f"{haiku_data_store_path}/test_file{i}.txt", f"test file {i}")
        time.sleep(1.5)
