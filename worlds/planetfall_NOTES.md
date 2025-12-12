# ZIL Conversion - Adaptation Notes

Generated from ZIL source files

## Conversion Summary

- **Locations**: 105
- **Items**: 144
- **NPCs**: 9
- **Puzzles**: 0
- **Manual review items**: 185

## Manual Review Required

The following items need manual review and possible implementation:

### 1. Room underwater has action routine

Room underwater has action routine: UNDERWATER-F
  Review ZIL routine for special room behavior

### 2. Room crag has action routine

Room crag has action routine: CRAG-F
  Review ZIL routine for special room behavior

### 3. Conditional exit down in room

Conditional exit down in room: condition=WATER-LEVEL-F
  Review ZIL to determine destination and create puzzle if needed

### 4. Room balcony has action routine

Room balcony has action routine: BALCONY-F
  Review ZIL routine for special room behavior

### 5. Conditional exit down in room

Conditional exit down in room: condition=WATER-LEVEL-F
  Review ZIL to determine destination and create puzzle if needed

### 6. Room winding_stair has action routine

Room winding_stair has action routine: WINDING-STAIR-F
  Review ZIL routine for special room behavior

### 7. Room courtyard has action routine

Room courtyard has action routine: COURTYARD-F
  Review ZIL routine for special room behavior

### 8. Room rec_area has action routine

Room rec_area has action routine: REC-AREA-F
  Review ZIL routine for special room behavior

### 9. Room conference_room has action routine

Room conference_room has action routine: CONFERENCE-ROOM-F
  Review ZIL routine for special room behavior

### 10. Room mess_corridor has action routine

Room mess_corridor has action routine: MESS-CORRIDOR-F
  Review ZIL routine for special room behavior

### 11. Conditional exit east in room

Conditional exit east in room: condition=LONG-HALL-F
  Review ZIL to determine destination and create puzzle if needed

### 12. Room mess_hall has action routine

Room mess_hall has action routine: MESS-HALL-F
  Review ZIL routine for special room behavior

### 13. Conditional exit west in room

Conditional exit west in room: condition=LONG-HALL-F
  Review ZIL to determine destination and create puzzle if needed

### 14. Room admin_corridor_s has action routine

Room admin_corridor_s has action routine: ADMIN-CORRIDOR-S-F
  Review ZIL routine for special room behavior

### 15. Conditional exit north in room

Conditional exit north in room: condition=LADDER-EXIT-F
  Review ZIL to determine destination and create puzzle if needed

### 16. Room admin_corridor has action routine

Room admin_corridor has action routine: ADMIN-CORRIDOR-F
  Review ZIL routine for special room behavior

### 17. Conditional exit south in room

Conditional exit south in room: condition=LADDER-EXIT-F
  Review ZIL to determine destination and create puzzle if needed

### 18. Room admin_corridor_n has action routine

Room admin_corridor_n has action routine: ADMIN-CORRIDOR-N-F
  Review ZIL routine for special room behavior

### 19. Room systems_monitors has action routine

Room systems_monitors has action routine: SYSTEMS-MONITORS-F
  Review ZIL routine for special room behavior

### 20. Room machine_shop has action routine

Room machine_shop has action routine: MACHINE-SHOP-F
  Review ZIL routine for special room behavior

### 21. Conditional exit north in room

Conditional exit north in room: condition=ELEVATOR-ENTER-F
  Review ZIL to determine destination and create puzzle if needed

### 22. Conditional exit south in room

Conditional exit south in room: condition=ELEVATOR-ENTER-F
  Review ZIL to determine destination and create puzzle if needed

### 23. Room elevator_lobby has action routine

Room elevator_lobby has action routine: ELEVATOR-LOBBY-F
  Review ZIL routine for special room behavior

### 24. Conditional exit south in room

Conditional exit south in room: condition=ELEVATOR-EXIT-F
  Review ZIL to determine destination and create puzzle if needed

