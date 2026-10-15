SELECT
    settlement_id,
    payment_id,
    settlement_amount,
    settlement_date,
    settlement_status
FROM {{ source('silver', 'settlements') }}