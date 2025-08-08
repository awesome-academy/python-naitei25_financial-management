# views.py
from django.shortcuts import render
from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator
from django.db.models import Q, Prefetch
from django.utils import timezone
from ...models import (
    Bill,
    RoomResident,
    PaymentHistory,
    BillAdditionalService,
    RentalPrice,
)


@login_required
def resident_bill_history(request):
    """
    View hiển thị lịch sử hóa đơn của cư dân
    Bao gồm tất cả hóa đơn của các phòng mà cư dân đang ở và đã từng ở
    """
    user = request.user

    # Lấy tất cả các phòng mà user đang ở và đã từng ở
    room_residents = RoomResident.objects.filter(user=user).select_related(
        "room"
    )

    # Tạo danh sách các điều kiện để lọc bill
    bill_conditions = Q()

    for room_resident in room_residents:
        room = room_resident.room
        move_in_date = room_resident.move_in_date
        move_out_date = room_resident.move_out_date

        # Điều kiện cơ bản: bill thuộc về phòng này
        room_condition = Q(room=room)

        # Nếu vẫn đang ở (move_out_date = None)
        if move_out_date is None:
            # Lấy tất cả bill từ ngày move_in đến hiện tại
            room_condition &= Q(bill_month__gte=move_in_date)
        else:
            # Nếu đã chuyển đi, chỉ lấy bill trong khoảng thời gian ở
            room_condition &= Q(
                bill_month__gte=move_in_date, bill_month__lte=move_out_date
            )

        bill_conditions |= room_condition

    # Lấy tất cả bill thỏa mãn điều kiện - chỉ select_related room
    bills = (
        Bill.objects.filter(bill_conditions)
        .select_related("room")
        .order_by("-bill_month")
    )

    # Lấy thông tin rental price cho từng bill
    bills_with_rent = []
    for bill in bills:
        # Tìm rental price hiệu lực tại thời điểm bill_month
        rental_price = (
            RentalPrice.objects.filter(
                room=bill.room, effective_date__lte=bill.bill_month
            )
            .order_by("-effective_date")
            .first()
        )

        # Thêm thông tin rental price vào bill
        bill.rent_amount = rental_price.price if rental_price else None
        bills_with_rent.append(bill)

    # Phân trang: 10 hóa đơn/trang
    paginator = Paginator(bills_with_rent, 10)
    page_number = request.GET.get("page")
    page_obj = paginator.get_page(page_number)

    # Lấy thống kê tổng quan từ bills gốc
    total_bills = len(bills_with_rent)
    paid_bills = len(
        [bill for bill in bills_with_rent if bill.status == "paid"]
    )
    unpaid_bills = len(
        [
            bill
            for bill in bills_with_rent
            if bill.status == "unpaid" or bill.status == "overdue"
        ]
    )

    context = {
        "page_obj": page_obj,
        "total_bills": total_bills,
        "paid_bills": paid_bills,
        "unpaid_bills": unpaid_bills,
    }

    return render(request, "resident/bill_history.html", context)
