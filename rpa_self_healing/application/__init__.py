"""Application layer — thin façades over infrastructure.

The actual healing logic resides in PlaywrightDriver (via HealingOrchestrator
pattern inside the driver). These modules expose the domain interfaces so that
future unit-testing or provider swaps don't require touching the driver.
"""
