# ZIL Conversion - Adaptation Notes

Generated from ZIL source files

## Conversion Summary

- **Locations**: 105
- **Items**: 143
- **NPCs**: 9
- **Puzzles**: 0
- **Manual review items**: 60

## Manual Review Required

The following items need manual review and possible implementation:

### 1. Conditional exit down in room

Conditional exit down in room: condition=WATER-LEVEL-F
  Review ZIL to determine destination and create puzzle if needed

### 2. Conditional exit down in room

Conditional exit down in room: condition=WATER-LEVEL-F
  Review ZIL to determine destination and create puzzle if needed

### 3. Conditional exit north -> conference_room

Conditional exit north -> conference_room: if CONFERENCE-DOOR
  LLM will interpret from raw_zil

### 4. Conditional exit south -> rec_area

Conditional exit south -> rec_area: if CONFERENCE-DOOR
  LLM will interpret from raw_zil

### 5. Conditional exit out -> rec_area

Conditional exit out -> rec_area: if CONFERENCE-DOOR
  LLM will interpret from raw_zil

### 6. Conditional exit north -> storage_west

Conditional exit north -> storage_west: if STORAGE-WEST-DOOR
  LLM will interpret from raw_zil

### 7. Conditional exit south -> mess_corridor

Conditional exit south -> mess_corridor: if STORAGE-WEST-DOOR
  LLM will interpret from raw_zil

### 8. Conditional exit out -> mess_corridor

Conditional exit out -> mess_corridor: if STORAGE-WEST-DOOR
  LLM will interpret from raw_zil

### 9. Conditional exit east in room

Conditional exit east in room: condition=LONG-HALL-F
  Review ZIL to determine destination and create puzzle if needed

### 10. Conditional exit south -> kitchen

Conditional exit south -> kitchen: if KITCHEN-DOOR
  LLM will interpret from raw_zil

### 11. Conditional exit in -> kitchen

Conditional exit in -> kitchen: if KITCHEN-DOOR
  LLM will interpret from raw_zil

### 12. Conditional exit west in room

Conditional exit west in room: condition=LONG-HALL-F
  Review ZIL to determine destination and create puzzle if needed

### 13. Conditional exit north in room

Conditional exit north in room: condition=LADDER-EXIT-F
  Review ZIL to determine destination and create puzzle if needed

### 14. Conditional exit south in room

Conditional exit south in room: condition=LADDER-EXIT-F
  Review ZIL to determine destination and create puzzle if needed

### 15. Conditional exit east -> reactor_elevator

Conditional exit east -> reactor_elevator: if REACTOR-ELEVATOR-DOOR
  LLM will interpret from raw_zil

### 16. Conditional exit in -> reactor_elevator

Conditional exit in -> reactor_elevator: if REACTOR-ELEVATOR-DOOR
  LLM will interpret from raw_zil

### 17. Conditional exit north in room

Conditional exit north in room: condition=ELEVATOR-ENTER-F
  Review ZIL to determine destination and create puzzle if needed

### 18. Conditional exit south in room

Conditional exit south in room: condition=ELEVATOR-ENTER-F
  Review ZIL to determine destination and create puzzle if needed

### 19. Conditional exit south in room

Conditional exit south in room: condition=ELEVATOR-EXIT-F
  Review ZIL to determine destination and create puzzle if needed

### 20. Conditional exit out in room

Conditional exit out in room: condition=ELEVATOR-EXIT-F
  Review ZIL to determine destination and create puzzle if needed

### 21. Conditional exit north in room

Conditional exit north in room: condition=ELEVATOR-EXIT-F
  Review ZIL to determine destination and create puzzle if needed

### 22. Conditional exit out in room

Conditional exit out in room: condition=ELEVATOR-EXIT-F
  Review ZIL to determine destination and create puzzle if needed

### 23. Conditional exit south in room

Conditional exit south in room: condition=OTHER-ELEVATOR-ENTER-F
  Review ZIL to determine destination and create puzzle if needed

### 24. Conditional exit north in room

