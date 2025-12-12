# ZIL Conversion - Adaptation Notes

Generated from ZIL source files

## Conversion Summary

- **Locations**: 109
- **Items**: 128
- **NPCs**: 7
- **Puzzles**: 0
- **Manual review items**: 136

## Manual Review Required

The following items need manual review and possible implementation:

### 1. Room west_of_house has action routine

Room west_of_house has action routine: WEST-HOUSE
  Review ZIL routine for special room behavior

### 2. Room stone_barrow has action routine

Room stone_barrow has action routine: STONE-BARROW-FCN
  Review ZIL routine for special room behavior

### 3. Room east_of_house has action routine

Room east_of_house has action routine: EAST-HOUSE
  Review ZIL routine for special room behavior

### 4. Room forest_1 has action routine

Room forest_1 has action routine: FOREST-ROOM
  Review ZIL routine for special room behavior

### 5. Room forest_2 has action routine

Room forest_2 has action routine: FOREST-ROOM
  Review ZIL routine for special room behavior

### 6. Room forest_3 has action routine

Room forest_3 has action routine: FOREST-ROOM
  Review ZIL routine for special room behavior

### 7. Room path has action routine

Room path has action routine: FOREST-ROOM
  Review ZIL routine for special room behavior

### 8. Room up_a_tree has action routine

Room up_a_tree has action routine: TREE-ROOM
  Review ZIL routine for special room behavior

### 9. Conditional exit down in room

Conditional exit down in room: condition=GRATING-EXIT
  Review ZIL to determine destination and create puzzle if needed

### 10. Room grating_clearing has action routine

Room grating_clearing has action routine: CLEARING-FCN
  Review ZIL routine for special room behavior

### 11. Room clearing has action routine

Room clearing has action routine: FOREST-ROOM
  Review ZIL routine for special room behavior

### 12. Room kitchen has action routine

Room kitchen has action routine: KITCHEN-FCN
  Review ZIL routine for special room behavior

### 13. Conditional exit down in room

Conditional exit down in room: condition=TRAP-DOOR-EXIT
  Review ZIL to determine destination and create puzzle if needed

### 14. Room living_room has action routine

Room living_room has action routine: LIVING-ROOM-FCN
  Review ZIL routine for special room behavior

### 15. Room cellar has action routine

Room cellar has action routine: CELLAR-FCN
  Review ZIL routine for special room behavior

### 16. Room troll_room has action routine

Room troll_room has action routine: TROLL-ROOM-F
  Review ZIL routine for special room behavior

### 17. Conditional exit up in room

Conditional exit up in room: condition=UP-CHIMNEY-FUNCTION
  Review ZIL to determine destination and create puzzle if needed

### 18. Conditional exit down in room

Conditional exit down in room: condition=MAZE-DIODES
  Review ZIL to determine destination and create puzzle if needed

### 19. Conditional exit down in room

Conditional exit down in room: condition=MAZE-DIODES
  Review ZIL to determine destination and create puzzle if needed

### 20. Conditional exit down in room

Conditional exit down in room: condition=MAZE-DIODES
  Review ZIL to determine destination and create puzzle if needed

### 21. Room grating_room has action routine

Room grating_room has action routine: MAZE-11-FCN
  Review ZIL routine for special room behavior

### 22. Conditional exit down in room

Conditional exit down in room: condition=MAZE-DIODES
  Review ZIL to determine destination and create puzzle if needed

### 23. Room cyclops_room has action routine

Room cyclops_room has action routine: CYCLOPS-ROOM-FCN
  Review ZIL routine for special room behavior

### 24. Room reservoir_south has action routine

Room reservoir_south has action routine: RESERVOIR-SOUTH-FCN
  Review ZIL routine for special room behavior

### 25. Room reservoir has action routine

Room reservoir has action routine: RESERVOIR-FCN
  Review ZIL routine for special room behavior

### 26. Room reservoir_north has action routine

Room reservoir_north has action routine: RESERVOIR-NORTH-FCN
  Review ZIL routine for special room behavior

### 27. Room mirror_room_1 has action routine

Room mirror_room_1 has action routine: MIRROR-ROOM
  Review ZIL routine for special room behavior

### 28. Room mirror_room_2 has action routine

Room mirror_room_2 has action routine: MIRROR-ROOM
  Review ZIL routine for special room behavior

