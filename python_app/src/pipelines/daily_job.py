from datetime import date
def run_daily(asof: date | None = None):
    # TODO: orchestrate ingestion -> features -> screening -> scoring -> save -> summarize -> alert
    print("Daily job executed (stub).")

if __name__ == "__main__":
    run_daily()
