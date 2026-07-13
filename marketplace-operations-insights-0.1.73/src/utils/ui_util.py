from datetime import datetime, timedelta


def load_date_selector_values():
    start_date = datetime(2023, 1, 1)
    current_date = datetime.now()

    dates_dict = {}
    while start_date <= current_date:
        # Key in 'Mon YYYY' format
        key = start_date.strftime("%b %Y")
        # Value in 'YYYY-MM-DD' format
        value = start_date.strftime("%Y-%m-%d")
        dates_dict[key] = value

        # Move to the first day of the next month
        next_month = start_date.replace(day=28) + timedelta(
            days=4
        )  # this will never fail
        start_date = next_month.replace(day=1)
    return dates_dict
