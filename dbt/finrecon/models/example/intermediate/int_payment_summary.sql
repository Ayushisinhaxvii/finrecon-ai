WITH refund_summary AS (

    SELECT
        payment_id,
        SUM(refund_amount) AS refund_amount
    FROM {{ ref('stg_refunds') }}
    GROUP BY payment_id

),

settlement_summary AS (

    SELECT
        payment_id,
        SUM(settlement_amount) AS settlement_amount
    FROM {{ ref('stg_settlements') }}
    GROUP BY payment_id

)

SELECT
    p.payment_id,
    p.order_id,
    p.amount AS payment_amount,
    p.currency,
    p.payment_status,
    p.payment_timestamp,
    COALESCE(r.refund_amount, 0) AS refund_amount,
    COALESCE(s.settlement_amount, 0) AS settlement_amount

FROM {{ ref('stg_payments') }} AS p

LEFT JOIN refund_summary AS r
    ON p.payment_id = r.payment_id

LEFT JOIN settlement_summary AS s
    ON p.payment_id = s.payment_id