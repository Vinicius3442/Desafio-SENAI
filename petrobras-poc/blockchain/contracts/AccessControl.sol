// SPDX-License-Identifier: MIT
pragma solidity ^0.8.0;

contract AccessControl {
    address public owner;
    
    // Mapping that stores which devices (frontends) are authorized to connect to the gateway
    mapping(address => bool) public authorizedDevices;

    // Event emitted when the backend gateway registers an attempt (success or block)
    // Emitting events is highly cost-effective for logging on the blockchain
    event AccessLogged(address indexed device, string action, string status, string metadata);

    constructor() {
        owner = msg.sender;
    }

    // Modifier to restrict actions to the contract owner
    modifier onlyOwner() {
        require(msg.sender == owner, "AccessControl: Only owner can perform this action");
        _;
    }

    // Method to authorize a new Smart Glasses device
    function authorizeDevice(address device) public onlyOwner {
        authorizedDevices[device] = true;
    }

    // Method to remove authorization from a device
    function revokeDevice(address device) public onlyOwner {
        authorizedDevices[device] = false;
    }

    // Method that the Gateway will call to ensure zero trust verification of the device
    function verifyAccess(address device) public view returns (bool) {
        return authorizedDevices[device];
    }

    // Method to log the access request. E.g action="LLM Request", status="Allowed" or "Blocked", metadata="Anomaly reason..."
    function logEvent(address device, string memory action, string memory status, string memory metadata) public {
        emit AccessLogged(device, action, status, metadata);
    }
}
