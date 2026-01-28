"""
Universe isolation for Market-Watch trading system.

This module defines the core Universe type that governs execution context
throughout the system. Every component must know its universe and cannot
operate across universe boundaries.

Design Principles:
- Universe is immutable after construction
- No component may operate without explicit universe context
- Universe changes require full teardown and reconstruction
- All data/logs/events are universe-scoped
"""

from enum import Enum
from typing import Optional
from datetime import datetime
import uuid


class Universe(Enum):
    """
    Execution universe defining authority and semantics.

    Market-Watch operates in three separate universes:

    - LIVE: Real capital, real execution, irreversible consequences.
      Uses live broker endpoints, real market constraints, and actual capital.
      Results are LIVE_VERIFIED and suitable for external auditing.

    - PAPER: Broker-mediated paper accounts with real market constraints.
      Uses paper broker endpoints, real market hours, and simulated fills.
      Results are PAPER_ONLY and represent what would have happened.

    - SIMULATION: Synthetic or replayed environments for learning and testing.
      Uses FakeBroker, can run 24/7, uses historical or generated data.
      Results are SIM_VALID_FOR_TRAINING or SIM_INVALID_FOR_TRAINING depending
      on realism constraints.

    These are separate realities, not modes. A result from one universe
    cannot be conflated with results from another.
    """

    LIVE = "live"
    PAPER = "paper"
    SIMULATION = "simulation"

    def __str__(self) -> str:
        """String representation (lowercase value)."""
        return self.value

    def __repr__(self) -> str:
        """Detailed representation for debugging."""
        return f"Universe.{self.name}"

    @property
    def is_real_capital(self) -> bool:
        """
        Returns True if this universe involves real capital.

        Only LIVE universe has irreversible financial consequences.
        PAPER and SIMULATION are learning environments.
        """
        return self == Universe.LIVE

    @property
    def allows_market_hours_override(self) -> bool:
        """
        Returns True if this universe can trade outside market hours.

        SIMULATION can run 24/7 for training and testing.
        LIVE and PAPER respect real market hours.
        """
        return self == Universe.SIMULATION

    @property
    def requires_explicit_confirmation(self) -> bool:
        """
        Returns True if this universe requires explicit user confirmation.

        LIVE trading requires LIVE_TRADING_CONFIRMED=true in environment
        as a safety check to prevent accidental deployment.
        """
        return self == Universe.LIVE

    @property
    def default_validity_class(self) -> str:
        """
        Returns the default validity class for metrics from this universe.

        Validity classes:
        - LIVE_VERIFIED: Actual results with real capital
        - PAPER_ONLY: Broker-mediated paper trading results
        - SIM_VALID_FOR_TRAINING: Realistic simulation suitable for training
        - SIM_INVALID_FOR_TRAINING: Unrealistic simulation (testing only)
        """
        if self == Universe.LIVE:
            return "LIVE_VERIFIED"
        elif self == Universe.PAPER:
            return "PAPER_ONLY"
        else:  # SIMULATION
            return "SIM_VALID_FOR_TRAINING"

    @classmethod
    def from_string(cls, value: str) -> "Universe":
        """
        Parse universe from string (case-insensitive).

        Examples:
            Universe.from_string("live") -> Universe.LIVE
            Universe.from_string("SIMULATION") -> Universe.SIMULATION

        Raises:
            ValueError: If value is not a valid universe name
        """
        value_upper = value.upper()
        try:
            return cls[value_upper]
        except KeyError:
            valid = ", ".join(u.value for u in cls)
            raise ValueError(f"Invalid universe: {value}. Must be one of: {valid}")


