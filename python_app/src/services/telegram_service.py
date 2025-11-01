def format_pick_telegram(pick, summary):
    line1 = f"[{pick['asof']}] {pick['strategy']} {pick['symbol']}"
    line2 = f"{pick['selected_option']}  ROI30d: {pick['roi_30d']:.2%}  IVR: {int(round(pick['ivr']))}%  Score: {pick['score']:.2f}"
    return "\n".join([line1, line2, f"Notes: {pick.get('notes','-')}", f"Summary: {summary}"])

def send_telegram(message: str) -> bool:
    # TODO: implement requests.post to Telegram bot
    return True
