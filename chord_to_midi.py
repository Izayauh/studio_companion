#!/usr/bin/env python3
"""
chord_to_midi.py — Text-to-MIDI Chord Generator
Takes LLM-generated chord progressions (JSON) and outputs rich, voiced MIDI files.
Uses music21 for chord parsing/theory and midiutil for MIDI file creation.
"""

import json
import sys
import os
import re
import random
from music21 import harmony
from midiutil import MIDIFile
from comping_engine import PATTERNS, render_comping_block


def normalize_chord(name):
    """
    Translate common LLM chord notation into music21's expected format.
      - Flat roots: Db -> D-,  Eb -> E-,  Bb -> B-  etc.
      - Unicode:    ♭ -> -,   ♯ -> #
      - Case:       maj9 -> Maj9  (music21 needs capital M for extended maj chords)
      - Slash:      Dm7/A stays as-is (music21 handles it)
    """
    s = name.strip()

    # Unicode symbols
    s = s.replace("\u266d", "-").replace("\u266f", "#")

    # Flat root: if second char is 'b' after a note letter, it's a flat sign
    # (distinguishes Bb = B-flat from Bm = B minor)
    if len(s) >= 2 and s[0] in "ABCDEFG" and s[1] == "b":
        # Make sure it's not just the note "B" followed by a quality
        # 'b' is flat when followed by: end-of-string, digit, letter that
        # starts a quality (m, M, d, a, s, +, °, etc.), or another accidental
        if len(s) == 2 or s[2] not in "b#":
            s = s[0] + "-" + s[2:]

    # Capitalize 'maj' -> 'Maj' ONLY before 9/11/13 (maj7 works lowercase,
    # but Maj7 breaks — music21 is picky about this specific inconsistency)
    s = re.sub(r"maj(?=9|11|13)", "Maj", s)

    return s


def voice_chord(chord_symbol, prev_upper=None):
    """
    Voice a chord with R&B-style spread:
      - Root isolated in octave 3 (bass)
      - Remaining tones placed ascending from octave 4, naturally spreading
        into octave 5 for extended chords (9ths, 11ths, 13ths)
      - Voice leading: keeps upper voicing close to the previous chord
        to avoid jumpy, mechanical transitions

    Returns (bass_midi_note, [upper_midi_notes])
    """
    root = chord_symbol.root()
    bass = root.pitchClass + 48  # root in octave 3

    pitches = list(chord_symbol.pitches)

    # Collect pitch classes for upper voicing, skip root (it's in the bass)
    upper_pcs = []
    skipped_root = False
    for p in pitches:
        if p.pitchClass == root.pitchClass and not skipped_root:
            skipped_root = True
            continue
        upper_pcs.append(p.pitchClass)

    # Fallback: if chord only had a root somehow, use all pitches
    if not upper_pcs:
        upper_pcs = [p.pitchClass for p in pitches]

    # Place notes ascending from C4 (MIDI 60) — each note must be
    # at or above the previous one, so extended chords naturally spread
    upper = []
    floor = 60
    for pc in upper_pcs:
        note = pc
        while note < floor:
            note += 12
        upper.append(note)
        floor = note

    # Voice leading: if there's a previous chord, shift the whole voicing
    # by octave if the center drifted too far (keeps transitions smooth)
    if prev_upper and upper:
        prev_center = sum(prev_upper) / len(prev_upper)
        curr_center = sum(upper) / len(upper)
        diff = curr_center - prev_center

        if diff > 6:
            upper = [n - 12 for n in upper]
        elif diff < -6:
            upper = [n + 12 for n in upper]

        # Clamp to a playable piano range (A3–A5)
        while min(upper) < 57:
            upper = [n + 12 for n in upper]
        while max(upper) > 81:
            upper = [n - 12 for n in upper]

    return bass, sorted(upper)


def generate_midi(input_source, output_path="output_loop.mid", default_bpm=120):
    """
    Main pipeline: JSON -> chord parsing -> voicing -> MIDI file.

    input_source: path to .json file, raw JSON string, or a dict
    output_path:  where to write the .mid (default: output_loop.mid)
    default_bpm:  tempo if not specified in JSON (default: 120)
    """
    # --- Parse input ---
    if isinstance(input_source, dict):
        data = input_source
    elif isinstance(input_source, str):
        if input_source.endswith(".json") and os.path.isfile(input_source):
            with open(input_source, "r") as f:
                data = json.load(f)
        else:
            try:
                data = json.loads(input_source)
            except json.JSONDecodeError:
                print("Error: Could not parse JSON string.")
                print("  PowerShell mangles inline JSON — use a .json file instead:")
                print('  python chord_to_midi.py input.json')
                return None
    else:
        print("Error: input must be a file path, JSON string, or dict.")
        return None

    chords = data.get("chords", [])
    bpm = data.get("bpm", default_bpm)
    rhythm = data.get("rhythm", "neo_soul_push")
    swing = data.get("swing", 58.0)

    if not chords:
        print("No chords found in input.")
        return None

    # Resolve comping pattern
    pattern = PATTERNS.get(rhythm)
    if pattern is None:
        print(f"  Unknown rhythm '{rhythm}', using neo_soul_push.")
        print(f"  Options: {', '.join(PATTERNS.keys())}")
        pattern = PATTERNS["neo_soul_push"]

    # --- Build MIDI ---
    midi = MIDIFile(1)
    track = 0
    channel = 0
    midi.addTempo(track, 0, bpm)

    beat = 0
    bar_length = 4  # 4/4 time, one chord per bar
    total_beats = len(chords) * bar_length  # total loop length
    prev_upper = None

    for chord_name in chords:
        # Normalize LLM notation -> music21 notation
        normalized = normalize_chord(chord_name)

        # Parse chord symbol
        try:
            cs = harmony.ChordSymbol(normalized)
            if not cs.pitches:
                raise ValueError("no pitches")
        except Exception:
            print(f"  Skipping unrecognized chord: '{chord_name}' (normalized: '{normalized}')")
            beat += bar_length
            continue

        bass, upper = voice_chord(cs, prev_upper)

        # Feed pitches to the comping engine
        all_pitches = [bass] + upper
        render_comping_block(
            midi_object=midi,
            track=track,
            channel=channel,
            start_measure_time=beat,
            bpm=bpm,
            chord_pitches=all_pitches,
            pattern=pattern,
            swing_percent=swing,
            base_velocity=85,
            total_duration=total_beats,
        )

        prev_upper = upper
        beat += bar_length

    # --- Write file ---
    with open(output_path, "wb") as f:
        midi.writeFile(f)

    rhythm_label = pattern.name
    print(f"Done: {output_path}  |  {len(chords)} chords  |  {bpm} BPM  |  {rhythm_label}  |  swing {swing}%")
    return output_path


# ── CLI entry point ──────────────────────────────────────────────
if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage:")
        print('  python chord_to_midi.py input.json')
        print('  python chord_to_midi.py \'{"chords": ["Fm9", "Dbmaj7", "Eb6", "C7b9"]}\'')
        sys.exit(1)

    generate_midi(sys.argv[1])
