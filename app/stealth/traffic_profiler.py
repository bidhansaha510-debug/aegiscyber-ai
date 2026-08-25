"""Traffic Profiler — jitter injection, rate limiting, and timing awareness.

Controls the tempo of operations to avoid triggering IDS/WAF thresholds.
In stealth mode, all tool executions pass through the profiler to ensure
they stay below detection thresholds.
"""

from __future__ import annotations

import asyncio
import random
import time
from datetime import datetime, timezone
from typing import Any

from pydantic import BaseModel, Field

from app.logging_config import get_logger

logger = get_logger("stealth.traffic")


class TrafficProfile(BaseModel):
    """Configuration for traffic shaping during stealth operations."""
    min_jitter_seconds: float = 2.0
    max_jitter_seconds: float = 15.0
    max_requests_per_minute: int = 10
    max_requests_per_hour: int = 200
    burst_limit: int = 3
    cooldown_seconds: float = 30.0
    respect_business_hours: bool = True
    business_hours_start: int = 8
    business_hours_end: int = 18
    randomize_order: bool = True
    fragment_large_scans: bool = True
    max_ports_per_fragment: int = 20


STEALTH_PROFILES: dict[str, TrafficProfile] = {
    "paranoid": TrafficProfile(
        min_jitter_seconds=10.0,
        max_jitter_seconds=60.0,
        max_requests_per_minute=3,
        max_requests_per_hour=60,
        burst_limit=1,
        cooldown_seconds=120.0,
        respect_business_hours=True,
        max_ports_per_fragment=5,
    ),
    "careful": TrafficProfile(
        min_jitter_seconds=3.0,
        max_jitter_seconds=20.0,
        max_requests_per_minute=8,
        max_requests_per_hour=150,
        burst_limit=2,
        cooldown_seconds=45.0,
        respect_business_hours=True,
        max_ports_per_fragment=15,
    ),
    "normal": TrafficProfile(
        min_jitter_seconds=1.0,
        max_jitter_seconds=5.0,
        max_requests_per_minute=20,
        max_requests_per_hour=500,
        burst_limit=5,
        cooldown_seconds=10.0,
        respect_business_hours=False,
        max_ports_per_fragment=50,
    ),
    "aggressive": TrafficProfile(
        min_jitter_seconds=0.0,
        max_jitter_seconds=1.0,
        max_requests_per_minute=100,
        max_requests_per_hour=5000,
        burst_limit=20,
        cooldown_seconds=0.0,
        respect_business_hours=False,
        max_ports_per_fragment=1000,
    ),
}


