from collections import defaultdict
from datetime import date, datetime
import calendar
import csv
import io
import os
import secrets
import zipfile

from flask import Flask, abort, flash, jsonify, redirect, render_template, request, send_file, send_from_directory, session, url_for
from werkzeug.utils import secure_filename

from config import Config
from models import PlaybookSetup, Trade, db

app = Flask(__name__)
app.config.from_object(Config)
db.init_app(app)
os.makedirs(app.config["UPLOAD_FOLDER"], exist_ok=True)

with app.app_context():
    db.create_all()


def allowed_file(filename):
    return "." in filename and filename.rsplit(".", 1)[1].lower() in app.config["ALLOWED_EXTENSIONS"]


def setting(name, default):
    try:
        with open(name, "r", encoding="utf-8") as file:
            value = file.read().strip()
            return value if value else default
    except FileNotFoundError:
        return default


def number_setting(name, default):
    try:
        return float(setting(name, str(default)))
    except ValueError:
        return float(default)


def currency():
    return setting("currency.txt", "USD")


def balance():
    return number_setting("balance.txt", 50000)


def profit_target():
    return number_setting("profit_target.txt", 3000)


def max_loss_limit():
    return number_setting("max_loss_limit.txt", 2000)


def daily_loss_limit():
    return number_setting("daily_loss_limit.txt", 1000)


def consistency_limit():
    return number_setting("consistency_limit.txt", 50)


TOPSTEP_PROFILES = {
    "custom": {"label": "Custom", "balance": None, "target": None, "max_loss": None, "daily_loss": None},
    "50k": {"label": "Topstep 50K", "balance": 50000, "target": 3000, "max_loss": 2000, "daily_loss": 1000},
    "100k": {"label": "Topstep 100K", "balance": 100000, "target": 6000, "max_loss": 3000, "daily_loss": 2000},
    "150k": {"label": "Topstep 150K", "balance": 150000, "target": 9000, "max_loss": 4500, "daily_loss": 3000},
}


def account_profile():
    value = setting("account_profile.txt", "custom")
    return value if value in TOPSTEP_PROFILES else "custom"


def csrf_token():
    if "csrf_token" not in session:
        session["csrf_token"] = secrets.token_hex(24)
    return session["csrf_token"]


app.jinja_env.globals["csrf_token"] = csrf_token


@app.before_request
def protect_post_requests():
    if request.method == "POST" and request.form.get("csrf_token") != session.get("csrf_token"):
        abort(400, description="Invalid or expired form token. Refresh the page and try again.")


def parse_float(value, default=0):
    try:
        if value is None or value == "":
            return default
        return float(value)
    except (TypeError, ValueError):
        return default


def required_float(value, label):
    if value is None or str(value).strip() == "":
        raise ValueError(f"{label} is required.")
    try:
        return float(value)
    except (TypeError, ValueError) as exc:
        raise ValueError(f"{label} must be a number.") from exc


def apply_trade_form(trade, form, use_current_datetime=False):
    now = datetime.now()
    date_value = (form.get("date") or "").strip()
    time_value = (form.get("time") or "").strip()

    if not date_value:
        if use_current_datetime:
            date_value = now.strftime("%Y-%m-%d")
        else:
            raise ValueError("Date is required.")
    if not time_value and use_current_datetime:
        time_value = now.strftime("%H:%M")

    trade.date = datetime.strptime(date_value, "%Y-%m-%d").date()
    if time_value:
        datetime.strptime(time_value, "%H:%M")
    trade.time = time_value

    instrument = (form.get("instrument") or "").strip().upper()
    if not instrument:
        raise ValueError("Instrument is required.")

    direction = (form.get("direction") or "Buy").strip()
    if direction not in {"Buy", "Sell", "Kupno", "Sprzedaż"}:
        raise ValueError("Direction must be Buy or Sell.")

    contracts = required_float(form.get("contracts"), "Contracts")
    if contracts <= 0:
        raise ValueError("Contracts must be greater than zero.")

    trade.session = form.get("session") or "Other"
    trade.instrument = instrument
    trade.direction = direction
    trade.contracts = contracts
    trade.entry_price = required_float(form.get("entry_price"), "Entry")
    trade.exit_price = required_float(form.get("exit_price"), "Exit")
    trade.stop_loss = parse_float(form.get("stop_loss"), None) if form.get("stop_loss") else None
    trade.take_profit = parse_float(form.get("take_profit"), None) if form.get("take_profit") else None
    trade.grade = form.get("grade") or ""
    trade.notes = form.get("notes") or ""
    trade.commission = max(0, parse_float(form.get("commission"), 0))
    trade.setup = (form.get("setup") or "").strip()
    trade.tags = (form.get("tags") or "").strip()
    trade.mistake = (form.get("mistake") or "").strip()
    trade.emotion_before = (form.get("emotion_before") or "").strip()
    trade.emotion_after = (form.get("emotion_after") or "").strip()
    trade.context = (form.get("context") or "").strip()


