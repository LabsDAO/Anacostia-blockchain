// SPDX-License-Identifier: MIT
pragma solidity ^0.8.23;

import "@openzeppelin/contracts/token/ERC1155/extensions/ERC1155Supply.sol";
import "@openzeppelin/contracts/access/Ownable.sol";
import "@openzeppelin/contracts/utils/ReentrancyGuard.sol";
import "@openzeppelin/contracts/utils/Pausable.sol";

contract MLOpsNFT is ERC1155Supply, Ownable, ReentrancyGuard, Pausable {
    uint256 public constant MLOPs_NFT1 = 1;
    uint256 public constant MLOPs_NFT2 = 2;
    uint256 public mintPrice = 0.006 ether; 

    // Name and symbol for the NFT collection
    string public name = "AnacostiaML NFTs";
    string public symbol = "AML";

    // Events
    event Minted(address indexed to, uint256 indexed id, uint256 amount);
    event PriceUpdated(uint256 newPrice);
    event Paused();
    event Unpaused();
    event Withdrawn(address indexed to, uint256 amount);
    event Gifted(address indexed to, uint256 indexed id, uint256 amount);

    constructor() ERC1155("https://bafybeihmegjwbtn35se2uufpit6sq65zj7w2mzegeplmxfnavxikeyhbmm.ipfs.nftstorage.link/{id}.json") Ownable(msg.sender)  {
    }

    function mint(address to, uint256 id, uint256 amount) public payable nonReentrant whenNotPaused {
        require(id == MLOPs_NFT1 || id == MLOPs_NFT2, "Invalid token ID");
        require(msg.value >= mintPrice * amount, "Insufficient funds");
        _mint(to, id, amount, "");
        emit Minted(to, id, amount);
    }

    function setURI(string memory newuri) public onlyOwner {
        _setURI(newuri);
    }

    function setMintPrice(uint256 newPrice) public onlyOwner {
        mintPrice = newPrice;
        emit PriceUpdated(newPrice);
    }
    
    function pause() public onlyOwner {
        _pause();
        emit Paused();
    }

    function unpause() public onlyOwner {
        _unpause();
        emit Unpaused();
    }

    function withdraw() public onlyOwner {
        uint256 balance = address(this).balance;
        require(balance > 0, "No funds available");
        (bool success, ) = owner().call{value: balance}("");
        require(success, "Transfer failed.");
        emit Withdrawn(owner(), balance);
    }
}
