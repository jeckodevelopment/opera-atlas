"""Presentation-only templates for Opera+ Atlas publication diagnostics.

Email-client-compatible table layout with inline styling and a plain-text fallback.
"""
from __future__ import annotations

from html import escape
from datetime import date, datetime

MONTHS_IT = ("gennaio", "febbraio", "marzo", "aprile", "maggio", "giugno", "luglio", "agosto", "settembre", "ottobre", "novembre", "dicembre")


def performance_labels(notice: dict) -> list[str]:
    """Only future published dates; never infer an unknown performance time."""
    if notice.get("kind") != "Nuova produzione":
        return []
    labels = []
    for performance in notice.get("performances", []):
        try:
            day = date.fromisoformat(performance["local_date"])
        except (KeyError, TypeError, ValueError):
            continue
        if day < date.today() or performance.get("status") == "cancelled":
            continue
        label = f"{day.day} {MONTHS_IT[day.month - 1]} {day.year}"
        if performance.get("time_known") and performance.get("starts_at"):
            try:
                time = datetime.fromisoformat(performance["starts_at"]).strftime("%H:%M")
                label += f" · ore {time}"
            except (TypeError, ValueError):
                pass
        labels.append((day, label))
    labels.sort(key=lambda item: (item[0], item[1]))
    return [label for _, label in labels]


def render_email(notice: dict) -> tuple[str, str]:
    """Return (HTML, plain text); escape all data taken from catalog records."""
    kind = str(notice["kind"])
    title = str(notice["title"])
    identifier = str(notice["id"])
    details = str(notice["details"])
    url = str(notice["url"])
    if not url.startswith("https://opera.plus/atlas/"):
        raise ValueError("notification URL must point to canonical Atlas")
    e = lambda value: escape(value, quote=True)
    labels = performance_labels(notice)
    recite_html = ""
    recite_plain = ""
    if kind == "Nuova produzione":
        recite_plain = "\\nRecite previste:\\n" + ("\\n".join(f"- {label}" for label in labels) if labels else "Date non ancora disponibili") + "\\n"
        items = "".join(f'<li style="padding:3px 0;">{e(label)}</li>' for label in labels)
        contents = f'<ul style="margin:8px 0;padding-left:20px;">{items}</ul>' if labels else "Date non ancora disponibili"
        recite_html = f'<tr><td style="padding:8px 0 16px;font-size:12px;color:#727272;vertical-align:top;">Recite</td><td style="padding:8px 0 16px;font-size:14px;line-height:1.6;color:#242424;">{contents}</td></tr>'
    html = f"""<!doctype html>
<html lang="it">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>{e(kind)} — Opera+ Atlas</title>
</head>
<body style="margin:0;padding:0;background:#f4f4f2;font-family:Arial,Helvetica,sans-serif;color:#212121;">
  <div style="display:none;font-size:1px;color:#f4f4f2;line-height:1px;max-height:0;max-width:0;opacity:0;overflow:hidden;">
    {e(kind)}: {e(title)}. Pubblicazione nel catalogo Opera+ Atlas.
  </div>
  <table role="presentation" cellpadding="0" cellspacing="0" border="0" width="100%" style="background:#f4f4f2;">
    <tr><td align="center" style="padding:30px 12px;">
      <table role="presentation" cellpadding="0" cellspacing="0" border="0" width="100%" style="max-width:600px;background:#ffffff;border:1px solid #e6e2d9;">
        <tr><td style="padding:26px 32px;background:#151515;text-align:center;">
          <span style="font-weight:700;font-size:22px;letter-spacing:2px;color:#ffffff;">OPERA</span><span style="font-weight:700;font-size:22px;letter-spacing:2px;color:#c9a65a;">+ ATLAS</span>
        </td></tr>
        <tr><td style="padding:32px 32px 12px;">
          <p style="margin:0 0 12px;font-size:12px;font-weight:700;text-transform:uppercase;letter-spacing:1.5px;color:#8b6a2c;">Notifica diagnostica di pubblicazione</p>
          <h1 style="margin:0 0 12px;font-size:27px;line-height:1.25;font-weight:700;color:#171717;">{e(kind)}</h1>
          <p style="margin:0;font-size:19px;line-height:1.5;color:#333333;">{e(title)}</p>
        </td></tr>
        <tr><td style="padding:15px 32px 8px;">
          <table role="presentation" width="100%" cellpadding="0" cellspacing="0" border="0" style="border-top:1px solid #e9e5dc;">
            <tr><td style="padding:18px 0 8px;font-size:12px;color:#727272;vertical-align:top;width:80px;">ID</td>
                <td style="padding:18px 0 8px;font-size:14px;color:#242424;overflow-wrap:anywhere;">{e(identifier)}</td></tr>
            <tr><td style="padding:8px 0 16px;font-size:12px;color:#727272;vertical-align:top;">Dettagli</td>
                <td style="padding:8px 0 16px;font-size:14px;line-height:1.6;color:#242424;">{e(details)}</td></tr>
            {recite_html}
          </table>
        </td></tr>
        <tr><td align="center" style="padding:12px 32px 36px;">
          <a href="{e(url)}" style="display:inline-block;background:#aa853e;border:1px solid #aa853e;border-radius:4px;padding:15px 23px;font-size:14px;font-weight:700;text-decoration:none;color:#ffffff;">Apri la scheda su Opera+ Atlas</a>
        </td></tr>
        <tr><td style="padding:20px 32px;background:#f8f7f4;border-top:1px solid #e9e5dc;">
          <p style="margin:0;font-size:12px;line-height:1.65;color:#686868;">Messaggio automatico a fini diagnostici, generato dopo la pubblicazione di una nuova scheda nel catalogo. Nessuna azione richiesta.</p>
        </td></tr>
      </table>
    </td></tr>
  </table>
</body>
</html>"""
    plain = (
        f"OPERA+ ATLAS — Notifica diagnostica di pubblicazione\n\n"
        f"{kind}\n{title}\n\nID: {identifier}\nDettagli: {details}\n\n"
        f"{recite_plain}\nApri la scheda: {url}\n\n"
        "Messaggio automatico a fini diagnostici. Nessuna azione richiesta.\n"
    )
    return html, plain