def save_uploaded_image(image):
    if not image or not image.filename:
        return None
    if not allowed_file(image.filename):
        raise ValueError("Unsupported screenshot format.")

    timestamp = datetime.now().strftime("%Y%m%d%H%M%S%f")
    filename = secure_filename(f"{timestamp}_{image.filename}")
    image.save(os.path.join(app.config["UPLOAD_FOLDER"], filename))
    return filename


def remove_uploaded_image(filename):
    if not filename:
        return
    try:
        os.remove(os.path.join(app.config["UPLOAD_FOLDER"], filename))
    except OSError:
        pass


def calc_stats(trades):
    total = sum(t.pnl() for t in trades)
    wins = [t for t in trades if t.pnl() > 0]
    losses = [t for t in trades if t.pnl() < 0]
    breakevens = [t for t in trades if t.pnl() == 0]

    gross_win = sum(t.pnl() for t in wins)
    gross_loss = abs(sum(t.pnl() for t in losses))
    win_rate = len(wins) / len(trades) * 100 if trades else 0
    profit_factor_value = gross_win / gross_loss if gross_loss else (gross_win if gross_win else 0)

    rr_values = [t.rr() for t in trades if t.rr() is not None]
    avg_rr = sum(rr_values) / len(rr_values) if rr_values else 0
    expectancy = total / len(trades) if trades else 0

    start = balance()
    equity = start
    peak = start
    max_drawdown = 0
    for trade in sorted(trades, key=lambda item: (item.date, item.time or "")):
        equity += trade.pnl()
        peak = max(peak, equity)
        max_drawdown = min(max_drawdown, equity - peak)

    target = profit_target()
    loss_limit = max_loss_limit()
    progress = max(0, min(100, total / target * 100)) if target > 0 else 0
    remaining_target = max(0, target - total)
    current_equity = start + total
    trailing_floor = max(start - loss_limit, peak - loss_limit)
    remaining_drawdown = max(0, current_equity - trailing_floor)
    days_traded = len({trade.date for trade in trades})
    pnl_by_day = defaultdict(float)
    for trade in trades:
        pnl_by_day[trade.date] += trade.pnl()
    best_day = max(pnl_by_day.values(), default=0)
    worst_day = min(pnl_by_day.values(), default=0)
    best_day_share = best_day / total * 100 if total > 0 and best_day > 0 else 0
    consistency = max(0, best_day_share)
    daily_limit = daily_loss_limit()
    today_pnl = pnl_by_day.get(date.today(), 0)

    return {
        "start_balance": round(start, 2),
        "current_balance": round(start + total, 2),
        "total": round(total, 2),
        "count": len(trades),
        "wins": len(wins),
        "losses": len(losses),
        "be": len(breakevens),
        "win_rate": round(win_rate, 2),
        "profit_factor": round(profit_factor_value, 2),
        "avg_rr": round(avg_rr, 2),
        "expectancy": round(expectancy, 2),
        "max_dd": round(max_drawdown, 2),
        "best_trade": round(max([t.pnl() for t in trades], default=0), 2),
        "worst_trade": round(min([t.pnl() for t in trades], default=0), 2),
        "target": round(target, 2),
        "progress": round(progress, 1),
        "remaining_target": round(remaining_target, 2),
        "remaining_drawdown": round(remaining_drawdown, 2),
        "trailing_floor": round(trailing_floor, 2),
        "days_traded": days_traded,
        "best_day": round(best_day, 2),
        "worst_day": round(worst_day, 2),
        "consistency": round(consistency, 1),
        "consistency_limit": consistency_limit(),
        "consistency_ok": consistency <= consistency_limit(),
        "today_pnl": round(today_pnl, 2),
        "daily_loss_remaining": round(max(0, daily_limit + min(today_pnl, 0)), 2),
        "daily_loss_limit": round(daily_limit, 2),
    }