### 25. Conditional exit out in room

Conditional exit out in room: condition=ELEVATOR-EXIT-F
  Review ZIL to determine destination and create puzzle if needed

### 26. Room upper_elevator has action routine

Room upper_elevator has action routine: UPPER-ELEVATOR-F
  Review ZIL routine for special room behavior

### 27. Conditional exit north in room

Conditional exit north in room: condition=ELEVATOR-EXIT-F
  Review ZIL to determine destination and create puzzle if needed

### 28. Conditional exit out in room

Conditional exit out in room: condition=ELEVATOR-EXIT-F
  Review ZIL to determine destination and create puzzle if needed

### 29. Room lower_elevator has action routine

Room lower_elevator has action routine: LOWER-ELEVATOR-F
  Review ZIL routine for special room behavior

### 30. Room comm_room has action routine

Room comm_room has action routine: COMM-ROOM-F
  Review ZIL routine for special room behavior

### 31. Conditional exit south in room

Conditional exit south in room: condition=OTHER-ELEVATOR-ENTER-F
  Review ZIL to determine destination and create puzzle if needed

### 32. Conditional exit in in room

Conditional exit in in room: condition=OTHER-ELEVATOR-ENTER-F
  Review ZIL to determine destination and create puzzle if needed

### 33. Conditional exit north in room

Conditional exit north in room: condition=SHUTTLE-ENTER-F
  Review ZIL to determine destination and create puzzle if needed

### 34. Conditional exit south in room

Conditional exit south in room: condition=SHUTTLE-ENTER-F
  Review ZIL to determine destination and create puzzle if needed

### 35. Room kalamontee_platform has action routine

Room kalamontee_platform has action routine: KALAMONTEE-PLATFORM-F
  Review ZIL routine for special room behavior

### 36. Room deck_nine has action routine

Room deck_nine has action routine: DECK-NINE-F
  Review ZIL routine for special room behavior

### 37. Room gangway has action routine

Room gangway has action routine: GANGWAY-F
  Review ZIL routine for special room behavior

### 38. Conditional exit east in room

Conditional exit east in room: condition=POD-EXIT-F
  Review ZIL to determine destination and create puzzle if needed

### 39. Conditional exit up in room

Conditional exit up in room: condition=POD-EXIT-F
  Review ZIL to determine destination and create puzzle if needed

### 40. Conditional exit out in room

Conditional exit out in room: condition=POD-EXIT-F
  Review ZIL to determine destination and create puzzle if needed

### 41. Room escape_pod has action routine

Room escape_pod has action routine: ESCAPE-POD-F
  Review ZIL routine for special room behavior

### 42. Conditional exit north in room

Conditional exit north in room: condition=SHUTTLE-EXIT-F
  Review ZIL to determine destination and create puzzle if needed

### 43. Room shuttle_car_alfie has action routine

Room shuttle_car_alfie has action routine: SHUTTLE-CAR-F
  Review ZIL routine for special room behavior

### 44. Room alfie_control_east has action routine

Room alfie_control_east has action routine: CONTROL-CABIN-F
  Review ZIL routine for special room behavior

### 45. Room alfie_control_west has action routine

Room alfie_control_west has action routine: CONTROL-CABIN-F
  Review ZIL routine for special room behavior

### 46. Conditional exit south in room

Conditional exit south in room: condition=SHUTTLE-EXIT-F
  Review ZIL to determine destination and create puzzle if needed

### 47. Room shuttle_car_betty has action routine

Room shuttle_car_betty has action routine: SHUTTLE-CAR-F
  Review ZIL routine for special room behavior

### 48. Room betty_control_east has action routine

Room betty_control_east has action routine: CONTROL-CABIN-F
  Review ZIL routine for special room behavior

### 49. Room betty_control_west has action routine

Room betty_control_west has action routine: CONTROL-CABIN-F
  Review ZIL routine for special room behavior