Conditional exit north in room: condition=SHUTTLE-ENTER-F
  Review ZIL to determine destination and create puzzle if needed

### 25. Conditional exit south in room

Conditional exit south in room: condition=SHUTTLE-ENTER-F
  Review ZIL to determine destination and create puzzle if needed

### 26. Conditional exit east -> reactor_lobby

Conditional exit east -> reactor_lobby: if CORRIDOR-DOOR
  LLM will interpret from raw_zil

### 27. Conditional exit west -> escape_pod

Conditional exit west -> escape_pod: if POD-DOOR
  LLM will interpret from raw_zil

### 28. Conditional exit up -> gangway

Conditional exit up -> gangway: if GANGWAY-DOOR
  LLM will interpret from raw_zil

### 29. Conditional exit in -> escape_pod

Conditional exit in -> escape_pod: if POD-DOOR
  LLM will interpret from raw_zil

### 30. Conditional exit west -> deck_nine

Conditional exit west -> deck_nine: if CORRIDOR-DOOR
  LLM will interpret from raw_zil

### 31. Conditional exit down -> deck_nine

Conditional exit down -> deck_nine: if GANGWAY-DOOR
  LLM will interpret from raw_zil

### 32. Conditional exit east in room

Conditional exit east in room: condition=POD-EXIT-F
  Review ZIL to determine destination and create puzzle if needed

### 33. Conditional exit up in room

Conditional exit up in room: condition=POD-EXIT-F
  Review ZIL to determine destination and create puzzle if needed

### 34. Conditional exit out in room

Conditional exit out in room: condition=POD-EXIT-F
  Review ZIL to determine destination and create puzzle if needed

### 35. Conditional exit north in room

Conditional exit north in room: condition=SHUTTLE-EXIT-F
  Review ZIL to determine destination and create puzzle if needed

### 36. Conditional exit west -> shuttle_car_alfie

Conditional exit west -> shuttle_car_alfie: if SHUTTLE-DOOR
  LLM will interpret from raw_zil

### 37. Conditional exit east -> shuttle_car_alfie

Conditional exit east -> shuttle_car_alfie: if SHUTTLE-DOOR
  LLM will interpret from raw_zil

### 38. Conditional exit south in room

Conditional exit south in room: condition=SHUTTLE-EXIT-F
  Review ZIL to determine destination and create puzzle if needed

### 39. Conditional exit west -> shuttle_car_betty

Conditional exit west -> shuttle_car_betty: if SHUTTLE-DOOR
  LLM will interpret from raw_zil

### 40. Conditional exit east -> shuttle_car_betty

Conditional exit east -> shuttle_car_betty: if SHUTTLE-DOOR
  LLM will interpret from raw_zil

### 41. Conditional exit north in room

Conditional exit north in room: condition=SHUTTLE-ENTER-F
  Review ZIL to determine destination and create puzzle if needed

### 42. Conditional exit south in room

Conditional exit south in room: condition=SHUTTLE-ENTER-F
  Review ZIL to determine destination and create puzzle if needed

### 43. Conditional exit south -> cryo_elevator

Conditional exit south -> cryo_elevator: if CRYO-ELEVATOR-DOOR
  LLM will interpret from raw_zil

### 44. Conditional exit north in room

Conditional exit north in room: condition=CRYO-EXIT-F
  Review ZIL to determine destination and create puzzle if needed

### 45. Conditional exit ne -> radiation_lock_west

Conditional exit ne -> radiation_lock_west: if RAD-DOOR-WEST
  LLM will interpret from raw_zil

### 46. Conditional exit se -> bio_lock_west

Conditional exit se -> bio_lock_west: if BIO-DOOR-WEST
  LLM will interpret from raw_zil

### 47. Conditional exit west -> main_lab

Conditional exit west -> main_lab: if BIO-DOOR-WEST
  LLM will interpret from raw_zil

### 48. Conditional exit east -> bio_lab

Conditional exit east -> bio_lab: if BIO-DOOR-EAST
  LLM will interpret from raw_zil

### 49. Conditional exit west -> main_lab

Conditional exit west -> main_lab: if RAD-DOOR-WEST
  LLM will interpret from raw_zil

