# Trinity — DM Brief

Everything here comes from the original ZIL source (`resources/zil/trinity/*.zil`, the same files as historicalsource/trinity), checked against `worlds/trinity.json`. **[UNVERIFIED]** marks anything that is not. Some routines are **missing from the JSON** but present in the source: `GO-TO-LONG-WATER`, `I-SHADOW`, `NEW-OSIGN`, `READ-DIAL`, `I-ICE`, `I-LEM`, `I-MAGPIE`, `MOVE-MEEP` and `MAIN-LOOP`. Read those with `grep -n "ROUTINE NAME" resources/zil/trinity/*.zil`.

Note: the JSON's `dm_instructions` mention a "London Blitz (1940)" zone. **No such zone exists.** London is the 1980s, on the day World War III starts.

## 1. Arc & structure

1. **Kensington Gardens, the present.** It is the last afternoon of a $599 London package tour. The player is a tourist; East–West tension is in the news. A nuclear strike is coming, and the player must leave the Gardens before it lands. Prams, an umbrella, the wind and a roadrunner get them to **Long Water**. There a white door hangs above the water while a Soviet missile falls in slow motion.
2. **The "Inside"** (the rooms flagged SHADOWY). This is a dreamlike hub: a meadow, toadstools, a giant sundial at the top of a vast stair, a cottage with a magpie, bogs, a barrow, the river Styx. The hub has no clock deadline. The wristwatch here shows *"digits are flashing randomly."* Seven toadstools have doors, and each door is tied to one symbol on the giant dial. A door opens when the dial's shadow reaches its symbol.
3. **Excursions.** Each door leads to one moment in nuclear history. Each excursion has a hard deadline (see §2). You collect an item there and return through the same door, which must still be open.
4. **Trinity site, New Mexico, 16 July 1945**, starting at 4:58:30 am. This is the final zone; there is no Inside after it.
5. **Epilogue.** The player wakes back at Palace Gate at 3:30:00 pm with everything reset. The story ends when the umbrella blows into the tree at Lancaster Gate (`I-BLOW` with `TR?` set).

## 2. Clock & deadlines (most important)

**Tick rule.** The game starts at **15:30:00 (3:30:00 pm)**. `CLOCKER` runs once at the end of each eligible move. It **runs all queued interrupts first** and only then adds **15 seconds**. So an interrupt sees the time the watch showed *before* the move. Tick N therefore runs with the watch at 3:30:00 + 15·(N−1) s. Interrupts queued during a move run at the end of that same move.

**Moves that do NOT tick:**
- **Game verbs:** INVENTORY, TIME, SCORE, SAVE, RESTORE, SCRIPT, UNSCRIPT, DIAGNOSE, HELP, VERBOSE, BRIEF, SUPERBRIEF, VERSION, QUIT, NOTIFY and TELL.
- **Failures and refusals:** parser failures; "You can't see any X here."; every blocked exit ("You can't go that way", "The iron fence blocks your path", and so on); and refusals that return RFATAL.

**WAIT / Z** can take up to **4 ticks (1 minute)**. It stops after the first tick on which any interrupt prints something; if a set-piece is running, WAIT is 1 tick. **WAIT n** (n ≤ 120) means up to n *ticks*, not minutes, with the same early stop.

**Engine:** use `--advance-turn` only on moves that tick. Use `--set-clock` whenever a routine SETGs the clock, and mirror `QUEUE`/`DEQUEUE` with `--queue`/`--dequeue`.

**Watch text** (`TELL-TIME`): `Your wristwatch says it's 3:57:45 pm.` The format is 12-hour, with no leading zero on the hour and two-digit minutes and seconds. If `FREEZE?` is set, add a new line: `(That's odd. The "seconds" display has stopped working.)` In SHADOWY rooms it prints `Your wristwatch's digits are flashing randomly.` On the Nagasaki playground, TIME reads the school clock instead.

### Gardens (boot queue: I-CRANE-APPEARS, I-BWOMAN, I-AIR-RAID, I-BOY, each runs every tick)