def apply_filters(query):
    instrument = request.args.get("instrument", "").strip()
    session_name = request.args.get("session", "").strip()
    result = request.args.get("result", "").strip()
    text = request.args.get("q", "").strip().lower()
    trade_date = request.args.get("date", "").strip()

    if instrument:
        query = query.filter(Trade.instrument == instrument.upper())
    if session_name:
        query = query.filter(Trade.session == session_name)
    if trade_date:
        try:
            query = query.filter(Trade.date == datetime.strptime(trade_date, "%Y-%m-%d").date())
        except ValueError:
            pass

    trades = query.order_by(Trade.date.desc(), Trade.time.desc()).all()
    if result:
        trades = [trade for trade in trades if trade.result() == result]
    if text:
        trades = [trade for trade in trades if any(text in (value or "").lower() for value in (trade.notes, trade.grade, trade.setup, trade.tags, trade.mistake))]
    return trades


@app.route("/")
def index():
    trades = apply_filters(Trade.query)
    all_trades = Trade.query.order_by(Trade.date.desc(), Trade.time.desc()).all()
    stats = calc_stats(trades)

    instruments = sorted({trade.instrument for trade in all_trades})
    sessions = ["Asia", "London", "New York", "Power Hour", "Other"]
    playbook_setups = PlaybookSetup.query.filter_by(active=True).order_by(PlaybookSetup.name).all()

    pnl_by_instrument = defaultdict(float)
    pnl_by_session = defaultdict(float)
    pnl_by_setup = defaultdict(float)
    pnl_by_direction = defaultdict(float)
    pnl_by_grade = defaultdict(float)
    for trade in trades:
        pnl_by_instrument[trade.instrument] += trade.pnl()
        pnl_by_session[trade.session or "Other"] += trade.pnl()
        pnl_by_setup[trade.setup or "Unclassified"] += trade.pnl()
        pnl_by_direction[trade.direction_label()] += trade.pnl()
        pnl_by_grade[trade.grade or "Not graded"] += trade.pnl()

    today = date.today()
    month_value = request.args.get("month", today.strftime("%Y-%m"))
    try:
        shown_month = datetime.strptime(month_value, "%Y-%m").date().replace(day=1)
    except ValueError:
        shown_month = today.replace(day=1)
    _, month_days = calendar.monthrange(shown_month.year, shown_month.month)
    pnl_by_day = defaultdict(float)
    count_by_day = defaultdict(int)
    for trade in all_trades:
        if trade.date.year == shown_month.year and trade.date.month == shown_month.month:
            pnl_by_day[trade.date.day] += trade.pnl()
            count_by_day[trade.date.day] += 1

    calendar_days = [
        {"day": day, "date": shown_month.replace(day=day).isoformat(), "pnl": round(pnl_by_day[day], 2), "count": count_by_day[day]}
        for day in range(1, month_days + 1)
    ]
    first_weekday = shown_month.weekday()
    previous_month = (shown_month.replace(day=1) - __import__("datetime").timedelta(days=1)).strftime("%Y-%m")
    next_month = (shown_month.replace(day=month_days) + __import__("datetime").timedelta(days=1)).strftime("%Y-%m")

    now = datetime.now()

    return render_template(
        "dashboard.html",
        trades=trades,
        stats=stats,
        all_count=len(all_trades),
        currency=currency(),
        instruments=instruments,
        sessions=sessions,
        playbook_setups=playbook_setups,
        pnl_by_instrument=sorted(pnl_by_instrument.items(), key=lambda item: item[1], reverse=True),
        pnl_by_session=sorted(pnl_by_session.items(), key=lambda item: item[1], reverse=True),
        pnl_by_setup=sorted(pnl_by_setup.items(), key=lambda item: item[1], reverse=True),
        pnl_by_direction=sorted(pnl_by_direction.items(), key=lambda item: item[1], reverse=True),
        pnl_by_grade=sorted(pnl_by_grade.items(), key=lambda item: item[1], reverse=True),
        calendar_days=calendar_days,
        filters=request.args,
        default_date=now.strftime("%Y-%m-%d"),
        default_time=now.strftime("%H:%M"),
        current_month=shown_month.strftime("%B %Y"),
        calendar_blanks=range(first_weekday),
        previous_month=previous_month,
        next_month=next_month,
    )


