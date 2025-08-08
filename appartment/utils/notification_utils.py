from datetime import datetime

from django.db.models import Q
from django.core.paginator import Paginator
from django.utils.translation import gettext as _
from django.contrib import messages


def filter_notifications(request, base_query):
    """
    Helper function để lọc, tìm kiếm và phân trang thông báo.
    Args:
        request: Request object chứa các tham số GET.
        base_query: QuerySet cơ bản của thông báo theo role.
    Returns:
        context: chứa danh sách thông báo phân trang và context.
    """
    # Lấy các tham số từ GET
    sort_by = request.GET.get("sort_by", "newest")
    filter_type = request.GET.get("filter_type", "all")
    filter_month = request.GET.get("filter_month", "")
    filter_date = request.GET.get("filter_date", "")
    search_query = request.GET.get("search_query", "")

    notifications = base_query

    # Lọc theo tháng
    if filter_month:
        try:
            year, month = map(int, filter_month.split("-"))
            notifications = notifications.filter(
                created_at__year=year, created_at__month=month
            )
        except ValueError:
            messages.error(request, _("Định dạng tháng không hợp lệ."))

    # Lọc theo ngày
    if filter_date:
        try:
            date = datetime.strptime(filter_date, "%Y-%m-%d")
            notifications = notifications.filter(created_at__date=date)
        except ValueError:
            messages.error(request, _("Định dạng ngày không hợp lệ."))

    # Tìm kiếm
    if search_query:
        notifications = notifications.filter(
            Q(title__icontains=search_query)
            | Q(message__icontains=search_query)
            | Q(sender__full_name__icontains=search_query)
        )

    # Sắp xếp
    if sort_by == "newest":
        notifications = notifications.order_by("-created_at")
    elif sort_by == "oldest":
        notifications = notifications.order_by("created_at")

    # Phân trang
    paginator = Paginator(notifications, 10)
    page_number = request.GET.get("page")
    page_obj = paginator.get_page(page_number)

    context = {
        "notifications": page_obj,
        "sort_by": sort_by,
        "filter_type": filter_type,
        "filter_month": filter_month,
        "filter_date": filter_date,
        "search_query": search_query,
    }
    return context