### 50. Conditional exit north in room

Conditional exit north in room: condition=SHUTTLE-ENTER-F
  Review ZIL to determine destination and create puzzle if needed

### 51. Conditional exit south in room

Conditional exit south in room: condition=SHUTTLE-ENTER-F
  Review ZIL to determine destination and create puzzle if needed

### 52. Room lawanda_platform has action routine

Room lawanda_platform has action routine: LAWANDA-PLATFORM-F
  Review ZIL routine for special room behavior

### 53. Room infirmary has action routine

Room infirmary has action routine: INFIRMARY-F
  Review ZIL routine for special room behavior

### 54. Room planetary_defense has action routine

Room planetary_defense has action routine: PLANETARY-DEFENSE-F
  Review ZIL routine for special room behavior

### 55. Room planetary_course_control has action routine

Room planetary_course_control has action routine: PLANETARY-COURSE-CONTROL-F
  Review ZIL routine for special room behavior

### 56. Room projcon_office has action routine

Room projcon_office has action routine: PROJCON-OFFICE-F
  Review ZIL routine for special room behavior

### 57. Conditional exit north in room

Conditional exit north in room: condition=CRYO-EXIT-F
  Review ZIL to determine destination and create puzzle if needed

### 58. Room cryo_elevator has action routine

Room cryo_elevator has action routine: CRYO-ELEVATOR-F
  Review ZIL routine for special room behavior

### 59. Room cryo_anteroom has action routine

Room cryo_anteroom has action routine: CRYO-ANTEROOM-F
  Review ZIL routine for special room behavior

### 60. Room bio_lock_east has action routine

Room bio_lock_east has action routine: BIO-LOCK-EAST-F
  Review ZIL routine for special room behavior

### 61. Room bio_lab has action routine

Room bio_lab has action routine: BIO-LAB-F
  Review ZIL routine for special room behavior

### 62. Room radiation_lab has action routine

Room radiation_lab has action routine: RADIATION-LAB-F
  Review ZIL routine for special room behavior

### 63. Room lab_office has action routine

Room lab_office has action routine: LAB-OFFICE-F
  Review ZIL routine for special room behavior

### 64. Room station_384 has action routine

Room station_384 has action routine: STATION-384-F
  Review ZIL routine for special room behavior

### 65. Room middle_of_strip has action routine

Room middle_of_strip has action routine: MIDDLE-OF-STRIP-F
  Review ZIL routine for special room behavior

### 66. Conditional exit east in room

Conditional exit east in room: condition=RELAY-EXIT-F
  Review ZIL to determine destination and create puzzle if needed

### 67. Room strip_near_relay has action routine

Room strip_near_relay has action routine: STRIP-NEAR-RELAY-F
  Review ZIL routine for special room behavior

### 68. Object conference_door has action routine

Object conference_door has action routine: CONFERENCE-DOOR-F
  Review ZIL routine for special object behavior

### 69. Object combination_dial has action routine

Object combination_dial has action routine: COMBINATION-DIAL-F
  Review ZIL routine for special object behavior

### 70. Object storage_west_door has action routine

Object storage_west_door has action routine: STORAGE-WEST-DOOR-F
  Review ZIL routine for special object behavior

### 71. Object padlock has action routine

Object padlock has action routine: PADLOCK-F
  Review ZIL routine for special object behavior

### 72. Object can has action routine

Object can has action routine: CAN-F
  Review ZIL routine for special object behavior

### 73. Object ladder has action routine

Object ladder has action routine: LADDER-F
  Review ZIL routine for special object behavior

### 74. Object kitchen_door has action routine

Object kitchen_door has action routine: KITCHEN-DOOR-F
  Review ZIL routine for special object behavior

### 75. Object dispenser has action routine

Object dispenser has action routine: DISPENSER-F
  Review ZIL routine for special object behavior

### 76. Object high_protein has action routine