| Tick | Watch before move | Event |
|---|---|---|
| 1 | 3:30:00 | — |
| **112** | **3:57:45** | **I-AIR-RAID** sets RAID?=10→9: *"A steady drone begins to rise above the east wind…Air-raid sirens."* The bird woman's FDESC changes to "A forgotten woman, too aged to run, is sitting nearby." |
| 113–119 | 3:58:00–3:59:30 | One escalation line per tick: another siren (the bubble boy flees Inverness Terrace) → sirens howling → shouts → police alarms → megaphones → gunfire → *"The ground trembles with the roar of jet interceptors."* |
| **120** | **3:59:45** | **VAPORIZE-GARDENS**: *"The [wind] falls silent, and a new star flashes to life over the doomed city."* Death. |

While the raid is on, room text changes (prams "flee", tourists are "frightened"/"panic-stricken"), and in the Wabe the crowd clauses are dropped. The escape command (opening the umbrella in the pram) does not itself tick, so it still works at 3:59:45.

Other Gardens timers:
- **I-CRANE-APPEARS** fires only at Round Pond. The first tick there "buys one move"; the paper bird floats up on the **second tick spent at the Pond**.
- **I-BLOW** is queued with delay 2 on the first entry to Lancaster Gate. It fires at the end of the *next* move: the gust takes the umbrella into the tree and the woman shuffles off. Until then, every exit from Lancaster Gate is refused ("You begin to walk past the old woman, but stop in your tracks") and costs no time.
- **I-RUBY:** one tick after the ruby appears, the roadrunner snatches it. The wind then **swings from east to west**.
- **I-BIKES:** after the grass first throws you off, the next visit to Lancaster Walk shows a couple cycling across the grass.

### Long Water (`GO-TO-LONG-WATER`)
- On arrival the clock is set to **3:59:45 and frozen** (`FREEZE?`). MOVES still counts, but the time no longer changes, so re-pin it with `--set-clock 15:59:45` after each advance.
- The interrupts I-AIR-RAID, I-BWOMAN, I-BOY, I-MEEP, I-CRANE-APPEARS and I-BIKES are all dequeued. **I-LONDON-HOLE** starts with HCNT=7 and counts down one per tick:

| HCNT | Event |
|---|---|
| 6 | The wind is still. |
| 5 | A missile is hanging in the sky. |
| 4 | **The white door appears** (`LWDOOR` touched). |
| 3 | Ravens fly through the door. |
| 2 | Swans and ducks paddle through. |
| 1 | The log arrives, carrying the roadrunner. |
| 0 | Vaporized. |

- After the door appears, the player gets 4 commands. They need 2: **E** (wade, "Wading") then **E/IN** (through the door).
- Trying any other exit refuses you, but it still runs one HCNT step.
- Entering while HCNT > 1 adds the roadrunner fluttering past you through the door.

### The Inside: the shadow clock (`I-SHADOW`, every tick while the sun moves)
- **Shadow position.** The shadow position steps through 0–12, one step per 13 ticks; even steps are on a symbol, odd steps are between symbols. The door for symbol k **opens on the 5th tick** of its step and **closes on the 7th**, so it is open for only 2 ticks unless the sun is stopped. When a door closes, the meadow door (and any door seen from outside the Inside) *"shimmers and fades from view"* for good.
- **Door timing from arrival.** The meadow door closes as you step out. Symbol 2 opens 24 ticks after arrival, then every 26 ticks: 24, 50, 76, 102, 128, 154. At the wrap after step 12 comes the twin-sun sunset/sunrise set-piece; a full cycle is 169 ticks.
- **Lever** (it rises once the gnomon is screwed into the giant dial): PUSH/LOWER stops the sun, so the open door **stays open**; PULL/RAISE restarts it.
- **Ring:** TURN RING TO <symbol/number/name> jumps the shadow straight to that symbol (step 5) and opens its door. The sun keeps moving, so the door shuts 2 ticks later unless the player lowers the lever.
- **I-SHADOW keeps running during excursions.** The return door shuts if the sun is not stopped. Muttered hint: "Gnomon can tether time or tide."

