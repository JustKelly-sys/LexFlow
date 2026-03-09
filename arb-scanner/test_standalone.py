# test_standalone.py - Standalone test for arbitrage calculator
class Market:
    def __init__(self, outcomes, outcome_prices):
        self.outcomes = outcomes
        self.outcome_prices = outcome_prices

def calc_arb(market, fee=2.0, gas=0.005, slip=0.5):
    sum_p = sum(market.outcome_prices.values())
    gross = (sum_p - 1.0) * 100
    fees = fee + (gas/1000.0)*100 + slip
    net = gross - fees
    return {"sum": sum_p, "gross": gross, "fees": fees, "net": net, "ok": net > 1.0}

print("TEST 1: Profitable (sum=1.05)")
m1 = Market(["YES","NO"], {"YES":0.52,"NO":0.53})
r1 = calc_arb(m1)
print(f"  Sum={r1['sum']}, Net={r1['net']:.2f}%, Profitable={r1['ok']}")
assert r1["ok"] == True
print("  PASSED")

print("TEST 2: No arb (sum=1.00)")
m2 = Market(["YES","NO"], {"YES":0.50,"NO":0.50})
r2 = calc_arb(m2)
print(f"  Sum={r2['sum']}, Net={r2['net']:.2f}%, Profitable={r2['ok']}")
assert r2["ok"] == False
print("  PASSED")

print("TEST 3: Below threshold (sum=1.03)")
m3 = Market(["YES","NO"], {"YES":0.515,"NO":0.515})
r3 = calc_arb(m3)
print(f"  Sum={r3['sum']}, Net={r3['net']:.2f}%, Profitable={r3['ok']}")
assert r3["ok"] == False
print("  PASSED")

print("ALL 3 TESTS PASSED!")