Object high_protein has action routine: HIGH-PROTEIN-F
  Review ZIL routine for special object behavior

### 77. Object crevice has action routine

Object crevice has action routine: CREVICE-F
  Review ZIL routine for special object behavior

### 78. Object key has action routine

Object key has action routine: KEY-F
  Review ZIL routine for special object behavior

### 79. Object rift has action routine

Object rift has action routine: RIFT-F
  Review ZIL routine for special object behavior

### 80. Object small_desk has action routine

Object small_desk has action routine: DESK-F
  Review ZIL routine for special object behavior

### 81. Object large_desk has action routine

Object large_desk has action routine: DESK-F
  Review ZIL routine for special object behavior

### 82. Object oil_can has action routine

Object oil_can has action routine: OIL-CAN-F
  Review ZIL routine for special object behavior

### 83. Object carton has action routine

Object carton has action routine: CARTON-F
  Review ZIL routine for special object behavior

### 84. Object cracked_board has action routine

Object cracked_board has action routine: CRACKED-BOARD-F
  Review ZIL routine for special object behavior

### 85. Object good_bedistor has action routine

Object good_bedistor has action routine: GOOD-BEDISTOR-F
  Review ZIL routine for special object behavior

### 86. Object reactor_elevator_door has action routine

Object reactor_elevator_door has action routine: REACTOR-ELEVATOR-DOOR-F
  Review ZIL routine for special object behavior

### 87. Object flask has action routine

Object flask has action routine: FLASK-F
  Review ZIL routine for special object behavior

### 88. Object magnet has action routine

Object magnet has action routine: MAGNET-F
  Review ZIL routine for special object behavior

### 89. Object chemical_dispenser has action routine

Object chemical_dispenser has action routine: CHEMICAL-DISPENSER-F
  Review ZIL routine for special object behavior

### 90. Object red_button has action routine

Object red_button has action routine: CHEM-BUTTON-F
  Review ZIL routine for special object behavior

### 91. Object blue_button has action routine

Object blue_button has action routine: CHEM-BUTTON-F
  Review ZIL routine for special object behavior

### 92. Object green_button has action routine

Object green_button has action routine: CHEM-BUTTON-F
  Review ZIL routine for special object behavior

### 93. Object yellow_button has action routine

Object yellow_button has action routine: CHEM-BUTTON-F
  Review ZIL routine for special object behavior

### 94. Object gray_button has action routine

Object gray_button has action routine: CHEM-BUTTON-F
  Review ZIL routine for special object behavior

### 95. Object brown_button has action routine

Object brown_button has action routine: CHEM-BUTTON-F
  Review ZIL routine for special object behavior

### 96. Object black_button has action routine

Object black_button has action routine: CHEM-BUTTON-F
  Review ZIL routine for special object behavior

### 97. Object round_white_button has action routine

Object round_white_button has action routine: CHEM-BUTTON-F
  Review ZIL routine for special object behavior

### 98. Object square_white_button has action routine

Object square_white_button has action routine: CHEM-BUTTON-F
  Review ZIL routine for special object behavior

### 99. Object floyd has action routine

Object floyd has action routine: FLOYD-F
  Review ZIL routine for special object behavior

### 100. Object dead_floyd has action routine

Object dead_floyd has action routine: DEAD-FLOYD-F
  Review ZIL routine for special object behavior

### 101. Object upper_elevator_door has action routine

Object upper_elevator_door has action routine: UPPER-ELEVATOR-DOOR-F
  Review ZIL routine for special object behavior

### 102. Object lower_elevator_door has action routine

Object lower_elevator_door has action routine: LOWER-ELEVATOR-DOOR-F
  Review ZIL routine for special object behavior

### 103. Object blue_elevator_button has action routine

Object blue_elevator_button has action routine: BLUE-ELEVATOR-BUTTON-F
  Review ZIL routine for special object behavior

### 104. Object red_elevator_button has action routine

