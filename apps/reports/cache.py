from django.core.cache import cache


FORM_REPORT_CACHE_TIMEOUT = 60 * 5
PROCESS_REPORT_CACHE_TIMEOUT = 60 * 5


def get_form_report_cache_key(form_id):
    return f"report:form:{form_id}"


def get_process_report_cache_key(process_id):
    return f"report:process:{process_id}"


def get_form_report(form_id):
    return cache.get(get_form_report_cache_key(form_id))


def set_form_report(form_id, data):
    cache.set(
        get_form_report_cache_key(form_id),
        data,
        FORM_REPORT_CACHE_TIMEOUT,
    )


def invalidate_form_report(form_id):
    cache.delete(get_form_report_cache_key(form_id))


def get_process_report(process_id):
    return cache.get(get_process_report_cache_key(process_id))


def set_process_report(process_id, data):
    cache.set(
        get_process_report_cache_key(process_id),
        data,
        PROCESS_REPORT_CACHE_TIMEOUT,
    )


def invalidate_process_report(process_id):
    cache.delete(get_process_report_cache_key(process_id))