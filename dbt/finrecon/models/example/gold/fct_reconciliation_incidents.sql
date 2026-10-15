
{{ config(materialized='table') }}

SELECT
    payment_id,
    order_id,

    reconciliation_status AS incident_type,

    order_amount,
    payment_amount,
    refund_amount,
    settlement_amount,

    order_currency,
    payment_currency,

    order_status,
    payment_status,

    'OPEN' AS incident_status,

    CASE
        WHEN reconciliation_status IN (
            'MISSING_PAYMENT',
            'PAYMENT_AMOUNT_MISMATCH',
            'CURRENCY_MISMATCH'
        ) THEN 'HIGH'
        WHEN reconciliation_status = 'SETTLEMENT_MISMATCH'
            THEN 'MEDIUM'
        ELSE 'LOW'
    END AS incident_severity,

    CASE
        WHEN reconciliation_status = 'MISSING_PAYMENT'
            THEN 'No matching payment record was found for this order.'
        WHEN reconciliation_status = 'PAYMENT_AMOUNT_MISMATCH'
            THEN 'The payment amount differs from the order amount.'
        WHEN reconciliation_status = 'CURRENCY_MISMATCH'
            THEN 'The order currency differs from the payment currency.'
        WHEN reconciliation_status = 'SETTLEMENT_MISMATCH'
            THEN 'The settlement amount differs from payment minus refund.'
        ELSE 'Investigate the reconciliation discrepancy.'
    END AS suspected_cause,

    CASE
        WHEN reconciliation_status = 'MISSING_PAYMENT'
            THEN 'Check payment ingestion and the payment provider records.'
        WHEN reconciliation_status = 'PAYMENT_AMOUNT_MISMATCH'
            THEN 'Compare the order total with the payment provider transaction.'
        WHEN reconciliation_status = 'CURRENCY_MISMATCH'
            THEN 'Verify currency codes and currency conversion handling.'
        WHEN reconciliation_status = 'SETTLEMENT_MISMATCH'
            THEN 'Compare payment, refund, and settlement records.'
        ELSE 'Review the source records and reconciliation details.'
    END AS recommended_action

FROM {{ ref('fct_reconciliation') }}

WHERE reconciliation_status != 'RECONCILED'
