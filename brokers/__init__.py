"""Broker abstraction package.

Public surface:
    BaseBroker  — abstract base class all brokers must implement
    IBKRBroker  — Interactive Brokers stub (requires TWS/Gateway)
"""
from brokers.base import BaseBroker
from brokers.ibkr import IBKRBroker

__all__ = ["BaseBroker", "IBKRBroker"]