### 29. Room tiny_cave has action routine

Room tiny_cave has action routine: CAVE2-ROOM
  Review ZIL routine for special room behavior

### 30. Room deep_canyon has action routine

Room deep_canyon has action routine: DEEP-CANYON-F
  Review ZIL routine for special room behavior

### 31. Room loud_room has action routine

Room loud_room has action routine: LOUD-ROOM-FCN
  Review ZIL routine for special room behavior

### 32. Room entrance_to_hades has action routine

Room entrance_to_hades has action routine: LLD-ROOM
  Review ZIL routine for special room behavior

### 33. Room dome_room has action routine

Room dome_room has action routine: DOME-ROOM-FCN
  Review ZIL routine for special room behavior

### 34. Room torch_room has action routine

Room torch_room has action routine: TORCH-ROOM-FCN
  Review ZIL routine for special room behavior

### 35. Room south_temple has action routine

Room south_temple has action routine: SOUTH-TEMPLE-FCN
  Review ZIL routine for special room behavior

### 36. Room dam_room has action routine

Room dam_room has action routine: DAM-ROOM-FCN
  Review ZIL routine for special room behavior

### 37. Room white_cliffs_north has action routine

Room white_cliffs_north has action routine: WHITE-CLIFFS-FUNCTION
  Review ZIL routine for special room behavior

### 38. Room white_cliffs_south has action routine

Room white_cliffs_south has action routine: WHITE-CLIFFS-FUNCTION
  Review ZIL routine for special room behavior

### 39. Room river_4 has action routine

Room river_4 has action routine: RIVR4-ROOM
  Review ZIL routine for special room behavior

### 40. Room aragain_falls has action routine

Room aragain_falls has action routine: FALLS-ROOM
  Review ZIL routine for special room behavior

### 41. Room canyon_view has action routine

Room canyon_view has action routine: CANYON-VIEW-F
  Review ZIL routine for special room behavior

### 42. Room bat_room has action routine

Room bat_room has action routine: BATS-ROOM
  Review ZIL routine for special room behavior

### 43. Room gas_room has action routine

Room gas_room has action routine: BOOM-ROOM
  Review ZIL routine for special room behavior

### 44. Room timber_room has action routine

Room timber_room has action routine: NO-OBJS
  Review ZIL routine for special room behavior

### 45. Room lower_shaft has action routine

Room lower_shaft has action routine: NO-OBJS
  Review ZIL routine for special room behavior

### 46. Room machine_room has action routine

Room machine_room has action routine: MACHINE-ROOM-FCN
  Review ZIL routine for special room behavior

### 47. Object board has action routine

Object board has action routine: BOARD-F
  Review ZIL routine for special object behavior

### 48. Object teeth has action routine

Object teeth has action routine: TEETH-F
  Review ZIL routine for special object behavior

### 49. Object granite_wall has action routine

Object granite_wall has action routine: GRANITE-WALL-F
  Review ZIL routine for special object behavior

### 50. Object songbird has action routine

Object songbird has action routine: SONGBIRD-F
  Review ZIL routine for special object behavior

### 51. Object white_house has action routine

Object white_house has action routine: WHITE-HOUSE-F
  Review ZIL routine for special object behavior

### 52. Object forest has action routine

Object forest has action routine: FOREST-F
  Review ZIL routine for special object behavior

### 53. Object mountain_range has action routine

Object mountain_range has action routine: MOUNTAIN-RANGE-F
  Review ZIL routine for special object behavior

### 54. Object global_water has action routine

Object global_water has action routine: WATER-F
  Review ZIL routine for special object behavior

### 55. Object water has action routine

Object water has action routine: WATER-F
  Review ZIL routine for special object behavior

### 56. Object chimney has action routine

Object chimney has action routine: CHIMNEY-F
  Review ZIL routine for special object behavior

### 57. Object lowered_basket has action routine

Object lowered_basket has action routine: BASKET-F
  Review ZIL routine for special object behavior

### 58. Object raised_basket has action routine

Object raised_basket has action routine: BASKET-F
  Review ZIL routine for special object behavior

### 59. Object bell has action routine

Object bell has action routine: BELL-F
  Review ZIL routine for special object behavior

### 60. Object hot_bell has action routine

