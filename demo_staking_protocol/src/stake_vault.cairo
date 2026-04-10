#[starknet::interface]
pub trait IStakeVault<TContractState> {
    fn stake(ref self: TContractState, amount: u128);
    fn withdraw(ref self: TContractState, amount: u128);
    fn get_staked(self: @TContractState) -> u128;
    fn get_unlock_at(self: @TContractState) -> u64;
}

#[starknet::contract]
mod StakeVault {
    use core::box::BoxTrait;
    use starknet::get_caller_address;
    use starknet::ContractAddress;

    use starknet::storage::{
        StoragePointerReadAccess,
        StoragePointerWriteAccess,
    };

    #[storage]
    struct Storage {
        staker: ContractAddress,
        staked: u128,
        unlock_at: u64,
    }

    #[constructor]
    fn constructor(ref self: ContractState, staker: ContractAddress, unlock_at: u64) {
        self.staker.write(staker);
        self.staked.write(0);
        self.unlock_at.write(unlock_at);
    }

    #[abi(embed_v0)]
    impl StakeVaultImpl of super::IStakeVault<ContractState> {
        fn stake(ref self: ContractState, amount: u128) {
            assert(amount > 0, 'amount must be > 0');

            let current = self.staked.read();
            self.staked.write(current + amount);
        }

        fn withdraw(ref self: ContractState, amount: u128) {
            let caller = get_caller_address();
            let now = starknet::get_block_info().unbox().block_timestamp;

            assert(caller == self.staker.read(), 'only staker');
            assert(now >= self.unlock_at.read(), 'stake is still locked');

            let staked = self.staked.read();
            assert(staked >= amount, 'insufficient stake');

            self.staked.write(staked - amount);
        }

        fn get_staked(self: @ContractState) -> u128 {
            self.staked.read()
        }

        fn get_unlock_at(self: @ContractState) -> u64 {
            self.unlock_at.read()
        }
    }
}