Object red_elevator_button has action routine: RED-ELEVATOR-BUTTON-F
  Review ZIL routine for special object behavior

### 105. Object elevator_button has action routine

Object elevator_button has action routine: ELEVATOR-BUTTON-F
  Review ZIL routine for special object behavior

### 106. Object helicopter_object has action routine

Object helicopter_object has action routine: HELICOPTER-OBJECT-F
  Review ZIL routine for special object behavior

### 107. Object playback_button has action routine

Object playback_button has action routine: PLAYBACK-BUTTON-F
  Review ZIL routine for special object behavior

### 108. Object chemical_fluid has action routine

Object chemical_fluid has action routine: CHEMICAL-FLUID-F
  Review ZIL routine for special object behavior

### 109. Object pseudo_object has action routine

Object pseudo_object has action routine: GO
  Review ZIL routine for special object behavior

### 110. Object ground has action routine

Object ground has action routine: GROUND-F
  Review ZIL routine for special object behavior

### 111. Object window has action routine

Object window has action routine: WINDOW-F
  Review ZIL routine for special object behavior

### 112. Object cliff has action routine

Object cliff has action routine: CLIFF-F
  Review ZIL routine for special object behavior

### 113. Object ocean has action routine

Object ocean has action routine: OCEAN-F
  Review ZIL routine for special object behavior

### 114. Object tables has action routine

Object tables has action routine: TABLES-F
  Review ZIL routine for special object behavior

### 115. Object shelves has action routine

Object shelves has action routine: SHELVES-F
  Review ZIL routine for special object behavior

### 116. Object lights has action routine

Object lights has action routine: LIGHTS-F
  Review ZIL routine for special object behavior

### 117. Object global_doorway has action routine

Object global_doorway has action routine: GLOBAL-DOORWAY-F
  Review ZIL routine for special object behavior

### 118. Object controls has action routine

Object controls has action routine: CONTROLS-F
  Review ZIL routine for special object behavior

### 119. Object global_games has action routine

Object global_games has action routine: GLOBAL-GAMES-F
  Review ZIL routine for special object behavior

### 120. Object hands has action routine

Object hands has action routine: HANDS-F
  Review ZIL routine for special object behavior

### 121. Object sleep has action routine

Object sleep has action routine: SLEEP-F
  Review ZIL routine for special object behavior

### 122. Object chronometer has action routine

Object chronometer has action routine: CHRONOMETER-F
  Review ZIL routine for special object behavior

### 123. Object patrol_uniform has action routine

Object patrol_uniform has action routine: PATROL-UNIFORM-F
  Review ZIL routine for special object behavior

### 124. Object diary has action routine

Object diary has action routine: DIARY-F
  Review ZIL routine for special object behavior

### 125. Object diary_button has action routine

Object diary_button has action routine: DIARY-BUTTON-F
  Review ZIL routine for special object behavior

### 126. Object celery has action routine

Object celery has action routine: CELERY-F
  Review ZIL routine for special object behavior

### 127. Object global_pod has action routine

Object global_pod has action routine: GLOBAL-POD-F
  Review ZIL routine for special object behavior

### 128. Object safety_web has action routine

Object safety_web has action routine: SAFETY-WEB-F
  Review ZIL routine for special object behavior

### 129. Object towel has action routine

Object towel has action routine: TOWEL-F
  Review ZIL routine for special object behavior

### 130. Object food_kit has action routine

Object food_kit has action routine: FOOD-KIT-F
  Review ZIL routine for special object behavior

### 131. Object red_goo has action routine

Object red_goo has action routine: GOO-F
  Review ZIL routine for special object behavior

### 132. Object brown_goo has action routine

Object brown_goo has action routine: GOO-F
  Review ZIL routine for special object behavior

### 133. Object green_goo has action routine

Object green_goo has action routine: GOO-F
  Review ZIL routine for special object behavior

### 134. Object pod_door has action routine