Object hot_bell has action routine: HOT-BELL-F
  Review ZIL routine for special object behavior

### 61. Object axe has action routine

Object axe has action routine: AXE-F
  Review ZIL routine for special object behavior

### 62. Object bolt has action routine

Object bolt has action routine: BOLT-F
  Review ZIL routine for special object behavior

### 63. Object bubble has action routine

Object bubble has action routine: BUBBLE-F
  Review ZIL routine for special object behavior

### 64. Object book has action routine

Object book has action routine: BLACK-BOOK
  Review ZIL routine for special object behavior

### 65. Object sceptre has action routine

Object sceptre has action routine: SCEPTRE-FUNCTION
  Review ZIL routine for special object behavior

### 66. Object sandwich_bag has action routine

Object sandwich_bag has action routine: SANDWICH-BAG-FCN
  Review ZIL routine for special object behavior

### 67. Object tool_chest has action routine

Object tool_chest has action routine: TOOL-CHEST-FCN
  Review ZIL routine for special object behavior

### 68. Object yellow_button has action routine

Object yellow_button has action routine: BUTTON-F
  Review ZIL routine for special object behavior

### 69. Object brown_button has action routine

Object brown_button has action routine: BUTTON-F
  Review ZIL routine for special object behavior

### 70. Object red_button has action routine

Object red_button has action routine: BUTTON-F
  Review ZIL routine for special object behavior

### 71. Object blue_button has action routine

Object blue_button has action routine: BUTTON-F
  Review ZIL routine for special object behavior

### 72. Object trophy_case has action routine

Object trophy_case has action routine: TROPHY-CASE-FCN
  Review ZIL routine for special object behavior

### 73. Object rug has action routine

Object rug has action routine: RUG-FCN
  Review ZIL routine for special object behavior

### 74. Object chalice has action routine

Object chalice has action routine: CHALICE-FCN
  Review ZIL routine for special object behavior

### 75. Object garlic has action routine

Object garlic has action routine: GARLIC-F
  Review ZIL routine for special object behavior

### 76. Object dam has action routine

Object dam has action routine: DAM-FUNCTION
  Review ZIL routine for special object behavior

### 77. Object trap_door has action routine

Object trap_door has action routine: TRAP-DOOR-FCN
  Review ZIL routine for special object behavior

### 78. Object boarded_window has action routine

Object boarded_window has action routine: BOARDED-WINDOW-FCN
  Review ZIL routine for special object behavior

### 79. Object front_door has action routine

Object front_door has action routine: FRONT-DOOR-FCN
  Review ZIL routine for special object behavior

### 80. Object barrow_door has action routine

Object barrow_door has action routine: BARROW-DOOR-FCN
  Review ZIL routine for special object behavior

### 81. Object barrow has action routine

Object barrow has action routine: BARROW-FCN
  Review ZIL routine for special object behavior

### 82. Object bottle has action routine

Object bottle has action routine: BOTTLE-FUNCTION
  Review ZIL routine for special object behavior

### 83. Object crack has action routine

Object crack has action routine: CRACK-FCN
  Review ZIL routine for special object behavior

### 84. Object grate has action routine

Object grate has action routine: GRATE-FUNCTION
  Review ZIL routine for special object behavior

### 85. Object knife has action routine

Object knife has action routine: KNIFE-F
  Review ZIL routine for special object behavior

### 86. Object bones has action routine

Object bones has action routine: SKELETON
  Review ZIL routine for special object behavior

### 87. Object bag_of_coins has action routine

Object bag_of_coins has action routine: BAG-OF-COINS-F
  Review ZIL routine for special object behavior

### 88. Object lamp has action routine

Object lamp has action routine: LANTERN
  Review ZIL routine for special object behavior

### 89. Object leak has action routine

Object leak has action routine: LEAK-FUNCTION
  Review ZIL routine for special object behavior

### 90. Object machine has action routine

Object machine has action routine: MACHINE-F
  Review ZIL routine for special object behavior

### 91. Object inflated_boat has action routine

Object inflated_boat has action routine: RBOAT-FUNCTION
  Review ZIL routine for special object behavior

### 92. Object mailbox has action routine

Object mailbox has action routine: MAILBOX-F
  Review ZIL routine for special object behavior

### 93. Object match has action routine

Object match has action routine: MATCH-FUNCTION
  Review ZIL routine for special object behavior

