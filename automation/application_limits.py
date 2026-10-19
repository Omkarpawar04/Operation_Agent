DAILY_APPLICATION_LIMIT = 5


def has_reached_daily_limit(confirmed_count):
    return confirmed_count >= DAILY_APPLICATION_LIMIT
