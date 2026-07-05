# 6. Hardware shopping list — Raspberry Pi 5 prototype

Everything needed to go from "bare Pi 5 board arrives tomorrow" to "a
head-worn camera + mic prototype that runs the validated brain + vision
pipeline from `poc/` untethered." Organized in buy-priority order.

Two things about the Pi 5 specifically that change this list versus a
generic Pi build, both confirmed from official Raspberry Pi documentation:

1. **The Pi 5 has no 3.5 mm audio jack** (it was removed vs. Pi 4). Audio
   out has to go through Bluetooth, a USB audio adapter, or an I2S/HAT DAC.
2. **The Pi 5 has a smaller ("mini," 22-pin) camera/display connector**,
   not the 15-pin connector of every earlier Pi. Any Camera Module needs a
   22-pin-to-15-pin adapter cable — some kits include it, some don't.

## Tier 1 — required just to get the Pi 5 running at all

| # | Item | Why | Notes |
|---|---|---|---|
| 1 | **Official Raspberry Pi 27W USB-C Power Supply** (5V/5A) | The Pi 5 wants 5V/5A (25W). A generic phone charger or 3A supply will run it but caps USB peripheral power at 600 mA — that's tight once a camera, mic, and active cooler are all drawing current. | ~$12. Don't substitute a random USB-C charger; "not enough power" is the #1 cause of flaky Pi behavior. |
| 2 | **microSD card, 64 GB+, A2-rated / UHS-I** (SanDisk Extreme, Samsung EVO Plus, or the official Raspberry Pi 64/128 GB card) | Holds the OS + the ~2.5 GB of models from `poc/`. 32 GB is technically enough but leaves no headroom; A2 rating matters for random-read speed (OS responsiveness, model loading), not just sequential MB/s. | ~$10–15. Avoid no-name brands — they're the most common source of random corruption/failure. |
| 3 | **Raspberry Pi 5 Active Cooler** (official) | The Pi 5's Cortex-A76 cores throttle under sustained load (like multi-token LLM generation) without active cooling — this is a $6 part that directly protects the tokens/sec numbers in `docs/04-pi-deployment.md`. | ~$5–8. Clips on tool-free, plugs into the 4-pin fan header. |
| 4 | **Micro-HDMI → HDMI cable** | For first boot / troubleshooting display output. Skippable if you do a fully headless setup (Raspberry Pi Imager can pre-configure Wi-Fi + SSH before first boot), but worth having once for debugging. | ~$6. Note: micro-HDMI, not mini-HDMI. |
| 5 | **USB keyboard + mouse** (any spare ones) | Same purpose as #4 — first-boot troubleshooting. Not needed post-setup. | You likely already have these. |
| 6 | **Raspberry Pi Imager** (free software, install on your Mac) | Flashes Raspberry Pi OS (64-bit) to the microSD card and can pre-configure hostname, Wi-Fi, and SSH so you never need a monitor at all. | Free: https://www.raspberrypi.com/software/ |

**Optional but recommended in Tier 1:** a case. For active prototyping,
it's genuinely fine to leave the board bare on a set of standoffs/rubber
feet — you'll be swapping cables (camera, mic, HATs) constantly over the
next few weeks. Buy a case once the parts list stabilizes.

## Tier 2 — the actual product features (camera, mic, speaker)

### Camera

| # | Item | Why |
|---|---|---|
| 7 | **Raspberry Pi Camera Module 3** (standard **or** Wide-angle variant) | 12MP, autofocus, the standard first-party CSI camera. Wide-angle is worth considering for a headset — it captures more of what the user is actually looking at, closer to natural field of view, at some cost of "zoomed in" detail on small objects. |
| 8 | **"Camera Cable for Raspberry Pi 5"** — 22-pin to 15-pin FPC, get the **200mm** length if the Pi will sit close to the headband, or **300–500mm** if the Pi/battery will live in a pocket or backpack | The Pi 5's camera connector is physically smaller than every earlier Pi's. **Check the Camera Module 3 listing carefully** — some kits now bundle this Pi 5 cable, some don't (the Wide-angle variant historically ships *without* it). If in doubt, buy the cable separately — it's ~$5. |

⚠️ **Known gotcha:** the ribbon cable's contacts face the *opposite*
direction on the Pi 5 connector compared to Pi 4/earlier — several people
report a "no cameras available" error purely from inserting the cable
"the old way." When you get to this step, double-check orientation against
the current Raspberry Pi camera documentation before assuming the camera
itself is faulty.

**Alternative if CSI ribbon cables prove too fragile for a moving,
head-worn rig:** a USB webcam. Simpler and far more robust for a cable that
runs from a headband to a pocket (standard USB-A/C extension cables are
much more mechanically forgiving than FPC ribbon), at the cost of being
physically bulkier on the headband. Worth keeping as a fallback, not a
first purchase.

### Audio in + out (pick one lane — this is the one real decision to make)

The Pi 5 has no analog audio jack, so mic input and speaker output both
need a path. Three real options, in order of "fastest to a working demo":

