SELECT
    order_id,
    customer_id,
    amount,
    currency,
    order_timestamp,
    order_status
FROM {{ source('silver', 'orders') }}