| Symbol | Name | Toadstool | Leads to |
|---|---|---|---|
| 1 | Omega | Meadow | (arrival; fades for good) |
| 2 | Mercury | Waterfall | Orbit |
| 3 | Pluto | Ossuary | Underground test tunnel |
| 4 | Neptune | Mesa (cross the felled oak) | Pacific H-bomb (the source names the island Elugelab/Eniwetok) |
| 5 | Libra | Cottage garden | Siberia |
| 6 | Mars | Moor | Sky over Nagasaki |
| 7 | Alpha | Islet across the Styx | Trinity |

### Excursion deadlines (tick 1 is the arrival move)

| Zone | Clock re-base on entry | Deadline |
|---|---|---|
| **Orbit** (`AT-FALLS-IN`) | No re-base. I-ORBIT runs at once (ORBCNT=1), then once per tick. | Door drops away (1); door vanishes at the moon's horns (2); satellite appears (3); satellite closer, and the lump tugs if carried (4); lump clamps you to the satellite, if you are in a bubble (5); door reappears (6); ICBM contrail, satellite heads for the door (7); door very close (8); **laser fires, death (9)**. **I-VACUUM**, if not in a bubble: "uncomfortable", then "blood boil", then death on the 3rd step. **Bubble-suit life (`SUITED?`=4)** counts down only *outside* orbit/sky: "shimmers", "sagging", "won't hold up much longer", then pop. |
| **Tunnel** (`OSSUARY-IN`) | **5:50:00 pm**; I-TUNNEL | **6:00:00 pm = tick 41**: the bomb erupts in white glare. A walkie-talkie that is on, with antenna up, on frequency **42** (the default), says "Ten" … "One" at each :00. |
| **Pacific** (`ON-MESA-IN`) | **4:52:00 am**; I-TIDE, I-FLIPPER | **5:00:00 = tick 33**, a multimegaton blast. Tide/coconut events: 4:54:15 and 4:54:45 tide rising; **4:55:15** coconut drops on the islet; **4:56:15** it floats into the lagoon off West Beach; 4:57:45 sand squishy; **4:58:15** coconut gone, if you are at West Beach. The PA, while its switch is on, calls "Zero minus N minutes" at each :00, "ninety seconds" at 4:58:30, then 4:59:15/30/45, plus jargon at :30. I-FLIPPER: the 4th tick off the scaffold shows a gray fin, then it glides closer, then the dolphin surfaces. |
| **Siberia** (`IN-GARDEN-IN`) | **2:41:00 pm**; I-RODENTS, I-RCOUNT | **3:00:00 pm = tick 77**: glare, and a radioactive gale. Russian loudspeaker countdown, heard on or under the platform: "<n> minut" each :00 (Dyevianatsat = 19 at 2:41 … Tree = 3), "Dva minut" at 2:58, "Dyevianosta sekund" at 2:58:30, then 60/45/30/15 sekund. After :49 the exit text reads "Numb with cold…" |
| **Nagasaki** (`ON-MOOR-IN`) | **10:54:00 am**; arrive in IN-SKY, I-FALLING queued with delay 2 | The player has **exactly one command** to open the umbrella (or already be in a bubble), else death at tick 2. **10:56:00 (tick 9)** girl appears. **11:01:15** faint drone; **11:01:30** louder, the teachers come; **11:01:45** power dive; **11:02:00 (tick 33)** flash, and death (a shielding epitaph if the girl is with you). Riding the giant bird (I-FLIGHT) pins the clock at 11:01:15. On the 2nd flight step the Mars door must be open, else Fat Man. |
| **Trinity** (`GO-TO-SHACK`) | **4:58:30 am**. I-SHADOW is dequeued, mirror mode (`FLIP?`) is reset, wire types are re-randomized, I-VOICES starts. | **5:29:45 = tick 126**: detonation, wherever you are. |

**Trinity timeline in detail:**
- **I-VOICES:**
  - 4:58:30: faint voice below.
  - 4:58:45: voice again, with a clatter.
  - 4:59:00: "Towerside breaker closed."
  - 4:59:15: wind gust.
  - **4:59:30:** searchlight floods the tower.
  - 4:59:45: wind.
  - **5:00:00:** the jeep leaves, and I-FLARE, I-TRINITY, I-DOG and I-OPPIE are queued.
  - Being on the ladder (ON-TOWER) at any point during I-VOICES means **immediate capture**.
