"""
comping_engine.py — Humanized MIDI Comping Engine

Takes static chord pitch arrays and translates them into rhythmic,
dynamically voiced performances using:
  - Comping pattern templates (CompingHit / CompingPattern)
  - MPC-style 16th-note swing
  - Gaussian velocity humanization with metrical accent + hand weighting
  - BPM-aware chord rolling (staggered onsets)

No dependencies beyond Python stdlib + midiutil.
"""

import math
import random
from dataclasses import dataclass, field
from typing import List


# ─── Data Structures ─────────────────────────────────────────────

@dataclass
class CompingHit:
    """A single rhythmic strike within a comping pattern."""
    beat_offset: float        # Position within the bar (0.0 = beat 1)
    duration: float           # Length in beats
    velocity_mult: float      # Scalar on base velocity (0.1–1.5)
    voice_group: str          # "bass", "chord", or "all"


@dataclass
class CompingPattern:
    """A complete groove template — one bar of rhythmic hits."""
    name: str
    length_in_beats: float
    hits: List[CompingHit]


# ─── Pattern Presets ─────────────────────────────────────────────

PATTERNS = {
    "straight": CompingPattern(
        name="straight",
        length_in_beats=4.0,
        hits=[
            CompingHit(0.0, 4.0, 1.0, "bass"),
            CompingHit(0.0, 4.0, 0.9, "chord"),
        ],
    ),

    "neo_soul_push": CompingPattern(
        name="neo_soul_push",
        length_in_beats=4.0,
        hits=[
            # Bass anchors beat 1, sustained
            CompingHit(0.0, 2.5, 1.1, "bass"),
            # Bass re-anchors on &-of-3
            CompingHit(2.5, 1.5, 0.85, "bass"),
            # Chord stab on beat 2, short
            CompingHit(1.0, 0.75, 0.8, "chord"),
            # Ghost chord on &-of-2
            CompingHit(1.5, 0.5, 0.45, "chord"),
            # Syncopated push — chord hits &-of-3, sustains through bar end
            CompingHit(2.5, 1.5, 1.05, "chord"),
        ],
    ),

    "syncopated": CompingPattern(
        name="syncopated",
        length_in_beats=4.0,
        hits=[
            # Bass on beat 1
            CompingHit(0.0, 1.75, 1.1, "bass"),
            # Bass on beat 3
            CompingHit(2.0, 1.75, 0.9, "bass"),
            # Chord stab on &-of-1
            CompingHit(0.5, 0.5, 0.75, "chord"),
            # Chord on beat 2, staccato
            CompingHit(1.0, 0.4, 0.85, "chord"),
            # Ghost on &-of-2
            CompingHit(1.75, 0.25, 0.4, "chord"),
            # Chord on &-of-3, emphasis
            CompingHit(2.5, 0.75, 1.0, "chord"),
            # Ghost on &-of-4
            CompingHit(3.5, 0.5, 0.5, "chord"),
        ],
    ),

    "ballad": CompingPattern(
        name="ballad",
        length_in_beats=4.0,
        hits=[
            # Bass sustains full bar
            CompingHit(0.0, 4.0, 1.0, "bass"),
            # Chord enters gently on beat 1, long sustain
            CompingHit(0.0, 3.0, 0.75, "chord"),
            # Soft chord re-articulation on beat 3
            CompingHit(3.0, 1.0, 0.55, "chord"),
        ],
    ),
}


# ─── Swing Engine ────────────────────────────────────────────────

def apply_swing(time_in_beats: float, swing_percent: float = 58.0,
                swing_grid: float = 0.25) -> float:
    """
    MPC-style swing: delays odd-indexed grid positions while
    anchoring even-indexed (downbeat) positions.

    swing_percent: 50.0 = straight, 66.6 = triplet, 58-62 = Dilla zone
    swing_grid: 0.25 = 16th notes (neo-soul default), 0.5 = 8th notes
    """
    if swing_percent <= 50.0:
        return time_in_beats

    swing_percent = min(max(swing_percent, 50.0), 80.0)

    epsilon = 1e-6
    step = math.floor((time_in_beats + epsilon) / swing_grid)

    if step % 2 != 0:
        delay_ratio = (swing_percent - 50.0) / 50.0
        max_push = swing_grid / 2.0
        return time_in_beats + (delay_ratio * max_push)

    return time_in_beats


# ─── Velocity Engine ─────────────────────────────────────────────

def get_metrical_base_velocity(beat_offset: float, base_vel: int = 90) -> float:
    """
    Metrical accent hierarchy for 4/4 time.
    Beat 1 hits hardest, ghost notes (16th subdivisions) are barely audible.
    """
    beat_in_measure = beat_offset % 4.0

    def is_close(a, b, tol=0.05):
        return abs(a - b) < tol

    if is_close(beat_in_measure, 0.0):
        return base_vel * 1.15      # Primary downbeat
    elif is_close(beat_in_measure, 2.0):
        return base_vel * 1.05      # Secondary downbeat
    elif is_close(beat_in_measure, 1.0) or is_close(beat_in_measure, 3.0):
        return base_vel * 0.95      # Backbeats
    elif (beat_in_measure % 0.5) < 0.05:
        return base_vel * 0.80      # 8th note off-beats
    else:
        return base_vel * 0.55      # 16th subdivisions (ghost notes)


