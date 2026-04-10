#[starknet::interface]
pub trait IVault<TContractState> {
    fn deposit(ref self: TContractState, amount: u128);
    fn withdraw(ref self: TContractState, amount: u128);
    fn get_balance(self: @TContractState) -> u128;
}

#[starknet::contract]
mod Vault {
    use starknet::get_caller_address;
    use starknet::ContractAddress;

    use starknet::storage::{
        StoragePointerReadAccess,
        StoragePointerWriteAccess,
    };

    #[storage]
    struct Storage {
        owner: ContractAddress,
        balance: u128,
    }

    #[constructor]
    fn constructor(ref self: ContractState, owner: ContractAddress) {
        self.owner.write(owner);
        self.balance.write(0);
    }

    #[abi(embed_v0)]
    impl VaultImpl of super::IVault<ContractState> {
        fn deposit(ref self: ContractState, amount: u128) {
            assert(amount > 0, 'amount must be > 0');

            let current = self.balance.read();
            self.balance.write(current + amount);
        }

        fn withdraw(ref self: ContractState, amount: u128) {
            let caller = get_caller_address();

            assert(caller == self.owner.read(), 'only owner');

            let bal = self.balance.read();
            assert(bal >= amount, 'insufficient balance');

            self.balance.write(bal - amount);
        }

        fn get_balance(self: @ContractState) -> u128 {
            self.balance.read()
        }
    }
}