- **Listening on the walkie-talkie** (antenna up, jeep radio seen, tuned to its random 21–79 frequency):
  - Chatter continues through 5:08:45.
  - 5:09:00–5:09:45: "Are we all in on this?" … then the Star-Spangled Banner and "zero minus twenty minutes."
  - At each :45 from 5:10:45: "Zero minus N minutes."
  - At each :15: technobabble.
  - 5:27:30: "Ninety seconds to auto-sequencer."
  - 5:28:00/15/30/45: auto-sequencer countdown.
  - **5:29:00** "Commence auto-sequence"; 5:29:15 thirty seconds; 5:29:30 fifteen seconds; **5:29:45** boom.
- **Flares and warnings (outdoors):**
  - **5:24:45:** first flare (five-minute warning on the loudspeaker at S100/W100).
  - **5:27:45:** two-minute warning; the dog is removed; GIs dive into trenches.
  - **5:28:45:** third flare.
- **Tower exposure (`TOLERANCE`).** Every tick on the ladder or platform before 5:30 costs 1 of TOLERANCE (start 4). It does not drop while the dog distraction is running; when the distraction starts it is reset to 2. At 0: "Scrub…", the police converge, and the game is lost. **Inside the shack is safe.**
- **Desert travel.** Walking between desert rooms *without both boots charged and worn* costs **19 extra silent ticks per step (29 in "boring" rooms; 9/19 for RUN or JOG)**. Interrupts still run and deaths still fire. With both boots: "Whoosh!" and a normal single tick.

### Other countdowns
- **Lantern:** 30 ticks of light in total, across all uses. Messages at 9 ("getting dimmer") and 4 ("quite dim now"); at 0 "flickers and goes out".
- **Icicle:** 6 ticks out of the cold. It refreezes in chilly rooms (the top of the stair) and in vacuum.
- **Barrow, unlit:** "Something is breathing…", "getting closer", "a few feet", then the neck snaps. Entering from the Ossuary in darkness gives *no* warning: death on the next tick.
- **Bee:** a 2nd sting gets a warning; a 3rd kills.
- **Snake bite:** you collapse 1 tick later.
- **Held breath:** 4 ticks.
- **Cauldron:** after the recipe is complete, 3 ticks; the 2nd tick rumbles and the 3rd explodes. You die if you are inside.
- **Windmill landing:** 4 ticks before it gives way.
- **Charon:** wants payment within 2 ticks of boarding, else you are kicked off. The dory cycle is 12 ticks.
- **Bubble boy (Promontory):** dips, blows, then bops to music.
- **Venus flytrap:** reopens 10 ticks after closing.

## 3. Text conventions

**Constants** (resolved from source, `misc.zil`; quote them literally):

| Constant | Text | Constant | Text |
|---|---|---|---|
| `,TON` | " to the north" | `,PERIOD` | ".⏎" |
| `,TOS` | " to the south" | `,PCR` | ".⏎⏎" |
| `,TOE` | " to the east" | `,BRACKET` | "]⏎⏎" |
| `,TOW` | " to the west" | `,PTHE` | ". The " |
| `,PA` | ". A " | `,ALLATONCE` | "All at once " |
| `,OUTASITE` | " out of sight.⏎" | `,CANT` | "You can't " |
| `,DONT` | "You don't " | `,YOU-SEE` | "You see " |
| `,YOURE-ALREADY` | "You're already " | `,AT-MOMENT` | " at the moment." |
| `,AS-IF` | ". It looks as if " | `,AGROUND` | " across the ground" |
| `,CTHEMEEP` | "The roadrunner " | `,CTHELEM` | "The lemming " |
| `,ONE-SHADE` | "One of the shades " | `,Z-MINUS` | "⏎\"Zero minus " |
| `,INRANCH` | ", into the ranch.⏎" | `,INTO-DESERT` | "into the desert" |
| `,ARROW-ON` | "The arrow on the ring is already pointing " | `,ALLPRAMS` | "All prams lead to the Kensington Gardens." |
| `,CHANGES` | " changes your mind." | `,RAZOR` | " divides the sky like a razor" |
| `STAIR-DIR` | " Up" | | |

So Palace Gate reads "Shaded glades stretch away **to the northeast**".