### 94. Object mirror_2 has action routine

Object mirror_2 has action routine: MIRROR-MIRROR
  Review ZIL routine for special object behavior

### 95. Object mirror_1 has action routine

Object mirror_1 has action routine: MIRROR-MIRROR
  Review ZIL routine for special object behavior

### 96. Object painting has action routine

Object painting has action routine: PAINTING-FCN
  Review ZIL routine for special object behavior

### 97. Object candles has action routine

Object candles has action routine: CANDLES-FCN
  Review ZIL routine for special object behavior

### 98. Object gunk has action routine

Object gunk has action routine: GUNK-FUNCTION
  Review ZIL routine for special object behavior

### 99. Object bodies has action routine

Object bodies has action routine: BODY-FUNCTION
  Review ZIL routine for special object behavior

### 100. Object leaves has action routine

Object leaves has action routine: LEAF-PILE
  Review ZIL routine for special object behavior

### 101. Object punctured_boat has action routine

Object punctured_boat has action routine: DBOAT-FUNCTION
  Review ZIL routine for special object behavior

### 102. Object inflatable_boat has action routine

Object inflatable_boat has action routine: IBOAT-FUNCTION
  Review ZIL routine for special object behavior

### 103. Object rainbow has action routine

Object rainbow has action routine: RAINBOW-FCN
  Review ZIL routine for special object behavior

### 104. Object river has action routine

Object river has action routine: RIVER-FUNCTION
  Review ZIL routine for special object behavior

### 105. Object buoy has action routine

Object buoy has action routine: TREASURE-INSIDE
  Review ZIL routine for special object behavior

### 106. Object rope has action routine

Object rope has action routine: ROPE-FUNCTION
  Review ZIL routine for special object behavior

### 107. Object rusty_knife has action routine

Object rusty_knife has action routine: RUSTY-KNIFE-FCN
  Review ZIL routine for special object behavior

### 108. Object sand has action routine

Object sand has action routine: SAND-FUNCTION
  Review ZIL routine for special object behavior

### 109. Object large_bag has action routine

Object large_bag has action routine: LARGE-BAG-F
  Review ZIL routine for special object behavior

### 110. Object stiletto has action routine

Object stiletto has action routine: STILETTO-FUNCTION
  Review ZIL routine for special object behavior

### 111. Object machine_switch has action routine

Object machine_switch has action routine: MSWITCH-FUNCTION
  Review ZIL routine for special object behavior

### 112. Object wooden_door has action routine

Object wooden_door has action routine: FRONT-DOOR-FCN
  Review ZIL routine for special object behavior

### 113. Object sword has action routine

Object sword has action routine: SWORD-FCN
  Review ZIL routine for special object behavior

### 114. Object pedestal has action routine

Object pedestal has action routine: DUMB-CONTAINER
  Review ZIL routine for special object behavior

### 115. Object torch has action routine

Object torch has action routine: TORCH-OBJECT
  Review ZIL routine for special object behavior

### 116. Object trunk has action routine

Object trunk has action routine: TRUNK-F
  Review ZIL routine for special object behavior

### 117. Object putty has action routine

Object putty has action routine: PUTTY-FCN
  Review ZIL routine for special object behavior

### 118. Object climbable_cliff has action routine

Object climbable_cliff has action routine: CLIFF-OBJECT
  Review ZIL routine for special object behavior

### 119. Object white_cliff has action routine

Object white_cliff has action routine: WCLIF-OBJECT
  Review ZIL routine for special object behavior

### 120. Object egg has action routine

Object egg has action routine: EGG-OBJECT
  Review ZIL routine for special object behavior

### 121. Object canary has action routine

Object canary has action routine: CANARY-OBJECT
  Review ZIL routine for special object behavior

### 122. Object broken_canary has action routine

Object broken_canary has action routine: CANARY-OBJECT
  Review ZIL routine for special object behavior

### 123. Object pseudo_object has action routine

Object pseudo_object has action routine: CRETIN-FCN
  Review ZIL routine for special object behavior

### 124. Object stairs has action routine

Object stairs has action routine: STAIRS-F
  Review ZIL routine for special object behavior

### 125. Object sailor has action routine

Object sailor has action routine: SAILOR-FCN
  Review ZIL routine for special object behavior

