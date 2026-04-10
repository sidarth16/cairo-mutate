use starknet::ContractAddress;

use snforge_std::{
    declare,
    ContractClassTrait,
    DeclareResultTrait,
    start_cheat_caller_address,
    stop_cheat_caller_address,
};

use demo_staking_protocol::vault::IVaultDispatcher;
use demo_staking_protocol::vault::IVaultDispatcherTrait;

fn deploy_vault(owner: felt252) -> ContractAddress {
    let contract = declare("Vault").unwrap().contract_class();
    let (contract_address, _) = contract.deploy(@array![owner]).unwrap();
    contract_address
}

#[test]
fn test_simple_deposit() {
    let contract_address = deploy_vault(123);
    let dispatcher = IVaultDispatcher { contract_address };

    dispatcher.deposit(100);
    assert(dispatcher.get_balance() == 100, 'deposit failed');
}

#[test]
#[should_panic]
fn test_vault_zero_deposit_should_fail() {
    let contract_address = deploy_vault(123);
    let dispatcher = IVaultDispatcher { contract_address };

    dispatcher.deposit(0);
}

#[test]
fn test_vault_deposit_and_owner_withdraw() {
    let owner_addr: ContractAddress = 123.try_into().unwrap();
    let contract_address = deploy_vault(123);
    let dispatcher = IVaultDispatcher { contract_address };

    assert(dispatcher.get_balance() == 0, 'init failed');

    dispatcher.deposit(100);
    assert(dispatcher.get_balance() == 100, 'deposit failed');

    start_cheat_caller_address(contract_address, owner_addr);
    dispatcher.withdraw(40);
    stop_cheat_caller_address(contract_address);

    assert(dispatcher.get_balance() == 60, 'withdraw failed');
}


