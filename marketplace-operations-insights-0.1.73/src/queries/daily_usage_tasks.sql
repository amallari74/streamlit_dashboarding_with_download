select
    date_trunc ('day', run_on) as running_day,
    status,
    count(*)
from
    cc.arrears_task at2
where
    running_day > dateadd (day, -60, current_date)
    and method = 'createUsageRecordsForSubscription'
group by
    running_day,
    status;