### 50. Conditional exit east -> radiation_lab

Conditional exit east -> radiation_lab: if RAD-DOOR-EAST
  LLM will interpret from raw_zil

### 51. Conditional exit east -> lab_office

Conditional exit east -> lab_office: if OFFICE-DOOR
  LLM will interpret from raw_zil

### 52. Conditional exit west -> bio_lock_east

Conditional exit west -> bio_lock_east: if BIO-DOOR-EAST
  LLM will interpret from raw_zil

### 53. Conditional exit west -> radiation_lock_east

Conditional exit west -> radiation_lock_east: if RAD-DOOR-EAST
  LLM will interpret from raw_zil

### 54. Conditional exit west -> bio_lab

Conditional exit west -> bio_lab: if OFFICE-DOOR
  LLM will interpret from raw_zil

### 55. Conditional exit south -> strip_near_station

Conditional exit south -> strip_near_station: if NO-MICROBE
  LLM will interpret from raw_zil

### 56. Conditional exit south -> middle_of_strip

Conditional exit south -> middle_of_strip: if NO-MICROBE
  LLM will interpret from raw_zil

### 57. Conditional exit east in room

Conditional exit east in room: condition=RELAY-EXIT-F
  Review ZIL to determine destination and create puzzle if needed

### 58. Object pseudo_object has action routine

Object pseudo_object has action routine: GO
  WARNING: Routine code not found in ZIL files

### 59. Object safety_web has action routine

Object safety_web has action routine: SAFETY-WEB-F
  WARNING: Routine code not found in ZIL files

### 60. Object bed has action routine

Object bed has action routine: BED-F
  WARNING: Routine code not found in ZIL files

## Additional Conversion Notes

# ZIL Conversion - Adaptation Notes

## Manual Review Required

The following items need manual review and possible implementation:

1. Conditional exit in balcony: down -> condition=WATER-LEVEL-F
  Needs implementation

2. Conditional exit in winding_stair: down -> condition=WATER-LEVEL-F
  Needs implementation

3. Conditional exit in rec_area: north -> condition=CONFERENCE-DOOR
  Needs implementation

4. Conditional exit in conference_room: south -> condition=CONFERENCE-DOOR
  Needs implementation

5. Conditional exit in conference_room: out -> condition=CONFERENCE-DOOR
  Needs implementation

6. Conditional exit in mess_corridor: north -> condition=STORAGE-WEST-DOOR
  Needs implementation

7. Conditional exit in storage_west: south -> condition=STORAGE-WEST-DOOR
  Needs implementation

8. Conditional exit in storage_west: out -> condition=STORAGE-WEST-DOOR
  Needs implementation

9. Conditional exit in dorm_corridor: east -> condition=LONG-HALL-F
  Needs implementation

10. Conditional exit in mess_hall: south -> condition=KITCHEN-DOOR
  Needs implementation

11. Conditional exit in mess_hall: in -> condition=KITCHEN-DOOR
  Needs implementation

12. Conditional exit in corridor_junction: west -> condition=LONG-HALL-F
  Needs implementation

13. Conditional exit in admin_corridor: north -> condition=LADDER-EXIT-F
  Needs implementation

14. Conditional exit in admin_corridor_n: south -> condition=LADDER-EXIT-F
  Needs implementation

15. Conditional exit in reactor_control: east -> condition=REACTOR-ELEVATOR-DOOR
  Needs implementation

16. Conditional exit in reactor_control: in -> condition=REACTOR-ELEVATOR-DOOR
  Needs implementation

17. Conditional exit in elevator_lobby: north -> condition=ELEVATOR-ENTER-F
  Needs implementation

18. Conditional exit in elevator_lobby: south -> condition=ELEVATOR-ENTER-F
  Needs implementation

19. Conditional exit in upper_elevator: south -> condition=ELEVATOR-EXIT-F
  Needs implementation

20. Conditional exit in upper_elevator: out -> condition=ELEVATOR-EXIT-F
  Needs implementation

21. Conditional exit in lower_elevator: north -> condition=ELEVATOR-EXIT-F
  Needs implementation