@app.route("/add", methods=["POST"])
def add():
    image_filename = None
    try:
        trade = Trade(
            date=date.today(),
            instrument="",
            direction="Buy",
            contracts=1,
            entry_price=0,
            exit_price=0,
        )
        apply_trade_form(trade, request.form, use_current_datetime=True)

        image_filename = save_uploaded_image(request.files.get("image"))
        if image_filename:
            trade.image = image_filename

        db.session.add(trade)
        db.session.commit()
        flash("Trade saved.", "success")
        return redirect(url_for("index") + "#history")
    except Exception as exc:
        db.session.rollback()
        remove_uploaded_image(image_filename)
        flash(f"Could not save trade: {exc}", "danger")
        return redirect(url_for("index") + "#add-trade")


@app.route("/edit/<int:trade_id>", methods=["GET", "POST"])
def edit(trade_id):
    trade = Trade.query.get_or_404(trade_id)
    sessions = ["Asia", "London", "New York", "Power Hour", "Other"]
    playbook_setups = PlaybookSetup.query.filter_by(active=True).order_by(PlaybookSetup.name).all()

    if request.method == "POST":
        old_image = trade.image
        new_image = None
        try:
            apply_trade_form(trade, request.form)

            new_image = save_uploaded_image(request.files.get("image"))
            remove_image = request.form.get("remove_image") == "1"
            if new_image:
                trade.image = new_image
            elif remove_image:
                trade.image = None

            db.session.commit()
            if old_image and old_image != trade.image:
                remove_uploaded_image(old_image)
            flash("Trade updated.", "success")
            return redirect(url_for("index") + "#history")
        except Exception as exc:
            db.session.rollback()
            remove_uploaded_image(new_image)
            flash(f"Could not update trade: {exc}", "danger")

    return render_template(
        "edit_trade.html",
        trade=trade,
        sessions=sessions,
        playbook_setups=playbook_setups,
        currency=currency(),
        balance=balance(),
        stats={"start_balance": balance()},
    )


@app.route("/delete/<int:trade_id>", methods=["POST"])
def delete(trade_id):
    trade = Trade.query.get_or_404(trade_id)
    image_filename = trade.image
    db.session.delete(trade)
    db.session.commit()
    remove_uploaded_image(image_filename)
    flash("Trade deleted.", "info")
    return redirect(url_for("index") + "#history")


