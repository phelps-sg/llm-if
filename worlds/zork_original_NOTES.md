# ZIL Conversion - Adaptation Notes

Generated from ZIL source files

## Conversion Summary

- **Locations**: 109
- **Items**: 130
- **NPCs**: 7
- **Puzzles**: 0
- **Manual review items**: 42

## Manual Review Required

The following items need manual review and possible implementation:

### 1. Conditional exit sw -> stone_barrow

Conditional exit sw -> stone_barrow: if WON-FLAG
  LLM will interpret from raw_zil

### 2. Conditional exit in -> stone_barrow

Conditional exit in -> stone_barrow: if WON-FLAG
  LLM will interpret from raw_zil

### 3. Conditional exit west -> kitchen

Conditional exit west -> kitchen: if KITCHEN-WINDOW
  LLM will interpret from raw_zil

### 4. Conditional exit in -> kitchen

Conditional exit in -> kitchen: if KITCHEN-WINDOW
  LLM will interpret from raw_zil

### 5. Conditional exit down in room

Conditional exit down in room: condition=GRATING-EXIT
  Review ZIL to determine destination and create puzzle if needed

### 6. Conditional exit east -> east_of_house

Conditional exit east -> east_of_house: if KITCHEN-WINDOW
  LLM will interpret from raw_zil

### 7. Conditional exit down -> studio

Conditional exit down -> studio: if FALSE-FLAG
  LLM will interpret from raw_zil

### 8. Conditional exit out -> east_of_house

Conditional exit out -> east_of_house: if KITCHEN-WINDOW
  LLM will interpret from raw_zil

### 9. Conditional exit west -> strange_passage

Conditional exit west -> strange_passage: if MAGIC-FLAG
  LLM will interpret from raw_zil

### 10. Conditional exit down in room

Conditional exit down in room: condition=TRAP-DOOR-EXIT
  Review ZIL to determine destination and create puzzle if needed

### 11. Conditional exit up -> living_room

Conditional exit up -> living_room: if TRAP-DOOR
  LLM will interpret from raw_zil

### 12. Conditional exit east -> ew_passage

Conditional exit east -> ew_passage: if TROLL-FLAG
  LLM will interpret from raw_zil

### 13. Conditional exit west -> maze_1

Conditional exit west -> maze_1: if TROLL-FLAG
  LLM will interpret from raw_zil

### 14. Conditional exit up in room

Conditional exit up in room: condition=UP-CHIMNEY-FUNCTION
  Review ZIL to determine destination and create puzzle if needed

### 15. Conditional exit down in room

Conditional exit down in room: condition=MAZE-DIODES
  Review ZIL to determine destination and create puzzle if needed

### 16. Conditional exit down in room

Conditional exit down in room: condition=MAZE-DIODES
  Review ZIL to determine destination and create puzzle if needed

### 17. Conditional exit down in room

Conditional exit down in room: condition=MAZE-DIODES
  Review ZIL to determine destination and create puzzle if needed

### 18. Conditional exit up -> grating_clearing

Conditional exit up -> grating_clearing: if GRATE
  LLM will interpret from raw_zil

### 19. Conditional exit down in room

Conditional exit down in room: condition=MAZE-DIODES
  Review ZIL to determine destination and create puzzle if needed

### 20. Conditional exit east -> strange_passage

Conditional exit east -> strange_passage: if MAGIC-FLAG
  LLM will interpret from raw_zil

### 21. Conditional exit up -> treasure_room

Conditional exit up -> treasure_room: if CYCLOPS-FLAG
  LLM will interpret from raw_zil

### 22. Conditional exit north -> reservoir

Conditional exit north -> reservoir: if LOW-TIDE
  LLM will interpret from raw_zil

### 23. Conditional exit south -> reservoir

Conditional exit south -> reservoir: if LOW-TIDE
  LLM will interpret from raw_zil

### 24. Room loud_room has action routine

Room loud_room has action routine: LOUD-ROOM-FCN
  WARNING: Routine code not found in ZIL files

### 25. Conditional exit south -> land_of_living_dead

Conditional exit south -> land_of_living_dead: if LLD-FLAG
  LLM will interpret from raw_zil

### 26. Conditional exit in -> land_of_living_dead

Conditional exit in -> land_of_living_dead: if LLD-FLAG
  LLM will interpret from raw_zil

### 27. Conditional exit down -> torch_room

Conditional exit down -> torch_room: if DOME-FLAG
  LLM will interpret from raw_zil