22. Conditional exit in lower_elevator: out -> condition=ELEVATOR-EXIT-F
  Needs implementation

23. Conditional exit in waiting_area: south -> condition=OTHER-ELEVATOR-ENTER-F
  Needs implementation

24. Conditional exit in kalamontee_platform: north -> condition=SHUTTLE-ENTER-F
  Needs implementation

25. Conditional exit in kalamontee_platform: south -> condition=SHUTTLE-ENTER-F
  Needs implementation

26. Conditional exit in deck_nine: east -> condition=CORRIDOR-DOOR
  Needs implementation

27. Conditional exit in deck_nine: west -> condition=POD-DOOR
  Needs implementation

28. Conditional exit in deck_nine: up -> condition=GANGWAY-DOOR
  Needs implementation

29. Conditional exit in deck_nine: in -> condition=POD-DOOR
  Needs implementation

30. Conditional exit in reactor_lobby: west -> condition=CORRIDOR-DOOR
  Needs implementation

31. Conditional exit in gangway: down -> condition=GANGWAY-DOOR
  Needs implementation

32. Conditional exit in escape_pod: east -> condition=POD-EXIT-F
  Needs implementation

33. Conditional exit in escape_pod: up -> condition=POD-EXIT-F
  Needs implementation

34. Conditional exit in escape_pod: out -> condition=POD-EXIT-F
  Needs implementation

35. Conditional exit in shuttle_car_alfie: north -> condition=SHUTTLE-EXIT-F
  Needs implementation

36. Conditional exit in alfie_control_east: west -> condition=SHUTTLE-DOOR
  Needs implementation

37. Conditional exit in alfie_control_west: east -> condition=SHUTTLE-DOOR
  Needs implementation

38. Conditional exit in shuttle_car_betty: south -> condition=SHUTTLE-EXIT-F
  Needs implementation

39. Conditional exit in betty_control_east: west -> condition=SHUTTLE-DOOR
  Needs implementation

40. Conditional exit in betty_control_west: east -> condition=SHUTTLE-DOOR
  Needs implementation

41. Conditional exit in lawanda_platform: north -> condition=SHUTTLE-ENTER-F
  Needs implementation

42. Conditional exit in lawanda_platform: south -> condition=SHUTTLE-ENTER-F
  Needs implementation

43. Conditional exit in projcon_office: south -> condition=CRYO-ELEVATOR-DOOR
  Needs implementation

44. Conditional exit in cryo_elevator: north -> condition=CRYO-EXIT-F
  Needs implementation

45. Conditional exit in main_lab: ne -> condition=RAD-DOOR-WEST
  Needs implementation

46. Conditional exit in main_lab: se -> condition=BIO-DOOR-WEST
  Needs implementation

47. Conditional exit in bio_lock_west: west -> condition=BIO-DOOR-WEST
  Needs implementation

48. Conditional exit in bio_lock_east: east -> condition=BIO-DOOR-EAST
  Needs implementation

49. Conditional exit in radiation_lock_west: west -> condition=RAD-DOOR-WEST
  Needs implementation

50. Conditional exit in radiation_lock_east: east -> condition=RAD-DOOR-EAST
  Needs implementation

51. Conditional exit in bio_lab: east -> condition=OFFICE-DOOR
  Needs implementation

52. Conditional exit in bio_lab: west -> condition=BIO-DOOR-EAST
  Needs implementation

53. Conditional exit in radiation_lab: west -> condition=RAD-DOOR-EAST
  Needs implementation

54. Conditional exit in lab_office: west -> condition=OFFICE-DOOR
  Needs implementation

55. Conditional exit in middle_of_strip: south -> condition=NO-MICROBE
  Needs implementation

56. Conditional exit in strip_near_relay: south -> condition=NO-MICROBE
  Needs implementation

57. Conditional exit in strip_near_relay: east -> condition=RELAY-EXIT-F
  Needs implementation

58. Object key is a weapon - add damage/attack stats if needed

59. Object key is a weapon - add damage/attack stats if needed



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

