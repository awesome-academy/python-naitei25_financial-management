from datetime import datetime

from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.utils.translation import gettext as _
from django.views.decorators.http import require_POST
from django.views.decorators.csrf import csrf_protect
from django.db.models import Q
from django.core.paginator import Paginator

from ..models import Notification
from ..constants import NotificationStatus, UserRole
from ..utils.permissions import role_required
from ..utils.notification_utils import filter_notifications

"""
sender: ROLE_RESIDENT -> receiver: null (ROLE_ADMIN + ROLE_APARTMENT_MANAGER)
sender: ROLE_APARTMENT_MANAGER -> receiver: ROLE_RESIDENT | ROLE_ADMIN
sender: ROLE_ADMIN -> receiver: ROLE_APARTMENT_MANAGER 
"""


@login_required
@role_required(UserRole.RESIDENT.value)
def resident_notification_history(request):
    """
    Hiển thị lịch sử thông báo cho người thuê.
    """
    notifications = Notification.objects.filter(
        receiver=request.user  # Chỉ lấy thông báo gửi đến người thuê
    ).select_related("sender", "receiver")

    context = filter_notifications(request, notifications)
    context["filter_type"] = "to_me"  # Chỉ có một loại: gửi đến người thuê
    return render(request, "resident/notifications/history_notifications.html", context)


@login_required
@role_required(UserRole.APARTMENT_MANAGER.value)
def manager_notification_history(request):
    """
    Hiển thị lịch sử thông báo cho người quản lý chung cư.
    """
    notifications = Notification.objects.filter(
        Q(
            receiver__isnull=True, sender__role__role_name=UserRole.RESIDENT.value
        )  # Từ người thuê gửi lên hệ thống
        | Q(receiver=request.user)  # Dành riêng cho chính người quản lý
        | Q(
            sender=request.user
        )  # Do chính người quản lý gửi (gán phòng, rời phòng, ...)
    ).select_related("sender", "receiver")

    # Lọc theo loại thông báo
    filter_type = request.GET.get("filter_type", "all")
    if filter_type == "from_resident":
        notifications = notifications.filter(
            receiver__isnull=True, sender__role__role_name=UserRole.RESIDENT.value
        )
    elif filter_type == "from_admin":
        notifications = notifications.filter(
            sender__role__role_name=UserRole.ADMIN.value
        )
    elif filter_type == "to_manager":
        notifications = notifications.filter(receiver=request.user)
    elif filter_type == "by_manager":
        notifications = notifications.filter(sender=request.user)

    context = filter_notifications(request, notifications)
    return render(request, "manager/notifications/history_notifications.html", context)


@login_required
@role_required(UserRole.ADMIN.value)
def admin_notification_history(request):
    """
    Hiển thị lịch sử thông báo cho admin.
    """
    notifications = Notification.objects.filter(
        Q(receiver=request.user)  # Dành riêng cho admin
        | Q(sender=request.user)  # Do admin gửi
    ).select_related("sender", "receiver")

    filter_type = request.GET.get("filter_type", "all")
    if filter_type == "to_admin":
        notifications = notifications.filter(receiver=request.user)
    elif filter_type == "by_admin":
        notifications = notifications.filter(sender=request.user)

    context = filter_notifications(request, notifications)
    return render(request, "admin/notifications/history_notifications.html", context)


@require_POST
@login_required
@csrf_protect
def mark_notification_read(request, notification_id):
    """
    Đánh dấu thông báo là đã đọc.
    """
    notification = get_object_or_404(Notification, pk=notification_id)

    # Kiểm tra quyền truy cập thông báo
    if not (
        (
            notification.receiver is None
            and notification.sender.role.role_name == UserRole.RESIDENT.value
        )
        or (notification.sender.role.role_name == UserRole.ADMIN.value)
        or (notification.receiver == request.user)
        or (notification.sender == request.user)
    ):
        messages.error(request, _("Bạn không có quyền xem thông báo này."))
        return redirect("notification_history")

    notification.status = NotificationStatus.READ.value
    notification.save()
    messages.success(request, _("Thông báo đã được đánh dấu là đã đọc."))

    role = request.user.role.role_name
    if role == UserRole.RESIDENT.value:
        return redirect("resident_notification_history")
    elif role == UserRole.APARTMENT_MANAGER.value:
        return redirect("manager_notification_history")
    elif role == UserRole.ADMIN.value:
        return redirect("admin_notification_history")
    return redirect("dashboard")