def humanize_velocity(beat_offset: float, pattern_multiplier: float,
                      voice_index: int, total_voices: int,
                      base_velocity: int = 90,
                      humanize_amount: float = 5.0) -> int:
    """
    Stochastic velocity humanization:
      1. Metrical accent weighting
      2. Pattern-defined dynamic multiplier
      3. Biomechanical hand weighting (outer voices louder)
      4. Gaussian randomization
    """
    target = get_metrical_base_velocity(beat_offset, base_velocity)
    target *= pattern_multiplier

    # Biomechanical hand weighting
    if total_voices > 1:
        if voice_index == 0:
            target *= 1.12          # Bass / thumb — natural weight
        elif voice_index == total_voices - 1:
            target *= 1.15          # Top note / pinky — cuts through mix
        else:
            target *= 0.88          # Inner voices suppressed

    # Gaussian randomization (not uniform — clusters near target)
    final = random.gauss(mu=target, sigma=humanize_amount)

    return max(1, min(127, int(round(final))))


# ─── Chord Rolling ───────────────────────────────────────────────

def calculate_roll_offsets(pitches: List[int], base_time: float,
                           bpm: float = 90.0, roll_ms_per_note: float = 12.0,
                           randomize_roll: bool = True) -> List[float]:
    """
    Staggers note onsets bottom-to-top to simulate a pianist rolling a chord.
    Converts millisecond gaps to beat fractions based on current BPM.

    At 72 BPM, 12ms ≈ 0.014 beats per note.
    A 5-note chord rolls across ~56ms total — subtle but organic.
    """
    sorted_pitches = sorted(pitches)
    time_offsets = []

    base_beat_gap = roll_ms_per_note * (bpm / 60000.0)
    current_time = base_time

    for i in range(len(sorted_pitches)):
        if i == 0:
            time_offsets.append(current_time)
        else:
            if randomize_roll:
                jitter_ms = random.gauss(mu=roll_ms_per_note, sigma=2.5)
                jitter_ms = max(2.0, jitter_ms)
                beat_gap = jitter_ms * (bpm / 60000.0)
            else:
                beat_gap = base_beat_gap

            current_time += beat_gap
            time_offsets.append(current_time)

    return time_offsets


# ─── Master Render Loop ─────────────────────────────────────────

def render_comping_block(midi_object, track: int, channel: int,
                         start_measure_time: float, bpm: float,
                         chord_pitches: List[int], pattern: CompingPattern,
                         swing_percent: float = 58.0,
                         base_velocity: int = 85) -> None:
    """
    Translates a static pitch array into a humanized, rhythmic performance.

    Pipeline per hit:
      voice separation → swing → chord rolling → velocity humanization → addNote
    """
    if not chord_pitches:
        return

    chord_pitches = sorted(chord_pitches)
    bass_pitch = chord_pitches[0]
    upper_voices = chord_pitches[1:] if len(chord_pitches) > 1 else [bass_pitch]

    for hit in pattern.hits:
        hit_global_time = start_measure_time + hit.beat_offset

        # Apply swing
        swung_time = apply_swing(hit_global_time, swing_percent, swing_grid=0.25)

        # Determine which pitches this hit triggers
        if hit.voice_group == "bass":
            target_pitches = [bass_pitch]
        elif hit.voice_group == "chord":
            target_pitches = upper_voices
        else:
            target_pitches = chord_pitches

        # Chord rolling — stagger onsets bottom to top
        rolled_times = calculate_roll_offsets(
            pitches=target_pitches,
            base_time=swung_time,
            bpm=bpm,
            roll_ms_per_note=15.0,
            randomize_roll=True,
        )

        total_voices = len(target_pitches)

        for i, pitch in enumerate(sorted(target_pitches)):
            # Duration humanization — subtle Gaussian jitter on note length
            dur_jitter = random.gauss(mu=1.0, sigma=0.04)
            final_duration = hit.duration * max(0.8, min(1.2, dur_jitter))

            final_velocity = humanize_velocity(
                beat_offset=hit.beat_offset,
                pattern_multiplier=hit.velocity_mult,
                voice_index=i,
                total_voices=total_voices,
                base_velocity=base_velocity,
                humanize_amount=6.0,
            )

            final_time = rolled_times[i]

            midi_object.addNote(
                track=track,
                channel=channel,
                pitch=pitch,
                time=final_time,
                duration=final_duration,
                volume=final_velocity,
            )
