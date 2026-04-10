use starknet::ContractAddress;

use snforge_std::{
    declare,
    ContractClassTrait,
    DeclareResultTrait,
    start_cheat_caller_address,
    start_cheat_block_timestamp,
    stop_cheat_caller_address,
    stop_cheat_block_timestamp,
};

use demo_staking_protocol::stake_vault::IStakeVaultDispatcher;
use demo_staking_protocol::stake_vault::IStakeVaultDispatcherTrait;

fn deploy_stake_vault(staker: felt252, unlock_at: felt252) -> ContractAddress {
    let contract = declare("StakeVault").unwrap().contract_class();
    let (contract_address, _) = contract.deploy(@array![staker, unlock_at]).unwrap();
    contract_address
}

#[test]
fn test_simple_stake() {
    let contract_address = deploy_stake_vault(456, 100);
    let dispatcher = IStakeVaultDispatcher { contract_address };

    dispatcher.stake(160);
    assert(dispatcher.get_staked() == 160, 'stake failed');

}

#[test]
#[should_panic]
fn test_zero_stake() {
    let contract_address = deploy_stake_vault(456, 100);
    let dispatcher = IStakeVaultDispatcher { contract_address };

    dispatcher.stake(0);
}

#[test]
fn test_stake_and_withdraw_after_unlock() {
    let staker: ContractAddress = 456.try_into().unwrap();
    let contract_address = deploy_stake_vault(456, 100);
    let dispatcher = IStakeVaultDispatcher { contract_address };

    assert(dispatcher.get_staked() == 0, 'init failed');
    assert(dispatcher.get_unlock_at() == 100, 'unlock time failed');

    dispatcher.stake(250);
    assert(dispatcher.get_staked() == 250, 'stake failed');

    start_cheat_caller_address(contract_address, staker);
    start_cheat_block_timestamp(contract_address, 100_u64);
    dispatcher.withdraw(100);
    stop_cheat_block_timestamp(contract_address);
    stop_cheat_caller_address(contract_address);

    //// NO check of the amount withdrawn
    // assert(dispatcher.get_staked() == 150, 'withdraw failed');
}

#[test]
#[should_panic]
fn test_stake_withdraw_too_early_should_fail() {
    let staker: ContractAddress = 456.try_into().unwrap();
    let contract_address = deploy_stake_vault(456, 100);
    let dispatcher = IStakeVaultDispatcher { contract_address };

    dispatcher.stake(50);

    start_cheat_caller_address(contract_address, staker);
    start_cheat_block_timestamp(contract_address, 99_u64);
    dispatcher.withdraw(10);
    stop_cheat_block_timestamp(contract_address);
    stop_cheat_caller_address(contract_address);
}