Object pod_door has action routine: POD-DOOR-F
  Review ZIL routine for special object behavior

### 135. Object corridor_door has action routine

Object corridor_door has action routine: GANGWAY-DOOR-F
  Review ZIL routine for special object behavior

### 136. Object gangway_door has action routine

Object gangway_door has action routine: GANGWAY-DOOR-F
  Review ZIL routine for special object behavior

### 137. Object slot has action routine

Object slot has action routine: SLOT-F
  Review ZIL routine for special object behavior

### 138. Object teleportation_button_1 has action routine

Object teleportation_button_1 has action routine: TELEPORTATION-BUTTON-1-F
  Review ZIL routine for special object behavior

### 139. Object teleportation_button_2 has action routine

Object teleportation_button_2 has action routine: TELEPORTATION-BUTTON-2-F
  Review ZIL routine for special object behavior

### 140. Object teleportation_button_3 has action routine

Object teleportation_button_3 has action routine: TELEPORTATION-BUTTON-3-F
  Review ZIL routine for special object behavior

### 141. Object global_shuttle has action routine

Object global_shuttle has action routine: GLOBAL-SHUTTLE-F
  Review ZIL routine for special object behavior

### 142. Object lever has action routine

Object lever has action routine: LEVER-F
  Review ZIL routine for special object behavior

### 143. Object shuttle_door has action routine

Object shuttle_door has action routine: SHUTTLE-DOOR-F
  Review ZIL routine for special object behavior

### 144. Object bed has action routine

Object bed has action routine: BED-F
  Review ZIL routine for special object behavior

### 145. Object red_spool has action routine

Object red_spool has action routine: RED-SPOOL-F
  Review ZIL routine for special object behavior

### 146. Object medicine has action routine

Object medicine has action routine: MEDICINE-F
  Review ZIL routine for special object behavior

### 147. Object robot_hole has action routine

Object robot_hole has action routine: ROBOT-HOLE-F
  Review ZIL routine for special object behavior

### 148. Object good_board has action routine

Object good_board has action routine: GOOD-BOARD-F
  Review ZIL routine for special object behavior

### 149. Object access_panel has action routine

Object access_panel has action routine: ACCESS-PANEL-F
  Review ZIL routine for special object behavior

### 150. Object first_board has action routine

Object first_board has action routine: BOARD-F
  Review ZIL routine for special object behavior

### 151. Object fourth_board has action routine

Object fourth_board has action routine: BOARD-F
  Review ZIL routine for special object behavior

### 152. Object third_board has action routine

Object third_board has action routine: BOARD-F
  Review ZIL routine for special object behavior

### 153. Object second_board has action routine

Object second_board has action routine: BOARD-F
  Review ZIL routine for special object behavior

### 154. Object fried_board has action routine

Object fried_board has action routine: FRIED-BOARD-F
  Review ZIL routine for special object behavior

### 155. Object cube has action routine

Object cube has action routine: CUBE-F
  Review ZIL routine for special object behavior

### 156. Object bad_bedistor has action routine

Object bad_bedistor has action routine: BAD-BEDISTOR-F
  Review ZIL routine for special object behavior

### 157. Object green_spool has action routine

Object green_spool has action routine: GREEN-SPOOL-F
  Review ZIL routine for special object behavior

### 158. Object terminal has action routine

Object terminal has action routine: TERMINAL-F
  Review ZIL routine for special object behavior

### 159. Object spool_reader has action routine

Object spool_reader has action routine: SPOOL-READER-F
  Review ZIL routine for special object behavior

### 160. Object print_out has action routine

Object print_out has action routine: PRINT-OUT-F
  Review ZIL routine for special object behavior

### 161. Object mini_card has action routine

Object mini_card has action routine: MINI-CARD-F
  Review ZIL routine for special object behavior

### 162. Object lab_uniform has action routine

Object lab_uniform has action routine: LAB-UNIFORM-F
  Review ZIL routine for special object behavior