### 28. Conditional exit down -> tiny_cave

Conditional exit down -> tiny_cave: if COFFIN-CURE
  LLM will interpret from raw_zil

### 29. Conditional exit south -> white_cliffs_south

Conditional exit south -> white_cliffs_south: if DEFLATE
  LLM will interpret from raw_zil

### 30. Conditional exit west -> damp_cave

Conditional exit west -> damp_cave: if DEFLATE
  LLM will interpret from raw_zil

### 31. Conditional exit north -> white_cliffs_north

Conditional exit north -> white_cliffs_north: if DEFLATE
  LLM will interpret from raw_zil

### 32. Conditional exit west -> on_rainbow

Conditional exit west -> on_rainbow: if RAINBOW-FLAG
  LLM will interpret from raw_zil

### 33. Conditional exit up -> on_rainbow

Conditional exit up -> on_rainbow: if RAINBOW-FLAG
  LLM will interpret from raw_zil

### 34. Conditional exit east -> on_rainbow

Conditional exit east -> on_rainbow: if RAINBOW-FLAG
  LLM will interpret from raw_zil

### 35. Conditional exit ne -> on_rainbow

Conditional exit ne -> on_rainbow: if RAINBOW-FLAG
  LLM will interpret from raw_zil

### 36. Conditional exit up -> on_rainbow

Conditional exit up -> on_rainbow: if RAINBOW-FLAG
  LLM will interpret from raw_zil

### 37. Conditional exit west -> lower_shaft

Conditional exit west -> lower_shaft: if EMPTY-HANDED
  LLM will interpret from raw_zil

### 38. Conditional exit east -> timber_room

Conditional exit east -> timber_room: if EMPTY-HANDED
  LLM will interpret from raw_zil

### 39. Conditional exit out -> timber_room

Conditional exit out -> timber_room: if EMPTY-HANDED
  LLM will interpret from raw_zil

### 40. Object global_water has action routine

Object global_water has action routine: WATER-F
  WARNING: Routine code not found in ZIL files

### 41. Object water has action routine

Object water has action routine: WATER-F
  WARNING: Routine code not found in ZIL files

### 42. NPC thief has action routine

NPC thief has action routine: ROBBER-FUNCTION
  WARNING: Routine code not found in ZIL files

## Additional Conversion Notes

# ZIL Conversion - Adaptation Notes

## Manual Review Required

The following items need manual review and possible implementation:

1. Conditional exit in west_of_house: sw -> condition=WON-FLAG
  Needs implementation

2. Conditional exit in west_of_house: in -> condition=WON-FLAG
  Needs implementation

3. Conditional exit in east_of_house: west -> condition=KITCHEN-WINDOW
  Needs implementation

4. Conditional exit in east_of_house: in -> condition=KITCHEN-WINDOW
  Needs implementation

5. Conditional exit in grating_clearing: down -> condition=GRATING-EXIT
  Needs implementation

6. Conditional exit in kitchen: east -> condition=KITCHEN-WINDOW
  Needs implementation

7. Conditional exit in kitchen: down -> condition=FALSE-FLAG
  Needs implementation

8. Conditional exit in kitchen: out -> condition=KITCHEN-WINDOW
  Needs implementation

9. Conditional exit in living_room: west -> condition=MAGIC-FLAG
  Needs implementation

10. Conditional exit in living_room: down -> condition=TRAP-DOOR-EXIT
  Needs implementation

11. Conditional exit in cellar: up -> condition=TRAP-DOOR
  Needs implementation

12. Conditional exit in troll_room: east -> condition=TROLL-FLAG
  Needs implementation

13. Conditional exit in troll_room: west -> condition=TROLL-FLAG
  Needs implementation

14. Conditional exit in studio: up -> condition=UP-CHIMNEY-FUNCTION
  Needs implementation

15. Conditional exit in maze_2: down -> condition=MAZE-DIODES
  Needs implementation

16. Conditional exit in maze_7: down -> condition=MAZE-DIODES
  Needs implementation

17. Conditional exit in maze_9: down -> condition=MAZE-DIODES
  Needs implementation

18. Conditional exit in grating_room: up -> condition=GRATE
  Needs implementation

19. Conditional exit in maze_12: down -> condition=MAZE-DIODES
  Needs implementation

20. Conditional exit in cyclops_room: east -> condition=MAGIC-FLAG
  Needs implementation