class TrafficProfiler:
    """Controls the tempo and pattern of tool executions for stealth."""

    def __init__(self, profile_name: str = "careful") -> None:
        self._profile = STEALTH_PROFILES.get(profile_name, STEALTH_PROFILES["careful"])
        self._profile_name = profile_name
        self._request_timestamps: list[float] = []
        self._burst_counter: int = 0
        self._last_execution_time: float = 0.0
        self._total_executions: int = 0
        self._total_jitter_seconds: float = 0.0

    @property
    def profile(self) -> TrafficProfile:
        return self._profile

    @property
    def profile_name(self) -> str:
        return self._profile_name

    def set_profile(self, profile_name: str) -> None:
        """Switch to a pre-built profile."""
        if profile_name in STEALTH_PROFILES:
            self._profile = STEALTH_PROFILES[profile_name]
            self._profile_name = profile_name
            logger.info("Traffic profile set to: %s", profile_name)
        else:
            logger.warning("Unknown profile '%s', keeping current: %s", profile_name, self._profile_name)

    def set_custom_profile(self, profile: TrafficProfile) -> None:
        """Set a custom traffic profile."""
        self._profile = profile
        self._profile_name = "custom"
        logger.info("Custom traffic profile applied")

    async def apply_jitter(self) -> float:
        """Apply randomized delay before the next operation.

        Returns the actual delay in seconds.
        """
        if self._profile.min_jitter_seconds <= 0 and self._profile.max_jitter_seconds <= 0:
            return 0.0

        delay = random.uniform(
            self._profile.min_jitter_seconds,
            self._profile.max_jitter_seconds,
        )

        if self._burst_counter >= self._profile.burst_limit:
            delay += self._profile.cooldown_seconds
            self._burst_counter = 0
            logger.info("Burst limit reached — applying %.1fs cooldown", delay)

        if delay > 0:
            logger.debug("Jitter: waiting %.1fs before next operation", delay)
            await asyncio.sleep(delay)

        self._burst_counter += 1
        self._total_jitter_seconds += delay
        return delay

    def check_rate_limit(self) -> tuple[bool, float]:
        """Check if we're within rate limits.

        Returns (allowed, wait_seconds).
        """
        now = time.monotonic()
        one_minute_ago = now - 60
        one_hour_ago = now - 3600
        self._request_timestamps = [t for t in self._request_timestamps if t > one_hour_ago]

        recent_minute = sum(1 for t in self._request_timestamps if t > one_minute_ago)
        recent_hour = len(self._request_timestamps)

        if recent_minute >= self._profile.max_requests_per_minute:
            wait = 60.0 - (now - min(t for t in self._request_timestamps if t > one_minute_ago))
            return False, max(0, wait)

        if recent_hour >= self._profile.max_requests_per_hour:
            wait = 3600.0 - (now - min(self._request_timestamps))
            return False, max(0, wait)

        return True, 0.0

    def record_execution(self) -> None:
        """Record that a tool execution occurred."""
        self._request_timestamps.append(time.monotonic())
        self._last_execution_time = time.monotonic()
        self._total_executions += 1

    def is_business_hours(self) -> bool:
        """Check if current time is within business hours."""
        if not self._profile.respect_business_hours:
            return True
        now = datetime.now()
        return self._profile.business_hours_start <= now.hour < self._profile.business_hours_end

    def get_timing_recommendation(self) -> str:
        """Get a recommendation about optimal execution timing."""
        now = datetime.now()
        hour = now.hour

        if 9 <= hour <= 17:
            return "OPTIMAL — Business hours. Network traffic provides natural cover."
        elif 7 <= hour <= 9 or 17 <= hour <= 19:
            return "GOOD — Transition hours. Mixed traffic patterns."
        elif 19 <= hour <= 23:
            return "MODERATE — Evening hours. Lower traffic may make anomalies more visible."
        else:
            return "RISKY — Late night/early morning. Minimal traffic makes scans highly anomalous."

    def fragment_port_list(self, ports: str) -> list[str]:
        """Fragment a large port specification into smaller chunks.

        Turns '-p 1-1000' into multiple smaller scans to reduce traffic spikes.
        """
        max_per_fragment = self._profile.max_ports_per_fragment

        all_ports: list[int] = []
        for part in ports.replace(" ", "").split(","):
            if "-" in part:
                try:
                    start, end = part.split("-", 1)
                    all_ports.extend(range(int(start), int(end) + 1))
                except ValueError:
                    continue
            else:
                try:
                    all_ports.append(int(part))
                except ValueError:
                    continue

        if not all_ports:
            return [ports]

        if len(all_ports) <= max_per_fragment:
            return [ports]

        if self._profile.randomize_order:
            random.shuffle(all_ports)

        fragments = []
        for i in range(0, len(all_ports), max_per_fragment):
            chunk = all_ports[i:i + max_per_fragment]
            fragments.append(",".join(str(p) for p in chunk))

        logger.info("Fragmented %d ports into %d chunks of max %d",
                     len(all_ports), len(fragments), max_per_fragment)
        return fragments

    def get_statistics(self) -> dict[str, Any]:
        """Return profiler statistics."""
        return {
            "profile": self._profile_name,
            "total_executions": self._total_executions,
            "total_jitter_seconds": round(self._total_jitter_seconds, 1),
            "avg_jitter_seconds": round(
                self._total_jitter_seconds / max(1, self._total_executions), 1
            ),
            "current_burst_count": self._burst_counter,
            "requests_last_minute": sum(
                1 for t in self._request_timestamps
                if t > time.monotonic() - 60
            ),
            "requests_last_hour": len(self._request_timestamps),
            "timing_recommendation": self.get_timing_recommendation(),
            "is_business_hours": self.is_business_hours(),
        }
