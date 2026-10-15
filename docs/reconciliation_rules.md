# FINRECON AI — Reconciliation Rules

## 1. Purpose

FINRECON AI reconciles orders, payments, refunds, and settlements to identify financial discrepancies.

## 2. Reconciliation Statuses

### RECONCILED
The payment amount matches the order amount, the order and payment currencies match, and the settlement amount equals the payment amount minus the refund amount.

### MISSING_PAYMENT
An order exists, but no matching payment record is available.

### PAYMENT_AMOUNT_MISMATCH
The payment amount differs from the order amount.

### CURRENCY_MISMATCH
The order currency differs from the payment currency.

### SETTLEMENT_MISMATCH
The settlement amount differs from the payment amount minus the refund amount.

## 3. Investigation Guidelines

- Identify the affected order and payment IDs.
- Compare the order amount with the payment amount.
- Compare the order currency with the payment currency.
- Check whether refunds have been accounted for in the settlement.
- Use database query results for financial facts; do not guess missing amounts.
- Do not modify financial records automatically.
- Require human approval before sensitive corrective actions.

## 4. Incident Severity

- HIGH: A missing payment requires investigation.
- MEDIUM: A settlement mismatch requires investigation.

These severity levels are the initial project rules and may be refined as the reconciliation policy evolves.