class UniverseContext:
    """
    Immutable context object carrying universe information.

    Every execution-affecting path should receive a UniverseContext that
    provides all necessary universe-scoped information.

    Attributes:
        universe: The execution universe (LIVE/PAPER/SIMULATION)
        session_id: Unique identifier for this universe session
        created_at: Timestamp when this context was created
        data_lineage_id: Optional identifier for data provenance
        validity_class: Default validity class for metrics
    """

    def __init__(
        self,
        universe: Universe,
        session_id: Optional[str] = None,
        data_lineage_id: Optional[str] = None
    ):
        """
        Create a new UniverseContext.

        Args:
            universe: The execution universe
            session_id: Unique session identifier (auto-generated if None)
            data_lineage_id: Optional data provenance identifier
        """
        self._universe = universe
        self._session_id = session_id or self._generate_session_id()
        self._created_at = datetime.utcnow()
        self._data_lineage_id = data_lineage_id
        self._validity_class = universe.default_validity_class

    @staticmethod
    def _generate_session_id() -> str:
        """Generate a unique session ID."""
        return f"session_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}_{uuid.uuid4().hex[:8]}"

    @property
    def universe(self) -> Universe:
        """The execution universe (immutable)."""
        return self._universe

    @property
    def session_id(self) -> str:
        """Unique session identifier (immutable)."""
        return self._session_id

    @property
    def created_at(self) -> datetime:
        """Timestamp when this context was created (immutable)."""
        return self._created_at

    @property
    def data_lineage_id(self) -> Optional[str]:
        """Data provenance identifier (immutable)."""
        return self._data_lineage_id

    @property
    def validity_class(self) -> str:
        """Default validity class for metrics (immutable)."""
        return self._validity_class

    def __repr__(self) -> str:
        """Detailed representation for debugging."""
        return (
            f"UniverseContext(universe={self.universe}, "
            f"session_id='{self.session_id}', "
            f"created_at={self.created_at.isoformat()})"
        )

    def to_dict(self) -> dict:
        """
        Convert to dictionary for serialization.

        Returns:
            Dict with all context fields
        """
        return {
            "universe": self.universe.value,
            "session_id": self.session_id,
            "created_at": self.created_at.isoformat(),
            "data_lineage_id": self.data_lineage_id,
            "validity_class": self.validity_class
        }


def get_data_path(universe: Universe, filename: str) -> str:
    """
    Get universe-scoped data file path.

    Args:
        universe: The execution universe
        filename: The filename (e.g., "config.json", "positions.json")

    Returns:
        Universe-scoped path (e.g., "data/live/config.json")

    Example:
        >>> get_data_path(Universe.SIMULATION, "config.json")
        'data/simulation/config.json'
    """
    return f"data/{universe.value}/{filename}"


def get_log_path(universe: Universe, filename: str) -> str:
    """
    Get universe-scoped log file path.

    Args:
        universe: The execution universe
        filename: The log filename (e.g., "trades.jsonl", "equity.jsonl")

    Returns:
        Universe-scoped path (e.g., "logs/live/trades.jsonl")

    Example:
        >>> get_log_path(Universe.LIVE, "trades.jsonl")
        'logs/live/trades.jsonl'
    """
    return f"logs/{universe.value}/{filename}"


def get_shared_data_path(filename: str) -> str:
    """
    Get shared data file path (universe-agnostic).

    Only use for truly universe-agnostic data like:
    - Symbol metadata (sector_map.json)
    - Historical market data cache
    - Static reference data

    Args:
        filename: The filename

    Returns:
        Shared data path (e.g., "data/shared/sector_map.json")

    Warning:
        Most data should be universe-scoped. Only use this for
        explicitly safe shared assets.
    """
    return f"data/shared/{filename}"


# Validation functions for universe isolation
def validate_universe_transition(
    from_universe: Universe,
    to_universe: Universe,
    reason: str
) -> dict:
    """
    Validate and log a universe transition.

    Universe transitions are not toggles - they require full teardown
    and reconstruction of all universe-bound components.

    Args:
        from_universe: Current universe
        to_universe: Target universe
        reason: Reason for transition (e.g., "market_closed_auto_switch")

    Returns:
        Dict with transition metadata for audit logging

    Raises:
        ValueError: If transition is invalid
    """
    if from_universe == to_universe:
        raise ValueError(f"Cannot transition to same universe: {from_universe}")

    # Log transition metadata
    transition_metadata = {
        "from_universe": from_universe.value,
        "to_universe": to_universe.value,
        "reason": reason,
        "timestamp": datetime.utcnow().isoformat(),
        "transition_id": uuid.uuid4().hex,
        "warning": "This is a destructive transition requiring teardown and rebuild"
    }

    return transition_metadata
