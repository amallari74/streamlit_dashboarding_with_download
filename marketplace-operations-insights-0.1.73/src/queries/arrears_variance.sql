with
    arrears_variance as (
        select
            pr.vendor,
            date_trunc ('MONTH', cli.provision_start) as provision_month,
            round(
                sum(
                    case date_trunc ('MONTH', cli.provision_start)
                        WHEN date_trunc ('MONTH', current_date + interval '-1 Month') THEN cli.pax8_gross_revenue
                        Else 0
                    end
                ),
                2
            ) as prior_month_gross_revenue,
            round(
                sum(
                    case date_trunc ('MONTH', cli.provision_start)
                        WHEN date_trunc ('MONTH', current_date) THEN cli.pax8_gross_revenue
                        Else 0
                    end
                ),
                2
            ) as current_month_gross_revenue,
            round(
                current_month_gross_revenue - prior_month_gross_revenue,
                2
            ) as gross_revenue_difference,
            bu.name as business_unit,
            cli.currency_id,
            case
                when c.api_code = 'USD' then 1
                when c.api_code = 'CAD' then 0.74
                when c.api_code = 'GBP' then 1.24
                when c.api_code = 'EUR' then 1.07
                when c.api_code = 'NOK' then 0.091
                when c.api_code = 'SEK' then 0.092
                when c.api_code = 'DKK' then 0.14
                when c.api_code = 'AUD' then 0.66
                when c.api_code = 'NZD' then 0.61
                when c.api_code = 'THB' then 0.029
                when c.api_code = 'IDR' then 0.000067
                when c.api_code = 'MYR' then 0.22
                when c.api_code = 'SGD' then 0.74
                when c.api_code = 'VND' then 0.000043
                when c.api_code = 'PHP' then 0.018
                else 1.00
            end as exhange_rate_multiple,
            exhange_rate_multiple * prior_month_gross_revenue as usd_prior_month_revenue,
            exhange_rate_multiple * current_month_gross_revenue as usd_current_month_gross_revenue,
            exhange_rate_multiple * gross_revenue_difference as usd_gross_revenue_difference
        from
            cc.subscription s
            inner join cc.completed_line_item cli on s.id = cli.arrears_subscription_id
            inner join cc.partner p on s.partner_id = p.id
            inner join cc.product pr on s.product_id = pr.id
            inner join cc.business_unit bu on p.business_unit_guid = bu.guid
            inner join cc.currency c on cli.currency_id = c.id
        where
            cli.voided = 'f'
            and cli.arrears_subscription_id is not null
            and cli.provision_start >= date_trunc ('MONTH', current_date + interval '-1 Month')
        group by
            pr.vendor,
            bu.name,
            cli.currency_id,
            cli.provision_start,
            c.api_code
        order by
            gross_revenue_difference desc
    )
select
    ar.vendor,
    ar.business_unit,
    sum(ar.usd_prior_month_revenue) as usd_prior_month_revenue,
    sum(ar.usd_current_month_gross_revenue) as usd_current_month_gross_revenue,
    sum(ar.usd_gross_revenue_difference) as usd_gross_revenue_difference
from
    arrears_variance ar
group by
    ar.vendor,
    ar.business_unit
order by
    ar.vendor;