### 163. Object combination_paper has action routine

Object combination_paper has action routine: COMBINATION-PAPER-F
  Review ZIL routine for special object behavior

### 164. Object bio_door_east has action routine

Object bio_door_east has action routine: BIO-DOOR-EAST-F
  Review ZIL routine for special object behavior

### 165. Object bio_door_west has action routine

Object bio_door_west has action routine: BIO-DOOR-WEST-F
  Review ZIL routine for special object behavior

### 166. Object rad_door_east has action routine

Object rad_door_east has action routine: RAD-DOOR-EAST-F
  Review ZIL routine for special object behavior

### 167. Object rad_door_west has action routine

Object rad_door_west has action routine: RAD-DOOR-WEST-F
  Review ZIL routine for special object behavior

### 168. Object lamp has action routine

Object lamp has action routine: LAMP-F
  Review ZIL routine for special object behavior

### 169. Object lab_desk has action routine

Object lab_desk has action routine: LAB-DESK-F
  Review ZIL routine for special object behavior

### 170. Object light_button has action routine

Object light_button has action routine: LIGHT-BUTTON-F
  Review ZIL routine for special object behavior

### 171. Object dark_button has action routine

Object dark_button has action routine: DARK-BUTTON-F
  Review ZIL routine for special object behavior

### 172. Object fungicide_button has action routine

Object fungicide_button has action routine: FUNGICIDE-BUTTON-F
  Review ZIL routine for special object behavior

### 173. Object relay has action routine

Object relay has action routine: RELAY-F
  Review ZIL routine for special object behavior

### 174. Object laser has action routine

Object laser has action routine: LASER-F
  Review ZIL routine for special object behavior

### 175. Object laser_dial has action routine

Object laser_dial has action routine: LASER-DIAL-F
  Review ZIL routine for special object behavior

### 176. Object strip has action routine

Object strip has action routine: STRIP-F
  Review ZIL routine for special object behavior

### 177. NPC me has action routine

NPC me has action routine: CRETIN-F
  Review ZIL routine to understand NPC behavior, dialogue, and AI

### 178. NPC measle has action routine

NPC measle has action routine: MEASLE-F
  Review ZIL routine to understand NPC behavior, dialogue, and AI

### 179. NPC blather has action routine

NPC blather has action routine: BLATHER-F
  Review ZIL routine to understand NPC behavior, dialogue, and AI

### 180. NPC ambassador has action routine

NPC ambassador has action routine: AMBASSADOR-F
  Review ZIL routine to understand NPC behavior, dialogue, and AI

### 181. NPC microbe has action routine

NPC microbe has action routine: MICROBE-F
  Review ZIL routine to understand NPC behavior, dialogue, and AI

### 182. NPC rat_ant has action routine

NPC rat_ant has action routine: None
  Review ZIL routine to understand NPC behavior, dialogue, and AI

### 183. NPC troll has action routine

NPC troll has action routine: None
  Review ZIL routine to understand NPC behavior, dialogue, and AI

### 184. NPC grue has action routine

NPC grue has action routine: GRUE-F
  Review ZIL routine to understand NPC behavior, dialogue, and AI

### 185. NPC triffid has action routine

NPC triffid has action routine: None
  Review ZIL routine to understand NPC behavior, dialogue, and AI

## Additional Conversion Notes

# ZIL Conversion - Adaptation Notes

## Manual Review Required

The following items need manual review and possible implementation:

1. Conditional exit in balcony: down -> condition=WATER-LEVEL-F
  Consider creating puzzle or adding logic to gate this exit

2. Conditional exit in winding_stair: down -> condition=WATER-LEVEL-F
  Consider creating puzzle or adding logic to gate this exit

3. Conditional exit in dorm_corridor: east -> condition=LONG-HALL-F
  Consider creating puzzle or adding logic to gate this exit

4. Conditional exit in corridor_junction: west -> condition=LONG-HALL-F
  Consider creating puzzle or adding logic to gate this exit

