# -*- coding: utf-8 -*-
"""
Fee Calculator - Calculate trading fees

Fee types:
- Commission: Broker fee (default 0.03%)
- Stamp tax: Government tax on sell (0.1%)
- Transfer fee: Stock transfer fee (0.002%)
"""

from dataclasses import dataclass
from typing import Optional
import logging

logger = logging.getLogger(__name__)


@dataclass
class FeeConfig:
    """Trading fee configuration"""
    commission_rate: float = 0.0003
    stamp_tax_rate: float = 0.001
    transfer_fee_rate: float = 0.00002
    min_commission: float = 5.0


@dataclass
class FeeResult:
    """Fee calculation result"""
    commission: float
    stamp_tax: float
    transfer_fee: float
    total_fee: float
    total_amount: float


class FeeCalculator:
    """Calculate trading fees"""
    
    def __init__(self, config: Optional[FeeConfig] = None):
        self.config = config or FeeConfig()
    
    def calculate_buy_fee(self, amount: float) -> FeeResult:
        """
        Calculate fees for buy order
        
        Args:
            amount: Trade amount in yuan
        
        Returns:
            FeeResult with fee breakdown
        """
        commission = max(amount * self.config.commission_rate, self.config.min_commission)
        stamp_tax = 0.0
        transfer_fee = amount * self.config.transfer_fee_rate
        
        total_fee = commission + stamp_tax + transfer_fee
        total_amount = amount + total_fee
        
        return FeeResult(
            commission=commission,
            stamp_tax=stamp_tax,
            transfer_fee=transfer_fee,
            total_fee=total_fee,
            total_amount=total_amount,
        )
    
    def calculate_sell_fee(self, amount: float) -> FeeResult:
        """
        Calculate fees for sell order
        
        Args:
            amount: Trade amount in yuan
        
        Returns:
            FeeResult with fee breakdown
        """
        commission = max(amount * self.config.commission_rate, self.config.min_commission)
        stamp_tax = amount * self.config.stamp_tax_rate
        transfer_fee = amount * self.config.transfer_fee_rate
        
        total_fee = commission + stamp_tax + transfer_fee
        total_amount = amount - total_fee
        
        return FeeResult(
            commission=commission,
            stamp_tax=stamp_tax,
            transfer_fee=transfer_fee,
            total_fee=total_fee,
            total_amount=total_amount,
        )
    
    def calculate_trade_fee(
        self,
        shares: int,
        price: float,
        trade_type: str,
    ) -> FeeResult:
        """
        Calculate fees for a trade
        
        Args:
            shares: Number of shares
            price: Price per share
            trade_type: 'buy' or 'sell'
        
        Returns:
            FeeResult with fee breakdown
        """
        amount = shares * price
        
        if trade_type.lower() == "buy":
            return self.calculate_buy_fee(amount)
        else:
            return self.calculate_sell_fee(amount)
