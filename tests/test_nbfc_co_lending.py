import unittest
from nbfc_co_lending.engine import CoLendingLoanAccount, FLDGCoverContract, NBFCCoLendingFLDGEngine

class TestNBFCCoLendingFLDGEngine(unittest.TestCase):
    def setUp(self):
        contract = FLDGCoverContract(
            contract_id="FLDG/SBI-FIN/2026/01", bank_partner="State Bank of India",
            total_pool_principal=100000000.0, max_fldg_cap_pct=5.0
        )
        self.engine = NBFCCoLendingFLDGEngine(contract)

    def test_co_lending_disbursement_split(self):
        loan = CoLendingLoanAccount(
            loan_account_no="CL-2026-0081", borrower_name="Apex Logistics LLP",
            borrower_pan="AAAFB9981K", disbursed_principal=5000000.0,
            bank_share_pct=80.0, nbfc_share_pct=20.0
        )
        res = self.engine.book_co_lending_loan(loan)
        self.assertEqual(res["bank_disbursement_share"], 4000000.0)
        self.assertEqual(res["nbfc_disbursement_share"], 1000000.0)

    def test_waterfall_settlement(self):
        loan = CoLendingLoanAccount(
            loan_account_no="CL-2026-0082", borrower_name="Surya Microtech",
            borrower_pan="AAAFS1122M", disbursed_principal=1000000.0
        )
        self.engine.book_co_lending_loan(loan)
        settlement = self.engine.process_daily_emi_waterfall(
            loan_account_no="CL-2026-0082", emi_amount_received=34000.0,
            interest_component=12000.0, principal_component=22000.0
        )
        self.assertEqual(settlement["bank_payout"]["total"], round(0.8 * 34000.0, 2))
        self.assertEqual(settlement["nbfc_payout"]["total"], round(0.2 * 34000.0, 2))

    def test_fldg_invocation(self):
        res = self.engine.invoke_fldg_for_default("CL-2026-0082", 200000.0)
        self.assertEqual(res["invoked_amount"], 200000.0)
        self.assertFalse(res["fldg_cap_breached"])

if __name__ == "__main__":
    unittest.main()
