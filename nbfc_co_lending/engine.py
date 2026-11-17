"""RBI Co-Lending Model (CLM) & 5% First Loss Default Guarantee (FLDG) Engine."""
from dataclasses import dataclass, field
from datetime import datetime, date
from typing import List, Dict, Any, Optional

@dataclass
class CoLendingLoanAccount:
    loan_account_no: str
    borrower_name: str
    borrower_pan: str
    disbursed_principal: float
    bank_share_pct: float = 80.0       # Scheduled Commercial Bank share
    nbfc_share_pct: float = 20.0       # NBFC Originator share
    interest_rate_pct: float = 14.5
    tenure_months: int = 36
    outstanding_principal: float = 0.0
    dpd_days: int = 0
    status: str = "STANDARD"          # STANDARD, SMA_1, SMA_2, NPA

@dataclass
class FLDGCoverContract:
    contract_id: str
    bank_partner: str
    total_pool_principal: float
    max_fldg_cap_pct: float = 5.0      # Statutory RBI Cap max 5.0%
    invoked_fldg_amount: float = 0.0

class NBFCCoLendingFLDGEngine:
    def __init__(self, fldg_contract: FLDGCoverContract):
        self.contract = fldg_contract
        self.loans: Dict[str, CoLendingLoanAccount] = {}

    def book_co_lending_loan(self, loan: CoLendingLoanAccount) -> Dict[str, Any]:
        if abs((loan.bank_share_pct + loan.nbfc_share_pct) - 100.0) > 0.001:
            raise ValueError("Bank and NBFC share percentage must sum exactly to 100.0%.")
        loan.outstanding_principal = loan.disbursed_principal
        self.loans[loan.loan_account_no] = loan
        
        bank_portion = round(loan.disbursed_principal * (loan.bank_share_pct / 100.0), 2)
        nbfc_portion = round(loan.disbursed_principal * (loan.nbfc_share_pct / 100.0), 2)
        return {
            "loan_account_no": loan.loan_account_no,
            "total_principal": loan.disbursed_principal,
            "bank_disbursement_share": bank_portion,
            "nbfc_disbursement_share": nbfc_portion
        }

    def process_daily_emi_waterfall(self, loan_account_no: str, emi_amount_received: float, interest_component: float, principal_component: float) -> Dict[str, Any]:
        if loan_account_no not in self.loans:
            raise ValueError(f"Loan {loan_account_no} not found.")
        loan = self.loans[loan_account_no]
        
        bank_p = round(principal_component * (loan.bank_share_pct / 100.0), 2)
        nbfc_p = round(principal_component * (loan.nbfc_share_pct / 100.0), 2)
        bank_i = round(interest_component * (loan.bank_share_pct / 100.0), 2)
        nbfc_i = round(interest_component * (loan.nbfc_share_pct / 100.0), 2)

        loan.outstanding_principal = max(0.0, round(loan.outstanding_principal - principal_component, 2))
        return {
            "loan_account_no": loan_account_no,
            "bank_payout": {"principal": bank_p, "interest": bank_i, "total": round(bank_p + bank_i, 2)},
            "nbfc_payout": {"principal": nbfc_p, "interest": nbfc_i, "total": round(nbfc_p + nbfc_i, 2)},
            "remaining_principal": loan.outstanding_principal
        }

    def invoke_fldg_for_default(self, loan_account_no: str, default_principal: float) -> Dict[str, Any]:
        max_allowable_fldg = round(self.contract.total_pool_principal * (self.contract.max_fldg_cap_pct / 100.0), 2)
        remaining_fldg_cap = round(max_allowable_fldg - self.contract.invoked_fldg_amount, 2)
        
        if default_principal > remaining_fldg_cap:
            claimable = remaining_fldg_cap
            breach_warning = True
        else:
            claimable = default_principal
            breach_warning = False

        self.contract.invoked_fldg_amount += claimable
        return {
            "contract_id": self.contract.contract_id,
            "loan_account_no": loan_account_no,
            "invoked_amount": claimable,
            "total_fldg_invoked_so_far": self.contract.invoked_fldg_amount,
            "fldg_cap_breached": breach_warning,
            "remaining_fldg_cap": round(max_allowable_fldg - self.contract.invoked_fldg_amount, 2)
        }
