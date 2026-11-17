from markupsafe import Markup


def plain_to_html(text: str) -> str:
    lines = [line.strip() for line in (text or '').splitlines()]
    html = []
    for line in lines:
        if not line:
            html.append('<br/>')
        elif line.startswith(('📅', '👨‍⚕️', '🧪', '📞', '⏰', '📍', '📝', '✅', '⚠️')):
            html.append(f"<div style='font-weight:600;margin:6px 0'>{line}</div>")
        else:
            html.append(f"<div style='margin:2px 0'>{line}</div>")
    return ''.join(html)


def as_markup(text: str):
    return Markup(plain_to_html(text))