5. Conditional exit in admin_corridor: north -> condition=LADDER-EXIT-F
  Consider creating puzzle or adding logic to gate this exit

6. Conditional exit in admin_corridor_n: south -> condition=LADDER-EXIT-F
  Consider creating puzzle or adding logic to gate this exit

7. Conditional exit in elevator_lobby: north -> condition=ELEVATOR-ENTER-F
  Consider creating puzzle or adding logic to gate this exit

8. Conditional exit in elevator_lobby: south -> condition=ELEVATOR-ENTER-F
  Consider creating puzzle or adding logic to gate this exit

9. Conditional exit in upper_elevator: south -> condition=ELEVATOR-EXIT-F
  Consider creating puzzle or adding logic to gate this exit

10. Conditional exit in upper_elevator: out -> condition=ELEVATOR-EXIT-F
  Consider creating puzzle or adding logic to gate this exit

11. Conditional exit in lower_elevator: north -> condition=ELEVATOR-EXIT-F
  Consider creating puzzle or adding logic to gate this exit

12. Conditional exit in lower_elevator: out -> condition=ELEVATOR-EXIT-F
  Consider creating puzzle or adding logic to gate this exit

13. Conditional exit in waiting_area: south -> condition=OTHER-ELEVATOR-ENTER-F
  Consider creating puzzle or adding logic to gate this exit

14. Conditional exit in waiting_area: in -> condition=OTHER-ELEVATOR-ENTER-F
  Consider creating puzzle or adding logic to gate this exit

15. Conditional exit in kalamontee_platform: north -> condition=SHUTTLE-ENTER-F
  Consider creating puzzle or adding logic to gate this exit

16. Conditional exit in kalamontee_platform: south -> condition=SHUTTLE-ENTER-F
  Consider creating puzzle or adding logic to gate this exit

17. Conditional exit in escape_pod: east -> condition=POD-EXIT-F
  Consider creating puzzle or adding logic to gate this exit

18. Conditional exit in escape_pod: up -> condition=POD-EXIT-F
  Consider creating puzzle or adding logic to gate this exit

19. Conditional exit in escape_pod: out -> condition=POD-EXIT-F
  Consider creating puzzle or adding logic to gate this exit

20. Conditional exit in shuttle_car_alfie: north -> condition=SHUTTLE-EXIT-F
  Consider creating puzzle or adding logic to gate this exit

21. Conditional exit in shuttle_car_betty: south -> condition=SHUTTLE-EXIT-F
  Consider creating puzzle or adding logic to gate this exit

22. Conditional exit in lawanda_platform: north -> condition=SHUTTLE-ENTER-F
  Consider creating puzzle or adding logic to gate this exit

23. Conditional exit in lawanda_platform: south -> condition=SHUTTLE-ENTER-F
  Consider creating puzzle or adding logic to gate this exit

24. Conditional exit in cryo_elevator: north -> condition=CRYO-EXIT-F
  Consider creating puzzle or adding logic to gate this exit

25. Conditional exit in strip_near_relay: east -> condition=RELAY-EXIT-F
  Consider creating puzzle or adding logic to gate this exit

26. Object key is a weapon - add damage/attack stats if needed

27. NPC me needs behavior implementation
  Review ZIL routine CRETIN-F for dialogue and AI logic

28. NPC measle needs behavior implementation
  Review ZIL routine MEASLE-F for dialogue and AI logic

29. NPC blather needs behavior implementation
  Review ZIL routine BLATHER-F for dialogue and AI logic

30. NPC ambassador needs behavior implementation
  Review ZIL routine AMBASSADOR-F for dialogue and AI logic

31. NPC microbe needs behavior implementation
  Review ZIL routine MICROBE-F for dialogue and AI logic

32. NPC grue needs behavior implementation
  Review ZIL routine GRUE-F for dialogue and AI logic



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

