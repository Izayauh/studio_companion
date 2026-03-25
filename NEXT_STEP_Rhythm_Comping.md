# Next Step: Adding Rhythm & Comping to chord_to_midi.py

## Where We Are Now

The script currently takes chord names from JSON (e.g. `Fm9`, `Dbmaj7`, `C7b9`) and outputs
a `.mid` file with correct, spread voicings using music21. The problem: every chord is a
single block of notes held for an entire bar. It sounds like a theory textbook, not a player.

## What's Missing: Rhythmic Comping

"Comping" (short for accompanying) is how keyboard players *actually* play chords in R&B,
neo-soul, and pop. Instead of pressing all the notes and holding them for 4 beats, a player
breaks the chord into a rhythmic pattern within the bar — short stabs, ghost notes, held
tones, and rests.

This is the difference between a chord chart and a performance.

## Core Concepts to Research

### 1. Comping Patterns (the big one)
A comping pattern defines *when* within a bar each chord hit lands, *how long* it's held,
and *how hard* it's played.

Example — a neo-soul "bounce" pattern in a single bar of 4/4:

```
Beat:    1     &     2     &     3     &     4     &
Upper:   HIT---      ghost       HIT-        ghost
Bass:    HIT------------------   HIT------------------
```

- "HIT" = full velocity note (85-105)
- "ghost" = soft re-articulation of the same chord (55-70 velocity)
- Dashes = note is held (sustained)
- Blank = rest (silence)

The bass (root note) usually plays a simpler, more sustained pattern underneath.

**Search terms:** "neo soul comping patterns", "R&B keyboard comping", "Rhodes comping rhythms",
"gospel piano comping patterns"

### 2. Ghost Notes
Very soft hits (low MIDI velocity, ~55-70 out of 127) that fill rhythmic space without
dominating. They create the "feel" between main hits. Think of them like a drummer's ghost
notes on the snare — you feel them more than hear them.

**Search terms:** "ghost notes piano MIDI", "velocity layers keyboard"

### 3. Swing / Groove
Straight timing puts every 8th note exactly on the grid. Swing pushes the upbeats
(the "ands") slightly late, creating a laid-back, leaning-back feel. This is critical for
R&B and neo-soul.

Technically: in straight time the "& of 1" falls at beat 1.5. With ~60% swing it falls
closer to beat 1.67 (triplet feel). With heavier swing, even later.

**Search terms:** "MIDI swing quantize", "swing ratio explained", "triplet feel vs straight"

### 4. Velocity Curves / Humanization
Real players don't hit every note at the same volume. Downbeats (1 and 3) are naturally
louder, upbeats softer. Adding slight randomness to velocity and micro-timing makes
MIDI feel human instead of robotic.

**Search terms:** "MIDI humanization techniques", "velocity curve piano MIDI"

### 5. Staggered Onsets (Chord Rolling)
A pianist doesn't press all 5 notes of a chord at the exact same millisecond. There's a
natural tiny spread (5-20ms) from bottom to top. This subtle stagger makes block chords
feel organic.

**Search terms:** "MIDI strum effect chords", "chord roll MIDI", "arpeggio vs block chord MIDI"

## How This Would Work in the Script

The implementation approach:

1. **Define a few named patterns** as data (not complex logic). Each pattern is just a list
   of hits per bar:
   ```
   hit = (beat_offset, duration_in_beats, velocity_multiplier)
   ```

2. **Separate bass and upper patterns** — bass stays simple and anchoring, upper voicing
   gets the rhythmic movement.

3. **Pattern is selected via JSON input:**
   ```json
   {
     "chords": ["Fm9", "Dbmaj7", "Eb6", "C7b9"],
     "bpm": 72,
     "rhythm": "bounce"
   }
   ```

4. **Default to a pattern with feel** (not whole notes). User can set `"rhythm": "straight"`
   to get the current flat behavior if they want pads.

## Proposed Patterns

| Name         | Feel                          | Use Case                        |
|--------------|-------------------------------|---------------------------------|
| `straight`   | Whole notes, no rhythm        | Pads, ambient, string sections  |
| `bounce`     | Neo-soul Rhodes groove        | Frank Ocean, Daniel Caesar      |
| `syncopated` | Heavy off-beat emphasis       | Anderson .Paak, Kaytranada      |
| `ballad`     | Gentle re-hits, lots of sustain| Slow jams, 6LACK, SZA          |

## Reference Listening

To hear what good comping *sounds like* before looking at the technical side:

- Frank Ocean "White Ferrari" — minimal, sustained chords with subtle movement
- Daniel Caesar "Best Part" — classic neo-soul Rhodes comping pattern
- Tom Misch "South of the River" — jazzy, rhythmic chord stabs
- Mac Miller "Dunno" — simple but bouncy chord rhythm
- Jon Bellion "All Time Low" — pop/R&B keys pattern with syncopation

Listen to the *keyboard/Rhodes specifically* and notice: it's never just holding the chord
flat. There's always a rhythm to it.

## Libraries / Tools (No Extra Dependencies Needed)

Everything described above is pure MIDI note placement logic. It doesn't require any new
libraries — just smarter use of `midiutil`'s `addNote(track, channel, pitch, time, duration, velocity)`.

The `time` parameter accepts floats (e.g. 1.5 = the "and" of beat 2), so we already have
sub-beat precision. The `velocity` parameter (0-127) gives us dynamics. That's all we need.

## Summary

The chord parsing and voicing engine is done. The missing layer is: instead of placing each
chord as one big note event per bar, place it as a series of rhythmic hits defined by a
comping pattern. This is a data-driven addition (pattern definitions) more than complex new
logic.