**Wind.** `SAY-WIND` prints "east wind" until the ruby is stolen, then "west wind". When `FLIP?` is set, `SAY-EAST`/`SAY-WEST` swap the words.

**Inventory** (`V-INVENTORY`). Pattern: `You're holding A, B and C. Inside the X you see …. You're wearing W, and you have P in your pocket.` Variants:
- Nothing held: `You're not holding anything, but you're wearing a wristwatch. You also have … in your pocket.`
- Empty pocket ends with `…r pocket is empty.`
- A lit lamp is listed as "(providing light)".

At the start the player holds nothing, wears the wristwatch, and has a credit card and a seven-sided coin in the pocket. **[UNVERIFIED]** the order in which those two are listed.

**Standard refusals:**
- "You can't go that way." outdoors / "There's no exit that way." indoors.
- "The <iron fence / statue of Queen Victoria / thicket / tall fence / cliff / hedge / stone wall / reservoir / equipment shed / building> blocks your path." (all the `*-BLOCKS` routines)
- Leaving the Gardens through a gate: "A surge of [haughty|starched|offended] nannies / [gawking|babbling|fat] tourists blocks your path."
- "[Which way do you want to go in?]" / "…out?]"
- "You can't see any X here."
- IMPOSSIBLE: "That's impossible." / "What a ridiculous concept." / "You can't be serious."
- HOW?: "How do you expect/intend to do that?"
- "It's too dark to see."
- "Time passes."
- "Perhaps you should take a moment to examine the X."

**Voice in your ear** (Inside, or anywhere after Trinity): `A voice in your ear whispers, "Smart move."` or `"Well done," mutters a voice in your ear.`

**Score:**
- On a gain: bold `[Your score just went up by N points. The total is now X out of 100.]` The first time only, add `[NOTE: You can turn score notification on or off at any time with the NOTIFY command.]`
- SCORE command: `[Your score is X points out of 100, in M moves. This gives you the rank of Tourist.]` Ranks: Tourist below 15, Explorer below 50, Historian below 100. At exactly 100 the rank is "Tourist." again, deliberately.

**Status line:** the centered room name and nothing else, with no score or time. Suffixes: ", in a soap bubble", ", in the perambulator", ", in the dish", ", in the dory" and ", in a sandpile". Unlit rooms show "Darkness".

**Death:** the player wakes at "The River". Charon's dory lands, he takes "a silver coin you didn't know you had", and the RESTART/RESTORE/QUIT prompt follows.

## 4. Characters & recurring behaviour

- **Bird woman (Broad Walk).** About half the turns she cries "Thirty p! Thirty p a bag", "Feed the hungry birds" and similar; during the raid it becomes "Sirens! The sirens", "Lord, have mercy". If you pay and leave without taking the bag or change (`LAYAWAY`), she pockets them ("Keep 'em myself").
- **Pigeons.** Dropping the bag in the Gardens means they eat every crumb.
- **Roadrunner ("meep").** Steals the ruby, then flees along fixed routes. On later visits it zig-zags past the player. It is the log passenger at Long Water and waits on the islet for the Alpha door. At Trinity it is a companion: it pecks crumbs (4 moves per bag), fetches on command, bothers the dog, and hates being held or caged.
- **Paper bird.** It floats at Round Pond, holds a note, and refolds into a crane that grows into a giant bird at Nagasaki.
- **Boy with bubbles.** At Inverness Terrace he is a child with headphones; on the Promontory he is a giant.
- **Old woman (Lancaster Gate)** has a scarred face; she is the Nagasaki girl, grown old.
- **Magpie** (cottage) babbles the recipe: "Milk and honey, fresh whole lizard / Killed in the light of a crescent moon / Mix 'em with a pinch o' garlic / Then stand back! 'Cause it go BOOM".
- **Others:** the barrow wight, Charon and the shades, the dolphin, the crabs, the lemmings, the skink, the giant bee, the Venus flytrap, the Russian loudspeaker, the "thin man" (Oppenheimer, who appears periodically at the S100 shelter), Able/Baker/Pittsburg on the radio, and the German shepherd.

## 5. Engine gaps the DM must cover

