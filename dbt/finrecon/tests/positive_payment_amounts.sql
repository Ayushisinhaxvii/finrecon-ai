SELECT *
FROM {{ ref('stg_payments') }}
WHERE amount <= 0
