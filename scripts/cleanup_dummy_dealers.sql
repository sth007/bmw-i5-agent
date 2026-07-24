SELECT
    id,
    bmw_dealer_id,
    name,
    city,
    email,
    is_published,
    created_at,
    updated_at
FROM public.dealer
WHERE email ILIKE '%@example.com'
   OR name ~ '^Dealer [0-9]+$'
ORDER BY id ASC;

DELETE FROM public.dealer
WHERE name ~ '^Dealer [0-9]+$'
  AND email ILIKE 'dealer%@example.com'
  AND bmw_dealer_id LIKE 'dealer-%';

SELECT
    COUNT(*) AS remaining_dummy_dealers
FROM public.dealer
WHERE email ILIKE '%@example.com'
   OR name ~ '^Dealer [0-9]+$';
