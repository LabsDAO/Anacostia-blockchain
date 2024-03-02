const { ethers } = require("hardhat");
const fs = require("fs");
async function main() {
  const deployNFTContract = await ethers.deployContract("MLOpsNFT");
  const [owner] = await hre.ethers.getSigners();
  const MLOpsNFT = await deployNFTContract.waitForDeployment();
  const contractAdd = await MLOpsNFT.getAddress();
  console.log("Deploying Contract...");

  console.log("contract has been deployed succesfully", contractAdd);
  console.log("owner", owner);

  // Prepare the content to write
  const content = `Contract deployed to: ${contractAdd}\nContract deployed by: ${owner.address}\n`;

  if (!fs.existsSync("./genericJson")) {
    fs.mkdirSync("./genericJson");
  }

  // Writing the content to a specific file, assuming 'deploymentInfo.txt' as per your message.
  // fs.writeFileSync requires a file name, not just a directory path.
  fs.writeFileSync(`./genericJson/deploymentInfo.txt`, content);

  console.log("Deployment information has been saved to deploymentInfo.txt");
}

main()
  .then(() => process.exit(0))
  .catch((err) => {
    console.error(err);
    process.exit(1);
  });
