SELECT
    p.payment_id,
    o.order_id,

    o.amount AS order_amount,
    p.payment_amount,
    p.refund_amount,
    p.settlement_amount,

    o.currency AS order_currency,
    p.currency AS payment_currency,

    o.order_status,
    p.payment_status,

    CASE
        WHEN p.payment_id IS NULL THEN 'MISSING_PAYMENT'
        WHEN p.payment_amount != o.amount THEN 'PAYMENT_AMOUNT_MISMATCH'
        WHEN p.currency != o.currency THEN 'CURRENCY_MISMATCH'
        WHEN p.settlement_amount != p.payment_amount - p.refund_amount
            THEN 'SETTLEMENT_MISMATCH'
        ELSE 'RECONCILED'
    END AS reconciliation_status

FROM {{ ref('stg_orders') }} AS o

LEFT JOIN {{ ref('int_payment_summary') }} AS p
    ON o.order_id = p.order_id