21. Conditional exit in cyclops_room: up -> condition=CYCLOPS-FLAG
  Needs implementation

22. Conditional exit in reservoir_south: north -> condition=LOW-TIDE
  Needs implementation

23. Conditional exit in reservoir_north: south -> condition=LOW-TIDE
  Needs implementation

24. Conditional exit in entrance_to_hades: south -> condition=LLD-FLAG
  Needs implementation

25. Conditional exit in entrance_to_hades: in -> condition=LLD-FLAG
  Needs implementation

26. Conditional exit in dome_room: down -> condition=DOME-FLAG
  Needs implementation

27. Conditional exit in south_temple: down -> condition=COFFIN-CURE
  Needs implementation

28. Conditional exit in white_cliffs_north: south -> condition=DEFLATE
  Needs implementation

29. Conditional exit in white_cliffs_north: west -> condition=DEFLATE
  Needs implementation

30. Conditional exit in white_cliffs_south: north -> condition=DEFLATE
  Needs implementation

31. Conditional exit in aragain_falls: west -> condition=RAINBOW-FLAG
  Needs implementation

32. Conditional exit in aragain_falls: up -> condition=RAINBOW-FLAG
  Needs implementation

33. Conditional exit in end_of_rainbow: east -> condition=RAINBOW-FLAG
  Needs implementation

34. Conditional exit in end_of_rainbow: ne -> condition=RAINBOW-FLAG
  Needs implementation

35. Conditional exit in end_of_rainbow: up -> condition=RAINBOW-FLAG
  Needs implementation

36. Conditional exit in timber_room: west -> condition=EMPTY-HANDED
  Needs implementation

37. Conditional exit in lower_shaft: east -> condition=EMPTY-HANDED
  Needs implementation

38. Conditional exit in lower_shaft: out -> condition=EMPTY-HANDED
  Needs implementation

39. Object axe is a weapon - add damage/attack stats if needed

40. Object sceptre is a weapon - add damage/attack stats if needed

41. Object pump is a weapon - add damage/attack stats if needed

42. Object knife is a weapon - add damage/attack stats if needed

43. Object rusty_knife is a weapon - add damage/attack stats if needed

44. Object screwdriver is a weapon - add damage/attack stats if needed

45. Object keys is a weapon - add damage/attack stats if needed

46. Object shovel is a weapon - add damage/attack stats if needed

47. Object stiletto is a weapon - add damage/attack stats if needed

48. Object sword is a weapon - add damage/attack stats if needed

49. Object putty is a weapon - add damage/attack stats if needed

50. Object wrench is a weapon - add damage/attack stats if needed

51. Object intnum is a weapon - add damage/attack stats if needed

52. Object hands is a weapon - add damage/attack stats if needed

53. Object axe is a weapon - add damage/attack stats if needed

54. Object sceptre is a weapon - add damage/attack stats if needed

55. Object pump is a weapon - add damage/attack stats if needed

56. Object knife is a weapon - add damage/attack stats if needed

57. Object rusty_knife is a weapon - add damage/attack stats if needed

58. Object screwdriver is a weapon - add damage/attack stats if needed

59. Object keys is a weapon - add damage/attack stats if needed

60. Object shovel is a weapon - add damage/attack stats if needed

61. Object stiletto is a weapon - add damage/attack stats if needed

62. Object sword is a weapon - add damage/attack stats if needed

63. Object putty is a weapon - add damage/attack stats if needed

64. Object wrench is a weapon - add damage/attack stats if needed

65. Object intnum is a weapon - add damage/attack stats if needed

66. Object hands is a weapon - add damage/attack stats if needed

67. NPC thief needs behavior implementation
  Review ZIL routine ROBBER-FUNCTION for dialogue and AI logic



## Next Steps

1. **Review** this file and prioritize adaptations
2. **Test** the converted world in the LLM-IF engine
3. **Implement** custom behaviors for NPCs with action routines
4. **Add** puzzle logic for conditional exits
5. **Polish** descriptions and attributes based on playtesting
6. **Validate** that the LLM DM correctly interprets ZIL attributes

## Reference

### ZIL Flags Preserved

The converter preserves ZIL flags as `zil_flags` attributes.
The LLM DM can interpret these for game behavior.

Common flags:
- `takebit` - Item can be taken
- `contbit` - Container
- `doorbit` - Door
- `lockedbit` - Locked
- `lightbit` - Light source
- `actorbit` - NPC
- `villainbit` - Hostile NPC

