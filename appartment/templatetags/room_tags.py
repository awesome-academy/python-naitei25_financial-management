from django import template
from django.utils.html import format_html

register = template.Library()


@register.simple_tag
def status_badge(status):
    if status == "Đang ở":
        return format_html(
            '<span class="bg-green-100 text-green-800 text-sm font-semibold px-3 py-1 rounded-full">{}</span>',
            status,
        )
    else:
        return format_html(
            '<span class="bg-red-100 text-red-800 text-sm font-semibold px-3 py-1 rounded-full">{}</span>',
            status,
        )
