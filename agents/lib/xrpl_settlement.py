"""
XRPL Settlement - RLUSD Stablecoin Transfers on XRPL.

Real XRPL settlement with RLUSD stablecoin for remittance operations.

RLUSD issuers (verified):
- Mainnet: rN7n7otQDd6FczFgLdlqtyMVrn3HMfXEro
- Testnet: rHb9CJAWyB4rj91VRWn96DkukG4bwdtyTh

Docs: https://xrpl.org/rlusd.html

@security Wallet seeds are never logged or stored
@author Vaal AI Empire Team
"""


import logging
from typing import Literal, Optional, Dict, Any
from dataclasses import dataclass

logger = logging.getLogger(__name__)

# Import xrpl-py conditionally
try:
    import xrpl
    from xrpl.clients import JsonRpcClient
    from xrpl.models.transactions import Payment

    from xrpl.wallet import Wallet
    from xrpl.utils import drops_to_xrp
    XRPL_AVAILABLE = True
except ImportError:
    XRPL_AVAILABLE = False
    logger.warning("xrpl-py not installed - XRPL settlement unavailable")


@dataclass
class SettlementResult:
    """Result of an XRPL settlement transaction."""
    success: bool
    hash: Optional[str] = None
    ledger_index: Optional[int] = None
    validated: bool = False
    amount_usd: float = 0.0
    destination: str = ""
    network: str = "testnet"
    error: Optional[str] = None
    fee_drops: Optional[str] = None