**Option A — Bluetooth earbuds/headset with a mic (recommended to start).**
The Pi 5 has Bluetooth 5.0 built in — pair any earbuds/headset with a mic
and it becomes both your microphone input and speaker output, no HATs, no
drivers, no soldering. This is exactly the pattern used by existing
open-source Pi 5 voice-assistant builds (whisper.cpp + local LLM + Piper,
all through Bluetooth earbuds). Tradeoff: Bluetooth's hands-free profile
(HFP) is compressed, mono, 16kHz audio — noticeably worse transcription
accuracy than a dedicated mic, and a small extra latency hop. Fine for
proving the pipeline; revisit for the "real" headset.

- **Buy:** any Bluetooth earbuds/headset you already own, or a cheap pair
  (~$15–30) if not. No new line item cost if you already have some.

**Option B — Wired USB audio adapter + small clip mic + small speaker
(recommended once you want believable audio quality).**

| Item | Why |
|---|---|
| USB-to-3.5mm audio adapter (a "USB sound card dongle") | Gives you a standard mic-in + speaker-out jack the Pi doesn't have natively; ~$8, plug-and-play, no driver hassle. |
| Small USB or 3.5mm clip-on lavalier mic | Better signal-to-noise than Bluetooth HFP, sits close to the mouth for clean STT input; ~$10–15. |
| Small speaker or wired earbuds | Whatever's simplest — a tiny USB/3.5mm speaker or a spare pair of wired earbuds; ~$5–15. |

**Option C — ReSpeaker 2-Mics Pi HAT (skip for now, revisit later).**
An all-in-one HAT with 2 mics (enables real far-field/beamforming pickup
later — genuinely useful for a headset that needs to hear you over ambient
noise) plus a speaker output. Confirmed to work on Pi 5, **but** it
requires manually compiling a device-tree overlay (not plug-and-play) and
there are scattered reports of instability on Pi 5 specifically. Good
"phase 2" upgrade once the Bluetooth/USB path has proven the software
pipeline works — not the first thing to buy while you're still debugging
software.

**Recommendation:** start with **Option A (Bluetooth)** tomorrow — it's
zero additional purchase if you have any Bluetooth earbuds, and it gets
you to a real "speak, hear an answer" demo fastest. Buy Option B's ~$25 in
parts once you want to evaluate real STT accuracy without Bluetooth codec
loss in the way.

## Tier 3 — making it wearable

| # | Item | Why |
|---|---|---|
| 9 | **USB-C PD power bank**, rated for **at least 5V/3A**, ideally advertising **PD 3.0** and 5V/5A(25W) output | Needed to test the rig untethered from a wall outlet. Many phone power banks under-deliver current at 5V and will trigger under-voltage warnings/throttling on the Pi — check the spec sheet for actual current at 5V, not just total watt-hours. |
| 10 | **A head-worn mount for the camera** | Cheapest real option: a hat or headband with a GoPro-style mount, plus a small ball-and-socket or cold-shoe adapter sized for the tiny Camera Module 3 board. For the first prototype, velcro/tape on a hat is a completely legitimate "day 1" solution — don't over-engineer this before the software loop is proven. |
| 11 | **A small pouch, hip bag, or 3D-printed enclosure** for the Pi + power bank | Lets the compute + battery ride on a belt/backpack strap while only the camera (and mic, if wired) sit on the head — keeps weight off your head and cable runs short. |

## Tier 4 — future upgrades (not needed for this milestone)

| Item | Why it's worth knowing about, later |
|---|---|
| Raspberry Pi M.2 HAT+ and a small (128–256 GB) NVMe SSD | Solves the microSD random-read latency caveat noted in `docs/04-pi-deployment.md`. Our validated ~2 GB model loads fine off microSD in testing today, so this is a "when it bugs you" upgrade, not a blocker. |
| A simple GPIO push-button | Gives you a clean "hold to ask" interaction (push-to-talk) instead of needing wake-word or voice-activity detection for the first end-to-end demo — matches how most whisper.cpp-based assistants are driven. Cheap (~$3) and worth adding once you're wiring up the mic. |
| Ethernet cable | Only useful for a more reliable one-time setup if Wi-Fi is flaky during initial provisioning; irrelevant once the device runs offline. |

## Suggested buy order, given the Pi arrives tomorrow

1. **Tonight/tomorrow morning, if not already owned:** official 27W PSU,
   64GB+ A2 microSD, official active cooler, micro-HDMI cable — this is the
   "get it booted and running the existing `poc/` brain + vision pipeline
   locally" set. (Everything in `poc/` already runs on this alone —
   no camera/mic needed to re-validate `run_llm.py` and `pipeline.py` on
   the real Pi hardware.)
2. **Next:** Camera Module 3 + the Pi 5 camera cable, so you can swap the
   `poc/test_images/*.jpg` stand-in for a live frame.
3. **Then:** Bluetooth earbuds (Option A) to close the loop into an actual
   spoken interaction — likely zero cost if you already own a pair.
4. **Once the full loop works:** power bank + a hat/headband mount, to
   test it untethered and actually worn.
5. **Later, as needed:** Option B's wired audio parts (if Bluetooth audio
   quality bothers you), the ReSpeaker HAT (if you want 2-mic pickup), the
   NVMe upgrade (if microSD load times bother you), a push-button (to
   replace typed `--question` input with a physical control).