- **The clock.** Run the clock, the interrupts and every rule in §2 yourself, including `FREEZE?` and the no-tick verbs.
- **Conditional exits** (`PER` routines). The engine cannot evaluate these, so apply them yourself:
  - `IFENCE-BLOCKS`, `VICTORIA-BLOCKS`, `THICKET-BLOCKS`, `HEDGE-`, `SWALL-`, `CLIFF-` and the other `-BLOCKS` routines are plain refusals that cost no time.
  - `EXIT-GARDEN` (south, east and out at the gates) is a refusal ("A surge of … blocks your path"), or, if you are in the pram, it gets you out of it.
  - `GARDEN-OUT`/`WABE-OUT` mean "which way out?", or leaving the pram.
  - In the Wabe, `WABE-N/NE/SE/SW/NW`: the first attempt only prints *"A noise makes you hesitate…the gnomon…wobbles"* and you stay put; after that the exits work.
  - At Long Water, `DONT-MISS-MISSILE` freezes you in place and advances the countdown.
  - `WALK-ON-GRASS` throws you off the grass (and closes an open umbrella).
  - `MEADOW-EXIT`, `CHASM-FALL` and the `*-IN` door routines are self-explanatory. Every toadstool door refuses entry while the umbrella is open.
- **Mirror world.** Climbing through the arbor (in one side, out the other) toggles `FLIP?`. While it is set, in SHADOWY rooms E↔W, NE↔NW and SE↔SW are swapped *for movement*, and "east" and "west" swap in the text. Every flippable item you are *not* carrying becomes FLIPPED and reads mirrored: the gnomon, credit card, crane paper, umbrella, walkie-talkie and coins.
- **Unreachable-win traps:**
  - The pigeons eat the crumbs.
  - A door closes behind the player.
  - The lantern runs out.
  - The coconut drifts away.
  - The breaker is opened twice.
  - Desert walking without the boots wastes the clock.

## 5a. Feelies (the player has no box — supply these when the game points at them)

- **Sundial** (`SYMBOLS`: "[You'll find the symbols reproduced on the sundial in
  your Trinity package.]"). Seven symbols round the dial, running clockwise from omega,
  in the order of §2's symbol table: 1 Ω Omega · 2 ☿ Mercury · 3 ♇ Pluto ·
  4 ♆ Neptune · 5 ♎ Libra · 6 ♂ Mars · 7 α Alpha — plus a compass rose, and
  "TEMPUS EDAX RERUM" across the bottom. In the mirror world (`FLIP?`) they run
  counterclockwise and are inscribed backwards. Do NOT add which door each symbol
  opens — the dial never said.
- **Map of the Trinity site** (`MAP-F`, the large map on the wall: "[This is the map
  included in your Trinity package.]"). Describe the site as a map would: the
  named places and the roads between them, from the engine's locations around the
  tower (the shack, the S100 / W100 / N75 bunkers and the others, the ranch, the
  reservoir). Names and layout only.
- **HELP** points at InvisiClues booklets and an order form. Say there are no
  booklets in this edition, and that the player can ask the DM for a hint with
  `god mode:`.

## 6. DM-ONLY SPOILERS — use only to adjudicate whether an action succeeds; never hint, foreshadow or steer

- **Gardens:**
  - Unscrew the gnomon at the Wabe and take it.
  - Take the ball from the Flower Walk beds and throw it at the umbrella in the tree at Lancaster Gate; the umbrella drops.
  - Give the seven-sided coin to the bird woman; take the bag and the 20p change.
  - Open the pram at Black Lion Gate and push it.
  - At Round Pond, on the 2nd tick, take the paper bird and unfold it for the note.
  - With the pram on Lancaster Walk (or at Round Pond or Broad Walk), get in and rummage in the bag. A ruby falls out; the roadrunner takes it; the wind turns west.
  - Open the umbrella in the pram to fly to Long Water. Then E, E through the door.