@app.route("/settings", methods=["GET", "POST"])
def settings():
    if request.method == "POST":
        selected_profile = request.form.get("account_profile", "custom")
        if selected_profile not in TOPSTEP_PROFILES:
            selected_profile = "custom"
        profile = TOPSTEP_PROFILES[selected_profile]
        currency_value = (request.form.get("currency") or "USD").strip().upper()
        try:
            numeric = {
                "balance.txt": profile["balance"] or required_float(request.form.get("balance"), "Starting balance"),
                "profit_target.txt": profile["target"] or required_float(request.form.get("profit_target"), "Profit target"),
                "max_loss_limit.txt": profile["max_loss"] or required_float(request.form.get("max_loss_limit"), "Maximum loss limit"),
                "daily_loss_limit.txt": profile["daily_loss"] or required_float(request.form.get("daily_loss_limit"), "Daily loss limit"),
                "consistency_limit.txt": required_float(request.form.get("consistency_limit"), "Consistency limit"),
            }
        except ValueError as exc:
            flash(str(exc), "danger")
            return redirect(url_for("settings"))
        if len(currency_value) != 3 or any(value <= 0 for value in numeric.values()):
            flash("Currency must have 3 letters and all limits must be greater than zero.", "danger")
            return redirect(url_for("settings"))
        values = {"currency.txt": currency_value, "account_profile.txt": selected_profile, **{name: str(value) for name, value in numeric.items()}}
        for filename, value in values.items():
            with open(filename, "w", encoding="utf-8") as file:
                file.write(value)
        flash("Settings saved.", "success")
        return redirect(url_for("index"))

    return render_template(
        "settings.html",
        currency=currency(),
        balance=balance(),
        profit_target=profit_target(),
        max_loss_limit=max_loss_limit(),
        daily_loss_limit=daily_loss_limit(),
        consistency_limit=consistency_limit(),
        account_profile=account_profile(),
        topstep_profiles=TOPSTEP_PROFILES,
        stats={"start_balance": balance()},
    )


@app.route("/calculator")
def calculator():
    return render_template(
        "calculator.html",
        currency=currency(),
        balance=balance(),
        stats={"start_balance": balance()},
    )


@app.route("/playbook", methods=["GET", "POST"])
def playbook():
    if request.method == "POST":
        name = (request.form.get("name") or "").strip()
        if not name:
            flash("Setup name is required.", "danger")
        elif PlaybookSetup.query.filter(db.func.lower(PlaybookSetup.name) == name.lower()).first():
            flash("A setup with this name already exists.", "danger")
        else:
            setup = PlaybookSetup(name=name)
            apply_setup_form(setup, request.form)
            db.session.add(setup)
            db.session.commit()
            flash("Setup added to the playbook.", "success")
        return redirect(url_for("playbook"))
    setups = PlaybookSetup.query.order_by(PlaybookSetup.active.desc(), PlaybookSetup.name).all()
    performance = defaultdict(lambda: {"count": 0, "pnl": 0.0, "wins": 0})
    for trade in Trade.query.all():
        key = trade.setup or ""
        performance[key]["count"] += 1
        performance[key]["pnl"] += trade.pnl()
        performance[key]["wins"] += int(trade.pnl() > 0)
    return render_template("playbook.html", setups=setups, performance=performance, currency=currency(), stats={"start_balance": balance()})


def apply_setup_form(setup, form):
    setup.name = (form.get("name") or setup.name).strip()
    setup.description = (form.get("description") or "").strip()
    setup.entry_rules = (form.get("entry_rules") or "").strip()
    setup.invalidation_rules = (form.get("invalidation_rules") or "").strip()
    setup.management_rules = (form.get("management_rules") or "").strip()
    setup.checklist = (form.get("checklist") or "").strip()
    setup.active = form.get("active") == "1"


@app.route("/playbook/<int:setup_id>/edit", methods=["POST"])
def edit_setup(setup_id):
    setup = PlaybookSetup.query.get_or_404(setup_id)
    apply_setup_form(setup, request.form)
    db.session.commit()
    flash("Playbook setup updated.", "success")
    return redirect(url_for("playbook"))


@app.route("/playbook/<int:setup_id>/delete", methods=["POST"])
def delete_setup(setup_id):
    setup = PlaybookSetup.query.get_or_404(setup_id)
    db.session.delete(setup)
    db.session.commit()
    flash("Setup removed from the playbook. Existing trades were not changed.", "info")
    return redirect(url_for("playbook"))


