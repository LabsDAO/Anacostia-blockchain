// SPDX-License-Identifier: MIT
pragma solidity ^0.8.24;

import "@chainlink/contracts/src/v0.8/ChainlinkClient.sol";
import "@chainlink/contracts/src/v0.8/shared/access/ConfirmedOwner.sol";
import "@chainlink/contracts/src/v0.8/interfaces/AggregatorV3Interface.sol";
/**
 * Request testnet LINK and ETH here: https://faucets.chain.link/
 * Find information on LINK Token Contracts and get the latest ETH and LINK faucets here: https://docs.chain.link/docs/link-token-contracts/
 */

/**
 * THIS IS AN EXAMPLE CONTRACT THAT USES HARDCODED VALUES FOR CLARITY.
 * THIS IS AN EXAMPLE CONTRACT THAT USES UN-AUDITED CODE.
 * DO NOT USE THIS CODE IN PRODUCTION.
 */

contract ModelAccuracyPricing is ChainlinkClient, ConfirmedOwner {
    using Chainlink for Chainlink.Request;

    uint256 public accuracy;

    uint256 public priceInEth;
    uint256 public priceInUsd; 

    AggregatorV3Interface internal ethUsdPriceFeed;

    bytes32 private jobId;
    uint256 private fee;

    event RequestFirstId(bytes32 indexed requestId, uint256 accuracy);
    event PriceUpdated(uint256 priceInEth, uint256 priceInUsd);
    /**
     * @notice Initialize the link token and target oracle
     *
     * Sepolia Testnet details:
     * Link Token: 0x779877A7B0D9E8603169DdbD7836e478b4624789
     * Oracle: 0x6090149792dAAeE9D1D568c9f9a6F6B46AA29eFD (Chainlink DevRel)
     * jobId: 7d80a6386ef543a3abb52817f6707e3b
     *
     */
    constructor() ConfirmedOwner(msg.sender) {
        setChainlinkToken(0x779877A7B0D9E8603169DdbD7836e478b4624789);
        setChainlinkOracle(0x6090149792dAAeE9D1D568c9f9a6F6B46AA29eFD);
        jobId = "ca98366cc7314957b8c012c72f05aeeb";
        fee = (1 * LINK_DIVISIBILITY) / 10; // 0,1 * 10**18 (Varies by network and job)
    
    // Initialize Chainlink ETH/USD Price Feed
        ethUsdPriceFeed = AggregatorV3Interface(
            0x694AA1769357215DE4FAC081bf1f309aDC325306
        );
    }

    /**
     * Create a Chainlink request to retrieve API response, find the target
     * data which is located in a list
     */
    function requestFirstId() public returns (bytes32 requestId) {
        Chainlink.Request memory req = buildChainlinkRequest(
            jobId,
            address(this),
            this.fulfill.selector
        );

        // Set the URL to perform the GET request on
        // API docs: https://www.coingecko.com/en/api/documentation?
        req.add(
            "get",
            "https://25cc-3-235-192-234.ngrok-free.app/api/metadata"
        );

        req.add("path", "runs,0,metrics,acc"); // Chainlink nodes 1.0.0 and later support this format

        // Multiply the result by 100 to account for two decimal places (if necessary)
        int256 timesAmount = 10 ** 2; // Adjust based on the accuracy's decimal places
        req.addInt("times", timesAmount);
        // Sends the request
        return sendChainlinkRequest(req, fee);
    }

    /**
     * Receive the response in the form of string
     */
 
    function fulfill(
            bytes32 _requestId,
            uint256 _accuracy
        ) public recordChainlinkFulfillment(_requestId) {
            emit RequestFirstId(_requestId, _accuracy);
            accuracy = _accuracy; // Assuming accuracy is a state variable
       
        // Calculate price based on accuracy and update the price in ETH and USD
        priceInUsd = calculatePriceInUsd(accuracy);  // Calculate and store USD price
        priceInEth = convertUsdToEth(priceInUsd);
        emit PriceUpdated(priceInEth, priceInUsd);
        }

    function calculatePriceInUsd(uint256 _accuracy) internal pure returns (uint256) {
                if (_accuracy <= 30) {
                    return 50;
                } else if (_accuracy <= 70) {
                    return 100;
                } else {
                    return 150;
                }
            }


    function calculatePriceInEth(uint256 _accuracy) internal view returns (uint256) {
        uint256 modelPriceInUsd;
        if (_accuracy <= 30) {
            modelPriceInUsd = 50;
        } else if (_accuracy <= 70) {
            modelPriceInUsd = 100;
        } else {
            modelPriceInUsd = 150;
        }

        // Convert USD price to ETH
        return convertUsdToEth(modelPriceInUsd);
    }

    //Function to view Model ETH price
    function convertUsdToEth(uint256 usdAmount) internal view returns (uint256) {
        (, int256 price, , ,) = ethUsdPriceFeed.latestRoundData();
        uint256 ethPriceInUsd = uint256(price) / 1e8; // Adjust based on the price feed decimals
        return (usdAmount * 1e18) / ethPriceInUsd; // Convert USD amount to ETH
    }

    // Function to view the Model USD price
    function getPriceInUsd() public view returns (uint256) {
        return priceInUsd;
    }

    /**
     * Allow withdraw of Link tokens from the contract
     */
    function withdrawLink() public onlyOwner {
        LinkTokenInterface link = LinkTokenInterface(chainlinkTokenAddress());
        require(
            link.transfer(msg.sender, link.balanceOf(address(this))),
            "Unable to transfer"
        );
    }
}