- **Gnomon:** in the normal world the London gnomon's thread does not match the giant dial. Carry it through the arbor once (world flipped, gnomon not), or drop it and go through again (gnomon flipped, world normal). Either way, screwing it in raises the lever (+5). Use the ring, or wait, then lower the lever.
- **Light:** the rotten log in the South Bog leaves a glowing splinter. The axe is at the top of the arbor.
- **Felling the oak:** cut the oak at Chasm's Brink with the axe. It falls 2 ticks later and bridges to the Mesa.
- **Ice and metal:** throw the axe at the icicles in the Ice Cave and carry the icicle (refreeze it at the dial). Put it on the hot lump in the crater, then take the lump; it is magnetic.
- **Honey:** reach into the hive and lead the bee to the North Bog, where the open flytrap eats it. Then get the honey.
- **Pluto (Tunnel):** take the lantern and the walkie-talkie. Turn on the lantern and drop it in the east tunnel; put the splinter in the crevice; the flushed skink runs in circles, so take it and pocket it. Return through the door. With light, search the ossuary bones for the skeleton key; the keyhole opens a slope to the Ice Cave.
- **Neptune (Pacific):** go down the scaffold. In the box, press the red button and the switch to turn off the PA. Go out. Swimming to the islet means crabs. When the dolphin appears, point at the floating coconut and it throws it to you. Leave before 5:00.
- **Libra (Siberia):** follow the lemmings north and east to the cliff. Put the lemming stuck in the fissure into the birdcage (from the cottage; release the magpie first or keep it). Leave by 3:00.
- **Mars (Nagasaki):**
  - Open the umbrella at once.
  - When the girl comes, give her the umbrella and follow her into the shelter; take the spade.
  - Give her the crane note and she refolds it. Step outside: the crane grows; board it. Requires the Mars door held open.
- **Mercury (Orbit):**
  - At the Promontory, climb into the dish, wait for the bubble, then S, SW, IN with the lump and the axe (and the skink).
  - In orbit, kill the skink under the crescent moon.
  - The lump clamps you to the satellite at step 5.
  - Break the bubble with the axe at step 7 or 8 to be blown back through the door.
- **Cauldron:** break the coconut with the axe and pour the milk in. Put the honeyed hand in, then the skink and the garlic (from the trash pile behind the cottage). Leave and wait for the boom. Take the emerald.
- **Crypt (cemetery above the falls):**
  - Pry the lid with the spade. Inside: your own corpse.
  - Take the shroud and the red and green boots. Untie the bandage to get the silver coin.
  - Put the emerald in the green boot. Wear both boots and the shroud.
- **Styx (Alpha door):** wearing the shroud, board the dory and give the silver coin. Bring the cage with the lemming, the lantern, the walkie-talkie and the bag of crumbs.
- **Trinity:**
  - Wait in the shack until the jeep leaves.
  - The paperback holds a slip of cardboard. Its legend `RD=… BL=… ST=… WH=…` maps the four wire colours to POS/GND/INF/DET, **randomized per game**. **Do not use the walkthrough's "red".**
  - At the tower base the roadrunner drops the ruby; put it in the red boot. Both boots now let you streak across the desert.
  - In the jeep (N75), look at the radio dial (random 21–79), then tune the walkie-talkie to it and raise the antenna.
  - Ranch: hide in the closet from the snake. Open the cage, then open the door; the lemming runs into the snake's fangs (+3). Get the screwdriver from the workbench and the knife from the kitchen.
  - Reservoir: drop your things, climb the windmill, and fall when the landing gives way. With the lantern lit, dive for the binoculars.
  - At Baker, from behind the shed, look at the bunkers through the binoculars to spot the key. Tell the roadrunner to get the key.
  - At the tower box, unlock the padlock and **open the breaker, then close it on the very next move**. Opened for a second tick, or opened again, it means a scrub. The radio then names the line ("Ask the kid if he reconnected the *detonator/positive/ground/informer* line on X").
  - At Pittsburg (W100), drop the crumbs by the sleeping dog. When the roadrunner arrives and wakes it, go straight up the tower into the shack.
  - Turn on the light, unscrew the enclosure with the screwdriver, and wait.
  - **CUT <the colour matching the named type> WIRE WITH KNIFE while the watch reads 5:29:00–5:29:30.** Before 5:29 the cut does nothing useful and the police converge; the wrong wire, the axe or bare hands mean a scrub or capture.
  - Success runs ENDGAME, then the epilogue in London.
