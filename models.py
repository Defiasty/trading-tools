from flask_sqlalchemy import SQLAlchemy


db = SQLAlchemy()


POINT_VALUES = {
    "NQ": 20.0,
    "MNQ": 2.0,
    "ES": 50.0,
    "MES": 5.0,
    "YM": 5.0,
    "MYM": 0.5,
    "RTY": 50.0,
    "M2K": 5.0,
    "CL": 1000.0,
    "MCL": 100.0,
    "GC": 100.0,
    "MGC": 10.0,
}


class Trade(db.Model):
    id = db.Column(db.Integer, primary_key=True)

    date = db.Column(db.Date, nullable=False)
    time = db.Column(db.String(5), nullable=True)
    session = db.Column(db.String(30), nullable=True)

    instrument = db.Column(db.String(50), nullable=False)
    direction = db.Column(db.String(10), nullable=False)
    contracts = db.Column(db.Float, nullable=False, default=1)

    entry_price = db.Column(db.Float, nullable=False)
    exit_price = db.Column(db.Float, nullable=False)
    stop_loss = db.Column(db.Float, nullable=True)
    take_profit = db.Column(db.Float, nullable=True)

    # Legacy columns are intentionally kept so an old trades.db remains compatible.
    risk = db.Column(db.Float, nullable=False, default=0)
    commission = db.Column(db.Float, nullable=False, default=0)
    setup = db.Column(db.String(100), nullable=True)
    tags = db.Column(db.String(400), nullable=True)
    emotion_before = db.Column(db.String(60), nullable=True)
    emotion_after = db.Column(db.String(60), nullable=True)
    grade = db.Column(db.String(10), nullable=True)
    mistake = db.Column(db.String(120), nullable=True)
    context = db.Column(db.String(500), nullable=True)
    notes = db.Column(db.Text, nullable=True)
    image = db.Column(db.String(200), nullable=True)

    def root_symbol(self):
        symbol = (self.instrument or "").upper().strip()
        for root in sorted(POINT_VALUES, key=len, reverse=True):
            if symbol.startswith(root):
                return root
        return symbol

    def point_value(self):
        return POINT_VALUES.get(self.root_symbol(), 1.0)

    def is_long(self):
        return (self.direction or "").strip().lower() in {"kupno", "buy", "long"}

    def direction_label(self):
        return "Buy" if self.is_long() else "Sell"

    def pnl(self):
        if self.is_long():
            points = self.exit_price - self.entry_price
        else:
            points = self.entry_price - self.exit_price
        return points * self.point_value() * self.contracts - (self.commission or 0)

    def planned_risk(self):
        if self.stop_loss is None:
            return None
        distance = abs(self.entry_price - self.stop_loss)
        if distance == 0:
            return None
        return distance * self.point_value() * self.contracts

    def planned_reward(self):
        if self.take_profit is None:
            return None
        distance = abs(self.take_profit - self.entry_price)
        return distance * self.point_value() * self.contracts

    def rr(self):
        risk = self.planned_risk()
        reward = self.planned_reward()
        if not risk or reward is None:
            return None
        return reward / risk

    def realized_r(self):
        risk = self.planned_risk()
        if not risk:
            return None
        return self.pnl() / risk

    def result(self):
        p = self.pnl()
        if p > 0:
            return "WIN"
        if p < 0:
            return "LOSS"
        return "BE"


class PlaybookSetup(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), unique=True, nullable=False)
    description = db.Column(db.Text, nullable=True)
    entry_rules = db.Column(db.Text, nullable=True)
    invalidation_rules = db.Column(db.Text, nullable=True)
    management_rules = db.Column(db.Text, nullable=True)
    checklist = db.Column(db.Text, nullable=True)
    active = db.Column(db.Boolean, nullable=False, default=True)

    def checklist_items(self):
        return [item.strip() for item in (self.checklist or "").splitlines() if item.strip()]