### 126. Object ground has action routine

Object ground has action routine: GROUND-FUNCTION
  Review ZIL routine for special object behavior

### 127. Object grue has action routine

Object grue has action routine: GRUE-FUNCTION
  Review ZIL routine for special object behavior

### 128. Object pathobj has action routine

Object pathobj has action routine: PATH-OBJECT
  Review ZIL routine for special object behavior

### 129. Object zorkmid has action routine

Object zorkmid has action routine: ZORKMID-FUNCTION
  Review ZIL routine for special object behavior

### 130. NPC ghosts has action routine

NPC ghosts has action routine: GHOSTS-F
  Review ZIL routine to understand NPC behavior, dialogue, and AI

### 131. NPC bat has action routine

NPC bat has action routine: BAT-F
  Review ZIL routine to understand NPC behavior, dialogue, and AI

### 132. NPC cyclops has action routine

NPC cyclops has action routine: CYCLOPS-FCN
  Review ZIL routine to understand NPC behavior, dialogue, and AI

### 133. NPC thief has action routine

NPC thief has action routine: ROBBER-FUNCTION
  Review ZIL routine to understand NPC behavior, dialogue, and AI

### 134. NPC troll has action routine

NPC troll has action routine: TROLL-FCN
  Review ZIL routine to understand NPC behavior, dialogue, and AI

### 135. NPC me has action routine

NPC me has action routine: CRETIN-FCN
  Review ZIL routine to understand NPC behavior, dialogue, and AI

### 136. NPC adventurer has action routine

NPC adventurer has action routine: 0
  Review ZIL routine to understand NPC behavior, dialogue, and AI

## Additional Conversion Notes

# ZIL Conversion - Adaptation Notes

## Manual Review Required

The following items need manual review and possible implementation:

1. Conditional exit in grating_clearing: down -> condition=GRATING-EXIT
  Consider creating puzzle or adding logic to gate this exit

2. Conditional exit in living_room: down -> condition=TRAP-DOOR-EXIT
  Consider creating puzzle or adding logic to gate this exit

3. Conditional exit in studio: up -> condition=UP-CHIMNEY-FUNCTION
  Consider creating puzzle or adding logic to gate this exit

4. Conditional exit in maze_2: down -> condition=MAZE-DIODES
  Consider creating puzzle or adding logic to gate this exit

5. Conditional exit in maze_7: down -> condition=MAZE-DIODES
  Consider creating puzzle or adding logic to gate this exit

6. Conditional exit in maze_9: down -> condition=MAZE-DIODES
  Consider creating puzzle or adding logic to gate this exit

7. Conditional exit in maze_12: down -> condition=MAZE-DIODES
  Consider creating puzzle or adding logic to gate this exit

8. Object axe is a weapon - add damage/attack stats if needed

9. Object sceptre is a weapon - add damage/attack stats if needed

10. Object pump is a weapon - add damage/attack stats if needed

11. Object knife is a weapon - add damage/attack stats if needed

12. Object rusty_knife is a weapon - add damage/attack stats if needed

13. Object screwdriver is a weapon - add damage/attack stats if needed

14. Object keys is a weapon - add damage/attack stats if needed

15. Object shovel is a weapon - add damage/attack stats if needed

16. Object stiletto is a weapon - add damage/attack stats if needed

17. Object sword is a weapon - add damage/attack stats if needed

18. Object putty is a weapon - add damage/attack stats if needed

19. Object wrench is a weapon - add damage/attack stats if needed

20. Object intnum is a weapon - add damage/attack stats if needed

21. Object hands is a weapon - add damage/attack stats if needed

22. NPC ghosts needs behavior implementation
  Review ZIL routine GHOSTS-F for dialogue and AI logic

23. NPC bat needs behavior implementation
  Review ZIL routine BAT-F for dialogue and AI logic

24. NPC cyclops needs behavior implementation
  Review ZIL routine CYCLOPS-FCN for dialogue and AI logic

25. NPC thief needs behavior implementation
  Review ZIL routine ROBBER-FUNCTION for dialogue and AI logic

26. NPC troll needs behavior implementation
  Review ZIL routine TROLL-FCN for dialogue and AI logic

27. NPC me needs behavior implementation
  Review ZIL routine CRETIN-FCN for dialogue and AI logic



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

