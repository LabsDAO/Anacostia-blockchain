require("@nomicfoundation/hardhat-toolbox");
require("dotenv").config({ path: ".env" });

const API_URL_KEY = process.env.ALCHEMY_HTTP_URL;
const PRIVATE_KEY = process.env.PRIVATE_KEY;

/** @type import('hardhat/config').HardhatUserConfig */
module.exports = {
  solidity: "0.8.24",
  defaultNetwork: "mumbai",
  networks: {
    mumbai: {
      url: API_URL_KEY,
      accounts: [PRIVATE_KEY],
    },

    // arbitrumSepolia: {
    //   url: "https://sepolia-rollup.arbitrum.io/rpc",
    //   chainId
    // arbitrumSepolia: {
    //   url: "https://sepolia-rollup.arbitrum.io/rpc",
    //   chainId: 421614,
    //   //accounts: [Sepolia_TESTNET_PRIVATE_KEY]
    // },
    // arbitrumOne: {
    //   url: "https://arb1.arbitrum.io/rpc",
    //   //accounts: [ARBITRUM_MAINNET_TEMPORARY_PRIVATE_KEY]
    //   accounts: [PRIVATE_KEY],
    // },
  },
  etherscan: {
    apiKey: "ANFR67XU9IYADTCUMFPDEREFM2KDWX455G",
  },
};
