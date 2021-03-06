# -*- coding: utf-8 -*-
"""
Simple Real Option Value using Least Squares Monte Carlo (LSMC)

Smith (2005) describes a straighforward procedure to value a real option
using Longstaff and Schwartz (2001) LSMC method and gives a simple
example (pp. 88-89). This code performs the steps discussed by Smith (2005) 
but with a different example.

Setup: Mine Co. is evaluating a widget mine with a 10 year life. Mine Co.
is considering a proposal by another company (Mine Ltd.) wherein Mine Co. 
would have the option to sell its interest to Mine Ltd. at the end of year 5. 
It can only excerise this option at the end of year 5 and not before or after. 
The price of widgets folllow a GBM process, and the mine's operating cost 
follows a mean-reverting process.

Question: What is the value of this option? The goal of this code is to
estimate this option value.

T: time periods (years)
n_sim: # of simulations to run
r: risk-free discount rate
buyout: amount Mine Co. will receive if it sells its iterest in year 5
price_0: initial price of widgets
price_sigma: annualized volatility of the price of widgets
roy_rate: royalty rate Mine Co. must pay to landowner
opex_0: initial annual operating expenses
opex_k: reversion speed parameter in mean-reverting process
opex_lr: long-run annual opex
opex_sigma: volaility parameter for opex

quant: quantity of widgets mined each year
capex: upfront CAPEX
tax_rate: income tax rate paid by mine
depr_sch: depreciation schedule for income tax calculation

References:
Smith, James E. "Alternative Approaches for Solving Real-Options Problems: 
    (Comment on Brandão et al. 2005)." Decision Analysis 2, no. 2 (2005): 89-102.
    
Longstaff, Francis A., and Eduardo S. Schwartz. "Valuing American options by 
    simulation: a simple least-squares approach." The review of financial 
    studies 14, no. 1 (2001): 113-147.

"""

import numpy as np
from sklearn import linear_model

# INPUTS
# ############################################################################

# 10 time periods, 1000 simulations
T = 10
n_sim = 1000
# offer is to buyout for $100
buyout = 100
buy_year = 5
# 5% risk-free rate (annual)
r = 0.05
# initial widget price and annualized vol
price_0 = 50
price_sigma = 0.3
# 1/8 royalty rate miner must pay to landowner
roy_rate = 0.125
# opex follows mean-reversion process with these params:
opex_0 = 25
opex_k = 0.5
opex_lr = 30
opex_sigma = 0.25
# quantity mined follows logarithmic decline from 10 to 1
quant = np.logspace(1, 0, T)
# inital capex was $100
capex = 1250
# 21% income tax rate
tax_rate = 0.21
# 7-year macrs depreciation schedule
depr_sch = np.array([0.1429, 0.2449, 0.1749, 0.1249, 0.0893, 
                     0.0892, 0.0893, 0.0446])


# SIMULATE PROJECT CASH FLOWS
# #############################################################################

rng = np.random.RandomState(1)
# price matrix and opex matrix
price = np.c_[np.ones((n_sim, 1))*price_0, np.empty([n_sim, T - 1])]
opex = np.c_[np.ones((n_sim, 1))*opex_0, np.empty([n_sim, T - 1])]
# simulate prices (GBM) and opex (mean reversion) 
for t in np.arange(1,T):
    price[:, t] = price[:, t - 1] * np.exp(-0.5*(price_sigma**2)*1 + 
                                            price_sigma*rng.randn(n_sim).T)
    # log(opex) follows mean-reversion opex shouldn't go negative, so
    # we use log opex and take exp to get opex
    opex[:, t] = np.exp(np.log(opex[:, t - 1]) + opex_k*(np.log(opex_lr) - 
                        np.log(opex[:, t - 1]))*1 + opex_sigma*rng.randn(n_sim).T)

# calculate revenues
rev_gross = price * quant
roy = rev_gross * roy_rate
rev_net = rev_gross - roy
# before-tax cash flow (btcf)
btcf = rev_net - opex
# calculate income tax
tax = tax_rate * (btcf - capex * np.r_[depr_sch, np.zeros((T-len(depr_sch)))])
# after-tax cash flow (atcf)
atcf = btcf - tax


# ESTIMATE OPTION VALUE
# ############################################################################

#discount factors
dis_fact = np.array([(1 + r)**(-i - 1) for i in range(T)])

# net present value of cash flows
npv = (atcf * dis_fact).sum(axis=1)
# net present value of cash flows in years 6-10
npv_cont = (atcf[:, buy_year:] * dis_fact[buy_year:]).sum(axis=1)

# put together regressor matrix with price and opex in buyout year
X_price = price[:, buy_year]
X_opex = opex[:, buy_year]
X = np.c_[X_price, X_opex]

# linear regression model
regr = linear_model.LinearRegression()
# regress buyout year price and opex on realized NPV
# simplest regression possible
regr.fit(X, npv_cont)
# predicted continuation value
cv_pred = regr.predict(X)

# if estimated continuation value < buyout price, sell
# if estimated continuation value > buyout price, don't sell
max_val = np.maximum(cv_pred, buyout)
# expected NPV with option
enpv_w_opt = ((atcf[:, :buy_year] * dis_fact[:buy_year]).sum(axis=1)).mean(axis=0) \
             + max_val.mean(axis=0) - capex
# expected NPV without the option
enpv_wo_opt = npv.mean(axis=0) - capex
opt_val = enpv_w_opt - enpv_wo_opt

print ("The ENPV of the project without the option is $%.1f" % enpv_wo_opt)
print ("The ENPV of the project with the option is $%.1f" % enpv_w_opt)
print ("The value of the option to sell in year %s is $%.1f" % (buy_year, opt_val))

