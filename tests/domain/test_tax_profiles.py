from server.domain.tax import TaxModel, TaxProfile


def test_short_vs_long_holding_period_rate_selection() -> None:
    model = TaxModel(short_term_rate=0.30, long_term_rate=0.15)
    short_tax = model.estimate_tax(realized_gain=100.0, holding_period_days=30, jurisdiction="US")
    long_tax = model.estimate_tax(realized_gain=100.0, holding_period_days=400, jurisdiction="US")
    assert short_tax == 30.0
    assert long_tax == 15.0


def test_jurisdiction_profile_selection() -> None:
    profiles = {
        "US": TaxProfile(jurisdiction="US", short_term_rate=0.3, long_term_rate=0.15),
        "CA": TaxProfile(jurisdiction="CA", short_term_rate=0.25, long_term_rate=0.12, state_rate=0.02),
    }
    model = TaxModel(profiles=profiles)
    tax = model.estimate_tax(realized_gain=200.0, holding_period_days=10, jurisdiction="CA")
    assert tax == 54.0  # 200 * (0.25 + 0.02)


def test_placeholder_foreign_withholding_and_credit() -> None:
    profiles = {
        "INTL": TaxProfile(
            jurisdiction="INTL",
            short_term_rate=0.2,
            long_term_rate=0.1,
            foreign_withholding_rate=0.03,
            foreign_tax_credit_rate=0.01,
        )
    }
    model = TaxModel(profiles=profiles)
    tax = model.estimate_tax(realized_gain=100.0, holding_period_days=10, jurisdiction="INTL")
    assert tax == 22.0
