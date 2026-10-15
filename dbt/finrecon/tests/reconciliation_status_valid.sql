SELECT *
FROM {{ ref('fct_reconciliation') }}
WHERE reconciliation_status NOT IN (
    'RECONCILED',
    'MISSING_PAYMENT',
    'PAYMENT_AMOUNT_MISMATCH',
    'CURRENCY_MISMATCH',
    'SETTLEMENT_MISMATCH'
)