@app.route("/review/<int:trade_id>")
def review_trade(trade_id):
    trade = Trade.query.get_or_404(trade_id)
    ordered = Trade.query.order_by(Trade.date, Trade.time, Trade.id).all()
    index_value = next((index for index, item in enumerate(ordered) if item.id == trade.id), 0)
    return render_template(
        "review_trade.html",
        trade=trade,
        previous_trade=ordered[index_value - 1] if index_value > 0 else None,
        next_trade=ordered[index_value + 1] if index_value + 1 < len(ordered) else None,
        currency=currency(),
        stats={"start_balance": balance()},
    )


CSV_FIELDS = ["date", "time", "session", "instrument", "direction", "contracts", "entry_price", "exit_price", "stop_loss", "take_profit", "commission", "setup", "tags", "emotion_before", "emotion_after", "grade", "mistake", "context", "notes"]


@app.route("/export/csv")
def export_csv():
    output = io.StringIO()
    writer = csv.DictWriter(output, fieldnames=CSV_FIELDS)
    writer.writeheader()
    for trade in Trade.query.order_by(Trade.date, Trade.time).all():
        writer.writerow({field: getattr(trade, field) if getattr(trade, field) is not None else "" for field in CSV_FIELDS})
    content = io.BytesIO(output.getvalue().encode("utf-8-sig"))
    return send_file(content, mimetype="text/csv", as_attachment=True, download_name=f"trades_{date.today().isoformat()}.csv")


@app.route("/backup")
def backup():
    memory = io.BytesIO()
    with zipfile.ZipFile(memory, "w", zipfile.ZIP_DEFLATED) as archive:
        database_path = os.path.join(app.root_path, "trades.db")
        if os.path.exists(database_path):
            archive.write(database_path, "trades.db")
        for filename in ("currency.txt", "balance.txt", "profit_target.txt", "max_loss_limit.txt", "daily_loss_limit.txt", "consistency_limit.txt"):
            path = os.path.join(app.root_path, filename)
            if os.path.exists(path):
                archive.write(path, filename)
        for filename in os.listdir(app.config["UPLOAD_FOLDER"]):
            path = os.path.join(app.config["UPLOAD_FOLDER"], filename)
            if os.path.isfile(path):
                archive.write(path, os.path.join("uploads", filename))
    memory.seek(0)
    return send_file(memory, mimetype="application/zip", as_attachment=True, download_name=f"trading_tracker_backup_{date.today().isoformat()}.zip")


@app.route("/import/csv", methods=["POST"])
def import_csv():
    upload = request.files.get("csv_file")
    if not upload or not upload.filename.lower().endswith(".csv"):
        flash("Select a CSV file.", "danger")
        return redirect(url_for("settings"))
    added = 0
    try:
        text_stream = io.StringIO(upload.stream.read().decode("utf-8-sig"), newline=None)
        reader = csv.DictReader(text_stream)
        if not reader.fieldnames:
            raise ValueError("CSV has no header row.")
        for source_row in reader:
            row = normalize_import_row(source_row, request.form.get("platform", "auto"))
            trade = Trade(date=date.today(), instrument="", direction="Buy", contracts=1, entry_price=0, exit_price=0)
            apply_trade_form(trade, row)
            db.session.add(trade)
            added += 1
        db.session.commit()
        flash(f"Imported {added} trades.", "success")
    except Exception as exc:
        db.session.rollback()
        flash(f"Import failed: {exc}", "danger")
    return redirect(url_for("index") + "#history")