class RLUSDSettlement:
    """
    REAL XRPL settlement with RLUSD stablecoin.
    
    Features:
    - Testnet and Mainnet support
    - RLUSD payment transactions
    - Account validation
    - Balance checking
    - Trust line management
    
    Example:
        >>> settlement = RLUSDSettlement(network="testnet")
        >>> result = await settlement.settle_rlusd(
        ...     wallet_seed="s...",
        ...     destination="r...",
        ...     amount_usd=10.00
        ... )
    """
    
    # RLUSD issuers (verified Feb 2026)
    RLUSD_ISSUERS = {
        "mainnet": "rN7n7otQDd6FczFgLdlqtyMVrn3HMfXEro",
        "testnet": "rHb9CJAWyB4rj91VRWn96DkukG4bwdtyTh"
    }
    
    XRPL_ENDPOINTS = {
        "mainnet": "https://xrplcluster.com",
        "testnet": "https://s.altnet.rippletest.net:51234"
    }
    
    def __init__(self, network: Literal["testnet", "mainnet"] = "testnet"):
        """
        Initialize XRPL settlement client.
        
        Args:
            network: XRPL network to use (testnet or mainnet)
        """
        if not XRPL_AVAILABLE:
            raise ImportError("xrpl-py is required for XRPL settlement")
        
        self.network = network
        self.client = JsonRpcClient(self.XRPL_ENDPOINTS[network])
        self.rlusd_issuer = self.RLUSD_ISSUERS[network]
        logger.info(f"RLUSD settlement initialized: {network}")
    
    async def settle_rlusd(
        self,
        wallet_seed: str,
        destination: str,
        amount_usd: float,
        memo: Optional[str] = None
    ) -> SettlementResult:
        """
        Execute RLUSD settlement transaction.
        
        Args:
            wallet_seed: XRPL wallet seed (from secure storage)
            destination: Recipient XRPL address
            amount_usd: Amount in USD (RLUSD is 1:1 USD)
            memo: Optional transaction memo for tracking
            
        Returns:
            SettlementResult with transaction details
        """
        try:
            # Load wallet from seed
            wallet = Wallet.from_seed(wallet_seed)
            
            # RLUSD as issued currency
            rlusd_currency = {
                "currency": "RLUSD",
                "value": f"{amount_usd:.2f}",
                "issuer": self.rlusd_issuer
            }
            
            # Create payment transaction
            payment = Payment(
                account=wallet.address,
                destination=destination,
                amount=rlusd_currency,
                memos=[{"memo": {"memo_data": memo.encode().hex()}}] if memo else None
            )
            
            # Submit transaction
            logger.info(f"Submitting RLUSD payment: {amount_usd} USD to {destination[:10]}...")
            
            response = xrpl.transaction.submit_and_wait(
                payment,
                self.client,
                wallet
            )
            
            # Initialize result safely before use
            result = response.result if response and hasattr(response, 'result') else {}
            
            if response.is_successful():
                logger.info(f"RLUSD settlement confirmed: {result.get('hash', 'unknown')}")
                
                return SettlementResult(
                    success=True,
                    hash=result.get("hash", ""),
                    ledger_index=result.get("ledger_index", 0),
                    validated=result.get("validated", False),
                    amount_usd=amount_usd,
                    destination=destination,
                    network=self.network,
                    fee_drops=result.get("Fee")
                )
            else:
                error = result.get("engine_result", "Unknown")
                logger.error(f"RLUSD settlement failed: {error}")
                return SettlementResult(
                    success=False,
                    error=f"XRPL transaction failed: {error}",
                    network=self.network
                )
                
        except Exception as e:
            logger.error(f"Settlement error: {e}")
            return SettlementResult(
                success=False,
                error=str(e),
                network=self.network
            )
    
    def check_account_exists(self, address: str) -> bool:
        """
        Check if XRPL account exists.
        
        Args:
            address: XRPL account address
            
        Returns:
            True if account exists
        """
        try:
            response = self.client.request(
                xrpl.models.requests.AccountInfo(account=address)
            )
            return response.is_successful()
        except Exception:
            return False
    
    def get_rlusd_balance(self, address: str) -> float:
        """
        Get RLUSD balance for an account.
        
        Args:
            address: XRPL account address
            
        Returns:
            RLUSD balance (0.0 if none)
        """
        try:
            response = self.client.request(
                xrpl.models.requests.AccountLines(
                    account=address,
                    ledger_index="validated"
                )
            )
            
            if response.is_successful():
                lines = response.result.get("lines", [])
                for line in lines:
                    if line.get("currency") == "RLUSD" and line.get("account") == self.rlusd_issuer:
                        return float(line.get("balance", 0))
            return 0.0
        except Exception as e:
            logger.warning(f"Balance check failed: {e}")
            return 0.0
    
    def get_xrp_balance(self, address: str) -> float:
        """
        Get XRP balance for an account.
        
        Args:
            address: XRPL account address
            
        Returns:
            XRP balance
        """
        try:
            response = self.client.request(
                xrpl.models.requests.AccountInfo(
                    account=address,
                    ledger_index="validated"
                )
            )
            
            if response.is_successful():
                balance_drops = int(response.result["account_data"]["Balance"])
                return drops_to_xrp(balance_drops)
            return 0.0
        except Exception as e:
            logger.warning(f"XRP balance check failed: {e}")
            return 0.0
    
    def has_trust_line(self, address: str) -> bool:
        """
        Check if account has RLUSD trust line.
        
        Args:
            address: XRPL account address
            
        Returns:
            True if trust line exists
        """
        try:
            response = self.client.request(
                xrpl.models.requests.AccountLines(
                    account=address,
                    issuer=self.rlusd_issuer
                )
            )
            
            if response.is_successful():
                lines = response.result.get("lines", [])
                return any(line.get("currency") == "RLUSD" for line in lines)
            return False
        except Exception:
            return False
    
    async def fund_testnet_account(self, wallet: Wallet) -> bool:
        """
        Fund a testnet account from the faucet.
        
        Args:
            wallet: Wallet to fund
            
        Returns:
            True if funding successful
        """
        if self.network != "testnet":
            logger.warning("Funding only available on testnet")
            return False
        
        try:
            # Use XRPL testnet faucet
            import requests
            response = requests.post(
                "https://faucet.altnet.rippletest.net/accounts",
                json={"destination": wallet.address},
                timeout=30  # APEX: Always specify timeout for external requests
            )
            
            if response.status_code == 200:
                logger.info(f"Testnet account funded: {wallet.address}")
                return True
            return False
        except Exception as e:
            logger.error(f"Failed to fund testnet account: {e}")
            return False


# Helper function for quick settlement
async def send_rlusd(
    wallet_seed: str,
    destination: str,
    amount_usd: float,
    network: Literal["testnet", "mainnet"] = "testnet"
) -> SettlementResult:
    """
    Quick helper for RLUSD settlement.
    
    Args:
        wallet_seed: Sender wallet seed
        destination: Recipient address
        amount_usd: Amount in USD
        network: XRPL network
        
    Returns:
        SettlementResult
    """
    settlement = RLUSDSettlement(network=network)
    return await settlement.settle_rlusd(
        wallet_seed=wallet_seed,
        destination=destination,
        amount_usd=amount_usd
    )