def normalize_import_row(source, platform="auto"):
    row = {str(key).strip().lower().replace(" ", "_"): value for key, value in source.items() if key is not None}
    aliases = {
        "date": ["date", "trade_date", "closed_date", "exit_date", "entry_date"],
        "time": ["time", "entry_time", "open_time", "filled_time"],
        "instrument": ["instrument", "symbol", "contract", "market"],
        "direction": ["direction", "side", "position", "market_pos."],
        "contracts": ["contracts", "qty", "quantity", "size"],
        "entry_price": ["entry_price", "entry", "avg_entry_price", "buy_price", "open_price"],
        "exit_price": ["exit_price", "exit", "avg_exit_price", "sell_price", "close_price"],
        "commission": ["commission", "commissions", "fees", "fee"],
        "notes": ["notes", "comment", "comments"],
    }
    result = {}
    for target, candidates in aliases.items():
        result[target] = next((row[name] for name in candidates if name in row and str(row[name]).strip()), "")
    for field in CSV_FIELDS:
        if field in row and not result.get(field):
            result[field] = row[field]
    raw_date = str(result.get("date", "")).strip()
    parsed_date = None
    for fmt in ("%Y-%m-%d", "%m/%d/%Y", "%m/%d/%y", "%d/%m/%Y", "%Y-%m-%d %H:%M:%S", "%m/%d/%Y %H:%M:%S"):
        try:
            parsed_date = datetime.strptime(raw_date, fmt)
            break
        except ValueError:
            continue
    if not parsed_date:
        try:
            parsed_date = datetime.fromisoformat(raw_date.replace("Z", "+00:00"))
        except ValueError as exc:
            raise ValueError(f"Unsupported date: {raw_date}") from exc
    result["date"] = parsed_date.strftime("%Y-%m-%d")
    if not result.get("time") and parsed_date.time() != datetime.min.time():
        result["time"] = parsed_date.strftime("%H:%M")
    direction = str(result.get("direction", "")).strip().lower()
    result["direction"] = "Buy" if direction in {"buy", "long", "b", "marketposition.long"} else "Sell" if direction in {"sell", "short", "s", "marketposition.short"} else result.get("direction")
    missing = [field for field in ("date", "instrument", "direction", "contracts", "entry_price", "exit_price") if not str(result.get(field, "")).strip()]
    if missing:
        raise ValueError(f"Could not map columns: {', '.join(missing)}. Choose the correct platform or use the tracker CSV template.")
    return result


@app.route("/api/charts")
def api_charts():
    trades = sorted(apply_filters(Trade.query), key=lambda trade: (trade.date, trade.time or ""))
    equity_value = balance()
    equity = []
    monthly = defaultdict(float)
    session_values = defaultdict(float)
    instrument_values = defaultdict(float)
    weekday_values = defaultdict(float)
    hour_values = defaultdict(float)
    result = {"WIN": 0, "LOSS": 0, "BE": 0}

    for index, trade in enumerate(trades, start=1):
        pnl = trade.pnl()
        equity_value += pnl
        equity.append({
            "number": index,
            "date": trade.date.isoformat(),
            "time": trade.time or "",
            "instrument": trade.instrument,
            "direction": trade.direction_label(),
            "pnl": round(pnl, 2),
            "result": trade.result(),
            "value": round(equity_value, 2),
        })
        monthly[trade.date.strftime("%Y-%m")] += pnl
        session_values[trade.session or "Other"] += pnl
        instrument_values[trade.instrument] += pnl
        weekday_values[trade.date.strftime("%a")] += pnl
        if trade.time:
            hour_values[trade.time[:2] + ":00"] += pnl
        result[trade.result()] += 1

    return jsonify({
        "start_balance": round(balance(), 2),
        "currency": currency(),
        "equity": equity,
        "monthly": [{"label": key, "value": round(value, 2)} for key, value in sorted(monthly.items())],
        "session": [{"label": key, "value": round(value, 2)} for key, value in sorted(session_values.items(), key=lambda item: item[1], reverse=True)],
        "instrument": [{"label": key, "value": round(value, 2)} for key, value in sorted(instrument_values.items(), key=lambda item: item[1], reverse=True)],
        "weekday": [{"label": key, "value": round(weekday_values.get(key, 0), 2)} for key in ["Mon", "Tue", "Wed", "Thu", "Fri"]],
        "hour": [{"label": key, "value": round(value, 2)} for key, value in sorted(hour_values.items())],
        "result": result,
    })


@app.route("/uploads/<filename>")
def uploaded(filename):
    return send_from_directory(app.config["UPLOAD_FOLDER"], filename)


if __name__ == "__main__":
    app.run(debug=True)
